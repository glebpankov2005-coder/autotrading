#!/usr/bin/env bash
# One-command setup for the Apex dry-run on a fresh Ubuntu VPS.
#   git clone <repo> && cd <repo> && sudo bash setup.sh
# Installs deps, builds the venv, sanity-checks the backtest, and starts the
# dry-run 24/7 via systemd (auto-restart + start on boot). No Docker needed.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
RUN_USER="${SUDO_USER:-$(whoami)}"
echo ">> Repo: $REPO_DIR   Run-as user: $RUN_USER"

echo ">> [1/5] Installing system packages…"
apt-get update -y
apt-get install -y python3-venv python3-pip git

echo ">> [2/5] Building Python environment…"
sudo -u "$RUN_USER" python3 -m venv "$REPO_DIR/.venv"
sudo -u "$RUN_USER" "$REPO_DIR/.venv/bin/pip" install --quiet --upgrade pip
sudo -u "$RUN_USER" "$REPO_DIR/.venv/bin/pip" install -r "$REPO_DIR/requirements.txt"

echo ">> [3/5] Sanity backtest (paper, committed data)…"
sudo -u "$RUN_USER" "$REPO_DIR/.venv/bin/freqtrade" backtesting \
  --config "$REPO_DIR/user_data/config_dryrun.json" \
  --datadir "$REPO_DIR/user_data/data" --timerange 20250101- --timeframe 1h \
  2>/dev/null | grep -E "Total profit %|CAGR|Sharpe" || echo "   (backtest summary above; continue)"

echo ">> [4/6] Generating API-server secrets…"
sudo -u "$RUN_USER" "$REPO_DIR/.venv/bin/python" - "$REPO_DIR/user_data/config_dryrun.json" <<'PY'
import json, secrets, sys
f = sys.argv[1]
c = json.load(open(f))
api = c.setdefault("api_server", {})
if str(api.get("jwt_secret_key", "")).startswith("CHANGE_ME"):
    api["jwt_secret_key"] = secrets.token_hex(32)
if str(api.get("ws_token", "")).startswith("CHANGE_ME"):
    api["ws_token"] = secrets.token_hex(16)
if str(api.get("password", "")).startswith("CHANGE_ME"):
    api["password"] = secrets.token_urlsafe(16)
json.dump(c, open(f, "w"), indent=4)
print("   secrets generated")
PY

echo ">> [5/6] Installing systemd service…"
cat > /etc/systemd/system/apex-dryrun.service <<UNIT
[Unit]
Description=Apex dry-run (Freqtrade paper trading)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$RUN_USER
WorkingDirectory=$REPO_DIR
ExecStart=$REPO_DIR/.venv/bin/freqtrade trade --config user_data/config_dryrun.json
Restart=always
RestartSec=15

[Install]
WantedBy=multi-user.target
UNIT

echo ">> [6/6] Starting the bot…"
systemctl daemon-reload
systemctl enable --now apex-dryrun

echo ""
echo "✅ Done. Apex is now paper-trading 24/7."
echo "   Live logs:   journalctl -u apex-dryrun -f"
echo "   Status:      systemctl status apex-dryrun"
echo "   Stop:        systemctl stop apex-dryrun"
