"""Usage ledger billing service.

Records CAPTURE entries on successful run completion and
RELEASE entries on run failure. Idempotent via unique constraint
on (run_id, charge_type).
"""

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.billing import UsageLedger
from app.models.run import Run
from app.models.service import ServiceDefinition

logger = logging.getLogger("neurohub.billing")


def capture_usage(
    session: Session,
    run: Run,
    service: ServiceDefinition | None = None,
) -> UsageLedger | None:
    """Create a CAPTURE ledger entry for a successful run.

    Returns None if already captured (idempotent).
    """
    try:
        entry = UsageLedger(
            institution_id=run.institution_id,
            request_id=run.request_id,
            run_id=run.id,
            service_id=service.id if service else None,
            service_version=service.version if service else None,
            charge_type="CAPTURE",
            units=1,
            unit_price=0,  # placeholder until pricing is implemented
            amount=0,
            currency="KRW",
            idempotency_token=f"capture-{run.id}",
        )
        session.add(entry)
        session.flush()
        logger.info("CAPTURE recorded for run %s", run.id)
        return entry
    except IntegrityError:
        session.rollback()
        logger.info("CAPTURE already exists for run %s, skipping", run.id)
        return None


def release_usage(
    session: Session,
    run: Run,
    service: ServiceDefinition | None = None,
) -> UsageLedger | None:
    """Create a RELEASE (negative) ledger entry for a failed run.

    Returns None if already released (idempotent).
    """
    try:
        entry = UsageLedger(
            institution_id=run.institution_id,
            request_id=run.request_id,
            run_id=run.id,
            service_id=service.id if service else None,
            service_version=service.version if service else None,
            charge_type="RELEASE",
            units=1,
            unit_price=0,
            amount=0,
            currency="KRW",
            idempotency_token=f"release-{run.id}",
        )
        session.add(entry)
        session.flush()
        logger.info("RELEASE recorded for run %s", run.id)
        return entry
    except IntegrityError:
        session.rollback()
        logger.info("RELEASE already exists for run %s, skipping", run.id)
        return None
