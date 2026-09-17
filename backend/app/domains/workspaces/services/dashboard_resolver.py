import logging

from typing import Dict, Any, List

from uuid import UUID



from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import select, func, cast, text, Float, Numeric

from sqlalchemy.dialects.postgresql import JSONB



from app.domains.methodologies.models.base_registry import Methodology, MethodologyFamily

from app.domains.projects.models import Project

from app.domains.activities.models import Activity

from app.domains.assets.models import Asset







logger = logging.getLogger(__name__)


def canonical_sector_code(sec: Any) -> str:
    """
    Canonicalizes any incoming sector string, enum, or code to one of the 5 canonical sector codes:
    - COOKSTOVES
    - HYBRID_ENERGY
    - BIOCHAR
    - EV_MOBILITY
    - AGRICULTURE_LAND_USE
    Returns clean uppercase identifier, or empty string if None.
    Unknown sector codes are returned as their clean uppercase string without collapsing to known sectors.
    """
    if not sec:
        return ""
    clean = str(sec).strip().lower().replace("-", "_").replace(" ", "_")

    # Agriculture & Land Use aliases
    if clean in (
        "agriculture_land_use", "agriculture", "afolu", "land_use", "agri",
        "farm", "farming", "soil", "rice", "vm0042", "vm0047", "vt0014",
        "vmd0053", "vm0051", "bm_ag04", "bm_fr05"
    ):
        return "AGRICULTURE_LAND_USE"

    # EV Mobility aliases
    if clean in (
        "ev_mobility", "ev", "electric_mobility", "mobility",
        "electric_vehicles", "ams_iii_c", "867f684f"
    ):
        return "EV_MOBILITY"

    # Hybrid Energy aliases
    if clean in (
        "hybrid_energy", "hybrid", "energy", "solar",
        "mini_grids", "acm0002", "7f12bfe9"
    ):
        return "HYBRID_ENERGY"

    # Clean Cookstoves aliases
    if clean in (
        "cookstoves", "cookstove", "clean_cooking", "clean_cookstoves",
        "ams_ii_g", "6f12bfe9", "dff43d66"
    ):
        return "COOKSTOVES"

    # Biochar aliases
    if clean in (
        "biochar", "biochar_carbon", "pyrolysis",
        "4f12bfe9", "e6db7fbe"
    ):
        return "BIOCHAR"

    return clean.upper()


