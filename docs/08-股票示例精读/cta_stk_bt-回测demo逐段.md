---
层级: L3
前置阅读:
  - docs/03-引擎/WtBtEngine-回测引擎.md
  - docs/04-策略与上下文/CtaContext-股票主轴.md
  - docs/05-数据/ContractMgr与stocks.json.md
  - docs/06-回测/回测流程与配置(configbt.yaml).md
  - docs/06-回测/WtBtAnalyst绩效分析.md
本篇目标: 逐段注解 `wtpy/demos/cta_stk_bt/runBT.py` + `configbt.yaml`，把"从 engine 初始化 → 载入合约 → 注册策略 → run → generate report"的主循环讲透。
读完后应能回答:
  - 这份 27 行的 demo 背后实际发生了几层函数调用？
  - 为什么 `engine.init(folder='../common/')` 而不是绝对路径？
  - `StraDualThrust(code="SSE.ETF.510300", period="m5", days=30)` 三个参数与 configbt.yaml 的时间窗如何互动？
  - 回测结束后 `input('press any key...')` 是给谁用的？
关键源码:
  - wtpy/demos/cta_stk_bt/runBT.py:L1-L27
  - wtpy/demos/cta_stk_bt/configbt.yaml
  - wtpy/demos/Strategies/DualThrust.py
  - wtpy/wtpy/WtBtEngine.py:L22-L55, L149-L175, L183-L205, L279-L300, L371-L383, L411-L446
术语表反链:
  - 回测
  - WtBtEngine
  - CTA
  - T+1
  - Bar
---

## 源码（27 行）

```python
from wtpy import WtBtEngine, EngineType
from wtpy.apps import WtBtAnalyst

import sys
sys.path.append('../Strategies')
from DualThrust import StraDualThrust

if __name__ == "__main__":
    # 创建一个运行环境，并加入策略
    engine = WtBtEngine(EngineType.ET_CTA)                                 # (1)
    engine.init(folder='../common/', cfgfile="configbt.yaml",              # (2)
                commfile="stk_comms.json", contractfile="stocks.json")
    engine.configBacktest(201901010930, 201912151500)                      # (3)
    engine.configBTStorage(mode="csv", path="../storage/")                 # (4)
    engine.commitBTConfig()                                                # (5)

    straInfo = StraDualThrust(name='pydt_SH510300',
                              code="SSE.ETF.510300",
                              barCnt=50, period="m5",
                              days=30, k1=0.1, k2=0.1)                     # (6)
    engine.set_cta_strategy(straInfo)                                      # (7)

    engine.run_backtest()                                                  # (8)

    # 绩效分析
    analyst = WtBtAnalyst()
    analyst.add_strategy("pydt_SH510300", folder="./outputs_bt/",
                         init_capital=5000, rf=0.0,
                         annual_trading_days=240)                          # (9)
    analyst.run()                                                          # (10)

    kw = input('press any key to exit\n')                                  # (11)
    engine.release_backtest()                                              # (12)
```

## 逐行注解

### (1) `engine = WtBtEngine(EngineType.ET_CTA)`

- 进入 `wtpy/wtpy/WtBtEngine.py:L25`。
- `@singleton` → 同进程只会有一份；
- 构造里触发 `WtBtWrapper(self)` → 加载 `wrapper/x64/WtBtPorter.dll`（Windows）/ `linux/libWtBtPorter.so`。
- `eType == ET_CTA` → 调 `wrapper.initialize_cta(logCfg="logcfgbt.yaml", isFile=True, outDir="./outputs_bt")`。
- 副作用：当前目录下若不存在 `logcfgbt.yaml`，日志子系统会报 warning 但不致命。

### (2) `engine.init(folder='../common/', cfgfile="configbt.yaml", commfile="stk_comms.json", contractfile="stocks.json")`

- 进 `WtBtEngine.init`（`WtBtEngine.py:L149`）：
  - 读 `configbt.yaml`（`chardet` 嗅探编码）→ `yaml.full_load`；
  - 调 `init_with_config(folder, config, ...)`；
- `init_with_config`（L101）把 `commfile`/`contractfile`/`sessionfile` 等文件名**覆盖** `config["replayer"]["basefiles"]` 里的对应字段（用 `os.path.join(folder, fname)`）：
  - `commodity=../common/stk_comms.json`（stk_comms.json 已在 yaml 里相对路径指定，这里等效）
  - `contract=../common/stocks.json`
