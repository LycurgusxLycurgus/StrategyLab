from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from .hashing import canonical_json_bytes, sha256_bytes


class ArtifactStore:
    """Content-addressed, immutable artifact bundles."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _bundle_dir(self, kind: str, content_hash: str) -> Path:
        safe_kind = "".join(ch for ch in kind if ch.isalnum() or ch in "-_")
        return self.root / safe_kind / content_hash[:2] / content_hash

    @staticmethod
    def _atomic_write(path: Path, payload: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            if path.read_bytes() != payload:
                raise RuntimeError(f"immutable artifact collision at {path}")
            return
        handle, temp_name = tempfile.mkstemp(prefix=".tmp-", dir=path.parent)
        try:
            with os.fdopen(handle, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp_name, path)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)

    def put_bundle(
        self,
        kind: str,
        request: dict[str, Any],
        files: dict[str, bytes | str | dict[str, Any] | list[Any]],
    ) -> dict[str, Any]:
        request_bytes = canonical_json_bytes(request)
        content_hash = sha256_bytes(request_bytes)
        bundle_dir = self._bundle_dir(kind, content_hash)
        manifest_files: list[dict[str, Any]] = []
        normalized_files = {"request.json": request_bytes, **files}
        for relative_name, value in normalized_files.items():
            if Path(relative_name).is_absolute() or ".." in Path(relative_name).parts:
                raise ValueError(f"unsafe artifact name: {relative_name}")
            if isinstance(value, bytes):
                payload = value
            elif isinstance(value, str):
                payload = value.encode("utf-8")
            else:
                payload = canonical_json_bytes(value)
            target = bundle_dir / relative_name
            self._atomic_write(target, payload)
            manifest_files.append(
                {
                    "path": relative_name.replace("\\", "/"),
                    "sha256": sha256_bytes(payload),
                    "bytes": len(payload),
                }
            )
        manifest = {
            "schema_version": "1.0",
            "artifact_id": f"{kind}_{content_hash[:20]}",
            "kind": kind,
            "content_hash": content_hash,
            "files": sorted(manifest_files, key=lambda item: item["path"]),
        }
        manifest_bytes = canonical_json_bytes(manifest)
        self._atomic_write(bundle_dir / "manifest.json", manifest_bytes)
        return {
            **manifest,
            "artifact_path": bundle_dir.relative_to(self.root).as_posix(),
        }

    def read_json(self, artifact_path: str, relative_name: str) -> Any:
        target = (self.root / artifact_path / relative_name).resolve()
        target.relative_to(self.root)
        return json.loads(target.read_text(encoding="utf-8"))
