import os, pandas as pd
SRC="user_data/data/binance"; OUT="user_data/data_fut2/binance/futures"; os.makedirs(OUT, exist_ok=True)
PAIRS={"BTC_USDT_USDT":"BTC_USDT","ETH_USDT_USDT":"ETH_USDT","SOL_USDT_USDT":"SOL_USDT"}
for fut,spot in PAIRS.items():
    for tf in ["1h","4h"]:
        df=pd.read_feather(f"{SRC}/{spot}-{tf}.feather")
        df.to_feather(f"{OUT}/{fut}-{tf}-futures.feather")
        df.to_feather(f"{OUT}/{fut}-{tf}-mark.feather")
        fr=df[["date"]].copy()
        for c in ["open","high","low","close","volume"]: fr[c]=0.0
        fr.to_feather(f"{OUT}/{fut}-{tf}-funding_rate.feather")
    fr8=pd.read_feather(f"{SRC}/{PAIRS[fut]}-1h.feather")[["date"]].copy()
    for c in ["open","high","low","close","volume"]: fr8[c]=0.0
    fr8.to_feather(f"{OUT}/{fut}-8h-funding_rate.feather")
    print(fut, "built")
print("done")
