"""Checksum-verified 5m quote turnover adapter; no downloads."""
import csv
import io
import math
from pathlib import Path
from app.btc_liquidity_data import _months, _load_manifest, _open_archive_member, _is_header

def load_quote_turnover(raw_root: Path, bars5):
    root=Path(raw_root); manifest=_load_manifest(root); values=[]; index=0
    for month in _months():
        archive, member=_open_archive_member(root,month,manifest)
        count=0
        try:
            reader=csv.reader(io.TextIOWrapper(member,encoding='utf-8',newline=''))
            for line,row in enumerate(reader,1):
                if line==1 and _is_header(row): continue
                if len(row)<8 or index>=len(bars5): raise ValueError('Invalid turnover row count/schema')
                try: t=int(row[0]); base=float(row[5]); quote=float(row[7])
                except (ValueError,TypeError) as exc: raise ValueError('Invalid turnover row') from exc
                b=bars5[index]
                if t!=b.t or not month.first_ms<=t<month.next_month_ms or base!=b.volume or not math.isfinite(quote) or quote<0 or (base==0)!=(quote==0) or (base>0 and not b.low*(1-1e-5)<=quote/base<=b.high*(1+1e-5)):
                    raise ValueError(f'Turnover alignment or value mismatch at {index}')
                values.append(quote); index+=1; count+=1
        finally:
            member.close(); archive.close()
        if count!=month.expected_rows: raise ValueError('Incomplete monthly turnover archive')
    if index!=len(bars5): raise ValueError('Turnover count mismatch')
    return values
