---
层级: L2
前置阅读:
  - docs/03-引擎/三类策略引擎概览(CTA-HFT-SEL).md
  - docs/02-架构/整体架构与分层.md
本篇目标: 说明 `wtpy/wtpy/WtDtEngine.py` 的定位、与 `datakit_stk` / `datakit_fut` demo 的关系，以及它是如何把行情落成 csv/dsb 的。
读完后应能回答:
  - DataKit 为什么要单独成进程？
  - `dtcfg.yaml` 里都声明了什么？
  - 扩展 `BaseExtParser` / `BaseExtDataDumper` 分别什么时候用？
  - 落地的数据和回测用的数据目录是什么关系？
关键源码:
  - wtpy/wtpy/WtDtEngine.py
  - wtpy/demos/datakit_stk/dtcfg.yaml
  - wtpy/demos/datakit_stk/mdparsers.yaml
  - wtpy/demos/datakit_stk/runDT.py
术语表反链:
  - WtDtEngine
  - DataKit
  - Parser
  - dsb / dmb
---

## 定位：数据落地的独立进程

`WtDtEngine` = **DataKit 的 Python 入口**。它负责：
1. 启动一批 [Parser](../00-基础/术语表.md#parser行情解析器) 连接上游行情源；
2. 根据交易时段把 Tick 切成 Bar；
3. 把 Bar/Tick 按 **dsb/dmb/csv** 格式落到 `storage/` 目录；
4. （可选）把行情再转发给内部消息队列或用户自定义 dumper。

**为什么独立成进程？** 因为数据采集是 7×24 要运行的常驻任务（尤其期货有夜盘；股票也要提前分钟拉增量），和策略/回测的生命周期不同；独立进程也保证行情源断连不会拖垮策略。

## 类结构

```python
@singleton
class WtDtEngine:
    def __init__(self):
        self.__wrapper__ = WtDtWrapper(self)   # 加载 WtDtPorter.dll|so
        self.__ext_parsers__ = dict()
        self.__ext_dumpers__ = dict()

    def initialize(cfgfile, logprofile, bCfgFile=True, bLogCfgFile=True):
    def init_with_config(cfgfile:dict, logprofile:dict):
    def run(bAsync=False):
    def add_exetended_parser(parser: BaseExtParser):
    def push_quote_from_extended_parser(id, newTick, uProcFlag):
    def add_extended_data_dumper(dumper: BaseExtDataDumper):
    def get_extended_data_dumper(id):
```

公开 API 一目了然：**把配置文件喂进去 → `run` 起主循环**。扩展点是 Parser 和 Dumper。

## `dtcfg.yaml` 典型结构

看 `demos/datakit_stk/dtcfg.yaml`（实际字段以该文件为准）。典型字段：
- `basefiles`：同 `configbt.yaml`，告诉 DataKit 哪些合约要采集。
- `parsers`：引用 `mdparsers.yaml`，里面配若干行情源。
- `writer`：数据写入目标（二进制 `dsb` / 实时 `dmb` / csv）。
- `broadcast`：是否把实时数据通过 UDP 广播出去（给 `EventReceiver` 用）。
- `statemonitor`：引用 `statemonitor.yaml`，声明每个时段模板何时切天、何时开盘收盘。

## `mdparsers.yaml`

Parser 子配置：每项声明一个行情源（例如 `ParserCTP`、`ParserXTP`、`ParserFakeMdx`）+ 连接地址 + 订阅合约白名单。Parser 用的底层 dll 在 `wrapper/x64/parsers/` 或 `linux/parsers/` 下。

## 扩展点

### `BaseExtParser`（纯 Python 行情源）
继承后重写 `connect` / `disconnect` / `release` / `subscribe` 等，再用 `push_quote_from_extended_parser(id, newTick, uProcFlag)` 喂 Tick 到 C++。适合：
- 自研 feed（如 WebSocket 聚合、CSV 重放）
- 把 akshare/tushare 模拟实时灌进 DataKit

### `BaseExtDataDumper`（用户自定义落盘）
让 DataKit 把 Tick/Bar 同步喂到你定义的 dumper（例如写到 Kafka、ClickHouse）。

## 与 `datakit_stk` demo 的关系

`demos/datakit_stk/runDT.py` 典型代码：
```python
from wtpy import WtDtEngine
engine = WtDtEngine()
engine.initialize(cfgfile='dtcfg.yaml', logprofile='logcfgdt.yaml')
engine.run()   # 默认 bAsync=False，阻塞常驻
```

流程：
1. DataKit 读 `dtcfg.yaml` 加载合约表 + Parser；
2. 运行到交易时段时，Parser 推 Tick 进来；
3. C++ 侧按 `statemonitor.yaml` 的时段切分，写 `storage/csv|his|rt` 下对应文件；
4. 晚上/收盘后由 `statemonitor` 触发日线生成 / 小时线 / 历史整理。

详细 demo 精读见 [datakit_stk 数据落地 demo](../08-股票示例精读/datakit_stk-数据落地demo.md)。

## 和回测的数据关系

```
DataKit (runDT.py)
     │ 落盘
     ▼
storage/
 ├── csv/{code}_{period}.csv   ← 回测 mode=csv 时直接读
 ├── his/{code}/               ← 历史 dsb（压缩二进制）
 └── rt/                        ← 实时快照 dmb
```

回测时 `configBTStorage(mode="csv", path="../storage/")` 就是指这个目录；若 `mode="wtp"`，底层会走 `WtDataStorage` 读 dsb。

回测用的 csv 文件格式细节见 [数据流与文件格式](../05-数据/数据流与文件格式(dsb-dmb-csv).md)。

## 常见坑

- **时段未配置**：新添加的交易所没写进 `stk_sessions.json` → DataKit 不知道何时切 bar，落盘会缺失。
- **假日**：没维护 `holidays.json` 会导致周末也在"等行情"。
- **磁盘 IO**：DataKit 落 dsb 有批量窗；意外断电可能丢最新的"内存中未刷盘"那段。
- **Parser DLL 找不到**：`wrapper/x64/parsers/`、`linux/parsers/` 下缺少对应插件，初始化时会直接报错退出。

## 进一步阅读

- 数据格式：[数据流与文件格式(dsb-dmb-csv)](../05-数据/数据流与文件格式(dsb-dmb-csv).md)
- Python 侧查询落地数据：[WtDtServo 数据查询](../05-数据/WtDtServo数据查询.md)
- demo 精读：[datakit_stk 数据落地 demo](../08-股票示例精读/datakit_stk-数据落地demo.md)
