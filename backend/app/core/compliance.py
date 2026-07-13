import logging
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.event_bus import EventBus
from app.core.rules import RuleEngine

logger = logging.getLogger("verifield.compliance")


class IComplianceTarget:
    """
    Common generic interface for any entity that can be subjected to compliance checks.
    """

    def __init__(
        self,
        target_id: str,
        target_type: str,
        data: Dict[str, Any],
        context: Dict[str, Any],
    ):
        self.target_id = target_id
        self.target_type = target_type
        self.data = data
        self.context = context


class ComplianceService:
    """
    Global Platform Compliance Service.
    Resolves targets via IComplianceTarget and runs rules against them.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def execute_compliance_run(
        self,
        target: IComplianceTarget,
        rule_packs: List[Dict[str, Any]],
        user_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        """
        Executes a compliance run against a generic target using a set of rule packs.
        Emits events upon completion.
        """
        logger.info(
            f"Starting compliance run for {target.target_type} ({target.target_id})"
        )

        all_reports = []
        overall_passed = True
        total_rules = 0
        failed_rules = 0

        # Flatten and evaluate all rules
        for pack in rule_packs:
            pack_name = pack.get("name", "Unnamed Pack")
            rules = pack.get("rules", [])

            # Use the rule engine
            report = RuleEngine.execute_rule_pack(rules, target.data)

            all_reports.append({"pack_name": pack_name, "report": report})

            total_rules += report["total"]
            failed_rules += report["failed"]
            if not report["is_compliant"]:
                overall_passed = False

        final_result = {
            "target_id": target.target_id,
            "target_type": target.target_type,
            "overall_compliant": overall_passed,
            "total_rules_evaluated": total_rules,
            "failed_rules": failed_rules,
            "pack_reports": all_reports,
        }

        # Emit Platform Event
        await EventBus.publish(
            event_type="ComplianceCompleted",
            payload=final_result,
            user_id=user_id,
            db=self.db,
        )

        return final_result
