# AdaptiveTrendTrail — faithful freqtrade port of Uptrick "Adaptive Trend Trail" (Pine v6).
# Always-in long/short trend follower, 1x, ATR trailing-stop (outerTrail) + reversal exit.
# Defaults match the source (trendLength 34; Supertrends 9/1.45, 14/1.95, 21/2.55; sensitivity 0.35).
import numpy as np
import talib.abstract as ta
from pandas import DataFrame
from freqtrade.strategy import IStrategy
from freqtrade.strategy import stoploss_from_absolute


def _supertrend_dir(high, low, close, atr, factor):
    """Pine ta.supertrend reference port. Returns direction: -1 uptrend(bull), +1 downtrend(bear)."""
    n = len(close)
    hl2 = (high + low) / 2.0
    up = hl2 + factor * atr
    dn = hl2 - factor * atr
    fu = np.copy(up)
    fl = np.copy(dn)
    direction = np.ones(n)
    st = np.full(n, np.nan)
    for i in range(1, n):
        fl[i] = dn[i] if (dn[i] > fl[i - 1] or close[i - 1] < fl[i - 1]) else fl[i - 1]
        fu[i] = up[i] if (up[i] < fu[i - 1] or close[i - 1] > fu[i - 1]) else fu[i - 1]
        if np.isnan(atr[i - 1]):
            direction[i] = 1
        elif st[i - 1] == fu[i - 1]:
            direction[i] = -1 if close[i] > fu[i] else 1
        else:
            direction[i] = 1 if close[i] < fl[i] else -1
        st[i] = fl[i] if direction[i] == -1 else fu[i]
    return direction


