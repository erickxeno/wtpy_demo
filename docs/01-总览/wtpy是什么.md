---
层级: L0
前置阅读:
  - docs/README.md
本篇目标: 用一页纸回答"wtpy 是什么、能干什么、跟 vnpy/backtrader 有什么不一样"。
读完后应能回答:
  - wtpy 与 WonderTrader 是什么关系？
  - wtpy 支持哪三类策略形态（CTA/HFT/SEL）？
  - 为什么它要 Python + C++ 混合，而不是纯 Python？
  - 它适合做股票回测吗？T+1 走哪条链路？
关键源码:
  - wtpy/README.md
  - wtpy/wtpy/__init__.py
术语表反链:
  - CTA
  - HFT
  - SEL
  - WtEngine
  - WtBtEngine
  - WtDtEngine
  - Strategy
  - Context
  - Bar
  - Tick
  - 回测
  - 实盘
  - T+1
---

## 一句话定义

**wtpy = WonderTrader（C++ 写的高性能多策略交易框架）的 Python3 子框架**。它把底层 C++ 引擎通过 `ctypes` 动态库暴露给 Python，让你可以"用 Python 写策略、让 C++ 跑回测/实盘"。

## 仓库关系

```
WonderTrader (C++ 主框架, 开源)
      └── wtpy (Python 适配, 开源, pip 可装)
```

- 官方源：<https://github.com/wondertrader/wtpy>
- pip：`pip install wtpy`
- 本仓库里：`wtpy/` 是 **git subtree 镜像**；我们不修改它，只阅读并在仓库根 `docs/` 写中文笔记。
- 对应版本：`0.9.9`，git commit `9fd4cd98`。

## 三类策略形态

| 形态 | 调度粒度 | 对应 Context | 典型 demo |
|---|---|---|---|
| [CTA](../00-基础/术语表.md#cta商品交易顾问--commodity-trading-advisor) | Bar / Tick | `CtaContext` | `demos/cta_stk_bt/` (股票回测)、`demos/cta_stk/` (股票实盘) |
| [HFT](../00-基础/术语表.md#hft高频交易--high-frequency-trading) | 逐笔 / 委托流 | `HftContext` | `demos/hft_fut/`、`demos/hft_fut_bt/` |
| [SEL](../00-基础/术语表.md#sel选股--selection) | 多标的批量 | `SelContext` | `demos/sel_fut_bt/` |

> 股票线优先：后续所有精读都围绕 CTA + 股票；期货只在 `docs/10-期货补充/` 做差异对照。

## 为什么 Python + C++ 混合

- **C++**：负责重算路径——数据回放、订单撮合、持仓/PnL 计算、行情推送等；毫秒级 tick 处理、海量 Bar 的高速回测，必须上 C++。
- **Python**：负责策略描述与胶水——定义策略类、读写 json/yaml、出 Excel、画图、做参数优化、对接数据源 SDK（tushare/akshare 等）。
- **边界**：`wtpy/wtpy/wrapper/*.py` 是 ctypes 包装层，`wrapper/x64/` 放 Windows DLL，`wrapper/linux/` 放 Linux SO。详见 [Python与C++的边界](../02-架构/Python与C++的边界.md)。

## 跟 vnpy / backtrader 的差异（小白对照）

| 维度 | wtpy | vnpy | backtrader |
|---|---|---|---|
| 底层 | C++ + Python | 纯 Python（部分 C 扩展） | 纯 Python |
| 回测速度 | 快（C++ 回放） | 中 | 慢 |
| 实盘 + 回测统一 | 同一策略代码通走 | 同一策略代码通走 | 实盘偏弱 |
| 券商/期货接入 | CTP/XTP/Mini 等（C++ 侧） | 品类更多、更活跃 | 较少 |
| 中文文档 | 偏薄 | 丰富 | 一般 |
| 定位 | 多策略组合工厂 | 策略 + 全栈平台 | 单策略研究 |

选择 wtpy 的典型理由：**要跑多策略组合、在意回测速度、不怕 C++ 动态库部署**。

## 一段 30 秒 demo：股票回测

参考 `wtpy/demos/cta_stk_bt/runBT.py`（见 [回测 demo 逐段精读](../08-股票示例精读/cta_stk_bt-回测demo逐段.md)）：

```python
from wtpy import WtBtEngine, EngineType
from wtpy.apps import WtBtAnalyst

engine = WtBtEngine(EngineType.ET_CTA)
engine.init(folder='../common/', cfgfile="configbt.yaml",
            commfile="stk_comms.json", contractfile="stocks.json")
engine.configBacktest(201901010930, 201912151500)
engine.configBTStorage(mode="csv", path="../storage/")
engine.commitBTConfig()
engine.set_cta_strategy(StraDualThrust(...))
engine.run_backtest()
# 出绩效
WtBtAnalyst().add_strategy("pydt_SH510300", folder="./outputs_bt/",
                           init_capital=5000).run()
```

四步：**配引擎 → 配时间窗 → 装策略 → 回测 → 出报告**。

## T+1 与股票特殊性

- A 股有 [T+1](../00-基础/术语表.md#t1) 限制：当日买入次日才能卖。
- 在 `CtaContext.stra_get_position` 里可分别查"总仓位"与"可用仓位"，策略代码要对这两者做区分。
- 回测引擎通过 `configbt.yaml` 中 `env.mocker: cta` + `replayer.basefiles.contract: stocks.json` 这一组合进入"股票模拟"分支。

## 读完下一步

- 继续 L0：[仓库结构总览](./仓库结构总览.md)
- 想直接看整体架构图 → [整体架构与分层](../02-架构/整体架构与分层.md)
- 想跑一个回测 demo → [cta_stk_bt 逐段精读](../08-股票示例精读/cta_stk_bt-回测demo逐段.md)
