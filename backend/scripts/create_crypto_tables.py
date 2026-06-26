"""
One-off: create crypto_payments + crypto_ledger tables in the empirebox.db
the live scheduler reads. Idempotent. Does NOT require a service restart.

Target: /home/rg/empire-data/empirebox.db
  - Verified via /proc/<pid>/environ: EMPIRE_DATA_DIR=/home/rg/empire-data
  - Verified via /proc/<pid>/fd/13: live backend has this file open
  - This is the SAME DB app.database.engine resolves to when EMPIRE_DATA_DIR
    is exported — which is how the scheduler's expire_crypto_payments job
    loads its SessionLocal.

Why not `alembic upgrade head`:
  - alembic.ini points at a non-existent postgres URL
  - alembic/env.py doesn't import CryptoPayment/CryptoLedger for autogenerate
  - backend/.env is missing
The existing migration 003_crypto_payments stays on disk for later use.
"""
import argparse
import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

DEFAULT_LIVE_DATA_DIR = "/home/rg/empire-data"
EXPECTED_DB_NAME = "empirebox.db"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--db",
        default=None,
        help="Override target DB path. Default: $EMPIRE_DATA_DIR/empirebox.db "
             "(falls back to /home/rg/empire-data/empirebox.db).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Run even if target isn't under /home/rg/empire-data/.",
    )
    args = parser.parse_args()

    # 1. Determine target DB path explicitly
    data_dir = os.environ.get("EMPIRE_DATA_DIR") or DEFAULT_LIVE_DATA_DIR
    target_db = args.db or os.path.join(data_dir, EXPECTED_DB_NAME)
    target_db = os.path.abspath(target_db)

    # 2. Safety: warn if target isn't the live DB
    expected_prefix = "/home/rg/empire-data/"
    if not target_db.startswith(expected_prefix) and not args.force:
        print(f"REFUSING: target {target_db} is not under {expected_prefix}")
        print("Pass --force to override, or set EMPIRE_DATA_DIR=/home/rg/empire-data")
        return 2

    if not os.path.exists(target_db):
        print(f"REFUSING: target DB does not exist: {target_db}")
        return 2

    # 3. Set EMPIRE_DATA_DIR before importing app.database so engine matches
    os.environ["EMPIRE_DATA_DIR"] = os.path.dirname(target_db)

    from sqlalchemy import inspect
    from app.database import Base, engine
    from app.models.crypto_payment import CryptoPayment, CryptoLedger  # noqa: F401

    # 4. Confirm engine.url agrees with our target
    if engine.url.database != target_db:
        print(f"MISMATCH: app.database.engine points at {engine.url.database}")
        print(f"          script target is                  {target_db}")
        print("Refusing to proceed — investigate before re-running.")
        return 3

    print(f"Target DB: {target_db}")
    insp = inspect(engine)
    targets = [CryptoPayment.__table__, CryptoLedger.__table__]
    Base.metadata.create_all(bind=engine, tables=targets)
    for tbl in ("crypto_payments", "crypto_ledger"):
        if insp.has_table(tbl):
            cols = [c["name"] for c in insp.get_columns(tbl)]
            print(f"  OK   {tbl} ({len(cols)} columns)")
        else:
            print(f"  FAIL {tbl} still missing")
            return 1
    print("Done. The scheduler's expire_crypto_payments job will stop failing "
          "on its next 15-minute cycle. No service restart needed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())