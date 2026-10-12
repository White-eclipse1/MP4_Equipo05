"""Envia una captura al receptor `/api/p4/captures` como lo hara el dispositivo (F4, F6, F10).

Herramienta de prueba del lado del portal: NO es el programa de la Pi (F3, Bryan).
Arma el evento del contrato (`docs/contratos.md`), lo guarda en `--evento` ANTES
de enviarlo y, con `--reenviar`, vuelve a mandar exactamente ese mismo evento
(mismo `capture_id` y `captured_at`): asi se prueba el reintento sin duplicados.

El token se lee de `P4_DEVICE_TOKEN` en el entorno o en `--env-file` y nunca se
imprime.

Primer envio (una sola linea en la consola):

    python scripts/enviar_captura.py --foto C:/ruta/foto.jpg --evento C:/fuera/evento.json
        --capture-id f4-prueba-20261008-0001 --device-id f4-prueba --clase dog
        --confianza 0.8859 --captured-at 2026-10-08T23:35:54-06:00 --env-file ../Proyecto2/.env

Reintento identico:

    python scripts/enviar_captura.py --reenviar --foto C:/ruta/foto.jpg
        --evento C:/fuera/evento.json --env-file ../Proyecto2/.env
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import httpx

DEFAULT_URL = "http://localhost:8000/api/p4/captures"
MODEL_VERSION = "1.0.0-int8.1"
MODEL_SHA256 = "ca689c4e1478ccca7821dffaba8f07886bd9609a8aa3cec7450d9f875fbd69c0"


def read_token(env_file: Path | None) -> str:
    token = os.environ.get("P4_DEVICE_TOKEN", "")
    if not token and env_file is not None:
        for line in env_file.read_text(encoding="utf-8").splitlines():
            name, _, value = line.partition("=")
            if name.strip() == "P4_DEVICE_TOKEN":
                token = value.strip().strip('"').strip("'")
    if not token:
        sys.exit("Falta P4_DEVICE_TOKEN (en el entorno o en --env-file).")
    return token


def build_event(args: argparse.Namespace, photo: bytes) -> dict[str, object]:
    captured_at = args.captured_at or datetime.now().astimezone().isoformat(timespec="seconds")
    return {
        "schema_version": 1,
        "capture_id": args.capture_id,
        "captured_at": captured_at,
        "predicted_class": args.clase,
        "confidence": args.confianza,
        "device_id": args.device_id,
        "model_version": MODEL_VERSION,
        "model_sha256": MODEL_SHA256,
        "image_ref": args.image_ref or str(args.foto),
        "image_sha256": hashlib.sha256(photo).hexdigest(),
        "region": None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--foto", type=Path, required=True)
    parser.add_argument("--evento", type=Path, required=True, help="JSON del evento (se escribe)")
    parser.add_argument("--reenviar", action="store_true", help="reenvia el --evento existente")
    parser.add_argument("--capture-id")
    parser.add_argument("--device-id")
    parser.add_argument("--clase")
    parser.add_argument("--confianza", type=float)
    parser.add_argument("--captured-at", help="ISO 8601 con offset; por defecto, ahora")
    parser.add_argument("--image-ref", help="referencia local de la foto; por defecto, --foto")
    parser.add_argument("--env-file", type=Path)
    args = parser.parse_args()

    photo = args.foto.read_bytes()
    if args.reenviar:
        event = json.loads(args.evento.read_text(encoding="utf-8"))
    else:
        missing = [
            n for n in ("capture_id", "device_id", "clase", "confianza") if not getattr(args, n)
        ]
        if missing:
            parser.error(f"faltan: {', '.join('--' + m.replace('_', '-') for m in missing)}")
        event = build_event(args, photo)
        # Registro local ANTES del envio: el reintento reutiliza este mismo evento.
        args.evento.parent.mkdir(parents=True, exist_ok=True)
        args.evento.write_text(json.dumps(event, indent=2), encoding="utf-8")

    print("Evento enviado:")
    print(json.dumps(event, indent=2))
    try:
        answer = httpx.post(
            args.url,
            headers={"Authorization": f"Bearer {read_token(args.env_file)}"},
            data={"event": json.dumps(event)},
            files={"image": (args.foto.name, photo, "image/jpeg")},
            timeout=30,
        )
    except httpx.HTTPError as error:
        print(f"Sin respuesta del receptor ({type(error).__name__}: {error}).")
        print("Reintenta con --reenviar (mismo capture_id).")
        return 2
    print(f"HTTP {answer.status_code}")
    print(json.dumps(answer.json(), indent=2, ensure_ascii=False))
    return 0 if answer.status_code in (200, 201) else 1


if __name__ == "__main__":
    sys.exit(main())
