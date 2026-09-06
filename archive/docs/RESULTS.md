# Candle2 ("Two Candle Theory") — 3-Year Backtest

**Period:** 2023-07-21 → 2026-07-21 (3 years) · **Timeframe:** 1h (+ 4h informative)
**Pair:** BTC/USDT · **Start:** 10,000 USDT · **Fees:** 0.1%/side · **Params:** `Candle2.json` (your hyperopt result)

## Headline

| Metric | Result |
|---|---|
| Total profit | **−36.24%** (−3,624 USDT) |
| Final balance | 6,376 USDT |
| CAGR | −13.92% |
| **BTC buy & hold, same period** | **+120.40%** |
| Trades | 504 |
| Win rate | 43.1% |
| Profit factor | 0.73 |
| Max drawdown | −36.79% (Jul 2023 → Jul 2026, i.e. nearly the whole test) |
| Sharpe / Sortino | −1.07 / −1.49 |

The strategy **lost money in a market that more than doubled.** It effectively bled capital
across the entire window rather than in one bad stretch.

## Why — the exits are the problem

Entries are fine; the losses come almost entirely from two **signal-based exits** that dump
positions into weakness at a near-zero win rate. The automated exits (trailing stop, ROI) are
strongly profitable — the strategy's own sell logic overrides them at the worst time.

| Exit reason | Exits | Total profit | Win% |
|---|---|---|---|
| `trailing_stop_loss` | 158 | **+76.56%** | 98.1% |
| `roi` | 56 | **+13.83%** | 83.9% |
| `Above Resistance 4h` | 9 | −0.11% | 44.4% |
| `Downtrend Inflection Cross` (`use_11`) | 62 | **−17.57%** | 6.5% |
| `Trending Bear Exit` (`use_13`) | 219 | **−108.96%** | 3.2% |

`Trending Bear Exit` alone gives back ~109% of starting capital across 219 trades at a **3.2%**
win rate. Trades that would have hit the trailing stop or ROI as winners are instead force-closed
at a loss. Turning off `use_11`/`use_13` (letting trailing stop + ROI manage exits) is the single
highest-impact change to test next.

## Entries, ranked (Total profit %)

| Enter tag | Entries | Total profit | Win% |
|---|---|---|---|
| Uptrend Inflection Cross | 92 | +2.10% | 52.2% |
| 4h Extreme RSI | 25 | +2.05% | 56.0% |
| Support Cross | 35 | −1.81% | 34.3% |
| Below Support 4h pull up | 57 | −7.93% | 36.8% |
| Pattern and RSI | 102 | −9.67% | 31.4% |
| Trending Bull Entry | 193 | −20.98% | 46.6% |

Every entry tag looks decent when it exits via trailing stop/ROI and terrible when the bear-exit
signal fires — confirming the issue is exit timing, not entry selection.

## Important caveats (read before trusting the number)

1. **Data ≠ your live exchange.** Source is **Bitstamp BTC/USD** 1-minute data
   (github.com/ff137/bitstamp-btcusd-minute-data), resampled to 1h/4h. This environment blocks
   every exchange API (Binance, Kraken, etc.), so this is the closest freely reachable proxy for
   BTC/USDT. Prices/spreads/fills differ slightly from Binance.
2. **BTC only.** Your config uses `max_open_trades: 3`, but only one pair was available here, so
   effective max open trades = 1. A real multi-pair run (BTC/ETH/SOL/…) would diversify and could
   look materially different.
3. **Exchange metadata is stubbed.** `run_backtest.py` feeds freqtrade a static BTC/USDT market
   definition so it never calls the network. Only metadata (precision/limits/fees) is stubbed —
   candles, indicators, and accounting are real freqtrade.
4. **Fees = 0.1%/side**, no slippage modeled beyond order-book pricing. 504 trades × spread/slippage
   would drag a live result somewhat below this.
5. **In-sample bias.** `Candle2.json` was hyperopted (buy_threshold 6.6, etc.). If that tuning used
   any of this period, results are optimistic. Validate on a held-out range.

## Reproduce

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
# feather data is committed; to rebuild from source: ./download_data.sh && python convert_data.py
python run_backtest.py backtesting \
  --config user_data/config.json --strategy Candle2 \
  --timerange 20230721-20260721 --timeframe 1h --cache none \
  --breakdown month
```
