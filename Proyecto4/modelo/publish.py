"""Publica la variante en S3 para que el dispositivo y el evaluador la descarguen (F2).

Sube a `s3://<bucket>/models/clasificador-edge/<version>/` los artefactos de
`artifacts/<version>/` y los registros de `modelo/registros/`. Las versiones
son inmutables: si el prefijo ya tiene objetos, se detiene. Tras subir, vuelve
a descargar cada archivo y compara su SHA-256; solo entonces escribe
`modelo/registros/publicacion.json` con llave, SHA-256 y VersionId.

Uso (desde Proyecto4/): .venv/Scripts/python modelo/publish.py --profile <perfil-aws>
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import boto3
import yaml

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "models/clasificador-edge"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    args = parser.parse_args()

    cfg = yaml.safe_load((ROOT / "modelo/conversion.yaml").read_text(encoding="utf-8"))
    version = cfg["variant"]["version"]
    bucket = cfg["source"]["s3_bucket"]
    artifacts = ROOT / "artifacts" / version
    records = ROOT / "modelo/registros"
    files = [
        artifacts / "model_int8.onnx",
        artifacts / "model_fp32.onnx",
        artifacts / "model_package.json",
        records / "conversion_log.json",
        records / "calibracion_manifest.jsonl",
        records / "smoke_test.json",
    ]

    log = json.loads((records / "conversion_log.json").read_text(encoding="utf-8"))
    for name in ("fp32", "int8"):
        path = artifacts / log["outputs"][name]["file"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != log["outputs"][name]["sha256"]:
            raise SystemExit(f"{path} no coincide con conversion_log.json")

    s3 = boto3.Session(profile_name=args.profile).client("s3")
    prefix = f"{PREFIX}/{version}/"
    if s3.list_objects_v2(Bucket=bucket, Prefix=prefix).get("KeyCount", 0):
        raise SystemExit(f"s3://{bucket}/{prefix} ya existe; las versiones son inmutables")

    published = []
    for path in files:
        data = path.read_bytes()
        key = prefix + path.name
        put = s3.put_object(Bucket=bucket, Key=key, Body=data)
        back = s3.get_object(Bucket=bucket, Key=key)
        if back.get("VersionId") != put.get("VersionId"):
            raise SystemExit(f"{key}: VersionId descargado distinto del subido")
        digest = hashlib.sha256(data).hexdigest()
        if hashlib.sha256(back["Body"].read()).hexdigest() != digest:
            raise SystemExit(f"{key}: SHA-256 descargado distinto del local")
        published.append({"key": key, "bytes": len(data), "sha256": digest, "version_id": put.get("VersionId")})
        print(f"{key} {len(data)} {digest} {put.get('VersionId')}")

    record = {
        "variant_version": version,
        "bucket": bucket,
        "prefix": prefix,
        "published_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "objects": published,
    }
    (records / "publicacion.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
