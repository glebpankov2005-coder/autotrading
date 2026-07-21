"""Convert Bitstamp 1-minute BTC/USD CSVs into freqtrade 1h + 4h feather files."""
import gzip
import pandas as pd

WARMUP_START = "2023-01-01"  # extra data before the 3y backtest window for indicator warmup
OUT_DIR = "user_data/data/binance"

def load(path, opener=open):
    with opener(path, "rt") as fh:
        df = pd.read_csv(fh)
    return df

print("Loading historical (gz)...")
hist = load("rawdata/btcusd_hist.csv.gz", gzip.open)
print("Loading latest...")
latest = load("rawdata/btcusd_latest.csv")

df = pd.concat([hist, latest], ignore_index=True)
df["date"] = pd.to_datetime(df["timestamp"], unit="s", utc=True)
df = df[["date", "open", "high", "low", "close", "volume"]]
df = df.drop_duplicates(subset="date").sort_values("date")
df = df[df["date"] >= pd.Timestamp(WARMUP_START, tz="UTC")]
df = df.set_index("date")
print(f"1-min rows in range: {len(df):,}  ({df.index.min()} -> {df.index.max()})")

agg = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}

for tf, rule in [("1h", "1h"), ("4h", "4h")]:
    res = df.resample(rule, label="left", closed="left").agg(agg)
    # forward-fill price on any empty candles (no trades that hour), volume 0
    empty = res["close"].isna()
    res["close"] = res["close"].ffill()
    for col in ["open", "high", "low"]:
        res[col] = res[col].fillna(res["close"])
    res["volume"] = res["volume"].fillna(0.0)
    res = res.reset_index()
    res = res[["date", "open", "high", "low", "close", "volume"]]
    out = f"{OUT_DIR}/BTC_USDT-{tf}.feather"
    res.to_feather(out)
    print(f"  {tf}: {len(res):,} candles ({res['date'].iloc[0]} -> {res['date'].iloc[-1]})  "
          f"empty_filled={int(empty.sum())}  -> {out}")

print("Done.")
