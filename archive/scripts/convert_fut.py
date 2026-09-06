"""Build freqtrade futures-format data (candles+mark+funding) from spot 1h feathers."""
import os, pandas as pd
SRC="user_data/data_4y/binance"; OUT="user_data/data_fut/binance/futures"; os.makedirs(OUT, exist_ok=True)
PAIRS={"BTC_USDT_USDT":"BTC_USDT","ETH_USDT_USDT":"ETH_USDT","SOL_USDT_USDT":"SOL_USDT"}
for fut,spot in PAIRS.items():
    df=pd.read_feather(f"{SRC}/{spot}-1h.feather")
    # candles + mark = same OHLCV; funding = 0
    df.to_feather(f"{OUT}/{fut}-1h-futures.feather")
    df.to_feather(f"{OUT}/{fut}-1h-mark.feather")
    fr=df[["date"]].copy(); fr["open"]=0.0
    fr.to_feather(f"{OUT}/{fut}-8h-funding_rate.feather")
    fr.to_feather(f"{OUT}/{fut}-1h-funding_rate.feather")
    print(f"{fut}: {len(df):,} candles ({str(df.date.iloc[0])[:10]}->{str(df.date.iloc[-1])[:10]})")
print("done")
