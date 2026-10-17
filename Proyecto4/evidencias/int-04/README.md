# INT-04: idempotencia, fallas y reintento controlado

Dos partes: la falla y el reintento **desde la Raspberry** con una captura física, y el comportamiento del receptor desplegado (duplicado, conflicto, sin sobrescritura) con una captura de prueba.

## Falla y reintento desde el dispositivo

**Captura:** `edge01-211538a088644fe19b3f579367d5b2c8` (`cat` 0.9987), tomada por Omar el 16 oct de 2026 a las 16:34:01 (UTC-06:00) y enviada con el programa de EDGE-06. Su recorrido completo está en INT-06.

**Cómo se provocó la falla:** Omar apagó el Wi-Fi (procedimiento reversible: se vuelve a encender, nada se borra ni se reconfigura). [`telefono-sin-wifi-ni-datos.webp`](telefono-sin-wifi-ni-datos.webp): el teléfono, que da la cámara por USB, con Wi-Fi y datos móviles apagados el viernes 16 oct; la foto no muestra la hora, así que la que vale es la del log.

[`envios-edge06.jsonl`](envios-edge06.jsonl) es el log de envíos que escribió la Raspberry, entregado sin editar (manifiesto con SHA-256; `3b0c826b…c4d9`):

| Hora (UTC-06:00) | Resultado | `capture_id` y hashes |
|---|---|---|
| 17:24:14 | Sin respuesta: "Error de red o timeout; evento local conservado", reintentable | mismo ID; evento `c3e01eb1…94fe`, foto `2f753f34…1250` |
| 17:24:18 | Igual (intento 2) | iguales |
| 17:24:27 | Igual (intento 3) | iguales |
| 17:26:59 | `201 creado`, `received_at` `2026-10-16T23:26:59.521+00:00` | iguales |
| 17:28:43 | `200 duplicado`, con el **mismo** `received_at` | iguales |

[`consulta-s3-edge01.txt`](consulta-s3-edge01.txt): en S3 el evento es igual en sus 11 campos al evento local de la Raspberry, la foto es idéntica byte por byte y hay **una sola versión** del registro y de la foto. Ni las 3 fallas ni el reenvío dejaron duplicados.

| Criterio | Evidencia |
|---|---|
| Procedimiento reversible para provocar la falla | Apagar el Wi-Fi y volver a encenderlo; el procedimiento repetible está [abajo](#procedimiento-en-el-dispositivo) |
| La falla queda visible en el dispositivo | El programa registra cada intento fallido con su motivo: 3 líneas de 17:24 en el log |
| El evento local se conserva | Cada falla dice "evento local conservado", y el mismo evento (`c3e01eb1…`) es el que llegó después a S3 |
| Al restablecer la conectividad se reintenta | 17:26:59 → `201 creado` |
| El reintento usa exactamente el mismo `capture_id` | Los 5 intentos llevan el mismo ID y los mismos SHA-256 de evento y foto |
| AWS contiene un solo registro final y una foto recuperable | Una versión de cada objeto; foto descargada idéntica a la de la Raspberry |
| Repetir exactamente el evento produce `duplicado` | 17:28:43 → `200 duplicado`, sin cambiar `received_at` |

## Receptor desplegado y S3, con una captura de prueba

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

## Procedimiento en el dispositivo

Para repetir la prueba. Es el mismo corte de red de EDGE-04. Opera desde el teclado y la pantalla de la Raspberry, **no por SSH**, porque la sesión se corta al apagar el Wi-Fi. El cable USB al teléfono se queda conectado, porque es el enlace con la cámara.

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

`resultado-receptor.json`, `envios-edge06.jsonl` y las consultas guardan respuestas, no solicitudes ni cabeceras: no contienen el token ni contraseñas. La foto del teléfono no muestra datos personales.
