"""Bloque 3 de F4 (persistencia): imagen y registro en S3 con los campos del receptor."""

from __future__ import annotations

import hashlib
import json

import boto3
import pytest
from botocore import UNSIGNED
from botocore.config import Config
from botocore.exceptions import ProfileNotFound
from botocore.stub import ANY, Stubber
from fastapi import FastAPI
from fastapi.testclient import TestClient

from conftest import BUCKET, CID, PREFIX, RECEIVED, make_jpeg, post, valid_event
from fake_s3 import client_error
from p4.captures import api
from p4.captures.event import CaptureEvent
from p4.captures.image import inspect_image
from p4.captures.s3_store import S3CaptureStore, UnavailableStore


def test_guarda_imagen_y_registro_con_campos_del_receptor(s3_client, s3):
    image = make_jpeg(64, 48)
    sent = valid_event(image)
    answer = post(s3_client, sent, image)

    assert answer.status_code == 201, answer.text
    assert answer.json() == {
        "status": "created",
        "capture_id": CID,
        "image_key": f"edge-captures/images/{CID}.jpg",
        "record_key": f"edge-captures/events/{CID}.json",
        "received_at": "2026-10-08T23:00:00.123+00:00",
        "warnings": [],
    }
    assert s3.keys() == [f"edge-captures/events/{CID}.json", f"edge-captures/images/{CID}.jpg"]

    photo = s3.objects[f"edge-captures/images/{CID}.jpg"]
    assert photo.body == image, "la imagen se guarda byte por byte"
    assert photo.content_type == "image/jpeg"
    assert photo.metadata == {"sha256": hashlib.sha256(image).hexdigest(), "capture-id": CID}

    stored = json.loads(s3.objects[f"edge-captures/events/{CID}.json"].body)
    for name, value in sent.items():
        assert stored[name] == value, f"{name} no coincide con lo enviado"
    assert stored["received_at"] == "2026-10-08T23:00:00.123+00:00"
    assert stored["image_key"] == f"edge-captures/images/{CID}.jpg"
    assert (stored["image_bytes"], stored["image_width"], stored["image_height"]) == (
        len(image),
        64,
        48,
    )
    # Capturada 2026-10-08T15:30:12-06:00 = 21:30:12Z; recibida 23:00:00.123Z.
    assert stored["delivery_delay_s"] == 5388.123
    assert stored["warnings"] == []


def test_reloj_adelantado_queda_senalado_en_el_registro(s3_client, s3):
    image = make_jpeg()
    answer = post(s3_client, valid_event(image, captured_at="2026-10-08T17:10:00-06:00"), image)
    assert answer.status_code == 201
    assert answer.json()["warnings"] == ["captured_at_en_el_futuro"]
    stored = json.loads(s3.objects[f"edge-captures/events/{CID}.json"].body)
    assert stored["warnings"] == ["captured_at_en_el_futuro"]


def test_region_se_guarda(s3_client, s3):
    image = make_jpeg(64, 48)
    region = {"x": 4, "y": 2, "width": 40, "height": 30}
    assert post(s3_client, valid_event(image, region=region), image).status_code == 201
    assert json.loads(s3.objects[f"edge-captures/events/{CID}.json"].body)["region"] == region


def test_error_de_s3_responde_503_visible(s3_client, s3):
    s3.fail_next["put_object"] = client_error("AccessDenied", 403, "PutObject")
    image = make_jpeg()
    answer = post(s3_client, valid_event(image), image)
    assert answer.status_code == 503
    body = answer.json()
    assert body["error"] == "almacenamiento_no_disponible"
    assert "AccessDenied" in body["mensaje"]
    assert "mismo capture_id" in body["mensaje"]
    assert s3.keys() == []


def test_falla_a_la_mitad_se_completa_con_el_reintento(s3_client, s3):
    """La imagen se guardo pero el registro no: el reintento lo completa sin duplicar."""
    image = make_jpeg()
    s3.calls.clear()
    # Primera llamada de put_object (imagen) pasa; la segunda (registro) falla.
    original = s3.put_object
    state = {"n": 0}

    def flaky(**kwargs):
        state["n"] += 1
        if state["n"] == 2:
            raise client_error("InternalError", 500, "PutObject")
        return original(**kwargs)

    s3.put_object = flaky  # type: ignore[method-assign]
    first = post(s3_client, valid_event(image), image)
    assert first.status_code == 503
    assert s3.keys() == [f"edge-captures/images/{CID}.jpg"]

    retry = post(s3_client, valid_event(image), image)
    assert retry.status_code == 201, retry.text
    assert s3.keys() == [f"edge-captures/events/{CID}.json", f"edge-captures/images/{CID}.jpg"]


