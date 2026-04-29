## ADDED Requirements

### Requirement: 文档根目录与导航入口

系统 SHALL 在仓库根创建 `docs/` 目录，并在其中提供唯一的阅读入口文档 `docs/README.md`，作为 AI 和人类读者进入 wtpy 阅读体系的起点。`docs/README.md` MUST 包含：目录树说明、渐进式披露的四层级定义（L0/L1/L2/L3）、文档元信息模板、术语表维护规则、阅读顺序建议、股票优先 vs 期货精简的范围声明。

#### Scenario: AI 冷启动读入仓库
- **WHEN** 新的 AI 会话只被告知"请继续读 wtpy 工程"
- **THEN** 它 MUST 能通过 `docs/README.md` 在 5 分钟内确定：当前已经读到哪一层、下一步应该打开哪份文档、需要查哪个术语去 `docs/00-基础/术语表.md`

#### Scenario: 人工读者第一次打开 docs
- **WHEN** 用户直接访问 `docs/` 目录
- **THEN** `docs/README.md` MUST 给出清晰的目录树与一句话章节简介，使读者不需要随机点开文件就能判断从哪里开始

### Requirement: 渐进式披露的四层分级

所有 `docs/` 下的阅读产出文档 MUST 被归入以下四个层级之一，并在文档头部元信息中声明：

- **L0 概览**：回答"这是什么 / 为什么存在"，不涉及 API 与源码细节。
- **L1 概念**：回答"由哪些核心概念构成 / 它们之间的关系"，可以画架构图。
- **L2 模块**：回答"某一个具体模块（文件或类）是做什么的 / 主要公开接口与职责"，允许引用源码路径与关键类名，但不逐行注释。
- **L3 源码级**：对某份 demo 或关键函数进行逐段/逐函数的中文解读，允许贴代码片段并加注释。

低层级文档 MUST NOT 假设读者已经读过高层级文档；高层级文档 MAY 在"前置阅读"中引用更低层级文档作为基础。

#### Scenario: 文档按层级分目录存放
- **WHEN** 产出一篇 L2 模块级文档（例如 `WtBtEngine-回测引擎.md`）
- **THEN** 它 MUST 放在 `docs/03-引擎/` 或其他模块目录下，且元信息 `层级` 字段标注为 `L2`

#### Scenario: L3 源码级文档只出现在精读目录
- **WHEN** 产出一篇对 `demos/cta_stk_bt/runBT.py` 的逐段解读
- **THEN** 它 MUST 位于 `docs/08-股票示例精读/` 下，并在元信息中声明 `层级: L3`，并列出前置的 L1/L2 文档

### Requirement: 每篇文档必备的元信息头

每份 `docs/**/*.md`（`README.md`、术语表、FAQ 除外）MUST 在正文之前提供如下 YAML 或等价结构化元信息：

- `层级`（L0/L1/L2/L3）
- `前置阅读`（零到多条其他 docs 路径）
- `本篇目标`（一句话）
- `读完后应能回答`（至少 2 条具体问题）
- `关键源码`（至少 1 条 `wtpy/...path:Lxx-Lyy` 形式的源码定位，L0 除外可为空）
- `术语表反链`（本篇引入或高频使用的术语名，逗号或列表分隔）

#### Scenario: 新建文档缺失元信息
- **WHEN** 新建的 md 文件没有完整的 6 个元信息字段
- **THEN** 该文档被视为**未完成**，不得在 `docs/README.md` 的目录里被标为"已完成"

#### Scenario: 源码引用稳定性
- **WHEN** L2/L3 文档引用源码行号
- **THEN** 文档顶部或底部 MUST 声明对应的 wtpy 版本号或 git commit hash，避免上游更新后行号漂移无法追踪

### Requirement: 术语表单一真理源

系统 MUST 维护唯一的中文术语表 `docs/00-基础/术语表.md`，作为全体文档的"词典"。每条术语条目 MUST 至少包含：

- 中文名 + 英文/缩写全称
- 一段面向金融小白的解释（3~10 行）
- 至少 1 个示例（场景或代码/数值例子）
- `tag`：`股票` / `期货` / `通用` 至少一个
- `首次出现`：指向第一次引入该术语的文档路径

其他文档 MUST NOT 复制粘贴术语解释；如需说明术语，MUST 通过指向术语表的链接方式引用，以保持单一维护点。

