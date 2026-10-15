# Comparación original contra INT8 — VAL-02 (#2, criterios 1.3 y 6.2)

Comparación reproducible, muestra por muestra, entre el modelo publicado 1.0.0 del Proyecto 3 y la variante del edge `1.0.0-int8-e05.1`. Se corre sobre **exactamente** las muestras `val` del manifiesto del P3 (`m-0.1.3-s42-1`, 292 recortes). La hace [`validacion/comparar_modelos.py`](../validacion/comparar_modelos.py).

> **Estado:** el comparador está listo y probado; **faltan los datos**. El manifiesto y los recortes del P3 solo están en el remoto DVC del otro equipo (`dataset-quality-dvc-cache-750702272375`). Mientras no estén en `p4-capturas-474665692638`, no existe `validacion/resultados/`.

## Qué se compara

| Modelo | Archivo | Runtime y preprocesamiento |
|---|---|---|
| `original` | `model.pt` del P3 (`e4acca42…`) | PyTorch, `build_eval_transform` del P3: el modelo tal como se evaluó en el P3 |
| `fp32` (referencia) | `model_fp32.onnx` (`6b640343…`) | onnxruntime CPU, [`modelo/preprocesar.py`](../modelo/preprocesar.py) |
| `int8` (optimizado) | `model_int8.onnx` (`ba89ee43…`) | onnxruntime CPU, `modelo/preprocesar.py`: el modelo tal como corre en el dispositivo |

La diferencia `original → int8` es la que ve el usuario. La columna `fp32` separa sus dos causas: de `original` a `fp32` cambian el runtime y el preprocesamiento del edge; de `fp32` a `int8` solo actúa la cuantización. VAL-04 usa esa separación para explicar los errores.

## Qué garantiza antes y después de correr

1. **Insumos con hash exigido.** El SHA-256 del manifiesto (`45600f29…`, el de `selection.json` del P3), el de `crops.jsonl` (`d3d61f35…`) y el de los tres modelos se toman de `modelo/conversion.yaml` y del registro de conversión que verificó VAL-01. Si alguno no coincide, el comparador se detiene sin escribir nada.
2. **Mismas muestras y etiquetas.** Toma las filas `split == "val"` del manifiesto, en su orden. La clase real (`true_class`) es la `category_name` del manifiesto, y se exige que su `class_index` corresponda al orden `cat, dog, person` del modelo.
3. **Calibración solo con train, comprobada contra el manifiesto.** Cada uno de los 300 IDs de `modelo/registros/calibracion_ids.jsonl` debe ser `train` según el manifiesto del P3. Ninguno puede ser de `val` ni de `test`, ni estar fuera del manifiesto.
4. **CSV verificado al releerlo.** Después de escribirlo, el CSV se vuelve a leer. Sus IDs deben ser exactamente los de `val`, sin duplicados y con las mismas etiquetas. Una muestra sin imagen se registra con su motivo y la comparación falla: no se aceptan faltantes.

## Evidencia

`validacion/resultados/comparacion_val.csv`: una fila por muestra.

| Columna | Contenido |
|---|---|
| `sample_id` | `crop_id` del manifiesto del P3 |
| `true_class` | clase real según el manifiesto |
| `original_prediction` | clase predicha por el modelo original |
| `optimized_prediction` | clase predicha por el INT8 (igual que `int8_prediction`) |
| `fp32_prediction`, `int8_prediction` | clase predicha por cada variante ONNX |
| `prob_<modelo>_<clase>` | probabilidad (softmax) sin redondear, para recalcular cualquier métrica |

`validacion/resultados/comparacion_val.json`: procedencia (hashes del manifiesto, de los recortes y de los modelos), comprobación de la calibración, verificación del CSV (IDs, duplicados, faltantes, etiquetas), SHA-256 del CSV, entorno (versiones y máquina) y un resumen con aciertos y acuerdo. Las métricas formales por clase son de VAL-04.

## Reproducir

Desde `Proyecto4/`, con Python 3.12 o superior (el lockfile fija `numpy==2.5.3`):

```bash
python -m venv modelo/.venv
modelo/.venv/Scripts/pip install -r modelo/requirements-conversion.lock.txt --extra-index-url https://download.pytorch.org/whl/cpu
modelo/.venv/Scripts/python validacion/comparar_modelos.py --descargar --profile <perfil-cuenta-p4>
```

`--descargar` baja de `s3://p4-capturas-474665692638/modelos/` los modelos que falten en local. El comparador espera el manifiesto en `Proyecto3/data/manifests/m-0.1.3-s42-1/` y los recortes en `Proyecto3/data/crops/0.1.3/`, las mismas rutas que usa `convertir.py`.

Las pruebas (`python -m pytest tests/test_comparacion.py`) no necesitan torch ni pesos. Usan un manifiesto y recortes sintéticos para comprobar la selección de `val`, el orden, las etiquetas, los duplicados, los faltantes, la calibración y la exigencia de hashes.

## Fuera de VAL-02

- El resultado en la laptop (x86) no sustituye a la medición en el dispositivo. La cuantización usa activaciones UINT8 para comportarse igual en x86 y en ARM, pero VAL-07 debe confirmarlo en el runtime del edge con entradas conocidas.
