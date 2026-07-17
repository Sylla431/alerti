#!/usr/bin/env python3
"""
CLI — exécute une passe Bamako alert-check (sans passer par HTTP).

Usage (depuis backend/) :
  ../venv/bin/python jobs/run_bamako_alert_check.py --dry-run
  ../venv/bin/python jobs/run_bamako_alert_check.py --force
  ../venv/bin/python jobs/run_bamako_alert_check.py

Via HTTP (serveur déjà lancé) :
  curl -X POST "http://127.0.0.1:5000/api/bamako/alert-check?dry_run=1" \\
    -H "X-Cron-Secret: $CRON_SECRET"
"""
from __future__ import annotations

import argparse
import json
import os
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)


def main() -> int:
    parser = argparse.ArgumentParser(description="Bamako alert-check (Alerti Pluie v1)")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Évalue les seuils sans envoyer de push",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Ignore le cooldown (utile pour un test d'envoi)",
    )
    args = parser.parse_args()

    from services.bamako_alert_watcher import BamakoAlertWatcher

    watcher = BamakoAlertWatcher()
    result = watcher.run(dry_run=args.dry_run, force=args.force)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
