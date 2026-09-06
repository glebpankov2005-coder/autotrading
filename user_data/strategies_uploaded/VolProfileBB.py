# VolProfileBB — Bollinger-Band oversold + volume-profile confluence + trend filter.
# Rules (a standard interpretation of "volume profile + bollinger, 1h, with the trend"):
#   ENTRY (long): close < lower Bollinger Band  AND  close <= Control Price (POC, volume fair
#                 value)  AND  close > 200-EMA (overall uptrend).
#   EXIT: close >= middle Bollinger Band (mean-reversion target).  Long-only spot.
import numpy as np
import talib.abstract as ta
from pandas import DataFrame
from freqtrade.strategy import IStrategy


class VolProfileBB(IStrategy):
    timeframe = "1h"
    can_short = False
    stoploss = -0.12
    minimal_roi = {"0": 100}
    trailing_stop = True
    trailing_stop_positive = 0.03
    trailing_stop_positive_offset = 0.05
    trailing_only_offset_is_reached = True
    use_exit_signal = True
    process_only_new_candles = True
    startup_candle_count: int = 220

    bb_len = 20
    bb_std = 2.0
    vp_lookback = 80
    vp_rows = 60

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Bollinger Bands
        upper, mid, lower = ta.BBANDS(dataframe["close"], timeperiod=self.bb_len,
                                      nbdevup=self.bb_std, nbdevdn=self.bb_std)
        dataframe["bb_upper"] = upper
        dataframe["bb_mid"] = mid
        dataframe["bb_lower"] = lower
        dataframe["ema200"] = ta.EMA(dataframe, timeperiod=200)

        # Volume profile Control Price (POC) over a rolling window
        h = dataframe["high"].values.astype(float)
        l = dataframe["low"].values.astype(float)
        c = dataframe["close"].values.astype(float)
        v = dataframe["volume"].values.astype(float)
        tp = (h + l + c) / 3.0
        n = len(c)
        LB, R = self.vp_lookback, self.vp_rows
        poc = np.full(n, np.nan)
        for i in range(LB, n):
            s = slice(i - LB + 1, i + 1)
            lo = l[s].min(); hi = h[s].max()
            if hi <= lo:
                continue
            rowH = (hi - lo) / R
            idx = np.clip(((tp[s] - lo) / rowH).astype(int), 0, R - 1)
            prof = np.bincount(idx, weights=v[s], minlength=R)
            poc[i] = lo + (int(prof.argmax()) + 0.5) * rowH
        dataframe["poc"] = poc
        return dataframe

    def populate_entry_trend(self, df: DataFrame, metadata: dict) -> DataFrame:
        df.loc[
            (df["close"] < df["bb_lower"])       # Bollinger oversold
            & (df["close"] <= df["poc"])          # below volume fair value (room to revert up)
            & (df["close"] > df["ema200"])        # overall uptrend
            & (df["volume"] > 0),
            ["enter_long", "enter_tag"],
        ] = (1, "bb_vp_dip")
        return df

    def populate_exit_trend(self, df: DataFrame, metadata: dict) -> DataFrame:
        df.loc[
            (df["close"] >= df["bb_mid"]) & (df["volume"] > 0),   # reverted to the mean
            ["exit_long", "exit_tag"],
        ] = (1, "bb_mid_revert")
        return df
