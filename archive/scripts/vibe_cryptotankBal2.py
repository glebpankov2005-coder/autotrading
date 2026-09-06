"""Link cryptotankBal2 with Vibe-Trading and backtest the last 4 years.

Ports cryptotankBal2's entry/exit signal into a Vibe-Trading SignalEngine and runs
it through Vibe's CryptoEngine on our BTC/ETH/SOL 1h data (2022-08..2026-08),
offline, no API key.

Note: this ports the SIGNAL (slope-dip entry gated by a deep-bear filter; exit on
slope-rip or a close below the 200-EMA). Freqtrade's tiered trailing stop / ROI /
DCA execution is NOT modelled here -- Vibe executes the state signal under its own
engine, so numbers differ from the freqtrade backtest. Purpose: run Bal2 inside Vibe.

Run with the vibe venv:
  scratchpad/vt_venv/bin/python vibe_cryptotankBal2.py
"""
from pathlib import Path
import tempfile
import pandas as pd

from backtest.engines.crypto import CryptoEngine

DATA = Path("/home/user/autotrading/user_data/data_top7/binance")
CODES = ["BTC-USDT", "ETH-USDT", "SOL-USDT"]
START, END = "2022-08-05", "2026-08-05"

# cryptotankBal2 defaults
REF_MA, SMOOTH, MAXLEN = 200, 30, 48
BUY_SLOPE, SELL_SLOPE = -0.35, 0.35
EMA_LEN, BEAR_SHIFT = 200, 72


class LocalLoader:
    def fetch(self, codes, start_date, end_date, fields=None, interval="1h"):
        out = {}
        for c in codes:
            df = pd.read_feather(DATA / f"{c.replace('-', '_')}-1h.feather").set_index("date")
            df.index = df.index.tz_convert("UTC").tz_localize(None).as_unit("ns")
            df = df[(df.index >= pd.Timestamp(start_date)) & (df.index <= pd.Timestamp(end_date))]
            out[c] = df[["open", "high", "low", "close", "volume"]]
        return out


class Bal2Signal:
    """cryptotankBal2 entry/exit -> Vibe target-state signal (1=long, 0=flat)."""

    def generate(self, data_map):
        sig = {}
        for code, df in data_map.items():
            close, vol = df["close"], df["volume"]
            ref = close.rolling(REF_MA).mean()
            change = (close - ref) / close * 100.0
            smooth = change.rolling(SMOOTH).mean()
            slope = smooth.diff()                              # pandas_ta slope(length=1)
            mn = slope.rolling(MAXLEN).min()
            mx = slope.rolling(MAXLEN).max()
            ema = close.ewm(span=EMA_LEN, adjust=False).mean()
            not_deep_bear = ~((close < ema) & (ema < ema.shift(BEAR_SHIFT)))
            crossed_below = (close < ema) & (close.shift(1) >= ema.shift(1))

            entry = (mn < BUY_SLOPE) & not_deep_bear & (vol > 0)
            exit_ = (((mx > SELL_SLOPE) | crossed_below) & (vol > 0))

            state = pd.Series(float("nan"), index=df.index)
            state[entry] = 1.0
            state[exit_] = 0.0                                 # exit overrides entry on the same bar
            sig[code] = state.ffill().fillna(0.0)
        return sig


def main():
    config = {
        "codes": CODES, "interval": "1h", "start_date": START, "end_date": END,
        "initial_cash": 10_000, "leverage": 1.0,
        "maker_rate": 0.001, "taker_rate": 0.001, "slippage": 0.0, "funding_rate": 0.0,
    }
    engine = CryptoEngine(config)
    run_dir = Path(tempfile.mkdtemp(prefix="vibe_bal2_"))
    m = engine.run_backtest(config, LocalLoader(), Bal2Signal(), run_dir, bars_per_year=24 * 365)

    print("\n=== cryptotankBal2 inside Vibe-Trading (CryptoEngine, BTC/ETH/SOL, 2022-08..2026-08) ===")
    for k in ("total_return", "annual_return", "sharpe", "sortino", "max_drawdown",
              "win_rate", "profit_factor", "trade_count", "benchmark_return"):
        if k in m:
            print(f"  {k:16s} {m[k]}")


if __name__ == "__main__":
    main()
