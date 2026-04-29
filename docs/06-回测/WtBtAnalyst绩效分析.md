---
层级: L2
前置阅读:
  - docs/06-回测/回测流程与配置(configbt.yaml).md
本篇目标: 基于 `wtpy/wtpy/apps/WtBtAnalyst.py`，列出 `Calculate` 产出字段（sharpe/sortino/calmar/max_falldown/win_rate 等），并和 `bt/.../Strategy[*]_PnLAnalyzing_*.xlsx` 对照。
读完后应能回答:
  - `WtBtAnalyst.run()` 产出什么文件？
  - `init_capital` 为什么要在 Analyst 里再传一次？
  - Sharpe/Sortino/Calmar 分别衡量什么？
  - `outputs_bt/` 下哪几个 csv 是 Analyst 的输入？
关键源码:
  - wtpy/wtpy/apps/WtBtAnalyst.py:L13-L80（Calculate 类）
  - wtpy/wtpy/apps/WtBtAnalyst.py:L1607-L1710（add_strategy / run / run_new / run_simple / run_flat）
术语表反链:
  - 回测
  - Sharpe / Sortino / Calmar
  - Max Drawdown / 最大回撤
  - 胜率
---

## Analyst 工作流

```
回测结束 →
  outputs_bt/<straID>/
       ├── trades.csv         ← 成交明细
       ├── funds.csv          ← 每日资金 / 动态权益
       ├── signals.csv        ← 策略信号
       ├── closes.csv         ← 每日持仓收盘市值
       └── btenv.json         ← 回测环境快照
        │
        ▼   WtBtAnalyst(add_strategy -> run)
  <straID>_PnLAnalyzing_<stime>_<etime>.xlsx
  summary.json   （由 Calculate + 外部脚本组合产出；见 Snooper 章节）
```

## 典型使用

```python
from wtpy.apps import WtBtAnalyst

analyst = WtBtAnalyst()
analyst.add_strategy(
    sname="pydt_SH510300",
    folder="./outputs_bt/",
    init_capital=5000,
    rf=0.0,
    annual_trading_days=240)
analyst.run()       # 默认生成 xlsx；可传 outFileName
```

- `sname` 要和 `WtBtEngine.set_cta_strategy(StraDualThrust(name="pydt_SH510300", ...))` 的 `name` 一致。
- `folder` 指向回测输出根目录，Analyst 会在其下找 `outputs_bt/<sname>/`。
- `init_capital`：**再次声明**初始资金，因为回测底层不记录"起始金额"，只记录增量；要算收益率必须告诉 Analyst 起点。
- `rf`：无风险利率，Sharpe/Sortino 需要。
- `annual_trading_days`：年化因子，A 股习惯 240。

## `Calculate` 类产出的关键指标

在 `WtBtAnalyst.py:L13-L80` 及其后续方法：

| 指标 | 含义 | 用途 |
|---|---|---|
| `sharp_ratio` | 夏普比率 | 风险调整收益（总标准差） |
| `sortino_ratio` | 索提诺比率 | 只看下行波动的风险调整收益 |
| `calmar_ratio` | 收益 / 最大回撤 | 评估极端损失场景下的表现 |
| `upside_ratio` | 上行比率（潜在） | 非对称收益评估 |
| `max_falldown` / `max_drawdown` | 最大回撤幅度 | 权益曲线从峰到谷的最大跌幅 |
| `annual_return` | 年化收益率 | |
| `total_return` | 总收益率 | |
| `win_rate` | 胜率 | 盈利笔数 / 总笔数 |
| `profit_loss_ratio` | 盈亏比 | 平均盈利 / 平均亏损 |
| `days` | 回测交易日数 | |
| `capital` | 初始资金 | |

## 本仓库 `docker/gen_summary.py` 的实战

（commit `a6aca5c`）用 `Calculate` 生成前端 Snooper 期待的 10 个字段：

```
sharpe_ratio / sortino_ratio / calmar_ratio / max_falldown /
max_profratio / annual_return / total_return / days / capital / win_rate
```

这些字段被写到 `summary.json`，Snooper 前端读取后显示"绩效概览"。

## `run` / `run_new` / `run_simple` / `run_flat` 的区别

| 方法 | 特点 |
|---|---|
| `run(outFileName='')` | 默认全量：多 sheet 的 Excel（净值曲线 / 回撤 / 逐笔）。Analyst 版本演进时**兼容老字段** |
| `run_new(outFileName='')` | 新版入口；字段与计算更新 |
| `run_simple()` | 只算指标不写 Excel；用于脚本化 |
| `run_flat()` | 扁平化版本；多策略汇总到单 sheet |

本仓库 `docker/gen_summary.py` 走的是 `Calculate` 单独计算 + 自己写 json 的路径，**没有直接用 `run()` 出 Excel**。

## Excel 结构（`run()` 产出）

- **净值曲线 sheet**：每日权益 vs 初始资金基线。
- **回撤 sheet**：drawdown 曲线。
- **逐笔明细 sheet**：每一次开平仓的盈亏、hold 周期。
- **指标汇总 sheet**：Calculate 产出字段。

## 常见坑

- **`init_capital` 给错**：收益率 / Sharpe 全错。和 `configbt.yaml` / `set_cta_strategy` 里没这个字段（回测只记增量），Analyst 是唯一入口。
- **annual_trading_days**：外汇/港股要用 252，A 股 240；不同品种混合时要分策略分别算。
- **样本过短**：不到 ~60 个交易日，Sharpe/Sortino 波动极大，没有统计意义。
- **Calmar = inf**：回测全程无回撤时分母为 0；代码里返回 9999 做占位。

## 进一步阅读

- 可视化面板：[WtBtSnooper 可视化](./WtBtSnooper可视化.md)
- 回测配置：[回测流程与配置](./回测流程与配置(configbt.yaml).md)
- demo 的 Analyst 部分：[cta_stk_bt 回测 demo 逐段](../08-股票示例精读/cta_stk_bt-回测demo逐段.md)
