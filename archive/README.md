# archive — research history

Everything here documents how `cryptotankBal2` was chosen. Kept for transparency and
reproducibility; none of it is needed to run the strategy.

- **strategies/** — every experimental variant (long/short futures `cryptotankLS`,
  leveraged `cryptotankProL`, overfit `cryptotankHO`, timeframe-scaled `cryptotankTF`,
  the 108-strategy tournament's `Candle2`, and the intermediate `cryptotankBal`, `V2`,
  `Pro2`, `Agg`, `Max`).
- **scripts/** — one-off tooling: the 108-strategy tournament (`tourney.py`), lookahead/
  repaint bias checks (`repaint_test.py`), multi-period validation (`validate_periods.py`),
  timeframe & leverage sweeps, futures runner, data converters, and the Vibe-Trading
  integration (`vibe_*.py`).
- **configs/** — per-experiment Freqtrade configs (2y/4y/intraday/futures/top6/top7/…).
- **docs/** — detailed findings: the tournament results, high-Sharpe write-up, the
  return-ceiling / futures-and-leverage analysis, and earlier RESULTS.
