#!/usr/bin/env bash
# Launch cryptotankBal2 in dry-run (paper trading) against live Binance data.
# Requires a machine/VPS with internet access to Binance. No real orders are placed.
set -euo pipefail
cd "$(dirname "$0")"
[ -d .venv ] && . .venv/bin/activate || true
exec freqtrade trade --config user_data/config_dryrun.json
