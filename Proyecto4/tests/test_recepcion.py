"""Bloque 1 de F4 (recepcion): token, partes del multipart, imagen y forma del evento."""

from __future__ import annotations

import io
import json

from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

from conftest import TOKEN, make_jpeg, post, valid_event
from p4.captures import api
from p4.captures.settings import CaptureSettings


def test_captura_valida_se_recibe_y_llega_al_almacen(client, store):
    image = make_jpeg()
    answer = post(client, valid_event(image), image)
    assert answer.status_code == 201, answer.text
    assert answer.json()["status"] == "created"
    assert answer.json()["capture_id"] == "edge01-20261009T153012-0007"
    [(event, received)] = store.saved
    assert event.predicted_class == "dog"
    assert received.data == image
    assert (received.width, received.height) == (64, 48)


def test_evento_como_parte_de_archivo_tambien_se_acepta(client, store):
    image = make_jpeg()
    answer = client.post(
        "/api/p4/captures",
        headers={"Authorization": f"Bearer {TOKEN}"},
        files={
            "event": ("event.json", json.dumps(valid_event(image)), "application/json"),
            "image": ("captura.jpg", image, "image/jpeg"),
        },
    )
    assert answer.status_code == 201, answer.text
    assert len(store.saved) == 1


def test_sin_token_401(client, store):
    image = make_jpeg()
    answer = post(client, valid_event(image), image, token=None)
    assert answer.status_code == 401
    assert answer.json()["error"] == "no_autorizado"
    assert store.saved == []


def test_token_incorrecto_401(client, store):
    image = make_jpeg()
    answer = post(client, valid_event(image), image, token="otro")
    assert answer.status_code == 401
    assert store.saved == []


def test_receptor_sin_token_configurado_503(store):
    app = FastAPI()
    app.include_router(api.router)
    app.dependency_overrides[api.get_settings] = lambda: CaptureSettings(P4_DEVICE_TOKEN="")
    app.dependency_overrides[api.get_store] = lambda: store
    image = make_jpeg()
    answer = post(TestClient(app), valid_event(image), image)
    assert answer.status_code == 503
    assert answer.json()["error"] == "receptor_no_configurado"


def test_receptor_sin_bucket_503():
    # Sin bucket no se construye cliente de S3: ninguna prueba toca AWS.
    settings = CaptureSettings(P4_DEVICE_TOKEN=TOKEN, P4_CAPTURES_BUCKET="")
    app = FastAPI()
    app.include_router(api.router)
    app.dependency_overrides[api.get_settings] = lambda: settings
    image = make_jpeg()
    answer = post(TestClient(app), valid_event(image), image)
    assert answer.status_code == 503
    assert "mismo capture_id" in answer.json()["mensaje"]


def test_falta_la_imagen_400(client):
    answer = post(client, valid_event(make_jpeg()), None)
    assert answer.status_code == 400
    assert answer.json()["mensaje"] == "Falta la parte 'image'"


def test_falta_el_evento_400(client):
    answer = post(client, None, make_jpeg())
    assert answer.status_code == 400
    assert answer.json()["mensaje"] == "Falta la parte 'event'"


def test_evento_que_no_es_json_400(client):
    answer = post(client, "{no es json", make_jpeg())
    assert answer.status_code == 400
    assert answer.json()["error"] == "solicitud_invalida"


def test_evento_que_no_es_objeto_400(client):
    answer = post(client, "[1, 2]", make_jpeg())
    assert answer.status_code == 400


def test_imagen_que_no_es_jpeg_415(client):
    answer = post(client, valid_event(b"x"), b"\x89PNG\r\n\x1a\n no es jpeg")
    assert answer.status_code == 415
    assert answer.json()["error"] == "imagen_no_soportada"


def test_jpeg_truncado_415(client):
    answer = post(client, valid_event(b"x"), b"\xff\xd8\xff\xe0 truncado")
    assert answer.status_code == 415


