from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.domains.authentication.models import User

from .repository import FinanceRepository
from .schemas import TransactionCreate, TransactionResponse
from .service import FinanceService

router = APIRouter()


def get_finance_service(db: AsyncSession = Depends(get_db)) -> FinanceService:
    repository = FinanceRepository(db)
    return FinanceService(repository)


@router.post(
    "/transactions",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def process_transaction(
    data: TransactionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: FinanceService = Depends(get_finance_service),
):
    if current_user.role not in ["SUPER_ADMIN", "ORG_ADMIN"]:
        raise HTTPException(
            status_code=403, detail="Not authorized to process transactions"
        )

    return await service.process_transaction(data, actor_id=current_user.id, db=db)


@router.get("/transactions/{tx_id}", response_model=TransactionResponse)
async def get_transaction(
    tx_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: FinanceService = Depends(get_finance_service),
):
    tx = await service.get_transaction(tx_id)
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return tx
