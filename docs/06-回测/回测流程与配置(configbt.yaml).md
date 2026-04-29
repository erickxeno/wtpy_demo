---
层级: L2
前置阅读:
  - docs/03-引擎/WtBtEngine-回测引擎.md
  - docs/05-数据/数据流与文件格式(dsb-dmb-csv).md
本篇目标: 对照 `demos/cta_stk_bt/configbt.yaml` 每个字段解释（`env.mocker`、`replayer.stime/etime`、`slippage`、`fees`、`replayer.mode/path` 等）。
读完后应能回答:
  - `env.mocker: cta` 和 `stk` 的选择对回测结果影响是什么？
  - 回测股票时 `fees_stk.json` 里包含哪几项收费？
  - 为什么 `basefiles` 里同时列出 `commodity`、`contract`、`session`、`holiday`？
  - `stime=201909010900` 含义？
关键源码:
  - wtpy/demos/cta_stk_bt/configbt.yaml
  - wtpy/wtpy/WtBtEngine.py:L57-L83, L183-L210
术语表反链:
  - 回测
  - 滑点
---

## 一份最小 `configbt.yaml`（股票 CTA）

```yaml
env:
    mocker: cta
replayer:
    basefiles:
        commodity: ../common/stk_comms.json
        contract:  ../common/stocks.json
        holiday:   ../common/holidays.json
        session:   ../common/stk_sessions.json
    etime: 201912011500
    fees:  ../common/fees_stk.json
    mode:  csv
    path:  ../storage/
    stime: 201909010900
```

## 字段逐项解释

### 顶层：`env`

| 键 | 取值 | 作用 |
|---|---|---|
| `env.mocker` | `cta`（默认） / `stk` / `hft` / `sel` | 选择底层模拟撮合器；`stk` 专门处理 A 股 T+1 与涨跌停；`cta` 更通用 |
| `env.incremental_backtest_base` | 字符串（基线策略 ID） | 只在使用 `configIncrementalBt` 时出现 |

> 一般股票回测写 `mocker: cta` 也可跑，但若需要严格 T+1 锁定与 ST 股±5% 涨跌停，推荐 `mocker: stk`（底层差异由 C++ 侧决定）。

### `replayer.basefiles`

| 键 | 文件内容 | 参考文档 |
|---|---|---|
| `commodity` | 品种定义（session/volscale/pricetick/minlots） | [ContractMgr 与 stocks.json](../05-数据/ContractMgr与stocks.json.md) |
| `contract`  | 合约清单 | 同上 |
| `session`   | 交易时段模板 | [SessionMgr 交易时段](../05-数据/SessionMgr交易时段.md) |
| `holiday`   | 交易日历 | 同上 |
| `hot`       | 期货主力换月规则（股票不需要） | [WtHotPicker 主力换月](../09-工具与扩展/WtHotPicker主力换月.md) |
| `second`    | 二主力规则 | 同上 |

`WtBtEngine.init(folder, ..., commfile, contractfile, ...)` 会把传入的文件名**覆盖**这里的相对路径。

### `replayer.stime` / `etime`

`yyyymmddHHMM` 整数格式。股票最早从 9:00（含集合竞价前）开始能兼容，日终以 15:00 结束。
`engine.configBacktest(stime, etime)` 就是修改这两项。

### `replayer.mode` / `path` / `store`

- `mode: csv` → 从 `path` 下 `csv/` 读明文。
- `mode: wtp` → 通过 `WtDataStorage.dll|so` 读 dsb。
- `store`：更复杂的存储字典；`configBTStorage(storage=...)` 可直接赋值。

### `replayer.fees`

指向 `fees_stk.json`（股票）或 `fees.json`（期货）。股票 `fees_stk.json` 字段示例：
```json
{
    "SSE.STK": {
        "open":   0.00025,   // 开仓佣金率
        "close":  0.00025,
        "close_today": 0.00025,
        "tax": 0.001,        // 卖出印花税
        "minimum": 5.0       // 最低佣金
    }
}
```

- `open`/`close`：买/卖的佣金率（双边）。
- `tax`：印花税（单边，卖出）。
- `minimum`：每笔最低佣金。
- 期货的 `fees.json` 还多 `margin`（保证金率）等字段。

### 隐式字段：`replayer.rules`

通过 `registerCustomRule(ruleTag, filename)` 注入，用于"自定义连续合约"——期货场景。

### 内部字段：`cta.strategy` / `hft.strategy`

当用 `setExternalCtaStrategy(...)` 挂 C++ dll 策略时，这些会被写入 `__config__`；常规 Python 策略不涉及。

## 滑点 slippage

**不在 yaml 里**，而是通过 `set_cta_strategy(slippage=2, isRatioSlp=False)` 传递：
- `isRatioSlp=False` 时 `slippage=2` 表示 2 个 tick。
- `isRatioSlp=True` 时 `slippage=2` 表示 0.02%（万分之二）。
- 股票一个 tick 通常是 0.01 元；ETF 0.001。

回测会把滑点**始终朝不利方向**叠加到成交价（买贵卖便宜），逼真模拟市场冲击。

## `logcfgbt.yaml` 要点

控制 `spdlog` 级别；不影响策略逻辑。

## 配置 → C++ 的流转顺序

```
1. engine.init(...)            加载 yaml 到 __config__
2. engine.configBacktest(...)  覆盖 replayer.stime/etime
3. engine.configBTStorage(...) 覆盖 replayer.mode/path/store
4. engine.commitBTConfig()     json.dumps + 下发 C++（一次性）
5. engine.set_cta_strategy(..., slippage=...)
6. engine.run_backtest()
```

第 4 步之后 yaml 不会再被读第二次。**配置改不了**，必须重启进程。

## 常见坑

- **时间跨度太短**：某些策略（如 DualThrust）需要 `days=30` 的预热，`stime` 到 `etime` 不够 30 个交易日会无信号。
- **`csv` 缺失合约**：`storage/csv/SSE.STK.600000_d.csv` 不存在会直接静默跳过该合约；信号为 0 可从这里找原因。
- **时段对齐**：`stime=201909010900` 若主合约是股票（9:30 开盘），前 30 分钟会被丢弃；若是期货夜盘则含义不同。
- **`replayer.fees` 缺失**：回测会**按 0 费率成交**，绩效会显著偏好。

## 进一步阅读

- demo 逐段：[cta_stk_bt 回测 demo 逐段](../08-股票示例精读/cta_stk_bt-回测demo逐段.md)
- 绩效报表：[WtBtAnalyst 绩效分析](./WtBtAnalyst绩效分析.md)
- 可视化：[WtBtSnooper 可视化](./WtBtSnooper可视化.md)
