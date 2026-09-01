# EMAMTFStoch — faithful port of "EMA Trend + MTF Stochastic Strategy" (Pine v6).
# EMA 38/62 trend filter + multi-timeframe stochastic timing (1h base, 4h confirm),
# staged ATR risk (initial 1.5xATR stop -> breakeven at 1R -> ATR trail at 1.5R),
# stoch-fade + trend-flip exits, 60-bar time stop. Long/short, 1x.
import numpy as np
import pandas as pd
import talib.abstract as ta
from datetime import datetime
from pandas import DataFrame
from freqtrade.strategy import IStrategy, stoploss_from_absolute


def _stoch_kd(df, length, sk, sd):
    ll = df["low"].rolling(length).min()
    hh = df["high"].rolling(length).max()
    raw = 100 * (df["close"] - ll) / (hh - ll).replace(0, np.nan)
    k = raw.rolling(sk).mean()
    d = k.rolling(sd).mean()
    return k, d


class EMAMTFStoch(IStrategy):
    timeframe = "1h"
    can_short = True
    stoploss = -0.99                 # real stop is the staged ATR logic in custom_stoploss
    minimal_roi = {"0": 100}
    use_custom_stoploss = True
    use_exit_signal = True
    process_only_new_candles = True
    startup_candle_count: int = 120

    # source defaults
    ema_fast, ema_slow = 38, 62
    slen, sk, sd = 11, 3, 3
    up_line, low_line = 80, 20
    require_trend = True
    atr_len = 14
    atr_stop_mult = 1.5
    breakeven_r = 1.0
    trail_start_r = 1.5
    trail_atr_mult = 1.5
    use_trend_exit = True
    max_bars = 60
    mtf = "4h"

    def populate_indicators(self, df: DataFrame, metadata: dict) -> DataFrame:
        df["ema_fast"] = ta.EMA(df, timeperiod=self.ema_fast)
        df["ema_slow"] = ta.EMA(df, timeperiod=self.ema_slow)
        df["trend_up"] = df["ema_fast"] > df["ema_slow"]
        df["atr"] = ta.ATR(df, timeperiod=self.atr_len)

        k, d = _stoch_kd(df, self.slen, self.sk, self.sd)
        df["k"], df["d"] = k, d

        # MTF stochastic on the 4h resample, LSMA-smoothed, previous-closed bar (non-repainting)
        r = df[["date", "open", "high", "low", "close"]].copy().set_index("date")
        h4 = r.resample(self.mtf).agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
        kk, dd = _stoch_kd(h4, self.slen, self.sk, self.sd)
        h4["mtfK"] = ta.LINEARREG(kk, timeperiod=self.slen)
        h4["mtfD"] = ta.LINEARREG(dd, timeperiod=self.slen)
        h4 = h4[["mtfK", "mtfD"]].shift(1).dropna().reset_index()      # last CLOSED 4h bar
        m = pd.merge_asof(df[["date"]].sort_values("date"), h4.sort_values("date"),
                          on="date", direction="backward")
        df["mtfK"] = m["mtfK"].values
        df["mtfD"] = m["mtfD"].values
        return df

    def populate_entry_trend(self, df: DataFrame, metadata: dict) -> DataFrame:
        k, d, mK, mD = df["k"], df["d"], df["mtfK"], df["mtfD"]
        stoch_long = (mK > 50) & (mK.shift(1) <= 50) & (k > 50) & (k.diff() > 0) & (k > d) & (mK > mD)
        stoch_short = (mD < 50) & (mD.shift(1) >= 50) & (k < 50) & (k.diff() < 0) & (k < d) & (mK < mD)
        long_ok = stoch_long & (df["trend_up"] if self.require_trend else True) & (df["volume"] > 0)
        short_ok = stoch_short & ((~df["trend_up"]) if self.require_trend else True) & (df["volume"] > 0)
        df.loc[long_ok, ["enter_long", "enter_tag"]] = (1, "mtf_stoch_long")
        df.loc[short_ok, ["enter_short", "enter_tag"]] = (1, "mtf_stoch_short")
        return df

    def populate_exit_trend(self, df: DataFrame, metadata: dict) -> DataFrame:
        # stoch-fade exits (mirror of entry) + optional trend-flip
        exit_long = (df["mtfD"] < self.up_line) & (df["mtfD"].shift(1) >= self.up_line)
        exit_short = (df["mtfK"] > self.low_line) & (df["mtfK"].shift(1) <= self.low_line)
        if self.use_trend_exit:
            exit_long = exit_long | (~df["trend_up"])
            exit_short = exit_short | (df["trend_up"])
        df.loc[exit_long, ["exit_long", "exit_tag"]] = (1, "stoch_fade/trend")
        df.loc[exit_short, ["exit_short", "exit_tag"]] = (1, "stoch_fade/trend")
        return df

    def custom_stoploss(self, pair, trade, current_time, current_rate, current_profit, **kwargs):
        df, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if df is None or len(df) == 0:
            return None
        since = df[df["date"] >= trade.open_date_utc]
        if since.empty:
            return None
        atr_entry = float(since["atr"].iloc[0])
        atr_now = float(since["atr"].iloc[-1])
        if not np.isfinite(atr_entry) or atr_entry <= 0:
            return None
        stop_dist = atr_entry * self.atr_stop_mult
        entry = trade.open_rate
        if not trade.is_short:
            peak_r = (trade.max_rate - entry) / stop_dist
            if peak_r >= self.trail_start_r:
                stop = trade.max_rate - atr_now * self.trail_atr_mult
            elif peak_r >= self.breakeven_r:
                stop = entry
            else:
                stop = entry - stop_dist
        else:
            peak_r = (entry - trade.min_rate) / stop_dist
            if peak_r >= self.trail_start_r:
                stop = trade.min_rate + atr_now * self.trail_atr_mult
            elif peak_r >= self.breakeven_r:
                stop = entry
            else:
                stop = entry + stop_dist
        return stoploss_from_absolute(stop, current_rate, is_short=trade.is_short, leverage=1.0)

    def custom_exit(self, pair, trade, current_time: datetime, current_rate, current_profit, **kwargs):
        if self.max_bars and trade.open_date_utc is not None:
            bars = (current_time - trade.open_date_utc).total_seconds() / 3600.0  # 1h bars
            if bars >= self.max_bars:
                return "time_stop"
        return None
