## 1. 建立文档骨架与规范（L0 准备）

- [x] 1.1 在仓库根创建 `docs/` 及所有二级目录（`00-基础/`、`01-总览/`、`02-架构/`、`03-引擎/`、`04-策略与上下文/`、`05-数据/`、`06-回测/`、`07-实盘与监控/`、`08-股票示例精读/`、`09-工具与扩展/`、`10-期货补充/`、`99-附录/`），每个子目录放一个占位 `.gitkeep` 或极简 `README.md`
- [x] 1.2 产出 `docs/README.md`：写明"面向 AI 的阅读入口"、目录树说明、渐进披露 L0~L3 层级定义、元信息模板、术语表使用规则、股票优先声明、对应的 wtpy 版本/commit
- [x] 1.3 产出 `docs/00-基础/阅读路线图.md`：按 `tasks.md` 任务编号列出所有阅读步骤的清单视图（可复制为进度表），并附"下一步该读哪篇"的决策树
- [x] 1.4 产出 `docs/00-基础/术语表.md` 初版骨架：预置 20 个核心词条（CTA、HFT、SEL、Bar、Tick、K线、DataKit、Parser、Executer、Trader、Broker、WtEngine、WtBtEngine、WtDtEngine、Context、Strategy、回测、实盘、T+1、滑点），每条至少给出中文解释 + `tag` + 占位 `首次出现`

## 2. L0 总览：wtpy 是什么、仓库长什么样

