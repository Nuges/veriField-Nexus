import asyncio
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Tuple, Set, Dict
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.biochar.models import (
    BiocharBatch,
    BiocharEndUseRecord,
    BiocharStorageEvent,
    BiocharMaterialTransaction,
    FeedstockLot,
    FeedstockRunAllocation,
    ProductionRun,
)
from app.domains.biochar.schemas import (
    MassBalanceReconciliationResponse,
    FeedstockAllocationResponse,
)


class BiocharMassBalanceEngine:
    """
    Material Balance & Conservation Engine for Biochar Value Chain.
    Enforces deterministic mass conservation across:
    Feedstock Lot -> Production Run -> Biochar Output Batch -> Terminal Dispositions.
    Guarantees row-level locking (with_for_update) and authoritative Decimal precision.
    """

    _batch_locks: Dict[UUID, asyncio.Lock] = {}

    @classmethod
    def get_batch_lock(cls, batch_id: UUID) -> asyncio.Lock:
        """Returns or creates an asynchronous lock for a specific batch to guarantee concurrency isolation."""
        if batch_id not in cls._batch_locks:
            cls._batch_locks[batch_id] = asyncio.Lock()
        return cls._batch_locks[batch_id]

    ALLOWED_TRANSITIONS: Dict[str, Set[str]] = {
        "PRODUCED": {"STORAGE", "SHIPMENT", "END_USE"},
        "STORAGE": {"STORAGE", "SHIPMENT", "END_USE"},
        "SHIPMENT": {"DELIVERY", "STORAGE"},
        "DELIVERY": {"STORAGE", "END_USE"},
        "END_USE": set(),  # Terminal disposition: cannot transition backwards
    }

    @classmethod
    def validate_material_transition(cls, from_state: str, to_state: str) -> None:
        """
        Validates material ledger transitions according to official state machine:
        PRODUCED -> STORAGE -> SHIPMENT -> DELIVERY -> END_USE.
        Blocks backward or invalid transitions such as END_USE -> SHIPMENT.
        """
        f = (from_state or "").upper().strip()
        t = (to_state or "").upper().strip()

        allowed = cls.ALLOWED_TRANSITIONS.get(f)
        if allowed is None:
            valid_states = {"PRODUCED", "STORAGE", "SHIPMENT", "DELIVERY", "END_USE"}
            if t not in valid_states:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid material state '{to_state}'. Must be one of {sorted(valid_states)}.",
                )
            return

        if t not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Invalid material transaction state transition from '{f}' to '{t}'. "
                    f"Permitted destination states: {sorted(list(allowed)) or 'None (Terminal state)'}."
                ),
            )

    @staticmethod
    async def allocate_feedstock_lot(
        db: AsyncSession,
        lot_id: UUID,
        production_run_id: UUID,
        allocated_wet_mass_tonnes: float,
    ) -> FeedstockRunAllocation:
        """
        Atomically allocates biomass from a Feedstock Lot to a Production Run with row-level locking.
        Rejects request if total allocated mass would exceed received mass.
        """
        stmt_lot = select(FeedstockLot).where(FeedstockLot.id == lot_id).with_for_update()
        res_lot = await db.execute(stmt_lot)
        lot = res_lot.scalar_one_or_none()
        if not lot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Feedstock Lot {lot_id} not found.",
            )

        stmt_run = select(ProductionRun).where(ProductionRun.id == production_run_id).with_for_update()
        res_run = await db.execute(stmt_run)
        run = res_run.scalar_one_or_none()
        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Production Run {production_run_id} not found.",
            )

        # Decimal arithmetic for authoritative mass conservation
        mass_received = Decimal(str(lot.mass_received_tonnes))
        current_alloc = Decimal(str(lot.allocated_mass_tonnes or 0.0))
        req_alloc = Decimal(str(allocated_wet_mass_tonnes))

        remaining_mass = mass_received - current_alloc
        if req_alloc > remaining_mass + Decimal("0.000001"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Mass balance violation: Feedstock Lot {lot.lot_number} has only "
                    f"{float(remaining_mass):.3f} t available, but {float(req_alloc):.3f} t was requested."
                ),
            )

        # Compute dry mass fraction with Decimal
        moisture_pct = Decimal(str(lot.moisture_content_pct or 0.0))
        dry_fraction = Decimal("1.0") - (moisture_pct / Decimal("100.0"))
        allocated_dry = (req_alloc * dry_fraction).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)

        # Update Lot
        lot.allocated_mass_tonnes = float(current_alloc + req_alloc)

        # Create allocation
        allocation = FeedstockRunAllocation(
            lot_id=lot.id,
            production_run_id=run.id,
            allocated_wet_mass_tonnes=float(req_alloc),
            allocated_dry_mass_tonnes=float(allocated_dry),
        )
        db.add(allocation)

        # Update Run totals
        run_wet = Decimal(str(run.total_feedstock_input_tonnes or 0.0)) + req_alloc
        run_dry = Decimal(str(run.total_feedstock_dry_tonnes or 0.0)) + allocated_dry
        run.total_feedstock_input_tonnes = float(run_wet)
        run.total_feedstock_dry_tonnes = float(run_dry)

        await db.commit()
        await db.refresh(allocation)
        return allocation

    @staticmethod
    async def allocate_batch_end_use(
        db: AsyncSession,
        batch_id: UUID,
        quantity_tonnes: float,
    ) -> BiocharBatch:
        """
        Atomically checks and allocates mass from a Biochar Batch with row-level locking (with_for_update).
        Prevents concurrent over-allocation of batch output mass.
        """
        stmt_batch = select(BiocharBatch).where(BiocharBatch.id == batch_id).with_for_update()
        res_batch = await db.execute(stmt_batch)
        batch = res_batch.scalar_one_or_none()
        if not batch:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Biochar Batch {batch_id} not found.",
            )

        total_yield = Decimal(str(batch.biochar_yield_tonnes or 0.0))
        current_alloc = Decimal(str(batch.mass_balance_allocated_tonnes or 0.0))
        req_qty = Decimal(str(quantity_tonnes))

        available = total_yield - current_alloc
        if req_qty > available + Decimal("0.000001"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Mass balance violation: Batch {batch.batch_number} has only "
                    f"{float(max(Decimal('0.0'), available)):.3f} t available, "
                    f"but {float(req_qty):.3f} t was requested."
                ),
            )

        batch.mass_balance_allocated_tonnes = float(current_alloc + req_qty)
        return batch

    @staticmethod
    async def reconcile_batch(
        db: AsyncSession,
        batch_id: UUID,
        tolerated_variance_tonnes: float = 0.01,
    ) -> MassBalanceReconciliationResponse:
        """
        Deterministic reconciliation of a Biochar Batch using Decimal arithmetic:
        original_produced_mass == current_inventory + terminal_end_use + documented_losses + rejected.
        Reconciles terminal dispositions without double-counting successive logistics custody events.
        """
        stmt_batch = select(BiocharBatch).where(BiocharBatch.id == batch_id).with_for_update()
        res_batch = await db.execute(stmt_batch)
        batch = res_batch.scalar_one_or_none()
        if not batch:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Biochar Batch {batch_id} not found.",
            )

        original_produced = Decimal(str(batch.biochar_yield_tonnes or 0.0))
        tol_variance = Decimal(str(tolerated_variance_tonnes))

        # 1. Terminal End-Use (Soil or Non-Soil durable application, non-rejected)
        stmt_end_use = select(
            func.coalesce(func.sum(BiocharEndUseRecord.applied_quantity_tonnes), 0.0)
        ).where(
            BiocharEndUseRecord.batch_id == batch.id,
            BiocharEndUseRecord.verification_status != "REJECTED",
        )
        res_eu = await db.execute(stmt_end_use)
        terminal_end_use = Decimal(str(res_eu.scalar() or 0.0))

        # 2. Documented Losses & Handling Degradation
        stmt_losses = select(
            func.coalesce(func.sum(BiocharStorageEvent.loss_or_damage_tonnes), 0.0)
        ).where(BiocharStorageEvent.batch_id == batch.id)
        res_losses = await db.execute(stmt_losses)
        documented_losses = Decimal(str(res_losses.scalar() or 0.0))

        # 3. Rejected Material
        stmt_rej = select(
            func.coalesce(func.sum(BiocharEndUseRecord.applied_quantity_tonnes), 0.0)
        ).where(
            BiocharEndUseRecord.batch_id == batch.id,
            BiocharEndUseRecord.verification_status == "REJECTED",
        )
        res_rej = await db.execute(stmt_rej)
        rejected = Decimal(str(res_rej.scalar() or 0.0))

        terminal_dispositions = terminal_end_use + documented_losses + rejected

        if terminal_dispositions > original_produced + tol_variance:
            current_inventory = Decimal("0.0")
            total_reconciled = terminal_dispositions
            discrepancy = terminal_dispositions - original_produced
            recon_status = "OVER_ALLOCATED"
            is_valid = False
            notes = (
                f"Critical Mass Balance Over-Allocation: Terminal dispositions ({float(terminal_dispositions):.3f} t) "
                f"exceed original produced mass ({float(original_produced):.3f} t) by {float(discrepancy):.3f} t."
            )
        else:
            current_inventory = max(Decimal("0.0"), original_produced - terminal_dispositions)
            total_reconciled = current_inventory + terminal_dispositions
            discrepancy = total_reconciled - original_produced
            recon_status = "RECONCILED"
            is_valid = True
            notes = "Mass balance fully reconciled within tolerance."

        # Update batch status
        batch.mass_balance_allocated_tonnes = float(terminal_dispositions)
        batch.mass_balance_status = recon_status
        await db.commit()

        return MassBalanceReconciliationResponse(
            batch_id=batch.id,
            batch_number=batch.batch_number,
            original_produced_mass_tonnes=float(original_produced),
            current_inventory_tonnes=float(current_inventory),
            terminal_end_use_tonnes=float(terminal_end_use),
            documented_losses_tonnes=float(documented_losses),
            rejected_tonnes=float(rejected),
            total_reconciled_tonnes=float(total_reconciled),
            discrepancy_tonnes=float(discrepancy),
            status=recon_status,
            is_valid=is_valid,
            tolerated_variance=float(tol_variance),
            notes=notes,
        )
