"""Convert cryptobigbro Binance 1h CSVs (BTCUSDT, ETHUSDT) into freqtrade 1h + 4h feather.

Source columns: open_timestamp_utc,close_timestamp_utc,open,high,low,close,volume
These are already clean hourly candles; 1h is written directly, 4h is resampled.
Output goes to a dedicated datadir so the existing recent BTC feather is untouched.
"""
import pandas as pd

OUT_DIR = "user_data/data_2y/binance"
PAIRS = {"BTC_USDT": "rawdata/btc_1h.csv", "ETH_USDT": "rawdata/eth_1h.csv"}
agg = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}

import os
os.makedirs(OUT_DIR, exist_ok=True)

for pair, path in PAIRS.items():
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["open_timestamp_utc"], unit="s", utc=True)
    df = df[["date", "open", "high", "low", "close", "volume"]]
    df = df.drop_duplicates(subset="date").sort_values("date").set_index("date")

    for tf, rule in [("1h", "1h"), ("4h", "4h")]:
        res = df.resample(rule, label="left", closed="left").agg(agg)
        empty = res["close"].isna()
        res["close"] = res["close"].ffill()
        for col in ["open", "high", "low"]:
            res[col] = res[col].fillna(res["close"])
        res["volume"] = res["volume"].fillna(0.0)
        res = res.reset_index()[["date", "open", "high", "low", "close", "volume"]]
        out = f"{OUT_DIR}/{pair}-{tf}.feather"
        res.to_feather(out)
        print(f"{pair} {tf}: {len(res):,} candles "
              f"({res['date'].iloc[0]} -> {res['date'].iloc[-1]}) empty={int(empty.sum())} -> {out}")
print("Done.")
