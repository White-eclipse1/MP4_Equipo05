# Contratos — Proyecto 4

Estado: **definido** (Emilio, 8 oct de 2026). Bryan lo implementa en F3 (ver [Para Bryan (F3)](#para-bryan-f3)). Cualquier cambio de forma va explícito en el PR, sube `schema_version` y se avisa al equipo.

## Evento de captura (`schema_version` 1)

Lo produce el dispositivo (F3), lo recibe y persiste AWS (F4) y lo muestra Capturas Edge (F5). Dónde y cómo se guarda: [`decisiones.md` §5](decisiones.md#5-servicios-de-aws).

### Cómo viaja

`POST /api/p4/captures` en el portal, con `multipart/form-data` y dos partes:

| Parte | Contenido |
|---|---|
| `event` | Campo de texto con el JSON del evento (tabla de abajo), máximo 16 KiB (16 384 bytes); el evento real pesa menos de 1 KB. |
| `image` | Archivo JPEG (`image/jpeg`), máximo 5 MB. Son los bytes de la fotografía tal como se guardaron en el dispositivo. |

Header obligatorio: `Authorization: Bearer <P4_DEVICE_TOKEN>`. El token vive en una variable de entorno del dispositivo y en el `.env` del portal; nunca en Git ni en el chat.

### Campos que envía el dispositivo

Todos son obligatorios salvo `region`. Un campo que no esté en esta tabla se rechaza (422), para que un error de tipeo no pase en silencio.

| Campo | Tipo | Regla |
|---|---|---|
| `schema_version` | entero | Vale `1`. |
| `capture_id` | texto | ID único de la captura y clave de idempotencia. `^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$` (sin `/` ni espacios). Formato sugerido: `{device_id}-{YYYYMMDDTHHMMSS}-{seq:04d}`. |
| `captured_at` | texto | ISO 8601 **con offset** (`Z` o `±HH:MM`), por ejemplo `2026-10-09T15:30:12-06:00`. Sin zona horaria se rechaza. |
| `predicted_class` | texto | `cat`, `dog` o `person` (clases del modelo del P3, en ese orden de salida). |
| `confidence` | número | Entre 0 y 1, ambos incluidos. Se rechazan valores fuera de rango, `NaN`, booleanos y texto. |
| `device_id` | texto | Identidad configurable del dispositivo. `^[A-Za-z0-9._-]{1,64}$`. |
| `model_version` | texto | Versión del artefacto optimizado cargado. Debe ser una versión aceptada por el receptor; hoy solo `1.0.0-int8.1` ([`artefacto.md`](artefacto.md)). |
| `model_sha256` | texto | SHA-256 de la variante cargada (64 hex en minúsculas), el mismo que muestra el programa al arrancar. Debe corresponder a `model_version`: para `1.0.0-int8.1` es `ca689c4e1478ccca7821dffaba8f07886bd9609a8aa3cec7450d9f875fbd69c0`. |
| `image_ref` | texto | Ruta de la fotografía en el dispositivo (registro local). |
| `image_sha256` | texto | SHA-256 de los bytes del JPEG enviado (64 hex en minúsculas). El receptor lo recalcula y debe coincidir: vincula los metadatos locales con la imagen recibida. |
| `region` | objeto o `null` | Región clasificada si hay recorte: `{"x", "y", "width", "height"}`, enteros en píxeles de la fotografía, `x, y ≥ 0`, `width, height > 0`, dentro de la imagen. `null` u omitido si no hay recorte. |

### Campos que agrega el receptor

No los envía el dispositivo; se guardan en el registro de S3.

| Campo | Tipo | Regla |
|---|---|---|
| `received_at` | texto | Cuándo recibió el portal el evento, ISO 8601 en UTC con offset (`+00:00`). |
| `image_key` | texto | Llave del objeto con la fotografía: `edge-captures/images/{capture_id}.jpg`. |
| `image_bytes` | entero | Tamaño de la fotografía. |
| `image_width`, `image_height` | enteros | Dimensiones de la fotografía en píxeles. |
| `delivery_delay_s` | número | `received_at − captured_at` en segundos. Informativo: el dispositivo clasifica sin red y puede enviar mucho después de capturar, y eso es normal. |
| `warnings` | lista de texto | Avisos que no rechazan el evento. Hoy solo `captured_at_en_el_futuro`: `captured_at` es más de 5 minutos posterior a `received_at` (reloj del dispositivo adelantado). Una captura que llega tarde **no** genera aviso. |

### Ejemplo válido

```json
{
  "schema_version": 1,
  "capture_id": "edge01-20261009T153012-0007",
  "captured_at": "2026-10-09T15:30:12-06:00",
  "predicted_class": "dog",
  "confidence": 0.9309,
  "device_id": "edge01",
  "model_version": "1.0.0-int8.1",
  "model_sha256": "ca689c4e1478ccca7821dffaba8f07886bd9609a8aa3cec7450d9f875fbd69c0",
  "image_ref": "capturas/edge01-20261009T153012-0007.jpg",
  "image_sha256": "<sha256 de los bytes del jpg>",
  "region": null
}
```

Registro guardado en `edge-captures/events/edge01-20261009T153012-0007.json`: los campos anteriores más `received_at`, `image_key`, `image_bytes`, `image_width`, `image_height`, `delivery_delay_s` y `warnings`.

### Respuestas

Los errores siempre tienen la forma `{"error": "<código>", "mensaje": "<texto>", "detalles": [{"campo": "...", "problema": "..."}]}`.

| Caso | HTTP | Respuesta |
|---|---:|---|
| Evento nuevo guardado | 201 | `{"status": "created", "capture_id", "image_key", "record_key", "received_at", "warnings"}` |
| Reintento idéntico (mismo `capture_id`, mismos campos e imagen) | 200 | `{"status": "duplicate", ...}` con el `received_at` original; no se escribe nada |
| Mismo `capture_id` con otros datos o con otra imagen | 409 | `conflicto_capture_id`: "El capture_id ya existe con otros datos", con cada campo distinto (guardado contra recibido) en `detalles`. No se sobrescribe |
| Sin token o token incorrecto | 401 | `no_autorizado` |
| Falta la parte `event` o `image`, el multipart está mal formado o el JSON no es válido | 400 | `solicitud_invalida`, por ejemplo "Falta la parte 'image'" |
| `captured_at` sin zona (`2026-10-09T15:30:12`) | 422 | `evento_invalido`: "captured_at debe incluir zona horaria (ej. -06:00)" |
| `confidence` fuera de [0, 1] (`1.2`) | 422 | `evento_invalido`: "confidence debe estar entre 0 y 1; llegó 1.2" |
| Sin `model_version` | 422 | `evento_invalido`: "model_version es obligatorio" |
| Versión no aceptada, o `model_sha256` que no corresponde a la versión | 422 | `evento_invalido`: "model_sha256 no corresponde a 1.0.0-int8.1" |
| `predicted_class` fuera de las clases (`bird`) | 422 | `evento_invalido`: "predicted_class debe ser cat, dog o person" |
| `image_sha256` distinto del de la imagen recibida | 422 | `evento_invalido`: "image_sha256 no coincide con la imagen recibida" |
| Campo desconocido o `region` fuera de la imagen | 422 | `evento_invalido` con el campo en `detalles` |
| La imagen no es JPEG | 415 | `imagen_no_soportada` |
| La parte `event` pasa de 16 KiB (16 384 bytes) | 413 | `evento_demasiado_grande`: "La parte 'event' pasa de 16384 bytes; el evento del contrato pesa menos de 1 KB" |
| La imagen pasa de 5 MB | 413 | `imagen_demasiado_grande` |
| S3 no responde o el receptor no está configurado (sin bucket, sin token o perfil de AWS que no se pudo cargar) | 503 | `almacenamiento_no_disponible` / `receptor_no_configurado`: "Reintenta con el mismo capture_id". Si falló la creación del cliente S3, el receptor la vuelve a intentar en el siguiente envío, como máximo una vez cada 5 s, sin reiniciar el portal |

**Reintentos:** el dispositivo reintenta **solo** ante 503 o un error de red (sin respuesta, timeout), siempre con el mismo evento y el mismo `capture_id`. Un 4xx no se reintenta: se muestra el error y se corrige. El reintento es seguro: si el primer envío sí llegó, la respuesta es `200 duplicate`.

### Lectura (portal y exportación)

| Endpoint | Qué devuelve |
|---|---|
| `GET /api/p4/captures?limit=N` | Registros ordenados por `captured_at` (UTC), de más reciente a más antigua |
| `GET /api/p4/captures/{capture_id}` | Un registro (404 si no existe) |
| `GET /api/p4/captures/{capture_id}/image` | La fotografía, leída de S3 por el servidor |
| `GET /api/p4/captures/export?format=csv\|json` | Exportación de todos los eventos con los campos del contrato (en CSV, `region` va en `region_x`, `region_y`, `region_width` y `region_height`) |

## Reglas de recepción (F4)

1. La fotografía y los metadatos llegan juntos y se guardan: imagen en `edge-captures/images/`, registro con `received_at` e `image_key` en `edge-captures/events/`.
2. Un evento sin zona horaria, con confianza fuera de 0 a 1 o sin versión del artefacto se rechaza con un error explícito; nunca se persiste en silencio como válido.
3. Un reintento con el mismo `capture_id` no crea un duplicado (`PutObject` con `If-None-Match: *`). Si trae otros datos, responde 409 y no sobrescribe.
4. El listado para el portal sale ordenado de más reciente a más antigua.
5. Hay exportación de eventos en CSV y JSON con los campos del evento.
6. Credenciales del receptor: si `P4_AWS_PROFILE` tiene valor, se usa ese perfil (solo en desarrollo local); si está vacío, boto3 usa la cadena estándar (rol de instancia o de tarea en el despliegue). En producción no hay llaves personales.

## Para Bryan (F3)

Lo que el programa del dispositivo necesita para cumplir este contrato:

1. **`capture_id`:** único por captura y estable en los reintentos. Formato sugerido: `{device_id}-{YYYYMMDDTHHMMSS}-{seq:04d}`, solo con caracteres `A-Z a-z 0-9 . _ -`.
2. **`device_id`:** configurable (variable de entorno o archivo de configuración), por ejemplo `edge01`.
3. **Reloj y zona horaria:** sincronizar la hora por NTP antes de la demo (la Pi no tiene reloj de hardware) y generar la fecha con offset: `datetime.now().astimezone().isoformat(timespec="seconds")`. Enviar tarde es normal; un reloj adelantado más de 5 minutos deja el aviso `captured_at_en_el_futuro`.
4. **Fotografía en JPEG**, máximo 5 MB, y enviar los mismos bytes que se guardaron localmente.
5. **`image_sha256`:** `hashlib.sha256(bytes_del_jpg).hexdigest()`.
6. **Recorte:** si hay recorte fijo (decisión 4), enviar `region` en píxeles de la fotografía; si no, `null`.
7. **Modelo:** `model_version` y `model_sha256` del artefacto realmente cargado (los que imprime al arrancar).
8. **Token:** leer `P4_DEVICE_TOKEN` de una variable de entorno; nunca escribirlo en el código ni en Git. Emilio lo comparte por un canal privado.
9. **Reintentos:** solo ante 503 o error de red, con el mismo `capture_id`; mostrar el error en pantalla (sin reintentos silenciosos). Un 4xx se muestra y no se reintenta. El registro local se conserva aunque el envío falle.

Ejemplo mínimo del envío desde la Pi (solo referencia; el código de F3 es de Bryan):

```python
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path

import requests

URL = os.environ["P4_RECEIVER_URL"]      # p. ej. http://<host-del-portal>:8000/api/p4/captures
TOKEN = os.environ["P4_DEVICE_TOKEN"]    # nunca en el código ni en Git


def construir_evento(capture_id, clase, confianza, ruta_jpg, model_version, model_sha256):
    datos = Path(ruta_jpg).read_bytes()
    return {
        "schema_version": 1,
        "capture_id": capture_id,
        "captured_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "predicted_class": clase,
        "confidence": float(confianza),
        "device_id": os.environ.get("P4_DEVICE_ID", "edge01"),
        "model_version": model_version,
        "model_sha256": model_sha256,
        "image_ref": str(ruta_jpg),
        "image_sha256": hashlib.sha256(datos).hexdigest(),
        "region": None,
    }


def enviar(evento, ruta_jpg):
    """Un intento. Devuelve (ok, mensaje). El reintento lo pide la persona,
    llamando otra vez con el MISMO evento (mismo capture_id)."""
    try:
        r = requests.post(
            URL,
            headers={"Authorization": f"Bearer {TOKEN}"},
            data={"event": json.dumps(evento)},
            files={"image": (Path(ruta_jpg).name, Path(ruta_jpg).read_bytes(), "image/jpeg")},
            timeout=15,
        )
    except requests.RequestException as e:
        return False, f"Sin respuesta del receptor ({e}); reintenta con el mismo capture_id"
    if r.status_code in (200, 201):
        return True, r.json()["status"]                    # "created" o "duplicate"
    error = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    reintentable = r.status_code == 503
    return False, f"HTTP {r.status_code} {error.get('error')}: {error.get('mensaje')}" + (
        " (reintenta con el mismo capture_id)" if reintentable else " (no reintentar: corregir)"
    )
```

Guarda el evento (JSON) junto a la foto en el registro local **antes** de enviarlo, y vuelve a leer ese mismo JSON para el reintento: así el `captured_at` y el `capture_id` no cambian.

## Comportamiento del dispositivo ante fallos (F3, F6, F9)

1. El registro local (imagen y evento) se conserva aunque el envío falle.
2. El error se muestra en el dispositivo y el reintento manual reutiliza el mismo `capture_id`.
3. Reiniciar el programa no borra el historial local.

## Modelo y paquete de entrada

Lo define el paquete del modelo del Proyecto 3 y lo reutilizan F2, F3 y F7; no se redefine aquí.

- Orden de clases, tamaño de entrada, canales, normalización y orden RGB/BGR: los del modelo original (`Proyecto3/docs/modelo.md`).
- Si la variante cuantiza la entrada, la cuantización queda documentada en la ficha del artefacto (F2) y el dispositivo la aplica igual (F3).

## Registros que se comparan entre fases

| Registro | Lo produce | Lo consume | Contenido mínimo |
|---|---|---|---|
| Registro de conversión | F2 | F3, F7, F10 | Archivo de entrada y de salida con SHA-256, técnica, configuración, versiones. |
| Predicciones por muestra | F7 | F3 (entradas conocidas), F10 | Identificador, clase real, clase del original, clase del optimizado. |
| Tiempos por repetición | F8 | F10 | Variante, número de repetición, milisegundos de preprocesamiento más inferencia; calentamiento identificado y excluido. |
| Exportación de eventos | F4, F9 | F10, F11 | Campos del evento de captura. |
