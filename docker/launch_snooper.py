"""Launch WtBtSnooper pre-configured with the cta_stk_bt workspace.

Runs inside the wtpy docker container. Serves on 0.0.0.0:8081 so the
host macOS browser can reach it via the port mapping in docker-compose.yml.

Open http://127.0.0.1:8081/backtest/backtest.html in macOS Chrome/Safari.
"""
import gzip
import os

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from wtpy.monitor import WtBtSnooper
from wtpy.monitor.WtBtSnooper import WtBtSnooper as _WtBtSnooperCls
from wtpy import WtDtServo


# ---------------------------------------------------------------------------
# Workaround: WtDtServoApi.get_bars() (native C++) segfaults the whole
# Python process in this macOS Docker (linux/amd64) setup when resolving
# ETF contracts — similar shape to upstream issue #164 (memory overflow on
# non-dominant contracts). Python try/except cannot catch a native
# segfault, so we bypass WtDtServo entirely and build the K-line response
# directly from the CSV files in demos/storage/csv/<CODE>_<PERIOD>.csv.
#
# Frontend bartime encoding (from backtest.*.js):
#   Math.floor(bartime/1e4) → YYYYMMDD
#   bartime % 1e4           → HHMM
# So bartime is packed as: YYYYMMDD * 10000 + HHMM
# ---------------------------------------------------------------------------
CSV_STORAGE_DIRS = [
    "/workspace/wtpy/demos/storage/csv",  # upstream demo data
    "/workspace/bt/storage/csv",          # our fetched data
]


def _csv_load_bars(code: str, period: str, stime: int, etime: int) -> list:
    """Load bars from CSV, return list of dicts matching the frontend schema."""
    import csv as _csv
    import os as _os

    fname = None
    for base in CSV_STORAGE_DIRS:
        candidate = _os.path.join(base, f"{code}_{period}.csv")
        if _os.path.exists(candidate):
            fname = candidate
            break
    if fname is None:
        searched = [_os.path.join(b, f"{code}_{period}.csv") for b in CSV_STORAGE_DIRS]
        print(f"[snooper] CSV not found in any of: {searched}")
        return []

    bars: list = []
    with open(fname, newline="") as f:
        reader = _csv.reader(f)
        header = next(reader, None)  # skip <Date>,<Time>,<Open>,...
        for row in reader:
            if len(row) < 7:
                continue
            date_str = row[0].strip()  # "2019/1/2"
            time_str = row[1].strip()  # "09:35:00"
            try:
                y, m, d = date_str.split("/")
                hh, mm, _ = time_str.split(":")
                bartime = int(y) * 10**8 + int(m) * 10**6 + int(d) * 10**4 + int(hh) * 100 + int(mm)
                if bartime < stime or (etime and bartime > etime):
                    continue
                bars.append({
                    "bartime": bartime,
                    "open": float(row[2]),
                    "high": float(row[3]),
                    "low": float(row[4]),
                    "close": float(row[5]),
                    "volume": float(row[6]),
                    "turnover": 0.0,
                })
            except (ValueError, IndexError):
                continue
    print(f"[snooper] CSV load {code} {period}: {len(bars)} bars in [{stime},{etime}]")
    return bars


def _csv_get_bt_kline(self, path: str, straid: str):
    """Drop-in replacement for WtBtSnooper.get_bt_kline that skips native C++."""
    import json as _json
    import os as _os

    btenv_file = _os.path.join(path, f"{straid}/btenv.json")
    if not _os.path.exists(btenv_file):
        return None, None, None, None

    with open(btenv_file) as f:
        btenv = _json.load(f)

    code = btenv.get("code", "")
    period = btenv.get("period", "")
    stime = int(btenv.get("stime", 0))
    etime = int(btenv.get("etime", 0))

    # Allow btchart.json to override code/period (same as upstream logic)
    btchart_file = _os.path.join(path, f"{straid}/btchart.json")
    index = None
    if _os.path.exists(btchart_file):
        try:
            with open(btchart_file) as f:
                btchart = _json.load(f)
            if "kline" in btchart:
                code = btchart["kline"].get("code", code)
                period = btchart["kline"].get("period", period)
            if "index" in btchart:
                index = btchart["index"]
        except (ValueError, KeyError):
            pass

    # marks.csv (signal markers on the chart) — same as upstream logic
    marks = None
    marks_file = _os.path.join(path, f"{straid}/marks.csv")
    if _os.path.exists(marks_file):
        with open(marks_file) as f:
            lines = f.readlines()
        if len(lines) > 2:
            marks = []
            for line in lines[1:-1]:
                items = line.strip().split(",")
                if len(items) < 4:
                    continue
                try:
                    marks.append({
                        "bartime": int(items[0]),
                        "price": float(items[1]),
                        "icon": items[2],
                        "tag": items[3],
                    })
                except (ValueError, IndexError):
                    continue

    bars = _csv_load_bars(code, period, stime, etime)
    return code, bars, index, marks


