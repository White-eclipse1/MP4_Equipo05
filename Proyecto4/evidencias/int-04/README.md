# INT-04: idempotencia, fallas y reintento controlado

**Estado: parcial.** La parte del receptor y de AWS ya está probada contra el portal desplegado. La falla de envío y el reintento **desde el dispositivo** se completan cuando el programa de la Raspberry envíe al receptor (EDGE-06), con el [procedimiento](#procedimiento-en-el-dispositivo) de abajo.

## Lo que ya está probado (receptor desplegado y S3)

Prueba del contrato del 16 oct de 2026, 00:59 (UTC-06:00), contra `https://54-80-197-58.sslip.io/api/p4/capturas`, con [`scripts/enviar_prueba.py`](../../scripts/enviar_prueba.py). Usó la captura de prueba `prueba-int-20261016T005939-0001` (`device_id=prueba-int`, foto sintética).

- [`resultado-receptor.json`](resultado-receptor.json): las respuestas del receptor. No incluye las solicitudes ni el token.
- [`consulta-s3.txt`](consulta-s3.txt): la consulta de solo lectura con `p4-lectura`, comparada con el registro local que guardó el script **antes** de enviar.

| Criterio | Evidencia |
|---|---|
| Repetir exactamente el evento produce `duplicado` | Caso 2: `200 duplicado` con el **mismo** `received_at` del primer envío (`2026-10-16T06:59:43.941+00:00`, caso 6). El reintento no escribe nada |
| Reutilizar el ID con otro contenido produce conflicto | Caso 3: `409 conflicto_capture_id`. En `detalles` aparece el campo que cambió: `predicted_class` guardado `dog`, recibido `cat` |
| No se sobrescribe en silencio el registro original | Tras el conflicto, S3 conserva `dog`. Hay **una sola versión** del registro (`1DcpFr826x6U5nXG.k_REtNvphYfEJSI`) y de la foto (`eVpJrcV3ldZfhW86h3_CRWqPhxX0_4fS`); el bucket tiene versionado, así que una sobrescritura dejaría una segunda versión |
| AWS contiene un solo registro final | Una versión por objeto, después de 1 alta, 1 reintento y 1 conflicto |
| AWS contiene una foto recuperable | Se descargó: 18 282 bytes, SHA-256 `aeff07d6…9002`, igual en el archivo, en S3, en el evento y en la foto local |
| El reintento usa el mismo `capture_id` | El reintento mandó el **mismo** evento guardado. Los 11 campos del contrato en S3 son iguales a los del registro local (`evento (11 campos del contrato) igual: True`) |

También lo cubren las pruebas del CI, contra un S3 simulado:

| Prueba | Qué comprueba |
|---|---|
| `test_reintento_identico_es_duplicado_sin_escribir` | El reintento responde `duplicado` y no escribe nada |
| `test_otra_foto_con_el_mismo_id_es_conflicto`, `test_otros_datos_con_el_mismo_id_es_conflicto` | Mismo ID con otra foto u otros datos → conflicto |
| `test_falla_a_la_mitad_se_completa_con_el_reintento` | Si S3 guarda la foto y falla antes del registro, el reintento completa la escritura sin duplicar |
| `test_sin_red_es_no_disponible`, `test_error_de_s3_al_guardar_es_no_disponible` | Si S3 falla, el receptor responde `503`, que es el caso en que el dispositivo **sí** reintenta (contrato) |
| `test_permiso_denegado_es_no_disponible_y_no_conflicto` | Un permiso denegado no se confunde con un conflicto |

## Lo que falta: el dispositivo

| Criterio | Cómo se demuestra |
|---|---|
| Procedimiento reversible para provocar la falla | Definido abajo: cortar la red de la Raspberry y volver a encenderla. Nada se borra ni se reconfigura |
| La falla se ve en el dispositivo | Captura de pantalla del programa con el error de red (paso 2) |
| El evento local se conserva | `ls` y `sha256sum` del JPEG y del JSON locales tras la falla (paso 2) |
| Al volver la red se puede reintentar | Captura de pantalla con `201 creado` (paso 4) |
| El reintento usa exactamente el mismo `capture_id` | `consultar_captura.py --evento-local --foto-local` sobre ese ID → `Resultado: OK` (paso 6) |
| AWS contiene un solo registro y una foto recuperable | La misma consulta: una versión de cada objeto y la foto con el mismo SHA-256 |

## Procedimiento en el dispositivo

Es el mismo corte de red de EDGE-04. Opera desde el teclado y la pantalla de la Raspberry, **no por SSH**, porque la sesión se corta al apagar el Wi-Fi. El cable USB al teléfono se queda conectado, porque es el enlace con la cámara.

**Requisitos:**
- El programa del dispositivo (EDGE-06) guarda el JPEG y el evento antes de enviar y muestra el código de cada respuesta.
- El token está en el `.env` de la Raspberry y nunca se imprime.

**1. Antes de cortar**, comprueba que el portal responde. Debe imprimir `401`, porque el portal pide usuario:

```bash
curl -sS -o /dev/null -w '%{http_code}\n' --max-time 10 https://54-80-197-58.sslip.io/
```

**2. Corta la red y captura:**
- En la Raspberry: `nmcli radio wifi off` y desconecta el Ethernet.
- En el teléfono: apaga el Wi-Fi y los datos móviles, pero deja el anclaje USB e IP Webcam.
- Guarda el estado de la red:

```bash
{ date --iso-8601=seconds; ip -br address; ip route; curl -sS -o /dev/null -w '%{http_code}\n' --max-time 10 https://54-80-197-58.sslip.io/; } > red-cortada.txt 2>&1
```

Toma una foto con el programa. El envío debe fallar **por red**, sin respuesta del receptor, y el error debe verse en pantalla: toma una **captura de pantalla**. Anota el `capture_id` y guarda la prueba de que el registro local sigue ahí:

```bash
ls -l <carpeta de capturas>/<capture_id>.*
sha256sum <carpeta de capturas>/<capture_id>.*
```

**3. Restablece la red:** `nmcli radio wifi on` y vuelve a encender los datos del teléfono si los usa. Repite el comando del paso 2 con `red-restablecida.txt`; esta vez debe imprimir `401`.

**4. Reintenta desde el programa** con el evento guardado, sin generar uno nuevo. Debe responder `201 creado`. Toma una **captura de pantalla**.

**5. Reintenta otra vez** con el mismo evento. Debe responder `200 duplicado`.

**6. En la laptop**, copia el JSON y el JPEG locales de esa captura (por ejemplo con `scp`) y corre:

```bash
python Proyecto4/scripts/consultar_captura.py <capture_id> --profile p4-lectura --evento-local <capture_id>.json --foto-local <capture_id>.jpg
```

Debe terminar en `Resultado: OK`: S3 guardó exactamente el evento y la foto del registro local, con una sola versión de cada objeto. Si el registro local trae campos propios del dispositivo (`estado`, `width`…), no se comparan: solo cuentan los 11 del contrato.

Guarda en esta carpeta `red-cortada.txt`, `red-restablecida.txt`, las capturas de pantalla, la salida de `sha256sum` y la de la consulta.

## Sin secretos

`resultado-receptor.json` y `consulta-s3.txt` no contienen el token ni contraseñas. Las capturas de pantalla del dispositivo no deben mostrar el `.env`.
