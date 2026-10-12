"""Preprocesamiento del modelo en el edge (F2; lo reutilizan F3 y F7).

Replica `build_eval_transform` del Proyecto 3 (`Proyecto3/src/p3/data/transforms.py`)
sin torch, para que el dispositivo solo necesite numpy y Pillow:

- RGB, estirado a `image_size x image_size` sin recortar bordes (bilineal con
  antialias, el mismo filtro que `v2.Resize(antialias=True)`).
- Escala a [0, 1] y normaliza con media y desviacion de ImageNet.
- Salida NCHW float32 con lote 1: la entrada `input` del ONNX.

La entrada del modelo cuantizado sigue siendo float32: la cuantizacion de la
activacion de entrada ocurre dentro del grafo (QuantizeLinear), asi que el
dispositivo no cuantiza nada a mano.
"""

from __future__ import annotations

import numpy as np
from PIL import Image

IMAGE_SIZE = 224
MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


def preprocess(image: Image.Image, image_size: int = IMAGE_SIZE) -> np.ndarray:
    """Imagen PIL (cualquier modo) -> tensor (1, 3, H, W) float32 normalizado."""
    rgb = image.convert("RGB").resize((image_size, image_size), Image.Resampling.BILINEAR)
    array = np.asarray(rgb, dtype=np.float32) / 255.0
    array = (array - MEAN) / STD
    return np.ascontiguousarray(array.transpose(2, 0, 1)[np.newaxis])


def softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - logits.max(axis=-1, keepdims=True)
    exp = np.exp(shifted)
    return exp / exp.sum(axis=-1, keepdims=True)
