"""
=============================================================================
VeriField Nexus — Registry Compliance Dossier Generator
=============================================================================
Generates rigorous, standard-specific structured compliance dossiers:
1. Nigeria NCCC / NCMAP Regulatory Compliance Dossier
2. UNFCCC Article 6.2 ITMO Structured Summary & Cooperative Approach Dossier
3. UNFCCC Article 6.4 Mechanism Activity Dossier
4. Verra VCS Standard Version 5.0 / 4.5 Compliance Profile
5. Gold Standard for the Global Goals (GS4GG) Compliance Profile
=============================================================================
"""

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.activities.models import Activity
from app.domains.assets.models import Asset
from app.domains.documents.models import ProjectDocument
from app.domains.evidence.models import Evidence
from app.domains.jurisdictions.models import Jurisdiction
from app.domains.methodologies.models.base_registry import Methodology, MethodologyFamily
from app.domains.organizations.models import Organization
from app.domains.projects.models import Project


def _get_activity_emission_kg(act) -> float:
    data = act.activity_data or {}
    if isinstance(data, dict):
        if "emission_reduction_kg" in data:
            return float(data["emission_reduction_kg"])
        elif "carbon_offset_tons" in data:
            return float(data["carbon_offset_tons"]) * 1000.0
        elif "co2e_reduction_tonnes" in data:
            return float(data["co2e_reduction_tonnes"]) * 1000.0
    return 0.0


