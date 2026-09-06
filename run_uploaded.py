import json, glob, os, subprocess, zipfile, sys
DD="user_data/data_fut2/binance"; CFG="user_data/config_upload.json"; SP="user_data/strategies_uploaded"
TR=sys.argv[1] if len(sys.argv)>1 else "20240805-20260805"
STRATS=[("ECRV32","ECRV32"),("FFTAdaptiveCycle","FFT_AdaptiveCycle"),
        ("AlexBandSniperV65513","AlexBandSniper"),("AlexNexusForgeV8AIV7","AlexNexusForge")]
def run(cls):
    before=set(glob.glob("user_data/backtest_results/*.zip"))
    p=subprocess.run([".venv/bin/python","run_backtest_fut.py","backtesting","--config",CFG,"--strategy",cls,
        "--strategy-path",SP,"--datadir",DD,"--timerange",TR,"--timeframe","1h","--cache","none","--export","trades"],
        capture_output=True,text=True,timeout=1800)
    new=set(glob.glob("user_data/backtest_results/*.zip"))-before
    if not new:
        errs=[l for l in (p.stdout+p.stderr).splitlines() if any(k in l for k in ("Error","Exception","No data","ModuleNotFound","OperationalException","raise"))]
        return {"status":"FAIL","reason":(errs[-1].split(" - ")[-1][:110] if errs else "no result")}
    z=max(new,key=os.path.getmtime); zf=zipfile.ZipFile(z)
    m=[x for x in zf.namelist() if x.endswith('.json') and '_config' not in x and not x.endswith(f'_{cls}.json')][0]
    st=json.loads(zf.read(m))['strategy'][cls]
    return {"status":"OK","ret":round(st['profit_total']*100,1),"cagr":round((st.get('cagr') or 0)*100,1),
            "sharpe":round(st.get('sharpe') or 0,2),"dd":round((st.get('max_drawdown_account') or 0)*100,1),
            "pf":round(st.get('profit_factor') or 0,2),"tr":st['total_trades'],"win":round((st.get('winrate') or 0)*100,1)}
res={}
for cls,label in STRATS:
    r=run(cls); res[label]=r
    print(f"{label:16s} {cls:22s} -> {r}",flush=True)
json.dump(res, open("uploaded_results.json","w"), indent=2)
print("DONE")
