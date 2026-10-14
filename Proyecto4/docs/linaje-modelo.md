# Linaje del modelo — VAL-01 (M1, criterio 1.1)

Demuestra que la variante que usa el Proyecto 4 sale del modelo que el equipo publicó en el Proyecto 3, y no de un modelo externo. La cadena se reconstruye y se contrasta con [`modelo/verificar_linaje.py`](../modelo/verificar_linaje.py). Su salida queda en [`modelo/registros/linaje_verificacion.json`](../modelo/registros/linaje_verificacion.json).

```
P3 1.0.0  model.pt  e4acca42…9172   (run 9f9b62c2…, selection.json del P3)
   │  modelo/convert.py + modelo/conversion.yaml + requirements-conversion.lock.txt
   ▼
conversion_log.json  (input: sha256 e4acca42…  →  outputs: fp32 e4dc89bb…, int8 ca689c4e…)
   │  modelo/publish.py → publicacion.json (llave, SHA-256 y VersionId de cada objeto)
   ▼
P4 1.0.0-int8.1  model_int8.onnx  ca689c4e…69c0  +  model_package.json  66a45231…87cc
```

## Ficha

| Dato | Original (Proyecto 3) | Variante (Proyecto 4) |
|---|---|---|
| Versión | `1.0.0` (activa en el registro del P3) | `1.0.0-int8.1` |
| Run ID de MLflow | `9f9b62c202f0446a8a4b411a10321eff` (r10, mejor época 6) | — (sale de ese run) |
| Checkpoint / archivo | `mlflow-artifacts:/3/9f9b62c2…/artifacts/checkpoint/model.pt` | `model_int8.onnx` (ONNX opset 18, INT8 QDQ por canal) |
| Llave en S3 | `s3://dataset-quality-releases-750702272375/models/clasificador/1.0.0/model.pt` | `s3://dataset-quality-releases-750702272375/models/clasificador-edge/1.0.0-int8.1/model_int8.onnx` |
| VersionId | `VtRww5se97lomVTcKJUv6d9mYSL7TXOf` | `zZUwIi72HXSCv1KEuw2hHmunc1.xdwjt` |
| SHA-256 | `e4acca429ebf73d0e5a60fb0dda383a6a5322dccb1decf04b4e40ab9db989172` | `ca689c4e1478ccca7821dffaba8f07886bd9609a8aa3cec7450d9f875fbd69c0` |
| Bytes | 44 783 563 | 11 349 151 |
| Mapa de clases (índice de salida) | `0 cat`, `1 dog`, `2 person` | `0 cat`, `1 dog`, `2 person` |
| Preprocesamiento | RGB, `resize_to_square` a 224×224 (bilineal con antialias), escala a [0, 1], media `[0.485, 0.456, 0.406]`, desviación `[0.229, 0.224, 0.225]` | El mismo, en [`modelo/preprocess.py`](../modelo/preprocess.py) (numpy + Pillow); entrada `input` float32 NCHW `[1, 3, 224, 224]`, salida `logits` `[1, 3]` |

Script de conversión: [`modelo/convert.py`](../modelo/convert.py). Configuración: [`modelo/conversion.yaml`](../modelo/conversion.yaml). Registro: [`modelo/registros/conversion_log.json`](../modelo/registros/conversion_log.json), SHA-256 `3113c9ab…86b5`, igual al publicado en S3.

## Criterios de aceptación

Resultado del nivel «registros» (`python modelo/verificar_linaje.py`, 13 oct de 2026): **14 ok, 0 fallas, 1 pendiente**.

