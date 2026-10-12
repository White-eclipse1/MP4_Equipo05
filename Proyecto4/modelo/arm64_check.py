"""Carga de la variante en ARM64 (F2, antes de tener la Raspberry Pi lista).

Corre dentro de un contenedor linux/arm64 (emulado con QEMU en la laptop) o
directamente en la Raspberry Pi. Solo usa onnxruntime, numpy y Pillow, como el
dispositivo. Imprime arquitectura, versiones, SHA-256 del artefacto, los
operadores que onnxruntime ejecuta tras optimizar el grafo (efecto de la
cuantizacion en el runtime) y la clase de las entradas conocidas.

En la laptop (desde la raiz del repo), ver docs/artefacto.md:
    docker run --rm --platform linux/arm64 -v <Proyecto4>:/p4:ro -v <crops 0.1.3>:/crops:ro \
        python:3.11-slim-bookworm sh -c "pip install -r /p4/modelo/requirements-edge.txt && \
        python /p4/modelo/arm64_check.py --model /p4/artifacts/1.0.0-int8.1/model_int8.onnx --crops /crops"
En la Pi:
    python modelo/arm64_check.py --model artifacts/1.0.0-int8.1/model_int8.onnx --crops <carpeta de recortes>
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import platform
import sys
import tempfile
from pathlib import Path

import numpy as np
import onnx
import onnxruntime as ort
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from preprocess import preprocess, softmax  # noqa: E402

CLASSES = ["cat", "dog", "person"]
KNOWN = ["dog/0.1.3_a1330.png", "cat/0.1.3_a1528.png", "person/0.1.3_a1022.png"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--crops", required=True, help="carpeta Proyecto3/data/crops/0.1.3")
    args = parser.parse_args()

    model = Path(args.model)
    print(f"machine={platform.machine()} python={platform.python_version()} "
          f"onnxruntime={ort.__version__} numpy={np.__version__}")
    print(f"model={model.name} bytes={model.stat().st_size} sha256={hashlib.sha256(model.read_bytes()).hexdigest()}")

    with tempfile.TemporaryDirectory() as tmp:
        options = ort.SessionOptions()
        options.optimized_model_filepath = str(Path(tmp) / "optimized.onnx")
        session = ort.InferenceSession(str(model), options, providers=["CPUExecutionProvider"])
        ops = collections.Counter(n.op_type for n in onnx.load(options.optimized_model_filepath).graph.node)
    print("runtime_ops=" + ", ".join(f"{k}:{v}" for k, v in sorted(ops.items())))

    name = session.get_inputs()[0].name
    for crop in KNOWN:
        probs = softmax(session.run(None, {name: preprocess(Image.open(Path(args.crops) / crop))})[0])[0]
        print(f"{crop} -> {CLASSES[int(probs.argmax())]} {[round(float(p), 6) for p in probs]}")


if __name__ == "__main__":
    main()
