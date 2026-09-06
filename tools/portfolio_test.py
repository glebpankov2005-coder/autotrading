#!/usr/bin/env python3
"""Full-window PORTFOLIO comparison for Apex — the un-flattered, whole-cycle test.

Unlike test_pairs.py (which scores each coin ALONE), this backtests whole
portfolios together, so diversification counts. It runs over the full window
(default 2022-01 -> now, INCLUDING the 2022 crash) and compares the current
BTC/ETH/SOL baseline against wider universes and more concurrent slots.

The question it answers: does adding coins raise the PORTFOLIO's Sharpe and
lower its drawdown? Individual-coin results don't decide that — this does.

Research only: writes temp configs in /tmp, never touches config_dryrun.json
or the live bot.

Run on the VPS (data already downloaded there):
    cd /opt/apex-trading-bot
    .venv/bin/python tools/portfolio_test.py            # full window 2022-01-
    .venv/bin/python tools/portfolio_test.py 20240101-  # custom window
"""
import glob
import json
import os
import subprocess
import sys
import tempfile
import zipfile

BASE_CONFIG = "user_data/config_research.json"
FREQTRADE = ".venv/bin/freqtrade"
TIMERANGE = sys.argv[1] if len(sys.argv) > 1 else "20220101-"

CORE = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
CANDIDATES = ["AVAX/USDT", "LINK/USDT", "INJ/USDT", "SUI/USDT",
              "APT/USDT", "NEAR/USDT", "DOGE/USDT", "ADA/USDT"]
ALL22 = json.load(open(BASE_CONFIG))["exchange"]["pair_whitelist"]

# (label, pairlist, max_open_trades)
PORTFOLIOS = [
    ("Baseline core (3 slots)",        CORE,               3),
    ("Core + 8 candidates (3 slots)",  CORE + CANDIDATES,  3),
    ("Core + 8 candidates (6 slots)",  CORE + CANDIDATES,  6),
    ("Full 22 universe (6 slots)",     ALL22,              6),
    ("Full 22 universe (10 slots)",    ALL22,             10),
]

base = json.load(open(BASE_CONFIG))
results = []

for label, pairs, mot in PORTFOLIOS:
    cfg = dict(base)
    cfg["exchange"] = dict(base["exchange"])
    cfg["exchange"]["pair_whitelist"] = pairs
    cfg["max_open_trades"] = mot
    tf = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
    json.dump(cfg, tf)
    tf.close()

    before = set(glob.glob("user_data/backtest_results/*.zip"))
    p = subprocess.run(
        [FREQTRADE, "backtesting", "--config", tf.name,
         "--timerange", TIMERANGE, "--timeframe", "1h", "--cache", "none"],
        capture_output=True, text=True, timeout=7200,
    )
    os.unlink(tf.name)
    new = set(glob.glob("user_data/backtest_results/*.zip")) - before
    if not new:
        print(f"[FAIL] {label}: no result")
        tail = "\n".join((p.stdout + p.stderr).splitlines()[-3:])
        print(tail)
        continue
    z = max(new, key=os.path.getmtime)
    zf = zipfile.ZipFile(z)
    meta = [x for x in zf.namelist() if x.endswith(".json") and "_config" not in x][0]
    st = json.loads(zf.read(meta))["strategy"]["Apex"]
    row = {
        "label": label,
        "ret": round(st["profit_total"] * 100, 1),
        "cagr": round((st.get("cagr") or 0) * 100, 1),
        "sharpe": round(st.get("sharpe") or 0, 2),
        "sortino": round(st.get("sortino") or 0, 2),
        "dd": round((st.get("max_drawdown_account") or 0) * 100, 1),
        "pf": round(st.get("profit_factor") or 0, 2),
        "tr": st["total_trades"],
    }
    results.append(row)
    print(f"[ok] {label:32s} ret={row['ret']:>7}%  Sharpe={row['sharpe']:>5}  "
          f"DD={row['dd']:>5}%  trades={row['tr']}", flush=True)

print(f"\n==================== PORTFOLIO COMPARISON  (window {TIMERANGE}) ====================")
print(f"{'PORTFOLIO':34s} {'RET%':>8} {'CAGR%':>7} {'SHARPE':>7} {'SORTINO':>8} {'MAXDD%':>7} {'PF':>5} {'TRADES':>7}")
for r in results:
    print(f"{r['label']:34s} {r['ret']:>8} {r['cagr']:>7} {r['sharpe']:>7} "
          f"{r['sortino']:>8} {r['dd']:>7} {r['pf']:>5} {r['tr']:>7}")

if results:
    b = results[0]
    print("\n---- vs baseline ----")
    for r in results[1:]:
        dsharpe = round(r["sharpe"] - b["sharpe"], 2)
        ddd = round(r["dd"] - b["dd"], 1)
        verdict = "BETTER" if (r["sharpe"] > b["sharpe"] and r["dd"] <= b["dd"] + 3) else \
                  "worse" if r["sharpe"] < b["sharpe"] else "mixed"
        print(f"  {r['label']:34s} dSharpe={dsharpe:+.2f}  dMaxDD={ddd:+.1f}%  -> {verdict}")
print("\nDecision rule: adding coins is worth it only if it RAISES Sharpe without")
print("materially raising max drawdown. If baseline wins, 3 coins is the ceiling.")
