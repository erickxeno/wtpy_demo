"""Fetch ETF/stock K-line data via AKShare on the HOST and write wtpy-format CSV.

Runs on the macOS host (not inside the wtpy docker container) because:
- The container gets blocked by push2his.eastmoney.com (bot IP filtering)
- The host usually has working direct network access (after proxy bypass)

Output format matches wtpy's built-in CSV reader:
    <Date>, <Time>, <Open>, <High>, <Low>, <Close>, <Volume>

Usage:
    python scripts/fetch_akshare.py                   # defaults: 510300, 5min, qfq
    python scripts/fetch_akshare.py --symbol 510300 --period 5 --adjust qfq
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def _disable_proxy() -> None:
    """Clear proxy env vars so requests goes direct.

    macOS system proxy (Clash/V2Ray on 127.0.0.1:1087) is auto-picked by
    requests via environment, but push2his.eastmoney.com rejects proxied
    traffic. Set NO_PROXY=* to bypass.
    """
    for key in list(os.environ):
        if "proxy" in key.lower():
            del os.environ[key]
    os.environ["NO_PROXY"] = "*"
    os.environ["no_proxy"] = "*"


def _detect_market_prefix(symbol: str) -> str:
    """SSE codes start with 5, 6 (or 51/60 etc). SZSE with 0,1,3."""
    if symbol.startswith(("5", "6", "7", "9")):
        return "SSE"
    return "SZSE"


def fetch_etf_min(symbol: str, period: str, adjust: str,
                  start_date: str, end_date: str) -> "pd.DataFrame":
    """Fetch minute bars from **Sina** (quotes.sina.cn), bypassing proxy.

    AKShare's East Money-based function is blocked (both by bot filtering
    and by requests picking up macOS system proxy). Sina's endpoint is:
        https://quotes.sina.cn/cn/api/json_v2.php/CN_MarketDataService.getKLineData

    Limits:
      - Max 1023 rows per call (datalen cap)
      - At 5-min period, 1023 rows ≈ 21 trading days (~1 month)
      - Data only goes back from "today" — no arbitrary historical range
      - No adjust parameter (returns unadjusted); `adjust=` arg is accepted
        for API compatibility but ignored
    """
    import pandas as pd
    import requests

    prefix = "sh" if symbol.startswith(("5", "6", "7", "9")) else "sz"
    sina_symbol = f"{prefix}{symbol}"

    session = requests.Session()
    session.trust_env = False  # ignore macOS system proxy for this call

    url = "https://quotes.sina.cn/cn/api/json_v2.php/CN_MarketDataService.getKLineData"
    params = {
        "symbol": sina_symbol,
        "scale": period,      # same as East Money klt: 1/5/15/30/60
        "datalen": "1023",    # Sina's hard upper bound
        "ma": "no",
    }

    r = session.get(url, params=params, timeout=20, proxies={})
    r.raise_for_status()
    data = r.json()
    if not data:
        return pd.DataFrame(columns=["时间", "开盘", "收盘", "最高", "最低", "成交量"])

    df = pd.DataFrame(data)
    # Sina columns: day, open, high, low, close, volume, amount (amount only on daily)
    df = df.rename(columns={
        "day": "时间",
        "open": "开盘",
        "high": "最高",
        "low": "最低",
        "close": "收盘",
        "volume": "成交量",
    })

    # Client-side date filter
    df.index = pd.to_datetime(df["时间"])
    df = df.loc[start_date:end_date]
    df.reset_index(drop=True, inplace=True)

    for c in ["开盘", "收盘", "最高", "最低", "成交量"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df["时间"] = pd.to_datetime(df["时间"]).astype(str)
    return df[["时间", "开盘", "收盘", "最高", "最低", "成交量"]]


def to_wtpy_csv(df, out_path: Path) -> int:
    """Convert AKShare response to wtpy CSV format. Returns row count written."""
    import pandas as pd  # noqa: F401

    if df is None or len(df) == 0:
        print(f"[fetch] no data received; not writing {out_path}", file=sys.stderr)
        return 0

    # AKShare returns columns: 时间,开盘,收盘,最高,最低,涨跌幅,涨跌额,成交量,成交额,振幅,换手率
    # Parse "2026-03-06 09:35" → date "2026/3/6" and time "09:35:00"
    import pandas as pd
    dt = pd.to_datetime(df["时间"])

    out = pd.DataFrame({
        "<Date>": dt.dt.strftime("%Y/%-m/%-d"),
        " <Time>": dt.dt.strftime("%H:%M:%S"),
        " <Open>": df["开盘"].astype(float),
        " <High>": df["最高"].astype(float),
        " <Low>": df["最低"].astype(float),
        " <Close>": df["收盘"].astype(float),
        " <Volume>": df["成交量"].astype(float),
    })

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_path, index=False)
    return len(out)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--symbol", default="510300", help="ETF code, e.g. 510300 (沪深300ETF)")
    p.add_argument("--period", default="5", choices=["1", "5", "15", "30", "60"],
                   help="minute-bar period")
    p.add_argument("--adjust", default="qfq", choices=["", "qfq", "hfq"],
                   help="'' = no adjust, qfq = forward-adjusted, hfq = backward-adjusted")
    p.add_argument("--start", default="2020-01-01 09:30:00",
                   help="start datetime (AKShare filters client-side so wide range is fine)")
    p.add_argument("--end", default="2030-01-01 15:00:00",
                   help="end datetime")
    p.add_argument("--out-dir", default=None,
                   help="output CSV dir (default: ./bt/storage/csv/)")
    args = p.parse_args()

    _disable_proxy()

    market = _detect_market_prefix(args.symbol)
    # wtpy standard code: SSE.ETF.510300 — file name SSE.ETF.510300_m5.csv
    std_code = f"{market}.ETF.{args.symbol}"
    period_tag = f"m{args.period}"

    out_dir = Path(args.out_dir) if args.out_dir else Path(__file__).resolve().parent.parent / "bt" / "storage" / "csv"
    out_file = out_dir / f"{std_code}_{period_tag}.csv"

    print(f"[fetch] symbol={std_code} period={period_tag} adjust={args.adjust!r}")
    print(f"[fetch] range={args.start} → {args.end}")
    print(f"[fetch] output={out_file}")

    df = fetch_etf_min(args.symbol, args.period, args.adjust, args.start, args.end)
    if df is None or len(df) == 0:
        print("[fetch] FAIL: no rows returned", file=sys.stderr)
        return 2

    print(f"[fetch] received {len(df)} rows, range "
          f"{df['时间'].min()} → {df['时间'].max()}")

    n = to_wtpy_csv(df, out_file)
    print(f"[fetch] wrote {n} rows to {out_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
