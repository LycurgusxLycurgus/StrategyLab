from __future__ import annotations

import json
from pathlib import Path

from app.features.strategies.schema import StrategyDraftRequest, StrategyManifest
from app.infra.config import AppConfig
from app.infra.logging import get_logger
from app.shared.errors import AppError


class StrategyService:
    def __init__(self, config: AppConfig):
        self.config = config
        self.logger = get_logger("strategylab.strategies")

    def list_families(self) -> list[StrategyManifest]:
        manifests: list[StrategyManifest] = []
        for manifest_path in sorted(self.config.strategies_dir.glob("*/manifest.json")):
            manifests.append(self._load_manifest_path(manifest_path))
        return manifests

    def get_family(self, family_id: str) -> StrategyManifest:
        manifest_path = self.config.strategies_dir / family_id / "manifest.json"
        if not manifest_path.exists():
            raise AppError(404, "STRATEGY_NOT_FOUND", "unknown strategy family", {"family_id": family_id})
        return self._load_manifest_path(manifest_path)

    def create_draft(self, payload: StrategyDraftRequest) -> StrategyManifest:
        if (self.config.strategies_dir / payload.new_family_id).exists():
            raise AppError(409, "STRATEGY_EXISTS", "strategy family already exists", {"family_id": payload.new_family_id})
        base = self.get_family(payload.base_family_id)
        manifest = StrategyManifest(
            family_id=payload.new_family_id,
            title=payload.title,
            class_type=base.class_type,
            asset=payload.asset,
            timeframe=payload.timeframe,
            parameters={**base.parameters, **payload.parameter_overrides},
            risk=base.risk,
            gates=base.gates,
            optimization_grid=base.optimization_grid,
            rules=base.rules,
            notes_path=f"strategies/families/{payload.new_family_id}/notes.md",
        )
        family_dir = self.config.strategies_dir / payload.new_family_id
        family_dir.mkdir(parents=True, exist_ok=False)
        (family_dir / "manifest.json").write_text(
            json.dumps(manifest.model_dump(), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        notes = payload.notes.strip() or f"Draft strategy cloned from {payload.base_family_id}."
        (family_dir / "notes.md").write_text(notes + "\n", encoding="utf-8")
        self.logger.info(
            "strategy draft created",
            extra={"extra_data": {"family_id": payload.new_family_id, "base_family_id": payload.base_family_id}},
        )
        return manifest

    def _load_manifest_path(self, manifest_path: Path) -> StrategyManifest:
        try:
            manifest = StrategyManifest(**json.loads(manifest_path.read_text(encoding="utf-8")))
            if not manifest.supported_timeframes:
                manifest.supported_timeframes = [manifest.timeframe]
            return manifest
        except Exception as exc:  # pragma: no cover
            raise AppError(
                500,
                "INVALID_STRATEGY_MANIFEST",
                "failed to load strategy manifest",
                {"path": str(manifest_path), "error": str(exc)},
            ) from exc
