#!/usr/bin/env bash
# Snapshot the dry-run trade DB (run from cron, e.g. hourly).
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p backups
cp -f user_data/dryrun.sqlite "backups/dryrun-$(date +%Y%m%d-%H%M).sqlite" 2>/dev/null || true
# keep only the last 48 snapshots
ls -1t backups/dryrun-*.sqlite 2>/dev/null | tail -n +49 | xargs -r rm -f
