# Deploy — run the dry-run 24/7 (auto-restart + survive reboots)

Two ways to keep `cryptotankBal2`'s dry-run alive on a VPS. Pick one.

## Option A — systemd (plain Linux VPS)

Assumes the repo is at `/opt/autotrading` with a `.venv` (see `docs/DRYRUN.md` install).

```bash
# adjust User= and the /opt/autotrading paths in the unit if your install differs
sudo cp deploy/freqtrade-dryrun.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now freqtrade-dryrun     # start now + on every boot
journalctl -u freqtrade-dryrun -f                # live logs
sudo systemctl restart freqtrade-dryrun          # after a config/strategy change
```

`Restart=always` relaunches it if it ever crashes; `enable` starts it on reboot.

## Option B — Docker (recommended if you have Docker)

Uses the official `freqtradeorg/freqtrade` image; no local Python needed.

```bash
docker compose -f deploy/docker-compose.yml up -d      # start (survives reboots)
docker compose -f deploy/docker-compose.yml logs -f    # live logs
docker compose -f deploy/docker-compose.yml restart    # after a change
docker compose -f deploy/docker-compose.yml down       # stop
```

`restart: unless-stopped` handles crashes and reboots. The repo's `user_data/` is mounted
into the container, so strategies, config, and the sqlite trade DB persist on the host.

## Back up the trade database (both options)

```bash
# hourly snapshots of user_data/dryrun.sqlite (keeps last 48)
crontab -e
0 * * * * /opt/autotrading/deploy/backup_db.sh
```

## Sanity checks

- Confirm it's actually trading: `journalctl -u freqtrade-dryrun` (systemd) or the Docker
  logs should show heartbeat lines and any entries/exits.
- If you enabled FreqUI (`api_server.enabled=true`), open `http://127.0.0.1:8080`
  (Docker: uncomment the `ports:` line first).
- If you enabled Telegram, `/status` and `/profit` in your bot chat report live state.

See `docs/DRYRUN.md` for what to monitor over the 4–8 week paper-trading window.

## Watchdog — get pinged if the bot dies or drawdown spikes

`deploy/healthcheck.py` is an external safety net: freqtrade's own Telegram alerts can't
fire if the process is dead, so this checks liveness independently (systemd → docker →
pgrep) and also alerts on a realized-drawdown breach. Alerts are de-duplicated.

```bash
# 1) point it at your Telegram bot (or set telegram creds in config_dryrun.json)
export TG_TOKEN=123456:abc...   TG_CHAT=987654321
# optional: MONITOR_DD_PCT=15  MONITOR_WALLET=1000  MONITOR_UNIT=freqtrade-dryrun

# 2) run every 5 minutes via cron
crontab -e
*/5 * * * * TG_TOKEN=... TG_CHAT=... /opt/autotrading/.venv/bin/python /opt/autotrading/deploy/healthcheck.py >> /opt/autotrading/user_data/monitor.log 2>&1
```

It sends: 🔴 when the bot goes down, 🟢 when it recovers, ⚠️ when drawdown ≥ threshold
(default 15%). With no Telegram configured it just prints the alert (visible in the log).
