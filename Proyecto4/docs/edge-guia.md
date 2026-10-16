# EDGE-01 a EDGE-06: Raspberry Pi 4 + POCO C65

## Alcance y estado real

Implementación en `edge/dispositivo.py`; preprocesamiento copiado de
`origin/handoff/p4-val-conversion:Proyecto4/modelo/preprocesar.py`.
No sustituye la validación física ni la revisión del PR. Las pruebas locales usan
dobles de cámara/modelo/receptor: no demuestran inferencia real ni recepción en AWS.
Solo se recibieron los tickets EDGE-01 a EDGE-06. Solicitar los textos de EDGE-07
a EDGE-09 antes de definir su alcance o estado.

| Ticket | Preparado en esta rama | Pendiente para cerrar |
|---|---|---|
| EDGE-01 | Hardware/runtime, cámara USB, JPEG, hash local y evidencias visuales recibidos; POCO C65 confirmado por Omar | Commit, publicación del PR y revisión/merge |
| EDGE-02 | Foto HTTP nueva, Enter o intervalo, UUID, fecha con zona, error visible | Varias capturas físicas con POCO C65 |
| EDGE-03 | ONNX local con hash verificado; código de carga CPU, RGB float32 NCHW 224, ImageNet, softmax | Carga e inferencia físicas, contrastar preprocesamiento con responsable VAL, pruebas de las tres clases |
| EDGE-04 | Captura e inferencia sin envío, registro local | Dos objetos nuevos sin Internet con enlace USB local activo |
| EDGE-05 | JPEG y JSON guardados antes de enviar, hashes y vínculo | Revisar eventos reales y conservar evidencia tras fallo de red |
| EDGE-06 | Multipart, token externo, respuestas y reintento del mismo registro | 201 creado, 200 duplicado y conflicto 409 contra receptor real |

## Ficha EDGE-01

Información verificada mediante las salidas de Terminal compartidas por Omar
el 15 de octubre de 2026, después de reinstalar la Raspberry. Se recibieron copias
de los archivos originales en `Proyecto4/evidencias/EDGE-01/` y se revisaron
localmente. Ver el [índice de evidencias](edge01-entrega.md).

| Componente | Configuración |
|---|---|
| Dispositivo | Raspberry Pi 4 Model B Rev 1.5 |
| SO | Debian GNU/Linux 13 (Trixie), DEBIAN_VERSION_FULL=13.7 |
| Arquitectura | ARM64 / aarch64 |
| Python | 3.13.5 |
| ONNX Runtime | 1.31.0 |
| Providers disponibles | AzureExecutionProvider, CPUExecutionProvider; todavía no se demuestra una sesión de inferencia |
| Cámara para esta implementación | POCO C65, confirmado expresamente por Omar; IP Webcam 1.19.0.913, HTTP mediante USB tethering |
| Versión del SO del teléfono reportada | 2.0.208.0 |
| JPEG comprobado | 1920 × 1080, 62 556 bytes, Pillow: imagen legible |
| Entorno virtual | `/home/pi/edge01/.venv` |
| Captura | Prueba manual con curl a /shot.jpg; programa con Enter/intervalo pendiente de validación EDGE-02 |
| Región | Imagen completa, `region: null` |
| device_id | `edge01`, alineado con el handoff del portal |

Omar confirmó expresamente POCO C65, versión del sistema 2.0.208.0 e IP Webcam
1.19.0.913, conexión USB y fotografía correcta. La identificación del modelo se
basa en esa confirmación; la foto del montaje presenta una marca OPPO visible
y por sí sola no corrobora el modelo reportado.

### Verificación física recibida para EDGE-01

- JPEG guardado en `/home/pi/edge01/evidencias/EDGE-01/camara-nueva.jpg` y
  verificado con Pillow. Omar confirmó visualmente que muestra la escena correcta.
- Modelo disponible en `/home/pi/edge01/modelo/model_int8.onnx`; `sha256sum`
  devolvió `ba89ee435ce33e0f0cdd4e8ed84dfb50d74e5a3bc23c32af975085306ca02a12`,
  exactamente el hash de `1.0.0-int8-e05.1`. Acceso local e identidad comprobados;
  no implica que ya se haya ejecutado inferencia.
- Archivos enumerados por Omar: `hardware-runtime.txt`, `camara-nueva.jpg`,
  `captura-verificacion.txt` y `modelo-sha256.txt`.
- `reloj.txt` recibido confirma reloj sincronizado, NTP activo y zona
  America/Mexico_City.
