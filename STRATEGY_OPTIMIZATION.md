# cryptotank — improvement attempts, OOS validation, and Vibe-Trading port

Everything here was measured, not assumed. Baseline = original `cryptotank`, 4y
(2022-08→2026-08), BTC/ETH/SOL, freqtrade.

## 1. Structural "improvements" (all tested on 4y, isolated one at a time)

| Change | Result vs baseline (+70%, DD 34%, Sharpe 0.23) | Verdict |
|---|---|---|
| Rewrite `custom_stoploss` as a clean `stoploss_from_open` ratchet | +70% → **−5.5%** | ❌ the original stoploss is load-bearing; reverted |
| **Trend filter** (buy dips only above the long MA) — `cryptotankV2` | +38%, **DD 17%**, **PF 1.93**, win 93% | ⚖️ lower return, half the drawdown |
| Milder "MA-rising" filter | +29%, DD 37% | ❌ worse on both |

**Takeaway:** the original is well-tuned. Naive structural changes trade return
for risk; none beat it on Sharpe. `cryptotankV2` is a legitimate *lower-risk*
variant if you value drawdown over peak return.

## 2. Hyperopt + out-of-sample validation (the decisive test)

Re-optimized a copy (`cryptotankHO`, corrected parameter ranges) with SharpeHyperOptLoss,
**training on 2020→2024**, then tested **on the untouched last 2 years (2024-08→2026-08)**.

| | In-sample (train, 2020–2024) | **Out-of-sample (2024–2026, unseen)** |
|---|---|---|
| **cryptotank** (original params) | — | **+50.5%** · Sharpe 0.33 · PF 1.65 · DD 24.7% · 113 tr · 88.5% win |
| **cryptotankHO** (hyperopted) | **+643%** 🤩 | **−38.9%** 💀 · Sharpe −0.28 · PF 0.84 · DD 62% · 195 tr |

**This is textbook overfitting.** The hyperopt found params that scored +643% on
the training window and **−38.9% on unseen data**. The original, un-optimized
params **generalize** (+50.5% OOS). 

**Verdict: keep the original (first) cryptotank.** Do NOT ship the hyperopted
version — it curve-fit the past. This is exactly why OOS validation (roadmap
Phase 1) exists.

## 3. Uniting cryptotank with Vibe-Trading

`vibe_cryptotank.py` ports the original cryptotank entry/exit into a Vibe-Trading
`SignalEngine` and runs it through Vibe's `CryptoEngine` on our data (offline, no
API key). Two integration fixes were needed: Vibe's `_align` assumes **ns-resolution,
tz-naive** date indexes.

| | freqtrade (native) | Vibe port (signal only) |
|---|---|---|
| 4y return | +70% | −7.2% |
| Avg hold | days–weeks | 573 days |

Vibe executes a target **state**, so the pure signal (no trailing-stop/ROI/DCA)
holds positions for ~1.5 years and the edge disappears. **Confirms again that
cryptotank's alpha is in its exit mechanics, not the entry signal.** To reproduce
native performance in Vibe you must model the trailing-stop/ROI in the engine,
not just emit the entry/exit signal.

## Bottom line
- **Ship the original `cryptotank`** — it's the only version that holds up out-of-sample.
- `cryptotankV2` is a fine *lower-drawdown* alternative if you prefer safety over return.
- Hyperopted params overfit — discard.
- Vibe-Trading is a great *research/analysis* layer, but running cryptotank there
  faithfully requires porting its exit logic, not just the signal.
