---
层级: L1
前置阅读:
  - docs/02-架构/整体架构与分层.md
本篇目标: 总结 `wtpy/wtpy/wrapper/` 下每个 Python 包装文件的职责、每个 dll/so 是什么、ctypes 如何加载、以及 Py→C++ / C++→Py 回调的调用方向。
读完后应能回答:
  - 为什么 `wrapper/` 下有 `x64/`、`x86/`、`linux/` 三个平台目录？
  - `WtBtWrapper.py` / `WtWrapper.py` / `WtDtWrapper.py` 分别包装哪个 dll？
  - 策略的 `on_bar` 是从哪儿被调到的？
  - 为什么 wrapper 类都打了 `@singleton`？
关键源码:
  - wtpy/wtpy/wrapper/WtBtWrapper.py:L1-L80
  - wtpy/wtpy/wrapper/WtWrapper.py
  - wtpy/wtpy/wrapper/WtDtWrapper.py
  - wtpy/wtpy/wrapper/PlatformHelper.py
  - wtpy/wtpy/WtUtilDefs.py
  - wtpy/wtpy/WtCoreDefs.py
术语表反链:
  - 动态库
  - 回调
  - ctypes
  - singleton
  - wrapper
  - Parser
  - Executer
  - Trader
---

## 为什么需要 wrapper 层

