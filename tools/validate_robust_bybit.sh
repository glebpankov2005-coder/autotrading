#!/usr/bin/env bash
# Bybit validation: base Apex vs Apex_Robust on REAL Bybit data (the exchange the bot
# trades), BTC/ETH/SOL 1h spot, across windows. This is the decisive test of whether
# the rising-SMA regime gate fixes Apex's full-cycle fragility on real market data.
# Research only — does NOT touch config_dryrun.json or the live bot.
#
# Run on the VPS (Bybit data already downloaded via config_research.json):
#   bash tools/validate_robust_bybit.sh
set -uo pipefail
cd "$(dirname "$0")/.."
FT=".venv/bin/freqtrade"
CFG="user_data/config_research.json"     # Bybit spot
PAIRS="BTC/USDT ETH/USDT SOL/USDT"

run () {
  local strat="$1" tr="$2"
  local out
  out=$($FT backtesting --config "$CFG" --strategy "$strat" \
        --strategy-path user_data/strategies --pairs $PAIRS \
        --timerange "$tr" --timeframe 1h --cache none 2>/dev/null)
  local ret shp dd trn
  ret=$(echo "$out" | grep -iE "Total profit %"                 | grep -oE "[-0-9.]+%" | head -1)
  shp=$(echo "$out" | grep -iE "Sharpe \(daily"                | grep -oE "[-0-9.]+"  | tail -1)
  dd=$(echo "$out"  | grep -iE "Max % of account underwater  "  | grep -oE "[0-9.]+%"  | head -1)
  trn=$(echo "$out" | grep -iE "Total/Daily Avg Trades"         | grep -oE "[0-9]+"    | head -1)
  printf "  %-12s ret=%-9s Sharpe=%-7s MaxDD=%-7s trades=%s\n" \
         "$strat" "${ret:-ERR}" "${shp:-NA}" "${dd:-NA}" "${trn:-NA}"
}

echo "############ APEX vs APEX_ROBUST on BYBIT data ############"
for w in "20220101-:FULL CYCLE (incl 2022 crash)" "20240101-:RECENT 2Y" "20250101-:RECENT 1Y"; do
  tr=${w%%:*}; lbl=${w##*:}
  echo ""
  echo "===== $lbl ====="
  run Apex        "$tr"
  run Apex_Robust "$tr"
done
echo ""
echo "PASS if Apex_Robust's FULL CYCLE is solidly positive with a lower drawdown than"
echo "base Apex (which was ~-13% / ~60% DD on Bybit). That confirms the regime gate"
echo "survives a real exchange switch — the whole point of the exercise."
