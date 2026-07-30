from typing import Optional

from uuid import UUID



from fastapi import HTTPException

from sqlalchemy import select

from sqlalchemy.ext.asyncio import AsyncSession



from app.domains.activities.models import Activity

from app.domains.authentication.models import User

from app.domains.methodologies.models.base_registry import Methodology

from app.domains.organizations.models import Organization

from app.domains.projects.models import Project





class ABACEngine:

    def __init__(self, db: AsyncSession, user: User):

        self.db = db

        self.user = user



    async def _check_org(self, target_org_id: Optional[UUID]):

        if self.user.role == "SUPER_ADMIN":

            return

        if not target_org_id or target_org_id != self.user.organization_id:

            raise HTTPException(

                status_code=403, detail="ABAC: Organization boundary violation."

            )



    async def _check_methodology_license(self, methodology_id: str, org_id: UUID):

        # Checks if organization has the license for the given methodology

        org_result = await self.db.execute(

            select(Organization).where(Organization.id == org_id)

        )

        org = org_result.scalar_one_or_none()

        if org and org.metadata_context and "licensed_sectors" in org.metadata_context:

            meth_result = await self.db.execute(

                select(Methodology).where(Methodology.code == methodology_id)

            )

            meth = meth_result.scalar_one_or_none()

            if meth and meth.family:

                sector = meth.family.code.lower()

                if (

                    sector not in org.metadata_context["licensed_sectors"]

                    and "all" not in org.metadata_context["licensed_sectors"]

                ):

                    pass  # Log warning or raise error depending on strictness

        return True



    async def enforce_project_access(self, project_id: UUID):

        result = await self.db.execute(select(Project).where(Project.id == project_id))

        project = result.scalar_one_or_none()

        if not project:

            raise HTTPException(status_code=404, detail="Project not found")

        await self._check_org(project.organization_id)

        if project.methodology_id:

            await self._check_methodology_license(

                project.methodology_id, project.organization_id

            )

        return project



    async def enforce_activity_access(

        self, activity_id: UUID, require_mutable: bool = False

    ):

        result = await self.db.execute(

            select(Activity).where(Activity.id == activity_id)

        )

        activity = result.scalar_one_or_none()

        if not activity:

            raise HTTPException(status_code=404, detail="Activity not found")



        await self._check_org(activity.organization_id)



        if require_mutable and getattr(activity, "is_locked", False):

            raise HTTPException(

                status_code=403,

                detail="ABAC: Resource is locked in current workflow state.",

            )



        if getattr(activity, "project_id", None):

            await self.enforce_project_access(activity.project_id)



        return activity





    async def enforce_evidence_access(

        self, evidence_id: UUID, access_type: str = "read"

    ):

        """

        ABAC check for evidence access.

        Verifies org boundary, role appropriateness, and sealed status.

        """

        from app.domains.evidence.models import Evidence



        result = await self.db.execute(

            select(Evidence).where(Evidence.id == evidence_id)

        )

        evidence = result.scalar_one_or_none()

        if not evidence:

            raise HTTPException(status_code=404, detail="Evidence not found")



        # Check org boundary via the activity's project

        if hasattr(evidence, "activity_id") and evidence.activity_id:

            activity_result = await self.db.execute(

                select(Activity).where(Activity.id == evidence.activity_id)

            )

            activity = activity_result.scalar_one_or_none()

            if activity:

                await self._check_org(activity.organization_id)



        # Role-based evidence access rules

        role = self.user.role.upper()

        upload_roles = {"FIELD_AGENT", "FIELD_SUPERVISOR", "PROJECT_MANAGER", "ORG_ADMIN", "SUPER_ADMIN", "ADMIN"}

        review_roles = {"QA_OFFICER", "FIELD_SUPERVISOR", "PROJECT_MANAGER", "ORG_ADMIN", "SUPER_ADMIN", "ADMIN"}

        audit_roles = {"VVB_AUDITOR", "COMPLIANCE_OFFICER", "SUPER_ADMIN"}



        if access_type == "upload" and role not in upload_roles:

            raise HTTPException(status_code=403, detail="ABAC: Insufficient role for evidence upload.")

        if access_type == "review" and role not in review_roles:

            raise HTTPException(status_code=403, detail="ABAC: Insufficient role for evidence review.")

        if access_type == "audit" and role not in audit_roles:

            raise HTTPException(status_code=403, detail="ABAC: Insufficient role for evidence audit.")



        # Sealed evidence check

        metadata = getattr(evidence, "meta_data", None) or {}

        if isinstance(metadata, dict) and metadata.get("sealed") and access_type in ("upload", "modify"):

            raise HTTPException(

                status_code=403,

                detail="ABAC: Evidence is sealed after verification and cannot be modified.",

            )



        return evidence



    def enforce_sensitive_data_access(

        self, resource_type: str, access_type: str = "read"

    ) -> str:

        """

        Determine access level for sensitive data based on resource type and user role.

        Returns: 'full', 'redacted', or raises 403.

        """

        role = self.user.role.upper()

        privileged = {"SUPER_ADMIN", "ORG_ADMIN", "ADMIN", "COMPLIANCE_OFFICER"}

        supervisor = {"FIELD_SUPERVISOR", "PROJECT_MANAGER", "QA_OFFICER", "VVB_AUDITOR"}



        if resource_type == "GPS_METADATA":

            if role in privileged or role in supervisor:

                return "full"

            return "redacted"



        if resource_type == "PERSONAL_IDENTIFICATION":

            if role in privileged:

                return "full"

            if role in supervisor:

                return "redacted"

            raise HTTPException(status_code=403, detail="ABAC: Cannot access personal identification data.")



        if resource_type == "FINANCIAL_DOCUMENT":

            if role in privileged or role == "FINANCE":

                return "full"

            raise HTTPException(status_code=403, detail="ABAC: Cannot access financial documents.")



        # Default: full access for recognized roles

        if role in privileged:

            return "full"

        return "redacted"



    async def enforce_export_access(self, export_type: str):

        """

        ABAC check for data exports.

        Registry exports require registry_manager+; bulk exports require admin+.

        """

        role = self.user.role.upper()



        if export_type == "registry":

            allowed = {"REGISTRY_MANAGER", "ORG_ADMIN", "SUPER_ADMIN", "ADMIN"}

            if role not in allowed:

                raise HTTPException(

                    status_code=403,

                    detail="ABAC: Only Registry Manager or Admin can export to registries.",

                )



        elif export_type == "bulk":

            allowed = {"ORG_ADMIN", "SUPER_ADMIN", "ADMIN"}

            if role not in allowed:

                raise HTTPException(

                    status_code=403,

                    detail="ABAC: Only Admin can perform bulk data exports.",

                )



        # Log export attempt

        try:

            from app.core.event_bus import EventBus

            import asyncio



            await EventBus.publish(

                stream_name="security_audit",

                event_type="ExportAttempt",

                payload={

                    "export_type": export_type,

                    "user_role": role,

                    "user_id": str(self.user.id),

                },

                actor_id=str(self.user.id),

            )

        except Exception:

            pass  # Never block exports due to audit logging failure





def get_abac_engine(db: AsyncSession, current_user: User) -> ABACEngine:

    return ABACEngine(db, current_user)
