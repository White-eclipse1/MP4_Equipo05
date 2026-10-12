"""Almacen de capturas en S3 (decision 5): imagen y registro por `capture_id`.

```
{prefix}images/{capture_id}.jpg     metadatos S3: sha256, capture-id
{prefix}events/{capture_id}.json    evento + campos del receptor
```

Idempotencia (contrato, regla 3): las dos escrituras usan `If-None-Match: *`,
primero la imagen y despues el registro, asi que un registro nunca apunta a una
imagen inexistente. Si la llave ya existe (412), se compara lo guardado con lo
recibido: igual → `duplicate` sin escribir; distinto → 409 con los campos que
difieren. Nunca se sobrescribe ni se borra.

Lectura (bloque 6, portal y exportacion): `ListObjectsV2` de `events/` y
`GetObject` en paralelo, ordenado por `captured_at` en UTC de mas reciente a mas
antigua (desempate `received_at`, `capture_id`), con cache corta. Un registro
ilegible no se esconde: se devuelve en `errores` junto al listado.
"""

from __future__ import annotations

import json
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from typing import Any

from botocore.exceptions import BotoCoreError, ClientError

from p4.captures.errors import CaptureError
from p4.captures.event import CaptureEvent
from p4.captures.image import ReceivedImage
from p4.captures.store import SaveResult
from p4.captures.validation import assess_timing, parse_captured_at

# Campos que envia el dispositivo: los que deciden si un reintento es identico.
DEVICE_FIELDS = tuple(CaptureEvent.model_fields)
# S3 responde 412 cuando `If-None-Match: *` encuentra la llave.
EXISTS = {"PreconditionFailed", "412"}
RETRY = "Reintenta con el mismo capture_id"
READ_RETRY = "Vuelve a consultar en unos segundos"
MISSING = {"NoSuchKey", "404", "NotFound"}
OLDEST = datetime.min.replace(tzinfo=UTC)


def build_record(
    event: CaptureEvent, image: ReceivedImage, image_key: str, received_at: datetime
) -> dict[str, Any]:
    """Registro que se guarda: el evento tal cual mas los campos del receptor."""
    delay, warnings = assess_timing(event, received_at)
    record: dict[str, Any] = event.model_dump(mode="json")
    record.update(
        received_at=received_at.astimezone(UTC).isoformat(timespec="milliseconds"),
        image_key=image_key,
        image_bytes=image.size,
        image_width=image.width,
        image_height=image.height,
        delivery_delay_s=round(delay, 3),
        warnings=warnings,
    )
    return record


def _code(error: ClientError) -> str:
    return str(error.response.get("Error", {}).get("Code", ""))


def unavailable(error: Exception, hint: str = RETRY) -> CaptureError:
    reason = _code(error) if isinstance(error, ClientError) else type(error).__name__
    return CaptureError(
        503,
        "almacenamiento_no_disponible",
        f"S3 no aceptó la operación ({reason}). {hint}",
    )


def not_found(capture_id: str) -> CaptureError:
    return CaptureError(
        404, "captura_no_encontrada", f"No existe la captura {capture_id} en el almacenamiento"
    )


def sort_key(record: dict[str, Any]) -> tuple[datetime, str, str]:
    """Orden del portal: `captured_at` en UTC, luego `received_at` y `capture_id`."""
    try:
        captured = parse_captured_at(str(record.get("captured_at"))).astimezone(UTC)
    except ValueError:
        captured = OLDEST
    return captured, str(record.get("received_at", "")), str(record.get("capture_id", ""))


def conflict(differences: list[dict[str, object]]) -> CaptureError:
    return CaptureError(
        409,
        "conflicto_capture_id",
        "El capture_id ya existe con otros datos; no se sobrescribe",
        differences,
    )


