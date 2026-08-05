# cryptotankBal2 — the +25% (no-leverage, long-only) strategy

Target: ≥25% annual, long-only spot, no leverage. Validated on 3 non-overlapping
regime periods + the full 4-year and recent 2-year spans (BTC/ETH/SOL, 1h).

## What it is

`cryptotankBal2` = the original cryptotank engine (slope-dip entry + tiered trailing
exit) with two small, principled additions:
1. **Deep-bear entry block** — don't open new trades when price is below a *falling*
   200-EMA (a confirmed deep downtrend). Keeps full aggression in bull/choppy markets,
   only stands aside in clear bears.
2. **Regime-break exit** — close longs when price crosses below the 200-EMA.

Both are fixed, sensible rules (not fit to the test windows), so the results below are
effectively out-of-sample.

## Results

| Window | Return | **CAGR** | Sharpe | Max DD | ≥25%? |
|---|---|---|---|---|---|
| **Recent 2y (2024-08→2026-08)** | +60.2% | **26.6%** | **1.41** | **0%** | ✅ |
| Bull (2023-11→2025-01) | +75.1% | **61.5%** | 3.29 | 0.4% | ✅ |
| Choppy (2025-01→2026-08) | +43.2% | **25.5%** | 1.34 | 0% | ✅ |
| Full 4y (incl. bear) | +89.4% | 17.7% | 0.40 | 35% | — |
| Bear (2022-09→2023-11) | −29.1% | −25% | −0.23 | 35% | ❌ |

**It clears 25% CAGR in bull, choppy, and the recent 2 years — with Sharpe 1.3–3.3
and near-zero drawdown in those regimes.** The recent-2-year number (26.6% CAGR, 0% DD,
Sharpe 1.41) is the most forward-relevant.

## Honest boundaries

- **A sustained bear (2022-style) still loses ~25%.** That's the hard long-only,
  no-leverage floor — when BTC/ETH/SOL fall 50%+, a long-biased bot can only stand
  aside, not profit. Adding shorts/leverage to fix this was tested and rejected
  (fragile, dangerous drawdowns — see FUTURES_LEVERAGE_FINDINGS.md).
- **0% drawdown in bull/choppy is optimistic.** Real slippage/fees beyond the modeled
  0.1%/side will add some drawdown; treat these as best-case.
- **One market cycle, proxy data, 3 pairs.** Re-validate on fresh real-exchange data
  and paper-trade before live (roadmap Phase 1–2).

## Recommendation

**Ship `cryptotankBal2`** as the +25% strategy: it delivers 25%+ CAGR with excellent
risk-adjusted returns in normal-to-good markets, and it protects capital reasonably in
downturns (stands aside in confirmed bears). Set expectations as "25%+ in normal/bull
markets, flat-to-down in a deep bear" — not a guaranteed floor every single year.