def test_perfil_inexistente_responde_503(settings):
    store = UnavailableStore("perfil de AWS 'no-existe' no disponible (ProfileNotFound)")
    app = FastAPI()
    app.include_router(api.router)
    app.dependency_overrides[api.get_settings] = lambda: settings
    app.dependency_overrides[api.get_store] = lambda: store
    image = make_jpeg()
    answer = post(TestClient(app), valid_event(image), image)
    assert answer.status_code == 503
    assert "no-existe" in answer.json()["mensaje"]


# --- cliente S3 que no se pudo crear: 503 visible y nuevo intento sin reiniciar ------------


@pytest.fixture
def fresh_stores(monkeypatch):
    """Fabrica de clientes vacia y reloj controlado; boto3.Session sustituible."""
    api.reset_stores()
    now = {"t": 1000.0}
    monkeypatch.setattr(api, "_clock", lambda: now["t"])
    yield now
    api.reset_stores()


def test_perfil_inexistente_no_rompe_el_arranque(fresh_stores):
    store = api._s3_store(BUCKET, PREFIX, "perfil-que-no-existe-en-ninguna-maquina", "us-east-1")
    assert isinstance(store, UnavailableStore)
    assert "se reintenta en 5 s" in store.reason


def test_perfil_inexistente_se_reintenta_tras_la_pausa_y_se_recupera(fresh_stores, monkeypatch):
    attempts = {"n": 0}
    real_session = boto3.Session

    def session(profile_name=None):
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise ProfileNotFound(profile="p4-emilio")
        # Crear el cliente no resuelve credenciales: la prueba no toca AWS.
        return real_session(region_name="us-east-1")

    monkeypatch.setattr(api.boto3, "Session", session)
    first = api._s3_store(BUCKET, PREFIX, "p4-emilio", "us-east-1")
    assert isinstance(first, UnavailableStore)

    # Dentro de la pausa: no se vuelve a intentar y el 503 sigue visible.
    fresh_stores["t"] += api.STORE_RETRY_S - 0.1
    assert api._s3_store(BUCKET, PREFIX, "p4-emilio", "us-east-1") is first
    assert attempts["n"] == 1

    # Pasada la pausa: nuevo intento; ahora funciona y el cliente queda guardado.
    fresh_stores["t"] += 0.2
    recovered = api._s3_store(BUCKET, PREFIX, "p4-emilio", "us-east-1")
    assert isinstance(recovered, S3CaptureStore)
    assert api._s3_store(BUCKET, PREFIX, "p4-emilio", "us-east-1") is recovered
    assert attempts["n"] == 2


def test_mientras_falla_el_post_sigue_respondiendo_503(fresh_stores, settings, monkeypatch):
    def broken(profile_name=None):
        raise ProfileNotFound(profile="p4-emilio")

    monkeypatch.setattr(api.boto3, "Session", broken)
    app = FastAPI()
    app.include_router(api.router)
    app.dependency_overrides[api.get_settings] = lambda: settings.model_copy(
        update={"aws_profile": "p4-emilio"}
    )
    client = TestClient(app)
    image = make_jpeg()
    for _ in range(2):
        answer = post(client, valid_event(image), image)
        assert answer.status_code == 503
        assert answer.json()["error"] == "receptor_no_configurado"
        assert "p4-emilio" in answer.json()["mensaje"]


def test_llamadas_reales_a_s3_con_los_parametros_del_contrato():
    """Stubber valida los nombres y tipos contra el modelo de la API de S3 (p. ej. IfNoneMatch)."""
    client = boto3.client("s3", region_name="us-east-1", config=Config(signature_version=UNSIGNED))
    image_bytes = make_jpeg()
    image = inspect_image(image_bytes, 1_000_000)
    event = CaptureEvent.model_validate(valid_event(image_bytes))
    with Stubber(client) as stub:
        stub.add_response(
            "put_object",
            {"VersionId": "v1"},
            {
                "Bucket": BUCKET,
                "Key": f"edge-captures/images/{CID}.jpg",
                "Body": image_bytes,
                "ContentType": "image/jpeg",
                "Metadata": {"sha256": image.sha256, "capture-id": CID},
                "IfNoneMatch": "*",
            },
        )
        stub.add_response(
            "put_object",
            {"VersionId": "v2"},
            {
                "Bucket": BUCKET,
                "Key": f"edge-captures/events/{CID}.json",
                "Body": ANY,
                "ContentType": "application/json",
                "Metadata": {},
                "IfNoneMatch": "*",
            },
        )
        result = S3CaptureStore(client, BUCKET, PREFIX, clock=lambda: RECEIVED).save(event, image)
        stub.assert_no_pending_responses()
    assert result.status == "created"
