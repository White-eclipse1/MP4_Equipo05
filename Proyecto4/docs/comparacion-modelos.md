# Comparación original contra INT8 — VAL-02 (#2, criterios 1.3 y 6.2)

Comparación reproducible, muestra por muestra, entre el modelo publicado 1.0.0 del Proyecto 3 y la variante del edge `1.0.0-int8-e05.1`. Se corre sobre **exactamente** las muestras `val` del manifiesto del P3 (`m-0.1.3-s42-1`, 292 recortes). La hace [`validacion/comparar_modelos.py`](../validacion/comparar_modelos.py), y la evidencia queda en [`validacion/resultados/`](../validacion/resultados/).

## Resultado (15 oct de 2026, laptop x86)

292 muestras de `val` (67 cat, 78 dog, 147 person), ninguna faltante, ningún ID duplicado. Los IDs y las etiquetas son los del manifiesto, en su orden, y los 300 IDs de calibración son de `train` según el manifiesto.

| Modelo | Aciertos | Accuracy | Acuerdo con el original |
|---|---:|---:|---:|
| `original` (PyTorch) | 291 / 292 | 0.99658 | — |
| `fp32` (ONNX) | 291 / 292 | 0.99658 | 292 / 292 |
| `int8_referencia` (QDQ sin fusionar) | 290 / 292 | 0.99315 | 291 / 292 |
| **`int8`** (onnxruntime por defecto, esta CPU) | **288 / 292** | **0.98630** | **287 / 292** |

Entorno: Python 3.13.15, torch 2.14.0+cpu, onnxruntime 1.31.0 y numpy 2.5.3 (idéntico a `modelo/requirements-conversion.lock.txt`). CPU: AMD Ryzen 5 5625U (Zen 3: AVX2, sin VNNI). Dos corridas seguidas dan el mismo CSV byte a byte (SHA-256 `e3be4f68…8240`).

