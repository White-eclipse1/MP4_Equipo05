"""Conversion F2: modelo 1.0.0 del Proyecto 3 -> ONNX FP32 -> ONNX INT8 (criterios 1.1, 1.2).

Pasos, todos con verificacion:

1. Obtiene el checkpoint del P3 (copia local o S3 con `--from-s3`) y exige el
   SHA-256 de `conversion.yaml`. Lo carga con el `load_checkpoint` del propio
   P3, asi que la arquitectura, las clases y el preprocesamiento salen del
   checkpoint y no se redefinen aqui.
2. Exporta a ONNX FP32 (lote 1, 3x224x224) y comprueba que sus logits
   coinciden con los de PyTorch.
3. Elige las muestras de calibracion SOLO de la particion de train del
   manifiesto del P3 y guarda sus IDs.
4. Cuantiza estaticamente a INT8 (QDQ, pesos por canal) con onnxruntime.
5. Escribe el registro de conversion: entrada y salida con SHA-256, tecnica,
   configuracion, versiones, tamanos y efecto en el grafo.

Uso (desde Proyecto4/):
    .venv/Scripts/python modelo/convert.py
    .venv/Scripts/python modelo/convert.py --from-s3 --profile <perfil-aws>
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import platform
import random
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import onnx
import onnxruntime as ort
import torch
import yaml
from onnxruntime.quantization import (
    CalibrationDataReader,
    CalibrationMethod,
    QuantFormat,
    QuantType,
    quantize_static,
)
from onnxruntime.quantization.shape_inference import quant_pre_process
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]  # Proyecto4/
sys.path.insert(0, str(ROOT / "modelo"))
sys.path.insert(0, str(ROOT.parent / "Proyecto3" / "src"))

from p3.model.build import load_checkpoint  # noqa: E402
from preprocess import preprocess  # noqa: E402


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def resolve(path: str) -> Path:
    return (ROOT / path).resolve()


def fetch_checkpoint(cfg: dict, from_s3: bool, profile: str | None, workdir: Path) -> tuple[Path, dict]:
    src = cfg["source"]
    if not from_s3:
        return resolve(src["local_checkpoint"]), {"origin": "local", "path": src["local_checkpoint"]}
    import boto3

    s3 = boto3.Session(profile_name=profile).client("s3")
    response = s3.get_object(Bucket=src["s3_bucket"], Key=src["s3_key"])
    if response.get("VersionId") != src["s3_version_id"]:
        raise SystemExit(
            f"S3 devolvio VersionId {response.get('VersionId')}, se esperaba {src['s3_version_id']}"
        )
    path = workdir / "model.pt"
    path.write_bytes(response["Body"].read())
    uri = f"s3://{src['s3_bucket']}/{src['s3_key']}"
    return path, {"origin": "s3", "uri": uri, "version_id": response["VersionId"]}


def calibration_rows(cfg: dict) -> list[dict]:
    cal = cfg["calibration"]
    manifest = resolve(cal["manifest"])
    if sha256(manifest) != cal["manifest_hash"]:
        raise SystemExit(f"El manifiesto {manifest} no coincide con manifest_hash")
    crops_jsonl = resolve(cal["crops_dir"]) / "crops.jsonl"
    if sha256(crops_jsonl) != cal["crops_jsonl_sha256"]:
        raise SystemExit(f"{crops_jsonl} no coincide con crops_jsonl_sha256")
    paths = {r["crop_id"]: r["crop_path"] for r in map(json.loads, crops_jsonl.open(encoding="utf-8"))}
    rows = [r for r in map(json.loads, manifest.open(encoding="utf-8")) if r["split"] == cal["split"]]
    rows.sort(key=lambda r: r["crop_id"])
    chosen = random.Random(cal["seed"]).sample(rows, cal["samples"])
    chosen.sort(key=lambda r: r["crop_id"])
    for row in chosen:
        if row["split"] != "train":
            raise SystemExit(f"{row['crop_id']} no es de train")
        row["crop_path"] = paths[row["crop_id"]]
    return chosen


class CropReader(CalibrationDataReader):
    def __init__(self, rows: list[dict], crops_dir: Path, input_name: str):
        self._items = iter(
            {input_name: preprocess(Image.open(crops_dir / row["crop_path"]))} for row in rows
        )

    def get_next(self):
        return next(self._items, None)


def graph_summary(path: Path) -> dict:
    model = onnx.load(str(path))
    ops = collections.Counter(node.op_type for node in model.graph.node)
    dtypes = collections.Counter(
        onnx.TensorProto.DataType.Name(init.data_type) for init in model.graph.initializer
    )
    return {
        "nodes": sum(ops.values()),
        "op_types": dict(sorted(ops.items())),
        "initializer_dtypes": dict(sorted(dtypes.items())),
        "opset": [{"domain": o.domain or "ai.onnx", "version": o.version} for o in model.opset_import],
    }


def run_onnx(path: Path, x: np.ndarray) -> np.ndarray:
    session = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
    return session.run(None, {session.get_inputs()[0].name: x})[0]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", default="modelo/conversion.yaml")
    parser.add_argument("--from-s3", action="store_true", help="descargar model.pt de S3 en vez de la copia local")
    parser.add_argument("--profile", help="perfil de AWS (solo con --from-s3)")
    parser.add_argument("--out", default="artifacts", help="carpeta de artefactos (ignorada por Git)")
    parser.add_argument("--records", default="modelo/registros", help="carpeta de registros versionados")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")  # torch.onnx imprime emojis; la consola de Windows es cp1252

    cfg =yaml.safe_load(resolve(args.config).read_text(encoding="utf-8"))
    variant = cfg["variant"]
    out = resolve(args.out) / variant["version"]
    records = resolve(args.records)
    out.mkdir(parents=True, exist_ok=True)
    records.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        checkpoint, origin = fetch_checkpoint(cfg, args.from_s3, args.profile, tmp)
        source_sha = sha256(checkpoint)
        if source_sha != cfg["source"]["sha256"]:
            raise SystemExit(f"SHA-256 del checkpoint {source_sha} != {cfg['source']['sha256']}")
        source_size = checkpoint.stat().st_size
        model, meta = load_checkpoint(checkpoint)
    print(f"origen {origin} sha256={source_sha} clases={meta['class_names']}")

    size = meta["preprocessing"]["image_size"]
    dummy = torch.zeros(1, 3, size, size)
    fp32 = out / "model_fp32.onnx"
    torch.onnx.export(
        model,
        (dummy,),
        str(fp32),
        input_names=[variant["input_name"]],
        output_names=[variant["output_name"]],
        opset_version=variant["opset"],
        dynamo=True,
        external_data=False,
    )
    onnx.checker.check_model(str(fp32))

    # Paridad PyTorch vs ONNX FP32 con entradas aleatorias fijas.
    rng = np.random.default_rng(0)
    probe = rng.standard_normal((1, 3, size, size), dtype=np.float32)
    with torch.no_grad():
        torch_logits = model(torch.from_numpy(probe)).numpy()
    fp32_max_abs = float(np.abs(run_onnx(fp32, probe) - torch_logits).max())
    if fp32_max_abs > 1e-3:
        raise SystemExit(f"ONNX FP32 difiere de PyTorch: {fp32_max_abs}")

    # Calibracion solo con train.
    cal = cfg["calibration"]
    rows = calibration_rows(cfg)
    manifest_path = records / "calibracion_manifest.jsonl"
    with manifest_path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            keep = {k: row[k] for k in ("crop_id", "split", "category_name", "class_index", "crop_path")}
            handle.write(json.dumps(keep, ensure_ascii=False) + "\n")

    q = cfg["quantization"]
    prepped = out / "model_fp32_prep.onnx"
    quant_pre_process(str(fp32), str(prepped), skip_symbolic_shape=True)
    int8 = out / "model_int8.onnx"
    quantize_static(
        str(prepped),
        str(int8),
        CropReader(rows, resolve(cal["crops_dir"]), variant["input_name"]),
        quant_format=getattr(QuantFormat, q["format"]),
        per_channel=q["per_channel"],
        activation_type=getattr(QuantType, q["activation_type"]),
        weight_type=getattr(QuantType, q["weight_type"]),
        calibrate_method=getattr(CalibrationMethod, q["calibrate_method"]),
    )
    prepped.unlink()
    onnx.checker.check_model(str(int8))

    class_map = {str(i): name for i, name in enumerate(meta["class_names"])}
    package = {
        "variant_version": variant["version"],
        "source_p3_version": cfg["source"]["p3_version"],
        "class_names": meta["class_names"],
        "class_map": class_map,
        "input": {"name": variant["input_name"], "shape": [1, 3, size, size], "dtype": "float32", "layout": "NCHW", "channels": "RGB"},
        "output": {"name": variant["output_name"], "shape": [1, len(class_map)], "meaning": "logits; softmax para confianza"},
        "preprocessing": meta["preprocessing"] | {"implementation": "modelo/preprocess.py", "interpolation": "bilinear_antialias"},
    }
    (out / "model_package.json").write_text(json.dumps(package, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    log = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "variant_version": variant["version"],
        "input": {
            "description": "modelo publicado 1.0.0 del Proyecto 3",
            "p3_version": cfg["source"]["p3_version"],
            "run_id": cfg["source"]["run_id"],
            "sha256": source_sha,
            "bytes": source_size,
            "s3": f"s3://{cfg['source']['s3_bucket']}/{cfg['source']['s3_key']}",
            "s3_version_id": cfg["source"]["s3_version_id"],
            "loaded_from": origin,
            "architecture": meta["architecture"],
            "class_names": meta["class_names"],
            "preprocessing": meta["preprocessing"],
        },
        "outputs": {
            name: {"file": path.name, "sha256": sha256(path), "bytes": path.stat().st_size, "graph": graph_summary(path)}
            for name, path in (("fp32", fp32), ("int8", int8))
        },
        "technique": q | {"calibration_samples": len(rows), "calibration_split": cal["split"]},
        "calibration": {
            "manifest": str(manifest_path.relative_to(ROOT)).replace("\\", "/"),
            "manifest_sha256": sha256(manifest_path),
            "source_manifest": cal["manifest"],
            "source_manifest_sha256": cal["manifest_hash"],
            "seed": cal["seed"],
            "per_class": dict(sorted(collections.Counter(r["category_name"] for r in rows).items())),
            "splits_used": sorted({r["split"] for r in rows}),
        },
        "checks": {"fp32_vs_torch_max_abs_logit_diff": fp32_max_abs},
        "package": {"file": "model_package.json", "sha256": sha256(out / "model_package.json")},
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "torch": torch.__version__,
            "onnx": onnx.__version__,
            "onnxruntime": ort.__version__,
            "numpy": np.__version__,
        },
    }
    log["size_reduction_pct"] = round(
        100 * (1 - log["outputs"]["int8"]["bytes"] / source_size), 2
    )
    log_path = records / "conversion_log.json"
    log_path.write_text(json.dumps(log, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: log[k] for k in ("variant_version", "size_reduction_pct", "checks")}, indent=2))
    for name, item in log["outputs"].items():
        print(f"{name}: {item['file']} {item['bytes']} bytes sha256={item['sha256']}")


if __name__ == "__main__":
    main()
