"""Fotografia recibida: solo JPEG, con tope de tamano, hash y dimensiones."""

from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass

from PIL import Image, UnidentifiedImageError

from p4.captures.errors import CaptureError

JPEG_MAGIC = b"\xff\xd8\xff"


@dataclass(frozen=True)
class ReceivedImage:
    data: bytes
    sha256: str
    width: int
    height: int

    @property
    def size(self) -> int:
        return len(self.data)


def inspect_image(data: bytes, max_bytes: int) -> ReceivedImage:
    """Bytes de la parte `image` → imagen verificada. 413 si es grande; 415 si no es JPEG."""
    if len(data) > max_bytes:
        raise CaptureError(
            413,
            "imagen_demasiado_grande",
            f"La imagen pesa {len(data)} bytes; el maximo es {max_bytes}",
        )
    if not data.startswith(JPEG_MAGIC):
        raise CaptureError(415, "imagen_no_soportada", "La imagen debe ser JPEG")
    try:
        with Image.open(io.BytesIO(data)) as picture:
            picture.verify()
            if picture.format != "JPEG":
                raise CaptureError(415, "imagen_no_soportada", "La imagen debe ser JPEG")
            width, height = picture.size
    except (UnidentifiedImageError, OSError, SyntaxError) as error:
        raise CaptureError(
            415, "imagen_no_soportada", f"La imagen no es un JPEG legible: {error}"
        ) from error
    return ReceivedImage(data, hashlib.sha256(data).hexdigest(), width, height)
