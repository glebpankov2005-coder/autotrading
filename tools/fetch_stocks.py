#!/usr/bin/env python3
"""Fetch daily US-stock OHLCV and write freqtrade feathers (via yfinance).

Runs where the internet is reachable (your VPS or laptop) — NOT in the Claude sandbox.
Stooq blocks datacenter IPs, so this uses yfinance (Yahoo). Install once:
    .venv/bin/pip install yfinance

    .venv/bin/python tools/fetch_stocks.py                # default basket, daily
    .venv/bin/python tools/fetch_stocks.py AAPL MSFT SPY  # custom tickers

Output: user_data/data_stocks/kraken/{TICKER}_USD-1d.feather  (freqtrade layout)
auto_adjust=True → split/dividend-adjusted prices (correct for backtesting).
"""
import os
import sys
import pandas as pd
import yfinance as yf

TICKERS = sys.argv[1:] or ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "SPY", "QQQ"]
OUT = "user_data/data_stocks/kraken"
os.makedirs(OUT, exist_ok=True)

for t in TICKERS:
    try:
        d = yf.Ticker(t).history(period="max", interval="1d", auto_adjust=True)
        if d is None or len(d) == 0:
            print(f"{t:6s} FAILED: no data returned")
            continue
        d = d.reset_index()
        d.columns = [str(c).lower() for c in d.columns]      # date/open/high/low/close/volume/...
        d["date"] = pd.to_datetime(d["date"], utc=True)
        out = d[["date", "open", "high", "low", "close", "volume"]].dropna().reset_index(drop=True)
        out.to_feather(f"{OUT}/{t}_USD-1d.feather")
        print(f"{t:6s} {len(out):5d} bars  {str(out.date.iloc[0])[:10]} -> {str(out.date.iloc[-1])[:10]}")
    except Exception as e:
        print(f"{t:6s} FAILED: {e}")

print(f"\nDone -> {OUT}")
print("Backtest: .venv/bin/python run_backtest_stocks.py backtesting --config user_data/config_stocks.json \\")
print("          --strategy StockExample --strategy-path user_data/strategies \\")
print("          --datadir user_data/data_stocks/kraken --timeframe 1d --timerange 20180101- --cache none")
