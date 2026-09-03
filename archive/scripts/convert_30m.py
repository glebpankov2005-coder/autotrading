"""Build native 30m freqtrade feathers from the uploaded 30m CSVs."""
import os, pandas as pd
OUT="user_data/data_30m/binance"; os.makedirs(OUT, exist_ok=True)
UP="/root/.claude/uploads/091796be-979d-5f7b-bf9b-03e9d6d4d91f"
SRC={"BTC_USDT":f"{UP}/16f18007-BTCUSDT30.csv","ETH_USDT":f"{UP}/cf91f5a3-ETHUSDT30.csv","SOL_USDT":f"{UP}/61b66895-SOLUSDT30.csv"}
for pair,path in SRC.items():
    df=pd.read_csv(path,sep="\t",header=None,names=["date","open","high","low","close","volume"])
    df["date"]=pd.to_datetime(df["date"],utc=True)
    df=df.drop_duplicates("date").sort_values("date")[["date","open","high","low","close","volume"]]
    out=f"{OUT}/{pair}-30m.feather"; df.reset_index(drop=True).to_feather(out)
    print(f"{pair} 30m: {len(df):,} candles {str(df.date.iloc[0])[:13]} -> {str(df.date.iloc[-1])[:13]} -> {out}")
