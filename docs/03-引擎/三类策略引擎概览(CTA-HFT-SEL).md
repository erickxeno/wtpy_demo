---
层级: L1
前置阅读:
  - docs/02-架构/整体架构与分层.md
本篇目标: 用对照表说明 CTA / HFT / SEL 三种策略引擎的调度粒度、典型场景、对应 Context 类、demo 入口文件，帮助读者选择正确的路线。
读完后应能回答:
  - 我想做股票波段策略应该选哪个引擎？
  - HFT 和 CTA 在 on_tick 上有什么区别？
  - SEL 为什么被叫做"选股"引擎？
  - 一个进程里能不能同时跑 CTA + HFT？
关键源码:
  - wtpy/wtpy/WtCoreDefs.py（EngineType 枚举）
  - wtpy/wtpy/StrategyDefs.py
  - wtpy/wtpy/WtBtEngine.py:L50-L56
  - wtpy/wtpy/WtEngine.py
术语表反链:
  - CTA
  - HFT
  - SEL
  - Strategy
  - Context
  - Bar
  - Tick
---

## 三剑客对照表

| 维度 | **CTA** | **HFT** | **SEL** |
|---|---|---|---|
| 中文名 | 商品交易顾问 | 高频交易 | 选股策略 |
| 调度粒度 | Bar / Tick（分钟或更大） | 逐笔 Tick / 逐笔成交 / 委托队列 | 多标的定时调度（秒/分/日/周/月/年） |
| 典型时间尺度 | m1 / m5 / d1 | 毫秒–秒 | d / w / m |
| 典型场景 | 趋势跟踪、双均线、DualThrust、ETF 股票波段 | 做市、套利、订单簿信号 | 多因子选股、指数增强、股票组合调仓 |
| 基类 | `BaseCtaStrategy` | `BaseHftStrategy` | `BaseSelStrategy` |
| 上下文 | `CtaContext` | `HftContext` | `SelContext` |
| `EngineType` | `ET_CTA` | `ET_HFT` | `ET_SEL` |
| 主回调钩子 | `on_init` / `on_bar` / `on_tick` / `on_calculate` / `on_session_begin` / `on_session_end` | `on_init` / `on_tick` / `on_order` / `on_trade` / `on_entrust` / `on_ordque` / `on_orddtl` / `on_trans` | `on_init` / `on_calculate` / `on_session_begin` / `on_session_end` |
| 下单 API | `stra_set_position` / `stra_enter_long` / `stra_exit_long` | `stra_buy` / `stra_sell` / `stra_cancel` 等事件驱动 | `stra_set_position`（调仓） |
| 股票/期货侧重 | 股票主流、期货通吃 | 期货主流 | 股票主流 |
| demo 入口 | `demos/cta_stk_bt/runBT.py`、`demos/cta_stk/run.py` | `demos/hft_fut/`、`demos/hft_fut_bt/` | `demos/sel_fut_bt/` |
| 底层 mocker | `cta` / `stk` | `hft` | `sel` |

## 如何选择？

```
你的策略是...
├─ 按固定 K 线周期算一次信号（如每 5 分钟判断一次） → CTA
├─ 关心盘口/逐笔，毫秒级反应，需要管理具体委托  → HFT
└─ 同时看几十上百只股票，按日/周做组合调仓      → SEL
```

股票主轴读者：**默认就是 CTA**。HFT 主要是期货线；SEL 在做多因子选股组合时才上。

## 三者在引擎层怎么分叉

`wtpy/wtpy/WtBtEngine.py:L50-L56`：
```python
if eType == eType.ET_CTA:
    self.__wrapper__.initialize_cta(...)
elif eType == eType.ET_HFT:
    self.__wrapper__.initialize_hft(...)
elif eType == eType.ET_SEL:
    self.__wrapper__.initialize_sel(...)
```

C++ 侧为每种引擎起一套独立的 mocker：
- `cta` mocker：处理 Bar 驱动 + 目标仓位执行；股票用 `stk` 子类处理 T+1。
- `hft` mocker：处理 Tick / 委托 / 成交事件流。
- `sel` mocker：按 `period/date/time` 定时调用 `on_calculate`。

## 一个进程能混装几个引擎？

不能。`WtBtEngine` 是 [singleton](../00-基础/术语表.md#singleton单例)；实盘的 `WtEngine` 同理。**一个进程只能跑一种 EngineType**。若要同跑多套，开多进程或用 C++ 的 CTA+SEL 组合运行。

## 进一步阅读

- [WtBtEngine 回测引擎](./WtBtEngine-回测引擎.md)
- [WtEngine 实盘引擎](./WtEngine-实盘引擎.md)
- [WtDtEngine 数据引擎](./WtDtEngine-数据引擎.md)
- [策略基类 StrategyDefs](../04-策略与上下文/策略基类StrategyDefs.md)
- [CtaContext 股票主轴](../04-策略与上下文/CtaContext-股票主轴.md)
