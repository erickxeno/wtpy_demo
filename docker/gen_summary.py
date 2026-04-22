"""Post-process a wtpy backtest output directory to generate summary.json.

New versions of WtBtEngine no longer emit summary.json, but WtBtSnooper's
frontend and several endpoints (get_bt_closes, get_bt_info) depend on it.
The frontend specifically reads these fields from `btInfo.summary`:
    capital, days, total_return, annual_return, max_falldown, max_profratio,
    win_rate, sharpe_ratio, sortino_ratio, calmar_ratio

plus the ones get_bt_closes / get_bt_info use:
    capital (required by get_bt_closes)
    any fields from do_trading_analyze

This script computes all of them from closes.csv + funds.csv using the
same Calculate class as WtBtAnalyst.

Usage inside the container:
    python /workspace/docker/gen_summary.py <output_bt_dir> <strategy_id> <init_capital>
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import pandas as pd

from wtpy.apps.WtBtAnalyst import Calculate
from wtpy.monitor.WtBtSnooper import do_trading_analyze


def _safe(v):
    """Convert NaN / inf to 0 so JSON stays valid and UI doesn't show NaN."""
    try:
        if v is None:
            return 0
        fv = float(v)
        if math.isnan(fv) or math.isinf(fv):
            return 0
        return fv
    except (TypeError, ValueError):
        return v


def build_summary(output_bt_dir: Path, strategy_id: str, capital: float) -> dict:
    strategy_dir = output_bt_dir / strategy_id
    closes_csv = strategy_dir / "closes.csv"
    funds_csv = strategy_dir / "funds.csv"
    btenv_json = strategy_dir / "btenv.json"

    if not closes_csv.exists():
        raise FileNotFoundError(f"closes.csv missing: {closes_csv}")
    if not funds_csv.exists():
        raise FileNotFoundError(f"funds.csv missing: {funds_csv}")

    df_closes = pd.read_csv(closes_csv)
    df_funds = pd.read_csv(funds_csv)

    # Pre-compute fee column used by Snooper's do_trading_analyze
    df_closes["fee"] = (
        df_closes["profit"]
        - df_closes["totalprofit"]
        + df_closes["totalprofit"].shift(1).fillna(value=0)
    )

    # Base summary (trade stats: winrate, avgprof, largest_profit/loss, etc.)
    summary = do_trading_analyze(df_closes, df_funds)

    # Calculate advanced ratios using WtBtAnalyst.Calculate
    period = 240  # annual trading days (consistent with demos/cta_stk_bt/runBT.py)
    rf = 0.0

    df_closes_calc = df_closes.copy()
    df_closes_calc["principal"] = df_closes_calc["totalprofit"] + capital
    df_closes_calc["principal"] = df_closes_calc["principal"].shift(1).fillna(capital)
    ret_trade = df_closes_calc["profit"] / df_closes_calc["principal"]
    profit_series = df_closes_calc["profit"]

    df_funds_calc = df_funds.copy()
    df_funds_calc["principal"] = df_funds_calc["dynbalance"] + capital
    df_funds_calc["principal2"] = df_funds_calc["principal"].shift(1).fillna(capital)
    ret_day = df_funds_calc["principal"] / df_funds_calc["principal2"] - 1
    trade_day = int(len(df_funds_calc))

    factors = Calculate(
        ret=ret_trade,
        mar=0,
        rf=rf,
        period=period,
        trade=1,
        capital=capital,
        ret_day=ret_day,
        trade_day=trade_day,
        profit=profit_series,
    )

    sharpe = _safe(factors.sharp_ratio())
    sortino = _safe(factors.sortion_ratio())
    max_drawdown_ratio = _safe(factors.maxDrawdown_ratio())
    annual_return = _safe(factors.get_annual_return())
    calmar = _safe(annual_return / max_drawdown_ratio) if max_drawdown_ratio else 0

    # Final net return (on capital)
    last_bal = float(df_funds["dynbalance"].iloc[-1]) if len(df_funds) else 0.0
    total_return = last_bal / capital if capital else 0.0

    # Max profit point (peak equity ratio above initial)
    equity_series = df_funds["dynbalance"] + capital
    max_profratio = _safe((equity_series.max() - capital) / capital) if capital else 0.0

    # Summary fields the frontend reads from `btInfo.summary`
    summary.update({
        "capital": float(capital),
        "days": trade_day,
        "total_return": float(total_return),
        "annual_return": float(annual_return),
        "max_falldown": float(max_drawdown_ratio),
        "max_profratio": float(max_profratio),
        "win_rate": summary.get("winrate", 0) / 100.0,  # frontend expects fraction 0..1
        "sharpe_ratio": float(sharpe),
        "sortino_ratio": float(sortino),
        "calmar_ratio": float(calmar),
        "strategy": strategy_id,
    })

    # Attach btenv for completeness (not strictly needed but harmless)
    if btenv_json.exists():
        summary["env"] = json.loads(btenv_json.read_text())

    return summary


def main() -> int:
    if len(sys.argv) != 4:
        print(__doc__)
        return 2

    output_bt_dir = Path(sys.argv[1])
    strategy_id = sys.argv[2]
    capital = float(sys.argv[3])

    summary = build_summary(output_bt_dir, strategy_id, capital)
    target = output_bt_dir / strategy_id / "summary.json"
    target.write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
    print(f"[gen_summary] wrote {target}")
    print(
        f"[gen_summary] capital={capital}, days={summary['days']}, "
        f"total_return={summary['total_return']*100:.2f}%, "
        f"annual_return={summary['annual_return']*100:.2f}%, "
        f"max_drawdown={summary['max_falldown']*100:.2f}%, "
        f"sharpe={summary['sharpe_ratio']:.3f}, "
        f"calmar={summary['calmar_ratio']:.3f}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
