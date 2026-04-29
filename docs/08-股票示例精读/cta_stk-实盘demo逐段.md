---
层级: L3
前置阅读:
  - docs/03-引擎/WtEngine-实盘引擎.md
  - docs/04-策略与上下文/CtaContext-股票主轴.md
  - docs/07-实盘与监控/实盘运行与配置.md
本篇目标: 逐段注解 `wtpy/demos/cta_stk/run.py`，解释 parser/trader/executer 实盘接入；同时把 6 个 yaml 在启动时的读取顺序讲清。
读完后应能回答:
  - `engine.init(...)` 实盘版比回测版多做了哪些事？
  - `isForStk=True` 给 DualThrust 带来什么差异？
  - `run(True)` 之后谁在跑循环？主线程为什么要 `while True: time.sleep(1)`？
  - 想把模拟盘切到真实盘要改哪些配置？
关键源码:
  - wtpy/demos/cta_stk/run.py:L1-L23
  - wtpy/demos/cta_stk/config.yaml
  - wtpy/demos/cta_stk/tdparsers.yaml / tdtraders.yaml / executers.yaml
  - wtpy/wtpy/WtEngine.py:L22-L63, L142-L260, L388-L446
  - wtpy/demos/Strategies/DualThrust.py
术语表反链:
  - 实盘
  - Parser
  - Trader
  - Executer
  - T+1
  - XTP
---

## 源码

```python
import time
from wtpy import WtEngine, EngineType

import sys
sys.path.append('../Strategies')
from DualThrust import StraDualThrust

if __name__ == "__main__":
    # 创建一个运行环境，并加入策略
    engine = WtEngine(EngineType.ET_CTA)                                  # (1)
    engine.init('../common/', "config.yaml",
                commfile="stk_comms.json", contractfile="stocks.json")    # (2)

    straInfo = StraDualThrust(name='pydt_SH600000',
                              code="SSE.STK.600000",
                              barCnt=50, period="d1",
                              days=30, k1=0.1, k2=0.1,
                              isForStk=True)                              # (3)
    engine.add_cta_strategy(straInfo)                                     # (4)

    engine.run(True)                                                      # (5)

    print('press ctrl-c to exit')
    try:
        while True:
            time.sleep(1)                                                 # (6)
    except KeyboardInterrupt:
        exit(0)
```

## 逐行注解

### (1) `engine = WtEngine(EngineType.ET_CTA)`

- 进入 `wtpy/wtpy/WtEngine.py:L27`。
- 加载 `WtPorter.dll|so`（注意：不是回测用的 `WtBtPorter`）。
- 构造后内部有三份 Context map：`__cta_ctxs__` / `__sel_ctxs__` / `__hft_ctxs__`，实盘允许多策略共存（但类型要和 `eType` 一致）。
- 日志默认读当前目录 `logcfg.yaml`；输出目录 `generated/`。

### (2) `engine.init('../common/', "config.yaml", commfile="stk_comms.json", contractfile="stocks.json")`

- `WtEngine.init`（`WtEngine.py:L142`）读主配置 + 引用的 5 个子 yaml：
  - `config.yaml` 指定 `executers: executers.yaml` / `parsers: tdparsers.yaml` / `traders: tdtraders.yaml` / `bspolicy: actpolicy.yaml` / `env.filters: filters.yaml`；
  - 这些子配置**也**会被加载和下发 C++。
- 基础数据：
  - 加载 `../common/stk_comms.json` → ProductMgr
  - 加载 `../common/stocks.json` → ContractMgr
  - 加载 yaml 里写死的 `../common/sessions.json` → SessionMgr（注意股票实盘 demo 这里用 `sessions.json`，不是 `stk_sessions.json`；因为实盘驱动要覆盖全品种）
- 副作用：向 C++ 侧注册 `WtDataStorage` 模块、`WtRiskMonFact` 模块等。
- 隐式：`notifier.url` 会初始化 MQ 客户端（IPC / TCP）。

### (3) `StraDualThrust(..., isForStk=True)`

- 实盘 demo 传了 **`isForStk=True`**；策略内部：
  - `on_init` 里 code 后缀变 `SSE.STK.600000-`——后缀 `+/-` 表示 **复权**（`+` 后复权，`-` 前复权），让 `stra_get_bars` 返回复权价（配合 adjfactors.json）。
  - `on_calculate` 里 `trdUnit = 100`（A 股 1 手 = 100 股）；`stra_enter_long(code, 1*trdUnit, 'enterlong')` 一次买 100 股。
  - 下跌突破分支被跳过（股票无做空能力）。
  - 只走多头开平，符合 A 股现实。

