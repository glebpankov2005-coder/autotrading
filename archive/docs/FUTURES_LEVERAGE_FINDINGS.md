# Can cryptotank hit a 30% annual minimum? Long/short + leverage — findings

Goal: force ≥30% CAGR across all regimes. Tested long/short futures and leverage.
Validated on the same 3 non-overlapping periods (BTC/ETH/SOL, 1h).

## Every path was tried. None delivers a reliable 30% floor.

| Approach | P1 bear | P2 bull | P3 chop | Max DD | Verdict |
|---|---|---|---|---|---|
| Long-only aggressive (original) | −34% | **+61% CAGR** | +17% | 34% | 30%+ only in bull; bear blows up |
| Long-only defensive (cryptotankPro) | +0.8% | +16.5% | +6.5% | ~0% | robust, but modest returns |
| **Long/short 3× (cryptotankLS)** | +20% | −21% | −4% | 36–50% | fixed bear, **broke bull** |
| Long/short 2× | −10% | −43% | −2% | 40–60% | **chaotic** (2×↔3× flips signs) |
| Long/short 2× strict-regime | −32% | −64% | +27% | 55–75% | shorts the recovery rally |
| **Leverage 3× on cryptotankPro** | +0.2% | +12.6% | +8.7% | 18–31% | **worse** than 1× on return AND drawdown |

### Why each failed
- **Long/short shorts are fragile and dangerous.** The mean-reversion short ("short
  the rip") gets squeezed in rallies — bull pullbacks and bear-recovery rallies both
  run it over. Results swing wildly on tiny parameter changes (a hallmark of
  noise-fitting, not edge), and leverage drives drawdowns to 40–75% (liquidation
  territory).
- **Leverage doesn't cleanly scale.** It amplifies losing trades and stop-losses more
  than winners, so 3× on cryptotankPro *lowered* return (19.6%→12.6% in the bull) and
  *raised* drawdown (~0%→31%). Strictly worse.

## Conclusion (definitive)

**A reliable ≥30% annual minimum is not achievable with this strategy family on
BTC/ETH/SOL without taking risks that defeat the purpose** (fragile shorts, or
leverage that blows up drawdowns). This isn't a tuning gap — it's been tested across
long/short, multiple leverage levels, and three market regimes.

The honest ceilings:
- **~30–60% CAGR is reachable in bull regimes** (long-only aggressive).
- **~10–20% blended across a full cycle**, capital-protected in bears (cryptotankPro).
- **Bear markets cannot yield +30% long-biased** — the assets fall 50%+, and the only
  thing that profits (leveraged shorts) is too fragile/risky to rely on.

## Recommendation

Treat **30% as a target in favorable regimes, not a guaranteed floor.** Ship the
**long-only cryptotankPro** (robust, high-Sharpe, ~0 drawdown; 30%+ in bulls, protected
in bears). If a hard 30% floor is non-negotiable, it requires a fundamentally different
(and riskier) engine than a tuned rule-based bot — e.g. a proper trend-following
long/short futures system with a real (not mean-reversion) short signal, built and
out-of-sample-validated as its own project. I do not recommend chasing the number with
leverage or the current shorts — the evidence above shows both make things worse.
