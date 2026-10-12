"""Bloque 4 de F4 (idempotencia): el mismo capture_id nunca crea un duplicado."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest

from conftest import CID, PREFIX, make_jpeg, post, valid_event
from fake_s3 import FakeS3
from p4.captures.event import CaptureEvent
from p4.captures.image import inspect_image
from p4.captures.s3_store import S3CaptureStore

RECORD = f"edge-captures/events/{CID}.json"
IMAGE = f"edge-captures/images/{CID}.jpg"


def test_reintento_identico_responde_duplicate_y_no_escribe(s3_client, s3):
    image = make_jpeg()
    event = valid_event(image)
    first = post(s3_client, event, image)
    stored_before = s3.objects[RECORD]

    second = post(s3_client, event, image)
    assert (first.status_code, second.status_code) == (201, 200)
    assert second.json()["status"] == "duplicate"
    assert second.json()["received_at"] == first.json()["received_at"]
    assert s3.keys() == [RECORD, IMAGE], "un solo registro y una sola imagen"
    assert s3.objects[RECORD] is stored_before, "el registro original no se reescribe"


def test_mismo_id_con_otra_confianza_responde_409_y_no_sobrescribe(s3_client, s3):
    image = make_jpeg()
    post(s3_client, valid_event(image), image)
    stored_before = s3.objects[RECORD].body

    answer = post(s3_client, valid_event(image, confidence=0.5), image)
    assert answer.status_code == 409
    body = answer.json()
    assert body["error"] == "conflicto_capture_id"
    assert body["detalles"] == [{"campo": "confidence", "guardado": 0.9309, "recibido": 0.5}]
    assert s3.objects[RECORD].body == stored_before


def test_mismo_id_con_otra_imagen_responde_409(s3_client, s3):
    image = make_jpeg()
    post(s3_client, valid_event(image), image)
    other = make_jpeg(color=(0, 0, 255))

    answer = post(s3_client, valid_event(other), other)
    assert answer.status_code == 409
    [detail] = answer.json()["detalles"]
    assert detail["campo"] == "image_sha256"
    assert s3.objects[IMAGE].body == image, "la foto original no se toca"


def test_varios_campos_distintos_se_listan_todos(s3_client):
    image = make_jpeg()
    post(s3_client, valid_event(image), image)
    answer = post(s3_client, valid_event(image, predicted_class="cat", device_id="edge02"), image)
    assert answer.status_code == 409
    assert {d["campo"] for d in answer.json()["detalles"]} == {"predicted_class", "device_id"}


def test_otro_id_si_crea_otro_registro(s3_client, s3):
    image = make_jpeg()
    post(s3_client, valid_event(image), image)
    assert post(s3_client, valid_event(image, capture_id="edge01-otra"), image).status_code == 201
    assert len(s3.keys("edge-captures/events/")) == 2


def test_reintento_horas_despues_sigue_siendo_duplicate():
    """received_at cambia entre intentos, pero solo cuentan los campos del dispositivo."""
    s3 = FakeS3()
    now = {"t": datetime(2026, 10, 8, 23, 0, tzinfo=UTC)}
    store = S3CaptureStore(s3, "b", PREFIX, clock=lambda: now["t"])
    data = make_jpeg()
    image = inspect_image(data, 1_000_000)
    event = CaptureEvent.model_validate(valid_event(data))

    assert store.save(event, image).status == "created"
    now["t"] += timedelta(hours=5)
    again = store.save(event, image)
    assert again.status == "duplicate"
    assert again.record["received_at"] == "2026-10-08T23:00:00.000+00:00"


@pytest.mark.parametrize("winner_conf", [0.9309, 0.5])
def test_carrera_entre_dos_envios_del_mismo_id(winner_conf):
    """Otro envio escribe el registro entre nuestra imagen y nuestro registro (412 de S3)."""
    s3 = FakeS3()
    store = S3CaptureStore(s3, "b", PREFIX)
    data = make_jpeg()
    image = inspect_image(data, 1_000_000)
    event = CaptureEvent.model_validate(valid_event(data))
    winner = dict(event.model_dump(mode="json"), confidence=winner_conf)

    original = s3.put_object

    def racing(**kwargs):
        if kwargs["Key"].endswith(".json") and kwargs["Key"] not in s3.objects:
            original(Bucket="b", Key=kwargs["Key"], Body=json.dumps(winner).encode())
        return original(**kwargs)

    s3.put_object = racing  # type: ignore[method-assign]
    if winner_conf == event.confidence:
        assert store.save(event, image).status == "duplicate"
    else:
        with pytest.raises(Exception) as caught:
            store.save(event, image)
        assert getattr(caught.value, "status", None) == 409
    assert len(s3.keys("edge-captures/events/")) == 1
