#!/usr/bin/env bash
# Enable FreqUI (freqtrade's web dashboard) on BOTH dry-run bots so you can watch and
# compare them in a browser. Turns on each bot's API server, installs the UI, opens the
# firewall ports, and restarts both. Paper bots only (no exchange keys) — so a public
# port carries limited risk, but a strong random password is set regardless.
#
# Run on the VPS:  sudo bash deploy/enable_webui.sh
set -euo pipefail
cd "$(dirname "$0")/.."
PY=".venv/bin/python"
FT=".venv/bin/freqtrade"

# one shared login password for both bots (so FreqUI is easy to use)
PASS=$($PY -c "import secrets;print(secrets.token_urlsafe(12))")

for pair in "user_data/config_dryrun.json:8080" "user_data/config_dryrun_robust.json:8081"; do
  cfg=${pair%%:*}; port=${pair##*:}
  PW="$PASS" CFG="$cfg" PORT="$port" $PY - <<'PYEOF'
import json, os, secrets
cfg = os.environ["CFG"]; port = int(os.environ["PORT"]); pw = os.environ["PW"]
c = json.load(open(cfg))
a = c.setdefault("api_server", {})
a.update(enabled=True, listen_ip_address="0.0.0.0", listen_port=port,
         verbosity="error", enable_openapi=False,
         jwt_secret_key=secrets.token_hex(32), ws_token=secrets.token_hex(16),
         CORS_origins=["*"], username="freqtrader", password=pw)
json.dump(c, open(cfg, "w"), indent=4)
print(f"   api_server enabled on {cfg} (port {port})")
PYEOF
done

echo ">> Installing FreqUI…"
$FT install-ui >/dev/null 2>&1 || $FT install-ui

# open firewall ports if ufw is active (Hetzner Cloud has no firewall by default)
if command -v ufw >/dev/null 2>&1 && ufw status 2>/dev/null | grep -q "Status: active"; then
  ufw allow 8080/tcp || true
  ufw allow 8081/tcp || true
fi

systemctl restart apex-dryrun apex-robust-dryrun

IP=$(curl -s -m 5 ifconfig.me 2>/dev/null || echo "YOUR_SERVER_IP")
echo ""
echo "✅ Web dashboard is live."
echo "   Base Apex:    http://$IP:8080"
echo "   Apex-Robust:  http://$IP:8081"
echo ""
echo "   Login:  username = freqtrader"
echo "           password = $PASS"
echo ""
echo "   Tip: open the base URL, log in, then in FreqUI add the second bot"
echo "   (Settings -> add bot -> http://$IP:8081, same login) to compare both."
