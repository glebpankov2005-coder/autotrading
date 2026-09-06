"""Backtest a VIBE-NATIVE strategy on our 4-year BTC/ETH/SOL data.

Uses Vibe-Trading's own bundled signal engine (technical-basic: a multi-indicator
trend + mean-reversion + volume voting model) and runs it through Vibe's CryptoEngine.
This is Vibe generating AND executing its own signal -- not a cryptotank port.
Offline, no API key.
"""
import importlib.util
from pathlib import Path
import tempfile
import site
import pandas as pd

from backtest.engines.crypto import CryptoEngine

DATA = Path("/home/user/autotrading/user_data/data_top7/binance")
CODES = ["BTC-USDT", "ETH-USDT", "SOL-USDT"]
START, END = "2022-08-05", "2026-08-05"

# locate the bundled technical-basic engine inside the installed package
SP = Path(site.getsitepackages()[0])
ENGINE_FILE = SP / "src/skills/technical-basic/example_signal_engine.py"


def load_engine():
    spec = importlib.util.spec_from_file_location("tb_engine", ENGINE_FILE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.SignalEngine()


class LocalLoader:
    def fetch(self, codes, start_date, end_date, fields=None, interval="1h"):
        out = {}
        for c in codes:
            df = pd.read_feather(DATA / f"{c.replace('-', '_')}-1h.feather").set_index("date")
            df.index = df.index.tz_convert("UTC").tz_localize(None).as_unit("ns")
            df = df[(df.index >= pd.Timestamp(start_date)) & (df.index <= pd.Timestamp(end_date))]
            out[c] = df[["open", "high", "low", "close", "volume"]]
        return out


def main():
    engine_signal = load_engine()
    print(f"Vibe native engine: {type(engine_signal).__module__}.{type(engine_signal).__name__}")
    config = {
        "codes": CODES, "interval": "1h", "start_date": START, "end_date": END,
        "initial_cash": 10_000, "leverage": 1.0,
        "maker_rate": 0.001, "taker_rate": 0.001, "slippage": 0.0, "funding_rate": 0.0,
    }
    engine = CryptoEngine(config)
    run_dir = Path(tempfile.mkdtemp(prefix="vibe_native_"))
    m = engine.run_backtest(config, LocalLoader(), engine_signal, run_dir, bars_per_year=24 * 365)

    print("\n=== Vibe-native strategy (technical-basic) on BTC/ETH/SOL, 2022-08..2026-08 ===")
    for k in ("total_return", "annual_return", "sharpe", "sortino", "max_drawdown",
              "win_rate", "profit_factor", "trade_count", "benchmark_return"):
        if k in m:
            print(f"  {k:16s} {m[k]}")


if __name__ == "__main__":
    main()
