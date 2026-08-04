"""Batch-backtest every root strategy from the source repo on BTC+ETH over 2 years.

For each .py file: isolate it, ask freqtrade for its strategy class, backtest it
(1h timeframe override, 2017-11-01..2019-11-01, BTC/USDT + ETH/USDT), and record
metrics or the failure reason. Results stream to tourney_results.jsonl.
"""
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import time
import zipfile

SRC = "/tmp/claude-0/-home-user-autotrading/091796be-979d-5f7b-bf9b-03e9d6d4d91f/scratchpad/src_strats"
WORK = "/tmp/tourney_work"
RESULTS_DIR = "user_data/backtest_results"
OUT = "tourney_results.jsonl"
PY = ".venv/bin/python"
RUNNER = "run_backtest_2y.py"
CONFIG = "user_data/config_2y.json"
DATADIR = "user_data/data_2y/binance"
TIMERANGE = "20171101-20191101"
LIST_TIMEOUT = 90
BT_TIMEOUT = 300

os.makedirs(WORK, exist_ok=True)


def sanitize(fn):
    base = os.path.splitext(os.path.basename(fn))[0]
    return re.sub(r"[^A-Za-z0-9_]", "_", base)


def detect_classes(strat_dir):
    """Return (classes, err). Uses freqtrade list-strategies (authoritative)."""
    try:
        p = subprocess.run(
            [PY, RUNNER, "list-strategies", "--strategy-path", strat_dir, "-1",
             "--config", CONFIG],
            capture_output=True, text=True, timeout=LIST_TIMEOUT)
    except subprocess.TimeoutExpired:
        return [], "list-strategies timeout"
    names = []
    for line in p.stdout.splitlines():
        s = line.strip()
        if re.fullmatch(r"[A-Za-z_]\w*", s) and s not in ("LOAD", "FAILED"):
            names.append(s)
    # capture a short error hint from stderr if nothing found
    err = ""
    if not names:
        tail = [l for l in p.stderr.splitlines()
                if any(k in l for k in ("Error", "error", "Exception", "No module",
                                        "cannot import", "Traceback"))]
        err = tail[-1][:300] if tail else "no IStrategy class detected"
    return names, err


def newest_zip(before):
    zips = set(glob.glob(f"{RESULTS_DIR}/*.zip")) - before
    if not zips:
        return None
    return max(zips, key=os.path.getmtime)


def parse_zip(zpath, cls):
    z = zipfile.ZipFile(zpath)
    main = [n for n in z.namelist() if n.endswith(".json")
            and "_config" not in n and not n.endswith(f"_{cls}.json")]
    d = json.loads(z.read(main[0]))
    st = d["strategy"][cls]
    per = {r["key"]: r for r in st.get("results_per_pair", [])}
    def pct(k):
        r = per.get(k)
        return round(r["profit_total_pct"], 2) if r else None
    def tr(k):
        r = per.get(k)
        return r["trades"] if r else None
    return {
        "trades": st.get("total_trades"),
        "profit_pct": round(st.get("profit_total", 0) * 100, 2),
        "cagr": round((st.get("cagr") or 0) * 100, 2),
        "sharpe": round(st.get("sharpe") or 0, 3),
        "sortino": round(st.get("sortino") or 0, 3),
        "calmar": round(st.get("calmar") or 0, 3),
        "profit_factor": round(st.get("profit_factor") or 0, 3),
        "max_dd_pct": round((st.get("max_drawdown_account") or 0) * 100, 2),
        "winrate": round((st.get("winrate") or 0) * 100, 2),
        "expectancy": round(st.get("expectancy") or 0, 4),
        "btc_pct": pct("BTC/USDT"), "btc_trades": tr("BTC/USDT"),
        "eth_pct": pct("ETH/USDT"), "eth_trades": tr("ETH/USDT"),
    }


def backtest(cls, strat_dir):
    before = set(glob.glob(f"{RESULTS_DIR}/*.zip"))
    try:
        p = subprocess.run(
            [PY, RUNNER, "backtesting", "--config", CONFIG, "--strategy", cls,
             "--strategy-path", strat_dir, "--datadir", DATADIR,
             "--timerange", TIMERANGE, "--timeframe", "1h", "--cache", "none",
             "--export", "trades"],
            capture_output=True, text=True, timeout=BT_TIMEOUT)
    except subprocess.TimeoutExpired:
        return {"status": "fail", "reason": "backtest timeout"}
    z = newest_zip(before)
    if z is None:
        # extract a concise reason
        err_lines = [l for l in p.stdout.splitlines() + p.stderr.splitlines()
                     if any(k in l for k in ("ERROR", "Error", "Exception",
                                             "No data", "No module", "OperationalException"))]
        reason = err_lines[-1].split(" - ")[-1][:300] if err_lines else "no result produced"
        return {"status": "fail", "reason": reason}
    try:
        m = parse_zip(z, cls)
    except Exception as e:
        return {"status": "fail", "reason": f"parse error: {e}"}
    m["status"] = "ok"
    return m


def main():
    files = sorted(glob.glob(f"{SRC}/*.py"))
    print(f"{len(files)} root strategy files")
    open(OUT, "w").close()
    for i, f in enumerate(files, 1):
        name = sanitize(f)
        d = os.path.join(WORK, name)
        shutil.rmtree(d, ignore_errors=True)
        os.makedirs(d)
        shutil.copy(f, os.path.join(d, name + ".py"))
        t0 = time.time()
        classes, derr = detect_classes(d)
        rec = {"file": os.path.basename(f), "classes": classes}
        if not classes:
            rec.update({"status": "fail", "reason": derr or "no strategy class"})
        else:
            cls = classes[0]
            rec["class"] = cls
            rec.update(backtest(cls, d))
        rec["secs"] = round(time.time() - t0, 1)
        with open(OUT, "a") as fh:
            fh.write(json.dumps(rec) + "\n")
        tag = rec.get("status")
        extra = (f"{rec.get('profit_pct')}% / {rec.get('trades')}tr"
                 if tag == "ok" else rec.get("reason", "")[:60])
        print(f"[{i}/{len(files)}] {os.path.basename(f)[:34]:34s} {tag:5s} {extra}  ({rec['secs']}s)",
              flush=True)
    print("DONE")


if __name__ == "__main__":
    main()
