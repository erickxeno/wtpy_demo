---
层级: L2
前置阅读:
  - docs/03-引擎/三类策略引擎概览(CTA-HFT-SEL).md
  - docs/02-架构/Python与C++的边界.md
本篇目标: 以 `wtpy/wtpy/WtBtEngine.py` 为主源码，列公开方法、回测主循环调用顺序、`configbt.yaml` / `logcfgbt.yaml` 的作用。
读完后应能回答:
  - 一次回测从 `WtBtEngine()` 构造到 `release_backtest()` 之间顺序是什么？
  - `commitBTConfig` 为什么只生效一次？
  - `configBacktest` 的时间格式是什么？
  - `set_cta_strategy` 做了什么？
关键源码:
  - wtpy/wtpy/WtBtEngine.py:L22-L55
  - wtpy/wtpy/WtBtEngine.py:L101-L175
  - wtpy/wtpy/WtBtEngine.py:L279-L300
  - wtpy/wtpy/WtBtEngine.py:L371-L420
术语表反链:
  - WtBtEngine
  - 回测
  - Strategy
  - Context
  - 滑点
---

## 类定位

```python
@singleton
class WtBtEngine:
    def __init__(self, eType: EngineType = EngineType.ET_CTA,
                 logCfg: str = "logcfgbt.yaml",
                 isFile: bool = True,
                 bDumpCfg: bool = False,
                 outDir: str = "./outputs_bt"):
```

- 进程**单例**：同一进程一次只能有一份回测引擎活体。
- 构造时就已经通过 `WtBtWrapper` 加载 `WtBtPorter.dll|so` 并按 `eType` 初始化 C++ 侧 mocker。
- `logCfg`：指向日志配置（默认读当前目录 `logcfgbt.yaml`）。
- `outDir`：所有输出（`outputs_bt/<策略ID>/trades.csv / funds.csv / signals.csv ...`）落到此目录。

## 回测生命周期（典型调用序列）

```
1. engine = WtBtEngine(EngineType.ET_CTA)
         └── 加载 dll + 初始化 C++ CTA mocker 环境
2. engine.init(folder, cfgfile, commfile, contractfile, ...)
         └── 解析 configbt.yaml → __config__
         └── 加载 stk_comms.json → ProductMgr
         └── 加载 stocks.json   → ContractMgr
         └── 加载 stk_sessions.json → SessionMgr
3. engine.configBacktest(stime, etime)
         └── 覆盖 __config__["replayer"]["stime"/"etime"]
         └── 时间格式 yyyymmddHHMM（如 201901010930）
4. engine.configBTStorage(mode="csv", path="../storage/")
         └── 指定数据源（csv 直读 / wtp 库 / dsb）
5. engine.commitBTConfig()
         └── json.dumps(config) 下发到 C++ 侧；只生效一次
6. engine.set_cta_strategy(strategy, slippage=0, ...)
         └── C++ 创建一个 ctxId
         └── Python 侧包装成 CtaContext
7. engine.run_backtest()
         └── 若未 commit 则自动 commit
         └── 调 C++ 的主循环；期间 C++ 通过回调喂 on_bar/on_tick
8. （回测结束后）engine.release_backtest()
         └── 析构 C++ 引擎；同一进程可再 new 下一轮
```

上述顺序可在 `demos/cta_stk_bt/runBT.py` 里原样找到。

## 公开方法分类速查

### 初始化 / 配置
| 方法 | 作用 |
|---|---|
| `__init__(eType, logCfg, isFile, bDumpCfg, outDir)` | 构造 + 加载 dll |
| `init(folder, cfgfile, commfile, contractfile, sessionfile, holidayfile, hotfile, secondfile)` | 读取 yaml/json 配置 + 加载基础数据表 |
| `init_with_config(folder, config, ...)` | 同上但 config 是 dict |
| `configMocker(name)` | 改 `env.mocker`（`cta` / `stk` / `hft` / `sel`） |
| `configBacktest(stime, etime)` | 回测起止时间，`yyyymmddHHMM` 整数 |
| `configBTStorage(mode, path, storage)` | 数据存储：`csv` / `wtp` |
| `configIncrementalBt(base)` | 增量回测的基线 |
| `registerCustomRule(ruleTag, filename)` | 自定义连续合约换月规则 |
| `set_extended_data_loader(loader, bAutoTrans)` | 挂用户自定义历史数据加载器 |

