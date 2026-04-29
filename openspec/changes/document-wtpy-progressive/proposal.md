## Why

用户要对 `wtpy/` 目录下的 WonderTrader Python 子框架做体系化阅读与理解（重点：股票相关模块；次优先：期货），但工程体量大、概念多、术语密集，用户自评为"金融领域小白"，一开始无从下手。直接硬啃源码会陷入细节、收益低；需要一份**渐进式披露（progressive disclosure）**阅读计划——从顶层架构 → 领域概念 → 子模块 → 关键源码 → 流程串联，逐层打开，并把阅读产出以中文 Markdown 的形式沉淀到 `docs/` 目录，形成可复用的知识库，使后续 AI/人都能按同一地图继续阅读。

## What Changes

- 在仓库根目录 `docs/` 下新建一套为 AI 阅读优化的目录骨架与导航文档（`README.md` + 分层子目录）。
- 按"总览 → 概念术语 → 架构与模块映射 → 引擎核心（数据/回测/实盘）→ 策略与上下文 → 股票示例 demo 精读 → 运维/监控/工具链 → 回测分析与绩效 → 期货补充"的顺序，分章节产出中文阅读笔记。
- 产出一份**术语表 `docs/00-基础/术语表.md`**，持续收录阅读过程中遇到的金融名词、英文缩写（如 CTA/HFT/SEL/Tick/Bar/IPO/T+1/滑点/佣金等）及 WonderTrader 特有概念（如 Parser/Executer/DataKit/Snooper 等），给出中文解释、简短示例与"首次出现章节"反链。
- 在 `docs/README.md` 中声明**渐进式披露约定**：每份文档必须显式声明"前置阅读"、"本篇目标"、"读完后应能回答的问题"，并按"L0 概览 → L1 概念 → L2 模块 → L3 源码级"四个层级分目录组织。
- **阅读驱动而非修改驱动**：本次变更**不修改 `wtpy/` 源码**，只新增/组织 `docs/` 下的 Markdown 文档。
- 明确股票优先级（`demos/cta_stk`、`demos/cta_stk_bt`、`demos/datakit_stk`、`ContractMgr` 对 stocks.json 的处理、T+1 规则等）高于期货；期货部分用精简章节收尾即可。

## Capabilities

### New Capabilities
- `wtpy-reading-guide`: 面向 AI/新人的 wtpy 工程渐进式阅读导航与文档编写规范（docs 目录结构、每篇文档的必备元信息、分层约定、术语表维护规则、阅读进度追踪）。

### Modified Capabilities
（无——仓库此前没有相关 spec，此变更仅新增能力。）

## Impact

- **新增目录与文件（docs/）**：新建 `docs/README.md`、`docs/00-基础/`、`docs/01-总览/`、`docs/02-架构/`、`docs/03-引擎/`、`docs/04-策略与上下文/`、`docs/05-数据/`、`docs/06-回测/`、`docs/07-实盘与监控/`、`docs/08-股票示例精读/`、`docs/09-工具与扩展/`、`docs/10-期货补充/`、`docs/99-附录/` 等子目录骨架；后续每章输出至少 1 份入门文档 + 按需细分。
- **不影响代码**：不改动 `wtpy/wtpy/`、`wtpy/demos/`、`bt/`、`docker/` 等目录下的任何源码或配置。
- **已有文档**：保留 `wtpy/docs/INDICATORS.md`、`wtpy/docs/JOURNAL.md`；新 `docs/` 目录位于仓库根（`F:\temp\wtpy_demo\wtpy_demo\docs\`），与 `wtpy/docs/` 分离，避免污染上游子工程。
- **下游**：后续 AI 会话可通过 `docs/README.md` 作为入口，按层级继续产出/更新文档；术语表作为全局词典。
- **依赖**：无新增代码依赖；只需 Markdown。
