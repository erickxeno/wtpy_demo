---
层级: L2
前置阅读:
  - docs/03-引擎/三类策略引擎概览(CTA-HFT-SEL).md
  - docs/03-引擎/WtBtEngine-回测引擎.md
本篇目标: 以 `wtpy/wtpy/WtEngine.py` 为主源码，列公开方法、实盘 6 套 yaml（`config.yaml` / `executers.yaml` / `tdtraders.yaml` / `tdparsers.yaml` / `filters.yaml` / `actpolicy.yaml`）的用途总览。
读完后应能回答:
  - 实盘引擎为什么要装 Parser、Trader、Executer 三层？
  - `add_cta_strategy` 和回测里 `set_cta_strategy` 有啥区别？
  - 风控（riskmon）是怎么接入的？
  - `run(bAsync=True)` 和回测 `run_backtest(bAsync=False)` 为什么默认不一样？
关键源码:
  - wtpy/wtpy/WtEngine.py:L22-L63
  - wtpy/wtpy/WtEngine.py:L142-L260
  - wtpy/wtpy/WtEngine.py:L388-L446
术语表反链:
  - WtEngine
  - 实盘
  - Parser
  - Trader
  - Executer
---

## 类定位

```python
@singleton
class WtEngine:
    def __init__(self, eType: EngineType,
                 logCfg: str = "logcfg.yaml",
                 genDir: str = "generated",
                 bDumpCfg: bool = False):
```

相对 `WtBtEngine`：
- 装载的 C++ 库是 `WtPorter.dll|so`（不是 `WtBtPorter`）。
- 引擎内部持有 **多份 Context 映射表**（`__cta_ctxs__` / `__sel_ctxs__` / `__hft_ctxs__`），实盘允许挂多条策略线到同一引擎（不过类型仍受 `eType` 限制）。
- 持 `__ext_parsers__` / `__ext_executers__` dict 以支持**自定义行情源 / 执行器**从 Python 侧接入。
- 默认输出目录 `generated/`，而不是回测的 `outputs_bt/`。

## 实盘数据流（再现一次）

```
上游行情
   │  （CTP / XTP / 自定义 Python Parser）
   ▼
[Parser]  ← tdparsers.yaml，或 add_exetended_parser(BaseExtParser)
   │
   ▼
[WtEngine / C++ 主循环]
   │  按交易时段切 bar / 推 tick 给策略
   ▼
[Strategy]  ← add_cta_strategy / add_hft_strategy / add_sel_strategy
   │  stra_set_position / stra_buy / ...
   ▼
[Executer]  ← executers.yaml，或 add_exetended_executer(BaseExtExecuter)
   │  目标仓位差额 → 委托
   ▼
[Trader]   ← tdtraders.yaml（addTrader）
   │  协议封装 → 柜台
   ▼
[Broker 柜台]
   │  回报
   ▼ Trader → Executer → WtEngine → Strategy.on_order/on_trade
```

## 6 套 YAML 总览

参考 `demos/cta_stk/`：

| 文件 | 指向 | 作用 | 可选？ |
|---|---|---|---|
| `config.yaml` | 主配置 | 引用其它所有 yaml，声明 `env.name`/`env.fees`/`env.product.session`/`env.riskmon`/`data.store`/`notifier` | 必需 |
| `tdparsers.yaml` | Parser 列表 | 配置要加载哪些行情源模块、连接地址、订阅合约 | 必需 |
| `tdtraders.yaml` | Trader 列表 | 配置交易通道（柜台地址、账号、协议） | 必需 |
| `executers.yaml` | Executer 列表 | 算法层：按哪个 Trader 下、用什么算法（diff/TWAP）、scale | 必需 |
| `filters.yaml` | 过滤器 | 盘中不停机干预：屏蔽某合约、冻结某策略、改仓位比例 | 可缺省 |
| `actpolicy.yaml` | 动作策略 | 买卖开平组合策略（配合 `bspolicy`） | 可缺省 |
| `logcfg.yaml` | 日志 | 输出级别 / 文件 / 回滚 | 可缺省 |

**`config.yaml` 的关键字段**（摘 `demos/cta_stk/config.yaml`）：
```yaml
basefiles: {commodity, contract, holiday, session}  # 跟回测一致
data.store: {module: WtDataStorage, path: ../storage/}
env:
  name: cta               # cta / hft / sel
  fees: ../common/fees_stk.json
  filters: filters.yaml
  product.session: TRADING
  riskmon: {active: true, module: WtRiskMonFact, name: SimpleRiskMon, ...}
executers: executers.yaml
parsers:   tdparsers.yaml
traders:   tdtraders.yaml
bspolicy:  actpolicy.yaml
notifier: {active: true, url: ipc:///wtpy/wt_cat_stk.ipc}
```

`riskmon` 是**组合级风控**：内置 `SimpleRiskMon` 提供日内/多日跟踪止损；`risk_scale` 会把策略的目标仓位乘一个比例下发执行。

## 公开方法分类

