# wtpy 学习工程日志

记录学习过程中的里程碑、填过的坑、以及下一步计划。按时间倒序追加。

---

## 2026-04-21 · WtBtSnooper 增强:底部 14 个指标按钮中文 tooltip

### 背景
信号分析 tab 底部的 `VOL / RSI / KDJ / MACD / CCI / BIAS / ROC / HMA / LMA / VMA / BOLL / STD / RST / OBV` 是 HQChart 库的内置指标按钮,英文缩写不熟悉的人看着吃力。`docs/INDICATORS.md` 里有完整中文速查,但切屏看不方便。

### 做法
**非侵入式注入** —— 不改 wtpy 上游任何文件:

1. **FastAPI 响应中间件 `_TooltipInjector`**:拦截 `/backtest/backtest.html` 响应,在 `</body>` 前追加一段 `<script>`
2. **注入脚本逻辑**:
   - 定义 14 个指标 → 中文说明的映射表
   - `MutationObserver` 监听 DOM 变化(HQChart 异步渲染按钮)
   - 遍历所有叶子元素,匹配 `textContent` = 指标缩写,设置 `title=` + `cursor:help`
   - 叠加一个 10 秒内的定时兜底,防止 MutationObserver 漏掉首帧
3. **挂载时机**:猴补丁 `WtBtSnooper.init_bt_apis`,在原初始化后再 `add_middleware`,这样中间件是最外层 wrapper,看到的是未被 gzip 压缩的响应(虽然 600 字节的 HTML 本来也不会触发 gzip 压缩阈值 1000)

### 结果
鼠标 hover 任意一个按钮,浏览器原生 tooltip 显示例如:
> `KDJ · 随机指标 — K上穿D=金叉(买),下穿=死叉(卖);震荡市好用`

免改上游、免切屏,所有新手看得懂。

### 已知不足
- 使用浏览器原生 `title=` tooltip,样式朴素,黑字白底小方块
- 想要更漂亮的(自定义样式、带箭头、延迟等)可以改用 Element UI 的 `el-tooltip`,但要改 JS 入口代码
- RST 的具体定义因 HQChart 版本而异,我们标注"以 HQChart 版本为准",精确含义未确定

---

## 2026-04-21 · WtBtSnooper 修复 v3:信号分析 K 线 — 用 CSV 绕开 native segfault

### 症状
切到"信号分析"tab 时,Snooper 进程**整个死掉**(无 Python 异常日志),前端一串 `Network Error` toast。Python 层 try/except 捕获不到。

### 根因
该 tab 通过 `/bt/qrybars` → `WtBtSnooper.get_bt_kline` → `WtDtServo.get_bars` → 底层 C++ `WtDtServoApi.get_bars`。在**当前 macOS + Docker linux/amd64** 环境下,native 调用在读取 `.dsb` 二进制文件时 **段错误**,直接终结整个进程。

上游 wtpy issue **#164**(仍 OPEN)描述了类似形状的 bug —— **"非主力合约使用 dataCount 时内存越界"**。我们用的是 ETF(非主力合约),时间段查询内部可能被转成 dataCount 路径,触发同一个越界。这不是配置问题,是 C++ 端代码缺陷。

### 真正的修复(非临时)
既然 CSV 源数据本来就在 `demos/storage/csv/SSE.ETF.510300_m5.csv`,**直接跳过 WtDtServo,Python 层读 CSV 构造 K 线数据给前端**。

关键点:前端 JS 对 bartime 的编码是:
```js
date = Math.floor(bartime / 10000)   // YYYYMMDD
time = bartime % 10000                // HHMM
```
即 `bartime = YYYYMMDD * 10000 + HHMM`。

`launch_snooper.py` 里重写了 `WtBtSnooper.get_bt_kline`:
1. 从 `btenv.json` 读 `code / period / stime / etime`
2. 打开 `demos/storage/csv/<code>_<period>.csv`
3. 解析日期时间列,打包成上述 bartime 格式
4. 保留原逻辑从 `marks.csv` / `btchart.json` 读标记和指标配置
5. 返回 `(code, bars, index, marks)` 元组

