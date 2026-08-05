import json, glob, os, subprocess, zipfile
DD="user_data/data_top7/binance"
def run(cfg,tr,label):
    b=set(glob.glob("user_data/backtest_results/*.zip"))
    subprocess.run([".venv/bin/python","run_backtest_2y.py","backtesting","--config",cfg,"--strategy","cryptotankBal2",
        "--datadir",DD,"--timerange",tr,"--timeframe","1h","--cache","none","--export","trades"],capture_output=True,text=True,timeout=500)
    n=set(glob.glob("user_data/backtest_results/*.zip"))-b
    if not n: print(label,"FAIL"); return
    z=max(n,key=os.path.getmtime); zf=zipfile.ZipFile(z)
    m=[x for x in zf.namelist() if x.endswith('.json') and '_config' not in x and not x.endswith('_cryptotankBal2.json')][0]
    st=json.loads(zf.read(m))['strategy']['cryptotankBal2']; c=round((st.get('cagr') or 0)*100,1)
    print(f"{label}: ret={round(st['profit_total']*100,1):>6}% CAGR={c:>6}% {'>=25 OK' if c>=25 else ''} Sharpe={round(st.get('sharpe') or 0,2)} DD={round((st.get('max_drawdown_account') or 0)*100,1)}% tr={st['total_trades']}",flush=True)
# base config
base=json.load(open("user_data/config_top7.json"))
for mot in [3,5,7]:
    base["max_open_trades"]=mot; json.dump(base,open(f"/tmp/c_{mot}.json","w"))
    run(f"/tmp/c_{mot}.json","20220805-20260805",f"4y  mot={mot}")
    run(f"/tmp/c_{mot}.json","20240805-20260805",f"2y  mot={mot}")
print("DONE")
