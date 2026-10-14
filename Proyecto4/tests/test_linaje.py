"""Verificacion del linaje del modelo (VAL-01, M1): `modelo/verificar_linaje.py`."""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "modelo" / "verificar_linaje.py"
_spec = importlib.util.spec_from_file_location("verificar_linaje", SCRIPT)
linaje = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = linaje  # dataclasses busca el modulo ahi
_spec.loader.exec_module(linaje)

RECORD_CHECKS = {
    "origen.version",
    "origen.run_id",
    "origen.checkpoint",
    "origen.sha256_registros",
    "variante.version",
    "variante.sha256_registros",
    "clases.orden",
    "preprocesamiento",
    "conversion.referencia",
    "conversion.entrada_salida",
    "registros.publicados",
    "paquete.reconstruido",
    "calibracion.train",
    "origen.no_externo",
}


def run_records() -> tuple[dict[str, str], dict]:
    checks = linaje.Checks()
    ctx = linaje.check_records(checks)
    return {c.id: c.estado for c in checks}, ctx


def failed(states: dict[str, str]) -> set[str]:
    return {check_id for check_id, state in states.items() if state == linaje.FAIL}


def test_linaje_en_registros_completo_y_sin_fallas():
    states, ctx = run_records()
    assert set(states) == RECORD_CHECKS
    assert failed(states) == set()
    ficha = ctx["ficha"]
    assert ficha["original"]["version"] == "1.0.0"
    assert ficha["original"]["run_id"] == "9f9b62c202f0446a8a4b411a10321eff"
    assert ficha["variante"]["version"] == "1.0.0-int8.1"
    assert ficha["class_map"] == {"0": "cat", "1": "dog", "2": "person"}


def test_model_package_se_reconstruye_byte_a_byte():
    _, ctx = run_records()
    expected = ctx["log"]["package"]["sha256"]
    rebuilt = {
        nl: linaje.sha256_bytes(linaje.rebuild_model_package(ctx["cfg"], ctx["log"], nl))
        for nl in ("\n", "\r\n")
    }
    assert expected in rebuilt.values()


def tamper(monkeypatch: pytest.MonkeyPatch, name: str, change) -> None:
    original = linaje.read_json

    def read_json(path: Path):
        data = original(path)
        if path.name == name:
            data = copy.deepcopy(data)
            change(data)
        return data

    monkeypatch.setattr(linaje, "read_json", read_json)


def test_detecta_variante_con_otro_hash(monkeypatch):
    def change(log):
        log["outputs"]["int8"]["sha256"] = "0" * 64

    tamper(monkeypatch, "conversion_log.json", change)
    states, _ = run_records()
    assert "variante.sha256_registros" in failed(states)


def test_detecta_orden_de_clases_distinto(monkeypatch):
    def change(log):
        log["input"]["class_names"] = ["dog", "cat", "person"]

    tamper(monkeypatch, "conversion_log.json", change)
    states, _ = run_records()
    # Cambia el orden declarado y el paquete reconstruido deja de ser el publicado.
    assert {"clases.orden", "paquete.reconstruido"} <= failed(states)


def test_detecta_origen_distinto_al_seleccionado_en_p3(monkeypatch):
    def change(selection):
        selection["run_id"] = "otro-run"
        selection["checkpoint_sha256"] = "f" * 64

    tamper(monkeypatch, "selection.json", change)
    states, _ = run_records()
    assert {"origen.run_id", "origen.sha256_registros"} <= failed(states)


def test_detecta_preprocesamiento_distinto(monkeypatch):
    def change(log):
        log["input"]["preprocessing"]["mean"] = [0.5, 0.5, 0.5]

    tamper(monkeypatch, "conversion_log.json", change)
    states, _ = run_records()
    assert "preprocesamiento" in failed(states)


class FakeBody:
    def __init__(self, data: bytes):
        self.data = data

    def read(self) -> bytes:
        return self.data

    def iter_chunks(self, size: int):
        for start in range(0, len(self.data), size):
            yield self.data[start : start + size]


class FakeS3:
    def __init__(self, objects: dict[str, tuple[bytes, str]]):
        self.objects = objects

    def get_object(self, Bucket: str, Key: str):  # noqa: N803 (firma de boto3)
        data, version_id = self.objects[Key]
        return {"Body": FakeBody(data), "VersionId": version_id}


def test_s3_detecta_modelo_sustituido():
    """Paquete del P3 correcto pero binarios ajenos: fallan los SHA-256 de los binarios."""
    checks = linaje.Checks()
    ctx = linaje.check_records(checks)
    cfg, log, publication = ctx["cfg"], ctx["log"], ctx["publication"]
    src = cfg["source"]
    prefix = f"{linaje.P3_MODELS_PREFIX}/{src['p3_version']}"
    as_json = lambda data: json.dumps(data).encode()  # noqa: E731
    objects = {
        src["s3_key"]: (b"pesos de otro modelo", src["s3_version_id"]),
        f"{linaje.P3_MODELS_PREFIX}/registry.json": (
            as_json(
                {
                    "schema_version": 1,
                    "active_version": src["p3_version"],
                    "versions": [
                        {
                            "version": src["p3_version"],
                            "run_id": src["run_id"],
                            "manifest_id": "m-0.1.3-s42-1",
                            "key": src["s3_key"],
                            "sha256": src["sha256"],
                            "s3_version_id": src["s3_version_id"],
                        }
                    ],
                }
            ),
            "v",
        ),
        f"{prefix}/class_map.json": (
            as_json(
                {
                    "classes": [
                        {"class_index": i, "category_name": name}
                        for i, name in enumerate(linaje.EXPECTED_CLASSES)
                    ]
                }
            ),
            "v",
        ),
        f"{prefix}/preprocessing.json": (as_json(log["input"]["preprocessing"]), "v"),
        f"{prefix}/model_version.json": (
            as_json({"run_id": src["run_id"], "files": {"model.pt": {"sha256": src["sha256"]}}}),
            "v",
        ),
    }
    package = linaje.rebuild_model_package(cfg, log, "\r\n")
    for obj in publication["objects"]:
        name = obj["key"].rsplit("/", 1)[-1]
        if name == "model_package.json":
            data = package
        elif name.endswith(".onnx"):
            data = b"onnx de otro modelo"
        else:
            data = (linaje.RECORDS / name).read_bytes()
        objects[obj["key"]] = (data, obj["version_id"])

    linaje.check_s3(checks, ctx, FakeS3(objects))
    states = {c.id: c.estado for c in checks}
    assert failed(states) == {
        "s3.original",
        "s3.variante.model_int8.onnx",
        "s3.variante.model_fp32.onnx",
    }
    assert states["s3.registry_p3"] == linaje.OK
    assert states["s3.paquete_p3"] == linaje.OK
    assert states["s3.variante.model_package.json"] == linaje.OK
    assert states["s3.model_package"] == linaje.OK
