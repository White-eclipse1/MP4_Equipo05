# Guion de Josué: pasos 1 y 9 de la demostración

Complementa [`guion-demo.md`](guion-demo.md). Todo se corre en la laptop, desde `Proyecto4/`, con cualquier Python 3.11 o superior y sin instalar nada. [`validacion/demo_val.py`](../validacion/demo_val.py) **solo lee** el paquete [`evidencias/VAL-08/`](../evidencias/VAL-08/), el mismo que recibe el evaluador, y **no escribe nada**: se puede repetir sin cambiar la evidencia.

> **No correr durante la demo** `python validacion/recursos.py`, `metricas.py` ni `modelo/verificar_linaje.py` sin `--salida`: reescriben archivos de evidencia (cambia la fecha). Para recalcular se usan `demo_val.py` y `recalcular.py`, que solo leen.

## Antes de empezar

```bash
cd Proyecto4
python validacion/demo_val.py linaje
cd evidencias/VAL-08 && python recalcular.py && cd ../..
```

Deja abiertas dos terminales en `Proyecto4/` y, en el navegador, [`evidencias/VAL-08/README.md`](../evidencias/VAL-08/README.md) y [`linaje-modelo.md`](linaje-modelo.md).

## Paso 1: el modelo viene del P3 (M1)

Cuando Omar arranca el programa en la Raspberry, la primera línea (`modelo_cargado`) muestra la versión `1.0.0-int8-e05.1` y el hash `ba89ee43…2a12`. Corre:

```bash
python validacion/demo_val.py linaje
```

**Qué decir:**

1. "El hash que acaba de imprimir la Raspberry, `ba89ee43…`, es el de la variante INT8. Aquí está, en la última línea de la cadena."
2. "Esa variante sale de `model.pt` versión 1.0.0 del Proyecto 3, el run de MLflow `9f9b62c2…`, que es el que el P3 seleccionó en su `selection.json`. Su hash es `e4acca42…`."
3. "La conversión es reproducible: `convertir.py` con `conversion.yaml`. Exige el hash del original antes de convertir y deja un registro con el hash de la entrada y de la salida. La calibración usó solo recortes de train; ninguno del test del P3."
4. "La verificación de linaje recalculó los hashes sobre los archivos reales en S3: 20 comprobaciones aprobadas, 0 fallas. Mismas clases (`cat`, `dog`, `person`, en ese orden) y mismo preprocesamiento: 224×224 con la media y la desviación de ImageNet."

Si preguntan si el preprocesamiento del dispositivo es el mismo: "Sí, lo verificamos (VAL-07). Los 295 tensores preprocesados en la Raspberry son idénticos bit a bit a los de la laptop."

## Paso 9: reproducir lo que elija el profe

### Si elige una imagen de la validación

Pídele un ID de [`predicciones_val.csv`](../validacion/resultados/predicciones_val.csv) (por ejemplo, `0.1.3:a559`, que es la interesante):

```bash
python validacion/demo_val.py muestra 0.1.3:a559
```

Muestra la clase real del manifiesto, las probabilidades del original y los **logits del INT8 registrados en la Raspberry** con su softmax, y comprueba que coincida con el archivo formal.

**Qué decir sobre `a559`:** "Es la única imagen en la que el INT8 se equivoca y el original no. El original ya dudaba: 58 % perro contra 42 % gato. En el INT8, los logits de gato y perro quedan exactamente iguales y el empate se resuelve hacia la primera clase. Es la pérdida propia de cuantizar: una muestra en la frontera."

### Si elige una cifra de calidad

```bash
python validacion/demo_val.py calidad
python validacion/demo_val.py clase dog          # o cat / person
```

Accuracy 291/292 → 290/292, F1 macro y caída **(291 − 290) / 292 × 100 = 25/73 = 0.3425 pp**. Se calcula como fracción exacta y se compara con 2 pp sin redondear. Por clase: TP, FP y FN, y de ahí la precisión, el recall y el F1.

**Qué decir:** "Todas las métricas salen del archivo de predicciones por muestra, que se une con el manifiesto del P3 por ID. No hay tablas copiadas a mano. Son cifras de **validación**; el test del P3 no se usó."

### Si elige latencia o una fila del benchmark

```bash
python validacion/demo_val.py latencia int8      # o fp32
python validacion/demo_val.py fila 57            # cualquier índice de 0 a 209
```

Muestra los 10 calentamientos excluidos y las 200 mediciones válidas ordenadas, y calcula p50 y p95 **a la vista** con la fórmula de interpolación lineal: h = (n − 1) × p / 100. Con `fila`, la fila cruda: fase, preprocesamiento, inferencia y total en ms, y la temperatura.

**Qué decir:** "Es la misma Raspberry de la demo. Cada medición incluye decodificar la foto, preprocesarla e inferir; no incluye el envío a AWS. INT8: p50 de 113.5 ms contra 190.1 del original en FP32, 40 % menos. La medición INT8 más lenta (118 ms) es más rápida que la FP32 más rápida (189 ms), así que la diferencia no está dentro del ruido."

### Si elige el tamaño

```bash
python validacion/demo_val.py tamano
```

44 783 563 B → 11 295 280 B: **−74.78 %**, 3.96 veces menor. Los bytes y los hashes están verificados en S3 y en la Raspberry.

### Si quiere todo de una vez

```bash
cd evidencias/VAL-08
python recalcular.py
```

Debe terminar en `VERIFICADO`: recalcula todo solo con el paquete y comprueba cada archivo contra `SHA256SUMS.txt`.

## Preguntas probables

| Pregunta | Respuesta corta |
|---|---|
| ¿Por qué la accuracy del INT8 baja tan poco? | Porque una sola muestra cambia (`a559`, una frontera). `person` conserva precisión y recall de 100 %. |
| ¿Comparan contra la laptop? | No. Latencia y calidad del optimizado son del mismo dispositivo. El original se midió en la Raspberry como ONNX FP32 (mismos pesos, mismo runtime). |
| ¿Por qué FP32 y no PyTorch en el dispositivo? | Para tener condiciones equivalentes: mismo runtime, preprocesamiento e imágenes. El FP32 da las mismas 292 predicciones que PyTorch. |
| ¿Qué método de percentil usan? | Interpolación lineal (tipo 7), el de `numpy.percentile` por defecto. Coincide con numpy y con `statistics`. |
| ¿Usaron el test para calibrar? | No. 300 recortes solo de train; está verificado contra el manifiesto. |
| ¿Por qué en su laptop daba 288 y no 290? | El mismo INT8 en una CPU x86 sin VNNI cambia 4 muestras por cómo ejecuta los kernels enteros. En la Raspberry coincide con la aritmética de referencia en las 295 entradas. La cifra que cuenta es la del dispositivo. |
| ¿Qué pasa si alguien cambia un archivo? | `recalcular.py` lo detecta por el hash y, además, al reconstruir las predicciones desde los datos primarios. |
