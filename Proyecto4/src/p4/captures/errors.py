"""Errores del receptor con la forma del contrato: `{error, mensaje, detalles}`."""

from __future__ import annotations

from fastapi.responses import JSONResponse


class CaptureError(Exception):
    """Un rechazo explicito: codigo HTTP, codigo de error y mensaje legible."""

    def __init__(
        self,
        status: int,
        error: str,
        mensaje: str,
        detalles: list[dict[str, object]] | None = None,
    ) -> None:
        super().__init__(mensaje)
        self.status = status
        self.error = error
        self.mensaje = mensaje
        self.detalles = detalles or []

    def response(self) -> JSONResponse:
        return JSONResponse(
            status_code=self.status,
            content={"error": self.error, "mensaje": self.mensaje, "detalles": self.detalles},
        )
