"""Comparacion original vs INT8 por muestra (VAL-02, #2): `validacion/comparar_modelos.py`.

Las pruebas usan un manifiesto y recortes sinteticos y predictores falsos: la logica de
muestras, IDs, etiquetas y calibracion se prueba sin torch, onnxruntime ni pesos.
"""

from __future__ import annotations

import csv
import importlib.util
import io
import json
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "validacion" / "comparar_modelos.py"
_spec = importlib.util.spec_from_file_location("comparar_modelos", SCRIPT)
comp = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = comp
_spec.loader.exec_module(comp)

CLASES = ["cat", "dog", "person"]


def fila(cid: str, clase: str, split: str) -> dict:
    return {
        "crop_id": cid,
        "category_name": clase,
        "class_index": CLASES.index(clase),
        "split": split,
    }


MANIFIESTO = [
    fila("0.1.3:a1", "cat", "train"),
    fila("0.1.3:a2", "dog", "val"),
    fila("0.1.3:a3", "person", "test"),
    fila("0.1.3:a4", "cat", "val"),
    fila("0.1.3:a5", "person", "val"),
    fila("0.1.3:a6", "dog", "train"),
]


@pytest.fixture
def recortes(tmp_path: Path) -> Path:
    lineas = []
    for f in MANIFIESTO:
        ruta = f"{f['category_name']}/{f['crop_id'].replace(':', '_')}.png"
        (tmp_path / ruta).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / ruta).write_bytes(b"png falso")
        lineas.append(json.dumps({"crop_id": f["crop_id"], "crop_path": ruta}))
    (tmp_path / "crops.jsonl").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    return tmp_path


def predictor_fijo(clase: str):
    return lambda _ruta: [0.9 if c == clase else 0.05 for c in CLASES]


def predictor_correcto(muestras):
    clase_de = {m["ruta"]: m["true_class"] for m in muestras}
    return lambda ruta: [0.8 if c == clase_de[ruta] else 0.1 for c in CLASES]


def test_solo_val_en_el_orden_del_manifiesto(recortes):
    muestras, faltantes = comp.muestras_val(MANIFIESTO, recortes, CLASES)
    assert [m["sample_id"] for m in muestras] == ["0.1.3:a2", "0.1.3:a4", "0.1.3:a5"]
    assert [m["true_class"] for m in muestras] == ["dog", "cat", "person"]
    assert faltantes == []


def test_csv_con_los_mismos_ids_y_etiquetas_que_val(recortes):
    muestras, faltantes = comp.muestras_val(MANIFIESTO, recortes, CLASES)
    correcto = predictor_correcto(muestras)
    predictores = {
        "original": correcto,
        "fp32": correcto,
        "int8": predictor_fijo("person"),
        "int8_referencia": correcto,
    }
    filas = comp.comparar(muestras, predictores, CLASES)
    datos = comp.csv_bytes(filas, CLASES)

    verificacion = comp.verificar_csv(datos, muestras, faltantes)
    assert verificacion["ok"]
    assert verificacion["mismo_orden_que_manifiesto"]

    leidas = list(csv.DictReader(io.StringIO(datos.decode("utf-8"))))
    for col in ("sample_id", "true_class", "original_prediction", "optimized_prediction"):
        assert col in leidas[0]
    assert [f["optimized_prediction"] for f in leidas] == ["person"] * 3
    assert [f["original_prediction"] for f in leidas] == ["dog", "cat", "person"]
    # Probabilidades exactas: se recalculan desde el CSV sin perder precision.
    assert float(leidas[0]["prob_int8_person"]) == 0.9

    r = comp.resumen(filas, CLASES)
    assert r["aciertos"] == {"original": 3, "fp32": 3, "int8": 1, "int8_referencia": 3}
    assert r["acuerdo_int8_vs_original"] == 1
    assert r["acuerdo_int8_vs_int8_referencia"] == 1
    assert [f["int8_referencia_prediction"] for f in leidas] == ["dog", "cat", "person"]
    assert r["clases_presentes"]