- Configuración y comprobaciones físicas de EDGE-01 completadas según resultados
  y confirmaciones de Omar. Archivos originales y cuatro capturas de Terminal
  recibidos, además de fotografía del montaje e imagen abierta. Identidad de cámara
  confirmada por Omar. Pendiente publicación y revisión/merge del PR. Estado: IN PROGRESS
  hasta completar esos requisitos de entrega.

### Diferencias respecto de la ficha anterior

La variante elegida por Omar y confirmada por el PR #29 en `origin/main` es
`1.0.0-int8-e05.1` con SHA-256
`ba89ee435ce33e0f0cdd4e8ed84dfb50d74e5a3bc23c32af975085306ca02a12`.
La ficha antigua y el registro de linaje anterior a ese PR corresponden a
`1.0.0-int8.1`, hash
`ca689c4e1478ccca7821dffaba8f07886bd9609a8aa3cec7450d9f875fbd69c0`.
Son identidades diferentes: no renombrar una versión para hacerla pasar por la otra.
La plantilla usa la variante nueva. El PR #29 documenta su origen en P3, su
publicación en S3 y verificación de 20 comprobaciones, sin fallas ni pendientes;
también registra la pareja versión/hash en la configuración aceptada del receptor.
Ya no queda pendiente elegir entre ambas variantes: se usa la nueva. Actualizar
el texto antiguo de EDGE-03 para reflejar esa versión. Esto no sustituye comprobar
el archivo local en la Raspberry. Revisión realizada contra `origin/main` después
de `git fetch`; esos commits todavía no se han integrado en esta rama EDGE-01.

EDGE-06 menciona `/api/p4/captures`, pero el contrato implementado y el handoff usan
`/api/p4/capturas`, con partes `evento` y `foto`; este programa sigue ese contrato.

## 1. Preparar la Raspberry

Los siguientes comandos son **Bash en la Raspberry**, desde la raíz del repositorio.
Primero lleva esta rama con sus cambios a la Raspberry mediante tu flujo habitual
de Git o copia de archivos. Si usas Git, debes guardar y subir antes los cambios
desde Windows; un `git pull` no transfiere cambios que aún no se han publicado.

```bash
git switch EDGE-01
cd Proyecto4
python3 -m venv /home/pi/edge01/.venv  # omitir si ese entorno ya existe
source /home/pi/edge01/.venv/bin/activate
python -m pip install -r edge/requirements.txt
cp -n contrato/dispositivo.env.example .env
nano .env
```

En `.env`, pega en privado el token entregado y cambia `P4_CAMERA_URL` por la URL
que funcionó ayer, terminada en `/shot.jpg`. Mantén `P4_DEVICE_ID=edge01` y revisa
modelo/versión/hash contra el archivo recibido. Las rutas se interpretan desde
`Proyecto4`: ejecuta siempre desde esa carpeta, también al reenviar.

```bash
chmod 600 .env
mkdir -p capturas/evidencia modelo
```

Recibe `model_int8.onnx` de tu compañero y cópialo a `Proyecto4/modelo/model_int8.onnx`
(por ejemplo con SCP desde Windows, ajustando host, usuario y ruta de origen).
El PR #29 también documenta el nuevo binario en
`s3://p4-capturas-474665692638/modelos/clasificador-edge/1.0.0-int8-e05.1/model_int8.onnx`,
VersionId `b6mYULAWBVpbLcHvZ2qGG5gGtXZK3zeS`, tamaño 11 295 280 bytes.
Si la Raspberry no tiene acceso autorizado a S3, pide al compañero que descargue
ese objeto y te lo transfiera; el dispositivo no necesita credenciales AWS para
capturar, inferir ni enviar al portal. No descargar el binario antiguo esperando
que tenga el hash nuevo.

```bash
sha256sum modelo/model_int8.onnx
```

Debe coincidir exactamente con el hash del handoff. Si no coincide, detente y
pide el archivo correcto: no adaptes el hash esperado para saltarte la verificación.

## 2. Guardar identificación y verificar cámara (EDGE-01/02)

En el POCO C65: conecta USB a la Raspberry, habilita conexión compartida USB,
inicia el servidor en IP Webcam y permite acceso a la cámara. Usa la dirección
de la interfaz USB que ya probaste; el programa no inicia la app del teléfono.

```bash
{ cat /proc/device-tree/model; echo; cat /etc/os-release; uname -m;
  python --version;
  python -c 'import onnxruntime as o; print(o.__version__); print(o.get_available_providers())';
  date --iso-8601=seconds; timedatectl status;
} | tee capturas/evidencia/hardware.txt
```

