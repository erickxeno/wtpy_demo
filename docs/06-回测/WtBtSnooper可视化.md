---
层级: L2
前置阅读:
  - docs/06-回测/WtBtAnalyst绩效分析.md
本篇目标: 基于 `wtpy/wtpy/monitor/WtBtSnooper.py` + 仓库 `docker/launch_snooper.py` 经验（commit a6aca5c）讲 Snooper 的用途、HQChart 绘图、`summary.json` 来源。
读完后应能回答:
  - Snooper 为什么要起 FastAPI + 静态站？
  - `summary.json` 是谁写的？什么时候写？
  - 为什么前端 K 线报 native segfault？
  - 如何给 HQChart 指标按钮加中文 tooltip？
关键源码:
  - wtpy/wtpy/monitor/WtBtSnooper.py:L107-L500
  - docker/launch_snooper.py（本仓库）
  - docker/gen_summary.py（本仓库）
术语表反链:
  - HQChart
  - 回测
---

## Snooper 是什么

`WtBtSnooper` 是一个 FastAPI 后端 + 前端 Web UI，用于在浏览器里**查看/对比多次回测的结果**：
- K 线图（HQChart 渲染）
- 成交、信号散点叠加
- 每日净值 / 回撤曲线
- 绩效指标卡片（由 `summary.json` 提供）

典型启动：
```python
from wtpy.monitor import WtBtSnooper
WtBtSnooper().run_as_server(port=8081, host="0.0.0.0", bSync=True)
```

默认读 `./workspaces/` 或传入 `workspaces_root`。

## 关键对外接口

在 `WtBtSnooper.py:L107-L500`：

| 接口 | 作用 |
|---|---|
| `run_as_server(port, host, bSync)` | 起服务 |
| `add_static_folder(folder, path, name)` | 挂额外静态目录（前端图标/css） |
| `get_workspace_path(id)` | workspaceId → 磁盘路径 |
| `init_bt_apis(app)` | 注册所有 `/bt/xxx` FastAPI 路由 |
| `get_all_strategy(path)` | 某 workspace 下全部策略 |
| `get_bt_info / get_bt_funds / get_bt_closes / get_bt_trades / get_bt_rounds / get_bt_analysis` | 聚合接口 |

前端页面在 `wtpy/wtpy/monitor/static/` 下。

## `summary.json` 的位置

Snooper 为每个策略回测目录期待一个 `summary.json`。它**不是** `WtBtEngine` 默认生成的；需要：
1. 调用 `WtBtAnalyst` 或自己脚本算出指标；
2. 写到 `outputs_bt/<straID>/summary.json`。

本仓库 `docker/gen_summary.py`（commit `a6aca5c`）即做这件事：用 `wtpy.apps.WtBtAnalyst.Calculate` 计算 10 个字段并写 json。这样前端才不会 "500 / 缺字段"。

## HQChart K 线绘图

前端用 [HQChart](https://github.com/jones2000/HQChart)（开源金融图表库，MIT）画 K 线；数据由 `/bt/qry_bars`（在 `WtBtSnooper.py:L266-L302`）返回。

### 本仓库踩过的 native segfault（v3 修复记录）

commit `a6aca5c` 的 journal：
- 原实现走 `WtDtServo.get_bars` → 触发 wtpy 上游 **issue #164**：ETF 场景底层内存越界 → Python 进程 segfault。
- 修复：绕开 `WtDtServo`，改为直接读 `demos/storage/csv/<code>_<period>.csv` 自拼 Bar 结构，`bartime = YYYYMMDD*10000 + HHMM` 喂给前端。
- 效果：9648 根 K 线 < 1 秒渲染。
- 教训：Python 侧 dsb 路径尚不完全稳定；**csv 直读**是可靠的兜底。

## 指标按钮中文 Tooltip（v3 注入）

前端 14 个默认指标按钮英文短码对新手不友好。`launch_snooper.py` 的做法：**FastAPI 中间件 `_TooltipInjector`** 在 HTML 响应尾部注入一段 `<script>`，用 `MutationObserver` 监听 HQChart 动态渲染的 `.btn_ind` 节点，按 id 映射到中文 `title=`，**非侵入**。这也是为什么修改前端无需改 wtpy 上游源码。

## 启动 Snooper 的坑（仓库 FAQ 级别）

| 症状 | 根因 | 解决 |
|---|---|---|
| `500 summary.json not found` | `outputs_bt/<stra>/summary.json` 缺 | 跑回测后接 `gen_summary.py` |
| K 线页一打开 Python 进程崩 | 触发 wtpy issue #164 | 绕开 `WtDtServo`，csv 直读 |
| 指标按钮无 tooltip | HQChart 动态 DOM | MutationObserver 注入 `title` |
| `summary.json` 字段不全 → 前端 NaN | Analyst 字段名与前端期待不完全一致 | `gen_summary.py` 按前端期望的 10 个字段补齐：sharpe_ratio / sortino_ratio / calmar_ratio / max_falldown / max_profratio / annual_return / total_return / days / capital / win_rate |

## 在 Docker 里跑 Snooper

本仓库 `docker/launch_snooper.py` + `docker-compose.yml` + `Dockerfile`：
- 容器启动后先 `run-bt.sh`（若指定）跑回测 → 跑 `gen_summary.py` → 起 Snooper。
- `requirements.txt` 补齐：`itsdangerous` / `python-multipart` / `akshare` / `pytz`（FastAPI 依赖 + 后处理）。
- `docker-compose.yml` 把 `./docker` 和 `./bt` 挂进容器。

## 进一步阅读

- 绩效指标背后的算法：[WtBtAnalyst 绩效分析](./WtBtAnalyst绩效分析.md)
- monitor 监控服务的总览（不仅 Snooper）：[monitor 监控服务](../07-实盘与监控/monitor监控服务.md)
- 常见坑：[99-附录/常见问题FAQ](../99-附录/常见问题FAQ.md)
