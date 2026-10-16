# Calidad del original y del optimizado en validación — VAL-04 (#14, criterio 1.3)

Métricas formales del modelo original del P3 (`model.pt` 1.0.0) y de la variante `1.0.0-int8-e05.1`, calculadas **exclusivamente** desde el archivo de predicciones por muestra de VAL-03 ([`predicciones_val.csv`](../validacion/resultados/predicciones_val.csv)) y sobre la **misma validación**: las 292 muestras `val` del manifiesto `m-0.1.3-s42-1`.

| Evidencia | Contenido |
|---|---|
| [`validacion/resultados/metricas_val.json`](../validacion/resultados/metricas_val.json) | Métricas de los dos modelos, matrices de confusión, caída de accuracy, cambios por clase, errores relevantes y la referencia del test del P3 (aparte) |
| [`validacion/resultados/metricas_val.csv`](../validacion/resultados/metricas_val.csv) | Tabla antes y después: cada métrica con el original, el optimizado y la diferencia en pp |

> **Todas las cifras son de validación (`val`).** Las del test del P3 aparecen solo en la [última sección](#cifras-del-test-del-p3-otra-partición), como referencia; no se comparan con estas.

## Resultado

| | Original | Optimizado |
|---|---:|---:|
| Aciertos | 291 / 292 | 288 / 292 |
| Accuracy | 99.658 % | 98.630 % |
| F1 macro | 99.537 % | 98.479 % |

**Caída de accuracy: 75/73 pp = 1.0274 pp. Cumple el límite de 2 pp.** La caída se calcula con fracciones exactas, (291 − 288) / 292 × 100, y se compara con 2 sin redondear. El accuracy del original en `val` es idéntico al que registró el P3 para el modelo seleccionado (0.9965753424657534 en `Proyecto3/docs/selection.json`).

El optimizado es el INT8 tal como lo ejecuta onnxruntime 1.31.0 en la laptop de VAL (AMD Ryzen 5 5625U). La cifra de la rúbrica es la del dispositivo: VAL-07 (#19) regenera las predicciones en el edge, y este cálculo se repite con el mismo comando.

## Antes y después por clase

| Clase | Support | Precisión orig. → opt. | Recall orig. → opt. | F1 orig. → opt. |
|---|---:|---|---|---|
| `cat` | 67 | 100.00 % → 98.48 % | 98.51 % → 97.01 % | 99.25 % → 97.74 % |
| `dog` | 78 | 98.73 % → 100.00 % | 100.00 % → 97.44 % | 99.36 % → 98.70 % |
| `person` | 147 | 100.00 % → 98.00 % | 100.00 % → 100.00 % | 100.00 % → 98.99 % |

Esta tabla está redondeada para leerla. Los valores exactos y las diferencias en pp están en `metricas_val.csv`.

Matrices de confusión (filas: clase real; columnas: predicha `cat`, `dog`, `person`):

| Real | Original | Optimizado |
|---|---|---|
| `cat` | 66, 1, 0 | 65, 0, **2** |
| `dog` | 0, 78, 0 | **1**, 76, **1** |
| `person` | 0, 0, 147 | 0, 0, 147 |

### Cambios notables por clase

- **`person`: el recall se mantiene en 100 % y la precisión baja 2 pp.** Ninguna persona se pierde, pero 3 muestras que no son personas (`a1647` y `a448`, que son `cat`, y `a554`, que es `dog`) pasan a predecirse como `person`. Es el patrón principal del INT8: sus errores nuevos se van hacia `person`, que es la clase mayoritaria (147 de 292).
- **`cat`: el recall baja 1.49 pp, de 66 a 65.** Hay dos regresiones (`a1647` y `a448` → `person`) y una corrección (`a322`). La precisión baja 1.52 pp porque `a559`, un `dog`, se predice como `cat`.
- **`dog`: el recall baja 2.56 pp** por dos regresiones (`a554` → `person` y `a559` → `cat`). La precisión **sube** a 100 %: el único falso `dog` del original (`a322`) desaparece.

## Errores relevantes

Son las 5 muestras en que algún modelo falla o en que los dos no coinciden. La última columna es contexto de VAL-02, no interviene en ninguna métrica: es lo que predice el mismo INT8 con la aritmética de referencia del grafo, sin kernels enteros fusionados.

| Muestra | Real | Original (prob.) | Optimizado (prob.) | Tipo | Referencia QDQ (VAL-02) |
|---|---|---|---|---|---|
| `0.1.3:a1647` | cat | cat (0.991) | person (0.571) | regresión | cat |
| `0.1.3:a448` | cat | cat (0.9997) | person (0.506) | regresión | cat |
| `0.1.3:a554` | dog | dog (0.553) | person (0.524) | regresión | dog |
| `0.1.3:a559` | dog | dog (0.583) | cat (0.888) | regresión | cat |
| `0.1.3:a322` | cat | dog (0.891) | cat (0.601) | corrección | dog |

Lectura:

- **Casos límite del original (`a554`, `a559`).** El original ya dudaba en estas dos muestras: `dog` con 0.553 contra `person` con 0.437, y `dog` con 0.583 contra `cat` con 0.416. Un cambio pequeño en los logits basta para invertirlas. Es el tipo de pérdida que se espera de la cuantización.
- **Regresiones con el original muy seguro (`a1647`, `a448`).** El original las clasificaba con 0.991 y 0.9997, y el INT8 las lleva casi al empate con `person`. Con la aritmética de referencia el INT8 sí acierta las dos (y también `a554`). Por eso se atribuyen a cómo ejecuta el INT8 el kernel entero fusionado en esta CPU. La causa exacta sigue siendo una hipótesis (saturación U8S8 en x86 sin VNNI; ver [`comparacion-modelos.md`](comparacion-modelos.md)) que se confirma o descarta en el dispositivo.
- **Corrección (`a322`).** El original se equivocaba con mucha seguridad (`dog`, 0.891) y el INT8 acierta con 0.601. Con la aritmética de referencia el INT8 repite el error del original, así que no es una mejora robusta: viene del mismo efecto del kernel.
- **`a559` es la única regresión que aparece también con la referencia.** Es la pérdida atribuible a la cuantización por sí sola.

En resumen: la cuantización por sí sola cuesta, en esta validación, una muestra frontera (`a559`). El resto de la diferencia depende del runtime de esta máquina. Con o sin ese efecto, la caída queda por debajo de 2 pp.

## Recalcular

Desde `Proyecto4/`, con cualquier Python 3.11 o superior y sin dependencias:

```bash
python validacion/verificar_predicciones.py   # VAL-03: el archivo de predicciones es válido
python validacion/metricas.py                 # VAL-04: recalcula y reescribe metricas_val.*
```

[`metricas.py`](../validacion/metricas.py) funciona así:
- **Antes de calcular,** verifica el archivo de predicciones contra el manifiesto.
- **Al calcular,** usa fracciones exactas y solo convierte a decimal al escribir. Para clases que nunca se predicen, la precisión vale 0.
- **Antes de escribir,** contrasta los aciertos con los que declara VAL-03. Si algo no cuadra, no toca la evidencia.

Dos corridas, y Python 3.11 contra 3.13, dan la misma tabla byte a byte. Como control independiente, las métricas coinciden con las de scikit-learn, con diferencias menores a 1e-12, en accuracy, F1 macro, precisión, recall, F1 y support por clase, y en las matrices de confusión. scikit-learn no es dependencia del proyecto: el contraste se hizo una vez y aquí queda registrado.

## Cifras del test del P3 (otra partición)

| Partición | Muestras | Modelo | Accuracy | F1 macro | Fuente |
|---|---:|---|---:|---:|---|
| **test** del P3 | 145 | solo el original | 97.93 % | 97.44 % | `Proyecto3/reports/evaluation/9f9b62c2…/metrics.json` |

**No es la validación de VAL-04 y no se compara con las cifras de arriba.** Es otra partición: el P3 evaluó en test solo el modelo seleccionado. El INT8 no se evalúa en test: el test del P3 no interviene en la conversión, la calibración ni esta comparación. En `metricas_val.json` estas cifras están aparte, en `referencia_test_p3`.
