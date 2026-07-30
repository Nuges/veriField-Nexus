from typing import Dict, Any, Optional, List

from datetime import datetime, timezone

import json

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import text, select



logger = logging.getLogger("verifield.ai_memory")



class EnterpriseMemoryService:

    """

    Practical Enterprise Memory System (Session, Workspace, Project, Document, Decision, Organisation, Knowledge, Learning Memory)

    using PostgreSQL & PgVector.

    """

    def __init__(self, db: AsyncSession):

        self.db = db



    async def record_decision(

        self,

        user_id: str,

        project_id: str,

        recommendation_type: str,

        recommendation_payload: Dict[str, Any],

        user_action: str, # ACCEPTED, REJECTED, MODIFIED

        impact_metrics: Optional[Dict[str, Any]] = None

    ) -> Dict[str, Any]:

        """

        Layer 6 & Layer 7: Decision & Learning Memory.

        Records an AI recommendation, the user's decision, and measures operational learning feedback.

        """

        query = text("""

            INSERT INTO ai_decision_memory (

                user_id, project_id, recommendation_type, recommendation_payload, user_action, impact_metrics, created_at

            ) VALUES (

                :user_id, :project_id, :recommendation_type, :recommendation_payload, :user_action, :impact_metrics, NOW()

            )

            RETURNING id, created_at

        """)

        params = {

            "user_id": user_id,

            "project_id": project_id,

            "recommendation_type": recommendation_type,

            "recommendation_payload": json.dumps(recommendation_payload),

            "user_action": user_action,

            "impact_metrics": json.dumps(impact_metrics or {})

        }

        res = await self.db.execute(query, params)

        await self.db.commit()

        row = res.one()

        return {"id": str(row.id), "status": "RECORDED", "created_at": str(row.created_at)}



    async def get_project_memory(self, project_id: str) -> Dict[str, Any]:

        """

        Layer 3 & Layer 4: Project & Knowledge Graph Memory summary for a project.

        """

        query = text("""

            SELECT recommendation_type, user_action, count(*) as count

            FROM ai_decision_memory

            WHERE project_id = :project_id

            GROUP BY recommendation_type, user_action

        """)

        res = await self.db.execute(query, {"project_id": project_id})

        decisions = [dict(r) for r in res.mappings().all()]



        return {

            "project_id": project_id,

            "historical_decisions_summary": decisions,

            "memory_status": "ACTIVE"

        }
