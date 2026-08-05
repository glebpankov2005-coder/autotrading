#!/usr/bin/env python3
"""Lightweight watchdog for the cryptotankBal2 dry-run.

Run from cron every ~5-10 min. Alerts (Telegram) when:
  * the bot process is DOWN  (its own Telegram can't warn you if it's dead)
  * realized drawdown breaches a threshold
  * it recovers after being down

Liveness is auto-detected: systemd unit -> docker container -> pgrep.
Telegram creds come from env (TG_TOKEN / TG_CHAT) or user_data/config_dryrun.json.
Alerts are de-duplicated via a small state file so cron doesn't spam you.

Env knobs:
  MONITOR_UNIT=freqtrade-dryrun     systemd unit name (default)
  MONITOR_CONTAINER=freqtrade-dryrun docker container name (default)
  MONITOR_DB=user_data/dryrun.sqlite path to the trade DB
  MONITOR_DD_PCT=15                  drawdown alert threshold (%)
"""
import json
import os
import shutil
import sqlite3
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE = Path(__file__).resolve().parent / ".monitor_state.json"
DB = Path(os.environ.get("MONITOR_DB", ROOT / "user_data/dryrun.sqlite"))
DD_LIMIT = float(os.environ.get("MONITOR_DD_PCT", "15"))
UNIT = os.environ.get("MONITOR_UNIT", "freqtrade-dryrun")
CONTAINER = os.environ.get("MONITOR_CONTAINER", "freqtrade-dryrun")


def _run(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    except Exception:
        return None


def is_alive():
    # 1) systemd
    if shutil.which("systemctl"):
        r = _run(["systemctl", "is-active", "--quiet", UNIT])
        if r is not None and r.returncode == 0:
            return True
    # 2) docker
    if shutil.which("docker"):
        r = _run(["docker", "inspect", "-f", "{{.State.Running}}", CONTAINER])
        if r and r.stdout.strip() == "true":
            return True
    # 3) pgrep fallback
    r = _run(["pgrep", "-f", "freqtrade trade"])
    if r and r.returncode == 0 and r.stdout.strip():
        return True
    return False


def realized_drawdown_pct():
    """Peak-to-current drawdown of cumulative realized PnL from the trade DB."""
    if not DB.exists():
        return None
    try:
        con = sqlite3.connect(str(DB))
        rows = con.execute(
            "SELECT close_profit_abs FROM trades WHERE is_open=0 ORDER BY close_date"
        ).fetchall()
        con.close()
    except Exception:
        return None
    cum = peak = maxdd = 0.0
    start = float(os.environ.get("MONITOR_WALLET", "1000"))
    for (p,) in rows:
        cum += p or 0.0
        equity = start + cum
        peak = max(peak, equity)
        if peak > 0:
            maxdd = max(maxdd, (peak - equity) / peak * 100.0)
    return round(maxdd, 2)


def telegram(msg):
    tok = os.environ.get("TG_TOKEN")
    chat = os.environ.get("TG_CHAT")
    if not tok or not chat:
        cfg = ROOT / "user_data/config_dryrun.json"
        if cfg.exists():
            t = json.load(open(cfg)).get("telegram", {})
            tok = tok or (t.get("token") if "HERE" not in str(t.get("token")) else None)
            chat = chat or (t.get("chat_id") if "HERE" not in str(t.get("chat_id")) else None)
    if not tok or not chat:
        print("ALERT (no telegram configured):", msg)
        return
    data = urllib.parse.urlencode({"chat_id": chat, "text": msg}).encode()
    try:
        urllib.request.urlopen(f"https://api.telegram.org/bot{tok}/sendMessage", data, timeout=10)
    except Exception as e:
        print("telegram send failed:", e, "|", msg)


def load_state():
    try:
        return json.load(open(STATE))
    except Exception:
        return {"down": False, "dd_alerted": False}


def main():
    st = load_state()
    alive = is_alive()

    if not alive and not st["down"]:
        telegram("🔴 cryptotankBal2 dry-run is DOWN — process not running.")
        st["down"] = True
    elif alive and st["down"]:
        telegram("🟢 cryptotankBal2 dry-run RECOVERED — process is running again.")
        st["down"] = False

    dd = realized_drawdown_pct()
    if dd is not None:
        if dd >= DD_LIMIT and not st["dd_alerted"]:
            telegram(f"⚠️ cryptotankBal2 drawdown {dd}% ≥ {DD_LIMIT}% threshold.")
            st["dd_alerted"] = True
        elif dd < DD_LIMIT * 0.7:
            st["dd_alerted"] = False  # reset once it recovers well below the line

    json.dump(st, open(STATE, "w"))
    print(f"alive={alive} drawdown={dd}% (limit {DD_LIMIT}%)")


if __name__ == "__main__":
    main()
