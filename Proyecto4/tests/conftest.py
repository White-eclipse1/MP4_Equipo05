"""Utilidades de prueba del receptor: JPEG sintetico, evento valido y app minima."""

from __future__ import annotations

import hashlib
import io
import json
from datetime import UTC, datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

from p4.captures import api
from p4.captures.event import CaptureEvent
from p4.captures.image import ReceivedImage
from p4.captures.s3_store import S3CaptureStore
from p4.captures.settings import CaptureSettings
from p4.captures.store import SaveResult

TOKEN = "token-de-prueba"  # valor falso, solo para pruebas
BUCKET = "bucket-de-prueba"
PREFIX = "edge-captures/"
RECEIVED = datetime(2026, 10, 8, 23, 0, 0, 123000, tzinfo=UTC)
CID = "edge01-20261009T153012-0007"
MODEL_SHA = "ca689c4e1478ccca7821dffaba8f07886bd9609a8aa3cec7450d9f875fbd69c0"


def make_jpeg(width: int = 64, height: int = 48, color: tuple[int, int, int] = (200, 30, 30)):
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), color).save(buffer, format="JPEG")
    return buffer.getvalue()


def valid_event(image: bytes, **changes: object) -> dict[str, object]:
    event: dict[str, object] = {
        "schema_version": 1,
        "capture_id": "edge01-20261009T153012-0007",
        "captured_at": "2026-10-08T15:30:12-06:00",
        "predicted_class": "dog",
        "confidence": 0.9309,
        "device_id": "edge01",
        "model_version": "1.0.0-int8.1",
        "model_sha256": MODEL_SHA,
        "image_ref": "capturas/edge01-20261009T153012-0007.jpg",
        "image_sha256": hashlib.sha256(image).hexdigest(),
        "region": None,
    }
    event.update(changes)
    return event


class MemoryStore:
    """Almacen en memoria con la misma interfaz que el de S3."""

    def __init__(self) -> None:
        self.saved: list[tuple[CaptureEvent, ReceivedImage]] = []

    def save(self, event: CaptureEvent, image: ReceivedImage) -> SaveResult:
        self.saved.append((event, image))
        record = event.model_dump()
        return SaveResult("created", record, f"edge-captures/events/{event.capture_id}.json")


@pytest.fixture
def settings() -> CaptureSettings:
    return CaptureSettings(P4_DEVICE_TOKEN=TOKEN, P4_MAX_IMAGE_BYTES=200_000)


@pytest.fixture
def store() -> MemoryStore:
    return MemoryStore()


@pytest.fixture
def client(settings: CaptureSettings, store: MemoryStore) -> TestClient:
    app = FastAPI()
    app.include_router(api.router)
    app.dependency_overrides[api.get_settings] = lambda: settings
    app.dependency_overrides[api.get_store] = lambda: store
    return TestClient(app)


def post(client: TestClient, event: object, image: bytes | None, token: str | None = TOKEN):
    """Envia como lo hara la Pi: `event` como campo de texto e `image` como archivo."""
    headers = {"Authorization": f"Bearer {token}"} if token is not None else {}
    text = event if isinstance(event, str) else json.dumps(event)
    data = {} if event is None else {"event": text}
    files = {} if image is None else {"image": ("captura.jpg", image, "image/jpeg")}
    return client.post("/api/p4/captures", headers=headers, data=data, files=files)


@pytest.fixture
def s3():
    from fake_s3 import FakeS3

    return FakeS3()


@pytest.fixture
def s3_store(s3) -> S3CaptureStore:
    return S3CaptureStore(s3, BUCKET, PREFIX, clock=lambda: RECEIVED)


@pytest.fixture
def s3_client(settings: CaptureSettings, s3_store: S3CaptureStore) -> TestClient:
    app = FastAPI()
    app.include_router(api.router)
    app.dependency_overrides[api.get_settings] = lambda: settings
    app.dependency_overrides[api.get_store] = lambda: s3_store
    return TestClient(app)
