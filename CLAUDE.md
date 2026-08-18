# CLAUDE.md — project memory

Read this first. It captures what this repo is, the key decisions, and where things live,
so a fresh session can continue seamlessly.

## What this project is
A Freqtrade crypto trading bot. The headline strategy is **`Apex`** (formerly
`cryptotankBal2`): a regime-aware dip-buyer with a tiered trailing-stop exit — long-only
spot, 1h, BTC/ETH/SOL. There is also a validated variant **`Apex_Robust`** (see below).

**Live status:** both strategies run 24/7 as **paper dry-runs on the user's Hetzner VPS**
(`46.225.135.31`, `/opt/apex-trading-bot`), trading **Bybit** (spot, no keys, no real money)
in a parallel A/B. A **FreqUI web dashboard** is enabled on both (ports 8080 / 8081).

**Apex validated results:**
- On **Binance** data (our historical feathers): +89.4% over 4y (17.3% CAGR, Sharpe 0.85,
  PF 2.83); +60% / Sharpe 1.53 / ~0% DD over recent 2y.
- On **Bybit** data (the exchange it actually trades): recent-2y +66.6% / Sharpe 1.14 /
  17% DD; **full cycle incl. 2022 crash −13.2% / 60% DD** ← the real weakness.
- Honest limit: long-only, no leverage → a sustained bear loses. Details in `docs/STRATEGY.md`.

## Repo layout
- `user_data/strategies/Apex.py` — the base strategy (default in `config.json`).
- `user_data/strategies/Apex_Robust.py` — **validated improvement** (regime gate; see below).
- `user_data/strategies/Apex_Ito.py`, `Apex_VolSize.py` — **rejected** research variants
  (financial-calculus experiments; documented negative results, kept for the record).
- `user_data/config.json` — canonical backtest config: BTC/ETH/SOL spot, 1h, `strategy: Apex`.
- `user_data/config_dryrun.json` — base-Apex dry-run (Bybit, Telegram on).
- `user_data/config_dryrun_robust.json` — Apex_Robust dry-run (Bybit, headless, separate DB).
- `user_data/config_research.json` — Bybit spot, 22-coin universe (used on the VPS).
- `user_data/data/binance/` — BTC/ETH/SOL 1h+4h feathers (the committed data).
- `run_backtest.py` — offline Freqtrade runner (stubs Binance metadata; no network).
  `run_backtest_fut.py` + `build_fut2.py` — futures-mode stub + data builder.
