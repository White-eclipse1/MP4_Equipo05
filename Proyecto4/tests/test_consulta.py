"""Bloque 6 de F4 (consulta y exportacion): listado ordenado, un registro, imagen y CSV/JSON."""

from __future__ import annotations

import csv
import io
import json

import pytest

from conftest import make_jpeg, post, valid_event
from fake_s3 import client_error

# Mismo instante expresado con offsets distintos: el orden es por UTC, no por texto.
#   a: 10:00-06:00 = 16:00Z    b: 15:00Z    c: 00:00+02:00 del 9 = 22:00Z del 8
CAPTURES = {
    "edge01-a": "2026-10-08T10:00:00-06:00",
    "edge01-b": "2026-10-08T15:00:00Z",
    "edge01-c": "2026-10-09T00:00:00+02:00",
}


def _send_all(client, captures=CAPTURES):
    for capture_id, captured_at in captures.items():
        image = make_jpeg()
        event = valid_event(image, capture_id=capture_id, captured_at=captured_at)
        assert post(client, event, image).status_code == 201


def test_listado_de_mas_reciente_a_mas_antigua_por_utc(s3_client):
    _send_all(s3_client)
    body = s3_client.get("/api/p4/captures").json()
    assert [item["capture_id"] for item in body["items"]] == ["edge01-c", "edge01-a", "edge01-b"]
    assert body["total"] == 3
    assert body["errores"] == []


def test_listado_trae_los_campos_del_contrato_y_del_receptor(s3_client):
    _send_all(s3_client, {"edge01-a": CAPTURES["edge01-a"]})
    [item] = s3_client.get("/api/p4/captures").json()["items"]
    for name in ("predicted_class", "confidence", "device_id", "model_version", "image_key"):
        assert name in item
    assert item["received_at"].endswith("+00:00")


def test_empate_en_captured_at_desempata_por_capture_id(s3_client):
    _send_all(s3_client, {"edge01-x": "2026-10-08T15:00:00Z", "edge01-y": "2026-10-08T15:00:00Z"})
    items = s3_client.get("/api/p4/captures").json()["items"]
    assert [item["capture_id"] for item in items] == ["edge01-y", "edge01-x"]


def test_limit_recorta_pero_total_cuenta_todo(s3_client):
    _send_all(s3_client)
    body = s3_client.get("/api/p4/captures?limit=2").json()
    assert [item["capture_id"] for item in body["items"]] == ["edge01-c", "edge01-a"]
    assert body["total"] == 3


def test_listado_vacio(s3_client):
    assert s3_client.get("/api/p4/captures").json() == {"items": [], "total": 0, "errores": []}


def test_captura_nueva_aparece_en_el_siguiente_listado(s3_client):
    _send_all(s3_client, {"edge01-a": CAPTURES["edge01-a"]})
    assert s3_client.get("/api/p4/captures").json()["total"] == 1
    _send_all(s3_client, {"edge01-b": CAPTURES["edge01-b"]})
    assert s3_client.get("/api/p4/captures").json()["total"] == 2


def test_cache_evita_releer_s3_en_consultas_seguidas(s3_client, s3):
    _send_all(s3_client)
    s3_client.get("/api/p4/captures")
    before = len(s3.calls)
    s3_client.get("/api/p4/captures")
    s3_client.get("/api/p4/captures/export?format=csv")
    assert len(s3.calls) == before


def test_paginacion_de_s3(s3_client, s3):
    s3.page_size = 2
    _send_all(s3_client)
    assert s3_client.get("/api/p4/captures").json()["total"] == 3
    assert sum(1 for call in s3.calls if call[0] == "list_objects_v2") == 2


def test_registro_ilegible_se_reporta_no_se_esconde(s3_client, s3):
    _send_all(s3_client, {"edge01-a": CAPTURES["edge01-a"]})
    s3.put_object(Bucket="b", Key="edge-captures/events/roto.json", Body=b"{no es json")
    body = s3_client.get("/api/p4/captures").json()
    assert [item["capture_id"] for item in body["items"]] == ["edge01-a"]
    assert body["errores"][0]["record_key"] == "edge-captures/events/roto.json"
    assert "JSON invalido" in body["errores"][0]["problema"]


