---
层级: L2
前置阅读:
  - docs/03-引擎/三类策略引擎概览(CTA-HFT-SEL).md
本篇目标: 从 `wtpy/wtpy/StrategyDefs.py` 出发，列 `BaseCtaStrategy` / `BaseHftStrategy` / `BaseSelStrategy` 的方法钩子（on_init / on_tick / on_bar / on_session_begin / on_session_end 等）。
读完后应能回答:
  - 我要写一个 CTA 策略，至少要重写哪几个方法？
  - HFT 策略比 CTA 多了哪些钩子？
  - `on_calculate` 和 `on_bar` 的区别？
  - `on_session_begin` 和交易日切换是什么关系？
关键源码:
  - wtpy/wtpy/StrategyDefs.py:L3-L100（CTA）
  - wtpy/wtpy/StrategyDefs.py:L101-L265（HFT）
  - wtpy/wtpy/StrategyDefs.py:L267-L346（SEL）
术语表反链:
  - Strategy
  - Context
  - CTA
  - HFT
  - SEL
  - Bar
  - Tick
---

## 三个基类同源

都在 `wtpy/wtpy/StrategyDefs.py`，都只做两件事：
1. 在 `__init__(name)` 里保存策略名（`name()` 查询）。
2. 提供一组默认**空实现**的钩子，让用户按需重写。

## 共有钩子（三基类都有）

| 钩子 | 触发时机 | 作用 |
|---|---|---|
| `on_init(context)` | 策略刚挂上、引擎 `run_backtest`/`run` 之后一次 | 订阅行情、读历史数据、加载用户存档 |
| `on_session_begin(context, curTDate)` | 每个交易日开盘前 | 重置"当日"状态、打印日期 |
| `on_session_end(context, curTDate)` | 每个交易日收盘后 | 结算、保存当日指标 |
| `on_backtest_end(context)` | 回测结束时（只回测触发） | 写 summary、生成 Excel 预处理 |
| `on_tick(context, stdCode, newTick)` | Tick 进来 | 盘口类策略计算 |
| `on_bar(context, stdCode, period, newBar)` | 一根 K 线闭合 | Bar 类策略计算 |

> `curTDate` 是 `yyyymmdd` 整数（如 `20210220`）；`period` 字符串（如 `'m5'`）；`newBar` 是 dict 形态的 `WTSBarStruct` 字段。

## CTA 独有

```python
class BaseCtaStrategy:
    def on_calculate(self, context)           # K 线闭合时（计算核心）
    def on_calculate_done(self, context)      # 计算之后，适合"收尾类"动作
    def on_condition_triggered(self, context, stdCode, target, price, usertag)
                                              # 条件单触发
```

- **`on_calculate` vs `on_bar`**：两者都在 K 线闭合时触发。区别在于 `on_calculate` 是"每一次要算信号都会调用"（与你订阅的多品种无关，更像"调度点"），而 `on_bar` 是"某一品种的 K 线闭合了才调"；多品种策略时在 `on_bar` 里按 `stdCode` 分派，在 `on_calculate` 里统一出信号。
- **最小 CTA 模板**：
  ```python
  class MyStrat(BaseCtaStrategy):
      def on_init(self, ctx):
          ctx.stra_get_bars("SSE.ETF.510300", "m5", 50)
      def on_calculate(self, ctx):
          # 读最近 K 线，决定目标仓位
          ctx.stra_set_position("SSE.ETF.510300", 100)
  ```

## HFT 独有（最复杂）

```python
def on_tick(...)
def on_order_detail(...)      # 逐笔委托
def on_order_queue(...)       # 委托队列
def on_transaction(...)       # 逐笔成交（Transactions）
def on_bar(...)               # 也有，但 HFT 一般不主用
def on_channel_ready(...)     # 交易通道就绪
def on_channel_lost(...)      # 通道丢失
def on_entrust(localid, stdCode, bSucc, msg, userTag)   # 下单回执
def on_order(localid, stdCode, isBuy, totalQty, leftQty, price, isCanceled, userTag)   # 订单状态变化
def on_trade(localid, stdCode, isBuy, qty, price, userTag)   # 成交回报
def on_position(stdCode, isLong, prevol, preavail, newvol, newavail)   # 初始仓位（仅实盘）
```

HFT 特点：**事件驱动**、要管理本地订单（`localid`）、要处理撤单和部分成交；比 CTA 难写好几个量级。

## SEL 独有

```python
def on_calculate(self, context)        # 同 CTA 的 on_calculate
def on_calculate_done(self, context)
```

SEL 本质是"定时调度 + 多标的批量调仓"，逻辑集中在 `on_calculate` 里：每到设定的时点（见 `set_sel_strategy` 的 `period/date/time` 参数），引擎就把**全市场快照** + 历史 K 线交到你手里，你挑一批标的、每个设置目标仓位（通过 `context.stra_set_position`）。

## 全局原则

1. **不要在 `__init__` 里做重活**：`__init__` 只存参数；真正的订阅 / 加载要放在 `on_init`。
2. **幂等订阅**：在 `on_init` 里多次订阅同一合约不会重复订阅，但逻辑上应该只调一次。
3. **跨会话状态**：想在多次 session 之间保留变量 → `context.stra_save_userdata` / `stra_load_userdata`（见 [CtaContext](./CtaContext-股票主轴.md)）。
4. **回测专属回调**：`on_backtest_end` 只在 `WtBtEngine.on_backtest_end` 转发时触发；实盘看不到它。

## 进一步阅读

- CTA 所有 `ctx.stra_*` API 速查：[CtaContext-股票主轴](./CtaContext-股票主轴.md)
- HFT 专用 API：[HftContext](./HftContext.md)
- SEL 专用：[SelContext选股上下文](./SelContext选股上下文.md)
- 实战 demo：`wtpy/demos/Strategies/DualThrust.py`（被 `cta_stk_bt/runBT.py` 引用）