| Criterio | Comprobación | Fuentes que se contrastan | Estado |
|---|---|---|---|
| Versión original 1.0.0 | `origen.version` | `conversion.yaml`, `conversion_log.json`, llave `models/clasificador/1.0.0/` | ok |
| run_id de origen | `origen.run_id` | `conversion.yaml`, `conversion_log.json`, `Proyecto3/docs/selection.json`, `Proyecto3/reports/evaluation/9f9b62c2…/` | ok |
| Checkpoint original | `origen.checkpoint` | URI de MLflow en `selection.json`, llave y VersionId en S3, ruta de la copia DVC | ok |
| SHA-256 del original | `origen.sha256_registros` | `conversion.yaml`, `conversion_log.json`, `selection.json`, `smoke_test.json` y la tabla de `Proyecto3/docs/publicacion_s3.md` (con VersionId y run_id) | ok en registros; **recálculo sobre el binario pendiente** |
| Variante 1.0.0-int8.1 | `variante.version` | `conversion.yaml`, `conversion_log.json`, `publicacion.json`, `smoke_test.json`, prefijo en S3 | ok |
| SHA-256 de la variante | `variante.sha256_registros` | `conversion_log.json`, `publicacion.json` (con VersionId), `smoke_test.json`, `arm64_check.txt` | ok en registros; **recálculo sobre el binario pendiente** |
| Orden de clases cat, dog, person | `clases.orden`, `paquete.reconstruido` | `Proyecto3/config/classes.yaml` → checkpoint (`conversion_log.input.class_names`) → `model_package.json` publicado | ok |
| Preprocesamiento | `preprocesamiento`, `paquete.reconstruido` | `Proyecto3/src/p3/data/transforms.py` (`EVAL_RESIZE`, `IMAGENET_MEAN`, `IMAGENET_STD`) → checkpoint → `modelo/preprocess.py` → `model_package.json` publicado | ok |
| Referencia al script y la configuración | `conversion.referencia` | `convert.py` lee `conversion.yaml`; lockfile presente; la técnica del registro es la de la configuración | ok |
| El registro identifica entrada y salida | `conversion.entrada_salida` | `conversion_log.json`: entrada con llave S3 y SHA-256; salidas FP32 e INT8 con archivo, bytes y SHA-256 | ok |
| No se sustituye por un modelo externo | `origen.no_externo`, `calibracion.train` | `convert.py` carga con `load_checkpoint` del P3 y se detiene si el SHA-256 no es el de `conversion.yaml`; arquitectura `resnet18` del P3; ONNX FP32 igual a PyTorch (máx. \|Δlogit\| 1.2e-7); calibración con 200 recortes de train del mismo manifiesto con que se entrenó el modelo seleccionado | ok |

Dos comprobaciones adicionales hacen que la cadena no dependa solo de que los registros digan lo mismo:

- **`registros.publicados`:** `conversion_log.json`, `calibracion_manifest.jsonl` y `smoke_test.json` en Git tienen, byte a byte, el SHA-256 que `publish.py` registró al subirlos a S3. El registro versionado es el mismo que se publicó con la variante.
- **`paquete.reconstruido`:** el script vuelve a generar `model_package.json` con la misma plantilla que `convert.py`, a partir de las clases y el preprocesamiento del registro, y obtiene el SHA-256 publicado (`66a45231…87cc`, 837 bytes). Así queda probado, sin descargar nada, que el paquete que lee el dispositivo declara exactamente ese mapa de clases y ese preprocesamiento.

## Pendiente: recalcular hashes sobre los binarios

Falta descargar `model.pt` y `model_int8.onnx` y recalcular su SHA-256. Los perfiles de AWS de Josué (`p3`, `default`) pertenecen a otras cuentas y reciben `403` en el bucket del equipo (`750702272375`). Lo puede correr quien tenga un perfil de la cuenta del equipo (por ejemplo, el de Emilio o Edith), desde `Proyecto4/`:

```bash
python modelo/verificar_linaje.py --profile <perfil-del-equipo>
```

Además del nivel «registros», en ese modo el script:

- recalcula el SHA-256 de `model.pt` del P3 y de los seis objetos de `models/clasificador-edge/1.0.0-int8.1/`, y exige el `VersionId` registrado;
- lee `models/clasificador/registry.json`, `class_map.json`, `preprocessing.json` y `model_version.json` del paquete 1.0.0 del P3 y los compara con la conversión.

Con las copias locales (`dvc pull mlflow_snapshot.dvc` en `Proyecto3/` y `artifacts/1.0.0-int8.1/` generado con `convert.py`), `--local` recalcula los mismos hashes sin red. El JSON se sobrescribe con los niveles ejecutados y la identidad de AWS usada.

## Observaciones

- **El SHA-256 de `model_package.json` depende del sistema operativo.** `convert.py` lo escribe con `Path.write_text`, que en Windows convierte `\n` en `\r\n`. El publicado (837 bytes) se generó en Windows; en Linux o macOS saldría otro hash (787 bytes) aunque el contenido sea el mismo. Los SHA-256 de los `.onnx` no se ven afectados. Si la variante se regenera en otro sistema, conviene escribir el paquete con `newline="\n"`.
- **Las probabilidades INT8 difieren entre x86 y ARM** (ver [`artefacto.md`](artefacto.md#aviso-para-f7-y-f8-medir-int8-en-arm-no-en-la-laptop)). No afecta al linaje, pero VAL-02 y VAL-03 deben medir en aarch64.

## Reproducir

Desde `Proyecto4/`, con Python 3.11 o superior y PyYAML (boto3 solo para `--profile`):

```bash
python modelo/verificar_linaje.py
python -m pytest tests/test_linaje.py
```

Las pruebas comprueban que el linaje actual pasa y que el script detecta un hash de variante alterado, otro orden de clases, otro run de origen, otro preprocesamiento y binarios sustituidos en S3.
