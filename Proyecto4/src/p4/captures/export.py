"""Exportacion de eventos en CSV y JSON (contrato, regla de recepcion 5).

Columnas: los campos del contrato en su orden, con `region` aplanada en
`region_x/y/width/height`, y despues los campos del receptor. `confidence` se
escribe con toda su precision: los numeros se recalculan desde aqui (regla 9 de
`AGENTS.md`).
"""

from __future__ import annotations

import csv
import io
import json
from datetime import UTC, datetime
from typing import Any

COLUMNS = (
    "schema_version",
    "capture_id",
    "captured_at",
    "predicted_class",
    "confidence",
    "device_id",
    "model_version",
    "model_sha256",
    "image_ref",
    "image_sha256",
    "region_x",
    "region_y",
    "region_width",
    "region_height",
    "received_at",
    "image_key",
    "image_bytes",
    "image_width",
    "image_height",
    "delivery_delay_s",
    "warnings",
)


def _row(record: dict[str, Any]) -> dict[str, Any]:
    region = record.get("region") or {}
    row = {name: record.get(name) for name in COLUMNS}
    for side in ("x", "y", "width", "height"):
        row[f"region_{side}"] = region.get(side)
    row["warnings"] = ";".join(record.get("warnings") or [])
    return row


def to_csv(records: list[dict[str, Any]]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(_row(record) for record in records)
    return buffer.getvalue()


def to_json(records: list[dict[str, Any]], problems: list[dict[str, str]], now: datetime) -> str:
    return json.dumps(
        {
            "exported_at": now.astimezone(UTC).isoformat(timespec="seconds"),
            "total": len(records),
            "items": records,
            "errores": problems,
        },
        ensure_ascii=False,
        indent=2,
    )


def filename(now: datetime, extension: str) -> str:
    return f"edge-captures-{now.astimezone(UTC):%Y%m%dT%H%M%SZ}.{extension}"
