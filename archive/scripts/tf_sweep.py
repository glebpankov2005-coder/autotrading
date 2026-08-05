"""Backtest cryptotank at 5m/15m/30m/1h on BTC, compare frequency & Sharpe."""
import json, glob, os, subprocess, zipfile
DD="user_data/data_intraday/binance"; TR="20240804-20260804"
CFG="user_data/config_intraday.json"
def run(tf):
    before=set(glob.glob("user_data/backtest_results/*.zip"))
    p=subprocess.run([".venv/bin/python","run_backtest_2y.py","backtesting","--config",CFG,
        "--strategy","cryptotank","--datadir",DD,"--timerange",TR,"--timeframe",tf,
        "--cache","none","--export","trades"],capture_output=True,text=True,timeout=600)
    new=set(glob.glob("user_data/backtest_results/*.zip"))-before
    if not new:
        err=[l for l in (p.stdout+p.stderr).splitlines() if "Error" in l or "No data" in l]
        return f"{tf}: FAILED {err[-1][:80] if err else ''}"
    z=max(new,key=os.path.getmtime); zf=zipfile.ZipFile(z)
    m=[n for n in zf.namelist() if n.endswith('.json') and '_config' not in n and not n.endswith('_cryptotank.json')][0]
    st=json.loads(zf.read(m))['strategy']['cryptotank']
    return (f"{tf:>4}: trades={st['total_trades']:>5} | return={round(st['profit_total']*100,1):>7}% | "
            f"CAGR={round((st.get('cagr') or 0)*100,1):>6}% | Sharpe={round(st.get('sharpe') or 0,3):>6} | "
            f"Sortino={round(st.get('sortino') or 0,3):>6} | PF={round(st.get('profit_factor') or 0,2)} | "
            f"DD={round((st.get('max_drawdown_account') or 0)*100,1)}% | win={round((st.get('winrate') or 0)*100,1)}%")
for tf in ["1h","30m","15m","5m"]:
    print(run(tf), flush=True)
