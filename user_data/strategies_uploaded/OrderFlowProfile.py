# OrderFlowProfile — freqtrade interpretation of Zeiierman's "Order Flow Profiler".
# The source is a VISUALIZATION indicator (no signals). Standard interpretation tested here:
# value-area mean-reversion — buy when price dips to the Value Area Low (VAL) in an uptrend,
# exit when it reverts to the Control Price / POC. Long-only spot. buyShare split matches source.
import numpy as np
import talib.abstract as ta
from pandas import DataFrame
from freqtrade.strategy import IStrategy


class OrderFlowProfile(IStrategy):
    timeframe = "1h"
    can_short = False
    stoploss = -0.15
    minimal_roi = {"0": 100}
    trailing_stop = True
    trailing_stop_positive = 0.03
    trailing_stop_positive_offset = 0.05
    trailing_only_offset_is_reached = True
    use_exit_signal = True
    process_only_new_candles = True
    startup_candle_count: int = 220

    lookback = 80      # source default
    rows = 60          # price cells
    va_pct = 0.70      # acceptance area

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        o = dataframe["open"].values.astype(float)
        h = dataframe["high"].values.astype(float)
        l = dataframe["low"].values.astype(float)
        c = dataframe["close"].values.astype(float)
        v = dataframe["volume"].values.astype(float)
        n = len(c)
        rng = np.maximum(h - l, 1e-12)

        # buyShare (source formula), vectorized
        closePos = np.clip((c - l) / rng, 0, 1)
        body = np.clip((c - o) / rng, -1, 1)
        upperWick = np.maximum(h - np.maximum(o, c), 0) / rng
        lowerWick = np.maximum(np.minimum(o, c) - l, 0) / rng
        drive = 0.48 * (2 * closePos - 1) + 0.32 * body + 0.20 * (lowerWick - upperWick)
        share = np.where(h - l > 0, np.clip(0.5 + 0.43 * drive, 0.025, 0.975), 0.5)
        tp = (h + l + c) / 3.0
        R, LB, goal = self.rows, self.lookback, self.va_pct

        poc = np.full(n, np.nan)
        val = np.full(n, np.nan)
        vah = np.full(n, np.nan)
        for i in range(LB, n):
            s = slice(i - LB + 1, i + 1)
            lo = l[s].min(); hi = h[s].max()
            if hi <= lo:
                continue
            rowH = (hi - lo) / R
            idx = np.clip(((tp[s] - lo) / rowH).astype(int), 0, R - 1)
            prof = np.bincount(idx, weights=v[s], minlength=R)
            pk = int(prof.argmax())
            total = prof.sum()
            # value area: expand from POC until va_pct of volume covered
            loR = hiR = pk
            acc = prof[pk]
            g = total * goal
            while acc < g and (loR > 0 or hiR < R - 1):
                up = prof[hiR + 1] if hiR < R - 1 else -1.0
                dn = prof[loR - 1] if loR > 0 else -1.0
                if up >= dn:
                    hiR += 1; acc += max(up, 0.0)
                else:
                    loR -= 1; acc += max(dn, 0.0)
            poc[i] = lo + (pk + 0.5) * rowH
            val[i] = lo + loR * rowH
            vah[i] = lo + (hiR + 1.0) * rowH

        dataframe["poc"] = poc
        dataframe["val"] = val
        dataframe["vah"] = vah
        dataframe["ema200"] = ta.EMA(dataframe, timeperiod=200)
        return dataframe

    def populate_entry_trend(self, df: DataFrame, metadata: dict) -> DataFrame:
        # buy the Value Area Low in an uptrend (mean-reversion toward the control price)
        uptrend = df["ema200"] > df["ema200"].shift(48)
        df.loc[
            (df["close"] <= df["val"]) & uptrend & (df["volume"] > 0),
            ["enter_long", "enter_tag"],
        ] = (1, "value_area_low")
        return df

    def populate_exit_trend(self, df: DataFrame, metadata: dict) -> DataFrame:
        # exit on reversion to the control price (POC)
        df.loc[(df["close"] >= df["poc"]) & (df["volume"] > 0), ["exit_long", "exit_tag"]] = (1, "reverted_to_poc")
        return df