- 最后实例化并加载：
  - `ProductMgr` → 读 `stk_comms.json`
  - `ContractMgr` → 读 `stocks.json`
  - `SessionMgr` → 读 `stk_sessions.json`（yaml 里写死）

这一步之后 Python 内存里已经有：**4 类基础数据 + 1 份 yaml 配置 dict**。

### (3) `engine.configBacktest(201901010930, 201912151500)`

- `WtBtEngine.py:L183`：仅改 `self.__config__["replayer"]["stime"/"etime"]`。
- 覆盖了 yaml 里原有的 `stime=201909010900, etime=201912011500`。**代码里的参数优先级 > yaml**。

### (4) `engine.configBTStorage(mode="csv", path="../storage/")`

- `WtBtEngine.py:L192`：写 `self.__config__["replayer"]["mode"] = "csv"` + `"store" = {"path": "../storage/"}`。
- 这里用 `mode=csv` 就是让 C++ 直接从 `../storage/csv/` 下读明文 csv。想跑得快可以改 `mode=wtp` + 提前把 csv 转 dsb。

### (5) `engine.commitBTConfig()`

- `WtBtEngine.py:L279`：
  - `__cfg_commited__` 已 True → 直接 return（重复调用安全，但只有第一次生效）。
  - 否则 `cfgfile = json.dumps(__config__, ...)` → 调 `wrapper.config_backtest(cfgfile, False)`；
  - 到这一步 C++ 侧才真正接收完整配置。
- 副作用：若构造时 `bDumpCfg=True`，会把最终 config 写到当前目录 `config_run.yaml` / `.json` 方便审计。

### (6) `StraDualThrust(name='pydt_SH510300', code="SSE.ETF.510300", barCnt=50, period="m5", days=30, k1=0.1, k2=0.1)`

- 在 `wtpy/demos/Strategies/DualThrust.py`。
- 参数：
  - `name`：策略 ID，将用于 `outputs_bt/<name>/` 目录名。
  - `code`：主合约 `SSE.ETF.510300`。
  - `barCnt=50`：`on_calculate` 时取最近 50 根 K 线。
  - `period="m5"`：5 分钟 K 线（必须和 `../storage/csv/SSE.ETF.510300_m5.csv` 存在匹配）。
  - `days=30`：策略预热所需天数——DualThrust 用前 30 日的 HH/HL 算上下轨。
  - `k1=0.1, k2=0.1`：突破系数。
- `__is_stk__` 没传，默认 `False`——对 ETF 会按"手数 1 手 = 1 张"走期货式下单；如果要走股票 T+1 + 100 股单位，应传 `isForStk=True`（run.py 的实盘 demo 就传了）。

### (7) `engine.set_cta_strategy(straInfo)`

- `WtBtEngine.py:L371`：
  - `wrapper.init_cta_mocker(name, slippage=0, hook=False, persistData=True, incremental=False, isRatioSlp=False)` → C++ 侧给本策略分配 `ctxId`；
  - Python 端把它包装成 `CtaContext(ctxId, strategy, wrapper, self)`；
  - 把这个 context 挂到 `self.__context__`。

### (8) `engine.run_backtest()`

- `WtBtEngine.py:L411`：
  - 若未 commit 自动 commit；
  - `wrapper.run_backtest(bNeedDump=True, bAsync=False)` → C++ 主循环开始。
- **回测主循环**（概念级）：
  ```
  for t in 按 session 的时间轴 推进:
      if t 跨交易日:
          on_session_begin(newTDate) → Strategy.on_session_begin
      for each bar or tick 到达:
          CtaContext.on_bar(...) 或 on_tick(...)
          如果触发 on_calculate → Strategy.on_calculate → stra_set_position/stra_enter_long
          底层 mocker 撮合并更新持仓/资金/PnL
      if t 跨 session end:
          on_session_end → Strategy.on_session_end
  最后 on_backtest_end → Strategy.on_backtest_end
  落盘 outputs_bt/<name>/ 下的 csv + json
  ```

