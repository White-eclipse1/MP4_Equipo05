# Evidencias del Proyecto 4

Índice de la evidencia que pide la rúbrica ([`docs/rubrica.md`](../docs/rubrica.md), "Entrega solicitada al equipo"), con el estado de cada pieza. ✅ = en el repo o en AWS, verificable. ⏳ = pendiente, con su responsable y su issue.

**Sin secretos:** ningún archivo de esta carpeta contiene tokens, contraseñas, llaves de AWS ni URLs firmadas. Antes de entregar se vuelve a revisar (INT-07 / INT-08), además de gitleaks en el CI.

## Evidencia solicitada

| Evidencia | Dónde | Estado |
|---|---|---|
| Ficha de entrega y README | [`../README.md`](../README.md) | ✅ con los datos del dispositivo de EDGE-01; faltan los comandos del programa del dispositivo (EDGE-08) |
| Identificación del modelo del P3 | [`../docs/linaje-modelo.md`](../docs/linaje-modelo.md), [`../modelo/registros/linaje_verificacion.json`](../modelo/registros/linaje_verificacion.json) | ✅ VAL-01 |
| Variante optimizada | [`../docs/modelo-optimizado.md`](../docs/modelo-optimizado.md), [`../modelo/registros/registro_conversion.json`](../modelo/registros/registro_conversion.json); archivo en `s3://p4-capturas-474665692638/modelos/clasificador-edge/1.0.0-int8-e05.1/` | ✅ |
| Comparación de calidad (predicciones por muestra, accuracy y F1) | Predicciones por muestra del original y del INT8 sobre las 292 de `val`: [`../validacion/resultados/predicciones_val.csv`](../validacion/resultados/predicciones_val.csv), verificador [`../validacion/verificar_predicciones.py`](../validacion/verificar_predicciones.py) y [`../docs/comparacion-modelos.md`](../docs/comparacion-modelos.md) (VAL-02, VAL-03); ⏳ métricas por clase y errores (VAL-04) y corrida en el dispositivo (VAL-07) | 🟡 |
| Comparación de recursos (tamaños, más de 100 tiempos tras 10 calentamientos, p50/p95) | Tamaños ✅ en la ficha del modelo; tiempos ⏳ Josué, VAL-05 y VAL-06 | ⏳ |
| Capturas de operación (20 eventos repartidos entre las clases) | ⏳ Omar, EDGE-07; exportación desde el portal (`/api/p4/capturas/exportar?formato=csv`) | ⏳ |
| Evidencia de AWS | [`../docs/despliegue.md`](../docs/despliegue.md), [`../docs/acceso-evaluacion.md`](../docs/acceso-evaluacion.md), [`../scripts/consultar_captura.py`](../scripts/consultar_captura.py) | ✅ falta con capturas reales |
| Acceso al portal | https://54-80-197-58.sslip.io → Capturas Edge, usuario `evaluador` | ✅ |
| Demostración funcional | Guion: [`../docs/guion-demo.md`](../docs/guion-demo.md); ⏳ simulacro con el dispositivo (INT-08, EDGE-08) | ⏳ |
| Video opcional | ⏳ | ⏳ |

## Requisitos mínimos

| Requisito | Evidencia | Estado |
|---|---|---|
| **M1:** la variante procede del modelo del P3 | Linaje verificado: 20 comprobaciones, 0 fallas (VAL-01); conversión reproducible con SHA-256 de entrada y salida | ✅ listo para mostrar |
| **M2:** clasificación local en un dispositivo físico con cámara | Dispositivo, cámara y modelo verificados en la Raspberry ([`EDGE-01/`](EDGE-01/)); ⏳ Omar: inferencia local, prueba sin red y versión visible (EDGE-02 a EDGE-04) | ⏳ |
| **M3:** fotos nuevas en AWS y en Capturas Edge | Receptor y portal desplegados y probados con la captura de prueba de INT-02; ⏳ falta una captura nueva del dispositivo seguida por ID hasta S3 y el portal (INT-03, INT-05, INT-06) | ⏳ |

## Carpetas

| Carpeta | Issue | Contenido |
|---|---|---|
| [`EDGE-01/`](EDGE-01/) | EDGE-01 (#5) | Hardware y runtime de la Raspberry, foto nueva de la cámara, hash del modelo local y montaje físico |
| [`int-02/`](int-02/) | INT-02 (#4) | Prueba del contrato contra el receptor desplegado: 5 respuestas, consulta en S3 y foto de prueba |
| `int-04/` | INT-04 (#16) | ⏳ Fallo controlado y reintento con el mismo ID |
| `int-06/` | INT-06 (#22) | ⏳ Una captura seguida del dispositivo a AWS y al portal |
| `operacion/` | EDGE-07 | ⏳ Exportación de las 20 capturas y prueba de reinicio |
