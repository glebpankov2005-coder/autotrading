# Dry-run (paper trading) — cryptotankBal2

Dry-run runs the strategy against **live Binance data** and simulates orders with **no
real money**. It's the make-or-break step before going live: it catches slippage, fills,
and data issues a backtest can't. Run it for **4–8 weeks** on an always-on machine.

> Must run on a machine/VPS with internet access to Binance. (It cannot run inside the
> Claude sandbox — exchange APIs are blocked there.)

## 1. Install

```bash
git clone <this repo> && cd autotrading
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt          # installs freqtrade
```

## 2. (Recommended) sanity-check on real data first

The committed backtests use proxy data. Confirm the edge holds on real Binance candles:

```bash
freqtrade download-data --exchange binance \
  --pairs BTC/USDT ETH/USDT SOL/USDT --timeframes 1h 4h --timerange 20220101-
freqtrade backtesting --config user_data/config_dryrun.json \
  --datadir user_data/data --timerange 20240101- --timeframe 1h
```

Expect roughly the documented profile (25%+ CAGR / high Sharpe on recent data). If it's
wildly different, stop and investigate before dry-running.

## 3. (Optional but recommended) monitoring

- **Telegram**: create a bot via @BotFather, get your chat id, then in
  `config_dryrun.json` set `telegram.enabled = true` and fill `token` / `chat_id`.
- **FreqUI dashboard**: set `api_server.enabled = true`, change `jwt_secret_key`,
  `ws_token`, and `password` to random strings, then open `http://127.0.0.1:8080`.

## 4. Launch the dry-run

```bash
freqtrade trade --config user_data/config_dryrun.json
# or use the helper:
./start_dryrun.sh
```

It starts paper-trading immediately (`dry_run: true`, 1000 USDT paper wallet, BTC/ETH/SOL,
`cryptotankBal2`). Trades are logged to `user_data/dryrun.sqlite`. Leave it running 24/7.

## 5. What to watch over the weeks

- **Do live signals/fills match the backtest** over the same dates? Big divergence =
  slippage or data problems to fix before live.
- **Trade frequency** — cryptotankBal2 is patient (dips only); quiet stretches are normal.
- **Drawdown** — the MaxDrawdown protection pauses new entries after a 20% account
  drawdown; confirm it behaves as expected.
- Keep the process alive (systemd / Docker restart policy) and back up the sqlite DB.

## 6. Gate before real money

Only go live if dry-run tracks the backtest over a meaningful number of trades. Then:
trade-only + IP-whitelisted API keys, withdrawals disabled, a small wallet you can afford
to lose, and `dry_run: false`. See `BOT_ROADMAP.md` Phase 3.

## Tuning knobs

- `dry_run_wallet` — set to your intended real capital so sizing is realistic.
- `max_open_trades` (3) and `stake_amount` (`unlimited`) — position sizing across pairs.
- Swap `strategy` to `cryptotankPro` for the lower-drawdown / lower-return defensive variant.
