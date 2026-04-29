---
层级: L2
前置阅读:
  - docs/05-数据/数据流与文件格式(dsb-dmb-csv).md
  - docs/03-引擎/WtBtEngine-回测引擎.md
本篇目标: 基于 `wtpy/wtpy/ContractMgr.py` 重点讲股票合约属性、`stocks.json` 格式，以及 v0.9.9 加入的上市/退市日期字段。
读完后应能回答:
  - `stocks.json` / `etfs.json` / `stk_comms.json` 这三个文件如何分工？
  - 标准代码（stdCode）是怎么拼出来的？
  - 上市日期（openDate）如何影响回测？
  - 股票代码不知道是哪个交易所怎么查？
关键源码:
  - wtpy/wtpy/ContractMgr.py:L7-L135
  - wtpy/demos/common/stocks.json
  - wtpy/demos/common/stk_comms.json
术语表反链:
  - 复权
  - 除权除息
  - 停牌
---

## `ContractInfo` 字段

```python
class ContractInfo:
    exchg:        str    # 交易所（SSE / SZSE / CFFEX / SHFE / ...）
    code:         str    # 合约代码（如 "600000"）
    name:         str    # 合约名（"浦发银行"）
    product:      str    # 品种代码（股票一般是 "STK"、"ETF"、"IDX"）
    stdCode:      str    # 标准代码（SSE.STK.600000）

    # 期权相关（股票/ETF 基本不用）
    isOption:     bool
    underlying:   str
    strikePrice:  float
    underlyingScale: float
    isCall:       bool

    # 上市 / 退市 日期（v0.9.9 起生效）
    openDate:     int = 19000101
    expireDate:   int = 20991231

    # 期货保证金率
    longMarginRatio:  float
    shortMarginRatio: float
```

## 标准代码规范（stdCode）

| 类型 | 格式 | 示例 |
|---|---|---|
| 指数 | `EXCH.IDX.CODE` | `SSE.IDX.000001` |
| 股票 | `EXCH.STK.CODE` | `SSE.STK.600000`、`SZSE.STK.000001` |
| ETF | `EXCH.ETF.CODE` | `SSE.ETF.510300`、`SZSE.ETF.159915` |
| 期货 主力 | `EXCH.PROD.HOT` | `SHFE.rb.HOT`、`CFFEX.IF.HOT` |
| 期货 具体月 | `EXCH.PROD.YYMM` | `SHFE.rb.2310` |
| 期货 二主力 | `EXCH.PROD.2ND` | `SHFE.rb.2ND` |

`ContractMgr.load` 在读取 json 时会按下列规则计算 `stdCode`（见 `ContractMgr.py:L76-L91`）：
- 若 `product` 是 `code` 的前缀（例如合约 `rb2310` 属品种 `rb`）→ 切分出 `month=2310`，生成 `SHFE.rb.2310`。若月份长度 < 4（像 `rb001`）则前补 `2`（历史习惯）。
- 否则 `stdCode = exchg.product.code`（股票多走这条：`SSE.STK.600000`）。
- 如果 `product` 没提供（极少），`stdCode = exchg.code`。

## `stocks.json` 结构

```json
{
    "SSE": {
        "000001": {"code":"000001","exchg":"SSE","name":"上证综指","product":"IDX"},
        "600000": {"code":"600000","exchg":"SSE","name":"浦发银行","product":"STK",
                   "opendate": 19991110, "expiredate": 20991231},
        "510300": {"code":"510300","exchg":"SSE","name":"沪深300ETF","product":"ETF",
                   "opendate": 20120528}
    },
    "SZSE": {
        "000001": {"code":"000001","exchg":"SZSE","name":"平安银行","product":"STK"}
    }
}
```

- 顶层按**交易所**分组（`SSE` / `SZSE` / `BJSE` 等）。
- 二层按**合约代码**。
- `product` 最关键：`STK`/`ETF`/`IDX` 分别走不同数据表。
- `opendate` / `expiredate` 为 `yyyymmdd`；缺省 `19000101` / `20991231` 等于"永远有效"。

## `stk_comms.json`（品种定义）

与 `stocks.json`（合约定义）对应。`stk_comms.json` 用来描述 **品种级别** 的信息（session、volscale、pricetick、minlots 等）：

```json
{
    "SSE": {
        "STK": {
            "name":"沪A",
            "session":"SD0930",   // 指向 stk_sessions.json 里的时段模板
            "volscale":1,
            "pricetick":0.01,
            "minlots":100,
            "lotstick":100
        },
        "ETF": { "session":"SD0930", "volscale":1, "pricetick":0.001 ... }
    }
}
```

`WtBtEngine.init(..., commfile="stk_comms.json")` 就是加载它，供 `ProductMgr` 查询。

## v0.9.9 新增：`openDate` / `expireDate`

在 `ContractMgr.py:L64-L67`：
```python
if "opendate" in cObj: cInfo.openDate = int(cObj["opendate"])
if "expiredate" in cObj: cInfo.expireDate = int(cObj["expiredate"])
```

`getContractInfo(stdCode, uDate)` / `getTotalCodes(uDate)` / `getCodesByProduct(pid, uDate)` 都会接受一个 `uDate` 参数（当前交易日），底层会过滤掉：
- `uDate < openDate`（还没上市）
- `uDate > expireDate`（已退市/到期）

这解决了回测中常见的"**样本外生存者偏差**"——老版本里即便合约那天还没上市，策略也能读到该股的"未来"数据。

## 上市/退市对策略的影响

- 回测长跨度股票池时，必须让 `stocks.json` 的 `opendate` 尽量准确，否则会把"新股次日之后"的数据强行用在更早的时间点。
- `expiredate` 对期货很重要，对股票只在退市处理时有用。
- 策略里通过 `ctx.stra_get_contract(stdCode)` 拿到 `ContractInfo`，自行决定要不要过滤。

## 常见坑

- **代码大小写**：`SSE.STK.600000` 不等于 `sse.stk.600000`；json 的键要严格。
- **product 名冲突**：同一交易所下股票和 ETF 都叫 `000001`——通过前缀 `STK.`/`ETF.` 区分，**不要**把两者放成同一 key。
- **新合约未更新**：`stocks.json` 过期，回测新股/新 ETF 取不到数据；常规做法是用 `wtpy/apps/datahelper/` 的脚本定期重生成。
- **复权因子**：`ContractInfo` 本身不带复权系数；复权由 `WtDtServo.setStorage(adjfactor="adjfactors.json")` 和底层 `WtDataStorageAD` 一起处理。

## 进一步阅读

- 交易时段：[SessionMgr 交易时段](./SessionMgr交易时段.md)
- 期货换月：[WtHotPicker 主力换月](../09-工具与扩展/WtHotPicker主力换月.md)
- 股票 vs 期货差异：[10-期货补充/与股票的差异清单](../10-期货补充/与股票的差异清单.md)
