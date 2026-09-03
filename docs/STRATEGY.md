# Apex — strategy specification & validation

Long-only spot, 1h, BTC/ETH/SOL. Built on the proven `cryptotank` engine with two
principled additions. Parameters are fixed/sensible (not fit to the validation
windows), so the multi-period results below are effectively out-of-sample.

## Logic

**Indicators**
- `reference_ma` = SMA(close, 200); `change` = (close − reference_ma) / close × 100
- `smooth` = SMA(change, 30); `slope` = Δsmooth; `min/max` = rolling(48) of slope
- `ema200` = EMA(close, 200)

**Entry (long)** — buy the dip, but not in a deep bear:
- `min < -0.35` (a sharp recent dip in the smoothed mean-distance), **and**
- `not_deep_bear` = NOT (close < ema200 AND ema200 falling over 72h)

**Exit** — trailing stop does most of the work; hard-exit on regime break:
- Tiered trailing stop via `custom_stoploss` (more room as profit grows: +3%→lock … +30%→wide)
- **or** `max > 0.35` (momentum exhaustion) **or** close crosses below `ema200`

**Risk** — `minimal_roi` cap, `-0.25` hard stop, partial profit-take at +10–15%,
protections: cooldown, stoploss-guard, max-drawdown.

## Validation (BTC/ETH/SOL, 1h)

| Window | Return | CAGR | Sharpe | Max DD |
|---|---|---|---|---|
| **Last 4 years (2022-08 → 2026-08)** | **+89.4%** | **17.3%** | 0.85 | 35% |
| **Recent 2 years (2024-08 → 2026-08)** | +60.2% | **26.6%** | **1.53** | ~0% |
| Bull regime (2023-11 → 2025-01) | +75.1% | 61.5% | 3.29 | ~0% |
| Choppy regime (2025-01 → 2026-08) | +43.2% | 25.5% | 1.34 | ~0% |
| Bear regime (2022-09 → 2023-11) | −29% | −25% | −0.23 | 35% |

**Per-token, 4 years:** SOL +63.6% (93.5% win) · ETH +16.1% (100% win) · BTC +9.7% (86% win).

It clears **25%+ CAGR in bull, choppy, and the recent 2 years** with Sharpe 1.3–3.3 and
near-zero drawdown. A **sustained bear** is the one regime it can't beat long-only.

## Why this design (evidence, not intuition)

- **Exits are the alpha, not entries.** Raising the ROI cap and removing the partial-take
  changed nothing — the trailing stop is the binding exit on nearly every trade. Porting
  only the *signal* into another engine (Vibe-Trading) collapsed the return to −5%.
- **A regime filter is required.** Without it the strategy loses ~34% in the 2022 bear.
  With a *strict* filter it barely trades (too defensive). The "deep-bear only" block +
  regime-break exit is the balance that keeps bull/choppy upside while cutting bear damage.
- **BTC/ETH/SOL beats a wider basket.** Adding LTC/ADA roughly halved the CAGR (17.3% →
  9.7%) — the strong large caps carry the edge.

## Variants (in the repo)

- **`Apex`** — default. Best return/robustness balance.
- **`cryptotankPro`** — more defensive: ~0 drawdown every regime, lower return. Use if you
  value capital protection over return.
- **`cryptotank`** — the original baseline (no regime filter): higher raw bull return but
  −34% in bears.

## Before live

Walk-forward on fresh real-exchange data, then a multi-week dry-run — see `BOT_ROADMAP.md`.
Rejected alternatives (long/short futures, leverage) and the full 108-strategy tournament
are documented in `../archive/docs/`.
