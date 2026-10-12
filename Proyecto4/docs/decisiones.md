# Decisiones técnicas — Proyecto 4

Se cierran en el kickoff de F1 (miércoles 7 de octubre). Cada líder escribe las suyas; el PR lo abre Edith y lo revisa Bryan. No incluyas contraseñas, claves ni tokens.

Estado: **cerrada** / **pendiente de dato**. Mientras una decisión esté pendiente, la fase que depende de ella no marca sus casillas.

| # | Decisión | Responsable | Fecha | Estado | Desbloquea |
|---|---|---|---|---|---|
| 1 | Formato y runtime del modelo en el dispositivo | Edith y Bryan | | pendiente | F2, F3 |
| 2 | Técnica y objetivo de optimización | Edith | | pendiente | F2, F7, F8 |
| 3 | Datos de comparación de calidad | Edith | | pendiente | F7 |
| 4 | Modo de captura | Bryan | | pendiente | F3, F9 |
| 5 | Servicios de AWS | Emilio | 8 oct | cerrada | F4, F5 |
| 6 | Ubicación de Capturas Edge en el portal | Emilio | 8 oct (URL y acceso: 9 oct) | cerrada | F5 |
| 7 | Hardware y entorno del dispositivo | Bryan | | pendiente | F3, F8 |
| 8 | Qué cabe en Git y qué se distribuye por enlace | Edith y Emilio | | pendiente | F2, F10 |

## 1. Formato y runtime

- Formato del artefacto optimizado (por ejemplo ONNX, TFLite, TorchScript u otro):
- Runtime en el dispositivo y versión:
- Por qué es compatible con el hardware de la decisión 7:

## 2. Técnica y objetivo de optimización

- Técnica (cuantización, poda, destilación u otra):
- Precisión resultante:
- Objetivo medible (tamaño, latencia o memoria) y por qué importa en este hardware:
- ¿Requiere calibración? Si sí, solo con muestras de entrenamiento del P3; el manifiesto de IDs se guarda en F2.

## 3. Datos de comparación de calidad

- Conjunto (validación del Proyecto 3, con el manifiesto y las etiquetas del P3):
- Manifiesto y hash de origen:
- Confirmación de que el test no se usa para calibrar ni ajustar:

## 4. Modo de captura

- Por botón o por intervalo:
- Un objeto por captura; ¿recorte fijo? (sí/no, y cuál):
- Resolución de captura:

## 5. Servicios de AWS

**Decisión:** reutilizar el bucket S3 de releases del P2/P3 con un prefijo nuevo y recibir los eventos en el FastAPI del portal existente. Sin servicios nuevos de AWS (la rúbrica no los exige) y sin recursos con costo fijo.

- **Cuenta y región:** `750702272375`, `us-east-1` (las de `Proyecto3/docs/almacenamiento.md`).
- **Dónde se guarda la imagen y el registro:** `s3://dataset-quality-releases-750702272375/edge-captures/` (versionado, cifrado SSE, sin acceso público, por Terraform en `Proyecto2/terraform/modules/s3`):

  ```
  edge-captures/images/{capture_id}.jpg     fotografía, bytes tal cual llegaron
                                            metadatos S3: sha256, capture-id
  edge-captures/events/{capture_id}.json    registro: evento + campos del servidor
  ```

  El `capture_id` va en la llave porque la idempotencia es una escritura condicional sobre una llave exacta. Nunca se sobrescribe ni se borra; la regla del bucket que expira versiones no actuales a los 90 días no afecta a objetos que no se reemplazan.
- **Cómo recibe el dispositivo:** `POST /api/p4/captures` (multipart, token Bearer) en el FastAPI del portal (`Proyecto2/src/dataset_quality/main.py`), con un router de `Proyecto4/src/p4/` montado igual que los de P3. El contrato completo está en [`contratos.md`](contratos.md). El mismo router sirve el listado, la imagen y la exportación a Capturas Edge (F5).
- **Idempotencia:** `PutObject` con `If-None-Match: *`, primero la imagen y después el registro. Si la llave ya existe (HTTP 412 de S3), se compara lo guardado con lo recibido: igual → `200 duplicate` sin escribir; distinto → `409 conflicto_capture_id` con los campos que difieren. Nunca se sobrescribe ni se responde 2xx a un conflicto. Una falla a la mitad (imagen escrita, registro no) se completa con el reintento del mismo ID; un registro nunca apunta a una imagen inexistente.
- **Listado ordenado:** `ListObjectsV2` de `events/` y `GetObject` en paralelo, ordenado por `captured_at` en UTC (más reciente primero; desempate `received_at`, `capture_id`), con caché en memoria de unos 10 s. Con el volumen esperado (menos de 300 eventos) son centavos y menos de un segundo. Si creciera, se agrega un índice `edge-captures/by-date/{captured_at_utc}_{capture_id}` que S3 lista en orden lexicográfico (no implementado).
- **Credenciales del receptor (sin llaves en Git):**
  - Si `P4_AWS_PROFILE` tiene valor, boto3 usa ese perfil de `~/.aws`. **Solo para desarrollo local:** compose monta `~/.aws` en solo lectura, igual que en `p3-inference`.
  - Si `P4_AWS_PROFILE` está vacío, boto3 usa la cadena estándar de credenciales (variables de entorno, rol de instancia, rol de tarea). Es el modo del despliegue: **en producción, nada de llaves personales**, el permiso viene de un rol.
  - Permisos que necesita el receptor: `s3:PutObject` y `s3:GetObject` sobre `edge-captures/*`, y `s3:ListBucket` con prefijo `edge-captures/`. No necesita `DeleteObject`.
