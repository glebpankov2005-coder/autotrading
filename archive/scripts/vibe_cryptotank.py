"""Unite cryptotank with Vibe-Trading.

Ports the ORIGINAL (first) cryptotank entry/exit logic into a Vibe-Trading
SignalEngine and runs it through Vibe's own crypto backtest engine on our local
BTC/ETH/SOL 1h data -- fully offline, no API key.

Run with the vibe-trading venv:
  scratchpad/vt_venv/bin/python vibe_cryptotank.py

Note: this ports the SIGNAL logic (dip-buy on smoothed-MA-slope, exit on strong
up-slope). Freqtrade's trailing-stop / ROI / DCA execution layer is NOT modelled
here -- Vibe executes the state signal under its own engine. So numbers will
differ from the freqtrade backtest; the point is to run cryptotank inside Vibe.
"""
from pathlib import Path
import tempfile
import pandas as pd

from backtest.engines.crypto import CryptoEngine

DATA = Path("/home/user/autotrading/user_data/data_4y/binance")
CODES = ["BTC-USDT", "ETH-USDT", "SOL-USDT"]
START, END = "2022-08-04", "2026-08-04"

# --- cryptotank original defaults ---
REF_MA = 200        # reference_ma_length
SMOOTH = 30         # smoothing_length
MAXLEN = 48         # max_length (rolling window for min/max of slope)
BUY_SLOPE = -0.35   # buy_ma_slope  (enter when rolling-min slope < this)
SELL_SLOPE = 0.35   # sell_ma_slope (exit when rolling-max slope > this)


class LocalLoader:
    """Minimal loader: serves our committed feathers as {code: OHLCV df}."""

    def fetch(self, codes, start_date, end_date, fields=None, interval="1h"):
        out = {}
        for c in codes:
            fn = DATA / f"{c.replace('-', '_')}-1h.feather"
            df = pd.read_feather(fn)
            df = df.set_index("date")
            # Vibe's _align emits ns-resolution, tz-NAIVE dates; match that so
            # `ts in df.index` succeeds during execution.
            df.index = df.index.tz_convert("UTC").tz_localize(None).as_unit("ns")
            df = df[(df.index >= pd.Timestamp(start_date)) &
                    (df.index <= pd.Timestamp(end_date))]
            out[c] = df[["open", "high", "low", "close", "volume"]]
        return out


class CryptotankSignal:
    """Original cryptotank entry/exit as a Vibe target-state signal (1=long, 0=flat)."""

    def generate(self, data_map):
        signals = {}
        for code, df in data_map.items():
            close, vol = df["close"], df["volume"]
            ref = close.rolling(REF_MA).mean()
            change = (close - ref) / close * 100.0
            smooth = change.rolling(SMOOTH).mean()
            slope = smooth.diff()                      # pandas_ta slope(length=1) == first difference
            mn = slope.rolling(MAXLEN).min()
            mx = slope.rolling(MAXLEN).max()

            entry = (mn < BUY_SLOPE) & (vol > 0)
            exit_ = (mx > SELL_SLOPE) & (vol > 0)

            state = pd.Series(float("nan"), index=df.index)
            state[entry] = 1.0
            state[exit_] = 0.0                         # exit overrides entry on the same bar
            state = state.ffill().fillna(0.0)
            signals[code] = state
        return signals


def main():
    config = {
        "codes": CODES, "interval": "1h",
        "start_date": START, "end_date": END,
        "initial_cash": 10_000, "leverage": 1.0,
        "maker_rate": 0.001, "taker_rate": 0.001,   # ~freqtrade 0.1%/side
        "slippage": 0.0, "funding_rate": 0.0,        # approximate spot (cryptotank is spot)
    }
    engine = CryptoEngine(config)
    run_dir = Path(tempfile.mkdtemp(prefix="vibe_cryptotank_"))
    bars_per_year = 24 * 365
    metrics = engine.run_backtest(config, LocalLoader(), CryptotankSignal(),
                                  run_dir, bars_per_year=bars_per_year)

    keys = ["total_return", "annual_return", "cagr", "sharpe", "sortino",
            "max_drawdown", "win_rate", "profit_factor", "num_trades",
            "total_trades", "calmar", "volatility"]
    print("\n=== cryptotank inside Vibe-Trading (CryptoEngine, 3 pairs, 2022-08..2026-08) ===")
    for k in keys:
        if k in metrics:
            print(f"  {k:16s} {metrics[k]}")
    print(f"\n  (artifacts: {run_dir})")
    # also dump any drawdown/return-ish keys we didn't hardcode
    extra = {k: v for k, v in metrics.items()
             if isinstance(v, (int, float)) and k not in keys}
    if extra:
        print("  other numeric metrics:", {k: round(v, 4) for k, v in list(extra.items())[:20]})


if __name__ == "__main__":
    main()
