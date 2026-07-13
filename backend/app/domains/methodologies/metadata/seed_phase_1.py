"""
=============================================================================
VeriField Nexus — Methodology Registry Seed (Phase 1)
=============================================================================
Seeds the Methodology Registry Engine with initial registries, families,
methodologies, versions, calculation rules, and legacy code mappings.
=============================================================================
"""

import asyncio
import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker,
                                    create_async_engine)

from app.core.config import settings
from app.domains.methodologies.models.base_registry import (
    Methodology, MethodologyFamily, MethodologyRegistry, MethodologyVersion)
from app.domains.methodologies.models.components import (
    CalculationRule, MonitoringTemplate, VersionCalculationRule,
    VersionMonitoringTemplate)
from app.domains.methodologies.models.legacy_mapping import \
    LegacyMethodologyMapping


async def seed_data(db: AsyncSession):
    """Idempotent seed — skips if registries already exist."""
    existing = await db.execute(select(MethodologyRegistry).limit(1))
    if existing.scalars().first():
        print("Registry already seeded — skipping.")
        return

    # ─── Registries ───
    verra = MethodologyRegistry(
        code="VERRA",
        name="Verra (VCS)",
        description="Verified Carbon Standard",
        is_active=True,
    )
    gs = MethodologyRegistry(
        code="GOLD_STANDARD",
        name="Gold Standard (GS)",
        description="Gold Standard for the Global Goals",
        is_active=True,
    )
    cdm = MethodologyRegistry(
        code="CDM",
        name="Clean Development Mechanism",
        description="UNFCCC CDM",
        is_active=True,
    )
    csi = MethodologyRegistry(
        code="CSI",
        name="Carbon Standards International",
        description="European biochar certification",
        is_active=True,
    )

    db.add_all([verra, gs, cdm, csi])
    await db.flush()

    # ─── Families ───
    cookstoves = MethodologyFamily(code="COOKSTOVES", name="Clean Cookstoves")
    hybrid = MethodologyFamily(code="HYBRID_ENERGY", name="Hybrid Energy & Mini-grids")
    biochar_fam = MethodologyFamily(code="BIOCHAR", name="Biochar Carbon Removal")
    ev_fam = MethodologyFamily(code="EV_MOBILITY", name="EV Mobility")

    db.add_all([cookstoves, hybrid, biochar_fam, ev_fam])
    await db.flush()

    # ─── Methodologies ───

    # Cookstoves
    vm0006 = Methodology(
        code="VM0006",
        name="Fuel Switching (Cookstoves)",
        registry_id=verra.id,
        family_id=cookstoves.id,
    )
    vm0050 = Methodology(
        code="VMR0050",
        name="Thermal Energy Displacement",
        registry_id=verra.id,
        family_id=cookstoves.id,
    )
    tpddtec = Methodology(
        code="GS_TPDDTEC",
        name="Displace Decentralized Thermal Energy",
        registry_id=gs.id,
        family_id=cookstoves.id,
    )
    mecd = Methodology(
        code="GS_MECD",
        name="Metered Energy Cooking Devices",
        registry_id=gs.id,
        family_id=cookstoves.id,
    )
    ams_ii_g = Methodology(
        code="AMS_II_G",
        name="Energy Efficiency in Thermal Applications",
        registry_id=cdm.id,
        family_id=cookstoves.id,
    )

    # Hybrid Energy
    energy_disp = Methodology(
        code="ENERGY_DISPLACEMENT",
        name="Renewable Energy Displacement",
        registry_id=verra.id,
        family_id=hybrid.id,
    )
    minigrid_disp = Methodology(
        code="MINIGRID_DIESEL_DISPLACEMENT",
        name="Mini-Grid Diesel Displacement",
        registry_id=verra.id,
        family_id=hybrid.id,
    )
    shs_disp = Methodology(
        code="SHS_RENEWABLE_DISPLACEMENT",
        name="Solar Home System Displacement",
        registry_id=gs.id,
        family_id=hybrid.id,
    )
    ci_disp = Methodology(
        code="CI_GRID_DISPLACEMENT",
        name="C&I Grid Displacement",
        registry_id=verra.id,
        family_id=hybrid.id,
    )
    ams_i_f = Methodology(
        code="AMS_I_F",
        name="Renewable Electricity for Captive Use",
        registry_id=cdm.id,
        family_id=hybrid.id,
    )

    # Biochar
    biochar_csink = Methodology(
        code="BIOCHAR_C_SINK",
        name="Biochar Carbon Sink",
        registry_id=csi.id,
        family_id=biochar_fam.id,
    )
    vm0044 = Methodology(
        code="VM0044",
        name="Biochar Utilization in Soil",
        registry_id=verra.id,
        family_id=biochar_fam.id,
    )

    # EV Mobility
    ev_disp = Methodology(
        code="EV_DISPLACEMENT",
        name="EV Fossil Fuel Displacement",
        registry_id=gs.id,
        family_id=ev_fam.id,
    )

    all_methodologies = [
        vm0006,
        vm0050,
        tpddtec,
        mecd,
        ams_ii_g,
        energy_disp,
        minigrid_disp,
        shs_disp,
        ci_disp,
        ams_i_f,
        biochar_csink,
        vm0044,
        ev_disp,
    ]
    db.add_all(all_methodologies)
    await db.flush()

    # ─── Versions ───
    vm0006_v1 = MethodologyVersion(
        methodology_id=vm0006.id,
        version="1.1.0",
        status="active",
        release_date=date(2020, 1, 1),
    )
    vm0050_v1 = MethodologyVersion(
        methodology_id=vm0050.id,
        version="1.0.0",
        status="active",
        release_date=date(2023, 1, 1),
    )
    tpddtec_v3 = MethodologyVersion(
        methodology_id=tpddtec.id,
        version="3.1.0",
        status="active",
        release_date=date(2021, 1, 1),
    )
    mecd_v3 = MethodologyVersion(
        methodology_id=mecd.id,
        version="3.0.0",
        status="active",
        release_date=date(2022, 1, 1),
    )
    ams_ii_g_v1 = MethodologyVersion(
        methodology_id=ams_ii_g.id,
        version="1.0.0",
        status="active",
        release_date=date(2019, 1, 1),
    )

    energy_disp_v1 = MethodologyVersion(
        methodology_id=energy_disp.id,
        version="1.0.0",
        status="active",
        release_date=date(2022, 1, 1),
    )
    minigrid_v1 = MethodologyVersion(
        methodology_id=minigrid_disp.id,
        version="1.0.0",
        status="active",
        release_date=date(2022, 1, 1),
    )
    shs_v1 = MethodologyVersion(
        methodology_id=shs_disp.id,
        version="1.0.0",
        status="active",
        release_date=date(2022, 1, 1),
    )
    ci_v1 = MethodologyVersion(
        methodology_id=ci_disp.id,
        version="1.0.0",
        status="active",
        release_date=date(2022, 1, 1),
    )
    ams_i_f_v1 = MethodologyVersion(
        methodology_id=ams_i_f.id,
        version="1.0.0",
        status="active",
        release_date=date(2020, 1, 1),
    )

    biochar_csink_v1 = MethodologyVersion(
        methodology_id=biochar_csink.id,
        version="1.0.0",
        status="active",
        release_date=date(2023, 1, 1),
    )
    vm0044_v1 = MethodologyVersion(
        methodology_id=vm0044.id,
        version="1.1.0",
        status="active",
        release_date=date(2022, 6, 1),
    )

    ev_disp_v1 = MethodologyVersion(
        methodology_id=ev_disp.id,
        version="1.0.0",
        status="active",
        release_date=date(2023, 1, 1),
    )

    all_versions = [
        vm0006_v1,
        vm0050_v1,
        tpddtec_v3,
        mecd_v3,
        ams_ii_g_v1,
        energy_disp_v1,
        minigrid_v1,
        shs_v1,
        ci_v1,
        ams_i_f_v1,
        biochar_csink_v1,
        vm0044_v1,
        ev_disp_v1,
    ]
    db.add_all(all_versions)
    await db.flush()

    # ─── Calculation Rules ───
    rule_vm0006 = CalculationRule(
        code="calc_vm0006_er",
        name="VM0006 Emission Reduction",
        formula="((baseline_fuel_kg_yr - project_fuel_kg_yr) / 1000.0) * ncv_tj_ton * ef_tco2_tj * fraction_non_renewable_biomass * sum_usage_rate",
        inputs_schema={
            "baseline_fuel_kg_yr": "number",
            "project_fuel_kg_yr": "number",
            "ncv_tj_ton": "number",
            "ef_tco2_tj": "number",
            "fraction_non_renewable_biomass": "number",
            "sum_usage_rate": "number",
        },
        outputs_schema={"tco2e": "number"},
    )
    rule_tpddtec = CalculationRule(
        code="calc_tpddtec_er",
        name="TPDDTEC Emission Reduction",
        formula="(baseline_fuel_kg_yr * (1.0 - thermal_efficiency_baseline / thermal_efficiency_project) * ncv_mj_kg / 1e6) * ef_tco2_tj * fraction_non_renewable_biomass * leakage_factor",
        inputs_schema={
            "baseline_fuel_kg_yr": "number",
            "thermal_efficiency_baseline": "number",
            "thermal_efficiency_project": "number",
            "ncv_mj_kg": "number",
            "ef_tco2_tj": "number",
            "fraction_non_renewable_biomass": "number",
            "leakage_factor": "number",
        },
        outputs_schema={"tco2e": "number"},
    )
    rule_mecd = CalculationRule(
        code="calc_mecd_er",
        name="MECD Emission Reduction",
        formula="metered_energy_kwh * baseline_emission_factor_tco2_kwh",
        inputs_schema={
            "metered_energy_kwh": "number",
            "baseline_emission_factor_tco2_kwh": "number",
        },
        outputs_schema={"tco2e": "number"},
    )
    rule_biochar = CalculationRule(
        code="calc_biochar_csink",
        name="Biochar C-Sink",
        formula="(batch_weight_kg * lab_carbon_content_pct / 100.0) * 3.664 / 1000.0",
        inputs_schema={"batch_weight_kg": "number", "lab_carbon_content_pct": "number"},
        outputs_schema={"tco2e": "number"},
    )
    rule_ev = CalculationRule(
        code="calc_ev_displacement",
        name="EV Fossil Fuel Displacement",
        formula="trip_distance_km * baseline_emission_factor_kgco2_km / 1000.0",
        inputs_schema={
            "trip_distance_km": "number",
            "baseline_emission_factor_kgco2_km": "number",
        },
        outputs_schema={"tco2e": "number"},
    )
    rule_energy_disp = CalculationRule(
        code="calc_energy_displacement",
        name="Energy Displacement",
        formula="solar_generation_kwh * grid_emission_factor_tco2_kwh",
        inputs_schema={
            "solar_generation_kwh": "number",
            "grid_emission_factor_tco2_kwh": "number",
        },
        outputs_schema={"tco2e": "number"},
    )

    all_rules = [
        rule_vm0006,
        rule_tpddtec,
        rule_mecd,
        rule_biochar,
        rule_ev,
        rule_energy_disp,
    ]
    db.add_all(all_rules)
    await db.flush()

    # ─── Link Rules to Versions ───
    version_rule_links = [
        VersionCalculationRule(
            version_id=vm0006_v1.id, rule_id=rule_vm0006.id, execution_order=1
        ),
        VersionCalculationRule(
            version_id=vm0050_v1.id, rule_id=rule_vm0006.id, execution_order=1
        ),  # VMR0050 uses same formula as VM0006
        VersionCalculationRule(
            version_id=tpddtec_v3.id, rule_id=rule_tpddtec.id, execution_order=1
        ),
        VersionCalculationRule(
            version_id=mecd_v3.id, rule_id=rule_mecd.id, execution_order=1
        ),
        VersionCalculationRule(
            version_id=biochar_csink_v1.id, rule_id=rule_biochar.id, execution_order=1
        ),
        VersionCalculationRule(
            version_id=vm0044_v1.id, rule_id=rule_biochar.id, execution_order=1
        ),
        VersionCalculationRule(
            version_id=ev_disp_v1.id, rule_id=rule_ev.id, execution_order=1
        ),
        VersionCalculationRule(
            version_id=energy_disp_v1.id, rule_id=rule_energy_disp.id, execution_order=1
        ),
        VersionCalculationRule(
            version_id=minigrid_v1.id, rule_id=rule_energy_disp.id, execution_order=1
        ),
        VersionCalculationRule(
            version_id=shs_v1.id, rule_id=rule_energy_disp.id, execution_order=1
        ),
        VersionCalculationRule(
            version_id=ci_v1.id, rule_id=rule_energy_disp.id, execution_order=1
        ),
    ]
    db.add_all(version_rule_links)
    await db.flush()

    # ─── Monitoring Templates ───
    param_fuel = MonitoringTemplate(
        code="fuel_consumption_kg",
        name="Fuel Consumption (kg)",
        data_type="numeric",
        unit="kg",
    )
    param_kwh = MonitoringTemplate(
        code="metered_energy_kwh",
        name="Metered Energy (kWh)",
        data_type="numeric",
        unit="kWh",
    )
    param_biochar_wt = MonitoringTemplate(
        code="biochar_batch_weight_kg",
        name="Biochar Batch Weight (kg)",
        data_type="numeric",
        unit="kg",
    )
    param_carbon_pct = MonitoringTemplate(
        code="lab_carbon_content_pct",
        name="Lab Carbon Content (%)",
        data_type="numeric",
        unit="%",
    )
    param_trip_km = MonitoringTemplate(
        code="trip_distance_km",
        name="Trip Distance (km)",
        data_type="numeric",
        unit="km",
    )
    param_solar_kwh = MonitoringTemplate(
        code="solar_generation_kwh",
        name="Solar Generation (kWh)",
        data_type="numeric",
        unit="kWh",
    )

    db.add_all(
        [
            param_fuel,
            param_kwh,
            param_biochar_wt,
            param_carbon_pct,
            param_trip_km,
            param_solar_kwh,
        ]
    )
    await db.flush()

    # ─── Link Monitoring Templates to Versions ───
    monitoring_links = [
        VersionMonitoringTemplate(
            version_id=vm0006_v1.id, template_id=param_fuel.id, is_required=True
        ),
        VersionMonitoringTemplate(
            version_id=vm0050_v1.id, template_id=param_fuel.id, is_required=True
        ),
        VersionMonitoringTemplate(
            version_id=tpddtec_v3.id, template_id=param_fuel.id, is_required=True
        ),
        VersionMonitoringTemplate(
            version_id=mecd_v3.id, template_id=param_kwh.id, is_required=True
        ),
        VersionMonitoringTemplate(
            version_id=biochar_csink_v1.id,
            template_id=param_biochar_wt.id,
            is_required=True,
        ),
        VersionMonitoringTemplate(
            version_id=ev_disp_v1.id, template_id=param_trip_km.id, is_required=True
        ),
        VersionMonitoringTemplate(
            version_id=energy_disp_v1.id,
            template_id=param_solar_kwh.id,
            is_required=True,
        ),
    ]
    db.add_all(monitoring_links)
    await db.flush()

    # ─── Legacy Mappings (all old hardcoded codes → new UUIDs) ───
    legacy_mappings = [
        # Cookstoves
        LegacyMethodologyMapping(
            legacy_code="VM0006", methodology_version_id=vm0006_v1.id
        ),
        LegacyMethodologyMapping(
            legacy_code="VMR0050", methodology_version_id=vm0050_v1.id
        ),
        LegacyMethodologyMapping(
            legacy_code="GS_TPDDTEC", methodology_version_id=tpddtec_v3.id
        ),
        LegacyMethodologyMapping(
            legacy_code="GS_MECD", methodology_version_id=mecd_v3.id
        ),
        # Hybrid Energy
        LegacyMethodologyMapping(
            legacy_code="ENERGY_DISPLACEMENT", methodology_version_id=energy_disp_v1.id
        ),
        LegacyMethodologyMapping(
            legacy_code="MINIGRID_DIESEL_DISPLACEMENT",
            methodology_version_id=minigrid_v1.id,
        ),
        LegacyMethodologyMapping(
            legacy_code="SHS_RENEWABLE_DISPLACEMENT", methodology_version_id=shs_v1.id
        ),
        LegacyMethodologyMapping(
            legacy_code="CI_GRID_DISPLACEMENT", methodology_version_id=ci_v1.id
        ),
        LegacyMethodologyMapping(
            legacy_code="AMS-I.F", methodology_version_id=ams_i_f_v1.id
        ),
        # Biochar
        LegacyMethodologyMapping(
            legacy_code="BIOCHAR_C_SINK", methodology_version_id=biochar_csink_v1.id
        ),
        LegacyMethodologyMapping(
            legacy_code="VM0044", methodology_version_id=vm0044_v1.id
        ),
        # EV
        LegacyMethodologyMapping(
            legacy_code="EV_DISPLACEMENT", methodology_version_id=ev_disp_v1.id
        ),
    ]
    db.add_all(legacy_mappings)

    await db.commit()
    print("✅ Seeded Methodology Registry — Phase 1 complete.")
    print(
        f"   Registries: 4  |  Families: 4  |  Methodologies: {len(all_methodologies)}"
    )
    print(
        f"   Versions: {len(all_versions)}  |  Rules: {len(all_rules)}  |  Legacy Mappings: {len(legacy_mappings)}"
    )


async def main():
    db_url = settings.database_url
    if db_url and db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif db_url and db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    engine = create_async_engine(
        db_url,
        connect_args={
            "ssl": "require",
            "server_settings": {"jit": "off"},
            "command_timeout": 10.0,
            "statement_cache_size": 0,
            "prepared_statement_cache_size": 0,
            "prepared_statement_name_func": lambda: f"__asyncpg_{uuid.uuid4()}__",
        },
    )
    async_session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session_factory() as db:
        await seed_data(db)


if __name__ == "__main__":
    asyncio.run(main())
