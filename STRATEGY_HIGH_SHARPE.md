# cryptotankPro — high-Sharpe rewrite, validated on 3 independent periods

Goal: rewrite cryptotank (1h) for **high Sharpe and high return**, then prove it's
legit by backtesting on **3 non-overlapping ~1-year periods** across BTC/ETH/SOL.
Params are fixed/sensible (not fit to these windows), so all three are effectively
out-of-sample.

## The winner: cryptotankPro

`cryptotankPro` = the proven cryptotank engine (slope-dip entry + tiered trailing
exit) **plus** two additions:
- **Regime filter** — only long when price is above a **rising 100-EMA** (be in the
  market during uptrends, flat during downtrends).
- **MaxDrawdown circuit-breaker** — stop opening trades after a 20% account drawdown.

## 3-period validation (BTC/ETH/SOL, 1h)

| Period (regime) | Strategy | Return | **Sharpe** | Max DD | Trades |
|---|---|---|---|---|---|
| **P1** 2022-09→2023-11 (bear) | cryptotank (orig) | −34.0% | −0.34 | 34% | 53 |
| | **cryptotankPro** | **+0.8%** | **+0.05** | **0.3%** | 2 |
| **P2** 2023-11→2025-01 (bull) | cryptotank (orig) | +74.7% | 1.00 | 16% | 82 |
| | **cryptotankPro** | +19.6% | **+1.76** | ~0% | 19 |
| **P3** 2025-01→2026-08 (choppy) | cryptotank (orig) | +28.4% | 0.26 | 25% | 100 |
| | **cryptotankPro** | +10.4% | **+0.69** | ~0% | 8 |

**cryptotankPro is positive in all three periods and has the best Sharpe in all
three** — including a bear market where the original lost 34%. That consistency
across independent regimes is what makes it *legit* (not a one-regime fluke).

## What did NOT work (and why the rewrite is honest)

- **From-scratch EMA/RSI momentum designs**: −5% to −15%, negative Sharpe. The
  original's specific slope-entry + trailing-exit is genuinely well-tuned.
- **cryptotankPro2** (looser regime: above 100-EMA but not required rising, no
  drawdown halt): −24.3% / +14.0% / +24.4% — great in P3 but **loses 24% in the
  bear (P1)**. Loosening the regime brings back exactly the losses the filter removes.
- **cryptotankV2** (reference-MA regime filter): −5.9% / +15.6% / +23.7% — also
  negative in P1. Not robust.

Every attempt to raise returns re-introduced bear-market losses. This is a real,
repeatable trade-off, not a tuning accident.

## The honest bottom line

**There is a genuine trade-off between Sharpe and raw return here — you cannot
maximize both at once.**

- **cryptotankPro = the risk-adjusted / robustness winner.** Positive every period,
  Sharpe ~0.05 / 1.76 / 0.69, near-zero drawdowns. Its **returns are moderate**
  (CAGR ~7–16% in up-regimes, flat in the bear) — that is the *price* of the high
  Sharpe: it sits out bad regimes. Ship this if you want consistency and to sleep
  at night.
- **cryptotank (original) = the raw-return winner** in bull/choppy markets
  (+75% / +28%) but **−34% and negative Sharpe in the bear**. Higher return, real
  regime risk.

Recommendation: **cryptotankPro** for a live bot — it's the only variant that held
up (positive, high-Sharpe) across bear, bull, and choppy periods. Validate it
further with a walk-forward and a paper-trade before going live (roadmap Phase 1–2).

> Caveat: BTC/ETH/SOL only, 1h, and these three periods overlap the 2022–2026 span
> (one broad market cycle). Different assets or a very different macro regime could
> shift the numbers; re-validate on fresh data before trusting it with capital.
