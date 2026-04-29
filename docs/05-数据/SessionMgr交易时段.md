---
层级: L2
前置阅读:
  - docs/05-数据/ContractMgr与stocks.json.md
本篇目标: 覆盖股票 A 股时段模板（09:30–11:30 / 13:00–15:00）、假日表、`sessions.json` 格式，和 `wtpy/wtpy/SessionMgr.py` 的常用 API。
读完后应能回答:
  - 为什么要把"时段"单独抽成模板而不是每个合约独立配？
  - 集合竞价（9:15–9:25）在哪里体现？
  - `holidays.json` 缺了国庆怎么办？
  - `SessionInfo.offsetTime` / `originalTime` 用途是什么？
关键源码:
  - wtpy/wtpy/SessionMgr.py
  - wtpy/demos/common/stk_sessions.json
  - wtpy/demos/common/holidays.json
术语表反链:
  - 集合竞价
  - 假日表
---

## 时段模板的意义

国内品种有数十个交易所 × 上百品种，但真正不同的"开收盘时刻组合"只有十几种（如"股票日盘"、"期货日盘"、"原油夜盘"）。WonderTrader 把每个组合定义成一个**交易时段模板**，记在 `sessions.json` / `stk_sessions.json`，然后每个品种通过 `stk_comms.json` 里的 `"session": "SD0930"` 引用模板。

## 典型股票时段：`stk_sessions.json`

```json
{
    "SD0930":{
        "name":"股票白盘0930",
        "offset": 0,
        "auction":{"from": 929, "to": 930},
        "sections":[
            {"from": 930, "to": 1130},
            {"from": 1300, "to": 1500}
        ]
    }
}
```

- `offset`：若模板跨越自然日（如期货夜盘），此字段是分钟偏移。股票为 0。
- `auction`：集合竞价窗口。`from=929 to=930` 表示 9:29–9:30。
- `sections`：正式交易段列表。股票有两段：上午 9:30–11:30、下午 13:00–15:00。
- 时间格式 `HHMM`（紧凑整数）。

## `SessionInfo` 关键方法

在 `wtpy/wtpy/SessionMgr.py:L14-L195`：

| 方法 | 作用 |
|---|---|
| `getOpenTime(bOffset)` | 最早开盘时间（带不带偏移） |
| `getCloseTime(bOffset)` | 最晚收盘时间 |
| `getTradingMins()` / `getTradingSecs()` | 总交易分钟/秒数（多段求和） |
| `offsetTime(rawTime)` / `originalTime(offTime)` | 用于夜盘跨日：把 21:00 → 偏移 450 分钟后记为 04:30 次日，便于排序 |
| `getSectionIndex(rawTime)` | 属于第几段（上/下午） |
| `isFirstOfSection(rawTime)` / `isLastOfSection(rawTime)` | 段头 / 段尾判断 |
| `timeToMinutes(rawTime)` | HHMM → 0..1440 的分钟索引 |
| `minutesToTime(minutes, bHeadFirst)` | 逆变换 |

## `SessionMgr` 入口

```python
mgr = SessionMgr()
mgr.load("common/stk_sessions.json")
info = mgr.getSession("SD0930")     # 按模板名
print(info.getTradingMins())        # 240（240 分钟）
```

策略里更常见：
```python
sess = ctx.stra_get_sessinfo("SSE.STK.600000")  # 自动根据合约查品种 → 时段
```

## 假日：`holidays.json`

```json
{
    "CHINA": {
        "20200101": true,
        "20200504": true,
        ...
    }
}
```

- 顶层按"交易日历模板名"分组（`CHINA` 是默认）。
- 引擎会在"自然日 → 交易日"映射时跳过假日。
- **缺假日**：若节日没进来，回测当天会按正常交易日处理（可能跑空信号），实盘会把订单发到一个没开盘的日子上。

## 股票 vs 期货的时段差别

| 模板特点 | 股票 | 期货 |
|---|---|---|
| 两段 / 多段 | 两段（上下午） | 多段（含夜盘） |
| 跨自然日 | 否 | 有（夜盘 21:00 → 次日 2:30） |
| `offset` | 0 | 典型 `540`（9 小时） |
| 集合竞价 | 有（9:25 生成开盘价） | 少（夜盘开盘/结算前） |
| 特殊情况 | 科创板、创业板、北交所有特殊涨跌停与竞价规则 | 商品期货各交易所微小差异 |

## 常见坑

- **新交易所忘加时段**：北交所上线后若不加 BSE 时段，北交所股票的 K 线会被 DataKit 丢弃。
- **夜盘 `offset` 错配**：期货夜盘 `offset=450` vs `540` 会把时间轴错位，导致回测顺序错乱。
- **Holiday 版本飘移**：每年都要更新 `holidays.json`（春节、国庆调休）。
- **集合竞价数据**：`auction` 段内的成交会被打标；部分 Parser 会把集合竞价成交归到 9:30 那一根 Bar。

## 进一步阅读

- `stocks.json` / 合约：[ContractMgr 与 stocks.json](./ContractMgr与stocks.json.md)
- 股票特殊规则：[10-期货补充/与股票的差异清单](../10-期货补充/与股票的差异清单.md)
