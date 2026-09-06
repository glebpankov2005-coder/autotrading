# Apex_Ito — Apex + a quadratic-variation (realized-volatility) filter.
# The Ito integral's defining companion is QUADRATIC VARIATION: for log-price,
# QV_t = sum (d ln P)^2 estimates the integrated variance ∫σ² ds (realized vol).
# Hypothesis under test: skipping entries during EXTREME realized-vol spikes avoids
# the worst falling-knife dips. (May instead remove the best capitulation buys — that's
# exactly what the backtest decides.) Everything else = base Apex, unchanged.
import numpy as np
from pandas import DataFrame
from Apex import Apex


class Apex_Ito(Apex):
    rv_window = 24          # bars over which quadratic variation is accumulated (~1 day on 1h)
    rv_block_quantile = 0.95   # block entries only when realized vol is in its top 5% (rolling)
    rv_rank_window = 720       # rolling window (~30d) for the vol percentile

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        logret = np.log(dataframe["close"] / dataframe["close"].shift(1))
        # discrete quadratic variation of log-price = realized variance over the window
        qv = (logret ** 2).rolling(self.rv_window).sum()
        dataframe["realized_vol"] = np.sqrt(qv)          # realized volatility (Itô QV estimator)
        # rolling percentile threshold: only the most extreme vol counts as "crash-like"
        thr = dataframe["realized_vol"].rolling(self.rv_rank_window).quantile(self.rv_block_quantile)
        dataframe["rv_ok"] = (dataframe["realized_vol"] <= thr) | thr.isna()
        return dataframe

    def populate_entry_trend(self, df: DataFrame, metadata: dict) -> DataFrame:
        df = super().populate_entry_trend(df, metadata)
        # block entries only during extreme realized-vol spikes
        off = ~df["rv_ok"].astype(bool)
        df.loc[off, "enter_long"] = 0
        df.loc[off, "enter_tag"] = None
        return df
