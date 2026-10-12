"""S3 en memoria con la semantica que usa el receptor: `If-None-Match: *` y metadatos.

No reemplaza a `botocore.stub.Stubber` (que valida nombres de parametros contra
el modelo real de S3, ver `test_persistencia.py`); sirve para probar secuencias:
reintentos, fallas a la mitad y carreras.
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from typing import Any

from botocore.exceptions import ClientError


def client_error(code: str, status: int, operation: str) -> ClientError:
    return ClientError(
        {"Error": {"Code": code, "Message": code}, "ResponseMetadata": {"HTTPStatusCode": status}},
        operation,
    )


@dataclass
class StoredObject:
    body: bytes
    content_type: str
    metadata: dict[str, str]
    version_id: str


@dataclass
class FakeS3:
    objects: dict[str, StoredObject] = field(default_factory=dict)
    calls: list[tuple[str, str]] = field(default_factory=list)
    # Errores a lanzar en la proxima llamada a una operacion: {"put_object": ClientError}.
    fail_next: dict[str, Exception] = field(default_factory=dict)
    # Llaves por pagina de `list_objects_v2` (S3 real: 1000), chico para probar la paginacion.
    page_size: int = 1000

    def _maybe_fail(self, operation: str) -> None:
        error = self.fail_next.pop(operation, None)
        if error is not None:
            raise error

    def put_object(self, *, Bucket: str, Key: str, Body: bytes, **kwargs: Any) -> dict[str, Any]:  # noqa: N803
        self.calls.append(("put_object", Key))
        self._maybe_fail("put_object")
        if kwargs.get("IfNoneMatch") == "*" and Key in self.objects:
            raise client_error("PreconditionFailed", 412, "PutObject")
        version = f"v{len(self.calls)}"
        self.objects[Key] = StoredObject(
            Body, kwargs.get("ContentType", ""), dict(kwargs.get("Metadata", {})), version
        )
        return {"VersionId": version}

    def head_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:  # noqa: N803
        self.calls.append(("head_object", Key))
        self._maybe_fail("head_object")
        if Key not in self.objects:
            raise client_error("404", 404, "HeadObject")
        stored = self.objects[Key]
        return {"Metadata": stored.metadata, "VersionId": stored.version_id}

    def get_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:  # noqa: N803
        self.calls.append(("get_object", Key))
        self._maybe_fail("get_object")
        if Key not in self.objects:
            raise client_error("NoSuchKey", 404, "GetObject")
        stored = self.objects[Key]
        return {"Body": io.BytesIO(stored.body), "ContentType": stored.content_type}

    def list_objects_v2(
        self,
        *,
        Bucket: str,  # noqa: N803
        Prefix: str = "",  # noqa: N803
        ContinuationToken: str | None = None,  # noqa: N803
    ) -> dict[str, Any]:
        self.calls.append(("list_objects_v2", Prefix))
        self._maybe_fail("list_objects_v2")
        keys = self.keys(Prefix)
        start = int(ContinuationToken or 0)
        page = keys[start : start + self.page_size]
        answer: dict[str, Any] = {
            "Contents": [{"Key": key, "Size": len(self.objects[key].body)} for key in page],
            "IsTruncated": start + self.page_size < len(keys),
        }
        if answer["IsTruncated"]:
            answer["NextContinuationToken"] = str(start + self.page_size)
        return answer

    def keys(self, prefix: str = "") -> list[str]:
        return sorted(key for key in self.objects if key.startswith(prefix))
