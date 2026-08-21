from __future__ import annotations

import logging
import time

from campus_ai.config import get_settings
from campus_ai.db import SessionLocal
from campus_ai.handlers import HANDLERS
from campus_ai.jobs import claim_job, complete_job, fail_job, recover_stale_jobs


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)


def run_forever() -> None:
    settings = get_settings()
    logger.info("worker_started kinds=%s", settings.enabled_job_kinds or "all")
    while True:
        with SessionLocal() as session:
            recovered = recover_stale_jobs(session, settings.job_lock_timeout_seconds)
            if recovered:
                logger.warning("recovered_stale_jobs count=%s", recovered)
            job = claim_job(session, settings.enabled_job_kinds)
            if job is None:
                time.sleep(settings.worker_poll_seconds)
                continue
            try:
                handler = HANDLERS[job.kind]
                result = handler(session, job.payload)
            except Exception as exc:
                logger.exception("job_failed id=%s kind=%s", job.id, job.kind)
                fail_job(session, job, exc)
            else:
                complete_job(session, job, result)
                logger.info("job_completed id=%s kind=%s", job.id, job.kind)


if __name__ == "__main__":
    run_forever()