Anota el modelo de POCO C65 y versión de la app en la evidencia. Confirma reloj
sincronizado antes de desconectar Internet.

```bash
python -c 'import sys; sys.path.insert(0,"edge"); from dotenv import load_dotenv; load_dotenv(".env"); import os; from dispositivo import obtener_foto; from pathlib import Path; Path("capturas/evidencia/camara.jpg").write_bytes(obtener_foto(os.environ["P4_CAMERA_URL"]))'
```

Presenta un objeto que no estuviera ayer y abre el JPEG en la Raspberry para
comprobarlo visualmente. La app usa la foto física solicitada, sin carpeta precargada.

## 3. Capturar e inferir localmente (EDGE-02/03/05)

```bash
set -o pipefail
python -u edge/dispositivo.py capturar --cantidad 3 2>&1 | tee capturas/evidencia/clases.log
```

El modelo se verifica y carga antes del primer Enter. Presenta un gato, perro y
persona (una entrada conocida por clase), pulsa Enter para cada fotografía nueva.
Guarda los resultados reales aunque una clasificación sea incorrecta; no cambiar
clases/confianzas en el JSON. Comprueba que las predicciones reaccionan a entradas
distintas. Si no reaccionan, no cierres EDGE-03: revisa encuadre, modelo y preprocesamiento.
El código usa el preprocesador del handoff; la equivalencia numérica con P3 queda
por contrastar con VAL, pues P3 usa torchvision y el handoff usa Pillow.

Modo automático opcional (espera de cinco segundos después de cada captura):

```bash
python edge/dispositivo.py capturar --intervalo 5 --cantidad 3
```

Cada captura deja `.jpg`, `.json` del contrato y `.inferencia.json` con logits,
probabilidades y tiempo local de preprocesamiento + inferencia. Ese tiempo excluye
la foto HTTP, carga inicial del modelo y envío. Si falla la inferencia, el JPEG
queda conservado y no se inventa un evento.

## 4. Demostración sin Internet (EDGE-04)

```bash
python -u edge/dispositivo.py capturar --cantidad 2 2>&1 | tee capturas/evidencia/offline.log
```

Espera al mensaje de Enter (modelo ya cargado). En otra terminal local de la
Raspberry desactiva Wi-Fi/Ethernet con los controles habituales; en el POCO C65 apaga
Wi-Fi y datos móviles, conservando conexión compartida USB y el servidor IP Webcam.
Evita hacerlo desde una sesión SSH cuya conexión vayas a cortar; usa consola local
o SSH por el enlace USB que permanece disponible.

**Sin Internet no significa sin enlace a la cámara:** el POCO C65 es una cámara HTTP
local. No desconectes el cable USB ni deshabilites su interfaz. Si el teléfono
desactiva tethering al apagar datos, prueba primero el enlace local y documenta
la limitación; no declares captura offline verificada si se pierde la cámara.

Guarda en la segunda terminal:

```bash
{ date --iso-8601=seconds; ip -br address; ip route;
  curl --connect-timeout 5 --max-time 10 -I https://example.com;
} > capturas/evidencia/estado-offline.txt 2>&1
```

Acompaña esto con evidencia visible de Wi-Fi/datos apagados: un fallo de `curl`
por sí solo no prueba aislamiento. Regresa al programa, presenta dos objetos nuevos
y pulsa Enter para cada captura. Conserva IDs, timestamps, clases y confianzas.
Reconecta Internet al terminar. La inferencia no hace ninguna llamada al portal/AWS.

## 5. Enviar una captura y repetirla (EDGE-06)

Sustituye `<capture_id>` por uno de los eventos reales anteriores. No uses los JSON
de métricas `.inferencia.json` ni archivos de evidencia como evento.

```bash
python edge/dispositivo.py enviar capturas/<capture_id>.json
python edge/dispositivo.py enviar capturas/<capture_id>.json
```

Espera `201 creado` y luego `200 duplicado`. Los intentos quedan en
`<capture_id>.envios.jsonl`, sin token. El JPEG y JSON originales se conservan.
Reintentos automáticos limitados: tres intentos totales, solo red/timeout o 503;
después se sale con error y se puede reenviar manualmente el mismo archivo.
400/401/409/413/415/422 y otros estados se muestran sin reintento automático.
Un 422 por modelo requiere corregir la autorización/identidad con el equipo.
No activar `--enviar` para la demostración offline.