### 结果
- qrybars 返回 9648 根 K 线(约 1 MB),< 1 秒
- 完全绕开 native C++,进程零崩溃
- 四个 tab 全部正常显示

### 未来改进(非紧急)
- 上游修复 #164 后,可考虑移除这个 monkey-patch 改回 native 路径(更快、支持更多格式)
- 当前 CSV loader 只认单一文件命名规则 `<code>_<period>.csv`,遇到其他 demo 可能需要扩展
- `turnover` 字段在 CSV 里没有,我填了 0.0;对 UI 展示无影响但不够严谨

---

## 2026-04-21 · WtBtSnooper 修复 v2:绩效概览字段缺失

### 症状
500 修复后绩效概览面板数值仍全为 0(胜率、夏普率、最大回撤、年化收益率等)。

### 根因
前端 `backtest.js` 读取 `btInfo.summary.{sharpe_ratio, sortino_ratio, calmar_ratio, max_falldown, max_profratio, annual_return, total_return, days, capital, win_rate}` 共 10 个字段,而我上一版 `gen_summary.py` 只生成了 `do_trading_analyze` 的交易统计字段,**没有生成这些高级指标**。结果接口返回 200,但字段不存在 → 前端显示 0。

### 修复
重写 `docker/gen_summary.py`,用 wtpy 自带的 `wtpy.apps.WtBtAnalyst.Calculate` 类从 `closes.csv` + `funds.csv` 完整计算:
- `sharpe_ratio` / `sortino_ratio` / `calmar_ratio` → 年化风险调整收益率
- `annual_return` / `total_return` → 年化/总收益率
- `max_falldown` → 最大回撤比例
- `max_profratio` → 最大盈利比例
- `days` → 回测交易日天数
- `win_rate` → 胜率(分数形式,不是百分比)
- `capital` → 初始资金

现有 cta_stk_bt 回测的实际指标:
```
days=201  total_return=9.11%  annual_return=10.97%
max_drawdown=8.64%  sharpe=0.907  calmar=1.269
```

### 教训
**前端期待的字段 ≠ 后端 `do_trading_analyze` 计算的字段**。Snooper 的前端 JS bundle 比后端 Python 逻辑"新"一代,期望的 summary 更丰富。后端现在既不生成 summary.json,前端读到什么不返回什么,就显示 0。排查方法:grep 前端 js bundle 里 `summary.xxx` 字段名,对齐填满。

---

## 2026-04-21 · WtBtSnooper 修复 v1:`summary.json` 缺失

### 症状
WtBtSnooper Web UI 所有数值显示为 0,前端弹出 `Request failed with status code 500`。
服务端 `/bt/qrybtcloses` 返回 500,日志里 `get_bt_closes` 抛 `FileNotFoundError: summary.json`。

### 根因
新版 `WtBtEngine` + `WtBtAnalyst` 的输出结构已经不再生成 `summary.json`,但 `WtBtSnooper.get_bt_closes`(`WtBtSnooper.py:540-551`)和 `get_bt_info`(`WtBtSnooper.py:455`)仍硬依赖 `summary.json` 读取 `capital` 等字段。这是上游 wtpy 版本内部的不一致。

### 修复
- 新增 `docker/gen_summary.py` 后处理器,用 `WtBtSnooper.do_trading_analyze` 的算法从 `closes.csv` + `funds.csv` 反算出完整 summary,写入 `outputs_bt/<strategy>/summary.json`
- `scripts/run-bt.sh` 在回测跑完后自动执行 post-processor,遍历 `outputs_bt/` 下所有策略目录逐个处理
- `docker-compose.yml` 挂载 `./docker:/workspace/docker:ro`,让容器随时能取到 gen_summary.py,不需 `docker cp`
- `docker/requirements.txt` 补 `itsdangerous` / `python-multipart`(starlette SessionMiddleware 和 FastAPI Form 依赖,上游 setup.py 漏列)

