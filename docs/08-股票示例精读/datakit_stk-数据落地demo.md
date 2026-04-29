---
层级: L3
前置阅读:
  - docs/03-引擎/WtDtEngine-数据引擎.md
  - docs/05-数据/数据流与文件格式(dsb-dmb-csv).md
本篇目标: 基于 `wtpy/demos/datakit_stk/`，讲数据如何被采集、落盘、供回测复用；跟回测 / 实盘的数据目录关系。
读完后应能回答:
  - DataKit 启动脚本 `runDT.py` 做了什么？
  - `dtcfg.yaml` / `mdparsers.yaml` / `statemonitor.yaml` 分别控制什么？
  - `exchange.membin` 是怎么来的，谁在读？
  - 落在 `storage/csv/` 的文件命名规律？
关键源码:
  - wtpy/demos/datakit_stk/runDT.py:L1-L17
  - wtpy/demos/datakit_stk/dtcfg.yaml
  - wtpy/demos/datakit_stk/mdparsers.yaml
  - wtpy/demos/datakit_stk/statemonitor.yaml
  - wtpy/wtpy/WtDtEngine.py
术语表反链:
  - DataKit
  - dsb / dmb
  - Parser
  - WtDtEngine
---

## 源码（17 行，最小化）

```python
import time
from wtpy import WtDtEngine

if __name__ == "__main__":
    env = WtDtEngine()               # (1)
    env.initialize()                 # (2)
    env.run(True)                    # (3)

    print('press ctrl-c to exit')
    try:
        while True:
            time.sleep(1)            # (4)
    except KeyboardInterrupt:
        exit(0)
```

## 逐行注解

### (1) `env = WtDtEngine()`

- `WtDtEngine.py:L7` 构造：加载 `WtDtPorter.dll|so` + 初始化 `__ext_parsers__` / `__ext_dumpers__` 空 map。
- 单例：同进程再构造只会返回同一个实例。

### (2) `env.initialize()`

- 默认读 `dtcfg.yaml` + `logcfgdt.yaml`（当前目录）。
- C++ 侧：
  - 加载基础文件（`basefiles.*`）；
  - 按 `parsers` 字段把 `mdparsers.yaml` 里列出的每个 Parser 模块装载；
  - 按 `statemonitor` 字段装载 `statemonitor.yaml`（时段状态机）；
  - 打开/创建 writer，准备写 `storage/csv/`、`storage/his/`、`storage/rt/`。

### (3) `env.run(True)`

- `True` 即异步。C++ 后台线程：
  - 轮询 Parser 有无新数据；
  - 调 `on_tick`（内部）把 Tick 推给 writer → csv + rt/dmb；
  - 根据 `statemonitor` 的时段定义在收盘时生成日线 / 切 his/dsb。

### (4) `while True: time.sleep(1)`

- 同实盘 `run.py`：保主线程存活即可，真实工作在后台。

## `dtcfg.yaml` 关键字段

（以 `demos/datakit_stk/dtcfg.yaml` 实际为准）典型：
```yaml
basefiles:
    commodity:  ../common/stk_comms.json
    contract:   ../common/stocks.json
    holiday:    ../common/holidays.json
    session:    ../common/stk_sessions.json

writer:
    async: true
    groupsize: 1000
    path: ../storage/
    savelog: true
    disabled_types: []      # 过滤不想落的周期

parsers: mdparsers.yaml
statemonitor: statemonitor.yaml

broadcaster:
    active: true
    bport: 3997
    sport: 9001
    broadcast:              # 把实时行情 UDP 广播出去给策略/监控消费
    - host: 224.169.169.169
      port: 9001
      sendtype: 2
```

- `writer.path: ../storage/` + `writer.async: true` → Tick 先进内存队列再批写，避免抖动。
- `broadcaster`：可选；有广播实盘侧就能 `ParserUDP` 接上。

## `mdparsers.yaml`

列一批 Parser。股票典型：
```yaml
parsers:
- active: true
  id: parser_xtp
  module: ParserXTP
  host:  xtp-host
  port:  6002
  user:  账号
  pass:  密码
  acckey: ...
  filter: ['SSE.STK.600000', 'SSE.ETF.510300']   # 白名单
```

用 `ParserShm` 的是反过来的：**datakit 是 shm 的写端**，不需要 `ParserShm`；策略侧才用 `ParserShm` 去读 `exchange.membin`。

## `statemonitor.yaml`

按时段模板描述一天内要触发的"状态事件"：
```yaml
- name: SD0930
  auction: "0925,0930"
  close: 1500
  opentime: 0930
  postclose: 1520      # 收盘后多少分钟开始落日线 / 切 dsb
  ...
```

C++ 侧的时段状态机据此决定：何时把 `rt/dmb` 的临时快照合入 `his/dsb`。

## 落盘目录结构

```
storage/
├── csv/
│   ├── SSE.STK.600000_m1.csv
│   ├── SSE.STK.600000_m5.csv
│   ├── SSE.STK.600000_d.csv
│   ├── SSE.ETF.510300_m5.csv
│   └── ...
├── his/
│   └── SSE.STK.600000/*.dsb     # 历史二进制
├── rt/
│   └── SSE.STK.600000/*.dmb     # 内存映射实时
└── exchange.membin               # 全品种实时快照（供 ParserShm 读）
```

- 文件名规律：`{交易所}.{品种或大类}.{代码}_{周期}.csv`，周期为 `m1` / `m5` / `m15` / `m30` / `m60` / `d`。
- 本仓库 `docker/launch_snooper.py` 的 csv 兜底也是用这一命名规律找文件。

## 供回测复用

回测 `configbt.yaml` 的 `replayer.path: ../storage/` 直接指向 DataKit 落盘目录。等价于：
- `mode=csv` → 读 `storage/csv/*.csv`
- `mode=wtp` → 读 `storage/his/*.dsb`

**常见工作模式**：
- DataKit 容器 7×24 跑在一台机器；
- 回测 / Snooper 共享挂载 `storage/`；
- 实盘进程 `ParserShm` 通过 `exchange.membin` 拿实时。

## 常见坑

- **Parser 凭据过期**：DataKit 静默断连，落盘跳空；要看 `logcfgdt.yaml` 的 error/warn。
- **磁盘不够**：A 股 4500+ 股票 × 多周期 × 多天 = 10GB 量级；预估空间。
- **时段不完整**：北交所 / 科创板刚上时忘加时段模板 → 数据丢。
- **假日没加**：节假日也在"拉数据"，浪费。

## 进一步阅读

- L2 引擎定位：[03-引擎/WtDtEngine-数据引擎](../03-引擎/WtDtEngine-数据引擎.md)
- 数据格式：[05-数据/数据流与文件格式](../05-数据/数据流与文件格式(dsb-dmb-csv).md)
- WtDtHelper 转换：[09-工具与扩展/datahelper数据转换](../09-工具与扩展/datahelper数据转换.md)
