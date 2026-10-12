"""`/api/p4/captures`: recepcion y consulta de capturas del dispositivo (F4, `docs/contratos.md`).

`POST` multipart con dos partes, `event` (JSON) e `image` (JPEG), y el header
`Authorization: Bearer <P4_DEVICE_TOKEN>`. Cada rechazo responde con
`{error, mensaje, detalles}` y el codigo HTTP del contrato: nada se descarta en
silencio.
"""

from __future__ import annotations

import hmac
import threading
import time
from datetime import UTC, datetime
from typing import Annotated, Literal

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError
from fastapi import APIRouter, Depends, Path, Query, Request
from fastapi.responses import JSONResponse, Response
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile
from starlette.exceptions import HTTPException
from starlette.formparsers import MultiPartException

from p4.captures import export
from p4.captures.errors import CaptureError
from p4.captures.event import CaptureEvent, parse_event
from p4.captures.image import ReceivedImage, inspect_image
from p4.captures.s3_store import S3CaptureStore, UnavailableStore
from p4.captures.settings import CaptureSettings, get_settings
from p4.captures.store import CaptureStore
from p4.captures.validation import validate_event

router = APIRouter(prefix="/api/p4/captures", tags=["p4-captures"])


SettingsDep = Annotated[CaptureSettings, Depends(get_settings)]


# Pausa minima entre intentos de crear el cliente S3 cuando fallo (perfil inexistente,
# credenciales aun no montadas): no se reintenta en cada peticion, pero tampoco hace
# falta reiniciar el portal cuando se corrige la configuracion.
STORE_RETRY_S = 5.0
_StoreKey = tuple[str, str, str | None, str]
_stores: dict[_StoreKey, CaptureStore] = {}
_failures: dict[_StoreKey, tuple[float, UnavailableStore]] = {}
_stores_lock = threading.Lock()
_clock = time.monotonic  # sustituible en pruebas


def reset_stores() -> None:
    with _stores_lock:
        _stores.clear()
        _failures.clear()


def _s3_store(bucket: str, prefix: str, profile: str | None, region: str) -> CaptureStore:
    """Cliente S3 compartido. Si crearlo falla, 503 visible y nuevo intento tras `STORE_RETRY_S`."""
    key = (bucket, prefix, profile, region)
    with _stores_lock:
        if key in _stores:
            return _stores[key]
        failed = _failures.get(key)
        if failed is not None and _clock() - failed[0] < STORE_RETRY_S:
            return failed[1]
        # Perfil vacio = cadena estandar de boto3 (rol de instancia en el despliegue).
        try:
            session = boto3.Session(profile_name=profile)
            client = session.client(
                "s3",
                region_name=region,
                config=Config(retries={"max_attempts": 3, "mode": "standard"}),
            )
        except BotoCoreError as error:
            store = UnavailableStore(
                f"perfil de AWS {profile!r} no disponible ({type(error).__name__}); "
                f"se reintenta en {STORE_RETRY_S:g} s"
            )
            _failures[key] = (_clock(), store)
            return store
        _failures.pop(key, None)
        _stores[key] = S3CaptureStore(client, bucket, prefix)
        return _stores[key]


def get_store(settings: SettingsDep) -> CaptureStore | None:
    """Almacen de capturas en S3; `None` si no hay bucket configurado."""
    if not settings.bucket.strip():
        return None
    return _s3_store(settings.bucket, settings.prefix, settings.aws_profile, settings.aws_region)


StoreDep = Annotated[CaptureStore | None, Depends(get_store)]


def check_token(header: str | None, settings: CaptureSettings) -> None:
    if settings.device_token is None:
        raise CaptureError(
            503,
            "receptor_no_configurado",
            "El receptor no tiene P4_DEVICE_TOKEN configurado; no acepta envios",
        )
    scheme, _, token = (header or "").partition(" ")
    expected = settings.device_token.get_secret_value()
    if scheme.lower() != "bearer" or not hmac.compare_digest(token.encode(), expected.encode()):
        raise CaptureError(401, "no_autorizado", "Falta el token del dispositivo o no es valido")


def event_too_large(max_event_bytes: int) -> CaptureError:
    return CaptureError(
        413,
        "evento_demasiado_grande",
        f"La parte 'event' pasa de {max_event_bytes} bytes; "
        "el evento del contrato pesa menos de 1 KB",
    )