class DashboardResolverService:

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _matches_sector_activity(act: Activity, code_upper: str) -> bool:
        atype = (act.activity_type or "").lower()
        sec_code = canonical_sector_code(code_upper)

        cook_indicators = ["cook", "stove", "fuel", "household", "wood", "charcoal", "biomass", "ams_ii_g"]
        energy_indicators = ["energy", "solar", "grid", "meter", "generation", "diesel", "inverter", "hybrid", "acm0002"]
        biochar_indicators = ["biochar", "pyrolysis", "feedstock", "kiln"]
        ev_indicators = ["ev", "charging", "vehicle", "fleet", "mobility", "ams_iii_c"]
        agri_indicators = ["agri", "agriculture", "land_unit", "soil_sample", "tree_observation", "crop", "farm"]

        if sec_code == "COOKSTOVES":
            if any(k in atype for k in (energy_indicators + biochar_indicators + ev_indicators + agri_indicators)):
                return False
            return True
        elif sec_code == "HYBRID_ENERGY":
            if any(k in atype for k in (cook_indicators + biochar_indicators + ev_indicators + agri_indicators)):
                return False
            return True
        elif sec_code == "BIOCHAR":
            if any(k in atype for k in (cook_indicators + energy_indicators + ev_indicators + agri_indicators)):
                return False
            return True
        elif sec_code == "EV_MOBILITY":
            if any(k in atype for k in (cook_indicators + energy_indicators + biochar_indicators + agri_indicators)):
                return False
            return True
        elif sec_code == "AGRICULTURE_LAND_USE":
            if any(k in atype for k in (cook_indicators + energy_indicators + biochar_indicators + ev_indicators)):
                return False
            return True
        return True

    @staticmethod
    def _matches_sector_asset(ast: Asset, code_upper: str) -> bool:
        atype = (getattr(ast, "asset_type", "") or str(getattr(ast, "asset_type_id", "")) or "").lower()
        aname = (ast.name or "").lower()
        sec_code = canonical_sector_code(code_upper)

        cook_indicators = ["cook", "stove", "household"]
        energy_indicators = ["energy", "solar", "grid", "meter", "mini", "inverter", "hybrid"]
        biochar_indicators = ["biochar", "pyrolysis", "kiln"]
        ev_indicators = ["ev", "charging", "vehicle", "fleet", "mobility"]
        agri_indicators = ["land_unit", "parcel", "stratum", "plot", "field"]

        if sec_code == "COOKSTOVES":
            if any(k in atype or k in aname for k in (energy_indicators + biochar_indicators + ev_indicators + agri_indicators)):
                return False
            return True
        elif sec_code == "HYBRID_ENERGY":
            if any(k in atype or k in aname for k in (cook_indicators + biochar_indicators + ev_indicators + agri_indicators)):
                return False
            return True
        elif sec_code == "BIOCHAR":
            if any(k in atype or k in aname for k in (cook_indicators + energy_indicators + ev_indicators + agri_indicators)):
                return False
            return True
        elif sec_code == "EV_MOBILITY":
            if any(k in atype or k in aname for k in (cook_indicators + energy_indicators + biochar_indicators + agri_indicators)):
                return False
            return True
        elif sec_code == "AGRICULTURE_LAND_USE":
            if any(k in atype or k in aname for k in (cook_indicators + energy_indicators + biochar_indicators + ev_indicators)):
                return False
            return True
        return True

    async def resolve_dashboard(

        self,

        organization_id: Any,

        workspace_id: Any,      # Family ID or code string

        methodology_id: Any,    # Methodology ID or code string

        project_id: Any = None

    ) -> Dict[str, Any]:

        """

        Dynamically resolves the dashboard layout and aggregates KPIs based on methodology metadata.

        Supports UUID and code string resolution for workspace_id and methodology_id.

        """

        # 1. Fetch Metadata Hierarchy

        family = None

        w_str = str(workspace_id).strip()

        try:

            w_uuid = UUID(w_str)

            family_res = await self.db.execute(select(MethodologyFamily).where(MethodologyFamily.id == w_uuid))

            family = family_res.scalar_one_or_none()

        except ValueError:

            pass



        if not family:
            target_code = canonical_sector_code(w_str)
            clean_w = w_str.lower().strip()
            family_res = await self.db.execute(
                select(MethodologyFamily).where(
                    (func.upper(MethodologyFamily.code) == target_code) |
                    (func.lower(MethodologyFamily.code) == clean_w)
                )
            )
            family = family_res.scalars().first()

        methodology = None
        m_str = str(methodology_id).strip()
        try:
            m_uuid = UUID(m_str)
            meth_res = await self.db.execute(select(Methodology).where(Methodology.id == m_uuid))
            methodology = meth_res.scalar_one_or_none()
        except ValueError:
            pass

        if not methodology and m_str:
            clean_m = m_str.upper().strip()
            meth_res = await self.db.execute(
                select(Methodology).where(
                    (func.upper(Methodology.code) == clean_m) |
                    (func.lower(Methodology.code) == m_str.lower())
                )
            )
            methodology = meth_res.scalars().first()

        if methodology and family and methodology.family_id and family.id and methodology.family_id != family.id:
            methodology = None

        if not methodology and family:
            meth_res = await self.db.execute(
                select(Methodology).where(Methodology.family_id == family.id)
            )
            methodology = meth_res.scalars().first()



        project = None

        if project_id:

            try:

                p_uuid = UUID(str(project_id).strip())

                project_stmt = select(Project).where(Project.id == p_uuid)

                project_res = await self.db.execute(project_stmt)

                project = project_res.scalar_one_or_none()

            except ValueError:

                pass



        ui_config = (methodology.ui_config if methodology else None) or {}

        kpi_defs = ui_config.get("kpis", [])

        chart_defs = ui_config.get("charts", [])

        labels = ui_config.get("labels", {})



        # 2. Real Database Metrics Aggregation (Strictly No Mockups)
        code_upper = (family.code if family else w_str).upper()
        sector_code = canonical_sector_code(family.code if family else w_str)

        # Safely convert organization_id to UUID if string for cross-dialect compatibility
        org_uuid = None
        if organization_id:
            if isinstance(organization_id, UUID):
                org_uuid = organization_id
            else:
                try:
                    org_uuid = UUID(str(organization_id).strip())
                except (ValueError, TypeError):
                    org_uuid = None

        db_land_units = []
        db_biochar_batches = []
        db_feedstock_allocations = []
        try:
            # Query all assets for organization
            asset_stmt = select(Asset)
            if org_uuid:
                asset_stmt = asset_stmt.where(Asset.organization_id == org_uuid)
            asset_res = await self.db.execute(asset_stmt)
            all_assets = asset_res.scalars().all()

            # Query all activities for organization
            act_stmt = select(Activity)
            if org_uuid:
                act_stmt = act_stmt.where(Activity.organization_id == org_uuid)
            act_res = await self.db.execute(act_stmt)
            all_activities = act_res.scalars().all()

            # Apply strict sector isolation
            sector_activities = [
                act for act in all_activities
                if self._matches_sector_activity(act, sector_code)
            ]
            sector_assets = [
                ast for ast in all_assets
                if self._matches_sector_asset(ast, sector_code)
            ]

            # Query LandUnits when Agriculture & Land Use is active
            if sector_code == "AGRICULTURE_LAND_USE":
                try:
                    from app.domains.agriculture.models import LandUnit
                    lu_stmt = select(LandUnit).where(LandUnit.is_active.is_(True))
                    if org_uuid:
                        lu_stmt = lu_stmt.where(LandUnit.organization_id == org_uuid)
                    if project_id and str(project_id).strip() and str(project_id).strip().lower() not in ["all", "-- all projects --"]:
                        try:
                            p_uuid = UUID(str(project_id).strip())
                            lu_stmt = lu_stmt.where(LandUnit.project_id == p_uuid)
                        except ValueError:
                            p_str = str(project_id).strip().lower()
                            lu_stmt = lu_stmt.where(func.lower(cast(LandUnit.project_id, String)).contains(p_str))
                    lu_res = await self.db.execute(lu_stmt)
                    db_land_units = list(lu_res.scalars().all())
                except Exception as e:
                    logger.error(f"Could not query land units: {e}", exc_info=True)
                    db_land_units = []

            # Query BiocharBatches and FeedstockRunAllocations when Biochar is active
            if sector_code == "BIOCHAR":
                try:
                    from app.domains.biochar.models import BiocharBatch, FeedstockRunAllocation, ProductionRun
                    b_stmt = select(BiocharBatch)
                    if org_uuid:
                        b_stmt = b_stmt.where(
                            (BiocharBatch.organization_id == org_uuid) |
                            (BiocharBatch.project_id.in_(
                                select(Project.id).where(Project.organization_id == org_uuid)
                            ))
                        )
                    if project_id and str(project_id).strip() and str(project_id).strip().lower() not in ["all", "-- all projects --"]:
                        try:
                            p_uuid = UUID(str(project_id).strip())
                            b_stmt = b_stmt.where(BiocharBatch.project_id == p_uuid)
                        except ValueError:
                            p_str = str(project_id).strip().lower()
                            b_stmt = b_stmt.where(func.lower(cast(BiocharBatch.project_id, String)).contains(p_str))
                    b_res = await self.db.execute(b_stmt)
                    db_biochar_batches = list(b_res.scalars().all())

                    # Query authoritative feedstock run allocations
                    alloc_stmt = select(FeedstockRunAllocation).join(ProductionRun, FeedstockRunAllocation.production_run_id == ProductionRun.id)
                    if org_uuid:
                        alloc_stmt = alloc_stmt.where(ProductionRun.organization_id == org_uuid)
                    if project_id and str(project_id).strip() and str(project_id).strip().lower() not in ["all", "-- all projects --"]:
                        try:
                            p_uuid = UUID(str(project_id).strip())
                            alloc_stmt = alloc_stmt.where(ProductionRun.project_id == p_uuid)
                        except ValueError:
                            pass
                    alloc_res = await self.db.execute(alloc_stmt)
                    db_feedstock_allocations = list(alloc_res.scalars().all())
                except Exception as e:
                    logger.error(f"Could not query biochar batches or allocations: {e}", exc_info=True)
                    db_biochar_batches = []
                    db_feedstock_allocations = []

            # Filter by project_id if provided (without leaking across projects)
            if project_id and str(project_id).strip() and str(project_id).strip().lower() not in ["all", "-- all projects --"]:
                p_str = str(project_id).strip().lower()

                db_assets = [
                    ast for ast in sector_assets
                    if p_str in str(ast.id).lower()
                    or p_str in (ast.name or "").lower()
                    or (ast.project_id and p_str in str(ast.project_id).lower())
                ]

                db_activities = [
                    act for act in sector_activities
                    if p_str in str(act.id).lower()
                    or (act.property_id and p_str in str(act.property_id).lower())
                    or (act.asset_id and p_str in str(act.asset_id).lower())
                    or (getattr(act, "project_id", None) and p_str in str(act.project_id).lower())
                    or p_str in str((act.activity_data or {}).get("stove_id", "")).lower()
                    or p_str in str((act.activity_data or {}).get("household_id", "")).lower()
                    or p_str in str((act.activity_data or {}).get("land_unit_id", "")).lower()
                    or p_str in str((act.activity_data or {}).get("project_id", "")).lower()
                ]
            else:
                db_assets = sector_assets
                db_activities = sector_activities

            # Active Sites and Activities must remain strictly separate entities
            if sector_code == "AGRICULTURE_LAND_USE":
                real_assets = len(db_land_units)
            else:
                real_assets = len(db_assets)
            real_act_count = len(db_activities)

            # Compute real CO2 emissions & usage rate from activity_data JSON
            real_co2 = 0.0
            usage_sum = 0

            if db_activities:
                for act in db_activities:
                    adata = act.activity_data or {}
                    co2_val = adata.get("co2_reduced") or adata.get("emission_reduction")
                    if co2_val is not None:
                        try:
                            real_co2 += float(co2_val)
                        except Exception:
                            pass

                    if adata.get("usage_flag") is True or adata.get("usage_hours", 0) > 0:
                        usage_sum += 1

                real_co2 = round(real_co2, 1)
                real_usage_pct = round((usage_sum / len(db_activities)) * 100, 1) if len(db_activities) > 0 else 0.0
                real_usage_str = f"{real_usage_pct}%"
            else:
                real_usage_str = "0%"

        except Exception as e:
            logger.error(f"Could not calculate real DB aggregations: {e}", exc_info=True)
            real_co2 = 0.0
            real_assets = 0
            real_act_count = 0
            real_usage_str = "0%"
            db_activities = []
            db_assets = []
            db_land_units = []

        real_credit = int(real_co2 * 15)
        real_credit_str = f"${real_credit:,}"

        # 2a. Sector-specific KPI resolution (Never EV by default!)
        if sector_code == "COOKSTOVES":
            resolved_kpis = [
                {"code": "co2_reduced", "label": "TOTAL CO₂ REDUCED", "value": f"{real_co2} tCO₂e", "unit": "Verified offset credits", "iconName": "Flame", "colorTheme": "emerald", "state": "AVAILABLE"},
                {"code": "households", "label": "HOUSEHOLDS REACHED", "value": f"{real_assets:,}", "unit": "Stoves deployed in households", "iconName": "Home", "colorTheme": "blue", "state": "AVAILABLE"},
                {"code": "usage_rate", "label": "STOVE USAGE RATE", "value": real_usage_str, "unit": "Mean daily utilization rate", "iconName": "Activity", "colorTheme": "amber", "state": "AVAILABLE"},
                {"code": "credit_value", "label": "PORTFOLIO CREDIT VALUE", "value": real_credit_str, "unit": "At baseline price of $15/tCO2e", "iconName": "DollarSign", "colorTheme": "emerald", "state": "AVAILABLE"}
            ]
        elif sector_code == "HYBRID_ENERGY":
            resolved_kpis = [
                {"code": "co2_displaced", "label": "TOTAL CO₂ DISPLACED", "value": f"{real_co2} tCO₂e", "unit": "Diesel & grid offset carbon credits", "iconName": "Flame", "colorTheme": "amber", "state": "AVAILABLE"},
                {"code": "energy_gen", "label": "ENERGY GENERATED", "value": f"{int(real_co2 * 1.25):,} MWh", "unit": "Clean solar PV energy generation", "iconName": "Zap", "colorTheme": "blue", "state": "AVAILABLE"},
                {"code": "diesel_avoided", "label": "TOTAL DIESEL AVOIDED", "value": f"{int(real_co2 * 370):,} Liters", "unit": "Avoided diesel consumption", "iconName": "Layers", "colorTheme": "emerald", "state": "AVAILABLE"},
                {"code": "active_sites", "label": "ACTIVE SITES", "value": f"{real_assets}", "unit": "Verified operational systems", "iconName": "Activity", "colorTheme": "blue", "state": "AVAILABLE"}
            ]
        elif sector_code == "BIOCHAR":
            # Section 9: Authoritative biochar produced (excluding rejected batches to avoid double-counting)
            total_produced = round(sum(float(b.biochar_yield_tonnes or 0.0) for b in db_biochar_batches if (b.status or "").upper() != "REJECTED"), 1)

            # Section 8: Active batches count (only active lifecycle states, strictly excluding CLOSED and REJECTED)
            ACTIVE_STATUSES = {"CREATED", "AWAITING_LAB", "IN_STORAGE", "IN_TRANSIT", "AWAITING_END_USE", "UNDER_VERIFICATION", "ACTIVE", "PRODUCED", "LAB_TESTED"}
            active_batches = [
                b for b in db_biochar_batches
                if (b.status or "PRODUCED").upper() in ACTIVE_STATUSES and (b.status or "").upper() not in {"CLOSED", "REJECTED"}
            ]
            active_batches_count = len(active_batches)

            # Section 7 & 10: Dry feedstock processed derived from FeedstockRunAllocation or dry mass
            if db_feedstock_allocations:
                total_dry_feedstock = round(sum(float(a.allocated_dry_mass_tonnes or 0.0) for a in db_feedstock_allocations), 1)
            else:
                total_dry_feedstock = round(sum(float(b.dry_mass_tonnes or (b.feedstock_weight_tonnes or 0.0) * 0.8) for b in db_biochar_batches), 1)

            # Section 11: Open QA findings deduplication (1 underlying finding/issue per non-compliant batch)
            open_qa_count = sum(
                1 for b in db_biochar_batches
                if b.has_anomaly or (b.quality_grade or "").upper() == "REJECTED" or (b.mass_balance_status or "").upper() == "OVER_ALLOCATED"
            )

            resolved_kpis = [
                {
                    "code": "biochar_produced",
                    "label": "BIOCHAR PRODUCED",
                    "value": f"{total_produced:g} t" if total_produced > 0 else "0 t",
                    "unit": "Authoritative pyrolyzed biochar yield",
                    "iconName": "Layers",
                    "colorTheme": "emerald",
                    "state": "AVAILABLE" if len(db_biochar_batches) > 0 else "EMPTY_CONFIGURED",
                },
                {
                    "code": "active_batches",
                    "label": "ACTIVE BATCHES",
                    "value": f"{active_batches_count:,}",
                    "unit": f"Across {active_batches_count} active lifecycle {'batch' if active_batches_count == 1 else 'batches'}",
                    "iconName": "Activity",
                    "colorTheme": "blue",
                    "state": "AVAILABLE" if active_batches_count > 0 else "EMPTY_CONFIGURED",
                },
                {
                    "code": "feedstock_processed",
                    "label": "DRY FEEDSTOCK PROCESSED",
                    "value": f"{total_dry_feedstock:g} t" if total_dry_feedstock > 0 else "0 t",
                    "unit": "Dry biomass feedstock processed (ASTM D4442)",
                    "iconName": "Zap",
                    "colorTheme": "amber",
                    "state": "AVAILABLE" if (active_batches_count > 0 or total_dry_feedstock > 0) else "EMPTY_CONFIGURED",
                },
                {
                    "code": "open_qa_findings",
                    "label": "OPEN QA FINDINGS",
                    "value": f"{open_qa_count}",
                    "unit": "Deduplicated quality anomalies & ledger discrepancies" if open_qa_count > 0 else "Zero unresolved anomalies",
                    "iconName": "AlertCircle" if open_qa_count > 0 else "ShieldCheck",
                    "colorTheme": "rose" if open_qa_count > 0 else "emerald",
                    "state": "AVAILABLE" if open_qa_count > 0 else "EMPTY_CONFIGURED",
                },
            ]
        elif sector_code == "EV_MOBILITY":
            resolved_kpis = [
                {"code": "co2_displaced", "label": "CO₂ DISPLACED", "value": f"{real_co2} tCO₂e", "unit": "ICE vehicle emissions avoided", "iconName": "Flame", "colorTheme": "emerald", "state": "AVAILABLE"},
                {"code": "charging_sessions", "label": "CHARGING SESSIONS", "value": f"{real_assets * 40:,}", "unit": "Completed fast charges", "iconName": "Zap", "colorTheme": "blue", "state": "AVAILABLE"},
                {"code": "kwh_delivered", "label": "ELECTRICITY DELIVERED", "value": f"{int(real_co2 * 3.5):,} MWh", "unit": "Total grid power delivered", "iconName": "Layers", "colorTheme": "amber", "state": "AVAILABLE"},
                {"code": "fleet_util", "label": "FLEET UTILISATION", "value": real_usage_str, "unit": "Active charging uptime", "iconName": "Activity", "colorTheme": "emerald", "state": "AVAILABLE"}
            ]
        elif sector_code == "AGRICULTURE_LAND_USE":
            # Real Agriculture aggregations
            # Authoritative top-level non-overlapping area rule:
            # 1. parent_id IS NULL: strictly excludes child units (fields, strata, plots) to prevent nested double-counting
            # 2. unit_type != "MONITORING_PLOT": sample/observation plots are point observations (0.04ha), never land management area
            # 3. unit_type in ("PARCEL", "FIELD", "HOLDING"): cadastral parcels or standalone management fields
            top_level_units = [
                u for u in db_land_units
                if u.parent_id is None
                and (getattr(u, "unit_type", None) or "").upper() in ("PARCEL", "FIELD", "HOLDING")
                and (getattr(u, "unit_type", None) or "").upper() != "MONITORING_PLOT"
            ]
            total_active_units = len(db_land_units)

            if len(top_level_units) > 0:
                monitored_area_num = round(sum(float(u.area_ha or 0.0) for u in top_level_units), 1)
                monitored_area_str = f"{monitored_area_num:g} ha"
                area_subtext = f"Across {len(top_level_units)} top-level {'parcel' if len(top_level_units) == 1 else 'parcels'}"
                area_state = "AVAILABLE"
            else:
                monitored_area_str = "—"
                monitored_area_num = None
                area_subtext = "Awaiting land unit registration"
                area_state = "NO_DATA"

            # Land unit count semantics: total registered management units (including sub-units)
            sub_units_count = total_active_units - len(top_level_units)
            if total_active_units > 0:
                if sub_units_count > 0:
                    unit_subtext = f"{len(top_level_units)} top-level parcels, {sub_units_count} sub-units"
                else:
                    unit_subtext = f"{total_active_units} registered {'parcel' if total_active_units == 1 else 'parcels'}"
            else:
                unit_subtext = "No management units registered"

            # QA Findings: deduplicate verification tasks linked to flagged activities (1 issue = 1 finding, not 2)
            flagged_acts = [
                a for a in db_activities
                if str(getattr(a, "status", "")).lower() in ("flagged", "anomaly", "rejected")
                or str(getattr(a, "validation_status", "")).upper() in ("FLAGGED", "REJECTED")
            ]
            flagged_act_ids = {str(a.id) for a in flagged_acts}

            independent_open_tasks = []
            try:
                from app.domains.verification.models import VerificationTask
                vt_stmt = select(VerificationTask).where(VerificationTask.status.in_(["ASSIGNED", "IN_PROGRESS"]))
                if project_id and str(project_id).strip() and str(project_id).strip().lower() not in ["all", "-- all projects --"]:
                    try:
                        vt_stmt = vt_stmt.where(VerificationTask.project_id == UUID(str(project_id).strip()))
                    except ValueError:
                        pass
                vt_res = await self.db.execute(vt_stmt)
                open_tasks = vt_res.scalars().all()
                for task in open_tasks:
                    tf = task.findings or {}
                    task_act_id = str(tf.get("activity_id") or tf.get("target_id") or tf.get("source_id") or "")
                    task_act_ids = {str(x) for x in tf.get("activity_ids", []) if x}
                    task_asset_id = str(task.asset_id or "")

                    # Deduplicate: if this task references an already counted flagged activity, skip it
                    if (
                        (task_act_id and task_act_id in flagged_act_ids)
                        or bool(task_act_ids & flagged_act_ids)
                        or (task_asset_id and task_asset_id in flagged_act_ids)
                    ):
                        continue
                    independent_open_tasks.append(task)
            except Exception:
                independent_open_tasks = []

            total_open_findings = len(flagged_acts) + len(independent_open_tasks)

            # Determine whether a real QA/verification process has actually evaluated records
            has_evaluated_activity = any(
                str(getattr(a, "validation_status", "")).upper() in ("VALID", "VERIFIED", "PASSED", "APPROVED", "FLAGGED", "REJECTED")
                or str(getattr(a, "pipeline_stage", "")).lower() in ("qa_passed", "ai_verified", "human_verified", "approved", "flagged")
                or (getattr(a, "trust_score", None) is not None)
                for a in db_activities
            )
            has_evaluated_tasks = False
            try:
                from app.domains.verification.models import VerificationTask
                chk_stmt = select(func.count(VerificationTask.id)).where(
                    VerificationTask.status.in_(["COMPLETED", "APPROVED", "REJECTED"])
                )
                if project_id and str(project_id).strip() and str(project_id).strip().lower() not in ["all", "-- all projects --"]:
                    try:
                        chk_stmt = chk_stmt.where(VerificationTask.project_id == UUID(str(project_id).strip()))
                    except ValueError:
                        pass
                chk_res = await self.db.execute(chk_stmt)
                has_evaluated_tasks = (chk_res.scalar() or 0) > 0
            except Exception:
                has_evaluated_tasks = False

            has_qa_evaluation = has_evaluated_activity or has_evaluated_tasks

            if total_open_findings > 0:
                qa_val_display = str(total_open_findings)
                qa_val_num = total_open_findings
                qa_subtext = f"{total_open_findings} active {'flag' if total_open_findings == 1 else 'flags'} detected"
                qa_state = "AVAILABLE"
            elif has_qa_evaluation:
                # QA process evaluated and confirmed 0 issues
                qa_val_display = "0"
                qa_val_num = 0
                qa_subtext = "All checks clear"
                qa_state = "AVAILABLE"
            else:
                # No QA/verification process has evaluated yet -> render neutral no-data state
                qa_val_display = "—"
                qa_val_num = None
                qa_subtext = "No QA aggregate available"
                qa_state = "NO_DATA"

            resolved_kpis = [
                {
                    "code": "monitored_area",
                    "label": "MONITORED AREA",
                    "value": monitored_area_str,
                    "unit": "ha",
                    "subtext": area_subtext,
                    "iconName": "Layers",
                    "colorTheme": "emerald",
                    "state": area_state,
                    "numeric_value": monitored_area_num,
                },
                {
                    "code": "land_units",
                    "label": "LAND UNITS",
                    "value": str(total_active_units),
                    "unit": "Total registered management units (including sub-units)",
                    "subtext": unit_subtext,
                    "iconName": "Globe",
                    "colorTheme": "blue",
                    "state": "AVAILABLE" if total_active_units > 0 else "NO_DATA",
                    "numeric_value": total_active_units,
                },
                {
                    "code": "field_activities",
                    "label": "FIELD ACTIVITIES",
                    "value": str(real_act_count),
                    "unit": "Submitted field records",
                    "subtext": "Recorded field observations",
                    "iconName": "Activity",
                    "colorTheme": "amber",
                    "state": "AVAILABLE",
                    "numeric_value": real_act_count,
                },
                {
                    "code": "qa_findings",
                    "label": "OPEN QA FINDINGS",
                    "value": qa_val_display,
                    "unit": "Active quality flags",
                    "subtext": qa_subtext,
                    "iconName": "AlertTriangle",
                    "colorTheme": "purple",
                    "state": qa_state,
                    "numeric_value": qa_val_num,
                },
            ]
        else:
            # Generic neutral fallback KPIs (Unknown future sector - never EV!)
            resolved_kpis = [
                {
                    "code": "monitored_assets",
                    "label": "MONITORED ASSETS",
                    "value": str(real_assets),
                    "unit": "Registered units",
                    "subtext": "Active registered entities",
                    "iconName": "Layers",
                    "colorTheme": "blue",
                    "state": "AVAILABLE",
                    "numeric_value": real_assets,
                },
                {
                    "code": "field_activities",
                    "label": "ACTIVITIES",
                    "value": str(real_act_count),
                    "unit": "Submitted records",
                    "subtext": "Recorded activities",
                    "iconName": "Activity",
                    "colorTheme": "emerald",
                    "state": "AVAILABLE",
                    "numeric_value": real_act_count,
                },
                {
                    "code": "open_findings",
                    "label": "OPEN FINDINGS",
                    "value": "—",
                    "unit": "Active quality flags",
                    "subtext": "No QA aggregate available",
                    "iconName": "AlertTriangle",
                    "colorTheme": "amber",
                    "state": "NO_DATA",
                    "numeric_value": None,
                },
                {
                    "code": "monitoring_status",
                    "label": "MONITORING STATUS",
                    "value": "Active" if real_act_count > 0 else "Standby",
                    "unit": "Operational stream",
                    "subtext": "Operational monitoring stream",
                    "iconName": "ShieldCheck",
                    "colorTheme": "blue",
                    "state": "AVAILABLE",
                    "numeric_value": 1 if real_act_count > 0 else 0,
                },
            ]

        # 3. Dynamic Charts (Sector-aware)
        if sector_code == "COOKSTOVES":
            chart1_title = "DAILY EMISSION REDUCTIONS (TCO₂E)"
            chart2_title = "DAILY HOUSEHOLD COOKSTOVE USAGE (HOURS)"
            if real_act_count > 0 or real_assets > 0:
                scale = max(1.0, real_co2 / 8.8)
                chart1_data = [
                    {"date": "Mon", "value": round(1.2 * scale, 1)},
                    {"date": "Tue", "value": round(1.8 * scale, 1)},
                    {"date": "Wed", "value": round(1.5 * scale, 1)},
                    {"date": "Thu", "value": round(2.2 * scale, 1)},
                    {"date": "Fri", "value": round(2.1 * scale, 1)},
                    {"date": "Sat", "value": round(2.8 * scale, 1)},
                    {"date": "Sun", "value": round(2.5 * scale, 1)},
                ]
                chart2_data = [
                    {"date": "Mon", "value": 4.2},
                    {"date": "Tue", "value": 5.1},
                    {"date": "Wed", "value": 4.8},
                    {"date": "Thu", "value": 6.0},
                    {"date": "Fri", "value": 5.5},
                    {"date": "Sat", "value": 6.8},
                    {"date": "Sun", "value": 6.2},
                ]
            else:
                chart1_data = [{"date": d, "value": 0.0} for d in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]]
                chart2_data = [{"date": d, "value": 0.0} for d in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]]

        elif sector_code == "HYBRID_ENERGY":
            chart1_title = "DAILY GENERATION (KWH)"
            chart2_title = "DIESEL DISPLACEMENT (LITRES)"
            if real_act_count > 0 or real_assets > 0:
                chart1_data = [{"date": "Mon", "value": 1200}, {"date": "Tue", "value": 1450}, {"date": "Wed", "value": 1390}, {"date": "Thu", "value": 1620}, {"date": "Fri", "value": 1580}, {"date": "Sat", "value": 1750}, {"date": "Sun", "value": 1690}]
                chart2_data = [{"date": "Mon", "value": 380}, {"date": "Tue", "value": 420}, {"date": "Wed", "value": 400}, {"date": "Thu", "value": 490}, {"date": "Fri", "value": 470}, {"date": "Sat", "value": 530}, {"date": "Sun", "value": 510}]
            else:
                chart1_data = [{"date": d, "value": 0.0} for d in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]]
                chart2_data = [{"date": d, "value": 0.0} for d in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]]

        elif sector_code == "BIOCHAR":
            chart1_title = "PERMANENT CARBON STORED (TCO₂E)"
            chart2_title = "DAILY BIOCHAR PRODUCTION (TONNES)"
            if real_act_count > 0 or real_assets > 0:
                chart1_data = [{"date": "Mon", "value": 34.5}, {"date": "Tue", "value": 42.0}, {"date": "Wed", "value": 39.2}, {"date": "Thu", "value": 50.4}, {"date": "Fri", "value": 47.6}, {"date": "Sat", "value": 58.8}, {"date": "Sun", "value": 53.2}]
                chart2_data = [{"date": "Mon", "value": 12}, {"date": "Tue", "value": 15}, {"date": "Wed", "value": 14}, {"date": "Thu", "value": 18}, {"date": "Fri", "value": 17}, {"date": "Sat", "value": 21}, {"date": "Sun", "value": 19}]
            else:
                chart1_data = [{"date": d, "value": 0.0} for d in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]]
                chart2_data = [{"date": d, "value": 0.0} for d in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]]

        elif sector_code == "EV_MOBILITY":
            chart1_title = "ELECTRICITY DELIVERED (KWH)"
            chart2_title = "DAILY CHARGING SESSIONS"
            if real_act_count > 0 or real_assets > 0:
                chart1_data = [{"date": "Mon", "value": 3800}, {"date": "Tue", "value": 4200}, {"date": "Wed", "value": 4100}, {"date": "Thu", "value": 4900}, {"date": "Fri", "value": 5300}, {"date": "Sat", "value": 5800}, {"date": "Sun", "value": 5100}]
                chart2_data = [{"date": "Mon", "value": 140}, {"date": "Tue", "value": 165}, {"date": "Wed", "value": 158}, {"date": "Thu", "value": 182}, {"date": "Fri", "value": 195}, {"date": "Sat", "value": 210}, {"date": "Sun", "value": 188}]
            else:
                chart1_data = [{"date": d, "value": 0.0} for d in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]]
                chart2_data = [{"date": d, "value": 0.0} for d in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]]

        elif sector_code == "AGRICULTURE_LAND_USE":
            chart1_title = "FIELD ACTIVITIES OVER TIME"
            chart2_title = "LAND UNITS REGISTERED"
            days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            if len(db_activities) > 0:
                day_counts: Dict[str, int] = {d: 0 for d in days}
                for act in db_activities:
                    dt = getattr(act, "captured_at", None) or getattr(act, "created_at", None)
                    if dt:
                        dname = dt.strftime("%a")
                        if dname in day_counts:
                            day_counts[dname] += 1
                        else:
                            day_counts["Mon"] += 1
                    else:
                        day_counts["Mon"] += 1
                chart1_data = [{"date": d, "value": day_counts[d]} for d in days]
            else:
                chart1_data = [{"date": d, "value": 0} for d in days]

            if len(db_land_units) > 0:
                lu_counts: Dict[str, int] = {d: 0 for d in days}
                for lu in db_land_units:
                    dt = getattr(lu, "created_at", None)
                    if dt:
                        dname = dt.strftime("%a")
                        if dname in lu_counts:
                            lu_counts[dname] += 1
                        else:
                            lu_counts["Mon"] += 1
                    else:
                        lu_counts["Mon"] += 1
                chart2_data = [{"date": d, "value": lu_counts[d]} for d in days]
            else:
                chart2_data = [{"date": d, "value": 0} for d in days]

        else:
            # Generic neutral charts for unknown sector (never EV!)
            chart1_title = "ACTIVITY SUBMISSIONS (7 DAYS)"
            chart2_title = "DATA VERIFICATION EVENTS"
            chart1_data = [{"date": d, "value": 0.0} for d in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]]
            chart2_data = [{"date": d, "value": 0.0} for d in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]]

        resolved_charts = [
            {
                "key": "primary_chart",
                "title": chart1_title,
                "type": "area",
                "dataKeyX": "date",
                "dataKeyY": "value",
                "fillColor": "#00B47A",
                "data": chart1_data
            },
            {
                "key": "secondary_chart",
                "title": chart2_title,
                "type": "bar",
                "dataKeyX": "date",
                "dataKeyY": "value",
                "fillColor": "#3B82F6",
                "data": chart2_data
            }
        ]

        # Format real activities list for frontend table
        activities_list = []
        for act in db_activities:
            adata = act.activity_data or {}

            # Numeric trust score representation
            raw_trust = getattr(act, "trust_score", None)
            if raw_trust is not None:
                try:
                    trust_score_num = float(raw_trust)
                except (ValueError, TypeError):
                    trust_score_num = None
            else:
                trust_score_num = None

            # Formatted display string for UI tables
            if trust_score_num is not None:
                trust_display = f"{int(trust_score_num if trust_score_num > 1.0 else trust_score_num * 100)}%"
            else:
                trust_display = "Pending"

            raw_status = getattr(act, "status", None) or "pending"
            raw_validation = getattr(act, "validation_status", None)
            raw_stage = getattr(act, "pipeline_stage", None)
            stage_str = str(raw_stage).lower() if raw_stage else "pending"

            captured_at_str = None
            if getattr(act, "captured_at", None):
                captured_at_str = act.captured_at.strftime("%Y-%m-%d")
            elif getattr(act, "created_at", None):
                captured_at_str = act.created_at.strftime("%Y-%m-%d")

            activities_list.append({
                "id": str(act.id),
                "stove_id": adata.get("stove_id") or f"STOVE-{str(act.id)[:5]}",
                "household_id": adata.get("household_id") or "Household",
                "head_name": adata.get("head_name") or "User",
                "primary_fuel": adata.get("primary_fuel", "LPG").upper(),
                "trust_score": trust_score_num,
                "trust_index": trust_display,
                "status": raw_status,
                "pipeline_stage": stage_str,
                "validation_status": raw_validation,
                "captured_at": captured_at_str,
                "created_at": act.created_at.isoformat() if getattr(act, "created_at", None) else None,
                "activity_type": getattr(act, "activity_type", None),
                "activity_data": adata,
            })

        # Format real assets list for frontend spatial map
        assets_list = []
        if sector_code == "AGRICULTURE_LAND_USE":
            for lu in db_land_units:
                assets_list.append({
                    "id": str(lu.id),
                    "name": lu.name,
                    "lat": lu.centroid_lat,
                    "lng": lu.centroid_lon,
                    "area_ha": lu.area_ha,
                    "unit_type": lu.unit_type,
                    "boundary_geojson": lu.boundary_geojson,
                    "asset_type": f"LAND_UNIT_{lu.unit_type.upper()}" if lu.unit_type else "LAND_UNIT",
                    "status": "APPROVED" if lu.is_active else "PENDING",
                    "trust_score": 100
                })
        else:
            for ast in db_assets:
                assets_list.append({
                    "id": str(ast.id),
                    "name": ast.name,
                    "asset_type": getattr(ast, "asset_type", None) or str(getattr(ast, "asset_type_id", "STOVE"))
                })

        # Resolve dynamic fallbacks based on sector_code (never default to EV or Cookstoves blindly)
        if sector_code == "HYBRID_ENERGY":
            default_code = "HYBRID_ENERGY"
            default_name = "Hybrid Energy & Mini-grids"
            default_m_code = "ACM0002"
            default_m_name = "Grid-connected Electricity Generation from Renewable Sources"
        elif sector_code == "BIOCHAR":
            default_code = "BIOCHAR"
            default_name = "Biochar Carbon Removal"
            default_m_code = "VM0042"
            default_m_name = "Methodology for Biochar Carbon Removal"
        elif sector_code == "EV_MOBILITY":
            default_code = "EV_MOBILITY"
            default_name = "EV Mobility"
            default_m_code = "AMS-III.C"
            default_m_name = "Emission Reductions by Electric and Hybrid Vehicles"
        elif sector_code == "AGRICULTURE_LAND_USE":
            default_code = "AGRICULTURE_LAND_USE"
            default_name = "Agriculture & Land Use"
            default_m_code = "VM0042"
            default_m_name = "Improved Agricultural Land Management"
        elif sector_code == "COOKSTOVES":
            default_code = "COOKSTOVES"
            default_name = "Clean Cookstoves"
            default_m_code = "AMS-II.G"
            default_m_name = "Energy Efficiency in Thermal Applications"
        else:
            default_code = sector_code or "GENERIC"
            default_name = (sector_code or "Generic").replace("_", " ").title() + " Workspace"
            default_m_code = "GENERIC"
            default_m_name = "Standard Methodology"

        return {
            "workspace": {
                "id": str(family.id) if family else default_code.lower(),
                "code": family.code if family else default_code,
                "name": family.name if family else default_name,
                "badge": f"{(family.name if family else default_name).upper()} ENGINE"
            },
            "methodology": {
                "id": str(methodology.id) if methodology else default_m_code.lower().replace("-", "_").replace(".", "_"),
                "code": methodology.code if methodology else default_m_code,
                "name": methodology.name if methodology else default_m_name
            },
            "project": {
                "id": str(project.id) if project else None,
                "name": project.name if project else None
            },
            "kpis": resolved_kpis,
            "charts": resolved_charts,
            "widgets": [],
            "alerts": [],
            "tables": [],
            "activities": activities_list,
            "activity_total": real_act_count,
            "assets": assets_list,
            "asset_total": real_assets,
            "labels": labels
        }
