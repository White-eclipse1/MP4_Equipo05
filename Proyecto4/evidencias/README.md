# Evidencias del Proyecto 4

Índice de la evidencia que pide la rúbrica ([`docs/rubrica.md`](../docs/rubrica.md), "Entrega solicitada al equipo"), con el estado de cada pieza. ✅ = en el repo o en AWS, verificable. ⏳ = pendiente, con su responsable y su issue.

**Sin secretos:** ningún archivo de esta carpeta contiene tokens, contraseñas, llaves de AWS ni URLs firmadas. Antes de entregar se vuelve a revisar (INT-07 / INT-08), además de gitleaks en el CI.

## Evidencia solicitada

| Evidencia | Dónde | Estado |
|---|---|---|
| Ficha de entrega y README | [`../README.md`](../README.md) | ✅ con los datos del dispositivo de EDGE-01; faltan los comandos del programa del dispositivo (EDGE-08) |
| Identificación del modelo del P3 | [`../docs/linaje-modelo.md`](../docs/linaje-modelo.md), [`../modelo/registros/linaje_verificacion.json`](../modelo/registros/linaje_verificacion.json) | ✅ VAL-01 |
| Variante optimizada | [`../docs/modelo-optimizado.md`](../docs/modelo-optimizado.md), [`../modelo/registros/registro_conversion.json`](../modelo/registros/registro_conversion.json); archivo en `s3://p4-capturas-474665692638/modelos/clasificador-edge/1.0.0-int8-e05.1/` | ✅ |
| Comparación de calidad (predicciones por muestra, accuracy y F1) | Predicciones por muestra del original y del INT8 sobre las 292 de `val`: [`../validacion/resultados/predicciones_val.csv`](../validacion/resultados/predicciones_val.csv), verificador [`../validacion/verificar_predicciones.py`](../validacion/verificar_predicciones.py) y [`../docs/comparacion-modelos.md`](../docs/comparacion-modelos.md) (VAL-02, VAL-03); métricas por clase y errores: [`../validacion/resultados/metricas_val.csv`](../validacion/resultados/metricas_val.csv) y [`../docs/metricas-val.md`](../docs/metricas-val.md) (VAL-04); ⏳ corrida en el dispositivo (VAL-07) | 🟡 |
| Comparación de recursos (tamaños, más de 100 tiempos tras 10 calentamientos, p50/p95) | Tamaños ✅ en la ficha del modelo. Tiempos ✅ en la Raspberry: 10 calentamientos + 200 mediciones del INT8 y del FP32 en [`VAL-05/`](VAL-05/) y [`../docs/benchmark-edge.md`](../docs/benchmark-edge.md) (VAL-05); ⏳ p50/p95 y la comparación formal (Josué, VAL-06) | 🟡 |
| Capturas de operación (20 eventos repartidos entre las clases) | ⏳ Omar, EDGE-07; exportación desde el portal (`/api/p4/capturas/exportar?formato=csv`) | ⏳ |
| Evidencia de AWS | [`../docs/despliegue.md`](../docs/despliegue.md), [`../docs/acceso-evaluacion.md`](../docs/acceso-evaluacion.md), [`../scripts/consultar_captura.py`](../scripts/consultar_captura.py) | ✅ con capturas de prueba ([`int-03/`](int-03/), [`int-05/`](int-05/)); ⏳ falta con capturas del dispositivo (INT-06) |
| Acceso al portal | https://54-80-197-58.sslip.io → Capturas Edge, usuario `evaluador` | ✅ |
| Demostración funcional | Guion: [`../docs/guion-demo.md`](../docs/guion-demo.md); ⏳ simulacro con el dispositivo (INT-08, EDGE-08) | ⏳ |
| Video opcional | ⏳ | ⏳ |

## Requisitos mínimos

| Requisito | Evidencia | Estado |
|---|---|---|
| **M1:** la variante procede del modelo del P3 | Linaje verificado: 20 comprobaciones, 0 fallas (VAL-01); conversión reproducible con SHA-256 de entrada y salida | ✅ listo para mostrar |
| **M2:** clasificación local en un dispositivo físico con cámara | Dispositivo, cámara y modelo verificados en la Raspberry ([`EDGE-01/`](EDGE-01/)), captura física ([`EDGE-02/`](EDGE-02/)), inferencia INT8 local con las tres clases ([`EDGE-03/`](EDGE-03/)) y clasificación con la red desconectada ([`EDGE-04/`](EDGE-04/)) | ✅ |
| **M3:** fotos nuevas en AWS y en Capturas Edge | Receptor y portal desplegados. Con capturas de prueba: persistencia en S3 y reinicio del portal ([`int-03/`](int-03/)), y Capturas Edge con datos de AWS y actualización ([`int-05/`](int-05/)); ⏳ falta una captura del dispositivo seguida por ID hasta S3 y el portal (INT-06) | 🟡 |

## Carpetas

| Carpeta | Issue | Contenido |
|---|---|---|
| [`EDGE-01/`](EDGE-01/) | EDGE-01 (#5) | Hardware y runtime de la Raspberry, foto nueva de la cámara, hash del modelo local y montaje físico |
| [`EDGE-02/`](EDGE-02/) | EDGE-02 | Captura física con la cámara: modo manual, por intervalo, sin red y con error |
| [`EDGE-03/`](EDGE-03/) | EDGE-03 | Inferencia INT8 en la Raspberry con una foto por clase y sus dependencias |
| [`EDGE-04/`](EDGE-04/) | EDGE-04 (#10) | Clasificación local con Wi-Fi y Ethernet desconectados: registros de red antes y después, capturas y su log |
| [`VAL-05/`](VAL-05/) | VAL-05 (#17) | Benchmark en la Raspberry: tiempos crudos (CSV), condiciones del dispositivo y captura de la Terminal |
| [`int-02/`](int-02/) | INT-02 (#4) | Prueba del contrato contra el receptor desplegado: 5 respuestas, consulta en S3 y foto de prueba |
| [`int-03/`](int-03/) | INT-03 (#15) | Captura persistida en S3, recuperada con un usuario de solo lectura y que sobrevive al reinicio del portal |
| `int-04/` | INT-04 (#16) | ⏳ Fallo controlado y reintento con el mismo ID |
| [`int-05/`](int-05/) | INT-05 (#21) | Capturas Edge en el portal desplegado: antes y después de una captura nueva, comparada campo por campo con S3 |
| `int-06/` | INT-06 (#22) | ⏳ Una captura seguida del dispositivo a AWS y al portal |
| `operacion/` | EDGE-07 | ⏳ Exportación de las 20 capturas y prueba de reinicio |