### 用法
```bash
# 老的回测要补生成 summary.json:
docker exec wtpy-dev python /workspace/docker/gen_summary.py \
    /workspace/wtpy/demos/cta_stk_bt/outputs_bt pydt_SH510300 5000

# 新跑的回测:run-bt.sh 已自动处理,无需手动做
./scripts/run-bt.sh demos/cta_stk_bt 5000    # 第二个参数是 init_capital
```

### 教训
WtBtSnooper 和 WtBtEngine 是上游同一个包里的两个模块,但存在**版本内部不一致** —— 一个模块的输出格式另一个模块不认。遇到类似 500 不要先怀疑自己配错,先去读出错端点的源码,看它到底依赖哪些文件。

---

## 2026-04-21 · 第一阶段:环境就绪

### 目标达成

- ✅ 本地搭好可复现的 wtpy 开发 / 回测环境(macOS + Docker Desktop)
- ✅ `cta_stk_bt` demo 完整跑通:4324 笔交易,生成 Excel + CSV + JSON 全套输出
- ✅ 版本控制就位,后续改动可追踪

### 为什么是 Docker,而不是 macOS 原生

wtpy 的 C++ 底层(`wtpy/wrapper/linux/*.so`、`wtpy/wrapper/x64/*.dll`)**不提供 macOS Mach-O 二进制**,`PlatformHelper.py` 的平台分支只有 Windows / Linux 两条路。macOS 进入 Linux 分支后试图加载 ELF `.so`,是操作系统层面的硬性禁止。

要么自己编译 wondertrader for Darwin(多日工作量,不适合学习起步),要么在 Linux 容器里跑 —— 并且后者与生产环境(Linux 服务器)一致,是自然选择。

### 工程目录结构

```
wt/
├── docker/                    # Docker 构建文件
│   ├── Dockerfile             # python:3.10-slim-bookworm + 系统库
│   ├── requirements.txt       # numpy==1.23.5, pandas==1.3.5(ABI 兼容关键)
│   └── launch_snooper.py      # WtBtSnooper 启动脚本(容器内执行)
├── docker-compose.yml         # 容器编排,挂载 + 端口映射
├── scripts/                   # 常用入口脚本
│   ├── shell.sh               # 进容器 bash
│   ├── run-bt.sh              # 一键跑回测
│   ├── run-snooper.sh         # 启动回测查看 Web UI
│   └── bt-summary.sh          # 终端快速查看回测摘要
├── wtpy/                      # 上游 wtpy 源码(独立 git,gitignored)
├── outputs/                   # (预留)容器内 /workspace/outputs 映射
├── notebooks/                 # (预留)Jupyter 工作目录
└── docs/
    └── JOURNAL.md             # 本文件
```

### 常用命令速查

```bash
# 进容器交互式 bash
./scripts/shell.sh

# 一键跑 cta_stk_bt 回测(默认)
./scripts/run-bt.sh

# 跑其他 demo
./scripts/run-bt.sh demos/cta_fut_bt

# 启动回测 Web UI(WtBtSnooper)
./scripts/run-snooper.sh
# 然后在 macOS 浏览器打开:
#   http://127.0.0.1:8081/backtest/backtest.html
# 预配置了 cta_stk_bt / cta_fut_bt 两个 workspace

# 终端快速查看回测结果摘要
./scripts/bt-summary.sh

# 容器停止 / 启动
docker compose down
docker compose up -d
```

### 回测产物位置

所有回测产物都在**宿主 macOS 文件系统**上(通过 volume 挂载),可直接打开:

| 产物 | 位置 |
|------|------|
| **PnL 绩效 Excel** | `wtpy/demos/cta_stk_bt/Strategy[pydt_SH510300]_PnLAnalyzing_*.xlsx` |
| 成交 / 平仓 / 信号 CSV | `wtpy/demos/cta_stk_bt/outputs_bt/pydt_SH510300/*.csv` |
| 资金曲线 | `wtpy/demos/cta_stk_bt/outputs_bt/pydt_SH510300/funds.csv` |
| 回测元数据 JSON | 同上,`*.json` |

