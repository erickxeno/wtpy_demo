# CTA 股票策略实盘部署指南

> 本文档描述将 `bt/cta_stk_bt_recent/` 中已验证的 DualThrust 回测策略，  
> 部署为基于 WonderTrader / wtpy 的 A 股 ETF 实盘交易系统的完整步骤。  
> **建议顺序执行，每步完成后再进入下一步。**

---

## 目录

1. [架构概览](#1-架构概览)
2. [前置准备](#2-前置准备)
3. [目录结构规划](#3-目录结构规划)
4. [Step 1 — 搭建 DataKit 行情服务](#step-1--搭建-datakit-行情服务)
5. [Step 2 — 创建实盘策略目录](#step-2--创建实盘策略目录)
6. [Step 3 — 配置交易通道（XTP）](#step-3--配置交易通道xtp)
7. [Step 4 — 配置执行器](#step-4--配置执行器)
8. [Step 5 — 配置策略引擎入口](#step-5--配置策略引擎入口)
9. [Step 6 — 首次仿真运行验证](#step-6--首次仿真运行验证)
10. [Step 7 — 切换真实账号上线](#step-7--切换真实账号上线)
11. [风控参数说明](#风控参数说明)
12. [常见问题排查](#常见问题排查)
13. [进阶：监控与告警](#进阶监控与告警)

---

## 1. 架构概览

```
┌──────────────────────────────────────────────────────────────────┐
│                          实盘进程拓扑                              │
│                                                                   │
│  [券商行情服务器]                                                  │
│       │  XTP/L1/L2                                               │
│       ▼                                                          │
│  ┌─────────────┐   exchange.membin(共享内存)   ┌──────────────┐  │
│  │  DataKit    │ ─────────────────────────────▶│  CTA Engine  │  │
│  │ (行情落地)  │                               │  (策略+执行)  │  │
│  └─────────────┘                               └──────┬───────┘  │
│       │ ../storage/                                   │           │
│       ▼ (历史K线持久化)                               │ 信号       │
│  ┌─────────────┐                               ┌──────▼───────┐  │
│  │  storage/   │ ◀──────────────────────────── │  Executer    │  │
│  │  (csv/bin)  │    (策略用历史K线)              │  (执行单元)  │  │
│  └─────────────┘                               └──────┬───────┘  │
│                                                       │ 委托       │
│                                                ┌──────▼───────┐  │
│                                                │  TraderXTP   │  │
│                                                │  (交易通道)  │  │
│                                                └──────┬───────┘  │
│                                                       │           │
│                                               [券商交易服务器]    │
└──────────────────────────────────────────────────────────────────┘
```

**两个独立进程，按顺序启动：**

| 进程 | 目录 | 职责 |
|------|------|------|
| DataKit | `live/datakit_stk/` | 接收实时行情、落地 storage、通过共享内存推送给策略进程 |
| CTA Engine | `live/cta_stk/` | 订阅行情、运行策略逻辑、生成信号、通过 TraderXTP 下单 |

---

## 2. 前置准备

### 2.1 申请 XTP 仿真账号

XTP（中泰证券极速交易平台）提供免费仿真环境，无需真实资金。

1. 前往 [XTP 开发者平台](http://xtp.zts.com.cn) 注册开发者账号
2. 申请仿真账户，获取以下三个凭据：
   - `user`：账号（通常是手机号）
   - `pass`：密码
   - `acckey`：AppKey（在控制台生成，每个 key 绑定一个 clientid）

**仿真服务器地址（固定）：**

| 用途 | 地址 | 端口 |
|------|------|------|
| 行情（L1） | `119.3.103.38` | `6002` |
| 交易 | `120.27.164.69` | `6001` |

### 2.2 确认 wtpy 安装

```bash
cd /Users/erick/xeno/ai/wt
source .venv/bin/activate
python -c "import wtpy; print(wtpy.__version__)"
```

> 本项目 `.venv` 中已安装 wtpy，无需重新安装。

### 2.3 确认 storage 目录有历史数据

策略启动时会读取历史 K 线做指标预热（`days=10` 需要 10 个交易日数据）：

```bash
ls bt/storage/csv/
# 应能看到 SSE.ETF.510300_m5.csv 或类似文件
```

---

## 3. 目录结构规划

在项目根目录下新建 `live/` 目录，结构如下：

```
live/
├── datakit_stk/          # 行情服务进程
│   ├── dtcfg.yaml        # DataKit 主配置
│   ├── mdparsers.yaml    # 行情解析器（XTP 账号填这里）
│   ├── logcfgdt.yaml     # 日志配置
│   └── statemonitor.yaml # 交易时间段监控
│
└── cta_stk/              # 策略引擎进程
    ├── config.yaml        # 引擎主配置
    ├── tdparsers.yaml     # 行情接入（接 DataKit 共享内存）
    ├── tdtraders.yaml     # 交易通道（XTP 账号填这里）
    ├── executers.yaml     # 执行器配置
    ├── filters.yaml       # 盘中干预过滤器
    ├── actpolicy.yaml     # 开平仓优先级策略
    ├── logcfg.yaml        # 日志配置
    └── run.py             # 启动入口
```

> **重要**：两个进程的 `storage` 路径必须指向同一个目录（`../../bt/storage/`），  
> DataKit 写入历史 K 线，CTA Engine 读取历史 K 线做指标计算。

---

## Step 1 — 搭建 DataKit 行情服务

### 1.1 创建目录

```bash
mkdir -p live/datakit_stk
```

### 1.2 创建 `live/datakit_stk/dtcfg.yaml`

```yaml
basefiles:
    commodity: ../../wtpy/demos/common/stk_comms.json
    contract:  ../../wtpy/demos/common/stocks.json
    holiday:   ../../wtpy/demos/common/holidays.json
    session:   ../../wtpy/demos/common/stk_sessions.json
    utf-8: true

shmcaster:                      # 共享内存转发（与 CTA Engine 同机必选）
    active: true
    path: ./exchange.membin     # 共享内存文件路径，CTA Engine 的 tdparsers.yaml 要对应

broadcaster:                    # UDP 广播（跨机器时启用，同机保持 false）
    active: false
    bport: 3997
    broadcast:
    -   host: 255.255.255.255
        port: 9001
        type: 2

parsers: mdparsers.yaml
statemonitor: statemonitor.yaml

writer:
    module: WtDataStorage
    async: true          # 股票行情量大，异步落地
    groupsize: 1000
    path: ../../bt/storage    # ★ 与回测 storage 共用同一目录
    savelog: false
    disabletick: false
    disablemin1: false
    disablemin5: false
    disableday: false
    disabletrans: true   # 暂不保存 L2 逐笔成交（节省磁盘）
    disableordque: true
    disableorddtl: true
```

### 1.3 创建 `live/datakit_stk/mdparsers.yaml`

```yaml
parsers:
-   active: true
    id: parser_xtp
    module: ParserXTP
    host: 119.3.103.38    # XTP 仿真行情服务器（真实账号时由券商提供）
    port: 6002
    protocol: 1           # TCP=1（仿真环境固定），L2 生产环境用 UDP=2
    buffsize: 128
    clientid: 1           # 同一进程固定为 1，范围 [1, 99]
    hbinterval: 15        # 心跳超时，单位秒
    local_ip: 0.0.0.0
    user: 你的XTP账号       # ← 替换
    pass: 你的XTP密码       # ← 替换
    # 订阅合约列表，逗号分隔；全市场订阅可以留空或写 ""
    code: SSE.ETF.510300,SSE.ETF.510050
```

> **注意**：`code` 字段只需填写策略实际交易的合约，订阅过多会增加网络和 IO 压力。

### 1.4 创建 `live/datakit_stk/statemonitor.yaml`

```yaml
SD0930:
    closetime: 1505
    inittime: 915
    name: 股白0930
    proctime: 1520
    schedule: true
```

### 1.5 创建 `live/datakit_stk/logcfgdt.yaml`

```yaml
config:
    async: true
    level: debug

sinks:
-   type: basic_file_sink
    filename: ./logs/DataKit.log
    pattern: '[%Y-%m-%d %H:%M:%S.%e][%l] %v'
    truncate: false

-   type: stdout_color_sink
    pattern: '[%m-%d %H:%M:%S.%e][%l] %v'
    level: info
```

### 1.6 创建 `live/datakit_stk/runDT.py`

```python
import time
from wtpy import WtDtEngine

if __name__ == "__main__":
    env = WtDtEngine()
    env.initialize("dtcfg.yaml", logcfg="logcfgdt.yaml")
    env.run(True)

    print("DataKit running, press Ctrl-C to exit")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        exit(0)
```

### 1.7 验证 DataKit 启动

```bash
cd live/datakit_stk
python runDT.py
```

**预期日志**（非交易时间看到 `connected` 即可，交易时间会看到 tick 流水）：

```
[INFO] ParserXTP connected to 119.3.103.38:6002
[INFO] ShmCaster started at ./exchange.membin
```

---

## Step 2 — 创建实盘策略目录

```bash
mkdir -p live/cta_stk
```

### 2.1 创建 `live/cta_stk/config.yaml`

```yaml
basefiles:
    commodity: ../../wtpy/demos/common/stk_comms.json
    contract:  ../../wtpy/demos/common/stocks.json
    holiday:   ../../wtpy/demos/common/holidays.json
    session:   ../../wtpy/demos/common/sessions.json

data:
    store:
        module: WtDataStorage
        path: ../../bt/storage    # ★ 与 DataKit 共用同一 storage

env:
    name: cta
    fees: ../../wtpy/demos/common/fees_stk.json
    filters: filters.yaml
    product:
        session: TRADING    # 覆盖全品种的最大时间模板
    riskmon:
        active: true
        module: WtRiskMonFact
        name: SimpleRiskMon
        base_amount: 100000     # ★ 改为你账户的实际资金（单位：元）
        basic_ratio: 101
        calc_span: 5
        inner_day_active: true
        inner_day_fd: 20.0      # 日内从高点回撤 20% 触发风控
        multi_day_active: false
        multi_day_fd: 60.0
        risk_scale: 0.3         # 触发风控后仓位降至理论仓位的 30%
        risk_span: 30

executers: executers.yaml
parsers:   tdparsers.yaml
traders:   tdtraders.yaml
bspolicy:  actpolicy.yaml

notifier:
    active: false    # 暂不推送 MQ 消息，稳定后可开启
```

---

## Step 3 — 配置交易通道（XTP）

### 3.1 创建 `live/cta_stk/tdtraders.yaml`

```yaml
traders:
-   active: true
    id: xtp_sim          # 执行器中通过此 id 绑定
    module: TraderXTP
    host: 120.27.164.69  # XTP 仿真交易服务器（真实账号时由券商提供）
    port: 6001
    user: 你的XTP账号      # ← 替换
    pass: 你的XTP密码      # ← 替换
    acckey: 你的XTPAppKey  # ← 替换（XTP 独有，开发者控制台生成）
    client: 1
    quick: true           # 极速委托模式

    riskmon:              # 交易通道级风控（独立于组合风控）
        active: true
        policy:
            default:
                cancel_stat_timespan: 10   # 统计撤单次数的时间窗口（秒）
                cancel_times_boundary: 20  # 该时间窗口内最多撤单次数
                cancel_total_limits: 470   # 单日总撤单上限
                order_stat_timespan: 10    # 统计下单次数的时间窗口（秒）
                order_times_boundary: 20   # 该时间窗口内最多下单次数
```

---

## Step 4 — 配置执行器

### 4.1 创建 `live/cta_stk/executers.yaml`

```yaml
executers:
-   active: true
    id: exec_xtp
    trader: xtp_sim      # ★ 与 tdtraders.yaml 中的 id 对应
    scale: 1             # 目标仓位放大倍数（1 = 按策略信号原始手数）
    local: true

    policy:
        default:
            name: WtExeFact.WtMinImpactExeUnit  # 最小冲击成本执行单元
            offset: 0       # 委托价相对基准价的偏移跳数
            expire: 5       # 委托超时秒数，超时自动撤单重发
            pricemode: 1    # 基准价：-1=己方最优 0=最新价 1=对手价（推荐）
            span: 500       # tick 驱动的下单间隔（毫秒）
            byrate: false
            lots: 1         # ETF 最小交易单位（100 份，框架自动处理）
            rate: 0

    clear:
        active: false       # 不启用过期主力自动清理（股票无需此功能）
```

---

## Step 5 — 配置策略引擎入口

### 5.1 创建 `live/cta_stk/tdparsers.yaml`

```yaml
parsers:
-   active: true
    id: parser_shm
    module: ParserShm                           # 共享内存行情接收
    path: ../datakit_stk/exchange.membin        # ★ 对应 DataKit 的 shmcaster.path
    gpsize: 1000
    check_span: 2
```

### 5.2 创建 `live/cta_stk/actpolicy.yaml`

```yaml
default:           # 股票 T+1，无平今概念，只需开仓/平仓
    order:
    -   action: closeyestoday
        limit: 0
    -   action: open
        limit: 0
```

### 5.3 创建 `live/cta_stk/filters.yaml`

```yaml
# 盘中不停机干预用，正常空配置即可
code_filters: {}
strategy_filters: {}
```

### 5.4 创建 `live/cta_stk/logcfg.yaml`

```yaml
config:
    async: true
    level: debug

sinks:
-   type: basic_file_sink
    filename: ./logs/CTA.log
    pattern: '[%Y-%m-%d %H:%M:%S.%e][%l] %v'
    truncate: false

-   type: stdout_color_sink
    pattern: '[%m-%d %H:%M:%S.%e][%l] %v'
    level: info
```

### 5.5 创建 `live/cta_stk/run.py`

```python
import time
import sys
sys.path.append("../../wtpy/demos/Strategies")

from wtpy import WtEngine, EngineType
from DualThrust import StraDualThrust

if __name__ == "__main__":
    engine = WtEngine(EngineType.ET_CTA)
    engine.init(
        folder="../../wtpy/demos/common/",
        cfgfile="config.yaml",
        commfile="stk_comms.json",
        contractfile="stocks.json",
        logcfg="logcfg.yaml",
    )

    # 策略参数与回测 bt/cta_stk_bt_recent/runBT.py 保持一致
    straInfo = StraDualThrust(
        name="pydt_SH510300",
        code="SSE.ETF.510300",
        barCnt=50,
        period="m5",
        days=10,       # 与回测一致
        k1=0.1,        # 与回测一致
        k2=0.1,        # 与回测一致
        isForStk=True,
    )
    engine.add_cta_strategy(straInfo)

    engine.run(True)

    print("CTA Engine running, press Ctrl-C to exit")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        exit(0)
```

---

## Step 6 — 首次仿真运行验证

### 6.1 创建 logs 目录

```bash
mkdir -p live/datakit_stk/logs
mkdir -p live/cta_stk/logs
```

### 6.2 启动顺序（必须先 DataKit 后 CTA Engine）

**终端 1：启动行情服务**

```bash
cd /Users/erick/xeno/ai/wt
source .venv/bin/activate
cd live/datakit_stk
python runDT.py
```

等待日志出现 `connected` 后，再启动 CTA Engine。

**终端 2：启动策略引擎**

```bash
cd /Users/erick/xeno/ai/wt
source .venv/bin/activate
cd live/cta_stk
python run.py
```

### 6.3 验证清单

| 检查项 | 预期输出 | 日志关键词 |
|--------|---------|-----------|
| DataKit 行情连接 | XTP 登录成功 | `ParserXTP connected` |
| 共享内存就绪 | membin 文件创建 | `ShmCaster started` |
| CTA Engine 行情接入 | 收到 tick | `on_tick` / `bar updated` |
| 交易通道连接 | XTP 交易登录 | `TraderXTP login success` |
| 策略初始化 | 指标预热完成 | `StraDualThrust initialized` |
| 有信号时 | 委托发出（仿真不实际成交） | `order placed` |

### 6.4 非交易时段验证

XTP 仿真在非交易时间也可登录，但不会有实时 tick。可以：

1. 确认两个进程都无报错退出
2. 检查 `exchange.membin` 文件是否生成（DataKit 正常）
3. 检查 CTA Engine 日志中是否有 `TraderXTP login success`

---

## Step 7 — 切换真实账号上线

> **前提**：仿真环境下策略运行 **至少 5 个完整交易日** 无异常后，再切换真实账号。

### 7.1 修改内容（仅需改账号和服务器地址）

**`live/datakit_stk/mdparsers.yaml`**：

```yaml
    host: <券商提供的真实行情服务器 IP>
    port: <券商提供的端口>
    user: 真实账号
    pass: 真实密码
```

**`live/cta_stk/tdtraders.yaml`**：

```yaml
    host: <券商提供的真实交易服务器 IP>
    port: <券商提供的端口>
    user: 真实账号
    pass: 真实密码
    acckey: 真实 AppKey
```

**`live/cta_stk/config.yaml`**：

```yaml
    base_amount: <你账户的真实资金>   # 单位：元
```

### 7.2 上线前 Checklist

- [ ] 仿真环境至少运行 5 个交易日无崩溃/连接中断
- [ ] 查看 `live/cta_stk/logs/CTA.log`，确认无 ERROR 级别日志
- [ ] `risk_scale` 设置合理（建议首周用 `0.1` 即一成仓）
- [ ] `base_amount` 已更新为真实资金
- [ ] 已在券商控制台为该 AppKey 设置合理的每日交易限额
- [ ] 确认 storage 目录有充足的历史数据（≥ 10 个交易日 m5 数据）

---

## 风控参数说明

`config.yaml` 中 `riskmon` 是组合级风控，作用于所有策略之上：

| 参数 | 含义 | 建议初始值 |
|------|------|-----------|
| `base_amount` | 组合基础资金（元） | 账户实际资金 |
| `inner_day_fd` | 日内从高点回撤多少 % 触发风控 | `20.0`（可根据策略波动调整） |
| `risk_scale` | 触发风控后目标仓位缩减至理论仓位的比例 | `0.3`（三成仓） |
| `multi_day_active` | 多日跟踪止损是否启用 | 初期 `false`，稳定后开启 |
| `multi_day_fd` | 多日回撤阈值 | `60.0` |

`tdtraders.yaml` 中 `riskmon` 是通道级风控，防止策略 bug 造成异常频繁下单：

| 参数 | 含义 | 说明 |
|------|------|------|
| `cancel_total_limits` | 单日总撤单上限 | 默认 470，接近交易所上限 500 |
| `order_times_boundary` | 时间窗口内最多下单次数 | 超出则该时间窗口内不再下单 |

---

## 常见问题排查

### Q1：DataKit 启动后 `exchange.membin` 没有生成

检查 `dtcfg.yaml` 中 `shmcaster.active` 是否为 `true`，以及对应路径是否有写权限：

```bash
ls -la live/datakit_stk/exchange.membin
```

### Q2：CTA Engine 报 `ShmParser: file not found`

DataKit 必须先于 CTA Engine 启动，且 `tdparsers.yaml` 中的 `path` 要与 DataKit `dtcfg.yaml` 的 `shmcaster.path` 完全对应（相对路径是相对各自的工作目录）。

### Q3：策略没有信号

可能是历史数据不足导致指标无法预热。检查：

```bash
ls -la bt/storage/csv/ | grep 510300
# 或
ls -la bt/storage/his/
```

若 m5 数据不足 10 个交易日（`days=10`），先用 `scripts/fetch_akshare.py` 补数据。

### Q4：XTP 登录报错 `error code: 11xx`

| 错误码 | 原因 | 处理 |
|--------|------|------|
| 1101 | 账号/密码错误 | 检查 yaml 文件中账号密码 |
| 1102 | AppKey 无效 | 在 XTP 控制台重新生成 |
| 1103 | clientid 冲突 | 同一账号下 clientid 需唯一，改为 2 或其他值 |

### Q5：委托发出但无成交（仿真环境）

XTP 仿真环境需要**在交易时间段内**才会撮合成交（09:30-11:30 / 13:00-15:00），非交易时间委托不会成交，属正常现象。

---

## 进阶：监控与告警

稳定运行后，可以扩展以下功能：

### 启用 WtMonSvr 监控面板

wtpy 内置了 Web 监控面板，在 `run.py` 中添加：

```python
from wtpy.monitor import WtMonSvr

svr = WtMonSvr(static_folder="../../wtpy/wtpy/monitor/html/")
svr.run(port=8099, bSync=False)
```

访问 `http://localhost:8099` 查看实时持仓、委托、K 线。

### 启用 MQ 通知

开启 `config.yaml` 中的 `notifier.active: true`，可将信号事件推送到 ZeroMQ，接入自定义告警（钉钉/微信/邮件）。

### 日志监控

```bash
# 实时跟踪 CTA Engine 日志
tail -f live/cta_stk/logs/CTA.log | grep -E "ERROR|order|position|risk"
```

---

*文档最后更新：2026-04-30*
