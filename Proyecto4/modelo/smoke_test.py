"""Prueba de humo F2: entradas conocidas con el original del P3 y con la variante.

Por cada recorte conocido de VALIDACION (nunca test) compara:

- `original`: model.pt del P3 con su propio preprocesamiento (torchvision).
- `fp32`: ONNX FP32 con el preprocesamiento del edge (`modelo/preprocess.py`).
- `int8`: la variante optimizada con el preprocesamiento del edge.

Pasa si las tres dan la clase esperada y la variante INT8 coincide en clase con
el original. Escribe `modelo/registros/smoke_test.json`.

Uso (desde Proyecto4/): .venv/Scripts/python modelo/smoke_test.py
"""

from __future__ import annotations

import hashlib
import json
import platform
import sys
from pathlib import Path

import numpy as np
import onnxruntime as ort
import torch
import yaml
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "modelo"))
sys.path.insert(0, str(ROOT.parent / "Proyecto3" / "src"))

from p3.data.transforms import build_eval_transform  # noqa: E402
from p3.model.build import load_checkpoint  # noqa: E402
from preprocess import preprocess, softmax  # noqa: E402

# a1330 es la entrada conocida que el P3 publico (dog 0.943828); las otras dos
# completan una por clase: el primer crop_id de validacion de cat y de person.
KNOWN = ["0.1.3:a1330", "0.1.3:a1528", "0.1.3:a1022"]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    cfg = yaml.safe_load((ROOT / "modelo/conversion.yaml").read_text(encoding="utf-8"))
    log = json.loads((ROOT / "modelo/registros/conversion_log.json").read_text(encoding="utf-8"))
    artifacts = ROOT / "artifacts" / cfg["variant"]["version"]
    cal = cfg["calibration"]
    crops_dir = (ROOT / cal["crops_dir"]).resolve()
    manifest = {r["crop_id"]: r for r in map(json.loads, (ROOT / cal["manifest"]).open(encoding="utf-8"))}
    paths = {r["crop_id"]: r["crop_path"] for r in map(json.loads, (crops_dir / "crops.jsonl").open(encoding="utf-8"))}

    checkpoint = (ROOT / cfg["source"]["local_checkpoint"]).resolve()
    assert sha256(checkpoint) == cfg["source"]["sha256"], "checkpoint del P3 alterado"
    model, meta = load_checkpoint(checkpoint)
    torch_transform = build_eval_transform(meta["preprocessing"]["image_size"])

    sessions = {}
    for name in ("fp32", "int8"):
        path = artifacts / log["outputs"][name]["file"]
        assert sha256(path) == log["outputs"][name]["sha256"], f"{path} no coincide con el registro"
        sessions[name] = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])

    classes = meta["class_names"]
    results, ok = [], True
    for crop_id in KNOWN:
        row = manifest[crop_id]
        assert row["split"] == "val", f"{crop_id} no es de validacion"
        image = Image.open(crops_dir / paths[crop_id]).convert("RGB")
        with torch.no_grad():
            p_orig = torch.softmax(model(torch_transform(image).unsqueeze(0)), 1)[0].numpy()
        x = preprocess(image)
        probs = {"original": p_orig}
        for name, session in sessions.items():
            probs[name] = softmax(session.run(None, {session.get_inputs()[0].name: x})[0])[0]
        pred = {k: classes[int(np.argmax(v))] for k, v in probs.items()}
        passed = all(c == row["category_name"] for c in pred.values())
        ok &= passed
        results.append(
            {
                "crop_id": crop_id,
                "split": row["split"],
                "expected": row["category_name"],
                "predicted": pred,
                "probabilities": {k: {c: round(float(p), 6) for c, p in zip(classes, v)} for k, v in probs.items()},
                "int8_vs_original_max_abs_prob_diff": round(float(np.abs(probs["int8"] - p_orig).max()), 6),
                "passed": passed,
            }
        )
        print(f"{crop_id} esperado={row['category_name']} {pred} {'OK' if passed else 'FALLA'}")

    report = {
        "variant_version": cfg["variant"]["version"],
        "int8_sha256": log["outputs"]["int8"]["sha256"],
        "source_sha256": cfg["source"]["sha256"],
        "machine": platform.machine(),
        "onnxruntime": ort.__version__,
        "results": results,
        "passed": ok,
    }
    out = ROOT / "modelo/registros/smoke_test.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
