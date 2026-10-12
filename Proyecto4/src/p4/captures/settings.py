"""Configuracion del receptor de capturas, leida del entorno (decision 5).

- Destino: bucket y prefijo de S3 (`edge-captures/` en el bucket de releases).
- Credenciales: `P4_AWS_PROFILE` solo en desarrollo local (perfil de `~/.aws`
  montado en el contenedor). Vacio = cadena estandar de boto3 (rol de instancia
  o de tarea en el despliegue): en produccion no hay llaves personales.
- Token del dispositivo: `P4_DEVICE_TOKEN`. Sin token el receptor no acepta
  envios (503): nunca queda abierto por olvido.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Variante de F2 (`docs/artefacto.md`): version=sha256 del `model_int8.onnx`.
DEFAULT_ACCEPTED_MODELS = (
    "1.0.0-int8.1=ca689c4e1478ccca7821dffaba8f07886bd9609a8aa3cec7450d9f875fbd69c0"
)


class CaptureSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    bucket: str = Field(default="dataset-quality-releases-750702272375", alias="P4_CAPTURES_BUCKET")
    prefix: str = Field(default="edge-captures/", alias="P4_CAPTURES_PREFIX")
    aws_profile: str | None = Field(default=None, alias="P4_AWS_PROFILE")
    aws_region: str = Field(default="us-east-1", alias="P4_AWS_REGION")
    device_token: SecretStr | None = Field(default=None, alias="P4_DEVICE_TOKEN")
    # `version=sha256` separados por coma.
    accepted_models: str = Field(default=DEFAULT_ACCEPTED_MODELS, alias="P4_ACCEPTED_MODELS")
    max_image_bytes: int = Field(default=5 * 1024 * 1024, alias="P4_MAX_IMAGE_BYTES")
    # El evento real pesa menos de 1 KB; 16 KiB deja margen (p. ej. rutas largas en image_ref).
    max_event_bytes: int = Field(default=16 * 1024, alias="P4_MAX_EVENT_BYTES")

    @field_validator("aws_profile", "device_token", mode="before")
    @classmethod
    def _empty_is_none(cls, value: object) -> object:
        # En `.env` una variable vacia llega como "": significa "sin valor".
        return None if isinstance(value, str) and not value.strip() else value

    @field_validator("prefix")
    @classmethod
    def _prefix_slash(cls, value: str) -> str:
        return value if value.endswith("/") else f"{value}/"

    def models(self) -> dict[str, str]:
        """Versiones aceptadas y el SHA-256 que corresponde a cada una."""
        pairs = (item.split("=", 1) for item in self.accepted_models.split(",") if "=" in item)
        return {version.strip(): sha.strip().lower() for version, sha in pairs}


@lru_cache
def get_settings() -> CaptureSettings:
    return CaptureSettings()