def test_detecta_id_duplicado(recortes):
    muestras, faltantes = comp.muestras_val(MANIFIESTO, recortes, CLASES)
    p = predictor_fijo("cat")
    filas = comp.comparar(muestras, dict.fromkeys(comp.MODELOS, p), CLASES)
    datos = comp.csv_bytes([*filas, filas[0]], CLASES)
    verificacion = comp.verificar_csv(datos, muestras, faltantes)
    assert verificacion["duplicados"] == ["0.1.3:a2"]
    assert not verificacion["ok"]


def test_muestra_sin_imagen_queda_como_faltante_y_falla(recortes):
    (recortes / "cat" / "0.1.3_a4.png").unlink()
    muestras, faltantes = comp.muestras_val(MANIFIESTO, recortes, CLASES)
    assert faltantes == [{"sample_id": "0.1.3:a4", "motivo": "no existe cat/0.1.3_a4.png"}]
    p = predictor_fijo("cat")
    datos = comp.csv_bytes(comp.comparar(muestras, dict.fromkeys(comp.MODELOS, p), CLASES), CLASES)
    assert not comp.verificar_csv(datos, muestras, faltantes)["ok"]


def test_rechaza_class_index_que_no_coincide(recortes):
    malo = [*MANIFIESTO, {**fila("0.1.3:a7", "dog", "val"), "class_index": 0}]
    with pytest.raises(comp.ComparacionError, match="class_index"):
        comp.muestras_val(malo, recortes, CLASES)


def test_calibracion_solo_train_segun_el_manifiesto():
    buena = [{"crop_id": "0.1.3:a1"}, {"crop_id": "0.1.3:a6"}]
    assert comp.comprobar_calibracion(MANIFIESTO, buena)["solo_train"]

    mala = [*buena, {"crop_id": "0.1.3:a3"}, {"crop_id": "0.1.3:a99"}]
    resultado = comp.comprobar_calibracion(MANIFIESTO, mala)
    assert not resultado["solo_train"]
    assert resultado["fuera_de_train"] == ["0.1.3:a3", "0.1.3:a99"]
    assert resultado["por_split_segun_manifiesto"] == {"ausente": 1, "test": 1, "train": 2}


def test_exige_sha256(tmp_path):
    ruta = tmp_path / "manifest.jsonl"
    ruta.write_text("{}\n", encoding="utf-8")
    with pytest.raises(comp.ComparacionError, match="SHA-256"):
        comp.exigir_sha(ruta, "0" * 64, "manifiesto")
    with pytest.raises(comp.ComparacionError, match="No existe"):
        comp.exigir_sha(tmp_path / "otro.jsonl", "0" * 64, "manifiesto")


def test_configuracion_toma_los_hashes_de_la_conversion_verificada():
    cfg = comp.configuracion()
    assert cfg["variante"] == "1.0.0-int8-e05.1"
    assert cfg["manifiesto"]["sha256"].startswith("45600f29")
    assert cfg["crops_jsonl_sha256"].startswith("d3d61f35")
    assert cfg["modelos"]["original"]["sha256"].startswith("e4acca42")
    assert cfg["modelos"]["int8"]["sha256"].startswith("ba89ee43")
    assert cfg["modelos"]["int8"]["s3"].endswith("1.0.0-int8-e05.1/model_int8.onnx")


def test_detecta_png_con_dimensiones_distintas_a_crops_jsonl(tmp_path):
    from PIL import Image

    bien, mal = tmp_path / "bien.png", tmp_path / "mal.png"
    Image.new("RGB", (30, 20)).save(bien)
    Image.new("RGB", (20, 30)).save(mal)
    muestras = [
        {"sample_id": "0.1.3:a1", "ruta": bien, "tamano": (30, 20)},
        {"sample_id": "0.1.3:a2", "ruta": mal, "tamano": (30, 20)},
    ]
    assert comp.dimensiones_distintas(muestras) == [
        {"sample_id": "0.1.3:a2", "esperado": (30, 20), "png": (20, 30)}
    ]
