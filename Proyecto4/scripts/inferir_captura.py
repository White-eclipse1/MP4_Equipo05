"""Clasifica una foto con la variante `1.0.0-int8.1` para recalcular la prediccion de una captura.

Usa el preprocesamiento de F2 (`modelo/preprocess.py`, sin modificar) y onnxruntime.
Antes de inferir exige que el SHA-256 de `model_int8.onnx` sea el de la ficha
(`docs/artefacto.md`). Imprime JSON con los SHA-256, las probabilidades y la clase.

Ojo: en x86 las probabilidades del INT8 difieren de las de aarch64 (la Pi); ver el
aviso de `docs/artefacto.md`. Para recalcular la captura de prueba de F4, que se
clasifico en x86, usa x86.

    python scripts/inferir_captura.py --foto <foto.jpg> --modelo-dir <carpeta con model_int8.onnx>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from pathlib import Path

import numpy as np
import onnxruntime as ort
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "modelo"))
from preprocess import preprocess, softmax  # F2, sin modificar

MODEL_VERSION = "1.0.0-int8.1"
MODEL_SHA256 = "ca689c4e1478ccca7821dffaba8f07886bd9609a8aa3cec7450d9f875fbd69c0"
CLASSES = ("cat", "dog", "person")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--foto", type=Path, required=True)
    parser.add_argument("--modelo-dir", type=Path, required=True)
    args = parser.parse_args()

    model = args.modelo_dir / "model_int8.onnx"
    model_sha = hashlib.sha256(model.read_bytes()).hexdigest()
    if model_sha != MODEL_SHA256:
        sys.exit(f"{model} no es {MODEL_VERSION}: SHA-256 {model_sha}, se esperaba {MODEL_SHA256}")

    photo = args.foto.read_bytes()
    session = ort.InferenceSession(str(model), providers=["CPUExecutionProvider"])
    with Image.open(args.foto) as image:
        size = image.size
        tensor = preprocess(image)
    probs = softmax(session.run(["logits"], {"input": tensor})[0])[0]
    best = int(np.argmax(probs))
    print(
        json.dumps(
            {
                "foto": args.foto.name,
                "image_sha256": hashlib.sha256(photo).hexdigest(),
                "image_bytes": len(photo),
                "image_size": list(size),
                "model_version": MODEL_VERSION,
                "model_sha256": model_sha,
                "onnxruntime": ort.__version__,
                "machine": platform.machine(),
                "probs": {name: float(p) for name, p in zip(CLASSES, probs, strict=True)},
                "predicted_class": CLASSES[best],
                "confidence": float(probs[best]),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
