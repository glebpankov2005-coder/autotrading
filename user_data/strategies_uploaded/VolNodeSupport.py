# VolNodeSupport — corrected volume-profile logic (per the HVN-magnet principle).
# Big volume nodes (HVN) are support/resistance; the gaps between are traversed fast.
#   ENTRY (long): price falls DOWN TO the nearest High-Volume Node below (support), in an
#                 uptrend (close > 200-EMA). Buying the bounce off the volume shelf.
#   EXIT: price reaches the next HVN above (target), OR mean-revert via trailing stop.
#   STOP: tight — if the support node BREAKS, price seeks the next node down, so bail.
# (Contrast with VolProfileBB, which naively bought "below the POC" and lost.)
import numpy as np
import talib.abstract as ta
from pandas import DataFrame
from freqtrade.strategy import IStrategy


class VolNodeSupport(IStrategy):
    timeframe = "1h"
    can_short = False
    stoploss = -0.06                 # tight: a broken volume node → exit fast
    minimal_roi = {"0": 100}
    trailing_stop = True
    trailing_stop_positive = 0.025
    trailing_stop_positive_offset = 0.04
    trailing_only_offset_is_reached = True
    use_exit_signal = True
    process_only_new_candles = True
    startup_candle_count: int = 220

    vp_lookback = 120
    vp_rows = 60
    hvn_frac = 0.70                  # a row is an HVN if its volume >= 70% of the peak row
    near_tol = 0.008                 # "at the node" = within 0.8% of it

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ema200"] = ta.EMA(dataframe, timeperiod=200)
        h = dataframe["high"].values.astype(float)
        l = dataframe["low"].values.astype(float)
        c = dataframe["close"].values.astype(float)
        v = dataframe["volume"].values.astype(float)
        tp = (h + l + c) / 3.0
        n = len(c)
        LB, R, frac = self.vp_lookback, self.vp_rows, self.hvn_frac

        support = np.full(n, np.nan)   # nearest HVN below price
        target = np.full(n, np.nan)    # nearest HVN above price
        rows_idx = np.arange(R)
        for i in range(LB, n):
            s = slice(i - LB + 1, i + 1)
            lo = l[s].min(); hi = h[s].max()
            if hi <= lo:
                continue
            rowH = (hi - lo) / R
            idx = np.clip(((tp[s] - lo) / rowH).astype(int), 0, R - 1)
            prof = np.bincount(idx, weights=v[s], minlength=R)
            peak = prof.max()
            if peak <= 0:
                continue
            hvn = prof >= frac * peak
            price_of_row = lo + (rows_idx + 0.5) * rowH
            cp = c[i]
            below = price_of_row[hvn & (price_of_row < cp)]
            above = price_of_row[hvn & (price_of_row > cp)]
            if below.size:
                support[i] = below.max()
            if above.size:
                target[i] = above.min()
        dataframe["vp_support"] = support
        dataframe["vp_target"] = target
        return dataframe

    def populate_entry_trend(self, df: DataFrame, metadata: dict) -> DataFrame:
        sup = df["vp_support"]
        df.loc[
            (df["close"] <= sup * (1 + self.near_tol))   # price arrived at the node…
            & (df["close"] >= sup * (1 - self.near_tol)) # …and is holding it (not through it)
            & (df["close"] < df["close"].shift(6))       # came DOWN to it
            & (df["close"] > df["ema200"])               # overall uptrend
            & (df["volume"] > 0),
            ["enter_long", "enter_tag"],
        ] = (1, "hvn_support")
        return df

    def populate_exit_trend(self, df: DataFrame, metadata: dict) -> DataFrame:
        tgt = df["vp_target"]
        df.loc[
            (tgt.notna()) & (df["close"] >= tgt * 0.995) & (df["volume"] > 0),   # reached node above
            ["exit_long", "exit_tag"],
        ] = (1, "hvn_target")
        return df
