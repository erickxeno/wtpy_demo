# 常见问题 FAQ

本篇收录阅读与实战过程中遇到的踩坑点，供下次 AI 会话快速定位。按"环境 / 数据 / 回测 / 实盘 / Snooper"分类。

## 环境

### Q: `ImportError: cannot load library WtBtPorter.dll`
A: 检查 `wtpy/wtpy/wrapper/` 下对应平台目录是否存在（Windows 是 `x64/WtBtPorter.dll`；Linux 是 `linux/libWtBtPorter.so`）。32 位 Python 会去 `x86/` 找。若在 Docker 里用 Linux 版需要 `libgcc`、`libstdc++` 的 glibc 兼容版本。

### Q: Docker 里缺少 Python 依赖
A: 见 commit `a6aca5c` / `docker/requirements.txt`：补 `itsdangerous`、`python-multipart`（FastAPI 上传/登录依赖）、`akshare`（数据抓取）、`pytz`（时区）。

### Q: 单例导致 Jupyter 里重跑 Engine 无效
A: `WtBtEngine`/`WtEngine`/`WtDtEngine` 都 `@singleton`；在 Jupyter 里第二次构造只会返回第一次的实例。必须 **重启内核**。

## 数据

### Q: csv 数据目录下有文件，为啥策略 `on_bar` 不触发？
A: 可能原因：
1. 文件命名不符 `{stdCode}_{period}.csv`（如 `SH510300_m5.csv` 应为 `SSE.ETF.510300_m5.csv`）；
2. 时间戳不在 `configbt.yaml.replayer.stime/etime` 范围内；
3. 该合约未在 `stocks.json` 注册；
4. 时段模板没覆盖该时间（如 9:15–9:25 的集合竞价被过滤）。

### Q: WtDtServo 取 ETF 数据时 Python 进程 segfault
A: 上游 wtpy issue #164 在 ETF 代码下踩到内存越界。绕法：
- 直接读 `demos/storage/csv/<code>_<period>.csv`，自拼 Bar（本仓库 `docker/launch_snooper.py` 即如此）；
- 或用 `wrapper/WtDtHelper` 直接读 dsb。

### Q: csv vs dsb 怎么选？
A: 初期用 csv（易检查）；量大后 csv 读速太慢，用 `WtDtHelper` 转 dsb，`mode=wtp`。

### Q: 历史股票价格跳变（除权除息）
A: 配 `adjfactors.json`；在策略里 code 后面加 `-`（前复权）或 `+`（后复权）。`demos/Strategies/DualThrust.py` 的 `isForStk=True` 分支里有示范。

## 回测

### Q: 跑完没产出 csv
A: `set_cta_strategy(..., persistData=True)` 默认 True；若被改 False 不会落盘。另外 `outputs_bt/` 目录要有写权限。

### Q: `summary.json` 缺失导致 Snooper 500
A: 回测不会默认生成 `summary.json`；需要跑 `WtBtAnalyst.Calculate` 或本仓库 `docker/gen_summary.py` 后处理产出（10 个字段齐全）。

### Q: DualThrust 在 1 个月的数据上没信号
A: 默认 `days=30` 要 30 个交易日做预热；若回测窗口短于 30 天，整段期间 `on_calculate` 都拿不到完整数组。本仓库 `bt/cta_stk_bt_recent/` 把 `days` 调小做验证。

### Q: 回测速度慢
A: 先 `mode=csv` → 确认正确，再转 dsb `mode=wtp`；另外可并发起多进程跑 Optimizer 级别的枚举。

### Q: 回测改参数没生效
A: `commitBTConfig` 只生效一次。必须进程重启或换实例。

## 实盘

### Q: `run(True)` 之后 Python 马上退出
A: 后面忘了 `while True: time.sleep(1)` 保活；C++ 在后台线程跑，主线程退了整个进程都退。

### Q: Parser 连上了但策略收不到 Tick
A:
1. `stra_sub_ticks(code)` 没在 `on_init` 调；
2. Parser 的 `filter` 白名单没包含该合约；
3. DataKit + ParserShm 模式下 `exchange.membin` 路径错。

### Q: 下单"看不见"
A:
1. `env.riskmon.risk_scale` 过小（如 0 / 0.01）；
2. Executer 的 `policy.default.offset` 太大导致跨涨跌停挂不上；
3. Trader 通道未登录（看 `on_channel_lost`）。

## Snooper

### Q: 打开 K 线页崩溃
A: 触发 wtpy issue #164。绕开 WtDtServo，csv 直读（见 `docker/launch_snooper.py` v3）。

### Q: HQChart 的指标按钮英文看不懂
A: `docker/launch_snooper.py` 的 FastAPI 中间件 `_TooltipInjector` 在 HTML 末尾注入 `<script>` + `MutationObserver`，按 id 给 `title=` 中文翻译。非侵入。

### Q: "绩效概览"几个数字都是 NaN
A: `summary.json` 字段不匹配前端期望（`sharpe_ratio` 而非 `sharpe`）；按 `docker/gen_summary.py` 的 10 字段补齐。

## 术语 / 规范

### Q: stdCode 怎么拼？
A: 见 [05-数据/ContractMgr 与 stocks.json](../05-数据/ContractMgr与stocks.json.md) "标准代码规范"一节。

### Q: 为什么文档叫"渐进式披露"？
A: 每篇文档头部声明前置阅读 + 本篇目标 + 应能回答的问题，读者/AI 按层级（L0→L3）逐渐展开，避免一口气塞全部细节。

### Q: 本仓库的 docs 和 wtpy/docs 如何区分？
A:
- `wtpy/docs/`：上游作者维护的 `INDICATORS.md`、`JOURNAL.md`，**不改动**。
- `docs/`（你正在读）：我们的中文阅读笔记，新建于仓库根。

## 如何提交新 FAQ

在阅读/实战中遇到坑 → 在本文末追加 `Q/A` 段落（按已有分类放）→ 必要时在术语表登记相关生词。**不要**另建 FAQ 文件。
