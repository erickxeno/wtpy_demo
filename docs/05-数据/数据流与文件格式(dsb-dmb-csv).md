---
层级: L2
前置阅读:
  - docs/03-引擎/WtDtEngine-数据引擎.md
  - docs/02-架构/Python与C++的边界.md
本篇目标: 梳理 WonderTrader 的数据存储格式（dsb / dmb / csv / WtBarStruct / WtTickStruct）以及读写入口（WtDtHelper）。
读完后应能回答:
  - 三种数据格式分别在什么场景下用？
  - 一根 Bar / 一笔 Tick 在内存里是什么字段？
  - 我有 csv 数据怎么转成 dsb 供回测？
  - 回测 `mode="csv"` 和 `mode="wtp"` 底层有何区别？
关键源码:
  - wtpy/wtpy/WtCoreDefs.py（WTSBarStruct/WTSTickStruct）
  - wtpy/wtpy/wrapper/WtDtHelper.py
  - wtpy/wtpy/WtDataDefs.py（WtNpKline/WtNpTicks 封装）
  - wtpy/demos/test_datahelper/
术语表反链:
  - Bar
  - Tick
  - K线
  - DataKit
  - dsb / dmb
  - 一级/二级行情
---

## 三种数据格式一览

| 格式 | 全称/特点 | 典型用途 | 读写方 |
|---|---|---|---|
| **csv** | 明文逗号分隔 | 冷启动导入、跨系统交换、回测 `mode=csv` 直读 | `WtDtHelper` 或任意外部工具 |
| **dsb** | WonderTrader 自有压缩二进制（历史块） | 常驻离线数据库 → 回测/实盘热加载 | `WtDataStorage` C++；`WtDtHelper` 可转换 |
| **dmb** | 内存映射的实时数据块 | 实时行情共享（DataKit 写，策略进程读） | `WtDataStorage` / 内存映射 |

核心思想：**DataKit 用 dmb 喂实时、用 dsb 归档历史**；回测时读 dsb（`mode=wtp`）或 csv（`mode=csv`）。

## 内存结构

在 `wtpy/wtpy/WtCoreDefs.py`：

```python
class WTSTickStruct(Structure):
    _fields_ = [
        ("exchg",     c_char*16),   # 交易所
        ("code",      c_char*32),   # 合约代码
        ("price",     c_double),    # 最新价
        ("open",      c_double),
        ("high",      c_double),
        ("low",       c_double),
        ("settle_price", c_double),
        ("upper_limit",  c_double), # 涨停
        ("lower_limit",  c_double), # 跌停
        ("total_volumn", c_uint32),
        ("volumn",       c_uint32),
        ("total_turnover", c_double),
        ("turn_over",    c_double),
        ("open_interest",c_uint32),
        ("diff_interest",c_int32),
        ("trading_date", c_uint32),
        ("action_date",  c_uint32),
        ("action_time",  c_uint32),
        ("pre_close",    c_double),
        ("pre_settle",   c_double),
        ("pre_interest", c_uint32),
        # 盘口 10 档：bid_price_0..9 / ask_price_0..9 / bid_qty_0..9 / ask_qty_0..9
        ...
    ]

class WTSBarStruct(Structure):
    _fields_ = [
        ("date",   c_uint32),  # yyyymmdd
        ("reserve",c_uint32),  # （内部占位）
        ("time",   c_uint64),  # 分钟线为 yyyymmddHHMM，日线=date
        ("open",   c_double),
        ("high",   c_double),
        ("low",    c_double),
        ("close",  c_double),
        ("settle", c_double),
        ("money",  c_double),  # 成交额
        ("vol",    c_uint64),  # 成交量
        ("hold",   c_uint32),  # 持仓量（期货）
        ("diff",   c_int32),
    ]
```

这两个结构体是 Python ↔ C++ 双向通行的数据单位；`WtNpKline`/`WtNpTicks`（在 `WtDataDefs.py`）是把 N 根结构体再包成 numpy view，策略里 `stra_get_bars` 返回的就是 `WtNpKline`。