_WtBtSnooperCls.get_bt_kline = _csv_get_bt_kline


# ---------------------------------------------------------------------------
# Inline Chinese tooltips for the 14 indicator buttons (VOL/RSI/KDJ/...).
# Injects a <script> before </body> of /backtest/backtest.html. The script
# walks the DOM (leaf elements only) and sets `title=` so hovering a button
# shows the 中文 explanation. Uses MutationObserver because HQChart renders
# these buttons asynchronously after data loads.
# ---------------------------------------------------------------------------
_TOOLTIP_JS = r"""
(function(){
  var MAP = {
    'VOL':  '成交量 — 一根K线内的成交手数。突破要放量才可信',
    'RSI':  '相对强弱指数 — 0~100。>70超买,<30超卖,50中性',
    'KDJ':  '随机指标 — K上穿D=金叉(买),下穿=死叉(卖);震荡市好用',
    'MACD': '平滑异同均线 — 最经典的趋势工具;看金叉死叉与红绿柱',
    'CCI':  '顺势指标 — >+100进多头区,<-100进空头区;适合趋势市',
    'BIAS': '乖离率 — 当前价偏离均线的百分比,越大越可能均值回归',
    'ROC':  '变动率 — 价格相对N周期前的%变化,衡量动量强弱',
    'HMA':  '赫尔均线 — 又快又平滑的加权均线,噪音小转向快',
    'LMA':  '线性加权均线 — 越近的K线权重越大,比SMA反应快',
    'VMA':  '可变均线 — 按波动率自动调周期,波动大更平滑',
    'BOLL': '布林带 — 中轨+2倍标差通道,震荡市高抛低吸,带收窄要注意突破',
    'STD':  '标准差 — 近N周期收盘价波动大小,波动率度量',
    'RST':  '相对强度/趋势反转类 — 具体定义以HQChart版本为准',
    'OBV':  '能量潮 — 累积成交量,反映资金净流入;与价背离=警惕反转'
  };
  function annotate(){
    var all = document.querySelectorAll('*');
    for (var i = 0; i < all.length; i++){
      var el = all[i];
      if (el.children.length !== 0) continue;
      var txt = (el.textContent || '').trim();
      if (!MAP.hasOwnProperty(txt)) continue;
      if (el.getAttribute('data-wt-tip') === '1') continue;
      el.setAttribute('title', txt + ' · ' + MAP[txt]);
      el.setAttribute('data-wt-tip', '1');
      el.style.cursor = 'help';
    }
  }
  annotate();
  var mo = new MutationObserver(annotate);
  mo.observe(document.body, { childList: true, subtree: true });
  // Backstop: annotate periodically for the first 10 seconds in case
  // HQChart renders after MutationObserver is set up.
  var n = 0;
  var iv = setInterval(function(){
    annotate();
    if (++n >= 20) clearInterval(iv);
  }, 500);
})();
"""

_INJECTION_BYTES = ("<script>" + _TOOLTIP_JS + "</script>").encode("utf-8")


