# StockExample — Connors RSI-2 mean-reversion (a classic daily equities strategy).
# Buy a short-term oversold pullback WITHIN a long-term uptrend; exit on the bounce.
# Long-only, daily. This is a sane, well-documented starting point for stock backtests —
# equities mean-revert far more reliably than crypto (where this style fails).
import talib.abstract as ta
from pandas import DataFrame
from freqtrade.strategy import IStrategy


class StockExample(IStrategy):
    timeframe = "1d"
    can_short = False
    stoploss = -0.08
    minimal_roi = {"0": 100}          # exits are signal-driven, not ROI
    use_exit_signal = True
    process_only_new_candles = True
    startup_candle_count: int = 210

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["sma200"] = ta.SMA(dataframe, timeperiod=200)   # long-term trend
        dataframe["sma5"] = ta.SMA(dataframe, timeperiod=5)       # exit reference
        dataframe["rsi2"] = ta.RSI(dataframe, timeperiod=2)       # short-term oversold
        return dataframe

    def populate_entry_trend(self, df: DataFrame, metadata: dict) -> DataFrame:
        df.loc[
            (df["close"] > df["sma200"])     # only in a long-term uptrend
            & (df["rsi2"] < 10)               # deeply oversold short-term pullback
            & (df["volume"] > 0),
            ["enter_long", "enter_tag"],
        ] = (1, "rsi2_dip")
        return df

    def populate_exit_trend(self, df: DataFrame, metadata: dict) -> DataFrame:
        df.loc[
            (df["close"] > df["sma5"]) & (df["volume"] > 0),   # bounce completed
            ["exit_long", "exit_tag"],
        ] = (1, "sma5_bounce")
        return df
