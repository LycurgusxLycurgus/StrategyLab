from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Any, Sequence


@dataclass(frozen=True, slots=True)
class ChronologicalSplit:
    development_ids: tuple[str, ...]
    holdout_ids: tuple[str, ...]
    walk_forward: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...]


def chronological_split(operations: Sequence[dict[str, Any]], holdout_fraction: float = 0.25, folds: int = 3) -> ChronologicalSplit:
    ordered = sorted(operations, key=lambda item: (item["opened_at"], item["execution_id"]))
    if not ordered:
        return ChronologicalSplit((), (), ())
    holdout_count = max(1, int(len(ordered) * holdout_fraction)) if len(ordered) >= 2 else 0
    development = ordered[:-holdout_count] if holdout_count else ordered
    holdout = ordered[-holdout_count:] if holdout_count else []
    windows: list[tuple[tuple[str, ...], tuple[str, ...]]] = []
    if len(development) >= 2:
        boundaries = [int(len(development) * ratio / (folds + 1)) for ratio in range(1, folds + 2)]
        for index, boundary in enumerate(boundaries[:-1]):
            boundary = max(1, boundary)
            test_end = max(boundary + 1, boundaries[index + 1])
            train = development[:boundary]
            test = development[boundary:test_end]
            if train and test:
                windows.append((tuple(item["execution_id"] for item in train), tuple(item["execution_id"] for item in test)))
    return ChronologicalSplit(
        tuple(item["execution_id"] for item in development),
        tuple(item["execution_id"] for item in holdout),
        tuple(windows),
    )


def pnl_metrics(results: Sequence[dict[str, Any]]) -> dict[str, float | int]:
    pnls = [float(item["net_pnl"]) for item in results if item.get("net_pnl") is not None]
    gross_profit = sum(value for value in pnls if value > 0)
    gross_loss = abs(sum(value for value in pnls if value < 0))
    equity = 0.0
    peak = 0.0
    max_drawdown = 0.0
    for value in pnls:
        equity += value
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, peak - equity)
    return {
        "operations": len(pnls),
        "net_pnl": gross_profit - gross_loss,
        "gross_profit_net": gross_profit,
        "gross_loss_net": gross_loss,
        "profit_factor": gross_profit / gross_loss if gross_loss else (999999.0 if gross_profit else 0.0),
        "max_drawdown_money": max_drawdown,
        "win_rate": sum(value > 0 for value in pnls) / len(pnls) if pnls else 0.0,
        "expectancy": sum(pnls) / len(pnls) if pnls else 0.0,
    }


def dual_promotion_improvement(candidate: dict[str, Any], baseline: dict[str, Any]) -> bool:
    return (
        float(candidate["gross_profit_net"]) > float(baseline["gross_profit_net"])
        and float(candidate["gross_loss_net"]) < float(baseline["gross_loss_net"])
    )


def full_promotion_improvement(candidate: dict[str, Any], baseline: dict[str, Any]) -> bool:
    return (
        dual_promotion_improvement(candidate, baseline)
        and float(candidate["net_pnl"]) > float(baseline["net_pnl"])
        and float(candidate["profit_factor"]) >= float(baseline["profit_factor"])
        and float(candidate["max_drawdown_money"]) <= float(baseline["max_drawdown_money"])
    )


def paired_block_bootstrap_equivalence(
    left: dict[str, dict[str, Any]], right: dict[str, dict[str, Any]],
    ordered_ids: Sequence[str], *, seed: int, samples: int = 2000,
    block_length: int = 3, confidence: float = 0.95,
) -> dict[str, Any]:
    """Compare paired net-P&L paths; it is a tie-breaker, never a promotion gate."""
    ids = [item for item in ordered_ids if item in left and item in right]
    deltas = [
        float(left[item].get("net_pnl") or 0) - float(right[item].get("net_pnl") or 0)
        for item in ids
    ]
    config = {
        "seed": seed, "samples": samples, "block_length": block_length,
        "confidence": confidence, "operations": len(deltas),
    }
    if not deltas:
        return {**config, "ci_low": 0.0, "ci_high": 0.0, "equivalent": True}
    rng = random.Random(seed)
    width = max(1, min(int(block_length), len(deltas)))
    means: list[float] = []
    for _ in range(max(1, int(samples))):
        sample: list[float] = []
        while len(sample) < len(deltas):
            start = rng.randrange(len(deltas))
            sample.extend(deltas[(start + offset) % len(deltas)] for offset in range(width))
        sample = sample[:len(deltas)]
        means.append(sum(sample) / len(sample))
    means.sort()
    tail = (1.0 - confidence) / 2.0
    low_index = min(len(means) - 1, max(0, int(tail * len(means))))
    high_index = min(len(means) - 1, max(0, int((1.0 - tail) * len(means)) - 1))
    low, high = means[low_index], means[high_index]
    return {
        **config, "observed_mean_delta": sum(deltas) / len(deltas),
        "ci_low": low, "ci_high": high, "equivalent": low <= 0 <= high,
    }
