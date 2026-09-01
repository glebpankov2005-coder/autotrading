# Stock backtesting setup

A parallel harness to backtest strategies on **US equities** (daily) using the same Freqtrade
engine as the crypto side. Stocks are modeled as `TICKER/USD` spot pairs.

## Why the two-step (fetch → backtest) split
The Claude sandbox blocks market-data hosts (Stooq, Yahoo all return `000`) — only GitHub/PyPI
are reachable. So **data is fetched where the internet works** (your VPS or laptop), then
backtested offline (in the sandbox or anywhere). Same pattern as the crypto data.

## Files
- `run_backtest_stocks.py` — offline runner; stubs equities as `TICKER/USD` spot (no network).
- `tools/fetch_stocks.py` — fetches daily OHLCV from **Stooq** (free, no key) → feathers.
- `user_data/config_stocks.json` — basket config (AAPL, MSFT, NVDA, AMZN, GOOGL, META, TSLA,
  SPY, QQQ), daily, spot, USD.
- `user_data/strategies/StockExample.py` — Connors **RSI-2** mean-reversion (a real edge on
  equities; a sane starting point).

## Step 1 — fetch data (on the VPS or your laptop, where internet works)
```bash
python tools/fetch_stocks.py                    # default basket, daily
python tools/fetch_stocks.py AAPL MSFT NVDA SPY # custom tickers
```
Writes `user_data/data_stocks/kraken/{TICKER}_USD-1d.feather`. Stooq data is split-adjusted
daily bars going back years. (Edit the `TICKERS` list in `tools/fetch_stocks.py` and the
`pair_whitelist` in `config_stocks.json` to match the names you fetch, and the `TICKERS`
list in `run_backtest_stocks.py`.)

**yfinance alternative** (if you prefer, needs `pip install yfinance`):
```python
import yfinance as yf, pandas as pd, os
os.makedirs("user_data/data_stocks/kraken", exist_ok=True)
for t in ["AAPL","MSFT","SPY"]:
    d = yf.download(t, start="2015-01-01", auto_adjust=True).reset_index()
    d.columns = [c.lower() for c in d.columns]
    d["date"] = pd.to_datetime(d["date"], utc=True)
    d[["date","open","high","low","close","volume"]].to_feather(
        f"user_data/data_stocks/kraken/{t}_USD-1d.feather")
```

## Step 2 — backtest
```bash
python run_backtest_stocks.py backtesting --config user_data/config_stocks.json \
  --strategy StockExample --strategy-path user_data/strategies \
  --datadir user_data/data_stocks/kraken --timeframe 1d --timerange 20180101- --cache none
```
Everything runs fully offline; OHLCV, indicators, entries/exits and accounting are 100% real
Freqtrade — only the exchange *metadata* is stubbed.

## Notes & caveats
- **Timeframe:** daily (`1d`) is the default. Freqtrade fills weekend/holiday gaps with flat
  bars — harmless for a daily strategy. Intraday equities (1h) are possible but need intraday
  data and mind the ~6.5h session.
- **RSI-2 works on stocks, not crypto.** Equities mean-revert reliably (institutional
  rebalancing, overnight risk); the same mean-reversion *fails* on crypto (we proved it). So
  don't assume crypto results transfer — and don't assume Apex (crypto-tuned, 1h) works on
  stocks without re-tuning its 200-EMA/slope parameters for daily bars.
- **Data quality:** Stooq free data is split-adjusted but not always dividend-adjusted, and has
  no delisted tickers (survivorship bias). Fine for research; validate before trusting.
- **Fees:** modeled at 0.05%/side (retail-ish). Real fills/slippage differ.
- **Universe:** a basket of liquid large-caps + SPY/QQQ. Add/remove tickers in all three places
  noted in Step 1.