- [x] 2.1 产出 `docs/01-总览/wtpy是什么.md`（L0）：解释 wtpy 与 WonderTrader 的关系、适用场景（CTA/HFT/SEL）、为什么要 Python+C++ 混合、与 vnpy/backtrader 的差异（小白向）
- [x] 2.2 产出 `docs/01-总览/仓库结构总览.md`（L0）：基于 `ls F:\temp\wtpy_demo\wtpy_demo\wtpy\` 与 `wtpy/README.md`，把 `wtpy/`、`wtpy/wtpy/`、`wtpy/demos/`、`wtpy/tools/` 每个目录一行话说清楚，并标注"本次重点读哪些 / 可以跳过哪些"
- [x] 2.3 在 `术语表.md` 中同步追加本章新引入的术语（至少：subtree、runtime、signal、position、pnl 等）

## 3. L1 架构：分层与 Python/C++ 边界

- [x] 3.1 产出 `docs/02-架构/整体架构与分层.md`（L1）：用 1 张 mermaid 图 + 中文解说呈现 `Parser → DataKit/Feed → Engine(CTA/HFT/SEL) → Strategy → Executer/Trader → 监控/分析` 的整体数据流；区分实盘与回测两条链路
- [x] 3.2 产出 `docs/02-架构/Python与C++的边界.md`（L1）：总结 `wtpy/wtpy/wrapper/` 下每个 `*Wrapper.py` 的职责（WtBtWrapper / WtDtWrapper / WtWrapper / WtExecApi / WtMQWrapper / WtDtHelper / WtDtServoApi / ContractLoader / TraderDumper），说明 `x64/`、`x86/`、`linux/` 下的 so/dll 是什么、如何加载、调用方向（Py→C++ / C++→Py 回调）
- [x] 3.3 同步术语表（动态库、回调、ctypes、singleton、wrapper 等）

## 4. L2 引擎核心

- [x] 4.1 产出 `docs/03-引擎/三类策略引擎概览(CTA-HFT-SEL).md`（L1）：用对照表说明三种引擎的调度粒度、典型场景、对应 Context 类名、demo 入口文件
- [x] 4.2 产出 `docs/03-引擎/WtBtEngine-回测引擎.md`（L2）：以 `wtpy/wtpy/WtBtEngine.py` 为主源码，列公开方法、回测主循环、配置文件（`configbt.yaml`、`logcfgbt.yaml`）作用
- [x] 4.3 产出 `docs/03-引擎/WtEngine-实盘引擎.md`（L2）：以 `wtpy/wtpy/WtEngine.py` 为主源码，列公开方法、实盘配置（`config.yaml`、`executers.yaml`、`tdtraders.yaml`、`tdparsers.yaml`、`filters.yaml`、`actpolicy.yaml`）的用途总览
- [x] 4.4 产出 `docs/03-引擎/WtDtEngine-数据引擎.md`（L2）：说明 `WtDtEngine.py` 的定位、与 `datakit_stk`/`datakit_fut` demo 的关系
- [x] 4.5 引擎章节全部完成后，更新术语表 + 阅读路线图进度

## 5. L2 策略与上下文（股票主轴）

- [x] 5.1 产出 `docs/04-策略与上下文/策略基类StrategyDefs.md`（L2）：从 `wtpy/wtpy/StrategyDefs.py` 出发，说明 BaseCtaStrategy / BaseHftStrategy / BaseSelStrategy 的方法钩子（on_init / on_tick / on_bar / on_session_begin / on_session_end 等）
- [x] 5.2 产出 `docs/04-策略与上下文/CtaContext-股票主轴.md`（L2）：逐个公开方法做中文速查表（stra_get_bars / stra_get_ticks / stra_set_position / stra_get_position / stra_get_fund_data / stra_get_tdate / stra_get_sessinfo / stra_get_last_exittime / stra_get_all_position 等）
- [x] 5.3 产出 `docs/04-策略与上下文/HftContext.md`（L2，轻量）：只列接口差异与典型用法
- [x] 5.4 产出 `docs/04-策略与上下文/SelContext选股上下文.md`（L2）：说明选股调度模型、与 CTA 的差异

## 6. L2 数据层（股票侧优先）

- [x] 6.1 产出 `docs/05-数据/数据流与文件格式(dsb-dmb-csv).md`（L2）：梳理 WonderTrader 的数据存储格式（dsb / dmb / csv / WtBarStruct / WtTickStruct），读写入口（WtDtHelper）
- [x] 6.2 产出 `docs/05-数据/WtDtServo数据查询.md`（L2）：基于 `wtpy/wtpy/WtDtServo.py` + `demos/test_dtservo`，讲 get_bars / get_ticks / get_bars_by_date 等 API
- [x] 6.3 产出 `docs/05-数据/ContractMgr与stocks.json.md`（L2）：基于 `wtpy/wtpy/ContractMgr.py` 重点讲股票合约属性、stocks.json 格式、上市/退市日期字段（v0.9.9 新增）
- [x] 6.4 产出 `docs/05-数据/SessionMgr交易时段.md`（L2）：股票 A 股时段模板（09:30-11:30/13:00-15:00）、假日表、`sessions.json`
- [x] 6.5 术语表补充：dsb/dmb、tick、bar、K线、复权、除权除息、停牌、集合竞价、一级/二级行情

## 7. L2 回测与分析

- [x] 7.1 产出 `docs/06-回测/回测流程与配置(configbt.yaml).md`（L2）：对照 `demos/cta_stk_bt/configbt.yaml` 每个字段解释（mode、start/end、slippage、capital、replayer/env 等）
- [x] 7.2 产出 `docs/06-回测/WtBtAnalyst绩效分析.md`（L2）：基于 `wtpy/wtpy/apps/WtBtAnalyst.py`，列出 Calculate 产出字段（sharpe/sortino/calmar/max_falldown/win_rate 等），和 `bt/.../Strategy[*]_PnLAnalyzing_*.xlsx` 对照
- [x] 7.3 产出 `docs/06-回测/WtBtSnooper可视化.md`（L2）：基于 `wtpy/wtpy/monitor/WtBtSnooper.py` + 仓库已有的 `docker/launch_snooper.py` 经验（见 commit a6aca5c），讲 Snooper 的用途、HQChart 绘图、summary.json 来源

## 8. L2 实盘与监控

- [x] 8.1 产出 `docs/07-实盘与监控/实盘运行与配置.md`（L2）：对照 `demos/cta_stk/` 的 `run.py` + 6 个 yaml 说明实盘上下文
- [x] 8.2 产出 `docs/07-实盘与监控/monitor监控服务.md`（L2）：基于 `wtpy/wtpy/monitor/`（DataMgr/EventReceiver/PushSvr/WatchDog/WtMonSvr/WtBtMon/WtBtSnooper）讲整体监控架构

## 9. L3 股票示例精读（重点）

- [x] 9.1 产出 `docs/08-股票示例精读/cta_stk_bt-回测demo逐段.md`（L3）：逐段注解 `demos/cta_stk_bt/runBT.py` + `configbt.yaml`，把"从 engine 初始化 → 载入合约 → 注册策略 → run → generate report"的主循环讲透；反链到第 4、5、6、7 章
- [x] 9.2 产出 `docs/08-股票示例精读/cta_stk-实盘demo逐段.md`（L3）：逐段注解 `demos/cta_stk/run.py`，解释 parser/trader/executer 实盘接入
- [x] 9.3 产出 `docs/08-股票示例精读/datakit_stk-数据落地demo.md`（L3）：基于 `demos/datakit_stk/`，讲数据如何被采集、落盘、供回测复用

## 10. L2 工具与扩展

- [x] 10.1 产出 `docs/09-工具与扩展/CtaOptimizer参数优化.md`（L2）：`wtpy/wtpy/apps/WtCtaOptimizer.py` + `WtCtaGAOptimizer.py` + `demos/cta_optimizer/`
- [x] 10.2 产出 `docs/09-工具与扩展/WtHotPicker主力换月.md`（L2，期货向，但作为通用工具纳入）：说明主力合约规则与使用场景
- [x] 10.3 产出 `docs/09-工具与扩展/datahelper数据转换.md`（L2）：`wtpy/wtpy/apps/datahelper/` 子模块，列出支持的数据源（tushare/rqdata/tqsdk/akshare）

## 11. 期货补充（精简）

- [x] 11.1 产出 `docs/10-期货补充/与股票的差异清单.md`（L1）：对照表形式列出期货 vs 股票在"交易制度（T+0/T+1）、保证金/杠杆、手续费模型、换月、涨跌停、交易时段、数据接入（CTP vs XTP）"等维度的差异；每一条指向更详细的股票侧文档

## 12. 附录与收尾

- [x] 12.1 产出 `docs/99-附录/参考链接.md`：汇总 wtpy / WonderTrader 官方文档、仓库内已有的 `wtpy/docs/JOURNAL.md`、`wtpy/docs/INDICATORS.md`、`docker/`、`bt/` 下的实战 journal 链接
- [x] 12.2 产出 `docs/99-附录/常见问题FAQ.md`：在阅读过程中积累的踩坑点（环境、动态库、路径、T+1 行为等）
- [x] 12.3 术语表最终版校对：统一排序、补齐 `首次出现` 反链、核心词与边缘词分区、每条 `tag` 齐全
- [x] 12.4 在 `docs/README.md` + `docs/00-基础/阅读路线图.md` 标记所有章节为 ✅ 完成；核对"每篇文档是否都带 6 字段元信息头"

## 13. 验证（本变更的整体验收）

- [x] 13.1 校验没有一处文件写入发生在 `wtpy/`、`wtpy/docs/`、`wtpy/wtpy/`、`wtpy/demos/` 等 wtpy 上游镜像目录
- [x] 13.2 校验 `docs/` 下所有 md（除 README/术语表/FAQ 外）都具备"层级 / 前置阅读 / 本篇目标 / 读完后应能回答 / 关键源码 / 术语表反链" 6 字段元信息
- [x] 13.3 抽查一份 L3 文档：读者只看该文档 + 其声明的前置阅读链，是否可理解；否则回头补前置
- [x] 13.4 抽查术语表：核心 20 词是否都被至少一篇正文反链引用；冗余/未使用词条合并或删除
