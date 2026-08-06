# Backtest — uploaded strategies

Five files were uploaded; `fft_cycle_module.py` is a helper (not an `IStrategy`). The four
strategies were backtested in **futures mode, 1h, BTC/ETH/SOL, 2024-08 → 2026-08**.

| Strategy | Native TF | Return | CAGR | Sharpe | Max DD | PF | Trades | Win% | Config fix |
|---|---|---|---|---|---|---|---|---|---|
| ECRV32 | 5m | +1.7% | 0.9% | 0.02 | 30.9% | 1.01 | 367 | 73.8% | — |
| AlexBandSniper (V65513) | 15m | −21.1% | −11.2% | −0.15 | 68.1% | 0.95 | 388 | 78.4% | market orders (`price_side=other`) |
| AlexNexusForge (V8AIV7) | 1h | −68.7% | −44.0% | −2.01 | 72.6% | 0.75 | 876 | 81.8% | — |
| FFTAdaptiveCycle | 5m | −82.7% | −58.4% | −0.13 | 95.8% | 0.75 | 260 | 93.1% | — |
| cryptotankBal2 (reference) | 1h | +60.2% | +26.6% | +1.53 | ~0% | — | — | — | spot |

## Caveats
- **Data**: only 1h is reachable here (exchange APIs blocked). ECRV32/FFT (5m) and
  AlexBandSniper (15m) ran at 1h → **distorted**, understating strategies whose logic is
  timeframe-critical (esp. FFT cycle detection). AlexNexusForge is natively 1h → its
  result is **fair**.
- **Leverage/futures**: all ran with their built-in leverage (ECRV32 10×, FFT 2×),
  amplifying drawdowns.
- **Pattern**: high win rates (74–93%) but negative returns + large drawdowns — many small
  wins wiped out by a few big leveraged losses (FFT: 93% win yet −82.7% / 95.8% DD).
- To judge the 5m/15m strategies fairly, re-run with uploaded 5m/15m data.

## Reproduce
```bash
python build_fut2.py                       # build dummy-funding futures data from user_data/data/binance
python run_uploaded.py 20240805-20260805   # backtest all four (uses run_backtest_fut.py stub)
# AlexBandSniper needs market orders:
python run_backtest_fut.py backtesting --config user_data/config_upload_market.json \
  --strategy AlexBandSniperV65513 --strategy-path user_data/strategies_uploaded \
  --datadir user_data/data_fut2/binance --timerange 20240805-20260805 --timeframe 1h --cache none
```
