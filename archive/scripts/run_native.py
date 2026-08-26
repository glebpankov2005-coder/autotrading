import json, glob, os, subprocess, zipfile
SP = "user_data/strategies_uploaded"
WIN = "20250716-20260805"  # ~13 months, common across 5m data
# (class, timeframe, config, datadir)
JOBS = [
    ("ECRV32", "5m", "user_data/config_5m.json", "user_data/data_5m/binance"),
    ("FFTAdaptiveCycle", "5m", "user_data/config_5m.json", "user_data/data_5m/binance"),
    ("AlexBandSniperV65513", "15m", "user_data/config_15m_market.json", "user_data/data_15m/binance"),
    ("NOTankAi_19_2", "15m", "user_data/config_15m.json", "user_data/data_15m/binance"),
]
res = {}
if os.path.exists("native_results.json"):
    res = json.load(open("native_results.json"))
for cls, tf, cfg, dd in JOBS:
    if cls in res and res[cls].get("status") == "OK":
        print(f"{cls}: already done, skip"); continue
    before = set(glob.glob("user_data/backtest_results/*.zip"))
    p = subprocess.run([".venv/bin/python", "run_backtest_fut.py", "backtesting", "--config", cfg,
        "--strategy", cls, "--strategy-path", SP, "--datadir", dd, "--timerange", WIN,
        "--timeframe", tf, "--cache", "none", "--export", "trades"],
        capture_output=True, text=True, timeout=7200)
    new = set(glob.glob("user_data/backtest_results/*.zip")) - before
    if not new:
        errs = [l for l in (p.stdout + p.stderr).splitlines() if any(k in l for k in ("Error", "Exception", "No data", "price_side"))]
        res[cls] = {"status": "FAIL", "tf": tf, "reason": (errs[-1][-110:] if errs else "no result")}
    else:
        z = max(new, key=os.path.getmtime); zf = zipfile.ZipFile(z)
        m = [x for x in zf.namelist() if x.endswith(".json") and "_config" not in x and not x.endswith(f"_{cls}.json")][0]
        st = json.loads(zf.read(m))["strategy"][cls]
        res[cls] = {"status": "OK", "tf": tf, "ret": round(st["profit_total"] * 100, 1),
                    "cagr": round((st.get("cagr") or 0) * 100, 1), "sharpe": round(st.get("sharpe") or 0, 2),
                    "dd": round((st.get("max_drawdown_account") or 0) * 100, 1), "pf": round(st.get("profit_factor") or 0, 2),
                    "tr": st["total_trades"], "win": round((st.get("winrate") or 0) * 100, 1)}
    json.dump(res, open("native_results.json", "w"), indent=2)
    print(f"{cls} ({tf}) -> {res[cls]}", flush=True)
print("DONE")
