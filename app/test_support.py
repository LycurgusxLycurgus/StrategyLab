from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.domain import Bar


def make_xau_fixture(symbol: str = "GC=F", timeframe: str = "15m", bars_count: int = 640) -> list[Bar]:
    start = datetime(2026, 1, 5, 0, 0, tzinfo=UTC)
    bars: list[Bar] = []
    price = 2650.0
    for index in range(bars_count):
        ts = start + timedelta(minutes=15 * index)
        day = index // 96
        bar_in_day = index % 96
        base = 2650.0 + (day * 1.4)
        wobble = ((bar_in_day % 6) - 3) * 0.01
        open_price = base + wobble
        close = base + wobble + 0.01
        high = max(open_price, close) + 0.08
        low = min(open_price, close) - 0.08

        long_winner = day % 2 == 0
        short_winner = day % 2 == 0

        if bar_in_day == 28:
            open_price, high, low, close = base - 0.02, base + 0.08, base - 0.22, base + 0.05
        elif bar_in_day == 29:
            open_price, high, low, close = base + 0.05, base + 0.38, base + 0.02, base + 0.32
        elif bar_in_day == 30:
            open_price, high, low, close = base + 0.34, base + 0.92, base + 0.22, base + 0.84
        elif bar_in_day == 31:
            open_price, high, low, close = base + 0.70, base + 0.76, base + 0.12, base + 0.28
        elif bar_in_day == 32:
            if long_winner:
                open_price, high, low, close = base + 0.30, base + 1.72, base + 0.26, base + 1.55
            else:
                open_price, high, low, close = base + 0.18, base + 0.22, base - 0.68, base - 0.52

        elif bar_in_day == 48:
            open_price, high, low, close = base + 0.02, base + 0.22, base - 0.08, base - 0.05
        elif bar_in_day == 49:
            open_price, high, low, close = base - 0.05, base - 0.02, base - 0.38, base - 0.32
        elif bar_in_day == 50:
            open_price, high, low, close = base - 0.34, base - 0.22, base - 0.92, base - 0.84
        elif bar_in_day == 51:
            open_price, high, low, close = base - 0.70, base - 0.12, base - 0.76, base - 0.28
        elif bar_in_day == 52:
            if short_winner:
                open_price, high, low, close = base - 0.30, base - 0.26, base - 1.72, base - 1.55
            else:
                open_price, high, low, close = base - 0.18, base + 0.68, base - 0.22, base + 0.52

        bars.append(
            Bar(
                ts=ts,
                open=round(open_price, 4),
                high=round(high, 4),
                low=round(low, 4),
                close=round(close, 4),
                volume=1000 + (bar_in_day % 7) * 40,
                symbol=symbol,
                timeframe=timeframe,
            )
        )
        price = close
    return bars
