# Preprocesamiento y entradas conocidas en el edge — VAL-07 (#19, criterios 2.2 y 6.2)

Comprueba que las diferencias entre el original y el INT8 **no vienen de un preprocesamiento incorrecto en el dispositivo**. Para eso corre **el mismo** [`edge/verificar_preprocesamiento.py`](../edge/verificar_preprocesamiento.py) en la Raspberry y en la laptop de VAL ("offline"), con las mismas entradas y los mismos modelos, y [`validacion/contrastar_edge.py`](../validacion/contrastar_edge.py) compara las dos corridas.

## Qué se comprueba

**1. Preprocesamiento contra valores calculados a mano.** El script verifica `modelo/preprocesar.py` en cada máquina con imágenes sintéticas, cuyos valores esperados se calculan en float32 sin depender de la otra máquina:

| Comprobación | Qué demuestra |
|---|---|
| `tensor.forma_tipo` | Entrada `[1, 3, 224, 224]`, float32, NCHW contiguo |
| `normalizacion.exacta` | Un color sólido (255, 128, 0) da, en los 224 × 224 píxeles, exactamente `(x/255 − media) / desviación`, con media `[0.485, 0.456, 0.406]` y desviación `[0.229, 0.224, 0.225]` de ImageNet. Prueba la escala a [0, 1] y el canal 0 = R |
| `rgb.orden_y_orientacion` | Una imagen roja a la izquierda y azul a la derecha conserva los colores y los lados: RGB (no BGR), sin espejo ni transposición |
| `resize.sin_recorte` | Una franja en el borde de una imagen de 400 × 100 sobrevive en la columna 0: se estira la imagen completa a 224 × 224 (`resize_to_square` del P3); no hay recorte central |
| `escala.cero_uno` | Un degradado 0..255 vuelve exactamente a [0, 1] al deshacer la normalización |
| `rgb.conversion` | Escala de grises y RGBA se convierten a RGB (el canal alfa se descarta) |

Las pruebas (`tests/test_preprocesamiento_edge.py`) confirman que estas comprobaciones **detectan** un preprocesamiento mal hecho: BGR, sin normalizar, con recorte central o en float64.

**2. Entradas conocidas**, verificadas por SHA-256 contra el índice versionado [`validacion/registros/entradas_edge.jsonl`](../validacion/registros/entradas_edge.jsonl):
- los **292 recortes `val`** del manifiesto del P3, con su clase real; sus predicciones offline son las de VAL-02;
- las **3 fotos de la cámara** de EDGE-03 (`cat`, `dog`, `person`).

Para cada entrada se registra el SHA-256 del tensor preprocesado, su forma y su tipo, y la clase y los logits de tres ejecuciones:

| Ejecución | Modelo | onnxruntime |
|---|---|---|
| `int8` | `model_int8.onnx` | Opciones por defecto, como `edge/inferencia.py` |
| `int8_referencia` | `model_int8.onnx` | `ORT_DISABLE_ALL`: el grafo QDQ paso a paso |
| `fp32` | `model_fp32.onnx` (original sin cuantizar) | Opciones por defecto |

**3. Contraste entre la Raspberry y la laptop** (`contrastar_edge.py`):
- **Lo que debe coincidir**, y si no coincide el contraste falla: las comprobaciones sintéticas en los dos lados, el mismo `preprocesar.py`, los mismos modelos y entradas, y el **tensor preprocesado idéntico bit a bit** en cada entrada.
- **Lo que se cuenta y se explica**, sin que sea una falla: las predicciones del edge contra las offline en cada ejecución, la diferencia máxima de logits y si en ARM el `int8` coincide con `int8_referencia`. Esto último pone a prueba la hipótesis de saturación de VAL-02.

## Pasos

### 1. Josué: preparar el paquete de entradas

Desde `Proyecto4/`, con el entorno de VAL y los datos del P3 (`--descargar` de VAL-02):

```bash
modelo/.venv/Scripts/python validacion/preparar_entradas_edge.py
modelo/.venv/Scripts/python edge/verificar_preprocesamiento.py --entradas validacion/entradas_edge --modelos modelo/artefactos/1.0.0-int8-e05.1 --maquina laptop
```

El primer comando genera `validacion/entradas_edge.zip` (69.5 MB, ignorado por Git) y el índice versionado. El segundo es la corrida offline, que queda en `evidencias/VAL-07/laptop/`. Josué le hace llegar el zip a Omar por un canal privado: directamente, o subiéndolo a S3 con un enlace temporal, como en VAL-05.

### 2. Omar: copiar a la Raspberry

Desde la laptop con el repositorio actualizado:

```bash
rsync -av Proyecto4/edge/verificar_preprocesamiento.py Proyecto4/edge/benchmark.py pi@<ip-de-la-raspberry>:/home/pi/edge01/app/
rsync -av Proyecto4/modelo/preprocesar.py pi@<ip-de-la-raspberry>:/home/pi/edge01/modelo/preprocesar.py
rsync -av entradas_edge.zip pi@<ip-de-la-raspberry>:/home/pi/edge01/
```

Los modelos INT8 y FP32 ya están en `/home/pi/edge01/modelo/` desde VAL-05.

### 3. Omar: correr en la Raspberry

```bash
cd "$HOME/edge01"
source .venv/bin/activate
sha256sum entradas_edge.zip
python -c "import zipfile; zipfile.ZipFile('entradas_edge.zip').extractall('.')"
python app/verificar_preprocesamiento.py
```

El hash del zip debe ser `8881813c3c1111f92c5076f3b9868e084237a39693d6bd6038d8a36221c6c085`.

La corrida tarda unos minutos. Debe mostrar `ok` en las 6 comprobaciones, avanzar de 50 en 50 hasta 295 entradas y escribir `evidencias/VAL-07/raspberry/resultados.csv` y `resultados.json`. Toma una captura de la Terminal. No hace llamadas de red.

### 4. Omar: devolver la evidencia

Devuelve, sin editarlos, `evidencias/VAL-07/raspberry/resultados.csv`, `resultados.json` y la captura (por ejemplo, en un zip). Josué los coloca en `Proyecto4/evidencias/VAL-07/raspberry/`.

### 5. Josué: contrastar

```bash
python validacion/contrastar_edge.py
```

Escribe `validacion/resultados/contraste_edge.json` y la tabla `validacion/resultados/entradas_conocidas.csv`, solo si el contraste pasa.

## Corrida offline (laptop de VAL)

En [`evidencias/VAL-07/laptop/`](../evidencias/VAL-07/laptop/): Python 3.13.15, onnxruntime 1.31.0, Ryzen 5 5625U. Las 6 comprobaciones sintéticas pasan. En `val`, `int8` acierta 288 de 292, `int8_referencia` 290 y `fp32` 291. Las predicciones de las tres ejecuciones son **idénticas, muestra por muestra**, a las de VAL-02 (`comparacion_val.csv`).