#### Scenario: 阅读过程新遇到的术语
- **WHEN** 某篇新文档出现一个未登记的术语（例如"滑点"、"Parser"）
- **THEN** 该篇文档的产出任务 MUST 在结束前把该术语追加到 `docs/00-基础/术语表.md`，并在正文里用链接引用，而不是内联解释

#### Scenario: 术语重复定义
- **WHEN** 多篇文档都需要解释同一个术语（例如 "CTA"）
- **THEN** 只有术语表中有完整解释；正文 MUST 使用 `[CTA](../00-基础/术语表.md#cta-商品交易顾问)` 这种反链方式

### Requirement: 股票优先的内容覆盖范围

系统 MUST 以"股票路线"作为默认主轴产出文档，具体覆盖范围至少包含：

- demo：`wtpy/demos/cta_stk`、`wtpy/demos/cta_stk_bt`、`wtpy/demos/datakit_stk`
- 核心模块：`wtpy/wtpy/WtBtEngine.py`、`wtpy/wtpy/WtEngine.py`、`wtpy/wtpy/WtDtEngine.py`、`wtpy/wtpy/CtaContext.py`、`wtpy/wtpy/ContractMgr.py`、`wtpy/wtpy/SessionMgr.py`、`wtpy/wtpy/StrategyDefs.py`
- 数据与分析：`wtpy/wtpy/WtDtServo.py`、`wtpy/wtpy/apps/WtBtAnalyst.py`、`wtpy/wtpy/monitor/WtBtSnooper.py`
- 股票特有规则解释：T+1、涨跌停、股票手续费/印花税、停牌、除权除息

期货相关内容 SHALL 限定在 `docs/10-期货补充/` 下，采用"差异清单 + 链接到股票文档"的方式收敛篇幅。

#### Scenario: 股票 demo 精读
- **WHEN** 用户要求"读懂股票回测 demo"
- **THEN** 他 MUST 能在 `docs/08-股票示例精读/cta_stk_bt-回测demo逐段.md` 找到逐段中文注释 + 指向 L2 引擎文档的反链

#### Scenario: 期货不被过度展开
- **WHEN** 任何产出任务涉及期货内容
- **THEN** 产出 MUST 先判断是否能以"差异对照表"或"指向股票文档并标注差异"的方式表达，仅在无法对照时才单独成篇

### Requirement: 阅读产出不得修改 wtpy 源码

本阅读计划 MUST 只对 `wtpy/` 目录做只读访问。MUST NOT 为了阅读便利去修改 `wtpy/wtpy/`、`wtpy/demos/`、`wtpy/tools/` 等任何源码文件；MUST NOT 在 `wtpy/docs/` 下新增文档（该子目录属于上游开源仓库的镜像）。所有中文阅读产出 MUST 写入仓库根目录的 `docs/` 下。

#### Scenario: 误触 wtpy 源码
- **WHEN** 某个任务需要"修复 wtpy 的某个 bug 以便读懂"
- **THEN** 该任务 MUST 被改写为"在 `docs/` 中以文字形式记录该 bug 与理解要点"，不得落到 `wtpy/` 的 Edit/Write 操作

#### Scenario: 新增文档位置校验
- **WHEN** 任何文档创建操作完成
- **THEN** 其绝对路径 MUST 以 `F:\temp\wtpy_demo\wtpy_demo\docs\` 开头（或等价的仓库根 `docs/` 路径），MUST NOT 以 `F:\temp\wtpy_demo\wtpy_demo\wtpy\docs\` 开头

### Requirement: 阅读任务的可中断恢复

阅读计划 MUST 以可独立验证的任务为粒度编排（见 `tasks.md`），使任意一次 AI 会话都能：
- 通过 `docs/README.md` + `docs/00-基础/阅读路线图.md` 快速查到"哪些任务已完成 / 下一个任务是什么"。
- 只完成 `tasks.md` 中的一个或少数几个任务后就可安全结束会话，无需全部做完。
- 下一次会话从上一份产出继续，无需重读全部 `wtpy/` 源码。

#### Scenario: 中途结束会话
- **WHEN** 本次会话只完成了"L0 总览"与"术语表初版 20 词"两个任务
- **THEN** `docs/00-基础/阅读路线图.md` MUST 更新完成标记，使下次会话能准确继续第 3 个任务

#### Scenario: 跨会话术语表增量
- **WHEN** 新会话产出新文档并发现了 5 个新术语
- **THEN** 这 5 条 MUST 被追加到既有 `docs/00-基础/术语表.md`（按字母或分类排序合并），而不是另建新术语文件