## csv 目录布局

`demos/storage/csv/` 下典型结构：
```
storage/csv/
├── SSE.ETF.510300_m5.csv     # 上证 510300 ETF 5 分钟线
├── SSE.ETF.510300_d.csv      # 日线
├── SSE.STK.600000_m5.csv
└── ...
```

列头示例（分钟/日 K 线）：
```
date,time,open,high,low,close,volumn,turnover,diff
20190102,20190102093500,3.012,3.025,3.010,3.022,1234567,3.72e6,0
```

- `date`：交易日，`yyyymmdd`。
- `time`：K 线收盘时间 `yyyymmddHHMM`（日线和 date 一致）。
- `volumn` 是 wtpy 的拼写，按原样保留。
- 在仓库 `docker/launch_snooper.py` 里即用这种 csv 直接构造 Bar 数据（commit `a6aca5c`）。

## `WtDtHelper`——csv ↔ dsb/dmb 的瑞士军刀

`wtpy/wtpy/wrapper/WtDtHelper.py` 是 `WtDtHelper.dll|so` 的 Python 包装。常见操作：

| 方法（示例） | 作用 |
|---|---|
| `read_dsb_bars(path)` | 读一整根 dsb 日线/分钟线为 list |
| `store_bars(path, bars, period)` | 将 Python 侧 Bar 列表写成 dsb |
| `read_dsb_ticks(path)` | 读 dsb tick |
| `trans_csv_bars(csv_path, dsb_path, period)` | csv → dsb 转换 |
| `resample_bars(src_path, target_period, ...)` | K 线重采样（如 m1 → m5） |

> 实际方法名以该文件当前版本为准；`demos/test_datahelper/` 里有完整样例。

## 回测 `mode=csv` vs `mode=wtp`

在 `configbt.yaml`：
```yaml
replayer:
    mode: csv      # 或 wtp
    path: ../storage/
```

- `csv`：直接读 `path/csv/*.csv`；方便，但数据量大时加载慢、多进程并行会重复 IO。
- `wtp`：底层走 `WtDataStorage.dll`，读 `path/his/` 下的 dsb；**压缩后体积小 10×，随机访问快**；但需要先用 `WtDtHelper` 或 DataKit 把 csv 转成 dsb。

推荐的实战路径：冷启动用 csv，稳定后转 dsb。

## 数据采集→回测的一条路径

```
 行情源
   │
   ▼  WtDtEngine (datakit_stk/runDT.py)
storage/csv/{code}_{period}.csv   （明文，可被 pandas / Excel 打开）
storage/his/{code}/...dsb         （压缩二进制，高效回测）
storage/rt/ ...dmb                （内存映射实时快照）
   │
   ▼  WtBtEngine (cta_stk_bt/runBT.py)
outputs_bt/{straID}/trades.csv / funds.csv / signals.csv
   │
   ▼  WtBtAnalyst / WtBtSnooper
Strategy[*]_PnLAnalyzing_*.xlsx（绩效）
summary.json（Snooper 用）
```

## 常见坑

- **时区 / 时间格式**：WonderTrader 内部按 `int` 表达时间，不含时区。策略和数据源要统一到"交易所本地时间"。
- **重采样必须用 WtDtHelper**：自己写 pandas resample 会在收盘点、集合竞价边界出错。
- **csv 列顺序**：csv 直读对列顺序有隐式依赖，改列顺序会导致字段错位；首选 dsb。
- **Python 侧的 `newBar` dict**：策略 on_bar 拿到的是 CtaContext 转好的 dict，字段名是 `WTSBarStruct` 的小写成员（open/high/low/close/vol/money 等）。

## 进一步阅读

- 在 Python 里直接查询数据：[WtDtServo 数据查询](./WtDtServo数据查询.md)
- 合约管理：[ContractMgr 与 stocks.json](./ContractMgr与stocks.json.md)
- 交易时段：[SessionMgr 交易时段](./SessionMgr交易时段.md)
