# Experiments & findings — August 2026 session

Full record of the improvement work and strategy testing done this session, so nothing gets
re-derived or relitigated. Companion to `STRATEGY.md` (Apex spec) and
`UPLOADED_STRATEGIES_RESULTS.md` (external-strategy table).

## TL;DR
- Built and **validated `Apex_Robust`** — the one genuine improvement (regime gate).
- Proved Apex's headline numbers are **regime- and data-fragile** over full cycles.
- **Switched the live bots to Bybit** and stood up a **parallel A/B dry-run** (base vs Robust)
  with a **FreqUI** dashboard.
- Tested 6 external strategies (5 losers, 1 unverified maybe) and 4 Apex modifications
  (1 win, 3 rejects). **Consistent lesson: sophistication hurts Apex; one simple filter helped.**

## 1. The fragility finding (why full-cycle numbers can't be trusted to a few points)
Apex over a full cycle sits near break-even (Sharpe ~0.4). Consequences, all measured:
- **Binance vs Bybit, same window/coins/config:** full cycle +40% vs −13%. Isolation tests
  proved it is **not** warmup/history (trimmed-Binance = full-Binance = +40.19%) and **not**
  config (order-book pricing on/off = identical). It is purely the exchanges' slightly-different
  candles deciding near-break-even trades.
- **0.15% random-noise jitter** on Binance candles swings the full cycle **+15% to +42%** across
  seeds. A thin edge gets decided by which wick tags which trailing stop.
- Implication: recent-regime numbers (Sharpe 1.5–1.9, far from break-even) are robust; full-cycle
  numbers are noisy. Validate on the exchange you trade (Bybit), and prefer a fatter-margin
  variant that doesn't flip sign on noise → motivates Apex_Robust.

## 2. Apex_Robust — the validated improvement ✅
Change: **only enter when BTC's 200-SMA is rising** (macro uptrend), lookahead-safe (`.shift(1)`
on a BTC informative). Everything else identical (exit untouched — it's the alpha).

Why the *rising* SMA and not "price > SMA": dips happen when price is *below* its MA, so a
"price > SMA" gate cut the best buys and made things worse. "SMA rising" allows healthy
pullbacks while blocking only confirmed bears (SMA falling).

Validation gauntlet — all passed:
| Test | Result |
|---|---|
| Bybit full cycle | **−13% → +25%**, drawdown **60% → 28%** |
| Bybit recent 2y | +29% (vs base +67%) — gives up ~half the bull upside |
| Parameter sweep (Binance full) | **+39% to +96%** across SMA 150–250 × window 24–72 (not a knife-edge) |
| Sub-periods | 2022 −12% (vs −33%), 2023 +21% (vs −13%), 2024/25 lower — sensible & consistent |
| Lookahead-analysis | **No bias** (0 biased signals/indicators) |
| Noise floor (0.15%) | **+13.7%** worst seed (base flipped to −13% on Bybit) |

Character: the "survive a 2022 / sleep at night" version. Lower bull upside, far lower crash
drawdown, positive across full cycles, less data-sensitive. **Now running live vs base Apex.**

## 3. Apex modifications that were REJECTED (don't retry)
| Variant | Idea | Result | Why it failed |
|---|---|---|---|
| Close-confirmed exit | exit on candle close, not intrabar wick | +60% → **+12%** | The intrabar tiered trail *is* the alpha; close-basing gives back winners |
| `BTC > 200-SMA` gate | only buy above BTC's MA | +40% → **+0.1%**, more fragile | Dips happen *below* the MA — cuts the best buys |
| `Apex_Ito` — QV vol filter | skip entries in top-5% realized vol (Itô quadratic variation) | full +14.6% vs +40.2%, higher DD | Apex *wants* vol spikes (capitulation dips); filter fights the alpha |
| `Apex_VolSize` — vol-targeted sizing | size ∝ 1/σ (risk parity) | **lower Sharpe every window** (0.34 vs 0.43 full) | Down-sizes SOL, the high-vol coin that generates ~70% of profit |

Meta-lesson: for a **volatility-harvesting dip-buyer**, "volatility = risk, reduce it" is
backwards — volatility = opportunity. Standard quant machinery fights Apex's concentrated-in-SOL
edge. The only thing that helped was one simple structural regime filter.

## 4. "More coins" was also rejected
Full-window portfolio test (Bybit, incl. 2022): baseline BTC/ETH/SOL −13% / 60% DD; adding 8
candidates → −80%; full 22-coin universe → −93%. In a crash crypto correlations → 1, so more
coins = more simultaneous falling-knife buys. **3 coins is the ceiling.** (`tools/portfolio_test.py`)

Per-coin scan (`tools/test_pairs.py`) over the full window showed nearly all alts negative/
break-even with 40–60% drawdowns — Apex's edge is not portable to arbitrary coins.

## 5. External strategies tested (all in `strategies_uploaded/`)
| Strategy | Type | Result | Verdict |
|---|---|---|---|
| AlexDivergenceV6 | 15m futures 5× divergence | −64% (6mo, BTC) while BTC +14.6% | reject (fee-shredder) |
| ANF_v2 | 1h futures ML/HMM | −85% floor (ML unbackestable by design) | reject |
| LiquiditySweep (BigBeluga) | indicator, no signals | no edge (−2% to −79% across configs) | reject |
| AdaptiveTrendTrail (Uptrick) | 1h futures L/S trend | −29% to −56% | reject (whipsawed by chop) |
| OrderFlowProfile (Zeiierman) | indicator, no signals | −21% to −69% (high churn) | reject |
| **SHM_RSIMomentum** | 4h L/S, daily-RSI gate + macro tide | **+28.5% full cycle / 16% DD** (low-win trend) | **unverified maybe** — needs Bybit + lookahead |

Recurring themes: indicators are not strategies (you must invent rules, which then have no edge);
leverage/shorts/ML consistently blow up on these coins; the market's chop-with-upward-drift
rewards exactly Apex's shape (long-only, buy dips, sit out crashes, never short).

## 6. Deployment done this session
- Switched configs from Binance → **Bybit** (user's exchange).
- VPS (Hetzner `46.225.135.31`, `/opt/apex-trading-bot`): `deploy/setup.sh` installed base
  `apex-dryrun`; added `apex-robust-dryrun` (separate DB) for the A/B.
- `deploy/enable_webui.sh` → **FreqUI** on ports 8080 (base) / 8081 (Robust), single login.
- `tools/compare_dryruns.py` → live scoreboard from both sqlite DBs.

## 7. What's genuinely open
- **Let the A/B run** — real Bybit paper data decides aggressive (base) vs robust. Nothing more
  to backtest for that question.
- **SHM verification** — the only external strategy worth a second look; run Bybit + lookahead.
- Stop porting indicators / adding math to Apex — the record is conclusive that it doesn't help.
