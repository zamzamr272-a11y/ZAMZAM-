"""Small polling worker for scheduled recurring transactions.

Run as a separate process/container: python -m app.recurring_worker
The API and worker must point at the same PostgreSQL database.
"""
from __future__ import annotations

import logging
import os
import time

from app.main import SessionLocal, process_due_recurring

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("nexora.recurring")


def main() -> None:
    interval = max(60, int(os.getenv("RECURRING_POLL_SECONDS", "900")))
    logger.info("Recurring worker started; poll interval=%s seconds", interval)
    while True:
        db = SessionLocal()
        try:
            count = process_due_recurring(db)
            if count:
                logger.info("Created %s scheduled transaction(s)", count)
        except Exception:
            logger.exception("Recurring run failed; will retry on the next poll")
            db.rollback()
        finally:
            db.close()
        time.sleep(interval)


if __name__ == "__main__":
    main()
