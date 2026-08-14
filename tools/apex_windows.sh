#!/usr/bin/env bash
# Re-baseline Apex on BYBIT data (the exchange the live bot trades), BTC/ETH/SOL,
# 1h spot, across multiple windows. This replaces the old Binance-based numbers so
# the backtest matches live reality — no more Binance/Bybit mismatch.
#
# Run on the VPS (Bybit data already downloaded via config_research.json):
#   bash tools/apex_windows.sh
set -uo pipefail
cd "$(dirname "$0")/.."
FT=".venv/bin/freqtrade"
CFG="user_data/config_research.json"   # Bybit spot, strategy Apex
PAIRS="BTC/USDT ETH/USDT SOL/USDT"

run () {
  local tr="$1" label="$2"
  local out
  out=$($FT backtesting --config "$CFG" --pairs $PAIRS \
        --timerange "$tr" --timeframe 1h --cache none 2>/dev/null)
  local ret cagr sharpe dd trn
  ret=$(echo "$out"   | grep -iE "Total profit %"                | grep -oE "[-0-9.]+%" | head -1)
  cagr=$(echo "$out"  | grep -iE "CAGR %"                        | grep -oE "[-0-9.]+%" | head -1)
  sharpe=$(echo "$out"| grep -iE "Sharpe \(daily"               | grep -oE "[-0-9.]+"  | tail -1)
  dd=$(echo "$out"    | grep -iE "Max % of account underwater  " | grep -oE "[0-9.]+%"  | head -1)
  trn=$(echo "$out"   | grep -iE "Total/Daily Avg Trades"        | grep -oE "[0-9]+"    | head -1)
  printf "%-22s ret=%-9s CAGR=%-8s Sharpe=%-7s MaxDD=%-7s trades=%s\n" \
         "$label" "${ret:-NA}" "${cagr:-NA}" "${sharpe:-NA}" "${dd:-NA}" "${trn:-NA}"
}

echo "=== APEX on BYBIT (BTC/ETH/SOL, 1h spot) — the real, live-matching numbers ==="
run 20220101-  "full_cycle_2022+"
run 20220805-  "last_4y"
run 20240805-  "recent_2y"
run 20250805-  "recent_1y"
echo ""
echo "These are the numbers to trust from now on — same data feed the live bot trades."
