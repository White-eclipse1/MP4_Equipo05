"""Fotografia recibida: JPEG real, con tope de tamano, SHA-256 y dimensiones."""

from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass

from PIL import Image, UnidentifiedImageError

from p4.capturas.errores import ErrorCaptura

INICIO_JPEG = b"\xff\xd8\xff"


@dataclass(frozen=True)
class Foto:
    datos: bytes
    sha256: str
    ancho: int
    alto: int

    @property
    def bytes(self) -> int:
        return len(self.datos)


def inspeccionar_foto(datos: bytes, max_bytes: int) -> Foto:
    """Bytes de la parte `foto` -> `Foto`. 413 si es grande; 415 si no es un JPEG legible."""
    if len(datos) > max_bytes:
        raise ErrorCaptura(
            413, "foto_demasiado_grande", f"La foto pesa {len(datos)} bytes; el maximo es {max_bytes}"
        )
    if not datos.startswith(INICIO_JPEG):
        raise ErrorCaptura(415, "foto_no_soportada", "La foto debe ser JPEG")
    try:
        with Image.open(io.BytesIO(datos)) as imagen:
            imagen.verify()
            ancho, alto = imagen.size
    except (UnidentifiedImageError, OSError, SyntaxError) as error:
        raise ErrorCaptura(
            415, "foto_no_soportada", f"La foto no es un JPEG legible: {error}"
        ) from error
    return Foto(datos, hashlib.sha256(datos).hexdigest(), ancho, alto)