async def read_parts(
    request: Request, max_image_bytes: int, max_event_bytes: int
) -> tuple[str, bytes]:
    """Partes `event` e `image` del multipart. 400 si falta alguna; 413 si `event` es enorme."""
    try:
        # `max_part_size` limita las partes de texto (no la imagen, que llega como archivo).
        form = await request.form(max_files=2, max_fields=2, max_part_size=max_event_bytes)
    except (MultiPartException, HTTPException) as error:
        # Dentro de una app, Starlette envuelve el MultiPartException en un HTTPException(400):
        # se traduce aqui al formato del contrato.
        reason = str(getattr(error, "message", None) or getattr(error, "detail", error))
        if "exceeded maximum size" in reason:
            raise event_too_large(max_event_bytes) from error
        raise CaptureError(
            400, "solicitud_invalida", f"El cuerpo no es multipart valido: {reason}"
        ) from error
    event = form.get("event")
    image = form.get("image")
    if event is None:
        raise CaptureError(400, "solicitud_invalida", "Falta la parte 'event'")
    if image is None:
        raise CaptureError(400, "solicitud_invalida", "Falta la parte 'image'")
    if not isinstance(image, UploadFile):
        raise CaptureError(400, "solicitud_invalida", "La parte 'image' debe ser un archivo")
    # Se lee un byte de mas para saber si pasa del tope sin cargar archivos enormes.
    data = await image.read(max_image_bytes + 1)
    if isinstance(event, UploadFile):
        raw = await event.read(max_event_bytes + 1)
        if len(raw) > max_event_bytes:
            raise event_too_large(max_event_bytes)
        event = raw.decode("utf-8", errors="replace")
    return event, data


def _created(result_record: dict[str, object], record_key: str, status: str) -> dict[str, object]:
    return {
        "status": status,
        "capture_id": result_record["capture_id"],
        "image_key": result_record.get("image_key"),
        "record_key": record_key,
        "received_at": result_record.get("received_at"),
        "warnings": result_record.get("warnings", []),
    }


@router.post("", status_code=201)
async def receive_capture(request: Request, settings: SettingsDep, store: StoreDep) -> JSONResponse:
    """Recibe una captura: token, partes, imagen, forma y reglas del evento, y almacenamiento."""
    try:
        check_token(request.headers.get("authorization"), settings)
        event_text, data = await read_parts(
            request, settings.max_image_bytes, settings.max_event_bytes
        )
        image: ReceivedImage = inspect_image(data, settings.max_image_bytes)
        event: CaptureEvent = parse_event(event_text)
        validate_event(event, image, settings)
        if store is None:
            raise CaptureError(
                503,
                "receptor_no_configurado",
                "El almacenamiento de capturas no esta configurado; reintenta con el mismo "
                "capture_id",
            )
        result = await run_in_threadpool(store.save, event, image)
    except CaptureError as error:
        return error.response()
    return JSONResponse(
        status_code=201 if result.status == "created" else 200,
        content=_created(result.record, result.record_key, result.status),
    )


# --- lectura: portal (F5) y exportacion (bloque 6) ----------------------------
# Sin token: el portal no tiene inicio de sesion (decision 6). Solo lectura.

CaptureId = Annotated[str, Path(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")]


def _readable(store: CaptureStore | None) -> CaptureStore:
    if store is None:
        raise CaptureError(
            503, "receptor_no_configurado", "El almacenamiento de capturas no esta configurado"
        )
    return store


@router.get("")
async def list_captures(
    store: StoreDep, limit: Annotated[int, Query(ge=1, le=1000)] = 100
) -> JSONResponse:
    """Capturas de mas reciente a mas antigua (`captured_at` en UTC)."""
    try:
        records, problems = await run_in_threadpool(_readable(store).list_records)
    except CaptureError as error:
        return error.response()
    return JSONResponse({"items": records[:limit], "total": len(records), "errores": problems})


# Antes de `/{capture_id}`: "export" tambien cumple el patron de un capture_id.
@router.get("/export")
async def export_captures(
    store: StoreDep, format: Annotated[Literal["csv", "json"], Query()] = "json"
) -> Response:
    """Todos los eventos con los campos del contrato, en CSV o JSON."""
    try:
        records, problems = await run_in_threadpool(_readable(store).list_records)
    except CaptureError as error:
        return error.response()
    now = datetime.now(UTC)
    headers = {
        "Content-Disposition": f'attachment; filename="{export.filename(now, format)}"',
        # Registros ilegibles: visibles tambien en CSV, donde no caben en el cuerpo.
        "X-Capturas-Con-Error": str(len(problems)),
    }
    if format == "csv":
        return Response(export.to_csv(records), media_type="text/csv", headers=headers)
    return Response(
        export.to_json(records, problems, now), media_type="application/json", headers=headers
    )


@router.get("/{capture_id}")
async def read_capture(capture_id: CaptureId, store: StoreDep) -> JSONResponse:
    try:
        record = await run_in_threadpool(_readable(store).get_record, capture_id)
    except CaptureError as error:
        return error.response()
    return JSONResponse(record)


@router.get("/{capture_id}/image")
async def read_capture_image(capture_id: CaptureId, store: StoreDep) -> Response:
    """La fotografia, leida de S3 por el servidor: el navegador no recibe URLs ni llaves."""
    try:
        data = await run_in_threadpool(_readable(store).get_image, capture_id)
    except CaptureError as error:
        return error.response()
    return Response(
        data, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=300"}
    )
