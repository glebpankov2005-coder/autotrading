# LiquiditySweep — freqtrade interpretation of BigBeluga's "Structural Liquidity & POC Matrix".
# NOTE: the original is a TradingView *indicator* (drawing only, no signals). These entry/exit
# rules are a standard interpretation of the concept, not from the source. Long-only spot.
from pandas import DataFrame
import talib.abstract as ta
from freqtrade.strategy import IStrategy, IntParameter


class LiquiditySweep(IStrategy):
    timeframe = "1h"
    can_short = False

    # risk management (the indicator has none, so we add sane defaults)
    stoploss = -0.10
    minimal_roi = {"0": 0.15}
    trailing_stop = True
    trailing_stop_positive = 0.02
    trailing_stop_positive_offset = 0.03
    trailing_only_offset_is_reached = True

    startup_candle_count: int = 220
    process_only_new_candles = True
    use_exit_signal = False

    liquidity_len = IntParameter(50, 150, default=100, space="buy", optimize=False)

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        n = self.liquidity_len.value
        # prior N-bar liquidity levels (shifted so the current bar can't see itself)
        dataframe["prior_low"] = dataframe["low"].rolling(n).min().shift(1)
        dataframe["prior_high"] = dataframe["high"].rolling(n).max().shift(1)
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=14)
        dataframe["ema200"] = ta.EMA(dataframe, timeperiod=200)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Bullish liquidity sweep: wick takes out the prior N-bar low (grabs sell-side
        # liquidity) but price CLOSES back above it -> rejection / reversal -> go long.
        # TREND FILTER: only in an uptrend (close > 200-EMA) -> buy pullbacks, not knives.
        dataframe.loc[
            (dataframe["low"] < dataframe["prior_low"])
            & (dataframe["close"] > dataframe["prior_low"])
            & (dataframe["close"] > dataframe["ema200"])
            & (dataframe["volume"] > 0),
            ["enter_long", "enter_tag"],
        ] = (1, "liq_sweep_long")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Exit when price runs up into the opposite (buy-side) liquidity: reaches prior high.
        dataframe.loc[
            (dataframe["high"] >= dataframe["prior_high"]) & (dataframe["volume"] > 0),
            ["exit_long", "exit_tag"],
        ] = (1, "reached_upper_liq")
        return dataframe
