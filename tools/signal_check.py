#!/usr/bin/env python3
"""Live signal check for Apex — verifies data flow AND how close each pair is to
an entry. Fetches recent 1h candles straight from Bybit and replays Apex's entry
indicators. Run on the VPS:  .venv/bin/python tools/signal_check.py
"""
import ccxt
import pandas as pd
import talib.abstract as ta
import pandas_ta as pta

PAIRS = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
BUY_MA_SLOPE = -0.35  # Apex default: enter when rolling-min slope < this

ex = ccxt.bybit({"options": {"defaultType": "spot"}, "enableRateLimit": True})
print(f"Exchange: {ex.id}   (fetching 1h candles)\n")

for p in PAIRS:
    try:
        o = ex.fetch_ohlcv(p, "1h", limit=400)
    except Exception as e:
        print(f"{p:10s} DATA ERROR: {e}")
        continue
    df = pd.DataFrame(o, columns=["date", "open", "high", "low", "close", "volume"])
    df["reference_ma_200"] = ta.SMA(df["close"], timeperiod=200)
    df["change"] = ((df["close"] - df["reference_ma_200"]) / df["close"]) * 100
    df["smooth_change_30"] = ta.SMA(df["change"], timeperiod=30)
    df["smooth_ma_slope"] = pta.momentum.slope(df["smooth_change_30"])
    df["min"] = df["smooth_ma_slope"].rolling(48).min()
    df["ema200"] = ta.EMA(df["close"], timeperiod=200)
    df["not_deep_bear"] = ~((df["close"] < df["ema200"]) & (df["ema200"] < df["ema200"].shift(72)))
    r = df.iloc[-1]
    fire = (r["min"] < BUY_MA_SLOPE) and bool(r["not_deep_bear"]) and r["volume"] > 0
    print(
        f"{p:10s} candles={len(df):4d}  close={r['close']:>10.2f}  "
        f"min_slope={r['min']:+.3f} (need < {BUY_MA_SLOPE})  "
        f"not_deep_bear={bool(r['not_deep_bear'])!s:5s}  "
        f"=> {'ENTER ✅' if fire else 'wait'}"
    )
print("\nIf min_slope is a real number (not nan), indicators are healthy and the")
print("bot will buy as soon as a pair's min_slope dips below the threshold.")
