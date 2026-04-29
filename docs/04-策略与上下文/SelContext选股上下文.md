---
层级: L2
前置阅读:
  - docs/04-策略与上下文/策略基类StrategyDefs.md
  - docs/04-策略与上下文/CtaContext-股票主轴.md
本篇目标: 说明选股调度模型（定时触发 + 多标的调仓），以及 `SelContext` 与 `CtaContext` 的差异。
读完后应能回答:
  - SEL 引擎按什么规则触发 `on_calculate`？
  - SEL 策略如何对多支股票同时下目标仓位？
  - SEL 和 CTA 共用哪些 API？
关键源码:
  - wtpy/wtpy/SelContext.py
  - wtpy/wtpy/WtBtEngine.py:L393-L406（set_sel_strategy）
  - wtpy/wtpy/StrategyDefs.py:L267-L346（BaseSelStrategy）
术语表反链:
  - Context
  - SEL
  - Strategy
---

## 调度模型

注入 SEL 策略时：
```python
engine.set_sel_strategy(
    strategy=MySel(...),
    date=0, time=1455,      # 每日 14:55 触发
    period="d",             # 周期：min / d / w / m / y
    trdtpl="CHINA",         # 交易日历模板
    session="TRADING",      # 交易时段模板
    slippage=0)
```

含义：按 `period` 指定的周期，在每个周期的 `date`/`time` 时点触发 `on_calculate`。
- `period="d"` + `date=0` + `time=1455` → 每个交易日 14:55。
- `period="w"` + `date=5` → 每周五。
- `period="m"` + `date=1` → 每月 1 日。
- `period="min"` + `time=5` → 每 5 分钟。

## 核心回调

| 钩子 | 时机 | 作用 |
|---|---|---|
| `on_init(ctx)` | 策略启动 | 订阅全市场合约 |
| `on_session_begin(ctx, tdate)` / `on_session_end` | 交易日切换 | 重置当日状态 |
| **`on_calculate(ctx)`** | 周期触发时 | 核心：批量读取因子 → 排名 → 调仓 |
| `on_tick(ctx, code, tick)` / `on_bar(ctx, code, period, bar)` | 可选订阅 | 一般 SEL 不用，留给需要实时跟踪的场景 |
| `on_backtest_end(ctx)` | 回测结束 |  |

## `SelContext` 与 `CtaContext` 的共用/差异

### 共用（语义相同）
- `stra_get_bars` / `stra_get_ticks`
- `stra_get_price` / `stra_get_day_price` / `stra_get_time` / `stra_get_date` / `stra_get_tdate`
- `stra_get_all_codes` / `stra_get_codes_by_product` / `stra_get_codes_by_underlying`
- `stra_get_comminfo` / `stra_get_contract` / `stra_get_sessinfo`
- `user_save_data` / `user_load_data` / `stra_log_text`
- 图表指标类方法（`register_index` 等）

### SEL 差异
- **`stra_set_position(stdCode, qty, usertag="")`**：
  - 签名比 CTA 的少了 `limitprice`/`stopprice`（SEL 不做限价/止损下单；按收盘价调仓）。
  - SEL 的"目标仓位"一般意指**股数**（股票）或**手数**（期货）。
- 没有 `stra_enter_long` / `stra_exit_long` 等显式开平接口——SEL 只有"目标仓位"模型。
- 不提供"最近开仓时间 / 分仓明细"那一类细粒度查询（本质是组合策略，不关心逐笔）。

## 典型骨架（股票多因子选股）

```python
class MomentumSel(BaseSelStrategy):
    def __init__(self, name, top_n=20, lookback=20):
        super().__init__(name)
        self.top_n = top_n; self.lookback = lookback

    def on_init(self, ctx):
        self.pool = ctx.stra_get_all_codes()   # 或自己定义股票池
        for c in self.pool:
            ctx.stra_prepare_bars(c, "d", self.lookback + 1)

    def on_calculate(self, ctx):
        scores = {}
        for c in self.pool:
            bars = ctx.stra_get_bars(c, "d", self.lookback + 1)
            if bars is None or len(bars) < self.lookback + 1:
                continue
            ret = bars.closes[-1] / bars.closes[-self.lookback - 1] - 1
            scores[c] = ret
        picks = sorted(scores.items(), key=lambda x: -x[1])[:self.top_n]
        total = sum(v for _, v in picks if v > 0) or 1
        for c, _ in picks:
            ctx.stra_set_position(c, 100)     # 简化：每只 100 股
        # 其他原先有仓位但这轮未被选中的要平掉
        old = ctx.stra_get_all_position()
        new_set = {c for c, _ in picks}
        for c in old:
            if c not in new_set:
                ctx.stra_set_position(c, 0)
```

## 常见坑

- **全市场订阅代价高**：`on_init` 里订阅几千支股票 + 上百根历史 K 线，内存和 IO 会暴涨；建议先筛股票池。
- **触发时机**：`time=1455` 指 14:55 刚刚闭合的分钟 K 线；在此之后新产生的价格变动已经不在本次 `on_calculate` 的时间窗内。
- **T+1**：SEL 股票策略同样遵守；在调仓时要考虑"今买的下一日才能卖"。
- **回测 SEL demo**：主要在 `demos/sel_fut_bt/`（期货），股票侧 demo 较少；自写时可参考 CTA 股票 demo + SEL 触发规则。

## 进一步阅读

- 策略基类：[策略基类 StrategyDefs](./策略基类StrategyDefs.md)
- CTA 上下文：[CtaContext-股票主轴](./CtaContext-股票主轴.md)