macOS 打开示例:
```bash
# 打开 Excel 绩效报告
open "wtpy/demos/cta_stk_bt/Strategy[pydt_SH510300]_PnLAnalyzing_20190102_20191031.xlsx"

# Finder 定位到输出目录
open wtpy/demos/cta_stk_bt/outputs_bt/pydt_SH510300/
```

### 已填过的坑

1. **macOS 原生不可行** —— Linux `.so` 与 Mach-O 不兼容(二进制层面硬阻塞)
2. **`python3.10` 多版本陷阱** —— `/Users/erick/.local/bin/python3.10` 是 arm64,和 x86_64 shell 不兼容;系统里还有 `/usr/local/bin/python3.10` 是 x86_64(此环境用不上,已改用 Docker)
3. **pandas 1.3.5 + numpy 2.x ABI 不兼容** —— `ValueError: numpy.dtype size changed`。必须钉死 `numpy==1.23.5`
4. **pip 版本坑** —— pip 26.x 对 `numpy<1.24` 这种范围约束解析异常;用精确版本号 `numpy==1.23.5` 更稳
5. **`runBT.py` 最后的 `input()`** —— 在非交互模式下会挂起,`./scripts/run-bt.sh` 已通过管道空行绕开
6. **WtBtSnooper 默认 `host=127.0.0.1`** —— 容器内默认只监听 loopback,宿主访问不到,需改 `host="0.0.0.0"`(`launch_snooper.py` 已处理)

---

## 下一阶段:看懂主干(建议路径)

目标:为「实盘交易接入」打基础。建议按顺序读源码 + 带注释重写一遍。

### 第 1 步 · 最小策略跑通回调链
- **文件**: `wtpy/demos/Strategies/DualThrust.py` + `wtpy/StrategyDefs.py`
- **目标**: 掌握 `on_init` / `on_bar` / `on_calculate` / `on_tick` 等生命周期
- **产出**: 能独立写一个最简策略,跑通回测

### 第 2 步 · Python ↔ C++ 桥接理解
- **文件**: `wtpy/wrapper/WtBtWrapper.py` + `wtpy/WtBtEngine.py`
- **目标**: 看懂 ctypes 怎么调 C++ 的 .so,回调怎么从 C++ 反向调回 Python
- **产出**: 画出"策略调用 → Python 桥 → C++ 引擎 → 回测结果"的完整调用链图

### 第 3 步 · 策略上下文 API 全貌
- **文件**: `wtpy/CtaContext.py`(`stk_context` 对应股票回测上下文)
- **目标**: 掌握 context 提供的所有查询 / 下单 / 持仓管理 API
- **产出**: 整理一份 CtaContext API 手册(自己的笔记)

### 第 4 步 · 实盘交易桥 / CTP 接入
- **文件**: `wtpy/wrapper/WtWrapper.py`、`wtpy/wrapper/ContractLoader.py`、`demos/ctp_loader/`
- **目标**: 理解实盘引擎和 CTP 柜台怎么接
- **产出**: 用 CTP SimNow(仿真账户)跑通一次真实行情订阅

### 第 5 步 · 行情落地服务 datakit
- **文件**: `wtpy/WtDtEngine.py`、`demos/datakit_stk/`、`demos/datakit_fut/`
- **目标**: 搭建可持续运行的行情采集服务
- **产出**: 能独立部署一个 datakit 进程,持续收集股票 / 期货行情入库

### 第 6 步 · 整合:自己的策略 + 实盘回路
- **目标**: 把自研策略从回测 → paper trading → simnow 仿真 → (可选)真实柜台
- **里程碑**: 一个闭环:策略信号 → 风控 → 下单 → 成交 → 盯盘

---

## 记录约定

- 每次出现阻塞或做出非显然决策时,在本文件顶部追加一条日志
- 填坑记录要写**为什么**,不只是**怎么做** —— 未来回顾时才能判断是否还适用
- 每阶段完成后记录关键度量(如回测耗时、触发次数、盈亏统计)
- 外部资源(issue、文档、讨论)链接记录在对应日志里
