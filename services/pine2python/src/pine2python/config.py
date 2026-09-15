from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True, slots=True)
class Settings:
    host: str = os.getenv("P2P_HOST", "127.0.0.1")
    port: int = int(os.getenv("P2P_PORT", "8080"))
    artifact_root: Path = Path(
        os.getenv("P2P_ARTIFACT_ROOT", str(SERVICE_ROOT / "artifacts"))
    ).resolve()
    work_root: Path = Path(
        os.getenv("P2P_WORK_ROOT", str(SERVICE_ROOT / ".work"))
    ).resolve()
    node_bin: str = os.getenv("P2P_NODE_BIN", "node")
    worker_path: Path = Path(
        os.getenv("P2P_WORKER_PATH", str(SERVICE_ROOT / "runtime" / "worker.mjs"))
    ).resolve()
    max_source_bytes: int = int(os.getenv("P2P_MAX_SOURCE_BYTES", "1000000"))
    max_bars: int = int(os.getenv("P2P_MAX_BARS", "200000"))
    max_worker_output_bytes: int = int(
        os.getenv("P2P_MAX_WORKER_OUTPUT_BYTES", "75000000")
    )
    worker_timeout_seconds: float = float(os.getenv("P2P_WORKER_TIMEOUT_SECONDS", "20"))

    def ensure_dirs(self) -> None:
        self.artifact_root.mkdir(parents=True, exist_ok=True)
        self.work_root.mkdir(parents=True, exist_ok=True)


settings = Settings()
