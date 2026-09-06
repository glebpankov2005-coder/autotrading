#!/usr/bin/env python3
"""Universe scan for Apex — backtests each candidate pair INDIVIDUALLY on real
Bybit data and prints a ranked table, so we only add coins where Apex actually
works. Research only: does NOT touch the live bot or its config.

Run on the VPS (has Bybit access):

    cd /opt/apex-trading-bot
    # 1) download candles for the whole candidate universe (multi-year)
    .venv/bin/freqtrade download-data --config user_data/config_research.json \
        --timerange 20220101- --timeframe 1h
    # 2) rank them
    .venv/bin/python tools/test_pairs.py

Add --timerange on step 1 to control history depth. Some newer coins will have
shorter history; the scan just uses whatever was downloaded and skips misses.
"""
import glob
import json
import os
import subprocess
import sys
import zipfile

CONFIG = "user_data/config_research.json"
TIMERANGE = sys.argv[1] if len(sys.argv) > 1 else "20220101-"
FREQTRADE = ".venv/bin/freqtrade"

pairs = json.load(open(CONFIG))["exchange"]["pair_whitelist"]
rows = []

for pair in pairs:
    before = set(glob.glob("user_data/backtest_results/*.zip"))
    p = subprocess.run(
        [FREQTRADE, "backtesting", "--config", CONFIG,
         "--pairs", pair, "--timerange", TIMERANGE, "--timeframe", "1h",
         "--cache", "none"],
        capture_output=True, text=True, timeout=3600,
    )
    new = set(glob.glob("user_data/backtest_results/*.zip")) - before
    if not new:
        why = "no data" if "No data" in (p.stdout + p.stderr) else "no result"
        rows.append((pair, None, None, None, None, 0, why))
        print(f"{pair:10s}  SKIP ({why})", flush=True)
        continue
    z = max(new, key=os.path.getmtime)
    zf = zipfile.ZipFile(z)
    meta = [x for x in zf.namelist() if x.endswith(".json") and "_config" not in x][0]
    st = json.loads(zf.read(meta))["strategy"]["Apex"]
    ret = round(st["profit_total"] * 100, 1)
    cagr = round((st.get("cagr") or 0) * 100, 1)
    sharpe = round(st.get("sharpe") or 0, 2)
    dd = round((st.get("max_drawdown_account") or 0) * 100, 1)
    tr = st["total_trades"]
    rows.append((pair, ret, cagr, sharpe, dd, tr, "ok"))
    print(f"{pair:10s}  ret={ret:>7}%  CAGR={cagr:>6}%  Sharpe={sharpe:>5}  DD={dd:>5}%  trades={tr}", flush=True)

# ranked summary (by Sharpe, then CAGR) — the coins worth adding
ok = [r for r in rows if r[6] == "ok"]
ok.sort(key=lambda r: (-(r[3] or -99), -(r[2] or -99)))
print("\n==================== RANKED (best first) ====================")
print(f"{'PAIR':10s} {'RET%':>8} {'CAGR%':>7} {'SHARPE':>7} {'DD%':>6} {'TRADES':>7}")
for pair, ret, cagr, sharpe, dd, tr, _ in ok:
    print(f"{pair:10s} {ret:>8} {cagr:>7} {sharpe:>7} {dd:>6} {tr:>7}")
skipped = [r[0] for r in rows if r[6] != "ok"]
if skipped:
    print("\nSkipped (no/short data on Bybit):", ", ".join(skipped))
print("\nGuideline: a coin is worth ADDING only if it's profitable with a")
print("positive Sharpe and a drawdown you'd tolerate. Negative-Sharpe or")
print("high-DD coins should stay OUT — adding them would drag the portfolio.")
