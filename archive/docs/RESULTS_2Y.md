# Strategy Tournament — RoboticAutomations/freqtradestrategies

**Task:** test the strategies from `RoboticAutomations/freqtradestrategies` over 2 years on
BTC/ETH/SOL and pick the best 3.

**Window:** 2024-07-21 → 2026-07-21 (last 2 years) · **Timeframe:** 1h
**Pairs:** BTC/USDT, ETH/USDT, SOL/USDT · **Start:** 10,000 USDT · **Fees:** 0.1%/side ·
**max_open_trades:** 3

## TL;DR

Of the repo's **108 root strategies**, 64 actually ran, and **almost every "winning" one is a
lookahead-bias artifact** — it looks profitable only because it peeks at future candles.
After filtering those out with freqtrade's `lookahead-analysis` plus a manual repaint test, the
best 3 strategies that would actually hold up are:

| Rank | Strategy | Total profit | CAGR | Sharpe (daily) | Profit factor | Max drawdown | Trades | Bias check |
|---|---|---|---|---|---|---|---|---|
| **1** | **cryptotank** | **+38.4%** | +17.6% | 0.70 | 1.44 | 24.7% | 125 | ✅ clean (2 tools) |
| **2** | **eltoro1_4** | +0.3% | +0.2% | 0.18 | 1.00 | 38.5% | 153 | ✅ clean |
| **3** | **wavetrend_rsi** | −2.6% | −1.3% | −0.11 | 0.90 | 10.1% | 161 | ✅ clean |

**Benchmark:** over this window buy-and-hold *lost* on all three pairs — BTC −2.7%, ETH −45.4%,
SOL −54.9% (≈ **−34% equal-weight**). So all three winners beat holding, and **cryptotank beat it
by ~70 points** while beating a falling market.

Only `cryptotank` is a genuinely strong result. #2 and #3 are essentially break-even — they make
the list because everything that scored higher is disqualified for bias.

## Why most of the leaderboard is disqualified

The raw return ranking is dominated by strategies with **physically impossible** risk/return, the
signature of using future data:

| Strategy | Raw return | Sharpe | Verdict |
|---|---|---|---|
| HurstCycle3 | +1331% | 21.1 | 🚩 non-credible (Sharpe 21, 4.5% DD) — bias |
| grad | +641% | 9.8 | 🚩 non-credible — bias |
| HurstCycle7 / HurstCycleV5 | +36% | 1.55 | ⚠️ unverifiable (FFT), family repaints — excluded |
| turbov8 | +11.9% | 0.21 | 🚩 `lookahead-analysis` = **Yes** (7 biased entries) |
| HurstCycleV6 | +7.5% | 0.32 | 🚩 repaint test = **repaints** (88 changed signals) |
| AlexBattleTankKiller (all variants) | −0.5% … −5.6% | — | 🚩 `lookahead-analysis` = **Yes** |

A real spot strategy does not make 13× with a 4.5% drawdown. The `HurstCycle*` family uses FFT
cycle *extrapolation* with `startup_candle_count = 0` — a classic repainting setup — and its own
variants disagree wildly (+1331% vs −98% on the same data), confirming the results aren't causal.

## The best 3 in detail (per-pair)

**1. cryptotank — +38.4%** (the only strong clean strategy). Win rate ~88%, PF 1.44.
Profit is concentrated in ETH; SOL was flat, BTC modestly positive.

| Pair | Trades | Profit | Win% |
|---|---|---|---|
| ETH/USDT | 37 | +31.8% | 91.9% |
| BTC/USDT | 10 | +6.7% | 90.0% |
| SOL/USDT | 78 | −0.1% | 87.2% |

**2. eltoro1_4 — +0.3%** (flat). BTC +7.0% / ETH +0.6% / SOL −7.3%. 38.5% max drawdown makes
this the weakest of the three on risk; it's here only because it's clean and net-positive.

**3. wavetrend_rsi — −2.6%** (small loss, but the *tightest risk*: 10.1% max DD, ~93% win rate).
Slightly negative on every pair; the few large open-trade losers outweigh many tiny wins.

## What ran and what didn't

- **108** root strategies tested · **64** ran · **44** failed (missing libs like FreqAI/`pandas_ta`
  variants, sub-hourly-data needs, or broken source — e.g. the flagship `2Candle.py` is invalid
  Python: `class 2Candle` can't start with a digit).
- **61** produced trades; **10** were nominally profitable, but **7 of those 10 are biased**.
- The `HUGE_FreqTrade_Strategy_Collection/` subfolder (478 more strategies) was out of scope.

## Important caveats

1. **BTC data is a proxy.** This locked-down environment blocks every exchange/data API. BTC is
   Bitstamp BTC/USD (the only reachable recent BTC source); ETH/SOL are the uploaded 15m Binance
   data resampled to 1h. Prices/fills differ slightly from live Binance.
2. **In-repo default params.** Each strategy ran with its own in-code parameters (no external
   hyperopt json), uniformly across all three pairs.
3. **Bias tools aren't perfect.** `HurstCycle7/V5` couldn't be verified (their FFT needs more data
   than the analyzer's per-signal slice); they're excluded as unverifiable, not proven clean.
4. **One regime.** 2024-07→2026-07 was a down/choppy market for alts. Rankings can shift in a
   different regime; validate on a held-out range before trusting any of these live.

## Follow-up: cryptotank over 4 years (2022-08-04 → 2026-08-04)

Re-tested the winner on a **4-year** window (30m uploads resampled to 1h), all three pairs.
Strategy is unchanged, so the earlier bias clearance (lookahead-analysis = No, repaint = clean)
still holds — this is a real, causal result.

| Metric | cryptotank (4y) |
|---|---|
| Total profit | **+70.1%** (CAGR 14.2%) |
| Sharpe (daily) / Sortino | 0.56 / 0.41 |
| Profit factor | 1.36 |
| Max drawdown | 34.4% |
| Trades / win rate | 247 / 87.9% |
| Per pair | ETH +38.6% · BTC +19.8% · SOL +11.7% (all positive) |
| **Buy & hold, same window** | **BTC +175% · ETH +13% · SOL +87% (≈ +92% avg)** |

**Read:** cryptotank is a *defensive, high-win-rate* strategy. Over the last 2 years (a −34%
market) it strongly beat buy-and-hold (+38% vs −34%). Over 4 years — which includes the big
2023-2024 bull — it made a solid **+70%** but **trailed simple holding (+92%)**: it protects
capital in down/choppy regimes and lags a strong bull. `user_data/strategies/cryptotank.py` is
the standalone strategy file.

## Reproduce

```bash
python convert_recent.py            # build ETH/SOL 1h+4h feathers from uploads (BTC pre-staged)
python tourney.py                   # backtest all 108 root strategies on BTC+ETH+SOL, 2y
# bias-check a strategy:
python run_backtest_2y.py lookahead-analysis --config user_data/config_lookahead.json \
  --strategy cryptotank --strategy-path /tmp/tourney_work/cryptotank \
  --datadir user_data/data_recent/binance --timerange 20240721-20260721 --timeframe 1h
python repaint_test.py cryptotank:cryptotank     # manual repaint test
```
