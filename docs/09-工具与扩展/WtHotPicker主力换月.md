---
层级: L2
前置阅读:
  - docs/05-数据/ContractMgr与stocks.json.md
本篇目标: 说明期货主力合约规则（`WtHotPicker`）与使用场景，虽然是期货向，但作为通用工具纳入（股票读者可跳过）。
读完后应能回答:
  - 什么是"主力合约"？为什么要换月？
  - `hots.json` / `seconds.json` 格式？
  - WtHotPicker 支持哪些数据源？
关键源码:
  - wtpy/wtpy/apps/WtHotPicker.py
  - wtpy/demos/common/hots.json
  - wtpy/demos/common/seconds.json
  - wtpy/demos/test_hotpicker/
术语表反链:
  - 换月
  - CTP
---

## 主力合约的概念

期货品种（如 `SHFE.rb` 螺纹钢）在任一时点有多个到期月份合约（`rb2309`、`rb2310`、`rb2401` ...），**主力合约**指那个"成交量 / 持仓量最大"的合约。策略通常不直接盯具体月，而是盯"主力" → 每逢换月，策略持仓要从老月份滚到新月份。

- WonderTrader 用 `SHFE.rb.HOT` 表示"主力连续合约"，用 `SHFE.rb.2ND` 表示"次主力"。
- 哪个月份是主力由 `hots.json` 规则文件给出；`seconds.json` 则是次主力。

## `hots.json` / `seconds.json` 格式

```json
{
    "SHFE": {
        "rb": [
            { "date": 20230101, "from": "2301", "to": "2305" },
            { "date": 20230601, "from": "2305", "to": "2310" }
        ]
    }
}
```

- 每条记录声明在 `date` 当天起把主力从 `from` 切到 `to`。
- 底层回放 / 实盘按这个日历找"当前生效的月合约"。

## `WtHotPicker` 支持的数据源

从源码看 `WtHotPicker.py`（依赖 `pyquery`、`urllib`）：
- **交易所网站爬取**：上期所、大商所、郑商所、中金所、能源等页面抓前一天成交量/持仓量排名 → 决定主力。
- **DataKit 落盘的 `snapshot.csv`**：每日收盘后 DataKit 会生成快照，按成交量直接排序换月。

两路互为备份：交易所页面易挂 / 改版；DataKit 依赖你自己跑 7×24。

## 使用姿势

```python
from wtpy.apps import WtHotPicker
picker = WtHotPicker()
picker.pick_hot_from_exchg(for_date=20230615)    # 网站模式
# 或
picker.pick_hot_from_snapshot(snapshot_csv="snapshot.csv")  # DataKit 模式
picker.save_to("hots.json")
```

输出就是上面的 json 格式；替换 `demos/common/hots.json` 后**回测和实盘均生效**。

## 自定义换月规则

`WtBtEngine.registerCustomRule(ruleTag, filename)` 可以挂自定义规则文件。例如：
- `ruleTag="THIS"` + 规则文件 → 对应的连续代码为 `CFFEX.IF.THIS`。
- 用来做 "第三主力" / "季度合约" / "反向择时主力" 等研究。

## 股票是否需要？

**不需要**。股票没有到期月概念，也没有"主力合约"。除非你做股指期货（`IF`/`IC`/`IH`/`IM`）才用。

## 常见坑

- **换月当日信号**：老合约平仓 + 新合约开仓会导致双边费用；某些策略会在换月日有非常规损益。
- **hots.json 缺当日条目**：引擎回退到上一条生效的 `to`；如果上一条也过期会直接报错。
- **交易所页面 403 / 验证码**：爬虫模式不稳定；建议切到 DataKit snapshot 模式。

## 进一步阅读

- 合约管理：[05-数据/ContractMgr 与 stocks.json](../05-数据/ContractMgr与stocks.json.md)
- 股票 vs 期货差异：[10-期货补充/与股票的差异清单](../10-期货补充/与股票的差异清单.md)
