# Apex_VolSize — Apex + volatility-targeted position sizing.
# Financial-calculus principle: keep each trade's contribution to portfolio variance
# constant by sizing inversely to the coin's realized volatility (the diffusion term σ).
#   stake = base_stake * clip(target_rv / realized_vol, lo, hi)
# realized_vol = std of hourly log-returns over 24h (a diffusion estimate). Small bets on
# high-σ coins/moments, bigger on low-σ. Signal & exit unchanged — only sizing differs.
import numpy as np
from datetime import datetime
from typing import Optional
from pandas import DataFrame
from Apex import Apex


class Apex_VolSize(Apex):
    target_rv = 0.0066     # universe-median realized vol (24h) — the vol we size toward
    size_min = 0.40        # clamp: never below 0.4x
    size_max = 2.00        # clamp: never above 2.0x
    rv_window = 24

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        logret = np.log(dataframe["close"] / dataframe["close"].shift(1))
        dataframe["rv"] = logret.rolling(self.rv_window).std()
        return dataframe

    def custom_stake_amount(self, pair: str, current_time: datetime, current_rate: float,
                            proposed_stake: float, min_stake: Optional[float], max_stake: float,
                            leverage: float, entry_tag: Optional[str], side: str,
                            **kwargs) -> float:
        base = proposed_stake / self.max_dca_multiplier
        df, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if df is None or len(df) == 0:
            return base
        rv = df["rv"].iloc[-1]
        if rv is None or np.isnan(rv) or rv <= 0:
            return base
        scale = float(np.clip(self.target_rv / rv, self.size_min, self.size_max))
        stake = base * scale
        if max_stake:
            stake = min(stake, max_stake)
        if min_stake:
            stake = max(stake, min_stake)
        return stake
