#!/usr/bin/env python3
"""Standalone intraday backtester for the EMA + MTF Stochastic strategy.

Why this exists: freqtrade pads fake flat bars across weekend/overnight gaps when
it loads equity data into its 24/7 candle grid (observed ~45% fake bars on daily
stocks). Those fake bars flatten the stochastic and stop the entry from firing —
which is why the freqtrade stock run made only 1 trade. This runner reads the RAW
feathers with NO gap-filling, so the strategy is tested on real bars only.

It re-implements EMAMTFStoch's logic faithfully (EMA 38/62 trend, stoch 11/3/3,
4h-MTF LSMA-smoothed stochastic confirmation, staged ATR stop, stoch-fade/trend
exits, 60-bar time stop). Indicators are computed directly (no TA-Lib/freqtrade
dependency) so it runs anywhere pandas+numpy+pyarrow are installed.

Absolute % returns won't match freqtrade to the decimal (different stake
accounting), but trade count, direction, win rate and Sharpe are apples-to-apples
and — crucially — computed on uncorrupted bars.

Usage:
    # stocks (on the VPS, after fetching 1h feathers):
    python tools/bt_intraday.py --datadir user_data/data_stocks/kraken \
        --pairs AAPL MSFT AMZN GOOGL META TSLA SPY QQQ --quote USD

    # crypto sanity check (committed data):
    python tools/bt_intraday.py --datadir user_data/data/binance \
        --pairs BTC ETH SOL --quote USDT
"""
import argparse
import numpy as np
import pandas as pd

# ---- strategy params (mirror EMAMTFStoch) ----
EMA_FAST, EMA_SLOW = 38, 62
SLEN, SK, SD = 11, 3, 3
UP_LINE, LOW_LINE = 80, 20
ATR_LEN = 14
ATR_STOP_MULT = 1.5
BREAKEVEN_R = 1.0
TRAIL_START_R = 1.5
TRAIL_ATR_MULT = 1.5
MAX_BARS = 60
STARTUP = 250


def ema(s, n):
    return s.ewm(span=n, adjust=False).mean()


def rma(s, n):                       # Wilder's smoothing (TA-Lib ATR/RSI style)
    return s.ewm(alpha=1.0 / n, adjust=False).mean()


def atr(df, n):
    h, l, c = df["high"], df["low"], df["close"]
    pc = c.shift(1)
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    return rma(tr, n)


def stoch_kd(df, length, sk, sd):
    ll = df["low"].rolling(length).min()
    hh = df["high"].rolling(length).max()
    raw = 100 * (df["close"] - ll) / (hh - ll).replace(0, np.nan)
    k = raw.rolling(sk).mean()
    d = k.rolling(sd).mean()
    return k, d


def linreg(s, n):                    # ta.LINEARREG: value of the LSMA line at each point
    x = np.arange(n)
    xm = x.mean()
    denom = ((x - xm) ** 2).sum()

    def f(w):
        ym = w.mean()
        slope = ((x - xm) * (w - ym)).sum() / denom
        intercept = ym - slope * xm
        return intercept + slope * (n - 1)     # projected to the last point

    return s.rolling(n).apply(f, raw=True)


def build_indicators(df):
    df = df.sort_values("date").reset_index(drop=True)
    df["ema_fast"] = ema(df["close"], EMA_FAST)
    df["ema_slow"] = ema(df["close"], EMA_SLOW)
    df["trend_up"] = df["ema_fast"] > df["ema_slow"]
    df["atr"] = atr(df, ATR_LEN)
    k, d = stoch_kd(df, SLEN, SK, SD)
    df["k"], df["d"] = k, d

    # 4h MTF stochastic, LSMA-smoothed, previous CLOSED bar (non-repainting)
    r = df[["date", "open", "high", "low", "close"]].set_index("date")
    h4 = r.resample("4h").agg({"open": "first", "high": "max",
                               "low": "min", "close": "last"}).dropna()
    kk, dd = stoch_kd(h4, SLEN, SK, SD)
    h4["mtfK"] = linreg(kk, SLEN)
    h4["mtfD"] = linreg(dd, SLEN)
    h4 = h4[["mtfK", "mtfD"]].shift(1).dropna().reset_index()
    m = pd.merge_asof(df[["date"]].sort_values("date"), h4.sort_values("date"),
                      on="date", direction="backward")
    df["mtfK"] = m["mtfK"].values
    df["mtfD"] = m["mtfD"].values

    k, d, mK, mD = df["k"], df["d"], df["mtfK"], df["mtfD"]
    df["enter_long"] = ((mK > 50) & (mK.shift(1) <= 50) & (k > 50) &
                        (k.diff() > 0) & (k > d) & (mK > mD) & df["trend_up"] &
                        (df["volume"] > 0))
    df["exit_sig"] = ((mD < UP_LINE) & (mD.shift(1) >= UP_LINE)) | (~df["trend_up"])
    return df


