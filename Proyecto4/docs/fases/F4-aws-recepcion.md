# F4 — Recepción y persistencia en AWS

| Campo | Valor |
|---|---|
| Responsable | Emilio (Líder de AWS · portal · integración) |
| Revisor de PRs | Edith |
| Fechas | 7 oct → 8 oct de 2026 |
| Rama | `feat/p4-fase-4-aws-recepcion` |
| Puntos de rúbrica | 10 (4.1 y 4.2) |
| Depende de | F1 (contrato) |
| Bloquea a | F5, F6 |
| Control | Control 2 |

**Nota de calendario:** arranca el miércoles 7 en cuanto el contrato del evento está escrito, en paralelo a la optimización. El jueves 8 debe haber una imagen de prueba persistida.

> Antes de empezar lee `AGENTS.md`, `docs/decisiones.md` (servicios de AWS) y `docs/contratos.md` (evento y reglas de recepción). Trabaja los bloques en orden.

## Rúbrica (10 puntos)

- **4.1 Evento completo y vinculado (5):** fotografía, ID, fecha con zona horaria, clase, confianza válida, dispositivo, versión optimizada y recorte si aplica; los metadatos locales coinciden con el registro recibido.
- **4.2 Persistencia real en AWS (5):** captura recuperable en el servicio usado, respaldada por una consulta de lectura o un recurso identificado. Una URL pública sola no demuestra AWS.

## Bloques de trabajo

- [x] **Recepción:** recibir fotografía y metadatos según el contrato, reutilizando los servicios existentes. — `POST /api/p4/captures` en el FastAPI del portal ([`src/p4/captures/api.py`](../../src/p4/captures/api.py)); pruebas en [`tests/test_recepcion.py`](../../tests/test_recepcion.py) (16 pasan).
- [x] **Validación del evento:** rechazar o señalar eventos sin zona horaria, con confianza fuera de 0 a 1 o sin versión del artefacto. — [`src/p4/captures/validation.py`](../../src/p4/captures/validation.py): 422 `evento_invalido` con todos los problemas juntos; reloj adelantado más de 5 min se señala (`captured_at_en_el_futuro`) sin rechazar. Pruebas en [`tests/test_validacion.py`](../../tests/test_validacion.py).
- [x] **Persistencia:** guardar imagen y registro; agregar fecha de recepción y clave de la imagen. — [`src/p4/captures/s3_store.py`](../../src/p4/captures/s3_store.py) en `s3://dataset-quality-releases-750702272375/edge-captures/`; registro con `received_at`, `image_key`, `image_bytes`, dimensiones, `delivery_delay_s` y `warnings`. Pruebas en [`tests/test_persistencia.py`](../../tests/test_persistencia.py); captura real `f4-prueba-20261008-0001` (ver Registro de avance).
- [x] **Idempotencia:** un reintento con el mismo ID de captura no crea un duplicado. — `PutObject` con `If-None-Match: *`; reintento idéntico → `200 duplicate` sin escribir; mismo ID con otros datos → `409 conflicto_capture_id`. Pruebas en [`tests/test_idempotencia.py`](../../tests/test_idempotencia.py); reenvío real de `f4-prueba-20261008-0001` → 200 y un solo registro.
- [x] **Consulta de solo lectura:** dejar lista la consulta que el equipo ejecutará en la demostración para mostrar un registro y el recurso de AWS donde vive, sin entregar credenciales. — [`docs/consulta-aws.md`](../consulta-aws.md): `head-object`, `get-object` y SHA-256 recalculado, probados con `p4-emilio` sobre `f4-prueba-20261008-0001`. Con el usuario `dataset-quality-evaluator` no se probó (no hay perfil configurado; ver el mismo documento).
- [x] **Consulta y exportación:** listado ordenado por fecha para el portal y exportación de eventos en CSV o JSON. — `GET /api/p4/captures` (de más reciente a más antigua por `captured_at` en UTC), `GET /api/p4/captures/{id}`, `GET /api/p4/captures/{id}/image` y `GET /api/p4/captures/export?format=csv|json` ([`src/p4/captures/api.py`](../../src/p4/captures/api.py), [`export.py`](../../src/p4/captures/export.py)). Pruebas en [`tests/test_consulta.py`](../../tests/test_consulta.py).

