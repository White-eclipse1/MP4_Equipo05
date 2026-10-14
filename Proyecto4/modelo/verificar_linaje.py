"""Verificacion del linaje del modelo (VAL-01; requisito M1 y criterio 1.1).

Reconstruye la cadena

    modelo publicado 1.0.0 del P3  ->  registro de conversion  ->  variante 1.0.0-int8.1

y contrasta versiones, run_id, SHA-256, orden de clases y preprocesamiento entre
fuentes independientes: lo que el P3 dejo en su repositorio (`selection.json`,
`config/classes.yaml`, `transforms.py`, `publicacion_s3.md`, el reporte de
evaluacion), la configuracion y el registro de la conversion del P4, y lo que
`modelo/publish.py` subio a S3.

Dos niveles:

- Sin argumentos ("registros"): solo lee archivos versionados; no necesita red,
  pesos ni dependencias pesadas (stdlib + PyYAML). Ademas reconstruye byte a byte
  `model_package.json` a partir del registro y compara su SHA-256 con el publicado.
- `--profile <perfil>` ("s3"): ademas descarga de S3 el `model.pt` del P3 y los
  objetos de la variante, recalcula sus SHA-256, compara su `VersionId` con el
  registrado y lee el paquete del P3 (`registry.json`, `class_map.json`,
  `preprocessing.json`, `model_version.json`). Necesita boto3 y un perfil con
  lectura sobre el bucket del equipo. Como la politica de los integrantes no
  incluye `s3:GetObjectVersion`, se descarga la version actual y se exige que su
  `VersionId` sea el registrado (igual que `Proyecto3/scripts/publish_model.py`).
- `--local`: recalcula el SHA-256 de las copias locales que existan (checkpoint
  de `dvc pull` y `artifacts/<version>/`), sin red.

Las comprobaciones que el nivel elegido no puede ejecutar quedan como
"pendiente", nunca como "ok". Sale con codigo 1 si alguna falla.

Uso (desde Proyecto4/):
    python modelo/verificar_linaje.py
    python modelo/verificar_linaje.py --profile <perfil-aws>
    python modelo/verificar_linaje.py --local
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import platform
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]  # Proyecto4/
P3 = ROOT.parent / "Proyecto3"
RECORDS = ROOT / "modelo" / "registros"

# Lo que la tarea VAL-01 exige encontrar al final de la cadena.
EXPECTED_P3_VERSION = "1.0.0"
EXPECTED_VARIANT = "1.0.0-int8.1"
EXPECTED_CLASSES = ["cat", "dog", "person"]
P3_MODELS_PREFIX = "models/clasificador"
EDGE_PREFIX = "models/clasificador-edge"

OK, FAIL, PENDING = "ok", "falla", "pendiente"


@dataclass
class Check:
    id: str
    criterio: str
    estado: str
    detalle: str


class Checks(list):
    def add(self, check_id: str, criterio: str, ok: bool, detalle: str) -> None:
        self.append(Check(check_id, criterio, OK if ok else FAIL, detalle))

    def pending(self, check_id: str, criterio: str, detalle: str) -> None:
        self.append(Check(check_id, criterio, PENDING, detalle))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def module_constants(path: Path) -> dict[str, Any]:
    """Constantes literales de un modulo sin importarlo (evita torch y numpy).

    `X = (0.1, 0.2)` da la tupla; `X = np.array([...], ...)` da su primer argumento.
    """
    constants: dict[str, Any] = {}
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if not (isinstance(node, ast.Assign) and len(node.targets) == 1):
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            continue
        value = node.value
        if isinstance(value, ast.Call) and value.args:
            value = value.args[0]
        try:
            constants[target.id] = ast.literal_eval(value)
        except ValueError:
            continue
    return constants


def rebuild_model_package(cfg: dict, log: dict, newline: str) -> bytes:
    """Mismo contenido que escribe `convert.py` en `model_package.json`.

    `convert.py` usa `Path.write_text`, que en Windows traduce "\\n" a "\\r\\n";
    por eso se prueba con los dos finales de linea.
    """
    variant = cfg["variant"]
    meta = log["input"]
    size = meta["preprocessing"]["image_size"]
    class_map = {str(i): name for i, name in enumerate(meta["class_names"])}
    package = {
        "variant_version": variant["version"],
        "source_p3_version": cfg["source"]["p3_version"],
        "class_names": meta["class_names"],
        "class_map": class_map,
        "input": {
            "name": variant["input_name"],
            "shape": [1, 3, size, size],
            "dtype": "float32",
            "layout": "NCHW",
            "channels": "RGB",
        },
        "output": {
            "name": variant["output_name"],
            "shape": [1, len(class_map)],
            "meaning": "logits; softmax para confianza",
        },
        "preprocessing": meta["preprocessing"]
        | {"implementation": "modelo/preprocess.py", "interpolation": "bilinear_antialias"},
    }
    text = json.dumps(package, indent=2, ensure_ascii=False) + "\n"
    return text.replace("\n", newline).encode("utf-8")


def p3_published_row(version: str) -> str | None:
    """Fila de `version` en la tabla de versiones de `Proyecto3/docs/publicacion_s3.md`."""
    for line in (P3 / "docs" / "publicacion_s3.md").read_text(encoding="utf-8").splitlines():
        if line.startswith(f"| **{version}** |") or line.startswith(f"| {version} |"):
            return line
    return None


def by_key(publication: dict) -> dict[str, dict]:
    return {obj["key"].rsplit("/", 1)[-1]: obj for obj in publication["objects"]}


# ---------------------------------------------------------------------------
# Nivel "registros": solo archivos versionados
# ---------------------------------------------------------------------------


def check_records(checks: Checks) -> dict[str, Any]:
    cfg = read_yaml(ROOT / "modelo" / "conversion.yaml")
    log = read_json(RECORDS / "conversion_log.json")
    publication = read_json(RECORDS / "publicacion.json")
    smoke = read_json(RECORDS / "smoke_test.json")
    selection = read_json(P3 / "docs" / "selection.json")
    p3_classes = read_yaml(P3 / "config" / "classes.yaml")
    p3_transforms = module_constants(P3 / "src" / "p3" / "data" / "transforms.py")
    p3_build = module_constants(P3 / "src" / "p3" / "model" / "build.py")
    edge_pre = module_constants(ROOT / "modelo" / "preprocess.py")
    src, inp = cfg["source"], log["input"]
    published = by_key(publication)
    run_id = src["run_id"]

    # 1. Version original 1.0.0
    checks.add(
        "origen.version",
        "Se identifica model version original 1.0.0",
        src["p3_version"] == inp["p3_version"] == EXPECTED_P3_VERSION
        and src["s3_key"] == f"{P3_MODELS_PREFIX}/{EXPECTED_P3_VERSION}/model.pt",
        f"conversion.yaml={src['p3_version']}, conversion_log={inp['p3_version']}, "
        f"s3_key={src['s3_key']}",
    )

    # 2. run_id de MLflow
    report = P3 / "reports" / "evaluation" / run_id / "metrics.json"
    checks.add(
        "origen.run_id",
        "Se identifica MLflow run_id de origen",
        run_id == inp["run_id"] == selection["run_id"] and report.is_file(),
        f"{run_id}: igual en conversion.yaml, conversion_log y Proyecto3/docs/selection.json "
        f"(regla '{selection['rule']}', {selection['candidates']} candidatas); evaluacion en "
        f"test del P3 en {report.relative_to(ROOT.parent).as_posix()}"
        + ("" if report.is_file() else " (NO EXISTE)"),
    )

    # 3. Checkpoint original
    expected_uri = f"mlflow-artifacts:/3/{run_id}/artifacts/checkpoint/model.pt"
    checks.add(
        "origen.checkpoint",
        "Se identifica checkpoint original",
        selection["checkpoint_uri"] == expected_uri
        and run_id in src["local_checkpoint"]
        and inp["s3"] == f"s3://{src['s3_bucket']}/{src['s3_key']}"
        and inp["s3_version_id"] == src["s3_version_id"],
        f"MLflow {selection['checkpoint_uri']}; S3 {inp['s3']} (VersionId "
        f"{src['s3_version_id']}); copia DVC {src['local_checkpoint']}",
    )

    # 4. SHA-256 del original, contra lo que el P3 registro por su cuenta
    p3_row = p3_published_row(EXPECTED_P3_VERSION) or ""
    checks.add(
        "origen.sha256_registros",
        "SHA-256 del modelo original coincide en todas las fuentes",
        src["sha256"] == inp["sha256"] == selection["checkpoint_sha256"] == smoke["source_sha256"]
        and src["sha256"] in p3_row
        and src["s3_version_id"] in p3_row
        and run_id in p3_row,
        f"{src['sha256']} ({inp['bytes']} bytes) en conversion.yaml, conversion_log, "
        f"selection.json del P3, smoke_test.json y la tabla de Proyecto3/docs/publicacion_s3.md "
        f"(junto con su VersionId y run_id)",
    )

    # 5. Variante 1.0.0-int8.1
    int8 = log["outputs"]["int8"]
    checks.add(
        "variante.version",
        "Se identifica variante 1.0.0-int8.1",
        cfg["variant"]["version"]
        == log["variant_version"]
        == publication["variant_version"]
        == smoke["variant_version"]
        == EXPECTED_VARIANT
        and publication["prefix"] == f"{EDGE_PREFIX}/{EXPECTED_VARIANT}/",
        f"{EXPECTED_VARIANT} en conversion.yaml, conversion_log, publicacion.json y "
        f"smoke_test.json; s3://{publication['bucket']}/{publication['prefix']}",
    )

    # 6. SHA-256 de la variante
    pub_int8 = published.get(int8["file"], {})
    arm64 = (RECORDS / "arm64_check.txt").read_text(encoding="utf-8")
    checks.add(
        "variante.sha256_registros",
        "SHA-256 de la variante coincide en todas las fuentes",
        int8["sha256"] == pub_int8.get("sha256") == smoke["int8_sha256"]
        and int8["bytes"] == pub_int8.get("bytes")
        and f"bytes={int8['bytes']} sha256={int8['sha256']}" in arm64,
        f"{int8['file']} {int8['sha256']} ({int8['bytes']} bytes) en conversion_log, "
        f"publicacion.json (VersionId {pub_int8.get('version_id')}), smoke_test.json y "
        "arm64_check.txt",
    )

    # 7. Orden de clases: P3 (classes.yaml) -> checkpoint (conversion_log) -> paquete
    p3_order = [
        c["category_name"] for c in sorted(p3_classes["classes"], key=lambda c: c["class_index"])
    ]
    checks.add(
        "clases.orden",
        "Se conserva class order: cat, dog, person",
        p3_order == inp["class_names"] == EXPECTED_CLASSES
        and inp["architecture"]["num_classes"] == len(EXPECTED_CLASSES),
        f"Proyecto3/config/classes.yaml={p3_order}; checkpoint (conversion_log)="
        f"{inp['class_names']}; num_classes={inp['architecture']['num_classes']}",
    )

    # 8. Preprocesamiento: P3 transforms.py -> checkpoint -> preprocess.py del edge
    pre = inp["preprocessing"]
    p3_mean, p3_std = list(p3_transforms["IMAGENET_MEAN"]), list(p3_transforms["IMAGENET_STD"])
    edge_src = (ROOT / "modelo" / "preprocess.py").read_text(encoding="utf-8")
    checks.add(
        "preprocesamiento",
        "Se conserva preprocessing requerido",
        pre["resize"] == p3_transforms["EVAL_RESIZE"]
        and pre["mean"] == p3_mean == list(edge_pre["MEAN"])
        and pre["std"] == p3_std == list(edge_pre["STD"])
        and pre["image_size"] == edge_pre["IMAGE_SIZE"]
        and 'convert("RGB")' in edge_src
        and "Image.Resampling.BILINEAR" in edge_src,
        f"checkpoint: {pre['image_size']}x{pre['image_size']} {pre['resize']}, mean "
        f"{pre['mean']}, std {pre['std']}; igual a EVAL_RESIZE/IMAGENET_MEAN/IMAGENET_STD de "
        f"Proyecto3/src/p3/data/transforms.py y a IMAGE_SIZE/MEAN/STD de modelo/preprocess.py "
        f"(RGB, bilineal)",
    )

    # 9. Referencia al script y la configuracion de conversion
    convert_src = (ROOT / "modelo" / "convert.py").read_text(encoding="utf-8")
    lock = ROOT / "modelo" / "requirements-conversion.lock.txt"
    q = cfg["quantization"]
    tech = log["technique"]
    checks.add(
        "conversion.referencia",
        "Se conserva referencia al script/configuracion de conversion",
        lock.is_file()
        and 'default="modelo/conversion.yaml"' in convert_src
        and all(tech[k] == v for k, v in q.items())
        and tech["calibration_split"] == cfg["calibration"]["split"] == "train",
        "modelo/convert.py (lee modelo/conversion.yaml por defecto) + "
        "modelo/requirements-conversion.lock.txt; la tecnica del registro "
        f"({tech['technique']}, {tech['format']}, per_channel={tech['per_channel']}) es la de "
        "conversion.yaml",
    )

    # 10. El registro identifica entrada y salida
    io_ok = all(
        isinstance(item.get("sha256"), str) and len(item["sha256"]) == 64 and item.get("bytes")
        for item in (inp, log["outputs"]["fp32"], int8)
    )
    checks.add(
        "conversion.entrada_salida",
        "El registro de conversion identifica input y output",
        io_ok and bool(inp.get("s3")) and bool(int8.get("file")),
        f"input: {inp['s3']} sha256 {inp['sha256'][:12]}...; outputs: "
        f"{log['outputs']['fp32']['file']} {log['outputs']['fp32']['sha256'][:12]}..., "
        f"{int8['file']} {int8['sha256'][:12]}...",
    )

    # 11. Los registros versionados son los mismos que se publicaron
    mismatches = [
        name
        for name in ("conversion_log.json", "calibracion_manifest.jsonl", "smoke_test.json")
        if sha256_file(RECORDS / name) != published.get(name, {}).get("sha256")
    ]
    checks.add(
        "registros.publicados",
        "Los registros en Git son byte a byte los publicados en S3",
        not mismatches,
        "conversion_log.json, calibracion_manifest.jsonl y smoke_test.json tienen el SHA-256 "
        "de publicacion.json" + (f"; difieren: {mismatches}" if mismatches else ""),
    )

    # 12. El paquete publicado (clases + preprocesamiento del dispositivo) sale del registro
    pkg_sha = log["package"]["sha256"]
    rebuilt = {nl: sha256_bytes(rebuild_model_package(cfg, log, nl)) for nl in ("\n", "\r\n")}
    match = [repr(nl) for nl, digest in rebuilt.items() if digest == pkg_sha]
    checks.add(
        "paquete.reconstruido",
        "model_package.json publicado se reconstruye desde conversion_log",
        bool(match) and published.get("model_package.json", {}).get("sha256") == pkg_sha,
        f"SHA-256 reconstruido {pkg_sha} (finales de linea {', '.join(match) or 'ninguno'}) "
        "igual a conversion_log.package y publicacion.json: el paquete que lee el dispositivo "
        "declara exactamente esas clases y ese preprocesamiento",
    )

    # 13. Calibracion solo con train y con el manifiesto del P3
    rows = [
        json.loads(line)
        for line in (RECORDS / "calibracion_manifest.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line
    ]
    per_class: dict[str, int] = {}
    for row in rows:
        per_class[row["category_name"]] = per_class.get(row["category_name"], 0) + 1
    cal = log["calibration"]
    checks.add(
        "calibracion.train",
        "Calibracion solo con train del manifiesto del P3 seleccionado",
        {r["split"] for r in rows} == {"train"}
        and len(rows) == cfg["calibration"]["samples"] == tech["calibration_samples"]
        and dict(sorted(per_class.items())) == cal["per_class"]
        and cal["source_manifest_sha256"]
        == cfg["calibration"]["manifest_hash"]
        == selection["manifest_hash"]
        and all(EXPECTED_CLASSES[r["class_index"]] == r["category_name"] for r in rows),
        f"{len(rows)} recortes, todos de train ({per_class}); manifiesto "
        f"{selection['manifest_id']} {cal['source_manifest_sha256'][:12]}..., el mismo con el que "
        "se entreno el modelo seleccionado",
    )

    # 14. No se sustituye el modelo del equipo por uno externo
    checks.add(
        "origen.no_externo",
        "No se sustituye el modelo del equipo por un modelo externo",
        "from p3.model.build import load_checkpoint" in convert_src
        and 'source_sha != cfg["source"]["sha256"]' in convert_src
        and inp["architecture"]["name"] == p3_build["ARCHITECTURE"]
        and log["checks"]["fp32_vs_torch_max_abs_logit_diff"] <= 1e-3,
        "convert.py carga el checkpoint con load_checkpoint del P3 y se detiene si su SHA-256 "
        f"no es el de conversion.yaml; arquitectura {inp['architecture']['name']} del P3; "
        "ONNX FP32 igual a PyTorch (max |dlogit| "
        f"{log['checks']['fp32_vs_torch_max_abs_logit_diff']:.1e})",
    )

    return {
        "cfg": cfg,
        "log": log,
        "publication": publication,
        "ficha": {
            "original": {
                "version": src["p3_version"],
                "run_id": run_id,
                "s3": inp["s3"],
                "s3_version_id": src["s3_version_id"],
                "mlflow": selection["checkpoint_uri"],
                "sha256": src["sha256"],
                "bytes": inp["bytes"],
            },
            "variante": {
                "version": log["variant_version"],
                "s3": f"s3://{publication['bucket']}/{pub_int8.get('key')}",
                "s3_version_id": pub_int8.get("version_id"),
                "sha256": int8["sha256"],
                "bytes": int8["bytes"],
            },
            "class_map": {str(i): name for i, name in enumerate(inp["class_names"])},
            "preprocessing": pre,
            "conversion": {
                "script": "modelo/convert.py",
                "config": "modelo/conversion.yaml",
                "registro": "modelo/registros/conversion_log.json",
                "registro_sha256": published.get("conversion_log.json", {}).get("sha256"),
            },
        },
    }


# ---------------------------------------------------------------------------
# Nivel "local": copias locales de los binarios
# ---------------------------------------------------------------------------


def check_local(checks: Checks, ctx: dict) -> None:
    cfg, log = ctx["cfg"], ctx["log"]
    checkpoint = (ROOT / cfg["source"]["local_checkpoint"]).resolve()
    artifacts = ROOT / "artifacts" / log["variant_version"]
    targets = [
        ("local.original", "SHA-256 recalculado del model.pt local", checkpoint, log["input"]),
        *(
            (
                f"local.{name}",
                f"SHA-256 recalculado de {item['file']} local",
                artifacts / item["file"],
                item,
            )
            for name, item in log["outputs"].items()
        ),
    ]
    for check_id, criterio, path, expected in targets:
        if not path.is_file():
            checks.pending(check_id, criterio, f"no existe {path}")
            continue
        digest = sha256_file(path)
        checks.add(check_id, criterio, digest == expected["sha256"], f"{path.name} {digest}")


# ---------------------------------------------------------------------------
# Nivel "s3": objetos publicados
# ---------------------------------------------------------------------------


def s3_get(s3: Any, bucket: str, key: str) -> tuple[bytes, str | None]:
    response = s3.get_object(Bucket=bucket, Key=key)
    return response["Body"].read(), response.get("VersionId")


def s3_hash(s3: Any, bucket: str, key: str) -> tuple[str, int, str | None]:
    response = s3.get_object(Bucket=bucket, Key=key)
    digest, size = hashlib.sha256(), 0
    for chunk in response["Body"].iter_chunks(1 << 20):
        digest.update(chunk)
        size += len(chunk)
    return digest.hexdigest(), size, response.get("VersionId")


def check_s3(checks: Checks, ctx: dict, s3: Any) -> None:
    cfg, log, publication = ctx["cfg"], ctx["log"], ctx["publication"]
    src = cfg["source"]
    bucket = src["s3_bucket"]
    p3_prefix = f"{P3_MODELS_PREFIX}/{src['p3_version']}"

    digest, size, version_id = s3_hash(s3, bucket, src["s3_key"])
    checks.add(
        "s3.original",
        "SHA-256 recalculado del model.pt publicado por el P3",
        digest == src["sha256"]
        and size == log["input"]["bytes"]
        and version_id == src["s3_version_id"],
        f"s3://{bucket}/{src['s3_key']} VersionId {version_id}, {size} bytes, sha256 {digest}",
    )

    registry = json.loads(s3_get(s3, bucket, f"{P3_MODELS_PREFIX}/registry.json")[0])
    entry = next((e for e in registry["versions"] if e["version"] == src["p3_version"]), {})
    checks.add(
        "s3.registry_p3",
        "registry.json del P3 apunta al mismo model.pt",
        entry.get("run_id") == src["run_id"]
        and entry.get("sha256") == src["sha256"]
        and entry.get("key") == src["s3_key"]
        and entry.get("s3_version_id") == src["s3_version_id"],
        f"version {entry.get('version')}: run_id {entry.get('run_id')}, key {entry.get('key')}, "
        f"VersionId {entry.get('s3_version_id')}; activa: {registry.get('active_version')}",
    )

    class_map = json.loads(s3_get(s3, bucket, f"{p3_prefix}/class_map.json")[0])
    p3_order = [
        c["category_name"] for c in sorted(class_map["classes"], key=lambda c: c["class_index"])
    ]
    preprocessing = json.loads(s3_get(s3, bucket, f"{p3_prefix}/preprocessing.json")[0])
    model_version = json.loads(s3_get(s3, bucket, f"{p3_prefix}/model_version.json")[0])
    checks.add(
        "s3.paquete_p3",
        "Clases y preprocesamiento del paquete 1.0.0 del P3 iguales a los de la conversion",
        p3_order == log["input"]["class_names"] == EXPECTED_CLASSES
        and preprocessing == log["input"]["preprocessing"]
        and model_version["run_id"] == src["run_id"]
        and model_version["files"]["model.pt"]["sha256"] == src["sha256"],
        f"class_map.json={p3_order}; preprocessing.json={preprocessing}; model_version.json "
        f"run_id {model_version['run_id']}",
    )

    for obj in publication["objects"]:
        name = obj["key"].rsplit("/", 1)[-1]
        digest, size, version_id = s3_hash(s3, publication["bucket"], obj["key"])
        checks.add(
            f"s3.variante.{name}",
            f"SHA-256 recalculado de {name} publicado",
            digest == obj["sha256"] and size == obj["bytes"] and version_id == obj["version_id"],
            f"s3://{publication['bucket']}/{obj['key']} VersionId {version_id}, {size} bytes, "
            f"sha256 {digest}",
        )

    package = json.loads(
        s3_get(s3, publication["bucket"], f"{publication['prefix']}model_package.json")[0]
    )
    checks.add(
        "s3.model_package",
        "model_package.json publicado declara las clases y el preprocesamiento del P3",
        package["class_names"] == EXPECTED_CLASSES
        and package["source_p3_version"] == src["p3_version"]
        and all(package["preprocessing"][k] == v for k, v in log["input"]["preprocessing"].items()),
        f"class_map {package['class_map']}; source_p3_version {package['source_p3_version']}",
    )


def pending_binaries(checks: Checks) -> None:
    checks.pending(
        "binarios.sha256",
        "SHA-256 recalculado sobre los binarios (model.pt y model_int8.onnx)",
        "este nivel solo lee registros; correr con --profile <perfil del equipo> o --local",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--profile", help="perfil de AWS con lectura sobre el bucket del equipo")
    parser.add_argument("--local", action="store_true", help="recalcular SHA-256 de copias locales")
    parser.add_argument("--out", default="modelo/registros/linaje_verificacion.json")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    checks = Checks()
    ctx = check_records(checks)
    levels = ["registros"]
    if args.local:
        check_local(checks, ctx)
        levels.append("local")
    if args.profile:
        import boto3

        session = boto3.Session(profile_name=args.profile)
        identity = session.client("sts").get_caller_identity()["Arn"]
        check_s3(checks, ctx, session.client("s3"))
        levels.append(f"s3 ({identity})")
    if not args.local and not args.profile:
        pending_binaries(checks)

    summary = {state: sum(c.estado == state for c in checks) for state in (OK, FAIL, PENDING)}
    record = {
        "schema_version": 1,
        "tarea": "VAL-01",
        "verificado_en": datetime.now(UTC).isoformat(timespec="seconds"),
        "niveles": levels,
        "resumen": summary,
        "linaje_verificado": summary[FAIL] == 0,
        "ficha": ctx["ficha"],
        "comprobaciones": [asdict(c) for c in checks],
        "entorno": {"python": platform.python_version(), "platform": platform.platform()},
    }
    out = (ROOT / args.out).resolve()
    out.write_text(
        json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )

    for check in checks:
        print(f"[{check.estado:9}] {check.id}: {check.criterio}")
        if check.estado != OK:
            print(f"            {check.detalle}")
    print(f"\n{summary} -> {out.relative_to(ROOT).as_posix()}")
    if summary[FAIL]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
