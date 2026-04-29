---
层级: L2
前置阅读:
  - docs/04-策略与上下文/策略基类StrategyDefs.md
  - docs/04-策略与上下文/CtaContext-股票主轴.md
本篇目标: 列 `wtpy/wtpy/HftContext.py` 相对 CtaContext 的接口差异与典型用法，轻量覆盖即可（期货向，不是本次主轴）。
读完后应能回答:
  - HFT 策略通过 context 如何下委托、如何撤单？
  - 如何查委托队列、逐笔成交？
  - `on_order` / `on_trade` / `on_entrust` 分别什么时候触发？
关键源码:
  - wtpy/wtpy/HftContext.py
  - wtpy/wtpy/StrategyDefs.py:L101-L265
术语表反链:
  - Context
  - HFT
  - Tick
---

## 同于 CtaContext 的部分

以下方法语义一致，不再重复：`stra_get_bars` / `stra_get_ticks` / `stra_sub_ticks` / `stra_sub_bar_events` / `stra_get_price` / `stra_get_time` / `stra_get_date` / `stra_get_tdate` / `stra_get_all_codes` / `stra_log_text` / `user_save_data` / `user_load_data` / 图表指标类方法。

## HFT 特有 API（下单 / 撤单）

| 方法 | 说明 |
|---|---|
| `stra_buy(stdCode, price, qty, userTag="")` | 限价买入 |
| `stra_sell(stdCode, price, qty, userTag="")` | 限价卖出 |
| `stra_cancel(localid)` | 按本地订单 id 撤单 |
| `stra_cancel_all(stdCode)` | 某合约全撤 |
| `stra_get_orders(stdCode)` | 当前活跃订单 |
| `stra_get_position(stdCode, usertag="")` | 查持仓 |
| `stra_get_undone(stdCode)` | 未成交数量 |

**本地订单 id**：`stra_buy/stra_sell` 返回一个/多个 `localid`，后续 `on_order` / `on_trade` / `on_entrust` 的回调都会带它，用来追踪订单状态。

## HFT 特有：委托/成交流查询

| 方法 | 说明 |
|---|---|
| `stra_get_order_queue(stdCode, count)` | 最近 count 条委托队列 `WtNpOrdQueues` |
| `stra_get_order_detail(stdCode, count)` | 最近 count 条逐笔委托 `WtNpOrdDetails` |
| `stra_get_transaction(stdCode, count)` | 最近 count 条逐笔成交 `WtNpTransactions` |
| `stra_sub_order_queues(stdCode)` | 订阅委托队列推送（`on_order_queue`） |
| `stra_sub_order_details(stdCode)` | 订阅逐笔委托 |
| `stra_sub_transactions(stdCode)` | 订阅逐笔成交（`on_transaction`） |

## 回调钩子对照

| 钩子 | 时机 |
|---|---|
| `on_channel_ready` | 交易通道就绪（实盘专用） |
| `on_channel_lost` | 通道丢失 |
| `on_entrust(localid, stdCode, bSucc, msg, userTag)` | 下单送出后的**报入**结果（委托被交易所接受 / 拒绝） |
| `on_order(localid, stdCode, isBuy, totalQty, leftQty, price, isCanceled, userTag)` | 订单**状态变化**（部分成交、撤单） |
| `on_trade(localid, stdCode, isBuy, qty, price, userTag)` | 有新**成交** |
| `on_position(stdCode, isLong, prevol, preavail, newvol, newavail)` | 实盘：初始仓位回报 |
| `on_tick / on_bar / on_order_detail / on_order_queue / on_transaction` | 数据推送 |

## 典型用法骨架

```python
class MakerStrat(BaseHftStrategy):
    def on_init(self, ctx):
        ctx.stra_sub_ticks("CFFEX.IF.HOT")
        ctx.stra_sub_transactions("CFFEX.IF.HOT")
        self._localids = {}

    def on_tick(self, ctx, code, tick):
        bid = tick["bid_price_0"]; ask = tick["ask_price_0"]
        if bid > 0 and ask > 0:
            lid_buy  = ctx.stra_buy (code, bid - 1, 1, userTag="MK_BUY")
            lid_sell = ctx.stra_sell(code, ask + 1, 1, userTag="MK_SELL")
            self._localids[lid_buy] = "pending"
            self._localids[lid_sell] = "pending"

    def on_trade(self, ctx, localid, code, isBuy, qty, price, userTag):
        ctx.stra_cancel_all(code)   # 成交后撤对侧

    def on_channel_lost(self, ctx):
        ctx.stra_log_text("通道丢失", level=3)
```

## 常见坑

- **下单撤单异步**：`stra_buy` 立即返回 localid，但交易所回执在 `on_entrust` / `on_order` 里；不能假设下一行代码时订单已进市场。
- **状态机**：要维护"订单 id → 状态"map；容易出现"撤单请求已发但成交先到"的竞态。
- **HFT 回测**：`demos/hft_fut_bt/` 用模拟撮合；真实盘口撮合顺序和回测会有差。

## 进一步阅读

- 策略基类钩子全表：[策略基类 StrategyDefs](./策略基类StrategyDefs.md)
- HFT 期货 demo：`wtpy/demos/hft_fut/`、`wtpy/demos/hft_fut_bt/`
- 期货与股票差异：[10-期货补充/与股票的差异清单](../10-期货补充/与股票的差异清单.md)