- **Identidad del dispositivo:** `device_id` en el evento y un token compartido (`P4_DEVICE_TOKEN`) en el header `Authorization`. El token vive en `Proyecto2/.env` y en una variable de entorno de la Pi, nunca en Git. El dispositivo **no** tiene credenciales de AWS: solo habla con el receptor.
- **Consulta de solo lectura para la demostración:** el equipo la ejecuta en vivo con `aws s3api head-object` y `get-object` sobre `edge-captures/events/{id}.json` e `edge-captures/images/{id}.jpg` (llave, `VersionId`, `LastModified`, `sha256` y contenido). Alternativa: el usuario `dataset-quality-evaluator`, que ya tiene solo lectura sobre el bucket. Nunca se entregan llaves. Los comandos exactos se documentan en F4 (bloque de consulta de solo lectura).

## 6. Ubicación de Capturas Edge

- **Entrada del menú y ruta:** entrada `Capturas Edge` (`id: 'edge-captures'`) en la lista `PAGES` de `Proyecto2/web/src/App.tsx`, después de `Inference` y antes de `Settings`; ruta `#/edge-captures`. Es el mismo portal de P2 y P3 (la app web de P2 con las páginas de P3).
- **Imágenes:** las sirve `GET /api/p4/captures/{id}/image`, que las lee de S3 del lado del servidor. El navegador no recibe URLs públicas ni credenciales.
- **Dónde está desplegado el portal (URL) y quién lo administra:** **`https://174-129-84-80.sslip.io`** (Capturas Edge en `#/edge-captures`; MLflow en `https://mlflow.174-129-84-80.sslip.io`). EC2 `i-0348c123c4c126267` (t3.medium, us-east-1) con IP elástica `174.129.84.80`, Docker Compose (`Proyecto2/docker-compose.prod.yml`) y Caddy con HTTPS de Let's Encrypt; rol de instancia `p4-portal-ec2`, sin llaves personales. Lo administra Emilio; los permisos los gestiona el PM (Sebastián). Guía: [`despliegue.md`](despliegue.md). P1 **no** se despliega (confirmado con el PM el 9 oct): solo el portal de P2 y P3 con Capturas Edge.
- **Acceso limitado para el evaluador:** usuario y contraseña de Caddy (`basic_auth`) en **todo** el portal (web, API, imágenes, exportación y MLflow), **excepto** `POST /api/p4/captures`, que usa el dispositivo y está protegido por su token (`P4_DEVICE_TOKEN`). Confirmado con el PM el 9 oct. El usuario es `evaluador`; la contraseña se entrega por un canal privado y solo su hash bcrypt vive en la EC2 (`/opt/p4/secretos/caddy.env`, 600, root). El evaluador no recibe llaves de AWS.

## 7. Hardware y entorno del dispositivo

- Dispositivo y cámara (modelo):
- Sistema operativo y versión:
- Runtime y versiones:
- Prueba realizada el 7 de oct (cámara captura, el runtime carga el modelo original o una entrada conocida):

## 8. Qué cabe en Git

- Pesos del original del P3 y de la variante: enlace de descarga y SHA-256, o en el repositorio:
- Dónde se alojan los artefactos grandes:
- Dónde queda la carpeta de evidencias (F10):

## Referencia del modelo del Proyecto 3

Se llena en F1 (Edith). Sin esto no hay continuidad demostrable (M1, 1.1).

| Dato | Valor |
|---|---|
| Versión del modelo publicada | |
| Run ID de MLflow | |
| Ubicación de los pesos y SHA-256 | |
| Clases y orden | |
| Preprocesamiento (tamaño, normalización, orden de canales) | |
| Entrada conocida con clase esperada | |
