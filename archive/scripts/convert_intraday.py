"""Build BTC feathers at 5m/15m/30m/1h from ff137 Bitstamp 1-min data."""
import gzip, os, pandas as pd
OUT="user_data/data_intraday/binance"; os.makedirs(OUT, exist_ok=True)
WARMUP="2023-06-01"  # warmup before a 2024->2026 window
def load(p, opener=open):
    with opener(p,"rt") as fh: return pd.read_csv(fh)
print("loading 1-min..."); 
df=pd.concat([load("rawdata/btc_hist.csv.gz",gzip.open), load("rawdata/btc_latest.csv")], ignore_index=True)
df["date"]=pd.to_datetime(df["timestamp"], unit="s", utc=True)
df=df[["date","open","high","low","close","volume"]].drop_duplicates("date").sort_values("date")
df=df[df["date"]>=pd.Timestamp(WARMUP, tz="UTC")].set_index("date")
print(f"1-min rows in range: {len(df):,} ({df.index.min()} -> {df.index.max()})")
agg={"open":"first","high":"max","low":"min","close":"last","volume":"sum"}
for tf,rule in [("5m","5min"),("15m","15min"),("30m","30min"),("1h","1h")]:
    r=df.resample(rule,label="left",closed="left").agg(agg)
    empty=r["close"].isna(); r["close"]=r["close"].ffill()
    for c in ("open","high","low"): r[c]=r[c].fillna(r["close"])
    r["volume"]=r["volume"].fillna(0.0)
    r=r.reset_index()[["date","open","high","low","close","volume"]]
    out=f"{OUT}/BTC_USDT-{tf}.feather"; r.to_feather(out)
    print(f"  {tf}: {len(r):,} candles empty={int(empty.sum())} -> {out}")
print("done")