class S3CaptureStore:
    def __init__(
        self,
        client: Any,
        bucket: str,
        prefix: str,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        cache_ttl: float = 10.0,
    ) -> None:
        self.client = client
        self.bucket = bucket
        self.prefix = prefix
        self.clock = clock
        self.cache_ttl = cache_ttl
        self._cache: tuple[float, list[dict[str, Any]], list[dict[str, str]]] | None = None
        self._lock = threading.Lock()

    def image_key(self, capture_id: str) -> str:
        return f"{self.prefix}images/{capture_id}.jpg"

    def record_key(self, capture_id: str) -> str:
        return f"{self.prefix}events/{capture_id}.json"

    def save(self, event: CaptureEvent, image: ReceivedImage) -> SaveResult:
        received_at = self.clock()
        image_key = self.image_key(event.capture_id)
        record_key = self.record_key(event.capture_id)
        try:
            self._put_image(image_key, event.capture_id, image)
            record = build_record(event, image, image_key, received_at)
            if self._put_new(record_key, _dump(record), "application/json", {}):
                self._cache = None  # la captura nueva aparece en el siguiente listado
                return SaveResult("created", record, record_key)
            stored = json.loads(self._get(record_key))
        except (ClientError, BotoCoreError) as error:
            raise unavailable(error) from error
        differences = _differences(stored, event)
        if differences:
            raise conflict(differences)
        return SaveResult("duplicate", stored, record_key)

    def _put_image(self, key: str, capture_id: str, image: ReceivedImage) -> None:
        metadata = {"sha256": image.sha256, "capture-id": capture_id}
        if self._put_new(key, image.data, "image/jpeg", metadata):
            return
        # Ya existe: es un reintento (quizas tras una falla a la mitad) solo si es la misma foto.
        stored_sha = self.client.head_object(Bucket=self.bucket, Key=key)["Metadata"].get("sha256")
        if stored_sha != image.sha256:
            raise conflict(
                [{"campo": "image_sha256", "guardado": stored_sha, "recibido": image.sha256}]
            )

    def _put_new(self, key: str, body: bytes, content_type: str, metadata: dict[str, str]) -> bool:
        """`True` si se escribio; `False` si la llave ya existia (no se toca)."""
        try:
            self.client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=body,
                ContentType=content_type,
                Metadata=metadata,
                IfNoneMatch="*",
            )
        except ClientError as error:
            if _code(error) in EXISTS:
                return False
            raise
        return True

    def _get(self, key: str) -> bytes:
        return self.client.get_object(Bucket=self.bucket, Key=key)["Body"].read()

    # --- lectura (bloque 6) ---------------------------------------------------

    def list_records(self) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
        """(registros de mas reciente a mas antigua, registros que no se pudieron leer)."""
        with self._lock:
            if self._cache and time.monotonic() - self._cache[0] < self.cache_ttl:
                return self._cache[1], self._cache[2]
            try:
                keys = self._event_keys()
            except (ClientError, BotoCoreError) as error:
                raise unavailable(error, READ_RETRY) from error
            records: list[dict[str, Any]] = []
            problems: list[dict[str, str]] = []
            with ThreadPoolExecutor(max_workers=16) as pool:
                for key, result in zip(keys, pool.map(self._read_record, keys), strict=True):
                    if isinstance(result, dict):
                        records.append(result)
                    else:
                        problems.append({"record_key": key, "problema": result})
            records.sort(key=sort_key, reverse=True)
            self._cache = (time.monotonic(), records, problems)
            return records, problems

    def get_record(self, capture_id: str) -> dict[str, Any]:
        return json.loads(self._read_one(self.record_key(capture_id), capture_id))

    def get_image(self, capture_id: str) -> bytes:
        return self._read_one(self.image_key(capture_id), capture_id)

    def _read_one(self, key: str, capture_id: str) -> bytes:
        try:
            return self._get(key)
        except ClientError as error:
            if _code(error) in MISSING:
                raise not_found(capture_id) from error
            raise unavailable(error, READ_RETRY) from error
        except BotoCoreError as error:
            raise unavailable(error, READ_RETRY) from error

    def _event_keys(self) -> list[str]:
        keys: list[str] = []
        params: dict[str, Any] = {"Bucket": self.bucket, "Prefix": f"{self.prefix}events/"}
        while True:
            page = self.client.list_objects_v2(**params)
            contents = page.get("Contents", [])
            keys += [item["Key"] for item in contents if item["Key"].endswith(".json")]
            if not page.get("IsTruncated"):
                return keys
            params["ContinuationToken"] = page["NextContinuationToken"]

    def _read_record(self, key: str) -> dict[str, Any] | str:
        try:
            record = json.loads(self._get(key))
        except (ClientError, BotoCoreError) as error:
            return f"no se pudo leer: {type(error).__name__}"
        except ValueError as error:
            return f"JSON invalido: {error}"
        return record if isinstance(record, dict) else "el registro no es un objeto JSON"


def _dump(record: dict[str, Any]) -> bytes:
    return json.dumps(record, ensure_ascii=False, indent=2).encode("utf-8")


def _differences(stored: dict[str, Any], event: CaptureEvent) -> list[dict[str, object]]:
    received = event.model_dump(mode="json")
    return [
        {"campo": name, "guardado": stored.get(name), "recibido": received[name]}
        for name in DEVICE_FIELDS
        if stored.get(name) != received[name]
    ]


class UnavailableStore:
    """Almacen que no se pudo construir (perfil inexistente, sin bucket): 503 con el motivo."""

    def __init__(self, reason: str) -> None:
        self.reason = reason

    def _fail(self, hint: str) -> CaptureError:
        return CaptureError(
            503, "receptor_no_configurado", f"Almacenamiento no disponible: {self.reason}. {hint}"
        )

    def save(self, event: CaptureEvent, image: ReceivedImage) -> SaveResult:
        raise self._fail(RETRY)

    def list_records(self) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
        raise self._fail(READ_RETRY)

    def get_record(self, capture_id: str) -> dict[str, Any]:
        raise self._fail(READ_RETRY)

    def get_image(self, capture_id: str) -> bytes:
        raise self._fail(READ_RETRY)