def run(datadir, pairs, quote, tf="1h"):
    data = {}
    for p in pairs:
        fn = f"{datadir}/{p}_{quote}-{tf}.feather"
        try:
            df = pd.read_feather(fn)
        except Exception as e:
            print(f"  skip {p}: {e}")
            continue
        df["date"] = pd.to_datetime(df["date"], utc=True)
        df = build_indicators(df)
        df = df.iloc[STARTUP:].reset_index(drop=True)     # drop warmup
        data[p] = df

    if not data:
        print("No data loaded.")
        return

    # global timeline
    all_dates = sorted(set().union(*[set(d["date"]) for d in data.values()]))
    idx = {p: {row.date: row for row in df.itertuples(index=False)} for p, df in data.items()}

    balance = 10000.0
    max_open = 5
    positions = {}          # pair -> dict(entry, atr_entry, peak, open_i, qty)
    bar_i = {p: 0 for p in data}
    trades = []
    equity_curve = []

    for t in all_dates:
        # update bar index per pair
        for p in data:
            row = idx[p].get(t)
            if row is None:
                continue
            bar_i[p] += 1
            price = row.close

            # ---- manage open position ----
            if p in positions:
                pos = positions[p]
                pos["peak"] = max(pos["peak"], row.high)
                stop_dist = pos["atr_entry"] * ATR_STOP_MULT
                peak_r = (pos["peak"] - pos["entry"]) / stop_dist if stop_dist > 0 else 0
                if peak_r >= TRAIL_START_R:
                    stop = pos["peak"] - row.atr * TRAIL_ATR_MULT
                elif peak_r >= BREAKEVEN_R:
                    stop = pos["entry"]
                else:
                    stop = pos["entry"] - stop_dist

                exit_price = None
                reason = None
                if row.low <= stop:                          # stop hit intrabar
                    exit_price = min(row.open, stop) if row.open < stop else stop
                    reason = "atr_stop"
                elif bool(row.exit_sig):                      # signal exit at close
                    exit_price = price
                    reason = "stoch_fade/trend"
                elif (bar_i[p] - pos["open_i"]) >= MAX_BARS:  # 60-bar time stop
                    exit_price = price
                    reason = "time_stop"

                if exit_price is not None:
                    pnl = (exit_price - pos["entry"]) * pos["qty"]
                    balance += pos["qty"] * exit_price
                    trades.append({"pair": p, "ret": (exit_price / pos["entry"] - 1),
                                   "pnl": pnl, "reason": reason,
                                   "bars": bar_i[p] - pos["open_i"]})
                    del positions[p]

            # ---- entries ----
            if p not in positions and len(positions) < max_open and bool(row.enter_long):
                free = max_open - len(positions)
                stake = balance / free
                if stake > 1 and price > 0:
                    qty = stake / price
                    balance -= stake
                    positions[p] = {"entry": price, "atr_entry": row.atr,
                                    "peak": row.high, "open_i": bar_i[p], "qty": qty}

        # mark-to-market equity
        mtm = balance + sum(pos["qty"] * idx[p][t].close
                            for p, pos in positions.items() if t in idx[p])
        equity_curve.append(mtm)

    # close any still-open at last price
    for p, pos in list(positions.items()):
        last = data[p].iloc[-1]
        balance += pos["qty"] * last.close
        trades.append({"pair": p, "ret": (last.close / pos["entry"] - 1),
                       "pnl": (last.close - pos["entry"]) * pos["qty"],
                       "reason": "open_at_end", "bars": 0})

    # ---- report ----
    eq = pd.Series(equity_curve)
    n = len(trades)
    print(f"\n=== EMAMTFStoch (standalone, no gap-fill) — {datadir} ===")
    print(f"Pairs: {', '.join(data.keys())}")
    d0 = min(df['date'].iloc[0] for df in data.values())
    d1 = max(df['date'].iloc[-1] for df in data.values())
    print(f"Period: {str(d0)[:10]} -> {str(d1)[:10]}")
    print(f"Trades: {n}")
    if n == 0:
        print("No trades. Entry logic did not fire on real bars.")
        return
    rets = np.array([tr["ret"] for tr in trades])
    wins = (rets > 0).sum()
    final = balance
    tot_ret = final / 10000 - 1
    print(f"Final balance: {final:,.2f}  (total return {tot_ret*100:+.1f}%)")
    print(f"Win rate: {wins}/{n} = {wins/n*100:.0f}%")
    print(f"Avg trade: {rets.mean()*100:+.2f}%   Best {rets.max()*100:+.1f}%   Worst {rets.min()*100:+.1f}%")
    gains = rets[rets > 0].sum(); losses = -rets[rets < 0].sum()
    print(f"Profit factor: {gains/losses:.2f}" if losses > 0 else "Profit factor: inf")
    # daily-ish Sharpe from the equity curve (bars are 1h; annualize ~ sqrt(24*365))
    r = eq.pct_change().dropna()
    if r.std() > 0:
        sharpe = r.mean() / r.std() * np.sqrt(24 * 365)
        print(f"Sharpe (bar-based, annualized): {sharpe:.2f}")
    dd = (eq / eq.cummax() - 1).min()
    print(f"Max drawdown: {dd*100:.1f}%")
    by_reason = {}
    for tr in trades:
        by_reason.setdefault(tr["reason"], []).append(tr["ret"])
    print("Exits:", {k: f"{len(v)} ({np.mean(v)*100:+.1f}%)" for k, v in by_reason.items()})


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--datadir", required=True)
    ap.add_argument("--pairs", nargs="+", required=True)
    ap.add_argument("--quote", default="USD")
    ap.add_argument("--tf", default="1h")
    a = ap.parse_args()
    run(a.datadir, a.pairs, a.quote, a.tf)