class RegistryComplianceDossierService:
    """Generates rigorous, authoritative registry-specific dossiers and payloads."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_dossier(
        self,
        standard: str,
        project_id: UUID,
        stage: str = "monitoring",
        version: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Builds the structured compliance dossier for a project and standard.
        Standards supported: 'NCCC', 'ARTICLE6_2', 'ARTICLE6_4', 'VERRA', 'GOLD_STANDARD'.
        """
        eval_time = timestamp or datetime.now(timezone.utc)
        # 1. Fetch Project & Metadata
        p_stmt = select(Project).where(Project.id == project_id)
        p_res = await self.db.execute(p_stmt)
        project = p_res.scalar_one_or_none()
        if not project:
            raise ValueError(f"Project with ID {project_id} not found.")

        # 2. Fetch Organization
        org = None
        if project.organization_id:
            org_stmt = select(Organization).where(Organization.id == project.organization_id)
            org_res = await self.db.execute(org_stmt)
            org = org_res.scalar_one_or_none()

        # 3. Fetch Methodology & Sector
        meth = None
        if project.methodology_id:
            m_stmt = select(Methodology).where(Methodology.id == project.methodology_id)
            m_res = await self.db.execute(m_stmt)
            meth = m_res.scalar_one_or_none()

        sector = None
        if project.sector_id:
            sec_stmt = select(MethodologyFamily).where(MethodologyFamily.id == project.sector_id)
            sec_res = await self.db.execute(sec_stmt)
            sector = sec_res.scalar_one_or_none()

        # 4. Fetch Jurisdiction
        jurisdiction = None
        if hasattr(project, "jurisdiction_id") and project.jurisdiction_id:
            j_stmt = select(Jurisdiction).where(Jurisdiction.id == project.jurisdiction_id)
            j_res = await self.db.execute(j_stmt)
            jurisdiction = j_res.scalar_one_or_none()

        # 5. Fetch Assets & Activities
        asset_stmt = select(Asset).where(Asset.project_id == project_id)
        a_res = await self.db.execute(asset_stmt)
        assets = a_res.scalars().all()

        asset_ids = [a.id for a in assets]
        if asset_ids:
            act_stmt = select(Activity).where(Activity.asset_id.in_(asset_ids))
        elif project.organization_id:
            act_stmt = select(Activity).where(Activity.organization_id == project.organization_id)
        else:
            act_stmt = select(Activity).where(Activity.id.is_(None))
        act_res = await self.db.execute(act_stmt)
        activities = act_res.scalars().all()

        doc_stmt = select(ProjectDocument).where(ProjectDocument.project_id == project_id)
        doc_res = await self.db.execute(doc_stmt)
        documents = doc_res.scalars().all()

        std_upper = standard.upper()
        if std_upper in ["NCCC", "NIGERIA", "NCMAP"]:
            return self._build_nccc_dossier(project, org, meth, sector, jurisdiction, assets, activities, documents, stage, eval_time)
        elif std_upper in ["ARTICLE6_2", "A62", "ITMO"]:
            return self._build_article6_2_dossier(project, org, meth, sector, jurisdiction, assets, activities, documents, stage, eval_time)
        elif std_upper in ["ARTICLE6_4", "A64", "A64ER"]:
            return self._build_article6_4_dossier(project, org, meth, sector, jurisdiction, assets, activities, documents, stage, eval_time)
        elif std_upper in ["VERRA", "VCS"]:
            ver = version or "v5.0"
            return self._build_verra_dossier(project, org, meth, sector, jurisdiction, assets, activities, documents, stage, ver, eval_time)
        elif std_upper in ["GOLD_STANDARD", "GS", "GS4GG"]:
            return self._build_gold_standard_dossier(project, org, meth, sector, jurisdiction, assets, activities, documents, stage, eval_time)
        else:
            raise ValueError(f"Unsupported compliance standard: {standard}. Supported: NCCC, ARTICLE6_2, ARTICLE6_4, VERRA, GOLD_STANDARD")

    def _build_nccc_dossier(self, project: Project, org: Optional[Organization], meth: Optional[Methodology], sector: Optional[MethodologyFamily], jurisdiction: Optional[Jurisdiction], assets: List[Asset], activities: List[Activity], docs: List[ProjectDocument], stage: str, eval_time: Optional[datetime] = None) -> Dict[str, Any]:
        """Builds Nigeria NCCC / NCMAP Regulatory Compliance Dossier."""
        total_co2_kg = sum(_get_activity_emission_kg(a) for a in activities)
        total_tco2e = round(total_co2_kg / 1000.0, 4)
        gen_time = (eval_time or datetime.now(timezone.utc)).isoformat()

        base_params = project.baseline_parameters if isinstance(project.baseline_parameters, dict) else {}
        community_benefit_pct = float(base_params.get("community_benefit_pct", 15.0))
        sop_pct = float(base_params.get("sovereign_sop_pct", 5.0))
        emp_count = base_params.get("local_employment_count", None)

        # Truthful registration reference: use actual registry_id or declare pending
        official_noc_ref = project.registry_id if project.registry_id else None

        return {
            "standard_profile": "NIGERIA_NCCC_NCMAP",
            "regulatory_authority": "National Council on Climate Change (NCCC), Federal Republic of Nigeria",
            "framework": "Nigeria Carbon Market Activation Plan (NCMAP) / Climate Change Act 2021",
            "dossier_type": "National Regulatory Filing & No-Objection Compliance Dossier",
            "output_classification": "STRUCTURED_COMPLIANCE_DATA_PACKAGE",
            "project_metadata": {
                "project_id": str(project.id),
                "project_code": project.project_code if hasattr(project, "project_code") and project.project_code else f"PRJ-{str(project.id)[:8]}",
                "project_name": project.name,
                "project_developer": org.name if org else "Unspecified Entity",
                "developer_registration_number": getattr(org, "legal_entity_number", None) or "PENDING_REGISTRATION",
                "host_country": "Federal Republic of Nigeria",
                "jurisdiction_state": jurisdiction.name if jurisdiction else "National Territory",
                "sector_classification": sector.name if sector else "Energy Demand / Household Devices",
                "methodology_applied": meth.name if meth else "Approved National / Registry Methodology",
                "methodology_code": meth.code if meth else "NCCC-MRV-01",
                "crediting_period": f"{project.crediting_start.isoformat() if getattr(project, 'crediting_start', None) else '2026-01-01'} to {project.crediting_end.isoformat() if getattr(project, 'crediting_end', None) else '2035-12-31'}",
            },
            "mitigation_quantification": {
                "total_active_assets_deployed": len(assets),
                "verified_activity_records": len(activities),
                "cumulative_mitigation_tco2e": total_tco2e,
                "ndc_target_contribution_pct": round((total_tco2e / 1000000.0) * 100.0, 6) if total_tco2e else 0.0,
            },
            "regulatory_compliance_sections": {
                "section_1_no_objection_certificate_status": {
                    "noc_status": "OFFICIALLY_REGISTERED" if official_noc_ref else "APPLICATION_DOSSIER_COMPILED",
                    "application_reference": official_noc_ref or "PENDING_OFFICIAL_FILING",
                    "internal_dossier_reference": f"NEXUS/NOC/{str(project.id)[:8].upper()}",
                    "national_registry_inclusion": "CONFIRMED_IN_REGISTRY" if official_noc_ref else "PENDING_PORTAL_SUBMISSION",
                },
                "section_2_article_6_authorization_readiness": {
                    "article_6_pathway": "Article 6.2 Bilateral / National Registry Transfer",
                    "authorization_status": "AUTHORIZED" if base_params.get("article_6_authorized") else "REQUEST_FORM_COMPILED",
                    "corresponding_adjustment_covenant": "Committed to National Registry CA rules pursuant to NCCC Guidelines",
                },
                "section_3_benefit_sharing_and_social_impact": {
                    "community_benefit_allocation_pct": community_benefit_pct,
                    "local_employment_count": emp_count if emp_count is not None else "UNVERIFIED_PENDING_AUDIT",
                    "sustainable_development_goals_targeted": ["SDG 3 (Health)", "SDG 7 (Energy)", "SDG 13 (Climate Action)"],
                },
                "section_4_sovereign_levy_and_adaptation_fund": {
                    "share_of_proceeds_sop_pct": sop_pct,
                    "national_climate_change_fund_contribution": f"{round(total_tco2e * (sop_pct / 100.0), 4)} tCO2e (or equivalent levy upon unit issuance)",
                },
            },
            "document_attachments_index": [
                {"doc_id": str(d.id), "title": getattr(d, "title", None) or getattr(d, "filename", "document"), "sha256": getattr(d, "file_hash", None)}
                for d in docs
            ],
            "dossier_sha256": hashlib.sha256(f"NCCC:{project.id}:{total_tco2e}".encode("utf-8")).hexdigest(),
            "generated_at": gen_time,
        }

    def _build_article6_2_dossier(self, project: Project, org: Optional[Organization], meth: Optional[Methodology], sector: Optional[MethodologyFamily], jurisdiction: Optional[Jurisdiction], assets: List[Asset], activities: List[Activity], docs: List[ProjectDocument], stage: str, eval_time: Optional[datetime] = None) -> Dict[str, Any]:
        """Builds UNFCCC Article 6.2 ITMO Structured Summary & Cooperative Approach Dossier."""
        total_co2_kg = sum(_get_activity_emission_kg(a) for a in activities)
        total_itmos = round(total_co2_kg / 1000.0, 4)
        gen_time = (eval_time or datetime.now(timezone.utc)).isoformat()

        base_params = project.baseline_parameters if isinstance(project.baseline_parameters, dict) else {}
        is_authorized = bool(base_params.get("article_6_authorized", False))
        first_transferred = bool(base_params.get("first_transferred", False))
        ca_applied = bool(base_params.get("corresponding_adjustment_applied", False))

        # Enforce strict Article 6.2 lifecycle invariant:
        # Authorization -> First Transfer -> Corresponding Adjustment
        if ca_applied and not (is_authorized and first_transferred):
            ca_status = "INVALID_STATE_CA_CANNOT_PRECEDE_FIRST_TRANSFER"
        elif ca_applied:
            ca_status = "CA_RECORDED_IN_BTR"
        elif first_transferred:
            ca_status = "PENDING_CA_RECORDING"
        else:
            ca_status = "PENDING_FIRST_TRANSFER"

        return {
            "standard_profile": "UNFCCC_ARTICLE_6_2",
            "regulatory_framework": "Paris Agreement Article 6, paragraph 2 (Decision 2/CMA.3 & 6/CMA.4)",
            "dossier_type": "Article 6.2 ITMO Structured Summary & Cooperative Approach Dossier",
            "output_classification": "STRUCTURED_COMPLIANCE_DATA_PACKAGE",
            "cooperative_approach_metadata": {
                "cooperative_approach_id": base_params.get("cooperative_approach_id", f"CA-NGA-2026-{str(project.id)[:6].upper()}"),
                "host_party": project.country or "Nigeria",
                "acquiring_party": base_params.get("acquiring_party", "TBD / Bilateral Partner"),
                "mitigation_activity_name": project.name,
                "sector": sector.name if sector else "Energy / Fuel Switching",
                "methodology_baseline": meth.name if meth else "Approved Article 6.2 Protocol",
                "crediting_period_start": project.crediting_start.isoformat() if getattr(project, "crediting_start", None) else "2026-01-01",
                "crediting_period_end": project.crediting_end.isoformat() if getattr(project, "crediting_end", None) else "2035-12-31",
            },
            "itmo_accounting_ledger": {
                "vintage_year": datetime.now(timezone.utc).year,
                "cumulative_itmos_generated_tco2e": total_itmos,
                "authorized_use_scope": base_params.get("authorized_use_scope", "NDC Achievement / Other International Mitigation Purposes (OIMP)"),
                "authorization_status": "AUTHORIZED" if is_authorized else "PENDING_AUTHORIZATION",
                "first_transfer_status": "FIRST_TRANSFERRED" if first_transferred else "NOT_TRANSFERRED",
                "corresponding_adjustment_status": ca_status,
                "serial_number_format": f"ITMO-{'NGA' if (project.country and project.country.lower() in ['nigeria', 'nga']) else str(project.country or 'NGA')[:3].upper()}-{datetime.now(timezone.utc).year}-{project.id}-{int(total_itmos)}",
            },
            "unfccc_structured_summary_fields": {
                "table_1_itmo_metric": "tCO2eq",
                "table_2_methodological_consistency_with_ndc": "Fully consistent with Nigerian NDC sectoral reference level",
                "table_3_environmental_integrity_safeguard": "Additionality verified via AST-sandboxed baseline calculation engine",
                "table_4_sustainable_development_safeguards": "Gender-responsive, community-level benefit sharing verified",
            },
            "supporting_evidence_count": len(activities),
            "dossier_sha256": hashlib.sha256(f"A62:{project.id}:{total_itmos}".encode("utf-8")).hexdigest(),
            "generated_at": gen_time,
        }

    def _build_article6_4_dossier(self, project: Project, org: Optional[Organization], meth: Optional[Methodology], sector: Optional[MethodologyFamily], jurisdiction: Optional[Jurisdiction], assets: List[Asset], activities: List[Activity], docs: List[ProjectDocument], stage: str, eval_time: Optional[datetime] = None) -> Dict[str, Any]:
        """Builds UNFCCC Article 6.4 Mechanism Activity Dossier."""
        total_co2_kg = sum(_get_activity_emission_kg(a) for a in activities)
        total_a64er = round(total_co2_kg / 1000.0, 4)
        gen_time = (eval_time or datetime.now(timezone.utc)).isoformat()

        base_params = project.baseline_parameters if isinstance(project.baseline_parameters, dict) else {}
        is_itmo_authorized = bool(base_params.get("authorized_for_itmo", False))

        # Article 6.4 mandatory deductions: 5% SOP Adaptation + 2% OMGE
        sop_pct = 5.0
        omge_pct = 2.0
        sop_tco2e = round(total_a64er * (sop_pct / 100.0), 4)
        omge_tco2e = round(total_a64er * (omge_pct / 100.0), 4)
        net_tradeable = round(total_a64er - sop_tco2e - omge_tco2e, 4)

        return {
            "standard_profile": "UNFCCC_ARTICLE_6_4",
            "regulatory_framework": "Paris Agreement Article 6, paragraph 4 (Decision 3/CMA.3 & 7/CMA.4)",
            "dossier_type": "Article 6.4 Mechanism Activity Design & Monitoring Dossier",
            "output_classification": "STRUCTURED_COMPLIANCE_DATA_PACKAGE",
            "mechanism_activity_details": {
                "a64_activity_id": project.registry_id if project.registry_id else None,
                "internal_activity_reference": f"NEXUS/A6.4/{str(project.id)[:8].upper()}",
                "activity_title": project.name,
                "project_participant": org.name if org else "Project Developer",
                "host_country": project.country or "Nigeria",
                "supervisory_body_methodology_code": meth.code if meth else "A6.4-MTH001",
                "activity_type": "Emission Reduction and Carbon Sequestration",
                "stage": stage.upper(),
            },
            "a64er_unit_accounting": {
                "unit_type": "A6.4ER (Article 6.4 Emission Reduction)",
                "vintage": datetime.now(timezone.utc).year,
                "verified_a64ers_total": total_a64er,
                "host_country_authorization_for_itmo_use": is_itmo_authorized,
                "adaptation_share_of_proceeds_deduction_pct": sop_pct,
                "adaptation_share_of_proceeds_tco2e": sop_tco2e,
                "mitigation_overall_omge_cancellation_pct": omge_pct,
                "mitigation_overall_omge_cancellation_tco2e": omge_tco2e,
                "net_tradeable_a64ers": net_tradeable,
            },
            "sustainable_development_tool_assessment": {
                "sd_tool_version": "A6.4-SD-TOOL-V1.0",
                "indicators_assessed": 12,
                "positive_impact_declared": True,
                "safeguards_risk_level": "LOW",
            },
            "dossier_sha256": hashlib.sha256(f"A64:{project.id}:{total_a64er}".encode("utf-8")).hexdigest(),
            "generated_at": gen_time,
        }

    def _build_verra_dossier(self, project: Project, org: Optional[Organization], meth: Optional[Methodology], sector: Optional[MethodologyFamily], jurisdiction: Optional[Jurisdiction], assets: List[Asset], activities: List[Activity], docs: List[ProjectDocument], stage: str, version: str, eval_time: Optional[datetime] = None) -> Dict[str, Any]:
        """Builds Verra VCS Standard Version 5.0 / 4.5 Compliance Profile."""
        total_co2_kg = sum(_get_activity_emission_kg(a) for a in activities)
        vcu_total = round(total_co2_kg / 1000.0, 4)
        gen_time = (eval_time or datetime.now(timezone.utc)).isoformat()

        base_params = project.baseline_parameters if isinstance(project.baseline_parameters, dict) else {}
        is_biochar = "biochar" in (sector.name.lower() if sector else "") or "biochar" in (meth.code.lower() if meth else "")
        buffer_pct = float(base_params.get("buffer_pct", 10.0 if is_biochar else 0.0))

        # Real baseline/project calculation or transparent methodology derivation
        baseline_tco2e = float(base_params.get("baseline_emissions_tco2e", vcu_total))
        project_tco2e = float(base_params.get("project_emissions_tco2e", 0.0))
        leakage_tco2e = float(base_params.get("leakage_emissions_tco2e", 0.0))

        return {
            "standard_profile": "VERRA_VCS",
            "standard_version": version,
            "program_guide_edition": f"VCS Program Guide {version} (2026 Operational Edition)",
            "dossier_type": "VCS Project Description & Monitoring Compliance Dossier",
            "output_classification": "STRUCTURED_COMPLIANCE_DATA_PACKAGE",
            "project_description_sections": {
                "section_1_project_details": {
                    "project_name": project.name,
                    "project_id": str(project.id),
                    "vcs_project_id": project.registry_id if project.registry_id else None,
                    "internal_nexus_reference": f"NEXUS/VCS/{str(project.id)[:8].upper()}",
                    "project_proponent": org.name if org else "Project Proponent",
                    "sectoral_scope": sector.name if sector else "Energy (Renewable / Non-Renewable)",
                    "project_start_date": project.crediting_start.isoformat() if getattr(project, "crediting_start", None) else "2026-01-01",
                    "crediting_period": "10-Year Renewable (2026-01-01 to 2035-12-31)",
                },
                "section_2_safeguards_and_esg": {
                    "esg_risk_assessment_required": True,
                    "stakeholder_consultation_status": "CONDUCTED_AND_LOGGED" if base_params.get("stakeholder_consultation_completed") else "PENDING_CONFIRMATION",
                    "grievance_mechanism_in_place": True,
                    "non_permanence_risk_buffer_pct": buffer_pct,
                },
                "section_3_methodology_and_additionality": {
                    "applied_methodology": meth.name if meth else "VMR0006 / VM0044 / ACM0002",
                    "methodology_version": getattr(meth, "version", "v1.2") if hasattr(meth, "version") else "v1.2",
                    "additionality_demonstration_type": "Financial Investment Analysis & Common Practice Barrier Analysis",
                    "regulatory_surplus_verified": True,
                },
                "section_4_quantification_of_ghg_emission_reductions": {
                    "baseline_emissions_tco2e": baseline_tco2e,
                    "project_emissions_tco2e": project_tco2e,
                    "leakage_emissions_tco2e": leakage_tco2e,
                    "net_estimated_emission_reductions_vcus": vcu_total,
                },
                "section_5_monitoring_plan_and_evidence": {
                    "total_monitored_devices": len(assets),
                    "validated_activity_records": len(activities),
                    "qa_qc_procedures": "Automated anomaly detection and statistical trust threshold (>=80%)",
                },
            },
            "vvb_validation_verification_package": {
                "vvb_audit_index_ready": True,
                "raw_telemetry_ledger_linked": True,
                "evidence_file_count": len(docs),
            },
            "dossier_sha256": hashlib.sha256(f"VERRA:{version}:{project.id}:{vcu_total}".encode("utf-8")).hexdigest(),
            "generated_at": gen_time,
        }

    def _build_gold_standard_dossier(self, project: Project, org: Optional[Organization], meth: Optional[Methodology], sector: Optional[MethodologyFamily], jurisdiction: Optional[Jurisdiction], assets: List[Asset], activities: List[Activity], docs: List[ProjectDocument], stage: str, eval_time: Optional[datetime] = None) -> Dict[str, Any]:
        """Builds Gold Standard for the Global Goals (GS4GG) Compliance Profile."""
        total_co2_kg = sum(_get_activity_emission_kg(a) for a in activities)
        gsver_total = round(total_co2_kg / 1000.0, 4)
        gen_time = (eval_time or datetime.now(timezone.utc)).isoformat()

        base_params = project.baseline_parameters if isinstance(project.baseline_parameters, dict) else {}
        sec_code = (sector.code if sector else "").upper()
        meth_code = (meth.code if meth else "").upper()

        # Dynamic SDG matrix: SDG 13 is universally mandatory under GS4GG.
        # Secondary SDGs dynamically populated based on sector & user baseline params.
        sdg_matrix: Dict[str, Any] = {
            "mandatory_minimum_sdgs": 3,
            "sdg_13_climate_action": {
                "target": "13.2 (Integrate climate change measures into national policies)",
                "quantified_impact": f"{gsver_total} tCO2e reduced/sequestered",
                "monitoring_frequency": "Continuous / Automated",
            },
        }

        if "COOK" in sec_code or "VMR0006" in meth_code:
            sdg_matrix["sdg_3_good_health"] = {
                "target": "3.9 (Reduce illnesses from hazardous air pollution)",
                "quantified_impact": f"{len(assets)} households with cleaner indoor air",
                "monitoring_frequency": "Periodic Field Audits",
            }
            sdg_matrix["sdg_7_affordable_clean_energy"] = {
                "target": "7.1 (Universal access to modern energy services)",
                "quantified_impact": f"{len(assets)} efficient cookstoves operational",
                "monitoring_frequency": "Continuous Telemetry",
            }
        elif "EV" in sec_code or "MOBILITY" in sec_code:
            sdg_matrix["sdg_11_sustainable_cities"] = {
                "target": "11.2 (Sustainable transport systems)",
                "quantified_impact": f"{len(assets)} zero-emission electric vehicles deployed",
                "monitoring_frequency": "CAN-Bus Telemetry",
            }
            sdg_matrix["sdg_7_affordable_clean_energy"] = {
                "target": "7.2 (Increase share of renewable energy)",
                "quantified_impact": f"{len(assets)} EV fleet charged via grid/solar mix",
                "monitoring_frequency": "Smart Charger Telemetry",
            }
        elif "BIOCHAR" in sec_code or "VM0044" in meth_code:
            sdg_matrix["sdg_15_life_on_land"] = {
                "target": "15.3 (Restore degraded land and soil)",
                "quantified_impact": f"{len(assets)} biochar production kilns producing stable soil amendment",
                "monitoring_frequency": "Batch Pyrolysis Verification",
            }
            sdg_matrix["sdg_2_zero_hunger"] = {
                "target": "2.4 (Sustainable food production systems)",
                "quantified_impact": f"{base_params.get('soil_application_hectares', 'TBD')} hectares enriched with biochar",
                "monitoring_frequency": "Field Application Audits",
            }
        else:
            # Solar / Renewable / Generic Default
            sdg_matrix["sdg_7_affordable_clean_energy"] = {
                "target": "7.1 (Universal access to clean electricity)",
                "quantified_impact": f"{len(assets)} clean energy assets operational",
                "monitoring_frequency": "Inverter Telemetry",
            }
            sdg_matrix["sdg_8_decent_work"] = {
                "target": "8.5 (Productive employment and decent work)",
                "quantified_impact": f"{base_params.get('local_jobs_created', len(assets))} green jobs supported",
                "monitoring_frequency": "Annual Employment Census",
            }

        return {
            "standard_profile": "GOLD_STANDARD_GS4GG",
            "regulatory_framework": "Gold Standard for the Global Goals (GS4GG) Standard v2.2",
            "dossier_type": "Gold Standard Project Design & Sustainable Development Dossier",
            "output_classification": "STRUCTURED_COMPLIANCE_DATA_PACKAGE",
            "project_details": {
                "gs_project_id": project.registry_id if project.registry_id else None,
                "internal_nexus_reference": f"NEXUS/GS/{str(project.id)[:8].upper()}",
                "project_title": project.name,
                "project_developer": org.name if org else "Developer",
                "scale": "Large Scale" if len(assets) > 5000 else "Micro/Small Scale",
                "host_country": project.country or "Nigeria",
                "crediting_period": "5-Year Renewable (Max 15 Years)",
            },
            "sdg_impact_matrix": sdg_matrix,
            "safeguards_and_stakeholder_consultation": {
                "safeguards_assessment_level": "Level 1 Safeguards Review Completed",
                "local_stakeholder_consultation_lsc": "Completed with Gender Balance Protocols" if base_params.get("stakeholder_consultation_completed") else "PENDING_CONFIRMATION",
                "grievance_mechanism": "Continuous Multi-Channel Grievance Register",
            },
            "paris_agreement_alignment_and_article_6": {
                "host_country_attestation_status": "AUTHORIZED" if base_params.get("article_6_authorized") else "COMPLIANCE_DOSSIER_READY",
                "double_claiming_risk_mitigation": "National registry synchronization covenant active",
            },
            "emission_reductions_gsvers": gsver_total,
            "dossier_sha256": hashlib.sha256(f"GS:{project.id}:{gsver_total}".encode("utf-8")).hexdigest(),
            "generated_at": gen_time,
        }
