#!/usr/bin/env python3
"""Fetch US-stock OHLCV and write freqtrade feathers (via yfinance).

Runs where the internet is reachable (your VPS or laptop) — NOT in the Claude sandbox.
Stooq blocks datacenter IPs, so this uses yfinance (Yahoo). Install once:
    .venv/bin/pip install yfinance

    .venv/bin/python tools/fetch_stocks.py                     # default basket, daily
    .venv/bin/python tools/fetch_stocks.py AAPL MSFT SPY       # custom tickers, daily
    .venv/bin/python tools/fetch_stocks.py --interval 1h       # default basket, HOURLY
    .venv/bin/python tools/fetch_stocks.py --interval 1h AAPL  # custom tickers, hourly

Output: user_data/data_stocks/kraken/{TICKER}_USD-{tf}.feather  (freqtrade layout)
auto_adjust=True → split/dividend-adjusted prices (correct for backtesting).

Note on intraday: Yahoo caps 1h/intraday history at ~730 days, so 1h feathers only
go back ~2 years. Daily ('max') goes back decades.
"""
import os
import sys
import pandas as pd
import yfinance as yf

args = sys.argv[1:]
interval = "1d"
if "--interval" in args:
    i = args.index("--interval")
    interval = args[i + 1]
    del args[i:i + 2]

# yfinance history period per interval (intraday is capped at ~730d by Yahoo)
PERIOD = {"1d": "max", "1h": "730d", "60m": "730d", "30m": "60d", "15m": "60d"}
period = PERIOD.get(interval, "730d")

TICKERS = args or ["AAPL", "MSFT", "AMZN", "GOOGL", "META", "TSLA", "SPY", "QQQ"]
OUT = "user_data/data_stocks/kraken"
os.makedirs(OUT, exist_ok=True)

for t in TICKERS:
    try:
        d = yf.Ticker(t).history(period=period, interval=interval, auto_adjust=True)
        if d is None or len(d) == 0:
            print(f"{t:6s} FAILED: no data returned")
            continue
        d = d.reset_index()
        d.columns = [str(c).lower() for c in d.columns]      # date/datetime/open/high/low/close/volume/...
        # intraday index is named 'datetime', daily is 'date' — normalise
        if "datetime" in d.columns and "date" not in d.columns:
            d = d.rename(columns={"datetime": "date"})
        d["date"] = pd.to_datetime(d["date"], utc=True)
        out = d[["date", "open", "high", "low", "close", "volume"]].dropna().reset_index(drop=True)
        out.to_feather(f"{OUT}/{t}_USD-{interval}.feather")
        print(f"{t:6s} {len(out):6d} bars  {str(out.date.iloc[0])[:16]} -> {str(out.date.iloc[-1])[:16]}")
    except Exception as e:
        print(f"{t:6s} FAILED: {e}")

print(f"\nDone -> {OUT}  (interval={interval})")
print("Backtest: .venv/bin/python run_backtest_stocks.py backtesting --config user_data/config_stocks.json \\")
print(f"          --strategy StockExample --strategy-path user_data/strategies \\")
print(f"          --datadir user_data/data_stocks/kraken --timeframe {interval} --timerange 20180101- --cache none")
