#!/usr/bin/env python3
"""Fetch daily US-stock OHLCV and write freqtrade feathers.

Runs where the internet is reachable (your VPS or laptop) — NOT in the Claude sandbox,
where market-data hosts are blocked. Uses Stooq (free, no API key). yfinance fallback
is noted in docs/STOCKS.md.

    python tools/fetch_stocks.py                       # default ticker set, daily
    python tools/fetch_stocks.py AAPL MSFT NVDA        # custom tickers

Output: user_data/data_stocks/kraken/{TICKER}_USD-1d.feather  (freqtrade layout)
"""
import io
import os
import sys
import urllib.request
import pandas as pd

TICKERS = sys.argv[1:] or ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "SPY", "QQQ"]
OUT = "user_data/data_stocks/kraken"
os.makedirs(OUT, exist_ok=True)


def fetch_stooq(ticker):
    url = f"https://stooq.com/q/d/l/?s={ticker.lower()}.us&i=d"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read().decode()
    if "Date" not in raw:
        raise RuntimeError(f"no data for {ticker} (got: {raw[:80]!r})")
    df = pd.read_csv(io.StringIO(raw))
    df = df.rename(columns=str.lower)  # Date,Open,High,Low,Close,Volume -> lower
    df["date"] = pd.to_datetime(df["date"], utc=True)
    df = df[["date", "open", "high", "low", "close", "volume"]].dropna().reset_index(drop=True)
    return df


for t in TICKERS:
    try:
        df = fetch_stooq(t)
        df.to_feather(f"{OUT}/{t}_USD-1d.feather")
        print(f"{t:6s} {len(df):5d} bars  {str(df.date.iloc[0])[:10]} -> {str(df.date.iloc[-1])[:10]}")
    except Exception as e:
        print(f"{t:6s} FAILED: {e}")
print(f"\nDone -> {OUT}")
print("Backtest with: python run_backtest_stocks.py backtesting --config user_data/config_stocks.json \\")
print("               --datadir user_data/data_stocks/kraken --timeframe 1d --timerange 20180101- --cache none")