### 初始化 / 配置
| 方法 | 作用 |
|---|---|
| `init(folder, cfgfile, commfile, contractfile, sessionfile, holidayfile, hotfile, secondfile)` | 读 yaml 主配置 + 加载基础数据 |
| `configEngine(name, mode)` | 手动覆盖 `env.name` / `env.mode`（product/simulate 等） |
| `configStorage(path, module)` | 数据存储（通常 `WtDataStorage` 模块） |
| `registerCustomRule(ruleTag, filename)` | 同 `WtBtEngine` |
| `regCtaStraFactories(folder)` / `regHftStraFactories(folder)` / `regExecuterFactories(folder)` | 注册 C++ 策略/执行器工厂目录，用于 dll 热插 |

### Parser / Trader / Executer 注入
| 方法 | 作用 |
|---|---|
| `add_exetended_parser(parser: BaseExtParser)` | 从 Python 侧挂自定义 Parser（`id()` 唯一） |
| `add_exetended_executer(executer: BaseExtExecuter)` | 从 Python 侧挂自定义 Executer |
| `addTrader(id, params)` | 声明一个 Trader（等价改 `tdtraders.yaml` 增加一项） |
| `addExecuter(id, trader, policies, scale)` | 声明一个 Executer（等价改 `executers.yaml`） |
| `push_quote_from_extended_parser(id, newTick, uProcFlag)` | 外部 Parser 把 Tick 推进引擎 |

### 策略注入
| 方法 | 作用 |
|---|---|
| `add_cta_strategy(strategy, slippage)` | 注入 CTA 策略；实盘可挂多条 |
| `add_hft_strategy(strategy, trader, agent, slippage)` | HFT 需指定走哪个 Trader；`agent` 代理撮合 |
| `add_sel_strategy(strategy, date, time, period, trdtpl, session, slippage)` | SEL 策略 + 触发规则 |
| `addExternalCtaStrategy(id, params)` / `addExternalHftStrategy(id, params)` | 挂 C++ dll 写的策略 |

### 运行控制
| 方法 | 作用 |
|---|---|
| `commitConfig()` | 下发配置到 C++；只一次 |
| `run(bAsync: bool = True)` | 启动主循环；**默认异步**——返回后 Python 主线程空转（因此 demo 里常跟一个 `while True: time.sleep(1)`） |
| `release()` | 关停 |
| `get_context(id)` | 根据 ctxId 取 Context |

### 查询工具
跟 `WtBtEngine` 的几乎一致：`getSessionByCode / getSessionByName / getProductInfo / getContractInfo / getAllCodes / getCodesByProduct / getCodesByUnderlying / getRawStdCode`。

### 引擎回调桩（C++→Py）
同 `WtBtEngine`：`on_init` / `on_schedule` / `on_session_begin` / `on_session_end`。
`on_session_begin(date)` 会更新 `self.trading_day = date`，供外部查询。

## 跟回测 API 的差异对比

| 动作 | 回测 (`WtBtEngine`) | 实盘 (`WtEngine`) |
|---|---|---|
| 注入 CTA 策略 | `set_cta_strategy(...)` 只能 1 条 | `add_cta_strategy(...)` 可多条 |
| 启动 | `run_backtest(bAsync=False)` | `run(bAsync=True)` |
| 配置入口 | `configbt.yaml` | `config.yaml` + 5 个子 yaml |
| 输出目录 | `outputs_bt/` | `generated/` |
| 滑点 | 构造时 `slippage=int` 或 `isRatioSlp=True` | `slippage` 同理，但 Executer 层也可能二次调整 |

## 典型实盘启动流程

```python
from wtpy import WtEngine, EngineType
engine = WtEngine(EngineType.ET_CTA)
engine.init('../common/', 'config.yaml',
            commfile='stk_comms.json', contractfile='stocks.json')
engine.add_cta_strategy(StraDualThrust(...))
engine.run(True)   # 返回后主线程空转以让 C++ 后台跑
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    exit(0)
```

参考 `demos/cta_stk/run.py`，逐段精读见 [cta_stk-实盘demo逐段](../08-股票示例精读/cta_stk-实盘demo逐段.md)。

## 常见坑

- **Singleton 陷阱**：在 Jupyter / IPython 里多次 `WtEngine(...)` 不会真正重建 C++ 引擎。需要重启内核。
- **`run(bAsync=True)` 之后没 sleep**：Python 主线程直接退出会把 C++ 工作线程也一起释放，策略就没跑起来。
- **Parser / Trader 不匹配**：`tdparsers.yaml` 声明了某合约的订阅，但 `executers.yaml` 指的 trader 不支持这个合约，会在运行时报错。

## 进一步阅读

- `demos/cta_stk/` 逐段精读：[cta_stk-实盘demo逐段](../08-股票示例精读/cta_stk-实盘demo逐段.md)
- 实盘 6 套 yaml 细节：[实盘运行与配置](../07-实盘与监控/实盘运行与配置.md)
- 监控面板：[monitor 监控服务](../07-实盘与监控/monitor监控服务.md)
