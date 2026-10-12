"""Interfaz del almacenamiento de capturas.

El router solo conoce `CaptureStore`; la implementacion es `S3CaptureStore`
(decision 5). Las pruebas de recepcion usan un almacen en memoria.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Protocol

from p4.captures.event import CaptureEvent
from p4.captures.image import ReceivedImage


@dataclass(frozen=True)
class SaveResult:
    status: Literal["created", "duplicate"]
    record: dict[str, object]
    record_key: str


class CaptureStore(Protocol):
    def save(self, event: CaptureEvent, image: ReceivedImage) -> SaveResult: ...

    def list_records(self) -> tuple[list[dict[str, Any]], list[dict[str, str]]]: ...

    def get_record(self, capture_id: str) -> dict[str, Any]: ...

    def get_image(self, capture_id: str) -> bytes: ...
