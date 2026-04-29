---
层级: L2
前置阅读:
  - docs/05-数据/数据流与文件格式(dsb-dmb-csv).md
本篇目标: 介绍 `wtpy/wtpy/apps/datahelper/` 子模块，列出支持的数据源（tushare / rqdata / tqsdk / akshare / baostock），以及与 WtDtHelper 的协作关系。
读完后应能回答:
  - 我只有 tushare 的历史 csv，怎么灌进 wtpy 回测？
  - DHFactory 是什么工厂？
  - akshare 是免费的吗？适合做股票还是期货？
  - 这和 `wrapper/WtDtHelper` 是什么关系？
关键源码:
  - wtpy/wtpy/apps/datahelper/__init__.py
  - wtpy/wtpy/apps/datahelper/DHDefs.py
  - wtpy/wtpy/apps/datahelper/DHFactory.py
  - wtpy/wtpy/apps/datahelper/DHTushare.py
  - wtpy/wtpy/apps/datahelper/DHRqData.py
  - wtpy/wtpy/apps/datahelper/DHTqSdk.py
  - wtpy/wtpy/apps/datahelper/DHBaostock.py
  - wtpy/demos/test_datahelper/
术语表反链:
  - tushare / rqdata / tqsdk / akshare
  - dsb / dmb
---

## datahelper 定位

`datahelper` 是 **"拉数据 + 转格式"** 的 Python 门面：
- 从第三方数据 SDK 拉 K 线 / Tick；
- 调用底层 `WtDtHelper` 把它写成 WonderTrader 内部格式（dsb/csv）；
- 回测 / 实盘从此之后只看 `storage/`。

## 数据源清单

| 模块 | 数据源 | 擅长 | 费用 |
|---|---|---|---|
| `DHTushare.py` | [tushare](https://tushare.pro) | A 股历史、财务、指数 | 积分制，免费额度够做研究 |
| `DHRqData.py` | [米筐 RQData](https://www.ricequant.com) | A 股 / 期货 / 期权，高质量 | 收费 |
| `DHTqSdk.py` | [天勤 TqSdk](https://www.shinnytech.com) | 期货实时/历史，商品期权 | 模拟免费，实盘订阅 |
| `DHBaostock.py` | [Baostock](http://baostock.com/) | A 股历史（日线、分钟线） | 免费，质量一般 |
| `DHDefs.py` | 基类接口 + `DBHelper` | 存储到本地 sqlite/文件 | — |
| `DHFactory.py` | 工厂，按名字实例化 | | — |
| `db/` | sqlite DB schema | 用于拉下来的中间落地 | — |

**akshare 不在 datahelper 内置**，但在本仓库 `scripts/fetch_akshare.py`（commit `65cdfbd`）用到；Sina/新浪财经 / akshare 免费稳，适合验证性实验。

## 基础用法（DHFactory）

```python
from wtpy.apps.datahelper import DHFactory

helper = DHFactory.createHelper('tushare', token='你的 token')
helper.dmpCodeListToFile("codelist.json", hasStock=True, hasIndex=False)
helper.dmpBarsToFile("SH600000", "./data/", period="day", start_date="20200101", end_date="20221231")
# 然后用底层 WtDtHelper 把拉到的文件转成 dsb/csv
```

具体方法名见 `DHDefs.BaseDataHelper` 的抽象接口：`dmpBarsToFile` / `dmpAdjFactorsToFile` / `dmpCodeListToFile` 等。各 provider 子类（`DHTushare` 等）各自实现。

## 与 `WtDtHelper` 的分工

```
 datahelper        → 从 SDK 拉到"中间格式"（json/csv）
 ↓
 wrapper/WtDtHelper → 把中间格式转成 wtpy 内部 dsb/dmb
 ↓
 storage/         → 回测/实盘直接用
```

所以"**datahelper 只管拉**、**WtDtHelper 只管格式转换**"。两者都是 Python 层面的工具类。

## 本仓库的实战轨迹

- commit `65cdfbd`：`scripts/fetch_akshare.py` 用 akshare + 新浪财经接口抓 2026-03-23~04-21 的 SH510300 5 分钟线，用于 `bt/cta_stk_bt_recent/` 验证 DualThrust。这里没走 datahelper（因为 akshare 无内置 helper），属于自定义实现的范式。

## 常见坑

- **tushare 积分不足**：免费用户的分钟线 API 会 403；需付费订阅或换 Baostock。
- **时区**：RqData 返回的时间有时带 `+08:00`；落盘前要转换成 `yyyymmddHHMM` 的纯整数。
- **列名差异**：不同数据源列名不一；要在 helper 里标准化成 wtpy 期望的 `open/high/low/close/vol/money/diff`。
- **复权因子**：A 股回测必须前/后复权，`dmpAdjFactorsToFile` 产出的是连续日的 factor 序列，回测配合 `adjfactors.json` 使用。

## 进一步阅读

- 数据格式：[05-数据/数据流与文件格式](../05-数据/数据流与文件格式(dsb-dmb-csv).md)
- 查询落地数据：[05-数据/WtDtServo 数据查询](../05-数据/WtDtServo数据查询.md)
- 回测配置：[06-回测/回测流程与配置](../06-回测/回测流程与配置(configbt.yaml).md)
