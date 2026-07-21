# autotrading

Freqtrade-based backtesting workspace for a candidate AI trading bot.

Currently contains the **Candle2** ("Two Candle Theory") strategy and a reproducible 3-year
backtest of it on BTC. See **[RESULTS.md](RESULTS.md)** for the numbers and analysis.

## Layout

| Path | What |
|---|---|
| `user_data/strategies/Candle2.py` | The strategy (Freqtrade `IStrategy`). |
| `user_data/strategies/Candle2.json` | Hyperopt parameters applied during the backtest. |
| `user_data/config.json` | Backtest config (BTC/USDT, spot, 10k wallet, 0.1% fees). |
| `user_data/data/binance/*.feather` | 1h + 4h OHLCV candles (BTC), 2023-01 → 2026-07. |
| `convert_data.py` | Builds the feather candles from raw 1-minute CSV. |
| `download_data.sh` | Fetches the raw 1-minute BTC/USD source data. |
| `run_backtest.py` | Offline wrapper around `freqtrade backtesting` (stubs exchange metadata). |
| `requirements.txt` | Python deps (freqtrade, TA-Lib, technical, scipy). |

## Quick start

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python run_backtest.py backtesting \
  --config user_data/config.json --strategy Candle2 \
  --timerange 20230721-20260721 --timeframe 1h --cache none
```

## Note on data / network

This backtest uses **Bitstamp BTC/USD** minute data (resampled to 1h/4h) as a stand-in for
Binance BTC/USDT, because the build environment blocks exchange APIs. `run_backtest.py` therefore
stubs exchange metadata so freqtrade runs fully offline. On a machine with exchange access you can
instead use `freqtrade download-data` and the standard `freqtrade backtesting` command.
