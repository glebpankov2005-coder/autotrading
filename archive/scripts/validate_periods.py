import json, glob, os, subprocess, zipfile
DD="user_data/data_4y/binance"; CFG="user_data/config_4y.json"
PERIODS=[("P1_2022-09..2023-11","20220901-20231101"),
         ("P2_2023-11..2025-01","20231101-20250101"),
         ("P3_2025-01..2026-08","20250101-20260801")]
STRATS=["cryptotank","cryptotankPro","cryptotankV2"]
def run(strat,tr):
    before=set(glob.glob("user_data/backtest_results/*.zip"))
    p=subprocess.run([".venv/bin/python","run_backtest_2y.py","backtesting","--config",CFG,
        "--strategy",strat,"--datadir",DD,"--timerange",tr,"--timeframe","1h","--cache","none","--export","trades"],
        capture_output=True,text=True,timeout=600)
    new=set(glob.glob("user_data/backtest_results/*.zip"))-before
    if not new: return None
    z=max(new,key=os.path.getmtime); zf=zipfile.ZipFile(z)
    m=[n for n in zf.namelist() if n.endswith('.json') and '_config' not in n and not n.endswith(f'_{strat}.json')][0]
    st=json.loads(zf.read(m))['strategy'][strat]
    return dict(ret=round(st['profit_total']*100,1), cagr=round((st.get('cagr') or 0)*100,1),
                sharpe=round(st.get('sharpe') or 0,3), sortino=round(st.get('sortino') or 0,3),
                pf=round(st.get('profit_factor') or 0,2), dd=round((st.get('max_drawdown_account') or 0)*100,1),
                tr=st['total_trades'], win=round((st.get('winrate') or 0)*100,1))
for name,tr in PERIODS:
    print(f"\n### {name}  ({tr}) ###",flush=True)
    print(f"{'strategy':16s} {'ret%':>7} {'CAGR%':>7} {'Sharpe':>7} {'Sortino':>8} {'PF':>5} {'DD%':>6} {'trades':>6} {'win%':>5}")
    for s in STRATS:
        r=run(s,tr)
        if r: print(f"{s:16s} {r['ret']:>7} {r['cagr']:>7} {r['sharpe']:>7} {r['sortino']:>8} {r['pf']:>5} {r['dd']:>6} {r['tr']:>6} {r['win']:>5}",flush=True)
        else: print(f"{s:16s} FAILED",flush=True)
print("\nDONE")
