# cryptotank → live trading bot: roadmap

A step-by-step path from the backtested `cryptotank` strategy to a live bot, ordered so you
never risk money on an unvalidated assumption. Each phase ends with a **GATE** — a pass/fail
check you must clear before spending effort (or capital) on the next phase.

> Reality check: cryptotank is a *defensive, high-win-rate* strategy. It beat a falling market
> over the last 2y (+38% vs −34%) but **trailed buy-and-hold over 4y** (+70% vs +92%), and its
> parameters are in-sample on proxy data. Phase 1 exists to find out whether the edge is real
> before you trust it.

---

## Phase 0 — Environment (your machine / a VPS, not this sandbox)

This sandbox blocks exchange APIs, so everything from here runs where you control it.

- [ ] Install freqtrade (Docker is easiest): follow https://www.freqtrade.io/en/stable/docker_quickstart/
- [ ] Copy `user_data/strategies/cryptotank.py` into your freqtrade `user_data/strategies/`.
- [ ] `freqtrade download-data` for real Binance data (replaces the proxy data used here):
  ```bash
  freqtrade download-data --exchange binance \
    --pairs BTC/USDT ETH/USDT SOL/USDT \
    --timeframes 1h 4h --timerange 20220101-
  ```
- [ ] Re-run the backtest on this **real** data and confirm it roughly matches what we saw
  (fills/spreads will differ from the Bitstamp/uploaded proxy).

**GATE 0:** backtest on real Binance data is in the same ballpark (~+70% / 4y, DD ~34%). If it's
wildly different, the proxy data was misleading — stop and investigate before continuing.

---

## Phase 1 — Validate the edge (the make-or-break phase)

The backtest number means nothing until it survives data the parameters never saw.

- [ ] **Walk-forward / out-of-sample split.** Look at / tune on the first 3 years, then test
  *untouched* on the last year:
  ```bash
  freqtrade backtesting --strategy cryptotank --timeframe 1h \
    --timerange 20250804-20260804 --config config.json   # held-out final year only
  ```
- [ ] **Re-hyperopt on the training slice only**, then confirm on the held-out slice — never judge
  performance on the window you optimized:
  ```bash
  freqtrade hyperopt --strategy cryptotank --hyperopt-loss SharpeHyperOptLoss \
    --spaces buy sell protection --timerange 20220804-20250804 -e 300
  freqtrade backtesting --strategy cryptotank --timerange 20250804-20260804  # test with new params
  ```
- [ ] **Re-run the bias checks** on any re-optimized version:
  ```bash
  freqtrade lookahead-analysis --strategy cryptotank ...
  freqtrade recursive-analysis --strategy cryptotank ...
  ```

**GATE 1:** held-out year is still profitable (or at least beats holding on a risk-adjusted basis)
**and** clears the lookahead/repaint checks. If the edge only exists on the optimized window, it
was curve-fit — do **not** go live. Stop here.

---

## Phase 2 — Paper trade (dry-run). The step that kills most "great" backtests.

- [ ] Production config with `dry_run: true`, `dry_run_wallet` set to your intended real size.
  Key sections to get right for cryptotank specifically:
  - `max_open_trades`, `stake_amount`, `tradable_balance_ratio`
  - **protections** (cooldown, stoploss-guard, max-drawdown) — cryptotank defines several
  - **`position_adjustment_enable: true`** — cryptotank uses DCA/position adjustment; make sure
    stake sizing accounts for it
  - `entry_pricing` / `exit_pricing` matched to how you expect real fills
- [ ] Deploy on a **VPS running 24/7** (a cheap Linux box; Docker + restart policy).
- [ ] Wire up **Telegram** (control + alerts) and **FreqUI** (dashboard).
- [ ] Run dry-run **4–8 weeks minimum** and compare live signals/fills to a backtest over the
  same dates — they should line up. Divergence = slippage, data, or timing problems to fix.

**GATE 2:** dry-run results track the backtest over the same period, with no execution surprises.
If live signals don't match the backtest, fix that before risking a cent.

---

## Phase 3 — Go live, small

- [ ] **Exchange API keys:** enable **trading only**, **disable withdrawals**, **IP-whitelist** the
  VPS. Store keys in env/secrets, never in git.
- [ ] Start with a **small wallet you can fully afford to lose.** `dry_run: false`.
- [ ] Hard risk limits: per-trade stake, `max_open_trades`, stoploss, and a **MaxDrawdown
  protection** as a kill-switch.
- [ ] Monitor daily for the first weeks; keep the dry-run running in parallel as a reference.

**GATE 3:** live results track your dry-run over a meaningful number of trades. Only then scale up
— gradually.

---

## Operations checklist (ongoing)

- [ ] Docker auto-restart + log rotation; alert if the bot process dies.
- [ ] Back up the sqlite trade DB (`tradesv3.sqlite`) regularly.
- [ ] Version-control config and strategy; keep secrets out of the repo.
- [ ] Watch for **exchange/pair changes** (delistings, fee changes) and **regime change** — a
  defensive strategy can bleed in a strong trending bull; know when to pause it.
- [ ] Periodically re-validate on fresh out-of-sample data; retire the strategy if the edge decays.

---

## Honest expectations

- cryptotank's demonstrated strength is **capital protection in down/choppy markets**, not beating
  a raging bull. Size and expectations should reflect that.
- One strategy on three pairs is concentrated. Consider running it alongside uncorrelated
  strategies rather than all-in on one.
- Past backtest performance — even bias-checked — is not a promise. Phases 1–2 are how you convert
  "looks good" into "trust it with real money."
```
