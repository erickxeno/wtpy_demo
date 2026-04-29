---
层级: L2
前置阅读:
  - docs/05-数据/数据流与文件格式(dsb-dmb-csv).md
本篇目标: 基于 `wtpy/wtpy/WtDtServo.py` + `demos/test_dtservo`，讲 `get_bars` / `get_ticks` / `get_bars_by_date` 等 API 的用法。
读完后应能回答:
  - 我想在 Jupyter 里查一根 ETF 的 5 分钟线，要多少行代码？
  - `get_bars` 和 `get_bars_by_date` 参数有何差异？
  - WtDtServo 读的是 dsb 还是 dmb？
  - 为什么 WtDtServo 是"只读旁路"而不是整个 DataKit？
关键源码:
  - wtpy/wtpy/WtDtServo.py:L1-L160
  - wtpy/wtpy/wrapper/WtDtServoApi.py
  - wtpy/demos/test_dtservo/
术语表反链:
  - DataKit
  - Bar
  - Tick
---

## 定位

`WtDtServo` 是**独立于 `WtDtEngine` 的只读旁路**：不启动 Parser / 不落盘，只用既有的 `storage/` 数据目录 + 基础文件（品种/合约/时段）在 Python 进程里**按需读取**。适合：
- Jupyter 研究
- 给仓库 `docker/launch_snooper.py`、`gen_summary.py` 等周边脚本取数
- 回测前检查数据完整性

底层库：`WtDtServo.dll|libWtDtServo.so`（见 `wrapper/WtDtServoApi.py`）。

## 最小用法

```python
from wtpy import WtDtServo

servo = WtDtServo()
servo.setBasefiles(folder="./common/",
                   commfile="stk_comms.json",
                   contractfile="stocks.json",
                   sessionfile="stk_sessions.json",
                   holidayfile="holidays.json")
servo.setStorage(path="./storage/")
servo.commitConfig()

bars = servo.get_bars("SSE.ETF.510300", "m5",
                       fromTime=201901010930, endTime=201901311500)
print(len(bars), bars.closes[-1])
```

返回 `WtNpKline`（numpy view），可直接切片与聚合。

## 公开方法

| 方法 | 参数 | 说明 |
|---|---|---|
| `setBasefiles(folder, commfile, contractfile, sessionfile, holidayfile, ...)` | 基础数据目录 + 文件名 | 与 `WtBtEngine.init` 一致 |
| `setStorage(path, adjfactor)` | 数据目录 + 复权因子文件 | 一般指向和回测同一个 `storage/` |
| `commitConfig()` | — | 下发到 C++；只一次 |
| `clear_cache()` | — | 清内存缓存 |
| `get_bars(stdCode, period, fromTime=None, dataCount=None, endTime=0)` | | 按时间窗或数量取 K 线，返回 `WtNpKline` |
| `get_ticks(stdCode, fromTime=None, dataCount=None, endTime=0)` | | 取 Tick，返回 `WtNpTicks` |
| `get_ticks_by_date(stdCode, iDate)` | `iDate=yyyymmdd` | 某交易日全部 Tick |
| `get_bars_by_date(stdCode, period, iDate)` | | 某交易日该周期全部 K 线 |
| `get_sbars_by_date(stdCode, iSec, iDate)` | `iSec` 秒线周期 | 秒级 K 线（需数据源提供） |

### `get_bars` 的三种用法

```python
# 1. 指定起止时间
servo.get_bars("SSE.ETF.510300", "m5", fromTime=201901010930, endTime=201901311500)

# 2. 指定起始时间 + 数量
servo.get_bars("SSE.ETF.510300", "m5", fromTime=201901010930, dataCount=100)

# 3. 指定结束时间 + 数量（最常用：取最近 N 根）
servo.get_bars("SSE.ETF.510300", "m5", endTime=201912151500, dataCount=50)
```

`fromTime` / `endTime` 是 `yyyymmddHHMM` 整数。

## 和 DataKit 的关系

```
DataKit (写) --> storage/ <-- WtDtServo (读)
                              WtBtEngine (读)
```

- DataKit 在生产进程里**独占写**；
- WtDtServo 和回测引擎都**只读**同一个目录；
- 多个 WtDtServo 实例可以并行（单进程内单例，多进程各自一个）。

## 实战范例：本仓库 `docker/launch_snooper.py`

仓库根 `docker/launch_snooper.py` 在 commit `a6aca5c` 的设计里，曾经尝试用 `WtDtServo.get_bars` 取 K 线；但因 wtpy 上游 issue #164 在 ETF 场景下踩到内存越界，最终改成直接读 csv 自拼 Bar。这是一个**非常有用的反例**：

- **收益**：Snooper Web K 线 9648 根 < 1 秒渲染；
- **代价**：跳过 WtDtServo，绕开对上游 dll 的依赖；
- **启示**：Python 侧对 dsb 读取并非 100% 稳定，关键路径建议先用 csv 验证；或者直接用 `WtDtHelper.read_dsb_bars`（类似但更底层的接口）。

详见 [WtBtSnooper 可视化](../06-回测/WtBtSnooper可视化.md) 和 [常见问题 FAQ](../99-附录/常见问题FAQ.md) 中的 Snooper 章节。

## 常见坑

- **忘了 `commitConfig()`**：大多数 `get_*` 调用会静默返回空。
- **`stdCode` 命名规范**：股票 `SSE.STK.600000`、ETF `SSE.ETF.510300`、期货 `SHFE.rb.HOT`；规范错误直接取不到。
- **时段没覆盖**：`sessions.json` 里没声明"夜盘"或"集合竞价"会导致部分 Bar 被过滤。
- **复权**：`setStorage(adjfactor="adjfactors.json")`；没配的话股票历史价是原始价，跨除权除息日会跳变。

## 进一步阅读

- 数据格式详解：[数据流与文件格式](./数据流与文件格式(dsb-dmb-csv).md)
- 合约代码规范：[ContractMgr 与 stocks.json](./ContractMgr与stocks.json.md)
- test 样例：`wtpy/demos/test_dtservo/`
