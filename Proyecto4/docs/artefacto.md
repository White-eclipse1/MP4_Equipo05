# Ficha del artefacto optimizado — F2

Variante **`1.0.0-int8.1`**: el modelo publicado 1.0.0 del Proyecto 3, exportado a ONNX y cuantizado estáticamente a INT8. Es el artefacto que carga el dispositivo (F3) y el que se compara en calidad (F7) y recursos (F8).

## Origen (Proyecto 3)

| Dato | Valor |
|---|---|
| Versión publicada | `1.0.0` (activa en `registry.json` del P3) |
| Run ID de MLflow | `9f9b62c202f0446a8a4b411a10321eff` (r10, mejor época 6, `selection.json`) |
| Pesos | `s3://dataset-quality-releases-750702272375/models/clasificador/1.0.0/model.pt`, VersionId `VtRww5se97lomVTcKJUv6d9mYSL7TXOf`; copia local en `Proyecto3/mlflow_snapshot/artifacts/3/9f9b62c2…/checkpoint/model.pt` (`dvc pull mlflow_snapshot.dvc`) |
| SHA-256 | `e4acca429ebf73d0e5a60fb0dda383a6a5322dccb1decf04b4e40ab9db989172` (44 783 563 bytes); el mismo en S3, en local y en `selection.json` |
| Arquitectura | ResNet-18, cabeza `Dropout(0.5) → Linear(512, 3)` (`hidden_layers: []`, leído del checkpoint) |
| Clases (orden de salida) | 0 `cat`, 1 `dog`, 2 `person` |
| Preprocesamiento | RGB, estirado a 224×224 sin recortar bordes (bilineal con antialias), escala a [0, 1], media `[0.485, 0.456, 0.406]`, desviación `[0.229, 0.224, 0.225]` |
| Entrada conocida | `0.1.3:a1330` (val, `dog`): cat 0.051366, **dog 0.943828**, person 0.004807, igual que `Proyecto3/docs/publicacion_s3.md` |

`convert.py` carga el checkpoint con el `load_checkpoint` del propio P3 y exige su SHA-256 antes de convertir: arquitectura, clases y preprocesamiento salen del checkpoint, no se redefinen.

## Variante

| Dato | Valor |
|---|---|
| Versión | `1.0.0-int8.1` |
| Formato | ONNX, opset 18 |
| Runtime | onnxruntime 1.30.0, `CPUExecutionProvider` (aarch64 en la Pi) |
| Técnica | Cuantización estática post-entrenamiento: formato QDQ, pesos INT8 **por canal**, activaciones INT8, calibración MinMax |
| Calibración | 200 recortes **solo de train** del manifiesto `m-0.1.3-s42-1` (semilla 42: 48 cat, 54 dog, 98 person); IDs en [`calibracion_manifest.jsonl`](../modelo/registros/calibracion_manifest.jsonl). Validación y test no intervienen |
| Entrada | `input`, float32, NCHW `[1, 3, 224, 224]`, RGB normalizado; la cuantización de la entrada ocurre dentro del grafo (`QuantizeLinear`), el dispositivo no cuantiza a mano |
| Salida | `logits` `[1, 3]`; confianza = softmax |
| Preprocesamiento en el edge | [`modelo/preprocess.py`](../modelo/preprocess.py) (numpy + Pillow, sin torch). En una revisión interna sobre las 292 muestras de validación, el original da el mismo accuracy (0.9966) con este preprocesamiento que con el de torchvision; la comparación formal por muestra es de F7 |

### Archivos

| Archivo | Bytes | SHA-256 |
|---|---:|---|
| `model.pt` (original P3) | 44 783 563 | `e4acca429ebf73d0e5a60fb0dda383a6a5322dccb1decf04b4e40ab9db989172` |
| `model_fp32.onnx` (exportación intermedia, referencia para F8) | 44 791 921 | `e4dc89bbb652f6de9bea2fffa94ff59abb0e6cb679d8a4d95aeadc9e0be65328` |
| **`model_int8.onnx` (variante)** | **11 349 151** | **`ca689c4e1478ccca7821dffaba8f07886bd9609a8aa3cec7450d9f875fbd69c0`** |
| `model_package.json` | ver [`conversion_log.json`](../modelo/registros/conversion_log.json) | |

Descarga: `s3://dataset-quality-releases-750702272375/models/clasificador-edge/1.0.0-int8.1/`. Llaves, SHA-256 y VersionId de cada objeto en [`publicacion.json`](../modelo/registros/publicacion.json).

## Efecto de la técnica

