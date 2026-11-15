"""Checksum-verified raw taker-quote flow aligned to accepted candles."""
import csv
import io
import math
from pathlib import Path
from app.btc_liquidity_data import _months, _load_manifest, _open_archive_member, _is_header


def load_flow(raw_root, bars5):
    root = Path(raw_root)
    manifest = _load_manifest(root)
    out = []
    for month in _months():
        archive, member = _open_archive_member(root, month, manifest)
        count = 0
        try:
            for line, row in enumerate(csv.reader(io.TextIOWrapper(member, encoding='utf-8', newline='')), 1):
                if line == 1 and _is_header(row):
                    continue
                if len(row) < 11 or len(out) >= len(bars5):
                    raise ValueError('Invalid flow row count/schema')
                try:
                    t = int(row[0]); o, h, l, c, base = map(float, row[1:6])
                    quote, buy_base, buy_quote = float(row[7]), float(row[9]), float(row[10])
                except (TypeError, ValueError) as exc:
                    raise ValueError('Invalid flow row') from exc
                b = bars5[len(out)]
                if t != b.t or not month.first_ms <= t < month.next_month_ms or (o,h,l,c,base) != (b.open,b.high,b.low,b.close,b.volume):
                    raise ValueError('Flow candle alignment mismatch')
                vals = (base, quote, buy_base, buy_quote)
                if any(not math.isfinite(x) or x < 0 for x in vals) or buy_base > base or buy_quote > quote:
                    raise ValueError('Invalid taker flow values')
                sell_base, sell_quote = base-buy_base, quote-buy_quote
                for bv, qv in ((base,quote),(buy_base,buy_quote),(sell_base,sell_quote)):
                    if (bv == 0) != (qv == 0) or (bv > 0 and not b.low*(1-1e-5) <= qv/bv <= b.high*(1+1e-5)):
                        raise ValueError('Inconsistent quote/base flow')
                out.append({'quote':quote,'taker_buy_quote':buy_quote}); count += 1
        finally:
            member.close(); archive.close()
        if count != month.expected_rows:
            raise ValueError('Incomplete monthly flow archive')
    if len(out) != len(bars5):
        raise ValueError('Flow count mismatch')
    return out


def aggregate_flow_15m(flow5):
    """Sum the validated components of each complete 5-minute triplet."""
    if len(flow5) % 3:
        raise ValueError('Incomplete 15-minute flow triplet')
    out = []
    for i in range(0, len(flow5), 3):
        quote = buy = 0.0
        for item in flow5[i:i+3]:
            try:
                q, b = item['quote'], item['taker_buy_quote']
                valid = all(math.isfinite(x) and x >= 0 for x in (q, b)) and b <= q
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError('Invalid flow schema or values') from exc
            if not valid:
                raise ValueError('Invalid flow values')
            quote += q
            buy += b
        if not math.isfinite(quote) or not math.isfinite(buy):
            raise ValueError('Nonfinite aggregated flow')
        out.append({'quote': quote, 'taker_buy_quote': buy})
    return out