class AdaptiveTrendTrail(IStrategy):
    timeframe = "1h"
    can_short = True
    stoploss = -0.35          # safety net; real exit is the ATR trail in custom_stoploss
    minimal_roi = {"0": 100}  # disabled — trend follower, no fixed ROI
    use_custom_stoploss = True
    use_exit_signal = True
    process_only_new_candles = True
    startup_candle_count: int = 120

    # ---- source defaults ----
    trendLength = 34
    momentumLength = 12
    sensitivity = 0.35
    stFastLen, stFastFac = 9, 1.45
    stMidLen, stMidFac = 14, 1.95
    stSlowLen, stSlowFac = 21, 2.55
    smoothness = 5
    trailSize = 1.0

    def populate_indicators(self, df: DataFrame, metadata: dict) -> DataFrame:
        c = df["close"].values.astype(float)
        h = df["high"].values.astype(float)
        l = df["low"].values.astype(float)
        o = df["open"].values.astype(float)
        n = len(c)
        mintick = max(1e-8, np.nanmedian(np.abs(np.diff(c))) * 1e-4)

        def A(x):
            return np.asarray(x, dtype=float)

        def sh(a, k):
            out = np.full(len(a), np.nan)
            if k < len(a):
                out[k:] = a[:-k]
            return out

        basis = A(ta.EMA(df, timeperiod=self.trendLength))
        atr = A(ta.ATR(df, timeperiod=14))
        safeATR = np.maximum(atr, mintick)

        mom_src = df["close"] - df["close"].shift(self.momentumLength)
        momentum = A(ta.EMA(mom_src, timeperiod=5)) / safeATR
        distance = (c - basis) / safeATR

        # directional efficiency (Kaufman-style, length 10)
        effLen = 10
        netMove = np.abs(c - np.concatenate([np.full(effLen, np.nan), c[:-effLen]]))
        d1 = np.abs(np.diff(c, prepend=c[0]))
        travel = np.convolve(d1, np.ones(effLen), "full")[:n]
        travel[:effLen] = np.nan
        with np.errstate(invalid="ignore", divide="ignore"):
            efficiency = np.clip(np.where(travel > 0, netMove / travel, 0.0), 0.0, 1.0)
        chop = 1.0 - efficiency
        cshift = np.concatenate([np.full(effLen, np.nan), c[:-effLen]])
        effDir = np.where(c > cshift, 1.0, np.where(c < cshift, -1.0, 0.0))
        efficiencyField = efficiency * effDir

        # volatility regime
        normalATR = A(ta.EMA(DataFrame({"close": safeATR}), timeperiod=50))
        volRatio = np.where(normalATR > 0, safeATR / normalATR, 1.0)
        volExpansion = np.clip(volRatio - 1.0, 0.0, 1.25)
        volDeviation = np.clip(np.abs(volRatio - 1.0), 0.0, 1.50)

        # adaptive supertrends
        fastFac = self.stFastFac + chop * 0.25 + volExpansion * 0.10
        midFac = self.stMidFac + chop * 0.35 + volExpansion * 0.15
        slowFac = self.stSlowFac + chop * 0.45 + volExpansion * 0.20
        atrF = A(ta.ATR(df, timeperiod=self.stFastLen))
        atrM = A(ta.ATR(df, timeperiod=self.stMidLen))
        atrS = A(ta.ATR(df, timeperiod=self.stSlowLen))
        dF = _supertrend_dir(h, l, c, np.nan_to_num(atrF), fastFac)
        dM = _supertrend_dir(h, l, c, np.nan_to_num(atrM), midFac)
        dS = _supertrend_dir(h, l, c, np.nan_to_num(atrS), slowFac)
        bullVotes = (dF < 0).astype(int) + (dM < 0).astype(int) + (dS < 0).astype(int)
        bearVotes = (dF > 0).astype(int) + (dM > 0).astype(int) + (dS > 0).astype(int)
        reqVotes = np.where(chop > 0.70, 3, 2)
        bullSTConfirmed = bullVotes >= reqVotes
        bearSTConfirmed = bearVotes >= reqVotes
        fullBullST = bullVotes == 3
        fullBearST = bearVotes == 3
        bullTakeover = (dF < 0) & ((dM < 0) | (dS < 0))
        bearTakeover = (dF > 0) & ((dM > 0) | (dS > 0))

        # regime fields
        def clip1(x):
            return np.clip(x, -1.0, 1.0)
        distanceField = clip1(distance / 1.20)
        momentumField = clip1(momentum / 0.35)
        slopeField = clip1(((basis - sh(basis,3)) / safeATR) / 0.25)
        rsi = A(ta.RSI(df, timeperiod=14))
        rsiField = clip1((rsi - 50.0) / 20.0)
        stField = (bullVotes - bearVotes) / 3.0
        slowCenter = A(ta.EMA(DataFrame({"close": (h + l) / 2.0}), timeperiod=max(10, int(round(self.trendLength * 0.70)))))
        slowSlope = (slowCenter - sh(slowCenter,3)) / safeATR
        slowSlopeField = clip1(slowSlope / 0.25)
        structLen = max(3, int(round(self.trendLength * 0.12)))
        recentHigh = A(df["high"].shift(1).rolling(structLen).max())
        recentLow = A(df["low"].shift(1).rolling(structLen).min())
        structureField = np.where(c > recentHigh, 1.0, np.where(c < recentLow, -1.0, 0.0))
        barRange = np.maximum(h - l, mintick)
        bodyPressure = (c - o) / barRange
        closeLoc = ((c - l) / barRange - 0.5) * 2.0
        pressureField = clip1(bodyPressure * 0.60 + closeLoc * 0.40)

        rawRegime = (distanceField * 0.22 + momentumField * 0.19 + slopeField * 0.14 +
                     slowSlopeField * 0.10 + rsiField * 0.08 + efficiencyField * 0.09 +
                     pressureField * 0.05 + structureField * 0.05 + stField * 0.20)
        regime = A(ta.EMA(DataFrame({"close": np.nan_to_num(rawRegime)}), timeperiod=3))

        chopPenalty = chop * 0.085
        volPenalty = np.clip(volDeviation * 0.04, 0.0, 0.06)
        dynamicGate = 0.22 + self.sensitivity * 0.12 + chopPenalty + volPenalty
        bullZone = regime > dynamicGate
        bearZone = regime < -dynamicGate
        bullPriceOK = c > basis + safeATR * self.sensitivity * 0.30
        bearPriceOK = c < basis - safeATR * self.sensitivity * 0.30

        # ---- stateful state machine (single sequential loop) ----
        trend = np.zeros(n)
        bullSTBars = bearSTBars = 0
        bullConfirm = bearConfirm = 0
        cur = 0
        lastFlip = -100000
        for i in range(n):
            if np.isnan(regime[i]) or np.isnan(momentum[i]):
                trend[i] = cur
                continue
            bullSTBars = min(bullSTBars + 1, 5) if bullSTConfirmed[i] else 0
            bearSTBars = min(bearSTBars + 1, 5) if bearSTConfirmed[i] else 0
            stPersReq = 2 if chop[i] > 0.72 else 1
            bullSTP = bullSTBars >= stPersReq
            bearSTP = bearSTBars >= stPersReq
            bullCand = bullZone[i] and bullPriceOK[i] and momentum[i] > 0.025 and bullSTP
            bearCand = bearZone[i] and bearPriceOK[i] and momentum[i] < -0.025 and bearSTP
            strongBull = (bullCand and fullBullST[i] and regime[i] > dynamicGate[i] + 0.26
                          and momentum[i] > 0.16 and efficiency[i] > 0.42)
            strongBear = (bearCand and fullBearST[i] and regime[i] < -(dynamicGate[i] + 0.26)
                          and momentum[i] < -0.16 and efficiency[i] > 0.42)
            reqBars = 3 if chop[i] > 0.72 else (2 if chop[i] > 0.40 else 1)
            bullConfirm = min(bullConfirm + 1, 4) if bullCand else 0
            bearConfirm = min(bearConfirm + 1, 4) if bearCand else 0
            bullReady = ((bullConfirm >= reqBars) or strongBull) and bullTakeover[i]
            bearReady = ((bearConfirm >= reqBars) or strongBear) and bearTakeover[i]
            cooldownBars = 6 + int(round(chop[i] * 4.0))
            cooldownDone = (i - lastFlip) >= cooldownBars
            if cur != 1 and bullReady and (cooldownDone or strongBull):
                cur = 1; lastFlip = i; bullConfirm = bearConfirm = bullSTBars = bearSTBars = 0
            elif cur != -1 and bearReady and (cooldownDone or strongBear):
                cur = -1; lastFlip = i; bullConfirm = bearConfirm = bullSTBars = bearSTBars = 0
            trend[i] = cur

        df["att_trend"] = trend
        prev = np.concatenate([[0], trend[:-1]])
        df["att_up"] = (trend == 1) & (prev != 1)
        df["att_down"] = (trend == -1) & (prev != -1)

        # ATR trail (outerTrail), ratchet handled in custom_stoploss
        smoothBasis = A(ta.EMA(DataFrame({"close": basis}), timeperiod=self.smoothness))
        smoothATR = A(ta.EMA(DataFrame({"close": safeATR}), timeperiod=self.smoothness))
        outer = 1.15 * self.trailSize
        df["outer_long"] = smoothBasis - smoothATR * outer
        df["outer_short"] = smoothBasis + smoothATR * outer
        return df

    def populate_entry_trend(self, df: DataFrame, metadata: dict) -> DataFrame:
        df.loc[df["att_up"] & (df["volume"] > 0), ["enter_long", "enter_tag"]] = (1, "att_up")
        df.loc[df["att_down"] & (df["volume"] > 0), ["enter_short", "enter_tag"]] = (1, "att_down")
        return df

    def populate_exit_trend(self, df: DataFrame, metadata: dict) -> DataFrame:
        df.loc[df["att_down"], ["exit_long", "exit_tag"]] = (1, "reversal")
        df.loc[df["att_up"], ["exit_short", "exit_tag"]] = (1, "reversal")
        return df

    def custom_stoploss(self, pair, trade, current_time, current_rate, current_profit, **kwargs):
        df, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if df is None or len(df) == 0:
            return None
        since = df[df["date"] >= trade.open_date_utc]
        if since.empty:
            return None
        if not trade.is_short:
            stop = since["outer_long"].max()      # ratchet up
        else:
            stop = since["outer_short"].min()      # ratchet down
        if stop is None or np.isnan(stop):
            return None
        return stoploss_from_absolute(stop, current_rate, is_short=trade.is_short, leverage=1.0)
