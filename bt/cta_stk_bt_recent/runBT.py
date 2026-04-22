"""Backtest DualThrust on SSE.ETF.510300 using recent ~23 trading days of
5-minute data fetched from Sina via scripts/fetch-data.sh.

Differences from wtpy/demos/cta_stk_bt/runBT.py:
- Time range pushed to 2026-03-23 → 2026-04-21 (recent Sina data limit)
- `days` parameter reduced from 30 to 10 so DualThrust can warm up within
  the 23-day window and produce signals
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
    engine.configBacktest(202603230930, 202604211500)
    engine.configBTStorage(mode="csv", path="../storage/")
    engine.commitBTConfig()

    # days=10: warmup window fits inside the available ~23 trading days
    straInfo = StraDualThrust(
        name="pydt_SH510300",
        code="SSE.ETF.510300",
        barCnt=50,
        period="m5",
        days=10,
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
