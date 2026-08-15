# SHM_RSIMomentum — faithful freqtrade port of "SHM - RSI Momentum Matrix" (Pine v6).
# WMA-cross breakout + daily-locked RSI velocity gate + macro-tide (480 WMA) filter.
# Native 4H. src=ohlc4. Long/short. The source is an indicator (no exits) — a WMA-break
# exit + stop are added here for risk management. Defaults match the source.
import numpy as np
import pandas as pd
import talib.abstract as ta
from pandas import DataFrame
from freqtrade.strategy import IStrategy


def _wma(series, length):
    w = np.arange(1, length + 1, dtype=float)
    return series.rolling(length).apply(lambda x: np.dot(x, w) / w.sum(), raw=True)


class SHM_RSIMomentum(IStrategy):
    timeframe = "4h"
    can_short = True
    stoploss = -0.20
    minimal_roi = {"0": 100}          # disabled — trend follower
    trailing_stop = True
    trailing_stop_positive = 0.05
    trailing_stop_positive_offset = 0.08
    trailing_only_offset_is_reached = True
    use_exit_signal = True
    process_only_new_candles = True
    startup_candle_count: int = 520   # 480 WMA + daily RSI warmup

    # ---- source defaults ----
    fast_len = 63
    slow_len = 480
    sens_len = 41
    rsi_len = 33
    long_min, long_max = 42.0, 48.0
    short_min, short_max = 46.0, 52.0

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        df = dataframe
        src = (df["open"] + df["high"] + df["low"] + df["close"]) / 4.0
        df["fast_wma"] = _wma(src, self.fast_len)
        df["slow_wma"] = _wma(src, self.slow_len)
        df["filter_ma"] = ta.SMA(src, timeperiod=self.sens_len)

        # daily-locked RSI(33) on ohlc4, previous closed day (non-repainting)
        d = df[["date", "open", "high", "low", "close"]].copy()
        d = d.set_index("date")
        daily = d.resample("1D").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
        dsrc = (daily["open"] + daily["high"] + daily["low"] + daily["close"]) / 4.0
        daily["rsi"] = ta.RSI(dsrc, timeperiod=self.rsi_len)
        daily["rsi_prev"] = daily["rsi"].shift(1)     # previous CLOSED daily bar
        # map each 4h bar to that day's "previous day" RSI
        df["day"] = df["date"].dt.floor("1D")
        rsi_map = daily["rsi_prev"]
        df["rsi_locked"] = df["day"].map(rsi_map)
        df.drop(columns=["day"], inplace=True)
        return df

    def populate_entry_trend(self, df: DataFrame, metadata: dict) -> DataFrame:
        c, cp = df["close"], df["close"].shift(1)
        fw, fwp = df["fast_wma"], df["fast_wma"].shift(1)
        sw, swp = df["slow_wma"], df["slow_wma"].shift(1)

        body_break_up = ((c > fw) & (cp <= fwp)) | ((c > sw) & (cp <= swp))
        body_break_dn = ((c < fw) & (cp >= fwp)) | ((c < sw) & (cp >= swp))

        long_ok = (df["rsi_locked"] >= self.long_min) & (df["rsi_locked"] <= self.long_max)
        short_ok = (df["rsi_locked"] <= self.short_max) & (df["rsi_locked"] >= self.short_min)

        df.loc[
            body_break_up & (c > df["filter_ma"]) & (c > df["slow_wma"]) & long_ok & (df["volume"] > 0),
            ["enter_long", "enter_tag"],
        ] = (1, "shm_long")
        df.loc[
            body_break_dn & (c < df["filter_ma"]) & (c < df["slow_wma"]) & short_ok & (df["volume"] > 0),
            ["enter_short", "enter_tag"],
        ] = (1, "shm_short")
        return df

    def populate_exit_trend(self, df: DataFrame, metadata: dict) -> DataFrame:
        c, cp = df["close"], df["close"].shift(1)
        fw, fwp = df["fast_wma"], df["fast_wma"].shift(1)
        # exit on structure break back through the fast WMA
        df.loc[(c < fw) & (cp >= fwp), ["exit_long", "exit_tag"]] = (1, "lost_fast_wma")
        df.loc[(c > fw) & (cp <= fwp), ["exit_short", "exit_tag"]] = (1, "regained_fast_wma")
        return df
