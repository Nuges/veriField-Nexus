"""
=============================================================================
VeriField Nexus — CSI Registry Sync Client Service
=============================================================================
Communicates with Carbon Standards International API nodes, executing
STOCK (pyrolysis batch production) and SINK (matrix application) registry logs.
=============================================================================
"""

import uuid
import httpx
import asyncio
import logging
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.models.carbon_sink import CSinkUnit, CSinkTransaction, BiocharBatch, BiomassProfile, KilnProfile, QrRecord
from app.models.activity import Activity


class CSIRegistryService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.logger = logging.getLogger("verifield.services.csi_registry")

    async def sync_bundle(self, bundle: CSinkUnit) -> dict:
        """
        Executes double-entry sync for a C-Sink Unit Bundle with CSI Global Registry:
        1. STOCK Transaction (Production Batch logging)
        2. SINK Transaction (Application and Matrix logging)
        
        Uses basic/bearer authentication and exponential backoff retry.
        """
        # Fetch constituent activities to build audit pack
        act_res = await self.db.execute(
            select(Activity).where(Activity.c_sink_unit_id == bundle.id)
        )
        activities = act_res.scalars().all()
        if not activities:
            return {"status": "failed", "errors": ["Bundle contains no activities."]}

        # Resolve credentials
        # We try to use configured settings, defaulting to local dry-run if credentials are empty
        api_url = getattr(settings, "csi_api_url", "https://api.carbon-standards.info/v1")
        api_key = getattr(settings, "csi_api_key", None)

        self.logger.info(f"Initiating CSI registry sync for bundle {bundle.id} (size: {len(activities)})...")

        # ----------------------------------------------------
        # 1. STOCK Transaction (Pyrolysis production logging)
        # ----------------------------------------------------
        # Query the biochar batch profile
        first_act = activities[0]
        batch_id_str = first_act.activity_data.get("biomass_id")
        batch_number = first_act.activity_data.get("batch_number", "BATCH-UNK")
        
        stock_payload = {
            "transaction": {
                "type": "STOCK",
                "client_id": str(bundle.id),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "batch_reference": batch_number,
                "biomass_type": bundle.biomass_type,
                "pyrolysis_technology": bundle.pyrolysis_technology,
                "carbon_content_pct": float(bundle.carbon_content_pct),
                "total_yield_t": round(sum(float(a.activity_data.get("batch_weight_kg", 0.0)) for a in activities) / 1000.0, 4),
                "gps": bundle.gps,
                "audit_trace_hash": str(uuid.uuid4())
            }
        }

        # ----------------------------------------------------
        # 2. SINK Transaction (Final matrix application)
        # ----------------------------------------------------
        sink_payload = {
            "transaction": {
                "type": "SINK",
                "client_id": str(bundle.id),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "stock_reference_id": str(bundle.id), # links sink back to production stock
                "application_matrix": bundle.matrix_category,
                "tco2e_issued": round(bundle.total_co2e_t, 4),
                "sinks": [
                    {
                        "activity_id": str(a.id),
                        "gps": {"latitude": a.latitude, "longitude": a.longitude},
                        "moisture_content_pct": float(a.activity_data.get("moisture_content_pct", 0.0)),
                        "net_applied_kg": float(a.activity_data.get("batch_weight_kg", 0.0)),
                        "qr_code": a.activity_data.get("qr_id", "N/A"),
                        "captured_at": a.captured_at.isoformat() if a.captured_at else None
                    }
                    for a in activities
                ]
            }
        }

        # Create local transaction logs as PENDING
        stock_tx = CSinkTransaction(
            c_sink_unit_id=bundle.id,
            transaction_type="STOCK",
            payload=stock_payload,
            status="PENDING"
        )
        sink_tx = CSinkTransaction(
            c_sink_unit_id=bundle.id,
            transaction_type="SINK",
            payload=sink_payload,
            status="PENDING"
        )
        self.db.add(stock_tx)
        self.db.add(sink_tx)
        await self.db.commit()

        if not api_key:
            # Dry-run mode: Mock success
            self.logger.warning("CSI API Key not configured. Simulating dry-run sync locally.")
            
            stock_tx.status = "SUCCESS"
            stock_tx.registry_tx_id = f"TX-STOCK-MOCK-{str(uuid.uuid4())[:8]}"
            stock_tx.response_log = "Dry-run mode. Local simulation successful."

            sink_tx.status = "SUCCESS"
            sink_tx.registry_tx_id = f"TX-SINK-MOCK-{str(uuid.uuid4())[:8]}"
            sink_tx.response_log = "Dry-run mode. Local simulation successful."
            
            await self.db.commit()
            return {
                "status": "success",
                "message": "Dry-run sync completed successfully.",
                "stock_tx_id": stock_tx.registry_tx_id,
                "sink_tx_id": sink_tx.registry_tx_id,
                "total_co2e_t": round(bundle.total_co2e_t, 4)
            }

        # Programmatic HTTP POST calls with 3 attempts retry logic
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        # Call STOCK endpoint
        stock_success = await self._post_transaction(
            f"{api_url}/transactions/stock", stock_payload, headers, stock_tx
        )
        if not stock_success:
            return {
                "status": "failed",
                "errors": [f"STOCK transaction failed: {stock_tx.response_log}"]
            }

        # Call SINK endpoint
        sink_success = await self._post_transaction(
            f"{api_url}/transactions/sink", sink_payload, headers, sink_tx
        )
        if not sink_success:
            return {
                "status": "failed",
                "errors": [f"SINK transaction failed: {sink_tx.response_log}"]
            }

        return {
            "status": "success",
            "message": "C-Sink Unit Bundle successfully registered on CSI registry.",
            "stock_tx_id": stock_tx.registry_tx_id,
            "sink_tx_id": sink_tx.registry_tx_id,
            "total_co2e_t": round(bundle.total_co2e_t, 4)
        }

    async def _post_transaction(
        self, url: str, payload: dict, headers: dict, tx_model: CSinkTransaction
    ) -> bool:
        """Helper to post transactions with 3-attempt exponential backoff."""
        for attempt in range(3):
            try:
                self.logger.info(f"Calling CSI registry API ({attempt+1}/3) at {url}...")
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.post(url, json=payload, headers=headers)
                    if resp.status_code in (200, 201, 202):
                        resp_json = resp.json()
                        tx_model.status = "SUCCESS"
                        tx_model.registry_tx_id = resp_json.get("transaction_id", f"TX-REG-{uuid.uuid4().hex[:8]}")
                        tx_model.response_log = f"Status {resp.status_code}: {resp.text}"
                        await self.db.commit()
                        return True
                    else:
                        tx_model.response_log = f"API returned error status {resp.status_code}: {resp.text}"
                        await self.db.commit()
            except Exception as e:
                tx_model.response_log = f"Connection error: {str(e)}"
                await self.db.commit()

            if attempt < 2:
                await asyncio.sleep(2.0 * (2 ** attempt))

        tx_model.status = "FAILED"
        await self.db.commit()
        return False
