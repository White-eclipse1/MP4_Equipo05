"""Reglas del evento `schema_version` 1 (`docs/contratos.md`, reglas de recepcion).

`validate_event` reune TODOS los problemas del evento y los devuelve juntos en un
422 `evento_invalido`: el dispositivo ve de una vez que corregir. Nada invalido
llega al almacen.

`assess_timing` no rechaza: calcula el retraso de entrega (informativo) y senala
un reloj adelantado. Una captura que llega tarde es normal (el dispositivo
clasifica sin red) y no genera aviso.
"""

from __future__ import annotations

import math
import re
from datetime import datetime, timedelta

from p4.captures.event import CaptureEvent, invalid_event
from p4.captures.image import ReceivedImage
from p4.captures.settings import CaptureSettings

# Orden de salida del modelo del P3 (`docs/artefacto.md`).
CLASSES = ("cat", "dog", "person")
CAPTURE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
DEVICE_ID = re.compile(r"[A-Za-z0-9._-]{1,64}")
SHA256 = re.compile(r"[0-9a-f]{64}")
FUTURE_TOLERANCE = timedelta(minutes=5)
FUTURE_WARNING = "captured_at_en_el_futuro"


def parse_captured_at(value: str) -> datetime:
    """ISO 8601 con offset → `datetime` con zona. `ValueError` con el motivo si no."""
    try:
        moment = datetime.fromisoformat(value)
    except ValueError as error:
        raise ValueError(
            "no es una fecha ISO 8601 válida (ej. 2026-10-09T15:30:12-06:00)"
        ) from error
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise ValueError("debe incluir zona horaria (ej. -06:00)")
    return moment


def _problems(
    event: CaptureEvent, image: ReceivedImage, settings: CaptureSettings
) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []

    if not CAPTURE_ID.fullmatch(event.capture_id):
        found.append(
            (
                "capture_id",
                "solo admite letras, dígitos, '.', '_' y '-' (1 a 128, sin '/'), "
                "empezando por letra o dígito",
            )
        )

    try:
        parse_captured_at(event.captured_at)
    except ValueError as error:
        found.append(("captured_at", str(error)))

    if event.predicted_class not in CLASSES:
        found.append(("predicted_class", f"debe ser {', '.join(CLASSES[:-1])} o {CLASSES[-1]}"))

    if not math.isfinite(event.confidence) or not 0 <= event.confidence <= 1:
        found.append(("confidence", f"debe estar entre 0 y 1; llegó {event.confidence}"))

    if not DEVICE_ID.fullmatch(event.device_id):
        found.append(("device_id", "solo admite letras, dígitos, '.', '_' y '-' (1 a 64)"))

    models = settings.models()
    if not event.model_version.strip():
        found.append(("model_version", "es obligatorio"))
    elif event.model_version not in models:
        accepted = ", ".join(sorted(models)) or "ninguna configurada"
        found.append(
            ("model_version", f"{event.model_version} no es una versión aceptada ({accepted})")
        )

    if not SHA256.fullmatch(event.model_sha256):
        found.append(("model_sha256", "debe ser un SHA-256 de 64 caracteres hex en minúsculas"))
    elif models.get(event.model_version, event.model_sha256) != event.model_sha256:
        found.append(("model_sha256", f"no corresponde a {event.model_version}"))

    if not event.image_ref.strip():
        found.append(("image_ref", "es obligatorio"))

    if not SHA256.fullmatch(event.image_sha256):
        found.append(("image_sha256", "debe ser un SHA-256 de 64 caracteres hex en minúsculas"))
    elif event.image_sha256 != image.sha256:
        found.append(("image_sha256", "no coincide con la imagen recibida"))

    region = event.region
    if region is not None:
        if region.x < 0 or region.y < 0 or region.width <= 0 or region.height <= 0:
            found.append(("region", "x, y deben ser >= 0 y width, height > 0"))
        elif region.x + region.width > image.width or region.y + region.height > image.height:
            found.append(
                (
                    "region",
                    f"queda fuera de la imagen ({image.width}x{image.height} px): "
                    f"x+width={region.x + region.width}, y+height={region.y + region.height}",
                )
            )
    return found


def validate_event(event: CaptureEvent, image: ReceivedImage, settings: CaptureSettings) -> None:
    """422 `evento_invalido` con todos los problemas, o nada si el evento cumple."""
    found = _problems(event, image, settings)
    if found:
        raise invalid_event([{"campo": campo, "problema": problema} for campo, problema in found])


def assess_timing(event: CaptureEvent, received_at: datetime) -> tuple[float, list[str]]:
    """(`delivery_delay_s`, `warnings`) de un evento ya validado."""
    captured = parse_captured_at(event.captured_at)
    delay = (received_at - captured).total_seconds()
    warnings = [FUTURE_WARNING] if captured - received_at > FUTURE_TOLERANCE else []
    return delay, warnings


__all__ = [
    "CLASSES",
    "FUTURE_WARNING",
    "assess_timing",
    "parse_captured_at",
    "validate_event",
]
