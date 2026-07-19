import asyncio
import logging
from sqlalchemy import select, update
from app.db.session import async_session_factory
from app.domains.organizations.models import Organization
from app.domains.projects.models import Project
from app.domains.methodologies.models.base_registry import Methodology, MethodologyFamily

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("migrate_cios")

async def migrate():
    async with async_session_factory() as db:
        logger.info("Starting CIOS Architecture Migration...")
        
        # 1. Fetch Methodology Families (Sectors) mapping
        stmt_fam = select(MethodologyFamily)
        res_fam = await db.execute(stmt_fam)
        families = res_fam.scalars().all()
        family_map = {f.id: f.code for f in families}
        
        # 2. Fetch Methodologies to map methodology_id -> family_id (sector_id)
        stmt_meth = select(Methodology)
        res_meth = await db.execute(stmt_meth)
        methodologies = res_meth.scalars().all()
        meth_to_family = {m.id: m.family_id for m in methodologies}
        
        # 3. Migrate Projects
        stmt_proj = select(Project)
        res_proj = await db.execute(stmt_proj)
        projects = res_proj.scalars().all()
        
        org_sector_map = {}
        
        for project in projects:
            if not project.sector_id:
                if project.methodology_id and project.methodology_id in meth_to_family:
                    family_id = meth_to_family[project.methodology_id]
                    project.sector_id = family_id
                    
                    # Track sectors per organization
                    if project.organization_id:
                        org_id_str = str(project.organization_id)
                        if org_id_str not in org_sector_map:
                            org_sector_map[org_id_str] = set()
                        family_code = family_map.get(family_id)
                        if family_code:
                            org_sector_map[org_id_str].add(family_code)
                    
                    logger.info(f"Mapped Project {project.id} to Sector {family_id}")
                else:
                    logger.warning(f"Project {project.id} missing methodology_id or unknown. Marking 'Migration Required'.")
                    # Using metadata_context to flag migration requirement isn't on Project, we will just leave sector_id null.

        # 4. Migrate Organizations
        stmt_orgs = select(Organization)
        res_orgs = await db.execute(stmt_orgs)
        orgs = res_orgs.scalars().all()
        
        for org in orgs:
            org_id_str = str(org.id)
            current_sectors = set(org.licensed_sectors or [])
            
            if not current_sectors:
                # Infer from projects
                inferred_sectors = org_sector_map.get(org_id_str, set())
                if inferred_sectors:
                    org.licensed_sectors = list(inferred_sectors)
                    logger.info(f"Inferred licensed_sectors for Org {org.name}: {list(inferred_sectors)}")
                else:
                    # Default
                    org.licensed_sectors = ["cookstove"]
                    logger.info(f"Defaulted licensed_sectors for Org {org.name}: ['cookstove']")

        await db.commit()
        logger.info("Migration completed successfully.")

if __name__ == "__main__":
    asyncio.run(migrate())
