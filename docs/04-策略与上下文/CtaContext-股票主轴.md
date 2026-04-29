---
层级: L2
前置阅读:
  - docs/04-策略与上下文/策略基类StrategyDefs.md
本篇目标: 对 `wtpy/wtpy/CtaContext.py` 的公开方法做**中文速查表**，覆盖取数据、查持仓、下单、查行情、用户存档、日志、指标、回测末尾处理等。股票主轴下强调 T+1 相关的用法。
读完后应能回答:
  - 我想在策略里查当前持仓应该调哪个方法？
  - `stra_set_position` 和 `stra_enter_long` 的区别？
  - 怎么在回测里让策略保存一些自定义变量并在下次会话恢复？
  - 股票如何区分"总仓位 vs 可用仓位"？
关键源码:
  - wtpy/wtpy/CtaContext.py
术语表反链:
  - Context
  - CTA
  - Strategy
  - T+1
  - Bar
  - Tick
  - position
  - pnl
---

## 获取方式

CTA 策略里 `on_xxx` 的每个钩子都会把 `context: CtaContext` 作为第一个参数（`self` 之外）传进来：

```python
def on_bar(self, context: CtaContext, stdCode, period, newBar):
    pos = context.stra_get_position(stdCode)
    context.stra_set_position(stdCode, pos + 100)
```

所有方法都以 `stra_` 开头（策略 API）或无前缀（日志/指标扩展）。

## 数据读取

| 方法 | 说明 | 返回 |
|---|---|---|
| `stra_prepare_bars(stdCode, period, count, isMain=False)` | 提前声明要用到的 K 线，不立刻返回 | None |
| `stra_get_bars(stdCode, period, count, isMain=False)` | 拉最近 count 根 K 线 | `WtNpKline`（numpy array-like） |
| `stra_get_ticks(stdCode, count)` | 最近 count 笔 Tick | `WtNpTicks` |
| `stra_sub_ticks(stdCode)` | 订阅 Tick，触发 `on_tick` | None |
| `stra_sub_bar_events(stdCode, period)` | 订阅 Bar 事件，触发 `on_bar`（默认主合约会自动订阅；多合约时要显式订阅） | None |

`isMain=True`：标记为"主合约"，策略的 `on_calculate` 和交易日驱动依据主合约的时间轴推进。一个策略通常只有 1 个主合约。

## 行情查询

| 方法 | 说明 |
|---|---|
| `stra_get_price(stdCode)` | 最新价 |
| `stra_get_day_price(stdCode, flag=0)` | 当日某价（0:开, 1:高, 2:低, 3:昨收） |
| `stra_get_time()` | 当前时间，`yyyymmddHHMM` 整数 |
| `stra_get_date()` | 当前自然日期，`yyyymmdd` 整数 |
| `stra_get_tdate()` | 当前交易日，`yyyymmdd` 整数（夜盘 + 次日视为同一交易日） |

## 持仓 / 资金（股票重点）

| 方法 | 说明 |
|---|---|
| `stra_get_position(stdCode, bonlyvalid=False, usertag="")` | 获取某合约持仓；`bonlyvalid=True` 仅返回"可用"仓位（**T+1 剔除今日买入**） |
| `stra_get_all_position()` | dict：`{stdCode: position}` |
| `stra_get_position_avgpx(stdCode)` | 持仓均价 |
| `stra_get_position_profit(stdCode)` | 持仓浮动盈亏 |
| `stra_get_fund_data(flag=0)` | 资金：0-动态权益, 1-总盈亏, 2-手续费等（详见源码） |

**股票 T+1 用法**：
```python
pos_total  = ctx.stra_get_position("SSE.STK.600000")                # 总仓位（含今日买入）
pos_usable = ctx.stra_get_position("SSE.STK.600000", bonlyvalid=True) # 可卖仓位
if want_sell and pos_usable >= qty:
    ctx.stra_set_position("SSE.STK.600000", pos_total - qty)
```

## 下单

| 方法 | 说明 |
|---|---|
| `stra_set_position(stdCode, qty, usertag="", limitprice=0.0, stopprice=0.0)` | **目标仓位模式**：告诉引擎"我想要 qty 手"，由 Executer 负责差额下单 |
| `stra_enter_long(stdCode, qty, usertag="", ...)` | 增量开多（按手） |
| `stra_exit_long(stdCode, qty, ...)` | 平多 |
| `stra_enter_short(stdCode, qty, ...)` | 增量开空（期货） |
| `stra_exit_short(stdCode, qty, ...)` | 平空（期货） |