wtpy 的核心算法（行情回放、撮合、持仓计算、订单路由）都在 C++ 里。Python 调它只能走"共享库 + FFI"这条路。Python 标准库里的 [ctypes](../00-基础/术语表.md#ctypes) 提供了：
- `cdll.LoadLibrary(path)` → 加载 `.dll`/`.so`
- `api.some_func.argtypes = [...]` / `api.some_func.restype = ...` → 显式声明 C 函数签名
- `CFUNCTYPE(ret, *args)` → 构造 C++ 可回调的 Python 函数指针

但直接用 ctypes 写业务不友好（要到处做 `c_char_p` 编解码），所以有 **wrapper 包装层**：把裸 ctypes API 装成 Python 风格的方法。

## 平台目录

```
wrapper/
├── x64/       ← Windows 64-bit DLL + 行情/交易插件子目录
├── x86/       ← Windows 32-bit（现代工程基本跳过）
├── linux/     ← Linux .so（同时是 Docker/服务器线主用）
├── PlatformHelper.py  ← 运行时根据 os.name + ctypes.sizeof 自动挑目录
└── *.py       ← 对各 dll 的 Python 包装
```

`PlatformHelper.getModule("WtBtPorter")` 返回形如：
- Windows 64 位 → `x64/WtBtPorter.dll`
- Linux → `linux/libWtBtPorter.so`
- Windows 32 位 → `x86/WtBtPorter.dll`

## wrapper 文件职责表

| Python 文件 | 包装的 dll/so | 职责 | 单例？ | 调用方向 |
|---|---|---|---|---|
| `WtBtWrapper.py` | `WtBtPorter.dll` / `libWtBtPorter.so` | **回测引擎** 所有 C 接口（cta_get_bars / cta_set_position / backtest_init / run_backtest …） | ✅ | Py→C++ 为主，C++→Py 回调策略钩子 |
| `WtWrapper.py` | `WtPorter.dll` / `libWtPorter.so` | **实盘引擎** 的 C 接口 | ✅ | 同上 |
| `WtDtWrapper.py` | `WtDtPorter.dll` / `libWtDtPorter.so` | **数据引擎（DataKit）** C 接口 | ✅ | Py→C++ 启动/停止；C++→Py 推送状态 |
| `WtDtServoApi.py` | `WtDtServo.dll` / `libWtDtServo.so` | 在 Python 脚本里"只读"查询 datakit 落地数据（不启用整条 DataKit 流水线） | — | Py→C++ |
| `WtDtHelper.py` | `WtDtHelper.dll` / `libWtDtHelper.so` | csv ↔ dsb/dmb 数据格式转换、K 线重采样 | — | Py→C++ |
| `WtExecApi.py` | `WtExecMon.dll` / `libWtExecMon.so` | 独立执行器进程的 Python 面板，少见用 | — | Py→C++ |
| `WtMQWrapper.py` | `WtMsgQue.dll` / `libWtMsgQue.so` | 消息队列客户端，进阶场景才用 | — | 双向 |
| `ContractLoader.py` | `CTPLoader.dll` / `CTPOptLoader.dll` / `.so` | 从 CTP 柜台拉合约基础数据写 json | — | Py→C++ |
| `TraderDumper.py` | `TraderDumper.dll` / `libTraderDumper.so` | 账户快照 dump，开发调试用 | — | Py→C++ |
| `PlatformHelper.py` | （无）纯 Python | 根据平台选择 dll/so 路径，统一生成前缀/后缀 | — | — |

## 目录里那些"无 Python 包装"的库

`wrapper/x64/` / `linux/` 下还有几个不直接被 Python 包装，但被 C++ 引擎内部 `dlopen` 的：

- `WtDataStorage.dll|so` / `WtDataStorageAD.dll|so` → 底层数据读写引擎（`AD` 带复权；股票侧会用）
- `WtRiskMonFact.dll|so` → 风控模块
- `parsers/`、`traders/`、`executer/` 子目录 → 具体的 Parser / Trader / Executer 插件（由实盘配置 yaml 里按名字挑）

这些插件一般不用 Python 直接碰，靠 yaml 配置自动装载。详见 [实盘运行与配置](../07-实盘与监控/实盘运行与配置.md)。

## 单例模式（为什么打 `@singleton`）

`WtBtWrapper`、`WtWrapper`、`WtDtWrapper` 都用 `wtpy/WtUtilDefs.py` 里的 `@singleton` 装饰，确保同一进程里只加载一次 dll、共享同一份全局 C++ 引擎状态。
原因：C++ 引擎内部本就是 **进程单例**（静态实例 + 全局注册表），如果 Python 侧构造两份 wrapper 会导致二次注册、崩溃或状态错乱。

## Py → C++（正向调用）

举例 `CtaContext.stra_get_bars()` → 底层：
```
Python 策略:  self.__ctx__.stra_get_bars('SSE.ETF.510300', 'm5', 50)
               ↓
wtpy.CtaContext.stra_get_bars(...)
               ↓
WtBtWrapper.cta_get_bars(ctxId, code, period, cnt, cb)
               ↓
api.cta_get_bars(c_ulong, c_char_p, c_char_p, c_uint32, CFUNCTYPE(...))
               ↓
WtBtPorter.dll 里的 C 函数 cta_get_bars(ctxId, code, period, cnt, cb)
```

要点：
1. Python 字符串 → `c_char_p` 时要 `.encode('utf-8')`。
2. 返回"大块数据"时 C++ 不直接返回指针，而是让 Python **传一个回调**，C++ 按行喂回来（节省内存拷贝 + 避免所有权问题）。

## C++ → Py（反向回调）

策略的 `on_init` / `on_bar` / `on_tick` / `on_session_begin` / …… 都是**被 C++ 回调的**：
```
C++ 回放引擎 (WtBtPorter)
      │  时间到一根新的 Bar
      ▼
调用预先通过 register_cta_callbacks() 注入的 C 函数指针
      │  这个指针由 CFUNCTYPE 包装，背后是 WtBtWrapper 里的 Python 函数
      ▼
WtBtWrapper.on_cta_bar(ctxId, code, period, barStruct, newBar)
      ▼
通过 ctxId 找到对应 CtaContext 实例 → 调用其 on_bar()
      ▼
CtaContext.on_bar() → 最终调用 user BaseCtaStrategy 的 on_bar()
```

因此"你写的 `def on_bar(self, context, period, ...)` 到底是被谁调起的"答案是：**C++ 引擎按时间顺序回调到你的 Python 函数里**。这也是为什么循环不用你来写。

## 小结表：4 个常见的边界通路

| 用户代码 | 方向 | 背后路径 |
|---|---|---|
| `engine.run_backtest()` | Py → C++ | `WtBtEngine.run_backtest` → `WtBtWrapper.run_backtest` → `WtBtPorter.run_backtest` |
| 策略 `on_bar` 被触发 | C++ → Py | `WtBtPorter` → `WtBtWrapper.on_cta_bar` → `CtaContext.on_bar` → 用户策略 |
| `context.stra_set_position(code, 100)` | Py → C++ | `CtaContext.stra_set_position` → `WtBtWrapper.cta_set_position` → `WtBtPorter.cta_set_position` |
| `WtDtServo.get_bars(code, period, count)` | Py → C++ | `WtDtServo.get_bars` → `WtDtServoApi.get_bars` → `WtDtServo.dll` |

## 下一步

- 三种引擎对边界的使用差异：[三类策略引擎概览](../03-引擎/三类策略引擎概览(CTA-HFT-SEL).md)
- 直接看具体 wrapper：`wtpy/wtpy/wrapper/WtBtWrapper.py`（L1–L80 是 dll 加载 + 所有 C 函数签名）
