import json, glob, os, subprocess, zipfile, sys
DD="user_data/data_intraday/binance"; TR="20240804-20260804"; CFG="user_data/config_intraday.json"
STRAT=sys.argv[1] if len(sys.argv)>1 else "cryptotankTF"
def run(tf):
    before=set(glob.glob("user_data/backtest_results/*.zip"))
    p=subprocess.run([".venv/bin/python","run_backtest_2y.py","backtesting","--config",CFG,
        "--strategy",STRAT,"--datadir",DD,"--timerange",TR,"--timeframe",tf,"--cache","none","--export","trades"],
        capture_output=True,text=True,timeout=600)
    new=set(glob.glob("user_data/backtest_results/*.zip"))-before
    if not new:
        e=[l for l in (p.stdout+p.stderr).splitlines() if "Error" in l or "No data" in l or "Exception" in l]
        return f"{tf:>4}: FAIL {e[-1][:90] if e else '?'}"
    z=max(new,key=os.path.getmtime); zf=zipfile.ZipFile(z)
    m=[n for n in zf.namelist() if n.endswith('.json') and '_config' not in n and not n.endswith(f'_{STRAT}.json')][0]
    st=json.loads(zf.read(m))['strategy'][STRAT]
    return (f"{tf:>4}: trades={st['total_trades']:>5} | ret={round(st['profit_total']*100,1):>7}% | "
            f"Sharpe={round(st.get('sharpe') or 0,3):>6} | Sortino={round(st.get('sortino') or 0,3):>6} | "
            f"PF={round(st.get('profit_factor') or 0,2):>5} | DD={round((st.get('max_drawdown_account') or 0)*100,1):>5}% | "
            f"win={round((st.get('winrate') or 0)*100,1)}%")
print(f"=== {STRAT} (k default) ===",flush=True)
for tf in ["1h","30m","15m","5m"]: print(run(tf),flush=True)