### (4) `engine.add_cta_strategy(straInfo)`

- `WtEngine.py:L388`：
  - C++ 分配 `ctxId`；
  - Python 侧包 `CtaContext(ctxId, strategy, wrapper, self)`；
  - 挂到 `__cta_ctxs__[ctxId]`。
- 回测是 `set_cta_strategy`（单一）；实盘是 `add_cta_strategy`（可重复调），支持一个引擎挂多条策略。

### (5) `engine.run(True)`

- `WtEngine.py:L437`：
  - 若未 `commitConfig()`，自动 commit；
  - `wrapper.run(bAsync=True)` → **异步**启动 C++ 主循环。
- C++ 侧会：
  1. 拉起所有激活的 Parser（`tdparsers.yaml`）→ 订阅合约；
  2. 拉起所有激活的 Trader（`tdtraders.yaml`）→ 连柜台；
  3. 加载所有 Executer（`executers.yaml`）→ 绑定对应 Trader；
  4. 对每条策略触发 `on_init`；
  5. 进入时间驱动：Tick 推入 / Bar 闭合 / 交易日切换 → 逐一回调 Python 策略；
  6. 策略 `stra_set_position` / `stra_enter_long` → 生成目标仓位 → Executer 差额下单 → Trader 发到柜台 → 回报返回策略 `on_trade`。

### (6) `while True: time.sleep(1)`

- 因 `run(True)` 是异步：函数立即返回，C++ 主循环在 **后台线程** 跑；
- Python 主线程若退出，进程会结束，后台线程被 OS 清理 → C++ 引擎中断。
- 所以要用 `while True: sleep` 保活；`KeyboardInterrupt` 捕获后 `exit(0)` 退出。
- 工业界版本会在这里接 `engine.release()` 做优雅下线（demo 省略）。

## 6 套 yaml 在启动时的读取顺序

```
WtEngine.init
    ├── 读 config.yaml
    │      └── env.* (引擎名、费率、风控)
    │      └── basefiles.*
    │      └── data.store
    │      └── notifier
    │      └── 引用 executers / parsers / traders / bspolicy / filters 指向子 yaml
    └── 读 commfile/contractfile（参数指定）

WtEngine.run -> wrapper.run -> C++ 侧依次 load:
    ├── parsers.yaml 里每个 active=true 的 Parser dll + 订阅
    ├── traders.yaml 里每个 Trader dll + 柜台登录
    ├── executers.yaml 里每个 Executer + 绑定 trader
    ├── filters.yaml（盘中可热加载）
    └── actpolicy.yaml
```

## 把"模拟盘"切到"真实盘"需要改哪些？

1. **Trader**：`tdtraders.yaml` 里把 `module: TraderXTP` 的 `host/port/user/pass/acckey/client` 换成真账户。
2. **Parser**：如果行情也走真柜台（而不是 DataKit 共享内存），把 `tdparsers.yaml` 改成 `ParserXTP` 并填账号。
3. **风控**：`config.yaml.env.riskmon.risk_scale` 先设小（0.1 / 0.2）灰度。
4. **合约范围**：`stocks.json` 要覆盖要交易的股票。
5. **Notifier**：`url` 换成接监控 / 告警服务的地址。
6. **日志**：`logcfg.yaml` 调大保留天数 + 文件级输出。

## 常见坑

- **Python 策略依赖找不到**：`sys.path.append('../Strategies')` 在容器 / CI 中要改成绝对路径。
- **isForStk 忘传**：DualThrust 会按期货 1 手单位下单 100 股 × 100 = 10000 股，账户资金不够；且会尝试开空仓（A 股不支持）。
- **主线程退出**：缺 `while True: sleep` 会导致策略启动 1 秒后就停。
- **交易通道掉线**：`on_channel_lost` 被回调时你没日志/告警 → 上线后"像是在跑但是零成交"。

## 进一步阅读

- 实盘 6 yaml 细节：[07-实盘与监控/实盘运行与配置](../07-实盘与监控/实盘运行与配置.md)
- CtaContext 股票 API：[04-策略与上下文/CtaContext-股票主轴](../04-策略与上下文/CtaContext-股票主轴.md)
- 回测 demo 对照：[cta_stk_bt 回测 demo 逐段](./cta_stk_bt-回测demo逐段.md)
- DataKit：[datakit_stk 数据落地 demo](./datakit_stk-数据落地demo.md)
