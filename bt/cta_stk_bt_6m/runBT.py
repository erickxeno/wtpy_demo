"""Backtest DualThrust on SSE.ETF.510300 using 6 months of daily bars.

Data: fetched by scripts/fetch-data.sh --period d (Sina via AKShare path),
range 2025-10-23 → 2026-04-21 (~120 trading days).

Why daily, not 5-min? WtBtEngine's CSV loader hardcodes reading
`<code>_m5.csv` as the base intraday source and resamples upward, so any
minute strategy requires 5-min coverage for the full window. Sina's
datalen cap is 1970 rows (~2 months at m5), which is not enough. Daily
bars are a clean fit for 6 months: 120 rows, wtpy loads `_d.csv`
directly, no resampling dependency.

Strategy parameters tuned for this window:
- period="d1" (matches the fetched CSV; ends in `_d.csv`)
- barCnt=50, days=20 (20-day warmup leaves ~100 live days)
"""
from wtpy import WtBtEngine, EngineType
from wtpy.apps import WtBtAnalyst

import sys
sys.path.append("../Strategies")
from DualThrust import StraDualThrust


if __name__ == "__main__":
    engine = WtBtEngine(EngineType.ET_CTA)
    engine.init(
        folder="../common/",
        cfgfile="configbt.yaml",
        commfile="stk_comms.json",
        contractfile="stocks.json",
    )
    engine.configBacktest(202510230930, 202604211500)
    engine.configBTStorage(mode="csv", path="../storage/")
    engine.commitBTConfig()

    straInfo = StraDualThrust(
        name="pydt_SH510300",
        code="SSE.ETF.510300",
        barCnt=50,
        period="d1",
        days=20,
        k1=0.1,
        k2=0.1,
    )
    engine.set_cta_strategy(straInfo)

    engine.run_backtest()

    analyst = WtBtAnalyst()
    analyst.add_strategy(
        "pydt_SH510300",
        folder="./outputs_bt/",
        init_capital=5000,
        rf=0.0,
        annual_trading_days=240,
    )
    analyst.run()

    kw = input("press any key to exit\n")
    engine.release_backtest()