**股票首选 `stra_set_position`**：Executer 会自动处理"当前 100 手 → 目标 300 手 = 买 200 手"；也会自然映射 T+1（若目标小于可用仓位则触发卖出）。

## 成交明细 / 回测细节查询

| 方法 | 说明 |
|---|---|
| `stra_get_last_entrytime(stdCode)` | 最近一次开仓时间（yyyymmddHHMM） |
| `stra_get_last_entrytag(stdCode)` | 开仓时的 `usertag` |
| `stra_get_last_exittime(stdCode)` | 最近一次平仓时间 |
| `stra_get_first_entrytime(stdCode)` | 本轮首次开仓时间 |
| `stra_get_detail_profit(stdCode, usertag, flag=0)` | 按 tag 分仓明细盈亏 |
| `stra_get_detail_cost(stdCode, usertag)` | 按 tag 分仓成本 |
| `stra_get_detail_entertime(stdCode, usertag)` | 按 tag 分仓开仓时间 |

## 合约 / 时段 / 交易日

| 方法 | 说明 |
|---|---|
| `stra_get_all_codes()` | 全部可交易合约 |
| `stra_get_codes_by_product(pid)` | 某品种下全部合约（期货更常用） |
| `stra_get_codes_by_underlying(u)` | 某 underlying 下 |
| `stra_get_comminfo(stdCode)` | 品种 `ProductInfo` |
| `stra_get_contract(stdCode)` | 合约 `ContractInfo`（股票：上市/退市日期等） |
| `stra_get_rawcode(stdCode)` | 连续合约 → 原始合约 |
| `stra_get_sessinfo(stdCode)` | 交易时段 `SessionInfo` |

## 用户存档 / 日志 / 指标

| 方法 | 说明 |
|---|---|
| `user_save_data(key, val)` | 持久化任意值（内部 str 序列化） |
| `user_load_data(key, defVal=None, vType=float)` | 恢复；vType 指定反序列化目标 |
| `stra_log_text(message, level=1)` | 写日志（0 debug / 1 info / 2 warn / 3 error） |
| `write_indicator(tag, time, data)` | 写指标（给 `WtBtAnalyst` / 监控 UI 读取） |

## Snooper / 图表辅助

| 方法 | 说明 |
|---|---|
| `set_chart_kline(stdCode, period)` | 指定主图 K 线 |
| `add_chart_mark(price, icon, tag)` | 在主图标注记号 |
| `register_index(idxName, idxType=1)` | 注册副图指标 |
| `register_index_line(idxName, lineName, lineType=0)` | 注册副图线条 |
| `add_index_baseline(idxName, lineName, value)` | 加基准线 |
| `set_index_value(idxName, lineName, val)` | 写指标数值 |

这些方法的数据最终被 [WtBtSnooper](../06-回测/WtBtSnooper可视化.md) 读取显示。

## 引擎回调桩（C++→Py→用户）

`on_init` / `on_session_begin` / `on_session_end` / `on_backtest_end` / `on_tick` / `on_bar` / `on_calculate` / `on_calculate_done` / `on_getticks` / `on_getpositions` / `on_getbars` / `on_condition_triggered`：
- 这些在 `CtaContext.py` 里是"胶水层"：先做统一预处理（比如把 `WTSTickStruct` 转成 dict），再转发到用户策略（`self.__stra__.on_bar(self, ...)` 等）。
- 用户一般不直接调用它们；你在策略里重写 `on_bar` 就是在钩接这里。

## 常见坑

- **订阅忘了导致 on_bar 不触发**：多合约策略要对**非主合约**显式 `stra_sub_bar_events` / `stra_sub_ticks`。
- **T+1 被忽略**：用 `stra_set_position` 直接降仓，引擎会在今日新买的量上"静默失败"；要用 `bonlyvalid=True` 提前查可用仓位。
- **`stra_get_fund_data(0)` ≠ 初始资金 + PnL**：它是"动态权益"，初始资金要在 `configbt.yaml` / WtBtAnalyst `init_capital` 参数里给。
- **`user_save_data` 序列化**：复杂对象会变字符串，再恢复要自己 `vType=str` + `json.loads`。

## 进一步阅读

- 策略 demo：`wtpy/demos/Strategies/DualThrust.py`（DualThrust 双推力策略）
- L3 逐段精读：[cta_stk_bt 回测 demo 逐段](../08-股票示例精读/cta_stk_bt-回测demo逐段.md)
- 其他 Context：[HftContext](./HftContext.md) / [SelContext选股上下文](./SelContext选股上下文.md)
