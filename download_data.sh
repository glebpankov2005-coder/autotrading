#!/usr/bin/env bash
# Download raw 1-minute BTC/USD data (Bitstamp) used to build the backtest candles.
# Source: https://github.com/ff137/bitstamp-btcusd-minute-data (daily-updated, plain CSV).
# Only needed to regenerate user_data/data/binance/*.feather via convert_data.py;
# the feather files are committed, so a plain backtest does not require this step.
set -euo pipefail
mkdir -p rawdata
BASE="https://raw.githubusercontent.com/ff137/bitstamp-btcusd-minute-data/main/data"
echo "Downloading historical (2012 -> 2025-01, ~90MB)..."
curl -fSL -o rawdata/btcusd_hist.csv.gz "$BASE/historical/btcusd_bitstamp_1min_2012-2025.csv.gz"
echo "Downloading latest updates (2025-01 -> today)..."
curl -fSL -o rawdata/btcusd_latest.csv "$BASE/updates/btcusd_bitstamp_1min_latest.csv"
echo "Done. Now run: python convert_data.py"