def test_imagen_demasiado_grande_413(client, settings):
    big = b"\xff\xd8\xff" + b"\0" * settings.max_image_bytes
    answer = post(client, valid_event(big), big)
    assert answer.status_code == 413
    assert answer.json()["error"] == "imagen_demasiado_grande"


def test_falta_un_campo_obligatorio_422(client, store):
    image = make_jpeg()
    event = valid_event(image)
    del event["device_id"]
    answer = post(client, event, image)
    assert answer.status_code == 422
    body = answer.json()
    assert body["error"] == "evento_invalido"
    assert {"campo": "device_id", "problema": "es obligatorio"} in body["detalles"]
    assert store.saved == []


def test_campo_desconocido_422(client):
    image = make_jpeg()
    answer = post(client, valid_event(image, clase="dog"), image)
    assert answer.status_code == 422
    assert answer.json()["detalles"][0]["campo"] == "clase"


def test_confianza_como_texto_422(client):
    image = make_jpeg()
    answer = post(client, valid_event(image, confidence="0.93"), image)
    assert answer.status_code == 422
    assert answer.json()["detalles"][0]["campo"] == "confidence"


# --- tope de la parte `event` (revision de Edith) ----------------------------


def test_evento_real_queda_muy_por_debajo_del_tope(settings):
    assert len(json.dumps(valid_event(make_jpeg())).encode()) < 1024 < settings.max_event_bytes


def test_evento_de_texto_demasiado_grande_413(client, store, settings):
    image = make_jpeg()
    event = valid_event(image, image_ref="x" * settings.max_event_bytes)
    answer = post(client, event, image)
    assert answer.status_code == 413
    body = answer.json()
    assert body["error"] == "evento_demasiado_grande"
    assert str(settings.max_event_bytes) in body["mensaje"]
    assert body["detalles"] == []
    assert store.saved == []


def test_evento_como_archivo_demasiado_grande_413(client, store, settings):
    image = make_jpeg()
    big = json.dumps(valid_event(image, image_ref="x" * settings.max_event_bytes))
    answer = client.post(
        "/api/p4/captures",
        headers={"Authorization": f"Bearer {TOKEN}"},
        files={
            "event": ("event.json", big, "application/json"),
            "image": ("captura.jpg", image, "image/jpeg"),
        },
    )
    assert answer.status_code == 413
    assert answer.json()["error"] == "evento_demasiado_grande"
    assert store.saved == []


def test_evento_justo_en_el_tope_no_es_413(client, settings):
    image = make_jpeg()
    base = json.dumps(valid_event(image, image_ref=""))
    padding = settings.max_event_bytes - len(base.encode())
    event = valid_event(image, image_ref="x" * padding)
    assert len(json.dumps(event).encode()) == settings.max_event_bytes
    # Llega entero: se valida como evento normal (aqui, aceptado).
    assert post(client, event, image).status_code == 201


def test_el_tope_no_afecta_a_la_imagen(client, settings):
    """La imagen llega como archivo: solo la limita su propio tope (200 KB en estas pruebas)."""
    buffer = io.BytesIO()
    Image.effect_noise((200, 200), 100).convert("RGB").save(buffer, format="JPEG", quality=95)
    image = buffer.getvalue()
    assert settings.max_event_bytes < len(image) < settings.max_image_bytes
    assert post(client, valid_event(image), image).status_code == 201


def test_multipart_mal_formado_400_con_formato_del_contrato(client):
    answer = client.post(
        "/api/p4/captures",
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "multipart/form-data; boundary=xyz",
        },
        # Una parte sin `name`: python-multipart la rechaza al parsear.
        content=b"--xyz\r\nContent-Disposition: form-data\r\n\r\nsin nombre\r\n--xyz--\r\n",
    )
    assert answer.status_code == 400
    assert answer.json()["error"] == "solicitud_invalida"
