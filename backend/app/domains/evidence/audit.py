"""

=============================================================================

VeriField Nexus — Evidence Audit Service

=============================================================================

Logs every evidence access, download, verification, and seal event

to the EventBus audit stream for immutable compliance tracking.

=============================================================================

"""



import logging

from datetime import datetime, timezone

from typing import Optional

from uuid import UUID



logger = logging.getLogger("verifield.evidence.audit")





class EvidenceAuditService:

    """Tracks all evidence lifecycle events for compliance and forensics."""



    def __init__(self, db=None):

        self.db = db



    async def log_access(

        self,

        evidence_id: UUID,

        user_id: UUID,

        access_type: str,

        ip_address: Optional[str] = None,

    ):

        """Log an evidence access event (view, preview, metadata read)."""

        await self._emit_event(

            event_type="EvidenceAccessed",

            evidence_id=evidence_id,

            actor_id=str(user_id),

            details={

                "access_type": access_type,

                "ip_address": ip_address,

                "timestamp": datetime.now(timezone.utc).isoformat(),

            },

        )



    async def log_download(

        self,

        evidence_id: UUID,

        user_id: UUID,

    ):

        """Log an evidence download event."""

        await self._emit_event(

            event_type="EvidenceDownloaded",

            evidence_id=evidence_id,

            actor_id=str(user_id),

            details={"timestamp": datetime.now(timezone.utc).isoformat()},

        )



    async def log_verification(

        self,

        evidence_id: UUID,

        verifier_id: UUID,

        result: str,

        notes: Optional[str] = None,

    ):

        """Log a verification action on evidence."""

        await self._emit_event(

            event_type="EvidenceVerified",

            evidence_id=evidence_id,

            actor_id=str(verifier_id),

            details={

                "result": result,

                "notes": notes,

                "timestamp": datetime.now(timezone.utc).isoformat(),

            },

        )



    async def log_seal(

        self,

        evidence_id: UUID,

        sealer_id: UUID,

    ):

        """Log evidence sealing (immutability lock)."""

        await self._emit_event(

            event_type="EvidenceSealed",

            evidence_id=evidence_id,

            actor_id=str(sealer_id),

            details={"timestamp": datetime.now(timezone.utc).isoformat()},

        )



    async def log_integrity_check(

        self,

        evidence_id: UUID,

        user_id: UUID,

        result: str,

    ):

        """Log an integrity verification check."""

        await self._emit_event(

            event_type="EvidenceIntegrityChecked",

            evidence_id=evidence_id,

            actor_id=str(user_id),

            details={

                "result": result,

                "timestamp": datetime.now(timezone.utc).isoformat(),

            },

        )



    async def _emit_event(

        self,

        event_type: str,

        evidence_id: UUID,

        actor_id: str,

        details: dict,

    ):

        """Emit to the EventBus audit stream."""

        try:

            from app.core.event_bus import EventBus



            await EventBus.publish(

                stream_name="evidence_audit",

                event_type=event_type,

                payload={

                    "evidence_id": str(evidence_id),

                    **details,

                },

                actor_id=actor_id,

            )

        except Exception as e:

            # Never let audit logging break the main flow

            logger.error(f"Evidence audit event emission failed: {e}")
