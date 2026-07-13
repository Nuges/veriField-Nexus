import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.compliance_engine.models import ComplianceRun
from app.domains.jurisdictions.models import Jurisdiction

from app.domains.projects.models import Project
from app.domains.activities.models import Activity
from app.domains.assets.models import Asset

logger = logging.getLogger("verifield.compliance")


class ComplianceService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def evaluate_project(self, project_id: uuid.UUID) -> ComplianceRun:
        """
        Executes the compliance pipeline:
        Load Rules -> Validate -> Generate Findings -> Store Report
        """
        # 1. Fetch project details
        project = await self.db.get(Project, project_id)
        if not project:
            raise ValueError("Project not found")

        # 2. Load rules dynamically
        rules = await self.load_rules(project)

        conformance_issues = []
        risk_score = 0.0

        # 3. Validate GPS bounds rules
        gps_passed = await self.validate_gps_bounds(project, rules, conformance_issues)
        if not gps_passed:
            risk_score += rules.get("risk_weights", {}).get("gps_bounds", 2.0)

        # 4. Validate Verifier conflict of interest
        verifier_passed = await self.validate_verifier_independence(
            project, conformance_issues
        )
        if not verifier_passed:
            risk_score += rules.get("risk_weights", {}).get("verifier_conflict", 3.0)

        # 5. Validate Evidence completeness checklist
        evidence_passed = await self.validate_evidence_completeness(
            project, rules, conformance_issues
        )
        if not evidence_passed:
            risk_score += rules.get("risk_weights", {}).get(
                "evidence_completeness", 2.5
            )

        # 6. Validate Sampling coverage
        sampling_status = await self.validate_sampling_coverage(
            project, rules, conformance_issues
        )
        if sampling_status == "FAILED":
            risk_score += rules.get("risk_weights", {}).get("sampling_coverage", 1.5)

        # 7. Generate findings & eligibility status
        eligibility_status = "PASSED"
        if any(issue["severity"] == "CRITICAL" for issue in conformance_issues):
            eligibility_status = "FAILED"

        risk_score = min(10.0, risk_score)

        # 8. Store report
        return await self.store_report(
            project_id,
            eligibility_status,
            sampling_status,
            conformance_issues,
            risk_score,
        )

    async def load_rules(self, project: Project) -> Dict[str, Any]:
        """Loads rules dynamically from country jurisdiction or methodology defaults."""
        rules = {
            "gps_bounds": None,
            "min_evidence_photos": 2,
            "min_sampling_pct": 10.0,
            "risk_weights": {
                "gps_bounds": 2.0,
                "verifier_conflict": 3.0,
                "evidence_completeness": 2.5,
                "sampling_coverage": 1.5,
            },
        }

        # Check database jurisdiction
        if project.jurisdiction_id:
            jur = await self.db.get(Jurisdiction, project.jurisdiction_id)
            if jur:
                # Merge dynamic settings
                req = jur.reporting_requirements or {}
                rules["gps_bounds"] = req.get("gps_bounds")
                rules["min_evidence_photos"] = req.get("min_evidence_photos", 2)
                rules["min_sampling_pct"] = req.get("min_sampling_pct", 10.0)

        return rules

    async def validate_gps_bounds(
        self, project: Project, rules: dict, issues: list
    ) -> bool:
        bounds = rules.get("gps_bounds")
        if not bounds:
            return True

        lat_min, lat_max = bounds["lat_min"], bounds["lat_max"]
        lon_min, lon_max = bounds["lon_min"], bounds["lon_max"]

        # Retrieve activities
        res = await self.db.execute(
            select(Activity)
            .join(Asset, Activity.asset_id == Asset.id)
            .where(Asset.project_id == project.id)
            .where(Activity.status == "verified")
        )
        activities = res.scalars().all()

        out_of_bounds = []
        for act in activities:
            lat = act.latitude
            lon = act.longitude
            if lat and lon:
                if not (lat_min <= lat <= lat_max) or not (lon_min <= lon <= lon_max):
                    out_of_bounds.append(act.id)

        if out_of_bounds:
            issues.append(
                {
                    "category": "GPS_BOUNDS",
                    "severity": "CRITICAL",
                    "message": f"{len(out_of_bounds)} activities contain GPS coordinates outside {project.country} regional boundaries.",
                    "details": [str(uid) for uid in out_of_bounds],
                }
            )
            return False
        return True

    async def validate_verifier_independence(
        self, project: Project, issues: list
    ) -> bool:
        from app.domains.ledger.models import Signature

        res = await self.db.execute(
            select(Signature)
            .where(Signature.project_id == project.id)
            .where(Signature.signer_role == "VERIFIER")
        )
        signatures = res.scalars().all()

        from app.domains.authentication.models import User

        conflict_detected = False

        for sig in signatures:
            signer_id = sig.signer_id
            if signer_id:
                signer = await self.db.get(User, signer_id)
                if signer and signer.organization_id == project.organization_id:
                    conflict_detected = True
                    issues.append(
                        {
                            "category": "INDEPENDENCE_VIOLATION",
                            "severity": "CRITICAL",
                            "message": f"Conflict of Interest: Verifier '{signer.full_name}' belongs to the same developer organization.",
                            "details": {"verifier_id": str(signer_id)},
                        }
                    )
                    break

        return not conflict_detected

    async def validate_evidence_completeness(
        self, project: Project, rules: dict, issues: list
    ) -> bool:
        res = await self.db.execute(
            select(Activity)
            .join(Asset, Activity.asset_id == Asset.id)
            .where(Asset.project_id == project.id)
        )
        activities = res.scalars().all()

        min_photos = rules.get("min_evidence_photos", 2)
        missing_photos_count = 0

        for act in activities:
            ad = act.activity_data or {}
            images = ad.get("images") or ad.get("image_urls") or []
            # Check single image_url field if list is empty
            if not images and act.image_url:
                images = [act.image_url]

            if len(images) < min_photos:
                missing_photos_count += 1

        if missing_photos_count > 0:
            issues.append(
                {
                    "category": "EVIDENCE_COMPLETENESS",
                    "severity": "WARNING",
                    "message": f"{missing_photos_count} activities are missing required verification photographs.",
                    "details": {"missing_count": missing_photos_count},
                }
            )
            return False
        return True

    async def validate_sampling_coverage(
        self, project: Project, rules: dict, issues: list
    ) -> str:
        total_res = await self.db.execute(
            select(func.count(Activity.id))
            .join(Asset, Activity.asset_id == Asset.id)
            .where(Asset.project_id == project.id)
        )
        total = total_res.scalar() or 0
        if total == 0:
            return "PASSED"

        verified_res = await self.db.execute(
            select(func.count(Activity.id))
            .join(Asset, Activity.asset_id == Asset.id)
            .where(Asset.project_id == project.id)
            .where(Activity.status.in_(["verified", "approved"]))
        )
        verified = verified_res.scalar() or 0
        coverage = (verified / total) * 100.0

        min_sampling = rules.get("min_sampling_pct", 10.0)
        if coverage < min_sampling:
            issues.append(
                {
                    "category": "SAMPLING_FREQUENCY",
                    "severity": "WARNING",
                    "message": f"Verification sampling frequency is {coverage:.1f}%, which is below the {min_sampling}% standard.",
                    "details": {"coverage_pct": coverage},
                }
            )
            return "FAILED"
        return "PASSED"

    async def store_report(
        self,
        project_id: uuid.UUID,
        eligibility_status: str,
        sampling_status: str,
        conformance_issues: list,
        risk_score: float,
    ) -> ComplianceRun:
        res = await self.db.execute(
            select(ComplianceRun).where(ComplianceRun.project_id == project_id)
        )
        run = res.scalar()

        if not run:
            run = ComplianceRun(
                project_id=project_id,
                eligibility_status=eligibility_status,
                sampling_status=sampling_status,
                conformance_issues=conformance_issues,
                risk_score=risk_score,
                last_evaluated=datetime.now(timezone.utc),
            )
            self.db.add(run)
        else:
            run.eligibility_status = eligibility_status
            run.sampling_status = sampling_status
            run.conformance_issues = conformance_issues
            run.risk_score = risk_score
            run.last_evaluated = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(run)
        return run