Son números de la laptop. Las métricas por clase y el análisis de errores corresponden a VAL-04 (#14), y la medición que cuenta para la rúbrica se hace en el dispositivo (VAL-07, VAL-05).

### Hallazgo: en x86 sin VNNI, el INT8 depende del CPU

El mismo `model_int8.onnx` da 288 aciertos con las optimizaciones por defecto de onnxruntime y 290 con la aritmética de referencia del grafo. La variante usa el formato U8S8 (activaciones UINT8 y pesos INT8). Cuando onnxruntime funde los pares QDQ en kernels enteros sobre una CPU x86 sin VNNI, las sumas intermedias pueden **saturar**. Los errores que solo aparecen por eso son de muestras que el original clasifica con total seguridad: `0.1.3:a448` es `cat` con probabilidad 0.9996 y el INT8 la convierte en `person` con 0.506. En una CPU con VNNI, o en ARM, el kernel entero no satura y el resultado debería coincidir con la referencia: el registro de conversión, generado en otra máquina, reporta 0.9932.

Por eso el CSV trae dos columnas del INT8, y la evidencia registra el nombre del CPU:

- **`int8`** (`optimized_prediction`): lo que ejecuta el runtime en la máquina que corre la comparación.
- **`int8_referencia`**: el mismo archivo con `ORT_DISABLE_ALL`. Cada `QuantizeLinear` y `DequantizeLinear` se ejecuta tal cual y la convolución se hace en float. No depende del CPU y es la cifra contra la que se contrasta el dispositivo.

Esto contradice el comentario de `modelo/conversion.yaml`, según el cual las activaciones UINT8 "se comportan igual en x86 y en ARM": no es así en x86 sin VNNI.

## Qué se compara

| Columna | Archivo | Runtime y preprocesamiento |
|---|---|---|
| `original` | `model.pt` del P3 (`e4acca42…`) | PyTorch con `build_eval_transform` del P3: el modelo tal como se evaluó en el P3 |
| `fp32` | `model_fp32.onnx` (`6b640343…`) | onnxruntime CPU con [`modelo/preprocesar.py`](../modelo/preprocesar.py) |
| `int8` | `model_int8.onnx` (`ba89ee43…`) | onnxruntime CPU con optimizaciones por defecto y `preprocesar.py`, como corre en el dispositivo |
| `int8_referencia` | `model_int8.onnx` (`ba89ee43…`) | onnxruntime CPU con `ORT_DISABLE_ALL` y `preprocesar.py` |

La diferencia entre `original` e `int8` es la que ve el usuario. Las otras columnas separan sus causas:

- De `original` a `fp32` cambian el runtime y el preprocesamiento del edge. Aquí no cambia ninguna predicción.
- De `fp32` a `int8_referencia` actúa solo la cuantización.
- De `int8_referencia` a `int8` actúa solo el kernel entero de esa CPU.

## Qué garantiza antes y después de correr

1. **Insumos con hash exigido.** El SHA-256 del manifiesto (`45600f29…`, el de `selection.json` del P3), el de `crops.jsonl` (`d3d61f35…`) y el de los tres modelos se toman de `modelo/conversion.yaml` y del registro de conversión que verificó VAL-01. Si alguno no coincide, el comparador se detiene sin escribir nada. Además, cada PNG de `val` debe medir lo que dice `crops.jsonl`.
2. **Mismas muestras y etiquetas.** El comparador toma las filas con `split == "val"` del manifiesto, en su orden. La clase real (`true_class`) es la `category_name` del manifiesto, y se exige que su `class_index` corresponda al orden `cat, dog, person` del modelo.
3. **Calibración solo con train, comprobada contra el manifiesto.** Cada uno de los 300 IDs de `modelo/registros/calibracion_ids.jsonl` debe ser `train` según el manifiesto del P3. Ninguno puede ser de `val` ni de `test`, ni estar fuera del manifiesto.
4. **CSV verificado al releerlo.** Después de escribirlo, el comparador vuelve a leer el CSV. Sus IDs deben ser exactamente los de `val`, sin duplicados y con las mismas etiquetas. Una muestra sin imagen se registra con su motivo y la comparación falla: no se aceptan faltantes.

## Evidencia

[`validacion/resultados/comparacion_val.csv`](../validacion/resultados/comparacion_val.csv): una fila por muestra.

| Columna | Contenido |
|---|---|
| `sample_id` | `crop_id` del manifiesto del P3 |
| `true_class` | clase real según el manifiesto |
| `original_prediction` | clase predicha por el modelo original |
| `optimized_prediction` | clase predicha por el INT8 (igual que `int8_prediction`) |
| `fp32_prediction`, `int8_prediction`, `int8_referencia_prediction` | clase predicha por cada ejecución ONNX |
| `prob_<columna>_<clase>` | probabilidad (softmax) sin redondear, para recalcular cualquier métrica |

[`validacion/resultados/comparacion_val.json`](../validacion/resultados/comparacion_val.json) contiene:
- la procedencia: hashes del manifiesto, de los recortes y de los modelos;
- la comprobación de la calibración;
- la verificación del CSV (IDs, duplicados, faltantes y etiquetas) y su SHA-256;
- el entorno, con versiones y CPU;
- un resumen con aciertos y acuerdos.

## Reproducir

Desde `Proyecto4/`, con Python 3.12 o superior (el lockfile fija `numpy==2.5.3`):

```bash
python -m venv modelo/.venv
modelo/.venv/Scripts/pip install -r modelo/requirements-conversion.lock.txt boto3 --extra-index-url https://download.pytorch.org/whl/cpu
modelo/.venv/Scripts/python validacion/comparar_modelos.py --descargar --profile <perfil-cuenta-p4>
```

`--descargar` baja de `s3://p4-capturas-474665692638/` lo que falte en local:
- los modelos, de `modelos/`;
- el manifiesto y los recortes del P3, de `datos/p3/`. Se guardan en `Proyecto3/data/manifests/m-0.1.3-s42-1/` y `Proyecto3/data/crops/0.1.3/`, las mismas rutas que usa `convertir.py`.

Después exige sus SHA-256 igual que con copias locales. En otra máquina x86 la columna `int8` puede cambiar según el CPU; las demás deben dar el mismo CSV.

Las pruebas (`python -m pytest tests/test_comparacion.py`) no necesitan torch ni pesos. Usan un manifiesto y recortes sintéticos para comprobar:
- la selección de `val`, el orden y las etiquetas;
- los duplicados y los faltantes;
- la calibración;
- las dimensiones de los recortes;
- la exigencia de hashes.