- **Tamaño:** 44 783 563 → 11 349 151 bytes, **74.66 % menos** que el original (`size_reduction_pct` en el registro).
- **Artefacto:** los 20 `Conv` y el `Gemm` guardan sus pesos en 73 inicializadores `INT8` (con sesgos `INT32`); el grafo agrega 32 `QuantizeLinear` y 74 `DequantizeLinear` (`outputs.*.graph` en el registro).
- **Runtime:** en aarch64, onnxruntime funde los pares QDQ y ejecuta aritmética entera: el grafo optimizado queda con 20 `QLinearConv`, 1 `QGemm` y 8 `QLinearAdd`, y solo 2 `QuantizeLinear`/`DequantizeLinear` en los bordes. Lo imprime [`arm64_check.py`](../modelo/arm64_check.py) (salida en [`arm64_check.txt`](../modelo/registros/arm64_check.txt)).
- **Latencia:** no se reporta aquí. Se mide en la Raspberry Pi en F8, FP32 contra INT8 con el mismo runtime; la laptop no cuenta para la rúbrica (3.1).

## Validaciones de F2

| Comprobación | Resultado | Evidencia |
|---|---|---|
| SHA-256 del original igual al publicado | sí | `conversion_log.json` → `input.sha256` |
| ONNX FP32 igual a PyTorch | diferencia máxima de logits 1.2e-7 | `checks.fp32_vs_torch_max_abs_logit_diff` |
| Calibración solo con train | 200/200 de `train` | `calibration.splits_used`, `calibracion_manifest.jsonl` |
| Conversión reproducible | dos corridas dan los mismos SHA-256 de FP32 e INT8 | mismo comando, mismo resultado |
| Entradas conocidas (x86) | original, FP32 e INT8 dan la clase esperada en 3/3 | [`smoke_test.json`](../modelo/registros/smoke_test.json) |
| Carga en aarch64 (Docker con QEMU, Python 3.11, onnxruntime 1.30.0) | carga; SHA-256 coincide; 3/3 entradas conocidas con la clase esperada (`a1330` dog 0.930898); el runtime ejecuta 20 `QLinearConv`, 1 `QGemm` y 8 `QLinearAdd` | [`arm64_check.txt`](../modelo/registros/arm64_check.txt) |
| Carga en la Raspberry Pi física | **pendiente de Bryan (F3)** | — |

### Aviso para F7 y F8: medir INT8 en ARM, no en la laptop

El mismo `model_int8.onnx` da probabilidades distintas en x86 y en aarch64 (por ejemplo, `a1330`: dog 0.562 en la laptop, 0.931 en aarch64). La causa probable es la saturación conocida de onnxruntime al ejecutar INT8×INT8 con AVX2 en x86 (sin VNNI); en ARM las instrucciones enteras no saturan. En una revisión interna en aarch64 sobre las 292 muestras de validación, FP32 dio 0.9966 e INT8 0.9932 (caída de 0.34 pp; en x86 la caída aparente era de 1.37 pp). Es una cifra preliminar: no se guardaron las predicciones por muestra, y el registro recalculable lo produce F7. La comparación de calidad formal (F7) y las mediciones (F8) se hacen con el runtime de aarch64.

## Reproducir

Desde `Proyecto4/`, con Python 3.12:

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r modelo/requirements-conversion.lock.txt --extra-index-url https://download.pytorch.org/whl/cpu
.venv/Scripts/python modelo/convert.py                       # copia local del P3
.venv/Scripts/python modelo/convert.py --from-s3 --profile <perfil-aws>   # o desde S3
.venv/Scripts/python modelo/smoke_test.py
.venv/Scripts/python modelo/publish.py --profile <perfil-aws>   # solo para una versión nueva
```

Requiere los recortes y el manifiesto del P3 (`dvc pull` en `Proyecto3`). Configuración en [`modelo/conversion.yaml`](../modelo/conversion.yaml); cualquier cambio sube `variant.version`.

Carga en ARM64 sin la Pi (Docker con emulación QEMU), desde la raíz del repo:

```bash
docker run --rm --platform linux/arm64 -v "$PWD/Proyecto4:/p4:ro" -v "$PWD/Proyecto3/data/crops/0.1.3:/crops:ro" python:3.11-slim-bookworm sh -c "pip install -q -r /p4/modelo/requirements-edge.txt && python /p4/modelo/arm64_check.py --model /p4/artifacts/1.0.0-int8.1/model_int8.onnx --crops /crops"
```

En la Raspberry Pi (Raspberry Pi OS de **64 bits**; onnxruntime no tiene wheels para armv7):

```bash
pip install -r modelo/requirements-edge.txt
python modelo/arm64_check.py --model artifacts/1.0.0-int8.1/model_int8.onnx --crops <recortes>
```
