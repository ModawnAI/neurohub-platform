import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select

from app.database import async_session_factory
from app.models.outbox import OutboxEvent

logger = logging.getLogger("neurohub.reconciler")


async def run_once() -> None:
    async with async_session_factory() as session:
        result = await session.execute(
            select(OutboxEvent)
            .where(OutboxEvent.status == "PENDING")
            .order_by(OutboxEvent.available_at.asc())
            .limit(50)
        )
        events = result.scalars().all()
        for event in events:
            # TODO: publish into queue and update status based on dispatch result.
            event.status = "PROCESSED"
            event.processed_at = datetime.now(timezone.utc)
        await session.commit()
        logger.info("Reconciler processed %d outbox events", len(events))


async def main():
    while True:
        try:
            await run_once()
        except Exception:
            logger.exception("Reconciler loop failed")
        await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())