- `tools/` — research/ops scripts (see "Tooling" below).
- `deploy/` — systemd + Docker + `enable_webui.sh` (turns on FreqUI on both bots).
- `docs/` — `STRATEGY.md`, `EXPERIMENTS.md` (this session's full record), `BOT_ROADMAP.md`,
  `DRYRUN.md`, `UPLOADED_STRATEGIES_RESULTS.md`.
- `user_data/strategies_uploaded/` — external strategies tested (all lost except SHM; unverified).
- `archive/` — full research history (108-strategy tournament, futures/leverage, Vibe).

## Run (backtest in the sandbox)
```bash
python -m venv .venv && . .venv/bin/activate
pip install freqtrade==2026.6 TA-Lib technical scipy finta ft-pandas-ta   # scipy is REQUIRED
python run_backtest.py backtesting --config user_data/config.json \
  --timerange 20220805-20260805 --timeframe 1h --cache none
# variants: --strategy Apex_Robust --strategy-path user_data/strategies
```

## Hard environment constraints (important)
- **Exchange/data APIs are blocked** in the Claude sandbox (Binance, Bybit, data.binance.vision
  all return 000). Only **GitHub-raw and PyPI** are reachable. Fresh market data → user uploads
  CSVs (`datetime,O,H,L,C,V`), or download it **on the VPS** (which reaches Bybit).
- The **venv is ephemeral** — reclaimed between idle periods; rebuild with the pip line above.
  **`scipy` must be installed explicitly** or freqtrade import fails (`No module named 'scipy'`).
- Live dry-run / trading runs on the user's VPS (needs exchange access). The sandbox cannot
  reach the VPS (no SSH); the user runs server commands, Claude interprets output.
- **Exchange = Bybit** (user's account is Bybit-only). Configs switched from Binance to Bybit.

## Key decisions & findings (so we don't relitigate)
- **Apex is the chosen strategy.** Beat a 108-strategy tournament; most public "winners" were
  lookahead-bias artifacts; a re-hyperopt overfit (+643% in-sample → −39% OOS); long/short +
  leverage tested and rejected as fragile/dangerous.
- **The alpha is the tiered trailing-stop EXIT, not the entry.** Every attempt to change the
  exit degrades it (Vibe port → −5%; close-confirmed exit → +60%→+12%). Do not touch the exit.
- **Apex's returns are concentrated in SOL** (~70% of profit) because SOL is the most volatile
  coin → most/deepest dips. Apex *harvests volatility*; volatility = opportunity here, not risk.
- **Full-cycle fragility:** over a complete cycle Apex sits near break-even (Sharpe ~0.4), so
  its result is noise-sensitive. Binance vs Bybit swings it +40% → −13% on the same window —
  NOT config/warmup (proven), purely the exchanges' slightly-different candles. A 0.15%-noise
  jitter alone swings the full cycle +15%→+42%. The recent-regime numbers (Sharpe 1.5+) are far
  from break-even and robust; the full-cycle numbers are thin/fragile.

## Apex_Robust — the one validated improvement (this session)
Same engine + **one change: only buy when BTC's 200-SMA is RISING** (macro uptrend,
lookahead-safe). Sits out confirmed bears, still buys healthy pullbacks.
- **Bybit full cycle: −13% → +25%, drawdown 60% → 28%.** Recent windows give up ~half the
  bull upside (2y +29% vs +67%) — it's the "sleep at night / survive a 2022" version.
- Validated: lookahead-clean (no bias), parameter-robust (+39% to +96% across SMA 150–250 ×
  rising-window 24–72 — not a knife-edge), consistent by sub-period (much better in 2022/2023).
- **Now running in the live A/B vs base Apex.** Decision (aggressive vs robust) deferred to
  real paper results.

## What did NOT improve Apex (tested & rejected this session — don't retry)
- **Close-confirmed exit** → guts the alpha (+60%→+12%). The intrabar trail IS the edge.
- **"BTC > 200-SMA" gate** (vs the rising-SMA one) → cuts the dip-buys, more fragile.
- **Itô / quadratic-variation realized-vol filter** (`Apex_Ito.py`) → worse (fights the alpha:
  Apex wants to buy vol spikes = capitulation dips).
- **Volatility-targeted position sizing** (`Apex_VolSize.py`) → lowers Sharpe in every window
  (down-sizes SOL, the high-vol coin that is the alpha).
- **Pattern:** sophistication consistently hurts Apex; the only win was one simple structural
  filter. More coins also hurt (crypto correlations → 1 in crashes); see `docs/EXPERIMENTS.md`.

## External strategies tested this session (all in `strategies_uploaded/`)
AlexDivergenceV6 −64%, ANF_v2 −85% floor, LiquiditySweep (BigBeluga) no-edge,
AdaptiveTrendTrail (Uptrick) −29%→−56%, OrderFlowProfile (Zeiierman) −21%→−69%.
**Only SHM_RSIMomentum showed a plausible edge** (+28.5% full cycle / 16% DD, low-win trend
follower) — but it is **unverified** (needs Bybit re-run + lookahead-analysis). Full table in
`docs/UPLOADED_STRATEGIES_RESULTS.md` and `docs/EXPERIMENTS.md`.

## Tooling (`tools/`)
- `signal_check.py` — live Bybit check: how close each pair is to an Apex entry.
- `test_pairs.py` / `portfolio_test.py` — multi-coin universe scans (run on VPS).
- `apex_windows.sh` — Apex on Bybit across windows.
- `validate_robust_bybit.sh` — base Apex vs Apex_Robust on Bybit (the A/B validation).
- `compare_dryruns.py` — reads both dry-run sqlite DBs, prints the live A/B scoreboard.
- `test_alexdiv.sh` — native 15m futures backtest + lookahead for an external strategy.

## Deployment (on the VPS)
- `deploy/setup.sh` — one-command install (venv, deps, systemd `apex-dryrun`, start).
- Second bot: systemd `apex-robust-dryrun` (Apex_Robust, separate DB `dryrun_robust.sqlite`).
- `deploy/enable_webui.sh` — turns on FreqUI on both (ports 8080/8081, one login).
- Compare: `.venv/bin/python tools/compare_dryruns.py`.

## Conventions
- Work on branch `claude/github-skills-setup-7o4x3z`; commit + push when changes are done.
- GitHub repo: `glebpankov2005-coder/autotrading` (user may rename to `apex-trading-bot`;
  do it in GitHub Settings + `git remote set-url`, can't be done from the sandbox).

## Open / next steps
- **Let the live A/B run** (weeks) — real Bybit paper data decides Apex vs Apex_Robust. Check
  via `compare_dryruns.py` or FreqUI. Both are patient; expect few early trades.
- If curious about SHM_RSIMomentum: run its Bybit + lookahead verification before trusting it.
- Before real money: a few weeks of clean dry-run, then small live size (`BOT_ROADMAP.md`).