class _TooltipInjector(BaseHTTPMiddleware):
    """Intercept /backtest/backtest.html and inject the tooltip script."""

    async def dispatch(self, request, call_next):
        response = await call_next(request)
        if not request.url.path.endswith("/backtest.html"):
            return response

        body = b""
        async for chunk in response.body_iterator:
            body += chunk

        encoding = response.headers.get("content-encoding", "")
        if "gzip" in encoding:
            try:
                body = gzip.decompress(body)
            except OSError:
                return Response(content=body, status_code=response.status_code,
                                headers=dict(response.headers))

        if b"</body>" in body:
            body = body.replace(b"</body>", _INJECTION_BYTES + b"</body>", 1)

        if "gzip" in encoding:
            body = gzip.compress(body)

        headers = dict(response.headers)
        headers["content-length"] = str(len(body))
        return Response(
            content=body,
            status_code=response.status_code,
            headers=headers,
            media_type=response.headers.get("content-type") or "text/html; charset=utf-8",
        )


_original_init_bt_apis = _WtBtSnooperCls.init_bt_apis


def _patched_init_bt_apis(self, app):
    _original_init_bt_apis(self, app)
    # Added last → outermost wrapper → sees raw response before gzip wraps.
    app.add_middleware(_TooltipInjector)


_WtBtSnooperCls.init_bt_apis = _patched_init_bt_apis

COMMON_DIR = "/workspace/wtpy/demos/common/"
# Datakit binary storage: `his/<period>/<exchange>/<code>.dsb`
# WtDtServo.get_bars() reads from here, needed by 信号分析 K-line tab.
STORAGE_DIR = "/workspace/wtpy/demos/storage/"
CANDIDATE_WORKSPACES = [
    {
        "id": "ws_cta_stk_bt",
        "name": "cta_stk_bt",
        "path": "/workspace/wtpy/demos/cta_stk_bt/outputs_bt",
    },
    {
        "id": "ws_cta_stk_bt_6m",
        "name": "cta_stk_bt_6m (近6个月 日线)",
        "path": "/workspace/bt/cta_stk_bt_6m/outputs_bt",
    },
    {
        "id": "ws_cta_stk_bt_recent",
        "name": "cta_stk_bt_recent (最近~23日 5min)",
        "path": "/workspace/bt/cta_stk_bt_recent/outputs_bt",
    },
    {
        "id": "ws_cta_fut_bt",
        "name": "cta_fut_bt",
        "path": "/workspace/wtpy/demos/cta_fut_bt/outputs_bt",
    },
    {
        "id": "ws_sel_fut_bt",
        "name": "sel_fut_bt",
        "path": "/workspace/wtpy/demos/sel_fut_bt/outputs_bt",
    },
    {
        "id": "ws_hft_fut_bt",
        "name": "hft_fut_bt",
        "path": "/workspace/wtpy/demos/hft_fut_bt/outputs_bt",
    },
]


def main() -> None:
    dt_servo = WtDtServo()
    # SSE.ETF.510300 lives in etfs.json, not contracts.json/stocks.json.
    # Without loading etfs.json, dt_servo.get_bars hangs when resolving
    # the ETF contract. Pass both files so all demo instruments work.
    dt_servo.setBasefiles(
        folder=COMMON_DIR,
        commfile=["commodities.json", "stk_comms.json"],
        contractfile=["contracts.json", "stocks.json", "etfs.json"],
    )
    dt_servo.setStorage(path=STORAGE_DIR)

    # Only register workspaces whose outputs_bt/ actually exists.
    # Registering a non-existent path crashes WtBtSnooper.get_all_strategy
    # with FileNotFoundError when the frontend clicks that workspace.
    valid = [ws for ws in CANDIDATE_WORKSPACES if os.path.isdir(ws["path"])]
    skipped = [ws["name"] for ws in CANDIDATE_WORKSPACES if ws not in valid]

    snooper = WtBtSnooper(dt_servo)
    snooper.workspaces = valid

    print(f"[snooper] Registered workspaces: {[w['name'] for w in valid]}")
    if skipped:
        print(f"[snooper] Skipped (no outputs_bt yet): {skipped}")
    print("[snooper] Starting on 0.0.0.0:8081")
    print("[snooper] Open on macOS:  http://127.0.0.1:8081/backtest/backtest.html")
    snooper.run_as_server(port=8081, host="0.0.0.0")


if __name__ == "__main__":
    main()
