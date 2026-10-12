"""Bloque 2 de F4 (validacion): reglas del evento y avisos de tiempo (`docs/contratos.md`)."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta

import pytest

from conftest import MODEL_SHA, make_jpeg, post, valid_event
from p4.captures.event import CaptureEvent
from p4.captures.validation import FUTURE_WARNING, assess_timing


def _rejected(client, store, event, image):
    answer = post(client, event, image)
    assert answer.status_code == 422, answer.text
    body = answer.json()
    assert body["error"] == "evento_invalido"
    assert store.saved == [], "un evento invalido nunca llega al almacen"
    return body


# --- las tres reglas que pide la guia de F4 ----------------------------------


@pytest.mark.parametrize("sin_zona", ["2026-10-09T15:30:12", "2026-10-09 15:30:12", "2026-10-09"])
def test_fecha_sin_zona_horaria_se_rechaza(client, store, sin_zona):
    image = make_jpeg()
    body = _rejected(client, store, valid_event(image, captured_at=sin_zona), image)
    assert body["mensaje"] == "captured_at debe incluir zona horaria (ej. -06:00)"


@pytest.mark.parametrize("con_zona", ["2026-10-09T15:30:12Z", "2026-10-09T21:30:12+00:00"])
def test_fecha_con_zona_horaria_se_acepta(client, store, con_zona):
    image = make_jpeg()
    assert post(client, valid_event(image, captured_at=con_zona), image).status_code == 201


def test_fecha_que_no_es_iso_se_rechaza(client, store):
    image = make_jpeg()
    body = _rejected(client, store, valid_event(image, captured_at="ayer a las 3"), image)
    assert body["detalles"][0]["campo"] == "captured_at"
    assert "ISO 8601" in body["mensaje"]


@pytest.mark.parametrize("fuera", [1.2, -0.01, 2])
def test_confianza_fuera_de_rango_se_rechaza(client, store, fuera):
    image = make_jpeg()
    body = _rejected(client, store, valid_event(image, confidence=fuera), image)
    assert body["mensaje"] == f"confidence debe estar entre 0 y 1; llegó {float(fuera)}"


def test_confianza_nan_se_rechaza(client, store):
    image = make_jpeg()
    event = valid_event(image)
    text = json.dumps(event).replace('"confidence": 0.9309', '"confidence": NaN')
    answer = post(client, text, image)
    assert answer.status_code == 422
    assert answer.json()["detalles"][0]["campo"] == "confidence"
    assert store.saved == []


@pytest.mark.parametrize("borde", [0, 1, 0.0, 1.0])
def test_confianza_en_los_bordes_se_acepta(client, borde):
    image = make_jpeg()
    assert post(client, valid_event(image, confidence=borde), image).status_code == 201


def test_sin_version_del_artefacto_se_rechaza(client, store):
    image = make_jpeg()
    event = valid_event(image)
    del event["model_version"]
    body = _rejected(client, store, event, image)
    assert body["mensaje"] == "model_version es obligatorio"


def test_version_vacia_se_rechaza(client, store):
    image = make_jpeg()
    body = _rejected(client, store, valid_event(image, model_version="  "), image)
    assert body["mensaje"] == "model_version es obligatorio"


# --- el resto del contrato ---------------------------------------------------


def test_version_no_aceptada_se_rechaza(client, store):
    image = make_jpeg()
    body = _rejected(client, store, valid_event(image, model_version="1.0.0"), image)
    assert body["mensaje"] == "model_version 1.0.0 no es una versión aceptada (1.0.0-int8.1)"


def test_sha_del_modelo_que_no_corresponde_se_rechaza(client, store):
    image = make_jpeg()
    body = _rejected(client, store, valid_event(image, model_sha256="0" * 64), image)
    assert body["mensaje"] == "model_sha256 no corresponde a 1.0.0-int8.1"


def test_sha_del_modelo_mal_formado_se_rechaza(client, store):
    image = make_jpeg()
    body = _rejected(client, store, valid_event(image, model_sha256=MODEL_SHA.upper()), image)
    assert body["detalles"][0]["campo"] == "model_sha256"


def test_clase_fuera_del_modelo_se_rechaza(client, store):
    image = make_jpeg()
    body = _rejected(client, store, valid_event(image, predicted_class="bird"), image)
    assert body["mensaje"] == "predicted_class debe ser cat, dog o person"


@pytest.mark.parametrize("clase", ["cat", "dog", "person"])
def test_las_tres_clases_se_aceptan(client, clase):
    image = make_jpeg()
    assert post(client, valid_event(image, predicted_class=clase), image).status_code == 201


def test_hash_de_imagen_distinto_se_rechaza(client, store):
    image = make_jpeg()
    otra = hashlib.sha256(make_jpeg(color=(0, 0, 0))).hexdigest()
    body = _rejected(client, store, valid_event(image, image_sha256=otra), image)
    assert body["mensaje"] == "image_sha256 no coincide con la imagen recibida"


@pytest.mark.parametrize(
    "capture_id", ["con/barra", "con espacio", "-empieza-con-guion", "x" * 129]
)
def test_capture_id_invalido_se_rechaza(client, store, capture_id):
    image = make_jpeg()
    body = _rejected(client, store, valid_event(image, capture_id=capture_id), image)
    assert body["detalles"][0]["campo"] == "capture_id"


def test_device_id_invalido_se_rechaza(client, store):
    image = make_jpeg()
    body = _rejected(client, store, valid_event(image, device_id="edge 01"), image)
    assert body["detalles"][0]["campo"] == "device_id"


def test_region_dentro_de_la_imagen_se_acepta(client, store):
    image = make_jpeg(64, 48)
    region = {"x": 10, "y": 8, "width": 54, "height": 40}
    assert post(client, valid_event(image, region=region), image).status_code == 201
    assert store.saved[0][0].region.width == 54


def test_region_fuera_de_la_imagen_se_rechaza(client, store):
    image = make_jpeg(64, 48)
    region = {"x": 10, "y": 8, "width": 60, "height": 40}
    body = _rejected(client, store, valid_event(image, region=region), image)
    assert body["detalles"][0]["campo"] == "region"
    assert "64x48" in body["mensaje"]


def test_region_con_tamano_cero_se_rechaza(client, store):
    image = make_jpeg()
    region = {"x": 0, "y": 0, "width": 0, "height": 10}
    _rejected(client, store, valid_event(image, region=region), image)


def test_se_reportan_todos_los_problemas_juntos(client, store):
    image = make_jpeg()
    event = valid_event(
        image, captured_at="2026-10-09T15:30:12", confidence=1.5, predicted_class="bird"
    )
    body = _rejected(client, store, event, image)
    assert [d["campo"] for d in body["detalles"]] == [
        "captured_at",
        "predicted_class",
        "confidence",
    ]


# --- avisos de tiempo: senalar sin rechazar ----------------------------------

RECEIVED = datetime(2026, 10, 8, 22, 0, 0, tzinfo=UTC)


def _event_at(captured_at: str) -> CaptureEvent:
    return CaptureEvent.model_validate(valid_event(make_jpeg(), captured_at=captured_at))


def test_captura_tardia_no_genera_aviso():
    # Capturada 3 dias antes, sin red: es normal y no se senala.
    delay, warnings = assess_timing(_event_at("2026-10-05T16:00:00-06:00"), RECEIVED)
    assert warnings == []
    assert delay == timedelta(days=3).total_seconds()


def test_reloj_adelantado_mas_de_5_minutos_genera_aviso():
    delay, warnings = assess_timing(_event_at("2026-10-08T16:06:00-06:00"), RECEIVED)
    assert warnings == [FUTURE_WARNING]
    assert delay == -360.0


def test_reloj_adelantado_hasta_5_minutos_no_genera_aviso():
    _, warnings = assess_timing(_event_at("2026-10-08T16:05:00-06:00"), RECEIVED)
    assert warnings == []