### 策略注入
| 方法 | 作用 |
|---|---|
| `set_cta_strategy(strategy, slippage, hook, persistData, incremental, isRatioSlp)` | 注入 CTA 策略；`slippage` 单位为 tick 跳数；`isRatioSlp=True` 时为万分比 |
| `set_hft_strategy(strategy, hook)` | 注入 HFT 策略 |
| `set_sel_strategy(strategy, date, time, period, trdtpl, session, slippage, isRatioSlp)` | 注入 SEL 策略；按 `period` 定时触发 |
| `setExternalCtaStrategy(id, module, typeName, params)` | 让 C++ 写的 CTA 策略 dll 直接挂进来 |
| `setExternalHftStrategy(...)` | HFT 版本 |

### 运行控制
| 方法 | 作用 |
|---|---|
| `commitBTConfig()` | 将 `__config__` 字典下发 C++，只一次 |
| `run_backtest(bAsync, bNeedDump)` | 同步/异步运行 |
| `stop_backtest()` | 手动中止 |
| `release_backtest()` | 释放资源 |
| `cta_step(remark)` / `hft_step()` | 单步调试模式（需 `hook=True` 挂钩） |
| `set_time_range(begin, end)` | 多轮回测之间换时间窗 |
| `clear_cache()` | 清内存缓存 |

### 查询工具
| 方法 | 作用 |
|---|---|
| `getSessionByCode(code)` / `getSessionByName(name)` | 获取交易时段模板 |
| `getProductInfo(code)` / `getContractInfo(code)` | 查合约/品种 |
| `getAllCodes()` / `getCodesByProduct(pid)` / `getCodesByUnderlying(u)` | 合约代码集合 |
| `get_context(id)` | 取策略 Context |
| `getRawStdCode(stdCode)` | 连续合约 → 原始合约 |

### 引擎回调桩（C++→Py）
`on_init` / `on_schedule(date,time,taskid)` / `on_session_begin(date)` / `on_session_end(date)` / `on_backtest_end()`：
- 父类是"空实现"，但 `on_session_begin` 自动更新 `self.trading_day = date`，供外部查询。
- `on_backtest_end` 把回调转发到 Context；`WtBtAnalyst` 的 hook 就挂在这里。

## `configbt.yaml` 字段总览

以 `demos/cta_stk_bt/configbt.yaml` 为例（详见 [回测流程与配置](../06-回测/回测流程与配置(configbt.yaml).md)）：

```yaml
env:
    mocker: cta          # 也可 stk / hft / sel
replayer:
    basefiles:
        commodity:  ../common/stk_comms.json   # 品种定义
        contract:   ../common/stocks.json      # 合约定义
        holiday:    ../common/holidays.json    # 假日
        session:    ../common/stk_sessions.json # 交易时段
    etime: 201912011500  # yyyymmddHHMM
    fees:  ../common/fees_stk.json
    mode:  csv
    path:  ../storage/
    stime: 201909010900
```

`init(...)` 时，若传入 `commfile/contractfile/sessionfile/holidayfile/hotfile/secondfile`，会把对应 `basefiles.xxx` **覆盖**为 `os.path.join(folder, xxx)`。这也是为什么 `cta_stk_bt/runBT.py` 里写了 `folder='../common/'`, `commfile="stk_comms.json"`, `contractfile="stocks.json"` 就能跑。

## `logcfgbt.yaml` 的作用

控制日志输出级别、文件落地、回滚策略。默认的 `demos/cta_stk_bt/logcfgbt.yaml` 即可直接用；改这个文件不会影响回测逻辑，只影响日志。

## 常见坑

- **`commitBTConfig` 只生效一次**：想改配置要开新进程或改完代码重跑。
- **时间格式**：`configBacktest` 要 `yyyymmddHHMM` 整数（不是字符串）。凌晨 9:30 写成 `201901010930`。
- **`slippage` 单位**：默认是跳数（tick 数）；传 `isRatioSlp=True` 时变成万分比。
- **`folder=` 路径**：`init()` 里的 `folder` 会跟传进来的基础文件名拼成绝对路径，所以 `folder` 可以是相对当前工作目录。
- **输出数据缺失**：如果 `persistData=False`（`set_cta_strategy` 参数），回测不会落盘 `outputs_bt/` 下的 csv；`WtBtAnalyst` 自然找不到数据。

## 进一步阅读

- `demos/cta_stk_bt/runBT.py` 的全段注解：[cta_stk_bt 逐段精读](../08-股票示例精读/cta_stk_bt-回测demo逐段.md)
- 配置字段逐项含义：[回测流程与配置](../06-回测/回测流程与配置(configbt.yaml).md)
- 绩效报表怎么出：[WtBtAnalyst 绩效分析](../06-回测/WtBtAnalyst绩效分析.md)
