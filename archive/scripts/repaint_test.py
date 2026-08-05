"""Definitive repaint / lookahead test.

For a strategy, compute enter/exit signals on the full dataframe, then recompute on
a dataframe truncated at cutoff C. If signals at times <= (C - guard) differ between
the two runs, the strategy repaints -> it used future data (lookahead bias).
"""
import sys
import warnings

warnings.filterwarnings("ignore")
import run_backtest_2y  # noqa: E402  (ccxt stubs)
import pandas as pd  # noqa: E402
from freqtrade.configuration import Configuration  # noqa: E402
from freqtrade.resolvers import StrategyResolver  # noqa: E402
from freqtrade.data.history import load_pair_history  # noqa: E402
from pathlib import Path  # noqa: E402


def load_strat(cls, spath):
    cfg = Configuration.from_files(["user_data/config_recent.json"])
    cfg["strategy"] = cls
    cfg["strategy_path"] = spath
    cfg["user_data_dir"] = Path("user_data")
    return StrategyResolver.load_strategy(cfg)


def signals(strat, df, pair):
    d = df.copy()
    d = strat.advise_indicators(d, {"pair": pair})
    d = strat.advise_entry(d, {"pair": pair})
    d = strat.advise_exit(d, {"pair": pair})
    cols = [c for c in ("enter_long", "exit_long", "enter_short", "exit_short") if c in d]
    out = d[["date"] + cols].copy()
    for c in cols:
        out[c] = out[c].fillna(0)
    return out, cols


def test(cls, spath, pair="BTC/USDT"):
    strat = load_strat(cls, spath)
    dd = Path("user_data/data_recent/binance")
    df = load_pair_history(pair=pair, timeframe="1h", datadir=dd, data_format="feather")
    df = df[(df.date >= pd.Timestamp("2024-07-21", tz="UTC")) &
            (df.date <= pd.Timestamp("2026-07-21", tz="UTC"))].reset_index(drop=True)
    full, cols = signals(strat, df, pair)
    n = len(df)
    guard = 5  # ignore the last few bars near the cutoff (legitimately unfinished)
    mismatches = 0
    checked = 0
    for cut in (int(n * 0.4), int(n * 0.6), int(n * 0.8)):
        trunc, _ = signals(strat, df.iloc[:cut].copy(), pair)
        m = min(cut - guard, len(trunc) - guard)
        a = full.iloc[:m]; b = trunc.iloc[:m]
        checked += m * len(cols)
        for c in cols:
            mismatches += int((a[c].values != b[c].values).sum())
    verdict = "REPAINTS (lookahead bias)" if mismatches > 0 else "clean (no repaint)"
    print(f"{cls:16s} {pair}: {verdict}  | changed signals={mismatches}/{checked}")
    return mismatches


if __name__ == "__main__":
    # cls:dir pairs from argv
    for arg in sys.argv[1:]:
        cls, d = arg.split(":")
        try:
            test(cls, f"/tmp/tourney_work/{d}")
        except Exception as e:
            print(f"{cls:16s} ERROR: {str(e)[:120]}")
