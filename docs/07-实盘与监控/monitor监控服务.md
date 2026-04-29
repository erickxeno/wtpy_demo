---
层级: L2
前置阅读:
  - docs/07-实盘与监控/实盘运行与配置.md
  - docs/06-回测/WtBtSnooper可视化.md
本篇目标: 基于 `wtpy/wtpy/monitor/` 讲整体监控架构：DataMgr / EventReceiver / PushSvr / WatchDog / WtMonSvr / WtBtMon / WtBtSnooper 的分工。
读完后应能回答:
  - 实盘监控和回测可视化为什么都放在 `monitor/` 下？
  - `WtMonSvr` 默认用什么框架、哪些端口？
  - `EventReceiver` 为什么用 UDP？
  - 想做自定义 Web dashboard 应从哪个类继承？
关键源码:
  - wtpy/wtpy/monitor/__init__.py
  - wtpy/wtpy/monitor/WtMonSvr.py
  - wtpy/wtpy/monitor/EventReceiver.py
  - wtpy/wtpy/monitor/PushSvr.py
  - wtpy/wtpy/monitor/DataMgr.py
  - wtpy/wtpy/monitor/WatchDog.py
  - wtpy/wtpy/monitor/WtBtMon.py
  - wtpy/wtpy/monitor/WtBtSnooper.py
术语表反链:
  - 实盘
  - HQChart
---

## `monitor/` 模块清单

| 文件 | 职责 |
|---|---|
| `WtMonSvr.py` | 监控主服务：Flask HTTP + `/sock.io` WebSocket；对外 REST + 推送 |
| `EventReceiver.py` | UDP 端口接收组合进程广播的各类事件（订单/成交/PnL/日志） |
| `PushSvr.py` | 把 `EventReceiver` 收到的事件转发到 WebSocket / MQ |
| `DataMgr.py` | 读缓存组合落地数据（持仓、资金、成交）供 HTTP 接口用 |
| `WatchDog.py` | 自动拉起 / 重启 组合后台进程（通过 popen，读 `tasks.yaml` 等） |
| `WtBtMon.py` | 回测任务批量管理（投放 / 取消 / 结果收集） |
| `WtBtSnooper.py` | 回测结果可视化 FastAPI 后端（HQChart 前端） |
| `WtLogger.py` | 统一日志封装 |
| `static/` | 前端静态文件（HTML / JS / CSS） |

## 实盘链路

```
策略/引擎 进程
   │ (UDP)
   ▼
 EventReceiver  ──►  DataMgr (缓存)
   │
   ▼
 PushSvr
   │
   ▼ WS / HTTP
 浏览器 / 手机端
```

- 组合进程在 `config.yaml.notifier.url` 指定 MQ 地址（也可以是 UDP）。
- `WtMonSvr` 起 Flask；浏览器先拿 HTTP 静态页面，再 `socket.io` 长连接订阅实时推送。
- `WatchDog` 负责多组合调度：通过配置文件 / 命令行起多个组合进程。

## 回测管理链路

```
浏览器 ──► WtBtSnooper (FastAPI) ──► outputs_bt/<stra>/...
                                    └──► summary.json（由 Analyst 产出）
```

- `WtBtSnooper` 是**只读面板**，不参与调度。
- `WtBtMon` 则是**调度端**：向多台机器派发回测任务、收集结果（队列模型）。

## `WtMonSvr` 常用入口

```python
from wtpy.monitor import WtMonSvr
svr = WtMonSvr(static_folder="./static", deploy_dir="./deploy")
svr.run(port=8099, host="0.0.0.0")
```

典型端口：
- `8099`（HTTP + socket.io）
- `10086`（EventReceiver 监听 UDP）
- `8081`（Snooper，独立进程）

## 自定义 Dashboard

若要做自己的 Web 面板：
1. 继承 `WtMonSvr`，重写 `register_*_apis`；
2. 或**旁路**：起一个独立 FastAPI，把 `DataMgr` 当库用（读 `outputs_bt/<stra>/`）。本仓库 `docker/launch_snooper.py` 的中间件（`_TooltipInjector`）就是这种"非侵入旁路"的范式。

## WatchDog 要点

- 监控配置（`tasks.yaml`）中声明每个组合的 `name / path / cmd / restart_policy`。
- 进程 crash 后自动拉起；配合 notifier 可发 Slack / 飞书。
- 对新手：暂时不用 WatchDog，手工启动组合进程观察日志即可。

## 常见坑

- **UDP 丢包**：`EventReceiver` 是 UDP；网络抖动会丢消息；关键数据以"定时全量拉取 DataMgr"为准。
- **Snooper vs MonSvr 混淆**：前者只看**回测结果**（离线），后者看**实盘运行**。两边端口别撞。
- **跨机部署**：`WtMonSvr` 默认假设和组合同机；跨机要开 UDP 端口 + DataMgr 数据目录共享。

## 进一步阅读

- 回测面板：[WtBtSnooper 可视化](../06-回测/WtBtSnooper可视化.md)
- 实盘配置：[实盘运行与配置](./实盘运行与配置.md)
- 附录：`wtpy/docs/JOURNAL.md` 里上游自留的改动记录
