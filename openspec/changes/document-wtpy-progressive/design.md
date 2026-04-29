## Context

- `wtpy/` 是 **WonderTrader** 针对 Python3 适配的量化交易子框架，功能面广：封装 C++ 底层（`wrapper/`）、三类策略引擎（CTA/HFT/SEL）、数据引擎（DataKit）、回测引擎（WtBtEngine）、实盘引擎（WtEngine）、监控服务（`monitor/`）、回测分析（`apps/WtBtAnalyst`）、以及各类 demo（`demos/cta_stk*`、`demos/cta_fut*`、`demos/datakit_*` 等）。
- 用户背景：**金融小白 + 新手 AI 读者**，需要大量解释背景术语；同时希望文档沉淀后 AI 会话能在后续 session 中接着读。
- 已有参考：`wtpy/README.md`（模块索引）、`wtpy/docs/INDICATORS.md`、`wtpy/docs/JOURNAL.md`、以及仓库根 `docker/`、`bt/` 等已经产出的实战脚本与 journal。
- 约束：**只读分析 `wtpy/` 源码，不做代码修改**；中文输出；产出物位于仓库根 `docs/`（与 `wtpy/docs/` 分离）。

## Goals / Non-Goals

**Goals:**
- 建立一个**层级清晰、可以逐级打开**的中文文档树（L0 概览 → L1 概念 → L2 模块 → L3 源码级），让下一轮 AI/人阅读 5 分钟就能知道"下一步该读哪个文件"。
- 建立**统一文档模板**：每篇文档顶部都有 `前置阅读 / 本篇目标 / 读完后应能回答 / 关键源码定位 / 术语表反链` 这 5 个字段。
- 建立**持续生长的术语表**：每次遇到新名词先登记，保证小白读者不被缩写劝退。
- 以 **stock（股票）路线**为默认主轴：CTA 股票策略 demo（`demos/cta_stk`、`demos/cta_stk_bt`）、`datakit_stk`、`ContractMgr` 对 `stocks.json` 的处理、T+1/滑点/佣金等股票特有规则优先覆盖。
- 明确**阅读计划的执行路径**：`tasks.md` 里拆成 10+ 个可独立验证的阅读任务，每个任务都能产出 1~N 份 md，便于多轮 session 推进。

**Non-Goals:**
- 不承诺对 `wtpy/wtpy/wrapper/` 下 C++ 动态库做二进制级分析（只分析 Python 侧调用约定与接口语义）。
- 不对期货策略（`cta_fut*`、`hft_fut*`、`sel_fut_bt`）做逐行精读，只在 `docs/10-期货补充/` 里做差异化梳理。
- 不重写/搬运 `wtpy/` 官方中文 README 的全部内容；文档只做"路标 + 小白解释 + 关键源码引用 + 样例串联"。
- 不做新 feature / bug fix / 性能优化。

## Decisions

### 决策 1：docs 放仓库根目录而不是放在 `wtpy/docs/` 下
- **选择**：`F:\temp\wtpy_demo\wtpy_demo\docs\`。
- **原因**：`wtpy/` 是 git subtree 或镜像上游开源仓库，后续 `git pull upstream` 时可能冲突；把我们的中文阅读笔记放在仓库根 `docs/` 更安全，也和现有 `openspec/`、`bt/`、`docker/` 同级，语义一致。
- **替代方案**：放到 `wtpy/docs/`——否决，原因同上。

### 决策 2：按"数字前缀 + 中文名"的目录结构组织文档
目录骨架（kebab 英文保底以便命令行友好，但文档正文中文）：
```
docs/
├─ README.md                          # 给 AI 的总入口 + 阅读规则
├─ 00-基础/
│   ├─ 术语表.md                      # 核心产出 #1，持续维护
│   └─ 阅读路线图.md                  # 四层渐进披露路线 + 检查清单
├─ 01-总览/
│   ├─ wtpy是什么.md                  # L0
│   └─ 仓库结构总览.md                # L0
├─ 02-架构/
│   ├─ 整体架构与分层.md              # L1
│   └─ Python与C++的边界.md           # L1（wrapper 概念）
├─ 03-引擎/
│   ├─ 三类策略引擎概览(CTA-HFT-SEL).md  # L1
│   ├─ WtEngine-实盘引擎.md           # L2
│   ├─ WtBtEngine-回测引擎.md         # L2
│   └─ WtDtEngine-数据引擎.md         # L2
├─ 04-策略与上下文/
│   ├─ 策略基类StrategyDefs.md        # L2
│   ├─ CtaContext-股票主轴.md         # L2（股票优先）
│   ├─ HftContext.md                  # L2（轻量）
│   └─ SelContext选股上下文.md        # L2
├─ 05-数据/
│   ├─ 数据流与文件格式(dsb-dmb-csv).md  # L2
│   ├─ WtDtServo数据查询.md           # L2
│   ├─ ContractMgr与stocks.json.md    # L2（股票优先）
│   └─ SessionMgr交易时段.md          # L2
├─ 06-回测/
│   ├─ 回测流程与配置(configbt.yaml).md  # L2
│   ├─ WtBtAnalyst绩效分析.md         # L2
│   └─ WtBtSnooper可视化.md           # L2
├─ 07-实盘与监控/
│   ├─ 实盘运行与配置.md              # L2
│   └─ monitor监控服务.md             # L2
├─ 08-股票示例精读/
│   ├─ cta_stk_bt-回测demo逐段.md     # L3（本次重点）
│   ├─ cta_stk-实盘demo逐段.md        # L3
│   └─ datakit_stk-数据落地demo.md    # L3
├─ 09-工具与扩展/
│   ├─ CtaOptimizer参数优化.md        # L2
│   ├─ WtHotPicker主力换月.md         # L2
│   └─ datahelper数据转换.md          # L2
├─ 10-期货补充/
│   └─ 与股票的差异清单.md            # L1（精简）
└─ 99-附录/
    ├─ 常见问题FAQ.md
    └─ 参考链接.md
