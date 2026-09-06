import os, sys, pandas as pd
U = "/root/.claude/uploads/091796be-979d-5f7b-bf9b-03e9d6d4d91f"
TF = sys.argv[1]  # "5m" or "15m"
FILES = {
    "5m": {"BTC_USDT_USDT": "8206f957-BTCUSDT5", "ETH_USDT_USDT": "74f1d035-ETHUSDT5", "SOL_USDT_USDT": "bfea9413-SOLUSDT5"},
    "15m": {"BTC_USDT_USDT": "2667659a-BTCUSDT15", "ETH_USDT_USDT": "39bb2b19-ETHUSDT152", "SOL_USDT_USDT": "d47059c7-SOLUSDT152"},
}[TF]
OUT = f"user_data/data_{TF}/binance/futures"
os.makedirs(OUT, exist_ok=True)
for pair, f in FILES.items():
    df = pd.read_csv(f"{U}/{f}.csv", sep="\t", header=None, names=["date", "open", "high", "low", "close", "volume"])
    df["date"] = pd.to_datetime(df["date"], utc=True)
    df = df.drop_duplicates("date").sort_values("date")[["date", "open", "high", "low", "close", "volume"]].reset_index(drop=True)
    df.to_feather(f"{OUT}/{pair}-{TF}-futures.feather")
    df.to_feather(f"{OUT}/{pair}-{TF}-mark.feather")
    fr = df[["date"]].copy()
    for c in ["open", "high", "low", "close", "volume"]:
        fr[c] = 0.0
    fr.to_feather(f"{OUT}/{pair}-{TF}-funding_rate.feather")
    fr.to_feather(f"{OUT}/{pair}-8h-funding_rate.feather")
    print(f"{pair} {TF}: {len(df):,} bars {str(df.date.iloc[0])[:10]} -> {str(df.date.iloc[-1])[:10]}")
print("done")
