from __future__ import annotations


class StrategyService:
    def __init__(self) -> None:
        self._current = {
            "family_id": "aurum_smc_hybrid",
            "title": "Project Aurum Hybrid SMC",
            "instrument": "XAUUSD",
            "symbol_default": "XAU_USD",
            "timeframe": "15m",
            "box_types": {
                "white_box": "Explicit liquidity sweep, POI, CHoCH, ATR risk, and breakeven logic.",
                "hybrid": "The same white-box candidate stream filtered by a gradient-boosted approval score.",
                "black_box": "Not first-class in this version. Black-box work is limited to setup scoring, not raw-bar strategy generation.",
            },
            "profiles": {
                "conservative": {
                    "swing_lookback": 5,
                    "sweep_atr_max": 0.6,
                    "poi_atr_threshold": 0.8,
                    "entry_offset": 0.35,
                    "stop_atr": 1.0,
                    "target_r": 2.0,
                    "breakeven_r": 1.0,
                    "order_ttl_bars": 4,
                },
                "balanced": {
                    "swing_lookback": 4,
                    "sweep_atr_max": 0.8,
                    "poi_atr_threshold": 0.6,
                    "entry_offset": 0.5,
                    "stop_atr": 1.0,
                    "target_r": 2.0,
                    "breakeven_r": 1.0,
                    "order_ttl_bars": 5,
                },
                "aggressive": {
                    "swing_lookback": 3,
                    "sweep_atr_max": 1.0,
                    "poi_atr_threshold": 0.45,
                    "entry_offset": 0.5,
                    "stop_atr": 0.9,
                    "target_r": 2.2,
                    "breakeven_r": 1.0,
                    "order_ttl_bars": 6,
                },
            },
            "workflow": [
                "Download 15m gold data from OANDA or import HistData M1.",
                "Run the white-box baseline on one profile.",
                "Run the hybrid comparison to train and evaluate setup scoring.",
                "Run a paper-week simulation before trusting webhook approvals.",
            ],
            "data_options": [
                {"symbol": "XAU_USD", "label": "Gold CFD (OANDA Practice)"},
            ],
            "data_providers": [
                {"provider": "auto", "label": "Auto"},
                {"provider": "oanda", "label": "OANDA Practice"},
            ],
        }

    def current(self) -> dict:
        return self._current

    def profiles(self) -> dict:
        return self._current["profiles"]
