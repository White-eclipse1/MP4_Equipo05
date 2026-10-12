"""Evento de captura `schema_version` 1 (`docs/contratos.md`).

Forma del evento: campos obligatorios, tipos estrictos (un numero en texto o un
booleano no pasan por `confidence`) y campos desconocidos rechazados, para que
un error de tipeo del dispositivo no se guarde en silencio.
"""

from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationError

from p4.captures.errors import CaptureError


class Region(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    x: int
    y: int
    width: int
    height: int


class CaptureEvent(BaseModel):
    """Campos que envia el dispositivo."""

    model_config = ConfigDict(extra="forbid", strict=True)

    schema_version: Literal[1]
    capture_id: str
    captured_at: str
    predicted_class: str
    confidence: float
    device_id: str
    model_version: str
    model_sha256: str
    image_ref: str
    image_sha256: str
    region: Region | None = None


def _field(loc: tuple[int | str, ...]) -> str:
    return ".".join(str(part) for part in loc) or "event"


def _problem(error: dict[str, object]) -> str:
    kind = error["type"]
    if kind == "missing":
        return "es obligatorio"
    if kind == "extra_forbidden":
        return "campo desconocido: no forma parte del contrato"
    return str(error["msg"])


def invalid_event(detalles: list[dict[str, object]]) -> CaptureError:
    first = detalles[0]
    return CaptureError(422, "evento_invalido", f"{first['campo']} {first['problema']}", detalles)


def parse_event(text: str) -> CaptureEvent:
    """Texto JSON de la parte `event` → evento. 400 si no es JSON; 422 si no cumple."""
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as error:
        raise CaptureError(
            400, "solicitud_invalida", f"La parte 'event' no es JSON valido: {error.msg}"
        ) from error
    if not isinstance(raw, dict):
        raise CaptureError(400, "solicitud_invalida", "La parte 'event' debe ser un objeto JSON")
    try:
        return CaptureEvent.model_validate(raw)
    except ValidationError as error:
        detalles = [
            {"campo": _field(item["loc"]), "problema": _problem(item)} for item in error.errors()
        ]
        raise invalid_event(detalles) from error