def test_s3_caido_en_el_listado_responde_503(s3_client, s3):
    s3.fail_next["list_objects_v2"] = client_error("AccessDenied", 403, "ListObjectsV2")
    answer = s3_client.get("/api/p4/captures")
    assert answer.status_code == 503
    assert answer.json()["error"] == "almacenamiento_no_disponible"
    assert "AccessDenied" in answer.json()["mensaje"]


# --- un registro y su imagen -------------------------------------------------


def test_un_registro_por_id(s3_client):
    _send_all(s3_client, {"edge01-a": CAPTURES["edge01-a"]})
    answer = s3_client.get("/api/p4/captures/edge01-a")
    assert answer.status_code == 200
    assert answer.json()["captured_at"] == CAPTURES["edge01-a"]


def test_registro_inexistente_404(s3_client):
    answer = s3_client.get("/api/p4/captures/no-existe")
    assert answer.status_code == 404
    assert answer.json()["error"] == "captura_no_encontrada"


def test_id_con_formato_invalido_no_llega_a_s3(s3_client, s3):
    assert s3_client.get("/api/p4/captures/-malo").status_code == 422
    assert s3.calls == []


def test_imagen_por_id_sale_de_s3_byte_por_byte(s3_client):
    image = make_jpeg(color=(10, 200, 10))
    post(s3_client, valid_event(image, capture_id="edge01-img"), image)
    answer = s3_client.get("/api/p4/captures/edge01-img/image")
    assert answer.status_code == 200
    assert answer.headers["content-type"] == "image/jpeg"
    assert answer.content == image


def test_imagen_inexistente_404(s3_client):
    assert s3_client.get("/api/p4/captures/no-existe/image").status_code == 404


# --- exportacion ---------------------------------------------------------------


def test_exportacion_json(s3_client):
    _send_all(s3_client)
    answer = s3_client.get("/api/p4/captures/export?format=json")
    assert answer.status_code == 200
    assert answer.headers["content-disposition"].startswith('attachment; filename="edge-captures-')
    body = json.loads(answer.content)
    assert body["total"] == 3
    assert [item["capture_id"] for item in body["items"]] == ["edge01-c", "edge01-a", "edge01-b"]
    assert body["errores"] == []


def test_exportacion_csv_con_todas_las_columnas(s3_client):
    image = make_jpeg(64, 48)
    region = {"x": 1, "y": 2, "width": 30, "height": 20}
    event = valid_event(image, confidence=0.8859987854957581, region=region)
    post(s3_client, event, image)
    answer = s3_client.get("/api/p4/captures/export?format=csv")
    assert answer.headers["content-type"].startswith("text/csv")
    assert answer.headers["x-capturas-con-error"] == "0"
    [row] = list(csv.DictReader(io.StringIO(answer.text)))
    assert row["confidence"] == "0.8859987854957581", "sin redondear"
    assert (row["region_x"], row["region_y"], row["region_width"], row["region_height"]) == (
        "1",
        "2",
        "30",
        "20",
    )
    assert row["captured_at"] == event["captured_at"]
    assert row["image_key"].endswith(".jpg")
    assert set(row) >= {"model_version", "model_sha256", "image_sha256", "received_at"}


def test_exportacion_csv_sin_region_deja_columnas_vacias(s3_client):
    _send_all(s3_client, {"edge01-a": CAPTURES["edge01-a"]})
    [row] = list(
        csv.DictReader(io.StringIO(s3_client.get("/api/p4/captures/export?format=csv").text))
    )
    assert row["region_x"] == ""


@pytest.mark.parametrize("formato", ["xml", ""])
def test_formato_no_soportado_422(s3_client, formato):
    assert s3_client.get(f"/api/p4/captures/export?format={formato}").status_code == 422