## Reproducir la predicción de la captura de prueba

La clase y la confianza de `f4-prueba-20261008-0001` salen de la variante `1.0.0-int8.1` corrida en **x86**, no en la Pi. Para recalcularlas desde el repo (PowerShell, desde `Proyecto4\`; el entorno necesita `onnxruntime==1.30.0` y `numpy`, como `modelo/requirements-edge.txt`):

```powershell
New-Item -ItemType Directory -Force $env:TEMP\modelo-f4 | Out-Null
aws s3 cp s3://dataset-quality-releases-750702272375/models/clasificador-edge/1.0.0-int8.1/model_int8.onnx $env:TEMP\modelo-f4\ --profile <perfil>
.\.venv\Scripts\python scripts\inferir_captura.py --foto <ruta de la foto> --modelo-dir $env:TEMP\modelo-f4
```

El script exige el SHA-256 `ca689c4e…69c0` del modelo y usa `modelo/preprocess.py` sin modificarlo. Resultado del 9 oct en x86 (onnxruntime 1.30.0): `image_sha256` `c898dd12…2f7a`, cat 0.01698353700339794, **dog 0.8859987854957581**, person 0.09701764583587646: igual, sin redondear, a lo que guarda el registro en S3. En aarch64 las probabilidades del INT8 pueden diferir (aviso de [`artefacto.md`](../artefacto.md)).

## Cómo se cierra

- [x] Una imagen de prueba enviada, guardada y recuperable (`f4-prueba-20261008-0001`: `get-object` devuelve 238 034 bytes con el mismo SHA-256 que la foto)
- [x] El registro recibido coincide con los metadatos enviados (11 de 11 campos, comparación campo por campo)
- [x] El mismo ID enviado dos veces aparece una sola vez (reenvío → `200 duplicate`; `s3 ls` muestra un registro y una imagen; `VersionId` del registro sin cambio)
- [x] Consulta de lectura documentada y probada ([`docs/consulta-aws.md`](../consulta-aws.md), resultado del 9 oct con `p4-emilio`)
- [x] Configuración sin credenciales reales en Git (gitleaks v8.30.1 con `.gitleaks.toml` el 9 oct: `main..HEAD` con los 4 commits de F4 y los cambios en staging sin hallazgos; `Proyecto2/.env` ignorado por `Proyecto2/.gitignore:4`; `.env.example` con `P4_DEVICE_TOKEN` y `P4_AWS_PROFILE` vacíos)
- [ ] PR fusionado con review de Edith
- [ ] Estado de la tarjeta en **Hecho**

## Registro de avance

| Fecha | Quién | Bloque | Qué se hizo / PR | Pendiente |
|---|---|---|---|---|
| 2026-10-08 | Emilio | Recepción | Router `POST /api/p4/captures` (multipart `event` + `image`, token Bearer, JPEG ≤ 5 MB, forma del evento con campos desconocidos rechazados) montado en el portal; compose monta `Proyecto4/src` y `~/.aws` (solo lectura); variables `P4_*` en `.env.example`. 16 pruebas. | Validación semántica (bloque 2); escritura en S3 (bloque 3): hasta entonces responde 503 `receptor_no_configurado`. |
| 2026-10-08 | Emilio | Validación del evento | Reglas del contrato antes de guardar: zona horaria obligatoria, confianza finita en [0, 1], versión aceptada y SHA-256 del modelo que le corresponde, clase `cat`/`dog`/`person`, `image_sha256` igual al de la imagen recibida, formato de `capture_id` y `device_id`, región dentro de la imagen. Aviso `captured_at_en_el_futuro` (sin rechazo) y `delivery_delay_s` informativo. 52 pruebas en total. | Escritura en S3 (bloque 3). |
| 2026-10-08 | Emilio | Persistencia | `S3CaptureStore`: imagen byte por byte con metadatos `sha256` y `capture-id`, después el registro JSON con los campos del receptor; errores de S3 → 503 visible con el código de S3. Receptor real en Docker Compose (`p4-emilio`). Captura `f4-prueba-20261008-0001` enviada el 8 oct 23:53 (-06:00): imagen `edge-captures/images/f4-prueba-20261008-0001.jpg` (VersionId `icZio54eDr2va6q3uSInCXuBD1UWlThQ`, 238 034 bytes, SHA-256 `c898dd12…2f7a` en metadatos e igual al de la foto descargada) y registro `edge-captures/events/f4-prueba-20261008-0001.json` (VersionId `Ti1VGCMyvBfeilNL8XS0Siut6LiSBsgS`, `received_at` `2026-10-09T05:53:22.210+00:00`). 11/11 campos enviados iguales en el registro. **Notas:** la clase y la confianza (dog 0.8859987854957581) salen de la variante `1.0.0-int8.1` corrida en **x86 (laptop), no en la Pi**: en aarch64 las probabilidades pueden variar (`docs/artefacto.md`); `captured_at` es la **hora de guardado del archivo** (la foto no trae EXIF), no la hora real de la toma. Suite de Proyecto2 en el contenedor: 278 pasan. | F10: copiar la evidencia de `C:\MLOps_Project_Four\evidencia_f4\` a la carpeta de evidencias del repo, sin tokens ni rutas sensibles. |
| 2026-10-08 | Emilio | Idempotencia | Escritura condicional `If-None-Match: *` en imagen y registro; comparación de los campos del dispositivo ante un 412 (igual → `200 duplicate`, distinto → `409` con los campos). Reenvío real del mismo evento → `HTTP 200 duplicate` con el `received_at` original; `s3 ls edge-captures/` muestra 1 registro y 1 imagen; el `VersionId` del registro no cambió. 68 pruebas de P4 en total. | Ningún workflow de `.github/` corre todavía `Proyecto4/tests`. |
| 2026-10-09 | Emilio | Consulta de solo lectura | [`docs/consulta-aws.md`](../consulta-aws.md) con los comandos de la demo (identidad, `head-object` y `get-object` de registro e imagen, SHA-256 recalculado y `s3 ls`). Probado con `p4-emilio`: imagen y registro con sus `VersionId`, SHA-256 de la descarga igual al de metadatos y al del registro, un solo registro por ID. Script `scripts/inferir_captura.py` (sin rutas de la máquina) que recalcula la predicción de la captura de prueba: mismo resultado sin redondear. | Probar con `dataset-quality-evaluator`: falta un perfil configurado (decisión del PM; ver `consulta-aws.md`). |
| 2026-10-09 | Emilio | Consulta y exportación | Listado ordenado por `captured_at` en UTC (desempate `received_at`, `capture_id`), paginado de S3, caché de 10 s que se invalida al guardar; registros ilegibles en `errores` (no se esconden). Un registro, su imagen (servida por el portal, sin URL pública) y exportación CSV/JSON con todas las columnas y `confidence` sin redondear. Probado contra S3 real con el receptor en Docker Compose: listado, imagen (mismo SHA-256), CSV, JSON y 404. 88 pruebas de P4. | **Propuesta para el PM (no aplicada):** agregar a `.github/workflows/` un job que corra `pytest` en `Proyecto4/` (hoy ningún workflow corre `Proyecto4/tests`). |
| 2026-10-09 | Emilio | Revisión de Edith (PR de F4) | (1) Si crear el cliente S3 falla (perfil inexistente), el receptor responde 503 visible y lo reintenta en el siguiente envío, como máximo una vez cada 5 s; al corregirse la configuración se recupera sin reiniciar el portal. (2) Tope de 16 KiB a la parte `event` (como texto o como archivo): `413 evento_demasiado_grande` con el formato del contrato; de paso, un multipart mal formado ahora responde `400 solicitud_invalida` con el formato del contrato (antes salía el `detail` genérico de Starlette). Tabla de respuestas de [`contratos.md`](../contratos.md) actualizada. 96 pruebas de P4. | **Pendiente para F5:** al desplegar, los GET de `/api/p4/captures` (listado, registro, imagen y exportación) quedan públicos y pueden mostrar fotos de personas; se resolverá con Caddy y `basic_auth` en todo el portal excepto `POST /api/p4/captures` (protegido con el token del dispositivo). |
