"""Comandos de la demostracion en vivo (`validacion/demo_val.py`): funcionan y no escriben."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

PROYECTO4 = Path(__file__).resolve().parents[1]
SCRIPT = PROYECTO4 / "validacion" / "demo_val.py"
PAQUETE = PROYECTO4 / "evidencias" / "VAL-08"

pytestmark = pytest.mark.skipif(not PAQUETE.is_dir(), reason="sin paquete de VAL-08")


def correr(*args: str) -> str:
    resultado = subprocess.run(
        [sys.executable, "-I", str(SCRIPT), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return resultado.stdout


@pytest.mark.parametrize(
    ("args", "esperado"),
    [
        (("linaje",), "ba89ee435ce33e0f0cdd4e8ed84dfb50d74e5a3bc23c32af975085306ca02a12"),
        (("muestra", "0.1.3:a559"), "optimizado cat"),
        (("calidad",), "25/73 pp"),
        (("clase", "dog"), "recall 77/78"),
        (("latencia", "int8"), "= 113.506 ms"),
        (("latencia", "fp32"), "= 191.517 ms"),
        (("fila", "57"), "medicion"),
        (("tamano",), "74.7781 %"),
    ],
)
def test_cada_comando_reproduce_su_cifra(args, esperado):
    assert esperado in correr(*args)


def test_no_escribe_en_el_paquete():
    antes = {p: p.stat().st_mtime_ns for p in PAQUETE.rglob("*") if p.is_file()}
    for args in (("linaje",), ("calidad",), ("latencia",), ("tamano",)):
        correr(*args)
    despues = {p: p.stat().st_mtime_ns for p in PAQUETE.rglob("*") if p.is_file()}
    assert antes == despues
