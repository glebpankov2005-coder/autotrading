#!/usr/bin/env bash
# Proper evaluation of Alex_DivergenceV6 — native 15m, Bybit futures.
# Runs: (1) data download, (2) backtest, (3) lookahead-bias analysis.
# Research only: separate config, never touches the live Apex bot.
#
# Usage (on the VPS):
#   bash tools/test_alexdiv.sh [TIMERANGE]
#   e.g. bash tools/test_alexdiv.sh 20240101-
set -uo pipefail
cd "$(dirname "$0")/.."

CFG="user_data/config_alexdiv.json"
SP="user_data/strategies_uploaded"
STRAT="Alex_DivergenceV6"
TR="${1:-20240101-}"
FT=".venv/bin/freqtrade"

echo ">> [1/3] Downloading 15m Bybit FUTURES data (candles + mark + funding)…"
$FT download-data --config "$CFG" --timerange "$TR" --timeframe 15m \
    --trading-mode futures || { echo "download failed"; exit 1; }

echo ""
echo ">> [2/3] Backtesting $STRAT (15m futures, $TR)…"
$FT backtesting --config "$CFG" --strategy "$STRAT" --strategy-path "$SP" \
    --timerange "$TR" --timeframe 15m --cache none

echo ""
echo ">> [3/3] Lookahead-bias analysis (THE decisive test for a divergence strategy)…"
echo "   If this reports a bias / entries change when future data is hidden,"
echo "   the backtest above is FAKE and the strategy must be rejected."
$FT lookahead-analysis --config "$CFG" --strategy "$STRAT" --strategy-path "$SP" \
    --timerange "$TR" --timeframe 15m 2>&1 | tail -40

echo ""
echo ">> Done. Read the lookahead result FIRST — a biased strategy's returns are meaningless."
