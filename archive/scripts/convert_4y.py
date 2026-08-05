"""Convert uploaded 30m BTC/ETH/SOL CSVs into freqtrade 1h + 4h feathers (4-year run)."""
import os
import pandas as pd

OUT_DIR = "user_data/data_4y/binance"
UP = "/root/.claude/uploads/091796be-979d-5f7b-bf9b-03e9d6d4d91f"
SRC = {
    "BTC_USDT": f"{UP}/16f18007-BTCUSDT30.csv",
    "ETH_USDT": f"{UP}/cf91f5a3-ETHUSDT30.csv",
    "SOL_USDT": f"{UP}/61b66895-SOLUSDT30.csv",
}
agg = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
os.makedirs(OUT_DIR, exist_ok=True)

for pair, path in SRC.items():
    df = pd.read_csv(path, sep="\t", header=None,
                     names=["date", "open", "high", "low", "close", "volume"])
    df["date"] = pd.to_datetime(df["date"], utc=True)
    df = df.drop_duplicates(subset="date").sort_values("date").set_index("date")
    for tf, rule in [("1h", "1h"), ("4h", "4h")]:
        res = df.resample(rule, label="left", closed="left").agg(agg)
        empty = res["close"].isna()
        res["close"] = res["close"].ffill()
        for c in ("open", "high", "low"):
            res[c] = res[c].fillna(res["close"])
        res["volume"] = res["volume"].fillna(0.0)
        res = res.reset_index()[["date", "open", "high", "low", "close", "volume"]]
        out = f"{OUT_DIR}/{pair}-{tf}.feather"
        res.to_feather(out)
        print(f"{pair} {tf}: {len(res):,} candles "
              f"({str(res['date'].iloc[0])[:13]} -> {str(res['date'].iloc[-1])[:13]}) "
              f"empty={int(empty.sum())} -> {out}")
print("Done.")
