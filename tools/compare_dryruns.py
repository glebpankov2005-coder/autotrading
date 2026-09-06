#!/usr/bin/env python3
"""Compare the two parallel paper bots (base Apex vs Apex_Robust) from their sqlite DBs.
Run on the VPS:  .venv/bin/python tools/compare_dryruns.py
"""
import os
import sqlite3

BOTS = [
    ("Apex (base)",   "user_data/dryrun.sqlite"),
    ("Apex-Robust",   "user_data/dryrun_robust.sqlite"),
]
WALLET = 1000.0


def stats(db):
    if not os.path.exists(db):
        return None
    con = sqlite3.connect(db)
    cur = con.cursor()
    try:
        cur.execute("SELECT COUNT(*), COALESCE(SUM(close_profit_abs),0), "
                    "COALESCE(SUM(CASE WHEN close_profit_abs>0 THEN 1 ELSE 0 END),0) "
                    "FROM trades WHERE is_open=0")
        n_closed, profit, wins = cur.fetchone()
        cur.execute("SELECT COUNT(*) FROM trades WHERE is_open=1")
        n_open = cur.fetchone()[0]
    except sqlite3.OperationalError:
        con.close()
        return {"closed": 0, "open": 0, "profit": 0.0, "wins": 0}
    con.close()
    return {"closed": n_closed, "open": n_open, "profit": profit or 0.0, "wins": wins}


print(f"{'BOT':16s} {'Closed':>7} {'Open':>5} {'Wins':>5} {'Win%':>6} {'Profit USDT':>12} {'Return%':>8}")
print("-" * 64)
for name, db in BOTS:
    s = stats(db)
    if s is None:
        print(f"{name:16s}   (no DB yet — bot hasn't run/traded)")
        continue
    win = (s["wins"] / s["closed"] * 100) if s["closed"] else 0.0
    ret = s["profit"] / WALLET * 100
    print(f"{name:16s} {s['closed']:>7} {s['open']:>5} {s['wins']:>5} {win:>5.1f}% "
          f"{s['profit']:>12.2f} {ret:>7.2f}%")
print("\n(Both start from a 1000 USDT paper wallet. Let it run a few weeks before judging —")
print(" Apex is a patient dip-buyer, so early trade counts will be low.)")
