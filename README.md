# Apex — Freqtrade crypto trading bot

A Freqtrade crypto trading strategy for **BTC / ETH / SOL** on the 1-hour timeframe,
long-only spot. The headline strategy, **`Apex`** (formerly `cryptotankBal2`), is a regime-aware
dip-buyer with a tiered trailing-stop exit. A validated variant, **`Apex_Robust`**, adds a
macro-trend regime gate for much lower full-cycle drawdown.

> **Apex backtest (BTC/ETH/SOL, 1h):**
> Binance data — **+89.4% over 4y** · 17.3% CAGR · Sharpe 0.85 · +60% / Sharpe 1.53 / ~0% DD recent-2y.
> Bybit data (the exchange it trades) — recent-2y **+66.6% / Sharpe 1.14**; full cycle incl.
> 2022 crash **−13.2% / 60% DD** ← the honest weakness.

**Live:** both `Apex` and `Apex_Robust` run 24/7 as **paper dry-runs on a Bybit VPS** in a
parallel A/B, with a FreqUI web dashboard. See `docs/DRYRUN.md`.

---

## The strategy: `Apex`

Three ideas, each earning its place empirically (see `docs/STRATEGY.md`):

1. **Buy the dip in a healthy market.** Enter long when a smoothed measure of price's
   distance-from-its-mean turns sharply negative (a fast dip), *unless* the market is in a
   confirmed deep bear (price below a falling 200-EMA).
2. **Let the trailing stop do the work.** A tiered trailing stop gives winners more room as
   they run and locks in gains — **this exit, not the entry, is the edge** (proven repeatedly:
   every attempt to change it degrades returns).
3. **Bail on a regime break.** Close longs when price crosses below the 200-EMA.

Returns are concentrated in **SOL** (~70% of profit) — the most volatile coin gives the most
and deepest dips. Apex *harvests* volatility.

### `Apex_Robust` — the validated improvement
Same engine + **one change: only buy when BTC's 200-SMA is rising** (macro uptrend). On Bybit
this turns the full-cycle **−13% / 60% DD into +25% / 28% DD**, at the cost of ~half the
bull-market upside. Lookahead-clean and parameter-robust. The "survive a 2022 / sleep at night"
version. Full write-up + every rejected experiment in `docs/EXPERIMENTS.md`.

### Honest boundaries
- **A sustained bear (2022-style) still hurts** — long-only, no leverage. `Apex_Robust`
  mitigates it; base `Apex` does not.
- Full-cycle results are **thin/noise-sensitive** (near break-even); recent-regime results
  (Sharpe 1.5+) are robust. Validate on the exchange you trade before trusting a few points.
- **Re-validate on fresh data and paper-trade before going live** — see `docs/BOT_ROADMAP.md`.

---

## Repository layout

```
run_backtest.py                Offline Freqtrade runner (stubs exchange metadata; no network)
run_backtest_fut.py            Same, for futures-mode strategy tests
build_fut2.py                  Build dummy-funding futures data from spot feathers
convert_data.py / download_data.sh   Build/fetch OHLCV feathers
setup.sh                       One-command VPS install (venv, deps, systemd dry-run)
user_data/
  config.json                  Canonical backtest config: BTC/ETH/SOL, Apex, spot 1h
  config_dryrun.json           Base-Apex dry-run (Bybit, Telegram)
  config_dryrun_robust.json    Apex_Robust dry-run (Bybit, headless, separate DB)
  config_research.json         Bybit 22-coin universe (VPS research)
  strategies/
    Apex.py                    the strategy (default)
    Apex_Robust.py             validated improvement (rising-SMA regime gate)
    Apex_Ito.py, Apex_VolSize.py   rejected research variants (documented negatives)
  strategies_uploaded/         external strategies tested (all lost except SHM; unverified)
  data/binance/                BTC/ETH/SOL 1h + 4h OHLCV feathers
tools/                         signal_check, compare_dryruns, validate_robust_bybit, pair scans
deploy/                        systemd + Docker + enable_webui.sh (FreqUI dashboard)
docs/                          STRATEGY.md, EXPERIMENTS.md, DRYRUN.md, BOT_ROADMAP.md, ...
archive/                       Full research history (108-strategy tournament, futures, Vibe)
```

## Quick start

```bash
python -m venv .venv && . .venv/bin/activate
pip install freqtrade==2026.6 TA-Lib technical scipy finta ft-pandas-ta   # scipy is required

# Backtest Apex on BTC/ETH/SOL, last 4 years
python run_backtest.py backtesting --config user_data/config.json \
  --timerange 20220805-20260805 --timeframe 1h --cache none
# variant: --strategy Apex_Robust --strategy-path user_data/strategies
```

`run_backtest.py` feeds Freqtrade static exchange metadata so it runs fully offline; OHLCV
data, indicators, entries/exits and accounting are 100% real Freqtrade.

## How this strategy was chosen

`Apex` is the result of extensive, documented research — a 108-strategy tournament,
lookahead-bias filtering, hyperopt with out-of-sample validation, long/short + leverage
experiments, a Vibe-Trading integration, and (this session) 8+ external/indicator strategies
and 4 Apex modifications. The consistent finding:

- Most public "winners" were **lookahead-bias artifacts**; a re-hyperopt **overfit**
  (+643% in-sample → −39% OOS); leverage/shorting/ML **increased risk without reward**;
  indicator/level mean-reversion has **no mechanical edge** on these coins at any timeframe.
- **Sophistication consistently hurt Apex**; the only win was one simple structural filter
  (`Apex_Robust`). The alpha is the trailing-stop exit + rare high-conviction dip entries.

The full story, data, and every experiment live in `archive/` and `docs/EXPERIMENTS.md`.
