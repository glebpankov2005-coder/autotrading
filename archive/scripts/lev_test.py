import json, glob, os, subprocess, zipfile, sys
DD="user_data/data_fut/binance"; CFG="user_data/config_fut.json"
STRAT=sys.argv[1] if len(sys.argv)>1 else "cryptotankProL"
P=[("P1 bear","20220901-20231101"),("P2 bull","20231101-20250101"),("P3 chop","20250101-20260801")]
def run(tr):
    b=set(glob.glob("user_data/backtest_results/*.zip"))
    subprocess.run([".venv/bin/python","run_backtest_fut.py","backtesting","--config",CFG,"--strategy",STRAT,
        "--datadir",DD,"--timerange",tr,"--timeframe","1h","--cache","none","--export","trades"],capture_output=True,text=True,timeout=700)
    n=set(glob.glob("user_data/backtest_results/*.zip"))-b
    if not n: return None
    z=max(n,key=os.path.getmtime); zf=zipfile.ZipFile(z)
    m=[x for x in zf.namelist() if x.endswith('.json') and '_config' not in x and not x.endswith(f'_{STRAT}.json')][0]
    return json.loads(zf.read(m))['strategy'][STRAT]
print(f"=== {STRAT} (futures) ===",flush=True)
for name,tr in P:
    st=run(tr); c=round((st.get('cagr') or 0)*100,1)
    print(f"{name}: ret={round(st['profit_total']*100,1):>7}% CAGR={c:>6}% {'>=30 OK' if c>=30 else ''} Sharpe={round(st.get('sharpe') or 0,2):>5} DD={round((st.get('max_drawdown_account') or 0)*100,1):>5}% tr={st['total_trades']}",flush=True)
print("DONE")
