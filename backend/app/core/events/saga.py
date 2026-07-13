import logging
import uuid
from typing import Any, Awaitable, Callable, Dict, List

from sqlalchemy import JSON, Column, DateTime, String
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

logger = logging.getLogger("verifield.saga")


class SagaState(Base):
    """
    Tracks the state of a distributed Saga workflow across multiple microservices/domains.
    """

    __tablename__ = "saga_states"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    saga_type = Column(String, nullable=False, index=True)
    status = Column(
        String, nullable=False, default="STARTED"
    )  # STARTED, COMPLETED, COMPENSATING, FAILED, ROLLED_BACK
    current_step = Column(String, nullable=False)
    payload = Column(JSON, default=dict)
    created_at = Column(
        DateTime,
        default=lambda: __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ),
    )
    updated_at = Column(
        DateTime,
        default=lambda: __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ),
        onupdate=lambda: __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ),
    )


class SagaStep:
    def __init__(
        self,
        name: str,
        action: Callable[[AsyncSession, Dict], Awaitable[Dict]],
        compensation: Callable[[AsyncSession, Dict], Awaitable[None]],
    ):
        self.name = name
        self.action = action
        self.compensation = compensation


class SagaOrchestrator:
    """
    Executes distributed transactions using the Saga pattern.
    Supports forward execution and backward compensation on failure.
    """

    def __init__(self, db: AsyncSession, saga_type: str, steps: List[SagaStep]):
        self.db = db
        self.saga_type = saga_type
        self.steps = steps

    async def execute(self, initial_payload: Dict[str, Any]) -> SagaState:
        saga = SagaState(
            id=str(uuid.uuid4()),
            saga_type=self.saga_type,
            status="STARTED",
            current_step=self.steps[0].name if self.steps else "NONE",
            payload=initial_payload,
        )
        self.db.add(saga)
        await self.db.commit()
        await self.db.refresh(saga)

        executed_steps = []

        for step in self.steps:
            try:
                saga.current_step = step.name
                await self.db.commit()

                logger.info(f"Saga {saga.id} executing step {step.name}")

                # Execute step action
                new_payload_data = await step.action(self.db, saga.payload)

                # Merge output back into payload
                saga.payload.update(new_payload_data)
                await self.db.commit()

                executed_steps.append(step)

            except Exception as e:
                logger.error(
                    f"Saga {saga.id} failed at step {step.name}: {e}. Initiating compensation."
                )
                saga.status = "COMPENSATING"
                await self.db.commit()

                await self._compensate(saga, executed_steps)

                saga.status = "ROLLED_BACK"
                await self.db.commit()
                raise RuntimeError(
                    f"Saga {self.saga_type} failed at {step.name} and was rolled back. Cause: {e}"
                )

        saga.status = "COMPLETED"
        await self.db.commit()
        return saga

    async def _compensate(self, saga: SagaState, executed_steps: List[SagaStep]):
        """
        Runs compensation transactions in reverse order of execution.
        """
        for step in reversed(executed_steps):
            logger.info(f"Saga {saga.id} compensating step {step.name}")
            try:
                await step.compensation(self.db, saga.payload)
            except Exception as e:
                logger.critical(
                    f"FATAL: Saga {saga.id} compensation failed at step {step.name}: {e}. Manual intervention required."
                )
                saga.status = "FAILED"
                await self.db.commit()
                raise