- 回测结束时生成的典型文件（对 `pydt_SH510300`）：
  ```
  outputs_bt/pydt_SH510300/
      trades.csv         -- 逐笔成交
      funds.csv          -- 每日资金 / 动态权益
      closes.csv         -- 每日持仓收盘市值
      signals.csv        -- 策略触发过的 signal
      btenv.json         -- 回测环境快照
  ```

### (9) `WtBtAnalyst().add_strategy("pydt_SH510300", folder="./outputs_bt/", init_capital=5000, rf=0.0, annual_trading_days=240)`

- Analyst 不依赖 Engine，它只读 `outputs_bt/<stra>/` 下的 csv/json。
- `init_capital=5000` 是告诉 Analyst "5000 元起步"；回测引擎本身不存这个数。
- `rf=0.0` 因为样例用无风险收益近似 0。
- `annual_trading_days=240` A 股惯例。

### (10) `analyst.run()`

- 默认生成 `<stra>_PnLAnalyzing_<stime>_<etime>.xlsx`；含净值 / 回撤 / 指标 / 成交明细多 sheet。

### (11) `kw = input('press any key to exit\n')`

- 作用：**让 Python 主线程阻塞**，方便你去看终端日志 / 文件。
- 如果想写进 CI / Docker，删掉这一行即可；或用 `bAsync=True` + `while True:` 方案。

### (12) `engine.release_backtest()`

- `WtBtEngine.py:L442` → `wrapper.release_backtest()` → C++ 资源释放。
- 若跳过这一步就 `exit()`，OS 会清理；但若同进程想再做第二轮回测，必须先 release。

## `configbt.yaml` 关键字段回顾

```yaml
env.mocker: cta                     # 用 CTA 模拟器（不是 stk，所以不强 T+1）
replayer.basefiles.commodity: ...   # 品种定义
replayer.basefiles.contract:  ...   # 合约定义
replayer.basefiles.holiday:   ...   # 假日
replayer.basefiles.session:   ...   # 时段
replayer.stime/etime: ...           # 被 configBacktest 覆盖
replayer.fees: ../common/fees_stk.json  # 股票费率/印花税
replayer.mode: csv                   # 被 configBTStorage 覆盖
replayer.path: ../storage/
```

## 反链：看哪一节延伸阅读

| 问题 | 去哪篇 |
|---|---|
| `WtBtEngine` 全部 API | [03-引擎/WtBtEngine-回测引擎](../03-引擎/WtBtEngine-回测引擎.md) |
| `CtaContext.stra_*` 细节 | [04-策略与上下文/CtaContext-股票主轴](../04-策略与上下文/CtaContext-股票主轴.md) |
| DualThrust 源码是什么 | `wtpy/demos/Strategies/DualThrust.py` |
| 绩效 xlsx 里的指标 | [06-回测/WtBtAnalyst绩效分析](../06-回测/WtBtAnalyst绩效分析.md) |
| 改 `mocker: stk` 会发生什么 | [06-回测/回测流程与配置](../06-回测/回测流程与配置(configbt.yaml).md) |
| 可视化看 K 线 / 成交 | [06-回测/WtBtSnooper可视化](../06-回测/WtBtSnooper可视化.md) |

## 跑通 demo 的前置准备清单

1. 数据目录 `demos/storage/csv/SSE.ETF.510300_m5.csv`（和对应日线）存在；
2. `demos/common/` 下 4 个基础 json（stk_comms / stocks / stk_sessions / holidays / fees_stk）齐全；
3. Python 能 import wtpy（`pip install wtpy` 或 `PYTHONPATH` 指到 `wtpy/`）；
4. `sys.path.append('../Strategies')` 指向 `demos/Strategies/DualThrust.py` 所在目录。

按上述 12 个步骤跑完，你应当在 `demos/cta_stk_bt/outputs_bt/pydt_SH510300/` 看到 csv 集和 xlsx 绩效文件。

## 本仓库的相关实战

- `bt/cta_stk_bt_recent/` 是在此基础上换成 **2026-03-23 → 2026-04-21** 近一个月的股票数据（由 `fetch_akshare.py` 抓回），验证策略能在短窗口跑出信号。
- `docker/gen_summary.py` 用 `WtBtAnalyst.Calculate` 把上述 csv 后处理成 `summary.json` 供 Snooper 读。
- 见 [99-附录/参考链接](../99-附录/参考链接.md)。