```
- **原因**：数字前缀便于文件系统按阅读顺序自然排序；中文目录名对人友好；两层层级足够容纳 40~60 份文档、不过深。
- **替代方案**：纯英文扁平结构——否决，牺牲小白可读性；flat layout——否决，规模上来之后难导航。

### 决策 3：每份文档必须带"渐进式披露元信息"头
统一模板（所有 `docs/**/*.md` 必须遵守）：
```markdown
---
层级: L0 | L1 | L2 | L3
前置阅读:
  - docs/xx/yy.md
本篇目标: 一句话说明
读完后应能回答:
  - 问题1
  - 问题2
关键源码:
  - wtpy/wtpy/xxx.py:L12-L45
术语表反链:
  - 术语A
  - 术语B
---
```
- **原因**：强制显式声明依赖关系 + 检验点 → 让渐进式披露可机读、可校验；后续 AI 读入任意一篇都能立刻定位上下文。
- **替代方案**：纯正文写——否决，依赖关系隐式，AI 容易跑偏。

### 决策 4：术语表是"单一真理源（SSoT）"
- 一处维护：`docs/00-基础/术语表.md`。
- 格式：每条术语 `### 术语名（英文/缩写）` + 中文解释 + 示例 + 首次出现章节链接。
- 阅读每篇文档时，遇到新术语先加到术语表，然后正文里只"轻引用"（挂一个反链，不重复解释）。
- **原因**：避免解释发散；小白只需在一处查字典；新 AI session 冷启动更快。

### 决策 5：股票优先、期货精简
- 精读对象：`demos/cta_stk_bt/runBT.py`、`demos/cta_stk/run.py`、`demos/datakit_stk/`、`wtpy/ContractMgr.py`、`wtpy/CtaContext.py`、`wtpy/WtBtEngine.py`、`wtpy/WtEngine.py`、`wtpy/WtDtServo.py`、`wtpy/apps/WtBtAnalyst.py`、`wtpy/monitor/WtBtSnooper.py` 等。
- 期货：只在 `docs/10-期货补充/与股票的差异清单.md` 里列对照表（T+0 vs T+1、手续费模型、换月规则、Parser/Trader 接入差异），不逐文件精读。
- **原因**：符合用户明确优先级；避免过度投入。

### 决策 6：阅读计划任务化、可中断恢复
- `tasks.md` 以"一任务 = 一批文档"为粒度，每个任务独立可验证（产出文件路径 + 校验点）。
- 任务之间尽量解耦，支持后续 AI 会话乱序/并行推进；术语表任务在每个阅读任务尾部"尾调"一次增量更新。
- **原因**：多 session 场景下保证进度可持久化。

## Risks / Trade-offs

- **[风险] 术语表膨胀失控** → 缓解：每条控制在 5~15 行；设"核心 20 词"章节置顶；同义词合并。
- **[风险] 文档和 wtpy 上游版本漂移**（wtpy v0.9.9 之后可能有更新）→ 缓解：每篇关键源码反链写到具体文件 + 行号区间，并在 README 声明阅读对应的 git commit / wtpy 版本。
- **[风险] 小白读者仍然读不懂 C++ wrapper 层** → 缓解：L2 `Python与C++的边界.md` 只讲调用约定、so/dll 加载、回调方向，不讲 C++ 实现；明确"想深入读底层，请跳到 WonderTrader C++ 仓库"。
- **[权衡] 文档数量 vs 维护成本**：40~60 份文档是上限；如果发现某主题单独成篇不够饱满，合并到上级主题；避免"一个 API 一份 md"的碎片化。
- **[权衡] 中文 vs 英文**：正文中文为主；文件名/目录名数字前缀 + 中文；标题里英文专有名词（CTA、DataKit、Parser）保留原文 + 首次解释时加括号翻译。
- **[风险] 与已有 `wtpy/docs/JOURNAL.md`、`wtpy/docs/INDICATORS.md` 重复** → 缓解：新 `docs/` 以"阅读笔记"视角组织，引用 `wtpy/docs/` 下的原始文档作为一手资料，不搬运、不替代。

## Open Questions

- 是否需要为每个术语标注"股票 / 期货 / 通用" tag？→ 倾向于是，放在术语表每条的末尾。
- 是否需要 mermaid 图？→ 倾向于在 `02-架构/` 和关键流程（回测主循环、tick→bar→策略 on_bar）里放 mermaid；其他章节以文字为主避免过度投入。
- 是否要把 `bt/`、`docker/` 下已有的实战 journal 链接进 `docs/`？→ 是，放在 `docs/99-附录/参考链接.md`。
