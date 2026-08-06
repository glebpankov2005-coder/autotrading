# CLAUDE.md — project memory

Read this first. It captures what this repo is, the key decisions, and where things live,
so a fresh session can continue seamlessly.

## What this project is
A Freqtrade crypto trading bot. The headline strategy is **`Apex`** (formerly
`cryptotankBal2`): a regime-aware dip-buyer with a tiered trailing-stop exit — long-only
spot, 1h, BTC/ETH/SOL.

**Apex validated result (BTC/ETH/SOL, 1h):** +89.4% over 4y (17.3% CAGR, Sharpe 0.85,
PF 2.83); +26.6% CAGR / Sharpe 1.53 / ~0% drawdown over the recent 2 years. Honest limit:
a sustained bear still loses (long-only, no leverage). Details in `docs/STRATEGY.md`.

## Repo layout
- `user_data/strategies/Apex.py` — the strategy (default). Also `cryptotankPro.py`
  (defensive, lower-return) and `cryptotank.py` (original baseline).
- `user_data/config.json` — canonical config: BTC/ETH/SOL spot, 1h, `strategy: Apex`.
- `user_data/data/binance/` — BTC/ETH/SOL 1h+4h feathers (the committed data).
- `run_backtest.py` — offline Freqtrade runner (stubs exchange metadata; no network).
- `docs/` — `STRATEGY.md` (spec+validation), `BOT_ROADMAP.md` (backtest→dry-run→live),
  `DRYRUN.md`, `UPLOADED_STRATEGIES_RESULTS.md` (community strategies, all lost).
- `deploy/` — systemd + Docker for 24/7 dry-run, DB backup, watchdog (Telegram alerts).
- `user_data/strategies_uploaded/` — community strategies that were tested (all negative).
- `archive/` — full research history (108-strategy tournament, futures/leverage, Vibe,
  intermediate variants). Historical; keeps the old `cryptotankBal2` name.

## Run
```bash
python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
python run_backtest.py backtesting --config user_data/config.json \
  --timerange 20220805-20260805 --timeframe 1h --cache none
```
Dry-run: `./start_dryrun.sh` (see `docs/DRYRUN.md`). Deploy: `deploy/README.md`.

## Hard environment constraints (important)
- **Exchange/data APIs are blocked** in the Claude sandbox (Binance, Yahoo, CryptoCompare,
  CoinGecko, Syve, etc. all fail). Only **GitHub-raw and PyPI** are reachable. Getting fresh
  market data requires the user to **upload CSVs** (format: `datetime,O,H,L,C,V`, tab or
  comma). We have BTC/ETH/SOL 1h (+ some 5m/15m uploads used for community-strategy tests).
- The **venv is ephemeral** — it gets reclaimed between idle periods; rebuild with
  `pip install freqtrade==2026.6 technical TA-Lib scipy finta` (add optuna/pandas_ta if a
  strategy needs them). Uploaded files in `/root/.claude/uploads/...` are also ephemeral.
- Live dry-run / trading must run on the user's own machine/VPS (needs Binance access).

## Key decisions & findings (so we don't relitigate)
- **Apex is the chosen strategy.** It beat a 108-strategy tournament; most public "winners"
  were lookahead-bias artifacts; a re-hyperopt overfit (+643% in-sample → −39% OOS);
  long/short + leverage were tested and rejected as fragile/dangerous.
- **The alpha is the trailing-stop EXIT, not the entry.** Porting only the signal elsewhere
  (Vibe-Trading) collapsed returns to −5%.
- **Community strategies uploaded for comparison all lost** at their native timeframes
  (−21% to −85%, big drawdowns) — see `docs/UPLOADED_STRATEGIES_RESULTS.md`. None beat Apex.
- **Vibe-Trading** is a research/agent layer (needs an LLM API key, blocked here), not a
  better executor. Keep Apex in Freqtrade.

## Conventions
- Work happens on branch `claude/github-skills-setup-7o4x3z`; commit + push when changes are
  done. Keep the root clean; put experiments in `archive/`.
- GitHub repo: `glebpankov2005-coder/autotrading` (user plans to rename to
  `apex-trading-bot`; can't be done from the sandbox — GitHub Settings + `git remote set-url`).

## Open / next steps
- Before real money: re-validate Apex on real Binance candles (`freqtrade download-data`),
  walk-forward, then a 4–8 week dry-run (`BOT_ROADMAP.md` Phases 1–3).
