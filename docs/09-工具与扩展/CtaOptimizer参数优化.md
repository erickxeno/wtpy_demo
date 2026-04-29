---
层级: L2
前置阅读:
  - docs/06-回测/WtBtAnalyst绩效分析.md
本篇目标: 介绍 `wtpy/wtpy/apps/WtCtaOptimizer.py`（网格）+ `WtCtaGAOptimizer.py`（遗传算法）+ `demos/cta_optimizer/`，讲 CTA 参数优化的两种方式。
读完后应能回答:
  - Optimizer 和 Analyst 分别在什么阶段使用？
  - 网格优化 vs 遗传算法（GA），什么时候选哪个？
  - 怎么在 multiprocessing 里避免 WtBtEngine 单例问题？
  - 结果如何汇总到 csv / xlsx？
关键源码:
  - wtpy/wtpy/apps/WtCtaOptimizer.py
  - wtpy/wtpy/apps/WtCtaGAOptimizer.py
  - wtpy/demos/cta_optimizer/runOptmizer.py
  - wtpy/demos/cta_optimizer/runGAOptimizer.py
  - wtpy/demos/cta_optimizer/runSummary.py
术语表反链:
  - 遗传算法
  - 回测
---

## 两个优化器对照

| 维度 | `WtCtaOptimizer` | `WtCtaGAOptimizer` |
|---|---|---|
| 方式 | 网格枚举（笛卡尔积） | 遗传算法（选择/交叉/变异） |
| 适合参数空间 | ≤ 数百种 | 上千 / 高维 |
| 执行方式 | `multiprocessing` 并行 | GA 逻辑 + 每代并行 |
| 停止条件 | 所有组合跑完 | 达到代数 / 收敛阈值 |
| 结果汇总 | 每组合一个子目录 + 统一 csv | 每代 population 的最佳体 |
| demo | `runOptmizer.py` | `runGAOptimizer.py` |

## 网格优化工作模式

1. 声明参数网格，例如：
   ```python
   params = {
     "k1": [0.1, 0.2, 0.3],
     "k2": [0.1, 0.2, 0.3],
     "days": [10, 20, 30]
   }
   ```
   笛卡尔积 → 27 组。
2. `WtCtaOptimizer` 为每组合构造一个独立进程：
   - 各自启动 `WtBtEngine`（**子进程各一份**，绕开同进程单例约束）；
   - 各自 `run_backtest()`；
   - 各自输出 `outputs_bt/<strategyName>/` 到独立子目录。
3. `runSummary.py` 遍历各子目录，读 `summary.csv` / `Calculate` 指标，汇总成一张总表。

## 遗传算法优化

- 种群 = 多组参数。每代：按**适应度**（比如 Sharpe）选强个体 → 随机交叉 → 低概率变异 → 下一代。
- `WtCtaGAOptimizer` 的精度：
  - **无法保证找到全局最优**；
  - 但对**高维空间**（10+ 参数）比网格高效得多；
  - 注意**过拟合**：GA 会偏向历史样本上表现最好的参数，样本外可能失效。

## 多进程单例陷阱

同一 Python 进程里 `WtBtEngine` 是 `@singleton`，这让"串行多次回测"困难。Optimizer 的解决方案：**每次 `Pool.apply_async` 起一个子进程**，子进程里新建 `WtBtEngine`，跑完即退出。确保 C++ 资源也被 OS 清理。

## 结果汇总

`runSummary.py` 典型做法：
```python
for d in os.listdir("./output_optmizer/"):
    funds = pd.read_csv(f"./output_optmizer/{d}/funds.csv")
    # 计算净值、Sharpe、回撤 ...
    rows.append({"params": d, "sharpe": ..., "mdd": ...})
pd.DataFrame(rows).to_csv("summary.csv")
```

对接 `WtBtAnalyst.Calculate` 可以把每组合都补齐 Sharpe/Sortino/Calmar/胜率/最大回撤等字段，便于横向比较。

## 常见坑

- **CPU 满载但出图慢**：并行把磁盘 IO 卷爆（csv 直读更明显）；可先把 csv 转 dsb。
- **种子 / 复现**：GA 有随机性；`random.seed()` 控制种子才能复现。
- **参数区间无意义值**：`days=1` 会让 DualThrust 退化；优化前筛一次合理性。
- **过拟合**：给 GA 定一个"样本外验证"阶段，别只看回测期 Sharpe。

## 进一步阅读

- 基础绩效算法：[06-回测/WtBtAnalyst 绩效分析](../06-回测/WtBtAnalyst绩效分析.md)
- Demo：`wtpy/demos/cta_optimizer/`
