"""Demostracion en vivo de calidad y recursos (guion, pasos 1 y 9): calculos paso a paso.

Solo lee el paquete `evidencias/VAL-08/` (los mismos archivos que recibe el evaluador) y
solo usa la biblioteca estandar. **No escribe nada**: se puede correr cuantas veces haga
falta durante la evaluacion sin cambiar la evidencia.

    cd Proyecto4
    python validacion/demo_val.py linaje                 # paso 1: de donde viene el modelo
    python validacion/demo_val.py muestra 0.1.3:a559     # paso 9: una imagen elegida
    python validacion/demo_val.py calidad                # accuracy, F1 macro y caida en pp
    python validacion/demo_val.py clase dog              # precision, recall y F1 de una clase
    python validacion/demo_val.py latencia int8          # p50/p95 desde los tiempos crudos
    python validacion/demo_val.py fila 57                # una fila cruda del benchmark
    python validacion/demo_val.py tamano                 # tamanos y reduccion
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
import sys
from collections import Counter
from fractions import Fraction
from pathlib import Path
from typing import Any

PAQUETE = Path(__file__).resolve().parents[1] / "evidencias" / "VAL-08"
CLASES = ("cat", "dog", "person")


def leer_json(ruta: str) -> Any:
    return json.loads((PAQUETE / ruta).read_text(encoding="utf-8"))


def leer_csv(ruta: str) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO((PAQUETE / ruta).read_text(encoding="utf-8"))))


def softmax(logits: list[float]) -> list[float]:
    maximo = max(logits)
    exp = [math.exp(x - maximo) for x in logits]
    total = math.fsum(exp)
    return [x / total for x in exp]


def linaje(_args: argparse.Namespace) -> None:
    ficha = leer_json("modelo/ficha_modelos.json")
    linaje_json = leer_json("modelo/linaje_verificacion.json")
    seleccion = linaje_json["ficha"]["original"]
    o, v = ficha["original"], ficha["optimizado"]
    print("Cadena del modelo (VAL-01):\n")
    print(f"  P3  {o['archivo']} version {o['version']}, run de MLflow {o['run_id']}")
    print(f"      SHA-256 {o['sha256']}")
    print(f"      publicado por el P3: {o['publicado_por_p3']}")
    print(f"      el mismo archivo en el P4: {o['s3']}")
    print("   |  convertir.py + conversion.yaml (INT8 estatico QDQ, calibracion solo con train)")
    print("   v  registro_conversion.json: entrada y salidas con SHA-256")
    print(f"  P4  {v['archivo']} version {v['version']}")
    print(f"      SHA-256 {v['sha256']}   <- el hash que imprime la Raspberry al cargar")
    print(
        f"      clases {ficha['clases']}; entrada {ficha['preprocesamiento']['image_size']}x"
        f"{ficha['preprocesamiento']['image_size']}, media/desviacion de ImageNet"
    )
    print(
        f"\nVerificacion de linaje: {linaje_json['resumen']} (niveles: "
        f"{', '.join(linaje_json['niveles'])})"
    )
    print(
        f"El run {seleccion['run_id'][:12]}... es el que selecciono el P3 en selection.json; "
        "los tres hashes se recalcularon sobre S3."
    )


def muestra(args: argparse.Namespace) -> None:
    cid = args.sample_id
    manifiesto = {
        json.loads(x)["crop_id"]: json.loads(x)
        for x in (PAQUETE / "validacion/manifest_val.jsonl").read_text("utf-8").splitlines()
    }
    if cid not in manifiesto:
        raise SystemExit(f"{cid} no es una muestra de val; ejemplos: {list(manifiesto)[:5]}")
    original = {
        f["sample_id"]: f for f in leer_csv("validacion/primarios/comparacion_val_val02.csv")
    }
    edge = {f["id"]: f for f in leer_csv("validacion/primarios/resultados_raspberry_val07.csv")}
    formal = {f["sample_id"]: f for f in leer_csv("validacion/predicciones_val.csv")}
    m, o, e, f = manifiesto[cid], original[cid], edge[cid], formal[cid]
    print(f"Muestra {cid}  (manifiesto {m['release_id']}, imagen {m['source_file_name']})")
    print(f"  clase real (manifiesto):     {m['category_name']} (class_index {m['class_index']})")
    probs_o = [float(o[f"prob_original_{c}"]) for c in CLASES]
    print(f"  original (PyTorch, VAL-02):  {fmt(probs_o)} -> {o['original_prediction']}")
    logits = [float(e[f"int8_logit_{c}"]) for c in CLASES]
    probs_i = softmax(logits)
    print(f"  INT8 en la Raspberry, logits {fmt(logits, 4)}")
    print(f"     softmax:                  {fmt(probs_i)} -> {CLASES[probs_i.index(max(probs_i))]}")
    print(
        f"  archivo formal (VAL-03):     original {f['original_prediction']}, "
        f"optimizado {f['optimized_prediction']}"
    )
    iguales = "si" if o["original_prediction"] == f["optimized_prediction"] else "NO"
    print(f"  coinciden original e INT8:   {iguales}")
    print(
        f"  tensor preprocesado en el edge: {e['tensor_sha256'][:16]}... "
        f"(identico al de la laptop en VAL-07)"
    )


def fmt(valores: list[float], decimales: int = 4) -> str:
    return (
        "["
        + ", ".join(f"{c} {v:.{decimales}f}" for c, v in zip(CLASES, valores, strict=True))
        + "]"
    )


def calidad(_args: argparse.Namespace) -> None:
    filas = leer_csv("validacion/predicciones_val.csv")
    n = len(filas)
    ao = sum(f["original_prediction"] == f["true_class"] for f in filas)
    ai = sum(f["optimized_prediction"] == f["true_class"] for f in filas)
    caida = Fraction(ao - ai, n) * 100
    declarado = leer_json("validacion/metricas_val.json")
    print(f"Desde validacion/predicciones_val.csv ({n} muestras de val):\n")
    print(f"  accuracy original   = {ao}/{n} = {ao / n * 100:.3f} %")
    print(f"  accuracy optimizado = {ai}/{n} = {ai / n * 100:.3f} %")
    print(
        f"  caida = ({ao} - {ai}) / {n} x 100 = {caida.numerator}/{caida.denominator} pp "
        f"= {float(caida):.4f} pp  ->  <= 2 pp: {caida <= 2} (fraccion exacta, sin redondear)"
    )
    for modelo, columna in (
        ("original", "original_prediction"),
        ("optimizado", "optimized_prediction"),
    ):
        f1s = [f1_clase(filas, columna, c)[3] for c in CLASES]
        macro = sum(f1s, Fraction(0)) / 3
        print(
            f"  F1 macro {modelo:10} = promedio de {[f'{float(x):.4f}' for x in f1s]} "
            f"= {float(macro) * 100:.3f} %"
        )
    distintas = [
        f["sample_id"] for f in filas if f["original_prediction"] != f["optimized_prediction"]
    ]
    print(f"\n  muestras donde difieren: {distintas}")
    print(
        f"  declarado en metricas_val.json: caida {declarado['caida_accuracy']['pp_fraccion']} pp"
    )


def f1_clase(filas: list[dict[str, str]], columna: str, clase: str) -> tuple:
    confusion = Counter((f["true_class"], f[columna]) for f in filas)
    tp = confusion[(clase, clase)]
    fp = sum(confusion[(t, clase)] for t in CLASES if t != clase)
    fn = sum(confusion[(clase, p)] for p in CLASES if p != clase)
    p = Fraction(tp, tp + fp) if tp + fp else Fraction(0)
    r = Fraction(tp, tp + fn) if tp + fn else Fraction(0)
    f1 = 2 * p * r / (p + r) if p + r else Fraction(0)
    return tp, fp, fn, f1, p, r


def clase(args: argparse.Namespace) -> None:
    filas = leer_csv("validacion/predicciones_val.csv")
    print(f"Clase {args.clase} desde validacion/predicciones_val.csv:\n")
    for modelo, columna in (
        ("original", "original_prediction"),
        ("optimizado", "optimized_prediction"),
    ):
        tp, fp, fn, f1, p, r = f1_clase(filas, columna, args.clase)
        print(f"  {modelo:10} TP {tp}, FP {fp}, FN {fn}, support {tp + fn}")
        print(
            f"             precision {tp}/{tp + fp} = {float(p) * 100:.2f} %, recall "
            f"{tp}/{tp + fn} = {float(r) * 100:.2f} %, F1 = 2PR/(P+R) = {float(f1) * 100:.2f} %"
        )


def latencia(args: argparse.Namespace) -> None:
    filas = leer_csv("benchmark/tiempos.csv")
    propias = [f for f in filas if f["modelo"] == args.modelo]
    calentamientos = [f for f in propias if f["fase"] == "calentamiento"]
    validas = sorted(
        float(f["ms_total"]) for f in propias if f["fase"] == "medicion" and f["valido"] == "True"
    )
    n = len(validas)
    print(f"{args.modelo} en la Raspberry, desde benchmark/tiempos.csv:")
    print(
        f"  {len(calentamientos)} calentamientos excluidos: "
        f"{[round(float(f['ms_total']), 1) for f in calentamientos]} ms"
    )
    print(f"  {n} mediciones validas (preprocesamiento + inferencia), ordenadas de menor a mayor")
    for p in (50, 95):
        h = (n - 1) * p / 100
        piso = math.floor(h)
        valor = validas[piso] + (h - piso) * (validas[piso + 1] - validas[piso])
        print(
            f"  p{p}: h = ({n} - 1) x {p}/100 = {h:.2f} -> x[{piso}] = {validas[piso]:.3f} y "
            f"x[{piso + 1}] = {validas[piso + 1]:.3f}; {validas[piso]:.3f} + {h - piso:.2f} x "
            f"({validas[piso + 1]:.3f} - {validas[piso]:.3f}) = {valor:.3f} ms"
        )
    declarado = leer_json("benchmark/recursos_edge.json")["latencia_edge"][args.modelo]["ms_total"]
    print(
        f"  declarado en recursos_edge.json: p50 {declarado['p50']:.3f}, p95 {declarado['p95']:.3f}"
    )
    print(f"  minimo {validas[0]:.3f} ms, maximo {validas[-1]:.3f} ms")


def fila(args: argparse.Namespace) -> None:
    filas = leer_csv("benchmark/tiempos.csv")
    f = next(
        (f for f in filas if f["modelo"] == args.modelo and f["indice"] == str(args.indice)), None
    )
    if f is None:
        raise SystemExit(f"No hay fila {args.indice} para {args.modelo} (0 a 209)")
    print(f"benchmark/tiempos.csv, modelo {args.modelo}, indice {args.indice}:")
    for clave in (
        "fase",
        "repeticion",
        "imagen",
        "ms_preprocesamiento",
        "ms_inferencia",
        "ms_total",
        "valido",
        "clase_predicha",
        "confianza",
        "temperatura_c",
    ):
        print(f"  {clave:20} {f[clave]}")
    print("  (fase 'calentamiento' = excluida del calculo; 'medicion' = cuenta para p50/p95)")


def tamano(_args: argparse.Namespace) -> None:
    ficha = leer_json("modelo/ficha_modelos.json")
    o, v, f = ficha["original"], ficha["optimizado"], ficha["fp32_onnx"]
    red = Fraction(o["bytes"] - v["bytes"], o["bytes"]) * 100
    print(
        "Desde modelo/ficha_modelos.json (bytes verificados por SHA-256 en S3 y en la Raspberry):\n"
    )
    print(f"  original   {o['archivo']:16} {o['bytes']:>12,} B  sha256 {o['sha256'][:16]}...")
    print(f"  FP32 ONNX  {f['archivo']:16} {f['bytes']:>12,} B  sha256 {f['sha256'][:16]}...")
    print(f"  optimizado {v['archivo']:16} {v['bytes']:>12,} B  sha256 {v['sha256'][:16]}...")
    print(
        f"  reduccion = ({o['bytes']} - {v['bytes']}) / {o['bytes']} x 100 = {float(red):.4f} % "
        f"({o['bytes'] / v['bytes']:.2f} veces menor)"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="orden", required=True)
    sub.add_parser("linaje").set_defaults(fn=linaje)
    p = sub.add_parser("muestra")
    p.add_argument("sample_id")
    p.set_defaults(fn=muestra)
    sub.add_parser("calidad").set_defaults(fn=calidad)
    p = sub.add_parser("clase")
    p.add_argument("clase", choices=CLASES)
    p.set_defaults(fn=clase)
    p = sub.add_parser("latencia")
    p.add_argument("modelo", choices=("int8", "fp32"), nargs="?", default="int8")
    p.set_defaults(fn=latencia)
    p = sub.add_parser("fila")
    p.add_argument("indice", type=int)
    p.add_argument("modelo", choices=("int8", "fp32"), nargs="?", default="int8")
    p.set_defaults(fn=fila)
    sub.add_parser("tamano").set_defaults(fn=tamano)
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    args.fn(args)


if __name__ == "__main__":
    main()
