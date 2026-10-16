# EDGE-04 — Clasificación local sin Internet

`edge/offline.py` reutiliza la cámara de EDGE-02 y el modelo de EDGE-03. Carga y
verifica el ONNX una sola vez, antes de solicitar la desconexión. Después solicita
dos capturas nuevas sin Internet y una tercera tras reconectar, usando la misma
instancia `Modelo` y sesión CPU. No se realiza ningún envío al portal ni a AWS.

Cada resultado se guarda en `offline.jsonl`, con session_id, PID, timestamp,
capture_id, clase, confianza, logits, probabilidades y versión/hash del modelo.
JPEG y JSON de captura se conservan en `sin_internet/` y `reconectado/`.
Los registros son evidencia local, no eventos para el receptor.

## Preparación

Distribuir `edge/offline.py` a `/home/pi/edge01/app/offline.py` mediante rsync.
Requiere `app/camara.py`, `app/inferencia.py`, `modelo/preprocesar.py`, el binario
local de EDGE-03 y las dependencias ya instaladas en `.venv`.

Usar pantalla y teclado de la Raspberry; una conexión SSH que se corte al apagar
Wi-Fi no permite operar la demostración. Preparar previamente dos entradas de
clases diferentes, sin necesitar buscarlas en Internet durante la prueba.
Se pueden usar imágenes ya abiertas o impresas presentadas a la cámara, anotando
esa condición. La cámara debe generar fotografías nuevas en cada disparo.

## Ejecución

```bash
cd "$HOME/edge01"
source .venv/bin/activate
python -u app/offline.py --modelo modelo/model_int8.onnx --url "http://10.60.188.31:8080/shot.jpg" --salida evidencias/EDGE-04
```

Sustituir la URL si cambia la dirección local de IP Webcam. Esperar a
`MODELO CARGADO`. No cerrar el programa. Apagar Wi-Fi y desconectar Ethernet de
la Raspberry; en el teléfono apagar Wi-Fi y datos móviles manteniendo anclaje USB
e IP Webcam. No desconectar el cable USB: es el enlace local de cámara.

En una segunda Terminal local guardar evidencia antes de pulsar Enter:

```bash
{ date --iso-8601=seconds; ip -br address; ip route; curl --connect-timeout 5 --max-time 10 -I https://example.com; } > "$HOME/edge01/evidencias/EDGE-04/red-sin-internet.txt" 2>&1
```

Guardar evidencia visible de los controles de Wi-Fi/datos del teléfono y red de
la Raspberry. El fallo de curl por sí solo no prueba desconexión completa.
Volver a la primera Terminal, pulsar Enter e introducir la clase conocida de cada
una de las dos escenas. El programa captura al siguiente Enter y clasifica sin
recargar el modelo. Verificar que las clases predichas sean distintas; no alterar
los resultados si el modelo se equivoca.

Al solicitar reconexión, activar Internet y registrar en la segunda Terminal:

```bash
{ date --iso-8601=seconds; ip -br address; ip route; curl --connect-timeout 5 --max-time 10 -I https://example.com; } > "$HOME/edge01/evidencias/EDGE-04/red-reconectada.txt" 2>&1
```

Volver al programa y generar la tercera foto. El session_id y PID deben mantenerse,
y solo debe aparecer una carga del modelo en esa ejecución. Las fases del log son
declaradas por el operador; las pruebas externas de conectividad las respaldan.
Reconectar no activa inferencia remota ni envío automático.

## Evidencia y verificación

Conservar el log, tres JPEG y sus JSON, registros de red y capturas de pantalla
de carga previa al corte, resultados y controles de conectividad. Los resultados
deben persistir aunque no haya forma de enviarlos. La ejecución física debe
respaldarse con los registros y controles de red de la misma sesión.

### Revisión de evidencias recibidas

En `evidencias/EDGE-04/` se recibieron seis JPEG con sus JSON, el log de dos
sesiones completas y un intento fallido, dos registros de red, una comprobación
adicional de acceso externo y seis fotos de Terminal y conectividad.
Se verificó que los seis JPEG son legibles y que sus hashes y fechas
coinciden con los registros de captura e inferencia.

La sesión `603e22c5faf74bf18bd85a3dad4e2e7f` (PID 5347) carga el modelo a las
00:42:08, clasifica cat a las 00:42:24 y dog a las 00:42:36 en la fase declarada
sin Internet, y vuelve a clasificar a las 00:44:04 tras declarar reconexión.
El modelo se carga una sola vez y conserva sesión y proceso. En la última foto,
la clase esperada era cat y el resultado fue dog; se conserva sin corregirlo.

La evidencia de red todavía no acredita toda la secuencia:

- `red-sin-internet.txt` es de las 00:34:24, anterior a las dos sesiones completas.
  Muestra Wi-Fi inactivo, Ethernet desconectado y fallo DNS, pero mantiene ruta
  por defecto al teléfono USB.
- `red-reconectada.txt` es de las 00:43:27, durante la segunda sesión. Muestra
  Wi-Fi activo, pero la conexión HTTPS externa sigue fallando. No prueba acceso
  a Internet restablecido.
- `internet-wifi-verificado.txt` registra HTTP/2 200 a las 00:56:13 usando
  `curl --interface wlan0`. Confirma acceso externo por Wi-Fi en ese momento,
  posterior al final de las sesiones; no se atribuye retroactivamente a las
  capturas de las 00:41 o 00:44.
- Se agregaron dos fotografías de conectividad: el teléfono muestra Wi-Fi y
  datos móviles desactivados, IP Webcam en uso y conexión USB activa. La foto
  del menú de la Raspberry muestra la opción `Turn Off Wireless LAN`, que indica
  radio Wi-Fi habilitada; no demuestra por sí sola asociación ni acceso a Internet.
  El registro de red de las 00:34 sí muestra wlan0 DORMANT.

La evidencia nueva respalda el aislamiento del teléfono. Para documentar una
secuencia completamente correlacionada falta el estado de red de la sesión
utilizada y acceso externo exitoso antes de la captura posterior a reconectar.
Los archivos actuales se conservan como evidencia de los intentos originales.

Prueba local desde `Proyecto4`:

```bash
python -m unittest discover -s edge -p test_offline.py -v
```

Comprueba que la carga precede a la primera interacción y que las tres inferencias
reciben el mismo objeto de modelo. Usa dobles de prueba y no acredita por sí sola
la captura o inferencia offline en el hardware.