Para verificar 409, crea una **copia** del JSON ya aceptado dentro de `capturas/`
con el mismo capture_id y una confidence diferente pero válida; envía esa copia.
Debe aparecer `409 conflicto_capture_id` una sola vez. Conserva el original y la
copia como evidencia; no alteres ni reintentes la copia para convertirla en otro evento.
Esto es una prueba de conflicto, no una nueva predicción física.

Comparte con tu compañero el `capture_id` aceptado y pídele comprobar foto,
predicción y versión en el portal. No hace falta compartir tokens ni `.env`.

## Evidencias y entrega

Las capturas se ignoran en Git. Revisa imágenes y logs antes de compartirlos por
el medio privado del equipo. Adjunta a cada ticket solo su evidencia pertinente:
hardware/cámara (01), fotos nuevas e IDs distintos (02), versión/hash/logits por
clase (03), aislamiento y dos objetos (04), JPEG/JSON/hashes correspondientes (05),
201/200/409 y persistencia ante fallo de red (06). Para demostrar esta última,
intenta enviar un evento offline y confirma que sigue pudiendo enviarse al volver.

No adjuntar `.env`, tokens, contraseñas, URLs con credenciales ni credenciales AWS.
No marcar tickets como DONE hasta completar sus pruebas físicas y revisión/merge
cuando el ticket lo exige. Esta rama todavía no contiene evidencia física nueva.

Pruebas del cliente, sin red ni modelo:

```bash
python -m unittest discover -s edge -p 'test_*.py' -v
```

## Alineación con el guion de demo del PR #31

Revisado contra `origin/feat/p4-int-08-readme:Proyecto4/docs/guion-demo.md`.
Ese guion aún no está en `origin/main` al momento de esta revisión. Los comandos
siguientes se ejecutan desde `Proyecto4`, con el entorno activado y `.env` preparado.
Son instrucciones pendientes de ejecutar físicamente; no constituyen evidencia.

| Paso del guion | Operación del cliente |
|---|---|
| 1 | Al arrancar muestra versión, hash real del modelo, runtime, provider y device_id |
| 2 | Muestra clase, confianza y tiempo local; confirma rutas del JPEG y JSON guardados |
| 3 | Cargar modelo, quitar Internet conservando USB, capturar e intentar enviar; error visible |
| 4 | Restablecer Internet y generar una captura nueva con envío |
| 7 | Fallo controlado, restaurar conectividad y reenviar el JSON original |
| 8 | Cerrar y abrir el programa; conserva archivos y genera una captura nueva |

**Pasos 1 y 2:**

```bash
python -u edge/dispositivo.py capturar --cantidad 3
```

**Paso 3:** iniciar con Internet y esperar Enter para asegurar que el modelo está
cargado. Después quitar Internet según la sección 4 de esta guía, mantener USB/IP
Webcam, presentar un objeto nuevo y pulsar Enter:

```bash
python -u edge/dispositivo.py capturar --enviar
```

La foto y el evento quedan guardados antes del intento. Después de agotar los
reintentos de red, el programa termina con error visible. El guion deja esa captura
offline guardada sin subirla después. Es distinta de la captura que se recupera
del fallo controlado en el paso 7.

**Paso 4:** restablecer Internet y ejecutar de nuevo el comando anterior para una
captura nueva. Leer el capture_id de la respuesta 201/200 al equipo.

**Paso 7:** se puede provocar el fallo sin cambiar `.env` ni desconectar la cámara.
Usar esta URL HTTPS de loopback solo para ese proceso (el puerto 1 debe estar
cerrado; no se envía a un servidor externo):

```bash
P4_RECEPTOR_URL=https://127.0.0.1:1/api/p4/capturas python -u edge/dispositivo.py capturar --enviar
```

El valor temporal tiene precedencia sobre `.env`. Anotar el capture_id guardado.
El siguiente comando vuelve a usar la URL normal de `.env`, siempre que no haya
una variable `P4_RECEPTOR_URL` exportada en la terminal. Verificar la URL sin
mostrar el token si tienes dudas. Reenviar exactamente ese registro y repetir:

```bash
python edge/dispositivo.py enviar capturas/<capture_id-del-paso-7>.json
python edge/dispositivo.py enviar capturas/<capture_id-del-paso-7>.json
```

Esperar 201 creado y luego 200 duplicado. Diego comprueba la única captura en el
portal/S3. No usar el JSON de otra foto ni regenerar el evento.

**Paso 8:** ejecutar otra vez `python -u edge/dispositivo.py capturar --enviar`.
Se vuelven a mostrar identidad y runtime; los JPEG, eventos y registros de envío
anteriores permanecen en `capturas/`. El cliente no tiene una pantalla de historial:
los archivos se consultan desde esa carpeta.
