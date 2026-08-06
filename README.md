# autotrading — Apex

A Freqtrade crypto trading strategy for **BTC / ETH / SOL** on the 1-hour timeframe,
long-only spot. The headline strategy, **`Apex`** (formerly `cryptotankBal2`), is a regime-aware
dip-buyer with a tiered trailing-stop exit, validated across multiple independent
market periods.

> **Backtested result (BTC/ETH/SOL, 1h):**
> **+89.4% over 4 years (2022→2026)** · **17.3% CAGR** · Sharpe 0.85 · Profit factor 2.83 ·
> and **+26.6% CAGR / Sharpe 1.53 / ~0% drawdown over the recent 2 years.**

---

## The strategy: `Apex`

It combines three ideas, each earning its place empirically (see `docs/STRATEGY.md`):

1. **Buy the dip in a healthy market.** Enter long when a smoothed measure of price's
   distance-from-its-mean turns sharply negative (a dip), *unless* the market is in a
   confirmed deep bear (price below a falling 200-EMA).
2. **Let the trailing stop do the work.** A tiered trailing stop gives winners more room
   as they run and locks in gains — this exit logic, not the entry, is where the edge
   lives (~86–100% win rate on exits).
3. **Bail on a regime break.** Close longs when price crosses below the 200-EMA.

**Per-token, last 4 years:** SOL +63.6% (93.5% win) · ETH +16.1% (100% win) · BTC +9.7%.

### Honest boundaries
- **A sustained bear (2022-style) still loses** — long-only, no leverage, so it can only
  stand aside when the whole market falls 50%+. The ~17% blended 4-year CAGR includes that
  bear; in normal/bull markets it clears 25%+.
- The near-zero recent drawdown is **best-case** — real slippage/fees beyond the modeled
  0.1%/side will add some.
- One market cycle, three pairs. **Re-validate on fresh data and paper-trade before going
  live** — see `docs/BOT_ROADMAP.md`.

---

## Repository layout

```
README.md                      This file
run_backtest.py                Offline Freqtrade runner (stubs exchange metadata; no network)
convert_data.py                Build feathers from raw source data
download_data.sh               Fetch raw source data
user_data/
  config.json                  Canonical config: BTC/ETH/SOL, Apex, spot 1h
  strategies/
    Apex.py          the strategy (default)
    cryptotankPro.py           defensive high-Sharpe variant (lower return, ~0 drawdown)
    cryptotank.py              the original baseline (reference)
  data/binance/                BTC/ETH/SOL 1h + 4h OHLCV feathers
docs/
  STRATEGY.md                  Detailed strategy write-up + validation
  BOT_ROADMAP.md               Path from backtest -> dry-run -> live
archive/                       Full research history (experiments, variants, findings)
```

## Quick start

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt

# Backtest Apex on BTC/ETH/SOL, last 4 years
python run_backtest.py backtesting --config user_data/config.json \
  --timerange 20220805-20260805 --timeframe 1h --cache none
```

`run_backtest.py` feeds Freqtrade static exchange metadata so it runs fully offline;
OHLCV data, indicators, entries/exits and accounting are 100% real Freqtrade.

## How this strategy was chosen

`Apex` is the result of an extensive, documented research process — a
108-strategy tournament, lookahead-bias filtering, hyperopt with out-of-sample
validation, a long/short futures experiment, leverage tests, and a Vibe-Trading
integration. The short version:

- Most public "winning" strategies were **lookahead-bias artifacts**; a re-hyperopt
  **overfit** (+643% in-sample -> -39% out-of-sample); leverage and shorting **increased
  risk without robust reward**.
- The winner keeps the original's proven entry + trailing-exit engine and adds a light
  **deep-bear filter** + **regime-break exit** — the only combination that stayed
  positive and high-Sharpe across bull, choppy, *and* recent windows.

The full story, data, and every experiment live in `archive/` and `docs/`.
