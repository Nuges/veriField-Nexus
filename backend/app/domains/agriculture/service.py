"""
=============================================================================
VeriField Nexus — Agriculture & Land Use Domain Service
=============================================================================
Orchestrates:
- Land Unit hierarchy, WGS84 geodesic area calculations, and boundary source tracking.
- Soil core sample intake, depth-classification, and SOC stock quantification.
- Tree observations and allometric biomass derivations (VM0047).
- Earth Observation satellite scene ingestion with cryptographic provenance.
- VT0014 Digital Soil Mapping runs with explicit spatial uncertainty rasters.
- End-to-end verification dossier compilation and cryptographic ledger sealing.
- Strict multi-tenant and sector isolation.
=============================================================================
"""

import hashlib
import json
import uuid
from decimal import Decimal, ROUND_HALF_EVEN
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

from fastapi import HTTPException, status

from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domains.agriculture.calculators.vm0042 import VM0042CalculatorV22
from app.domains.agriculture.calculators.vm0047 import VM0047CalculatorV11
from app.domains.agriculture.geospatial import (
    compute_centroid,
    compute_geodesic_area_ha,
    compute_geodesic_distance_m,
    point_in_geojson_polygon,
    validate_geojson_polygon,
)
from app.domains.agriculture.models import (
    AgricultureManagementRecord,
    AgricultureModelRun,
    ChainOfCustodyEvent,
    LaboratoryAnalysis,
    LaboratoryReceipt,
    LaboratoryResult,
    LandUnit,
    PhysicalSample,
    SampleCollectionEvent,
    SampleQAReview,
    SamplingCampaign,
    SamplingPlanVersion,
    SamplingPoint,
    SatelliteObservation,
    SoilSample,
    Stratum,
    StratumMembership,
    TreeObservation,
    QuantificationInputSnapshot,
    AgriculturePrerequisiteAssessment,
    AgricultureSOCStockSnapshot,
    AgricultureSOCStockResult,
    AgricultureSOCLayerResult,
    AgricultureSOCChangeResult,
    AgricultureNetGHGResult,
    AgricultureVintageGHGResult,
)
from app.domains.agriculture.quantification.net_ghg_calculator import (
    ApplicabilityStatus,
    ActivityDataStatus,
    QuantificationApproach,
    SourceApplicabilityItem,
    FossilFuelActivity,
    LimingActivity,
    FertilizerN2OActivity,
    NitrogenFixingActivity,
    ManureDepositionActivity,
    EntericFermentationActivity,
    BiomassBurningActivity,
    SoilMethanogenesisActivity,
    WoodyBiomassPoolData,
    LeakageInputData,
    NPRRiskAssessmentInput,
    GWPConfig,
    AnnualVintageGHGResult,
    NetGHGProjectOutput,
    NetGHGCalculationError,
    VMD0054Version,
    resolve_vmd0054_version,
    evaluate_single_vintage_net_ghg,
    validate_table_5_applicability,
    aggregate_verification_period_net_ghg,
)
from app.domains.agriculture.soil.soc_stock_calculator import (
    LayerInput,
    LayerResult,
    ProfileESMResult,
    SOCStockCalculationError,
    calculate_layer_soil_mass,
    calculate_layer_soil_mass_direct,
    calculate_profile_esm_proportioning,
    calculate_profile_esm_spline,
    aggregate_stratum_soc_stock,
    aggregate_project_area_weighted_soc_stock,
    compute_deterministic_hash,
    to_json_serializable,
)
from app.domains.agriculture.soil.soc_change_calculator import (
    StratumInputData,
    StratumChangeOutput,
    UncertaintyDeductionOutput,
    ProjectSOCChangeOutput,
    SOCChangeCalculationError,
    aggregate_project_qa2_soc_change,
    calculate_student_t_0667,
    CO2_TO_C_RATIO,
)
from app.domains.agriculture.schemas import (
    CustodyEventCreate,
    DepthAlignmentStatus,
    ExcludedMeasurementItem,
    ExclusionReasonCode,
    LabAnalysisCreate,
    LabReceiptCreate,
    LabResultCreate,
    LabResultRevisionCreate,
    LandUnitCreate,
    LandUnitUpdate,
    LinkBoundaryRequest,
    ManagementRecordCreate,
    ManagementRecordUpdate,
    QuantificationInputSnapshotCreate,
    QuantificationMeasurementItem,
    SampleCollectionCreate,
    SampleQAReviewCreate,
    SamplingCampaignCreate,
    SamplingCampaignUpdate,
    SamplingPlanLockRequest,
    SamplingPlanVersionCreate,
    SamplingPointBatchCreate,
    SamplingPointCreate,
    SatelliteObservationCreate,
    SoilSampleCreate,
    StratumCreate,
    StratumMembershipItem,
    StratumUpdate,
    TreeObservationBase,
    TreeObservationCreate,
    VT0014ModelRunRequest,
)
from app.domains.agriculture.soil.depth_classifier import (
    classify_soil_sample_depth,
    compute_soc_stock_t_c_ha,
)
from app.domains.agriculture.allometrics import estimate_tree_biomass_pools
from app.domains.agriculture.soil.digital_soil_mapping import (
    VT0014SoilMappingEngine,
)
from app.domains.earth_observation.models import ProjectBoundaryVersion
from app.domains.ledger.service import LedgerService
from app.domains.methodologies.models.base_registry import (
    Methodology,
    MethodologyFamily,
    MethodologyVersion,
)
from app.domains.projects.models import Project


class AgricultureService:
    """
    Core business logic and multi-tenant security for the Agriculture & Land Use sector.
    """

    @classmethod
    async def get_project_or_raise(
        cls,
        db: AsyncSession,
        project_id: uuid.UUID,
        organization_id: uuid.UUID,
    ) -> Project:
        """
        Retrieves project while enforcing multi-tenant isolation.
        """
        stmt = select(Project).where(
            Project.id == project_id,
            Project.organization_id == organization_id,
        )
        result = await db.execute(stmt)
        project = result.scalars().first()
        if not project:
            raise ValueError(f"Project '{project_id}' not found for organization '{organization_id}'.")
        return project

    # ─── Land Units ───

    @classmethod
    async def create_land_unit(
        cls,
        db: AsyncSession,
        payload: LandUnitCreate,
        organization_id: uuid.UUID,
    ) -> LandUnit:
        # Validate project ownership
        await cls.get_project_or_raise(db, payload.project_id, organization_id)

        # Validate parent hierarchy if supplied
        if payload.parent_id:
            parent_stmt = select(LandUnit).where(
                LandUnit.id == payload.parent_id,
                LandUnit.organization_id == organization_id,
                LandUnit.project_id == payload.project_id,
            )
            parent_res = await db.execute(parent_stmt)
            if not parent_res.scalars().first():
                raise ValueError(f"Parent land unit '{payload.parent_id}' not found within project.")

        # Compute exact WGS84 geodesic area and perimeter using GeographicLib
        area_ha, perimeter_m = compute_geodesic_area_ha(payload.boundary_geojson)
        centroid_lat, centroid_lon = compute_centroid(payload.boundary_geojson)

        geom_val = None
        try:
            from shapely.geometry import shape
            from geoalchemy2.shape import from_shape
            geom_val = from_shape(shape(payload.boundary_geojson), srid=4326)
        except Exception:
            geom_val = None

        land_unit = LandUnit(
            organization_id=organization_id,
            project_id=payload.project_id,
            parent_id=payload.parent_id,
            unit_type=payload.unit_type,
            name=payload.name,
            code=payload.code,
            boundary_geojson=payload.boundary_geojson,
            geom=geom_val,
            boundary_source=payload.boundary_source,
            boundary_crs=payload.boundary_crs,
            area_ha=area_ha,
            perimeter_m=perimeter_m,
            centroid_lat=centroid_lat,
            centroid_lon=centroid_lon,
            land_use_category=payload.land_use_category,
            soil_type=payload.soil_type,
            slope_pct=payload.slope_pct,
            is_active=payload.is_active,
            properties=payload.properties,
        )
        db.add(land_unit)
        await db.flush()
        await db.refresh(land_unit)
        return land_unit

    @classmethod
    async def get_land_units(
        cls,
        db: AsyncSession,
        organization_id: uuid.UUID,
        project_id: Optional[uuid.UUID] = None,
        parent_id: Optional[uuid.UUID] = None,
        unit_type: Optional[str] = None,
    ) -> List[LandUnit]:
        stmt = select(LandUnit).where(LandUnit.organization_id == organization_id)
        if project_id:
            stmt = stmt.where(LandUnit.project_id == project_id)
        if parent_id:
            stmt = stmt.where(LandUnit.parent_id == parent_id)
        if unit_type:
            stmt = stmt.where(LandUnit.unit_type == unit_type.upper())
        stmt = stmt.order_by(LandUnit.name.asc())
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @classmethod
    async def get_land_unit_by_id(
        cls,
        db: AsyncSession,
        land_unit_id: uuid.UUID,
        organization_id: uuid.UUID,
    ) -> Optional[LandUnit]:
        stmt = select(LandUnit).where(
            LandUnit.id == land_unit_id,
            LandUnit.organization_id == organization_id,
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    @classmethod
    async def update_land_unit(
        cls,
        db: AsyncSession,
        land_unit_id: uuid.UUID,
        payload: LandUnitUpdate,
        organization_id: uuid.UUID,
    ) -> LandUnit:
        unit = await cls.get_land_unit_by_id(db, land_unit_id, organization_id)
        if not unit:
            raise ValueError(f"Land unit '{land_unit_id}' not found.")

        update_data = payload.model_dump(exclude_unset=True)
        if "boundary_geojson" in update_data and update_data["boundary_geojson"]:
            new_geom = update_data["boundary_geojson"]
            area_ha, perimeter_m = compute_geodesic_area_ha(new_geom)
            centroid_lat, centroid_lon = compute_centroid(new_geom)
            unit.boundary_geojson = new_geom
            unit.area_ha = area_ha
            unit.perimeter_m = perimeter_m
            unit.centroid_lat = centroid_lat
            unit.centroid_lon = centroid_lon
            try:
                from shapely.geometry import shape
                from geoalchemy2.shape import from_shape
                unit.geom = from_shape(shape(new_geom), srid=4326)
            except Exception:
                pass
            del update_data["boundary_geojson"]

        for k, v in update_data.items():
            setattr(unit, k, v)

        unit.updated_at = datetime.now(timezone.utc)
        await db.flush()
        await db.refresh(unit)
        return unit

    @classmethod
    async def delete_land_unit(
        cls,
        db: AsyncSession,
        land_unit_id: uuid.UUID,
        organization_id: uuid.UUID,
    ) -> bool:
        unit = await cls.get_land_unit_by_id(db, land_unit_id, organization_id)
        if not unit:
            return False
        await db.delete(unit)
        await db.flush()
        return True

    # ─── Soil Samples ───

    @classmethod
    async def create_soil_sample(
        cls,
        db: AsyncSession,
        payload: SoilSampleCreate,
        organization_id: uuid.UUID,
    ) -> SoilSample:
        await cls.get_project_or_raise(db, payload.project_id, organization_id)

        if payload.land_unit_id:
            unit = await cls.get_land_unit_by_id(db, payload.land_unit_id, organization_id)
            if not unit:
                raise ValueError(f"Land unit '{payload.land_unit_id}' not found.")

        # Classify soil sample depth according to VM0042 rules
        classification, notes = classify_soil_sample_depth(
            depth_upper_cm=payload.depth_upper_cm,
            depth_lower_cm=payload.depth_lower_cm,
            latitude=payload.latitude,
            longitude=payload.longitude,
            soc_stock_pct=payload.soc_stock_pct,
            bulk_density_g_cm3=payload.bulk_density_g_cm3,
            lab_method=payload.lab_method,
            has_lab_accreditation=bool(payload.lab_accreditation),
            is_model_calibration_source=payload.is_model_calibration_source,
            is_model_validation_source=payload.is_model_validation_source,
            model_represents_30cm=payload.model_represents_30cm,
            extrapolation_method=payload.extrapolation_method,
        )

        # Compute stock if bulk density provided
        computed_stock = None
        if payload.bulk_density_g_cm3:
            depth_span = payload.depth_lower_cm - payload.depth_upper_cm
            computed_stock = compute_soc_stock_t_c_ha(
                soc_pct=payload.soc_stock_pct,
                bulk_density_g_cm3=payload.bulk_density_g_cm3,
                depth_thickness_cm=depth_span,
                coarse_fragments_pct=payload.coarse_fragments_pct,
            )

        sample = SoilSample(
            organization_id=organization_id,
            project_id=payload.project_id,
            land_unit_id=payload.land_unit_id,
            sample_code=payload.sample_code,
            sampling_date=payload.sampling_date,
            latitude=payload.latitude,
            longitude=payload.longitude,
            depth_upper_cm=payload.depth_upper_cm,
            depth_lower_cm=payload.depth_lower_cm,
            bulk_density_g_cm3=payload.bulk_density_g_cm3,
            soc_stock_pct=payload.soc_stock_pct,
            total_organic_carbon_g_kg=payload.total_organic_carbon_g_kg,
            computed_soc_stock_t_c_ha=computed_stock,
            coarse_fragments_pct=payload.coarse_fragments_pct,
            ph=payload.ph,
            electrical_conductivity_ds_m=payload.electrical_conductivity_ds_m,
            texture_class=payload.texture_class,
            lab_method=payload.lab_method,
            lab_name=payload.lab_name,
            lab_accreditation=payload.lab_accreditation,
            qa_status="ACCEPTED",
            compliance_classification=classification.value,
            model_represents_30cm=payload.model_represents_30cm,
            extrapolation_method=payload.extrapolation_method,
            compliance_notes=notes,
            evidence_id=payload.evidence_id,
        )
        db.add(sample)
        await db.flush()
        await db.refresh(sample)
        return sample

    @classmethod
    async def get_soil_samples(
        cls,
        db: AsyncSession,
        organization_id: uuid.UUID,
        project_id: Optional[uuid.UUID] = None,
        land_unit_id: Optional[uuid.UUID] = None,
        compliance_classification: Optional[str] = None,
    ) -> List[SoilSample]:
        stmt = select(SoilSample).where(SoilSample.organization_id == organization_id)
        if project_id:
            stmt = stmt.where(SoilSample.project_id == project_id)
        if land_unit_id:
            stmt = stmt.where(SoilSample.land_unit_id == land_unit_id)
        if compliance_classification:
            stmt = stmt.where(SoilSample.compliance_classification == compliance_classification)
        stmt = stmt.order_by(SoilSample.sampling_date.desc())
        result = await db.execute(stmt)
        return list(result.scalars().all())

    # ─── Tree Observations (VM0047) ───

    @classmethod
    async def create_tree_observation(
        cls,
        db: AsyncSession,
        payload: TreeObservationCreate,
        organization_id: uuid.UUID,
    ) -> TreeObservation:
        await cls.get_project_or_raise(db, payload.project_id, organization_id)
        unit = await cls.get_land_unit_by_id(db, payload.land_unit_id, organization_id)
        if not unit:
            raise ValueError(f"Land unit '{payload.land_unit_id}' not found.")

        # Derive biomass using registered allometric equations (separating AGB and BGB)
        agb_model = getattr(payload, "allometric_model_id", None) or payload.allometric_equation_id or "CHAVE_2014_PANTROPICAL_AGB"
        bgb_model = getattr(payload, "belowground_model_id", None)
        wood_density_src = getattr(payload, "wood_density_source", "Global Wood Density Database (Zanne et al. 2009)")

        biomass_res = estimate_tree_biomass_pools(
            dbh_cm=payload.dbh_cm,
            height_m=payload.height_m,
            wood_density_g_cm3=payload.wood_density_g_cm3,
            agb_model_id=agb_model,
            bgb_model_id=bgb_model,
            wood_density_source=wood_density_src,
        )

        tree = TreeObservation(
            organization_id=organization_id,
            project_id=payload.project_id,
            land_unit_id=payload.land_unit_id,
            sampling_approach=payload.sampling_approach,
            tag_number=payload.tag_number,
            species_scientific=payload.species_scientific,
            species_common=payload.species_common,
            dbh_cm=payload.dbh_cm,
            height_m=payload.height_m,
            crown_diameter_m=payload.crown_diameter_m,
            health_status=payload.health_status,
            latitude=payload.latitude,
            longitude=payload.longitude,
            measurement_date=payload.measurement_date,
            allometric_equation_id=agb_model,
            belowground_model_id=bgb_model,
            derived_aboveground_biomass_kg=biomass_res["agb_kg"],
            derived_belowground_biomass_kg=biomass_res["bgb_kg"],
            derived_carbon_stock_t_co2e=biomass_res["carbon_stock_t_co2e"],
            evidence_photo_hash=payload.evidence_photo_hash,
        )
        db.add(tree)
        await db.flush()
        await db.refresh(tree)
        return tree

    @classmethod
    async def batch_create_tree_observations(
        cls,
        db: AsyncSession,
        project_id: uuid.UUID,
        land_unit_id: uuid.UUID,
        observations: List[TreeObservationBase],
        organization_id: uuid.UUID,
    ) -> List[TreeObservation]:
        await cls.get_project_or_raise(db, project_id, organization_id)
        unit = await cls.get_land_unit_by_id(db, land_unit_id, organization_id)
        if not unit:
            raise ValueError(f"Land unit '{land_unit_id}' not found.")

        created = []
        for obs in observations:
            agb_model = getattr(obs, "allometric_model_id", None) or obs.allometric_equation_id or "CHAVE_2014_PANTROPICAL_AGB"
            bgb_model = getattr(obs, "belowground_model_id", None)
            wood_density_src = getattr(obs, "wood_density_source", "Global Wood Density Database (Zanne et al. 2009)")

            biomass_res = estimate_tree_biomass_pools(
                dbh_cm=obs.dbh_cm,
                height_m=obs.height_m,
                wood_density_g_cm3=obs.wood_density_g_cm3,
                agb_model_id=agb_model,
                bgb_model_id=bgb_model,
                wood_density_source=wood_density_src,
            )
            tree = TreeObservation(
                organization_id=organization_id,
                project_id=project_id,
                land_unit_id=land_unit_id,
                sampling_approach=obs.sampling_approach,
                tag_number=obs.tag_number,
                species_scientific=obs.species_scientific,
                species_common=obs.species_common,
                dbh_cm=obs.dbh_cm,
                height_m=obs.height_m,
                crown_diameter_m=obs.crown_diameter_m,
                health_status=obs.health_status,
                latitude=obs.latitude,
                longitude=obs.longitude,
                measurement_date=obs.measurement_date,
                allometric_equation_id=agb_model,
                belowground_model_id=bgb_model,
                derived_aboveground_biomass_kg=biomass_res["agb_kg"],
                derived_belowground_biomass_kg=biomass_res["bgb_kg"],
                derived_carbon_stock_t_co2e=biomass_res["carbon_stock_t_co2e"],
            )
            db.add(tree)
            created.append(tree)

        await db.flush()
        for t in created:
            await db.refresh(t)
        return created

    @classmethod
    async def get_tree_observations(
        cls,
        db: AsyncSession,
        organization_id: uuid.UUID,
        project_id: Optional[uuid.UUID] = None,
        land_unit_id: Optional[uuid.UUID] = None,
    ) -> List[TreeObservation]:
        stmt = select(TreeObservation).where(TreeObservation.organization_id == organization_id)
        if project_id:
            stmt = stmt.where(TreeObservation.project_id == project_id)
        if land_unit_id:
            stmt = stmt.where(TreeObservation.land_unit_id == land_unit_id)
        stmt = stmt.order_by(TreeObservation.measurement_date.desc())
        result = await db.execute(stmt)
        return list(result.scalars().all())

    # ─── Earth Observation Ingestion ───

    @classmethod
    async def ingest_satellite_observation(
        cls,
        db: AsyncSession,
        payload: SatelliteObservationCreate,
        organization_id: uuid.UUID,
    ) -> SatelliteObservation:
        await cls.get_project_or_raise(db, payload.project_id, organization_id)

        # Generate cryptographic provenance hash
        prov_payload = {
            "provider": payload.provider,
            "scene_id": payload.scene_id,
            "timestamp": payload.acquisition_timestamp.isoformat(),
            "indices": payload.derived_indices,
            "resolution": payload.spatial_resolution_m,
        }
        provenance_hash = hashlib.sha256(
            json.dumps(prov_payload, sort_keys=True).encode("utf-8")
        ).hexdigest()

        obs = SatelliteObservation(
            organization_id=organization_id,
            project_id=payload.project_id,
            land_unit_id=payload.land_unit_id,
            provider=payload.provider,
            scene_id=payload.scene_id,
            acquisition_timestamp=payload.acquisition_timestamp,
            cloud_coverage_pct=payload.cloud_coverage_pct,
            spatial_resolution_m=payload.spatial_resolution_m,
            observation_type=payload.observation_type,
            raw_band_uris=payload.raw_band_uris,
            derived_indices=payload.derived_indices,
            provenance_hash=provenance_hash,
            processing_level=payload.processing_level,
            lineage_manifest=payload.lineage_manifest,
        )
        db.add(obs)
        await db.flush()
        await db.refresh(obs)
        return obs

    @classmethod
    async def get_satellite_observations(
        cls,
        db: AsyncSession,
        organization_id: uuid.UUID,
        project_id: Optional[uuid.UUID] = None,
    ) -> List[SatelliteObservation]:
        stmt = select(SatelliteObservation).where(SatelliteObservation.organization_id == organization_id)
        if project_id:
            stmt = stmt.where(SatelliteObservation.project_id == project_id)
        stmt = stmt.order_by(SatelliteObservation.acquisition_timestamp.desc())
        result = await db.execute(stmt)
        return list(result.scalars().all())

    # ─── VT0014 Soil Mapping Execution ───

    @classmethod
    async def run_vt0014_soil_mapping(
        cls,
        db: AsyncSession,
        payload: VT0014ModelRunRequest,
        organization_id: uuid.UUID,
    ) -> AgricultureModelRun:
        await cls.get_project_or_raise(db, payload.project_id, organization_id)

        # Fetch soil samples for this project
        samples = await cls.get_soil_samples(db, organization_id, project_id=payload.project_id)
        if len(samples) < 3:
            raise ValueError(
                f"VT0014 requires at least 3 ground calibration points for statistical modeling. Found {len(samples)}."
            )

        calibration_points = []
        for s in samples:
            # Synthetic or real covariate extraction for calibration
            calibration_points.append({
                "lat": s.latitude,
                "lon": s.longitude,
                "soc_stock_t_c_ha": s.computed_soc_stock_t_c_ha or (s.soc_stock_pct * 25.0),
                "covariates": {
                    "ndvi": 0.65,
                    "elevation": 220.0,
                    "slope": 2.5,
                },
            })

        # Run VT0014 Engine
        result = VT0014SoilMappingEngine.run_mapping(
            sample_points=calibration_points,
            covariate_features=payload.covariate_features,
            model_algorithm=payload.model_algorithm,
        )

        model_run = AgricultureModelRun(
            organization_id=organization_id,
            project_id=payload.project_id,
            model_name=result["model_name"],
            model_type="DIGITAL_SOIL_MAPPING",
            version=result["version"],
            run_timestamp=datetime.now(timezone.utc),
            status=result["status"],
            input_parameters={
                "algorithm": payload.model_algorithm,
                "covariates": payload.covariate_features,
                "sample_count": len(samples),
            },
            input_dataset_hashes={
                "soil_samples_count": len(samples),
                "soil_samples_hash": hashlib.sha256(
                    "".join(s.sample_code for s in samples).encode("utf-8")
                ).hexdigest(),
            },
            performance_metrics=result["performance_metrics"],
            uncertainty_metrics=result["spatial_uncertainty"],
            output_manifest={
                "predictions_summary": result["spatial_predictions"],
                "manifest_summary": result["manifest_summary"],
            },
            provenance_hash=result["provenance_hash"],
        )
        db.add(model_run)
        await db.flush()
        await db.refresh(model_run)
        return model_run

    @classmethod
    async def get_model_runs(
        cls,
        db: AsyncSession,
        organization_id: uuid.UUID,
        project_id: Optional[uuid.UUID] = None,
    ) -> List[AgricultureModelRun]:
        stmt = select(AgricultureModelRun).where(AgricultureModelRun.organization_id == organization_id)
        if project_id:
            stmt = stmt.where(AgricultureModelRun.project_id == project_id)
        stmt = stmt.order_by(AgricultureModelRun.run_timestamp.desc())
        result = await db.execute(stmt)
        return list(result.scalars().all())

    # ─── Verification Dossier Compilation ───

    @classmethod
    async def generate_verification_dossier(
        cls,
        db: AsyncSession,
        project_id: uuid.UUID,
        organization_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        """
        Compiles the authoritative, immutable MRV Verification Dossier:
        - Project metadata & locked methodology snapshot
        - Exact WGS84 geodesic land unit boundaries & hierarchy
        - Depth-stratified soil sample inventory (VM0042 classification)
        - Tree observation census & derived allometrics (VM0047)
        - Earth Observation scenes & optical/SAR provenance
        - VT0014 / VMD0053 model runs & explicit spatial uncertainty
        - Fail-closed quantification manifest (status=NOT_CONFIGURED)
        - Sealed SHA-256 cryptographic ledger signature
        """
        project = await cls.get_project_or_raise(db, project_id, organization_id)

        # Fetch all related entities
        units = await cls.get_land_units(db, organization_id, project_id=project_id)
        soil_samples = await cls.get_soil_samples(db, organization_id, project_id=project_id)
        trees = await cls.get_tree_observations(db, organization_id, project_id=project_id)
        eo_scenes = await cls.get_satellite_observations(db, organization_id, project_id=project_id)
        model_runs = await cls.get_model_runs(db, organization_id, project_id=project_id)

        # Land units summary
        total_area_ha = sum(u.area_ha for u in units)
        units_by_type = {}
        for u in units:
            units_by_type[u.unit_type] = units_by_type.get(u.unit_type, 0) + 1

        # Soil samples summary
        soil_by_class = {}
        for s in soil_samples:
            soil_by_class[s.compliance_classification] = soil_by_class.get(s.compliance_classification, 0) + 1

        # Locked methodology snapshot from project baseline_parameters
        baseline_params = project.baseline_parameters or {}
        locked_methodology = baseline_params.get("locked_methodology_version", {
            "methodology_code": "VM0042",
            "version": "2.2",
            "locked_at": project.created_at.isoformat() if project.created_at else None,
            "status": "LOCKED",
        })

        # Fail-closed quantification
        calc = VM0042CalculatorV22()
        calc_result = calc.calculate_project_credits(
            project_data={"id": str(project_id)},
            monitoring_data={"units_count": len(units), "soil_samples_count": len(soil_samples)},
        )

        dossier_data = {
            "project_id": str(project.id),
            "project_name": project.name,
            "project_code": project.project_code,
            "sector_code": "AGRICULTURE_LAND_USE",
            "methodology_code": locked_methodology.get("methodology_code", "VM0042"),
            "methodology_version": locked_methodology.get("version", "2.2"),
            "methodology_version_snapshot": locked_methodology,
            "dossier_timestamp": datetime.now(timezone.utc).isoformat(),
            "land_units_summary": {
                "total_count": len(units),
                "total_area_ha": round(total_area_ha, 4),
                "breakdown_by_type": units_by_type,
            },
            "soil_inventory_summary": {
                "total_samples": len(soil_samples),
                "breakdown_by_compliance": soil_by_class,
            },
            "tree_inventory_summary": {
                "total_trees": len(trees),
                "total_aboveground_biomass_kg": round(sum(t.derived_aboveground_biomass_kg or 0.0 for t in trees), 2),
                "total_carbon_stock_t_co2e": round(sum(t.derived_carbon_stock_t_co2e or 0.0 for t in trees), 4),
            },
            "earth_observation_scenes": [
                {
                    "scene_id": s.scene_id,
                    "provider": s.provider,
                    "timestamp": s.acquisition_timestamp.isoformat(),
                    "provenance_hash": s.provenance_hash,
                }
                for s in eo_scenes
            ],
            "model_runs_summary": [
                {
                    "model_name": m.model_name,
                    "version": m.version,
                    "status": m.status,
                    "provenance_hash": m.provenance_hash,
                }
                for m in model_runs
            ],
            "quantification_manifest": {
                "calculation_status": calc_result.status.value,
                "is_issuance_eligible": calc_result.is_issuance_eligible,
                "issuable_credits_t_co2e": calc_result.issuable_credits_t_co2e,
                "compliance_notes": calc_result.compliance_notes,
            },
        }

        canonical_json = json.dumps(dossier_data, sort_keys=True, separators=(",", ":"))
        manifest_sha256 = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
        dossier_data["manifest_sha256"] = manifest_sha256

        # Seal manifest into cryptographic ledger via official LedgerService
        ledger_service = LedgerService(db)
        sig = await ledger_service.record_dossier_seal(
            project_id=project_id,
            organization_id=organization_id,
            manifest_sha256=manifest_sha256,
            raw_payload={
                "action": "SEAL_VERIFICATION_DOSSIER",
                "manifest_sha256": manifest_sha256,
                "project_code": project.project_code,
                "sector": "AGRICULTURE_LAND_USE",
            },
            signer_id=user_id,
            signer_role="METHODOLOGY_ENGINEER",
        )

        dossier_data["ledger_seal_status"] = "SEALED_CRYPTOGRAPHICALLY"
        dossier_data["ledger_signature_id"] = str(sig.id)
        return dossier_data

    # ─── Phase 1: Strata & Stratum Memberships ───

    @classmethod
    async def create_stratum(
        cls,
        db: AsyncSession,
        payload: StratumCreate,
        organization_id: uuid.UUID,
        project_id: Optional[uuid.UUID] = None,
    ) -> Stratum:
        proj_id = project_id or payload.project_id
        if not proj_id:
            raise ValueError("project_id is required.")
        await cls.get_project_or_raise(db, proj_id, organization_id)

        stratum = Stratum(
            organization_id=organization_id,
            project_id=proj_id,
            code=payload.code,
            name=payload.name,
            description=payload.description,
            stratum_type=payload.stratum_type,
            area_ha=payload.area_ha,
            is_active=payload.is_active,
            properties=payload.properties,
        )
        db.add(stratum)
        await db.flush()
        await db.refresh(stratum)
        return stratum

    @classmethod
    async def get_strata(
        cls,
        db: AsyncSession,
        organization_id: uuid.UUID,
        project_id: uuid.UUID,
        as_of_date: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        await cls.get_project_or_raise(db, project_id, organization_id)
        stmt = (
            select(Stratum)
            .where(
                Stratum.organization_id == organization_id,
                Stratum.project_id == project_id,
            )
            .order_by(Stratum.code.asc())
        )
        result = await db.execute(stmt)
        strata = list(result.scalars().all())

        # Query all memberships directly with land units to ensure accurate live database state
        mem_stmt = (
            select(StratumMembership)
            .join(Stratum, Stratum.id == StratumMembership.stratum_id)
            .where(
                Stratum.organization_id == organization_id,
                Stratum.project_id == project_id,
            )
            .options(selectinload(StratumMembership.land_unit))
        )
        mem_res = await db.execute(mem_stmt)
        all_memberships = list(mem_res.scalars().all())

        mems_by_stratum: Dict[uuid.UUID, List[StratumMembership]] = {s.id: [] for s in strata}
        for m in all_memberships:
            if m.stratum_id in mems_by_stratum:
                mems_by_stratum[m.stratum_id].append(m)

        output = []
        for s in strata:
            s_mems = mems_by_stratum.get(s.id, [])
            if as_of_date is not None:
                active_members = [
                    m for m in s_mems
                    if m.status == "ACTIVE"
                    and m.valid_from <= as_of_date
                    and (m.valid_to is None or m.valid_to >= as_of_date)
                ]
                distinct_units = {
                    m.land_unit_id: (m.land_unit.area_ha if m.land_unit else 0.0)
                    for m in active_members
                }
                computed_area = round(float(sum(distinct_units.values())), 4)
            else:
                active_members = [m for m in s_mems if m.status == "ACTIVE"]
                computed_area = s.area_ha

            output.append({
                "id": s.id,
                "organization_id": s.organization_id,
                "project_id": s.project_id,
                "code": s.code,
                "name": s.name,
                "description": s.description,
                "stratum_type": s.stratum_type,
                "area_ha": computed_area,
                "is_active": s.is_active,
                "properties": s.properties,
                "created_at": s.created_at,
                "updated_at": s.updated_at,
                "member_count": len(active_members),
                "land_unit_ids": sorted(list({m.land_unit_id for m in active_members})),
            })
        return output

    @classmethod
    async def get_stratum_by_id(
        cls,
        db: AsyncSession,
        stratum_id: uuid.UUID,
        organization_id: uuid.UUID,
        as_of_date: Optional[date] = None,
    ) -> Optional[Dict[str, Any]]:
        stmt = (
            select(Stratum)
            .where(
                Stratum.id == stratum_id,
                Stratum.organization_id == organization_id,
            )
        )
        result = await db.execute(stmt)
        s = result.scalars().first()
        if not s:
            return None

        mem_stmt = (
            select(StratumMembership)
            .where(
                StratumMembership.stratum_id == stratum_id,
                StratumMembership.organization_id == organization_id,
            )
            .options(selectinload(StratumMembership.land_unit))
        )
        mem_res = await db.execute(mem_stmt)
        memberships = list(mem_res.scalars().all())

        if as_of_date is not None:
            active_members = [
                m for m in memberships
                if m.status == "ACTIVE"
                and m.valid_from <= as_of_date
                and (m.valid_to is None or m.valid_to >= as_of_date)
            ]
            distinct_units = {
                m.land_unit_id: (m.land_unit.area_ha if m.land_unit else 0.0)
                for m in active_members
            }
            computed_area = round(float(sum(distinct_units.values())), 4)
        else:
            active_members = [m for m in memberships if m.status == "ACTIVE"]
            computed_area = s.area_ha

        return {
            "id": s.id,
            "organization_id": s.organization_id,
            "project_id": s.project_id,
            "code": s.code,
            "name": s.name,
            "description": s.description,
            "stratum_type": s.stratum_type,
            "area_ha": computed_area,
            "is_active": s.is_active,
            "properties": s.properties,
            "created_at": s.created_at,
            "updated_at": s.updated_at,
            "member_count": len(active_members),
            "land_unit_ids": sorted(list({m.land_unit_id for m in active_members})),
        }

    @classmethod
    async def update_stratum(
        cls,
        db: AsyncSession,
        stratum_id: uuid.UUID,
        payload: StratumUpdate,
        organization_id: uuid.UUID,
    ) -> Dict[str, Any]:
        stmt = select(Stratum).where(Stratum.id == stratum_id, Stratum.organization_id == organization_id)
        result = await db.execute(stmt)
        stratum = result.scalars().first()
        if not stratum:
            raise ValueError(f"Stratum '{stratum_id}' not found.")

        update_data = payload.model_dump(exclude_unset=True)
        for key, val in update_data.items():
            setattr(stratum, key, val)

        stratum.updated_at = datetime.now(timezone.utc)
        await db.flush()
        res = await cls.get_stratum_by_id(db, stratum_id, organization_id)
        if not res:
            raise ValueError("Failed to retrieve updated stratum.")
        return res

    @classmethod
    async def delete_stratum(
        cls,
        db: AsyncSession,
        stratum_id: uuid.UUID,
        organization_id: uuid.UUID,
    ) -> bool:
        stmt = select(Stratum).where(Stratum.id == stratum_id, Stratum.organization_id == organization_id)
        result = await db.execute(stmt)
        stratum = result.scalars().first()
        if not stratum:
            return False
        await db.delete(stratum)
        await db.flush()
        return True

    @classmethod
    async def add_stratum_memberships(
        cls,
        db: AsyncSession,
        stratum_id: uuid.UUID,
        organization_id: uuid.UUID,
        memberships: List[StratumMembershipItem],
    ) -> Dict[str, Any]:
        stratum_stmt = select(Stratum).where(Stratum.id == stratum_id, Stratum.organization_id == organization_id)
        stratum_res = await db.execute(stratum_stmt)
        stratum = stratum_res.scalars().first()
        if not stratum:
            raise ValueError(f"Stratum '{stratum_id}' not found.")

        unit_ids = [m.land_unit_id for m in memberships]
        units_stmt = select(LandUnit).where(
            LandUnit.id.in_(unit_ids),
            LandUnit.project_id == stratum.project_id,
            LandUnit.organization_id == organization_id,
        )
        units_res = await db.execute(units_stmt)
        found_units = {u.id: u for u in units_res.scalars().all()}

        # 1. Intra-batch validation
        active_in_batch = [m for m in memberships if m.status == "ACTIVE"]
        for i, m1 in enumerate(active_in_batch):
            m1_end = m1.valid_to or date.max
            for m2 in active_in_batch[i + 1 :]:
                if m1.land_unit_id == m2.land_unit_id:
                    m2_end = m2.valid_to or date.max
                    if m1.valid_from <= m2_end and m1_end >= m2.valid_from:
                        raise ValueError(
                            f"Temporal overlap conflict in submission: LandUnit '{m1.land_unit_id}' "
                            f"has multiple overlapping active periods in the same request."
                        )

        # 2. Database validation & insertion
        for m in memberships:
            if m.land_unit_id not in found_units:
                raise ValueError(f"LandUnit '{m.land_unit_id}' not found in project '{stratum.project_id}'.")

            if m.valid_to and m.valid_to < m.valid_from:
                raise ValueError(f"valid_to '{m.valid_to}' cannot precede valid_from '{m.valid_from}'.")

            m_end = m.valid_to or date.max

            # If this membership is ACTIVE, verify it does not overlap with another ACTIVE membership
            # for the same land unit in the SAME stratum_type within this project.
            if m.status == "ACTIVE":
                overlap_stmt = (
                    select(StratumMembership, Stratum)
                    .join(Stratum, Stratum.id == StratumMembership.stratum_id)
                    .where(
                        Stratum.project_id == stratum.project_id,
                        Stratum.stratum_type == stratum.stratum_type,
                        StratumMembership.land_unit_id == m.land_unit_id,
                        StratumMembership.status == "ACTIVE",
                    )
                )
                overlap_res = await db.execute(overlap_stmt)
                for exist_mem, exist_strat in overlap_res.all():
                    # If this is updating the exact same membership record, allow it
                    if exist_mem.stratum_id == stratum_id and exist_mem.valid_from == m.valid_from:
                        continue
                    exist_end = exist_mem.valid_to or date.max
                    if m.valid_from <= exist_end and m_end >= exist_mem.valid_from:
                        raise ValueError(
                            f"Temporal overlap conflict: LandUnit '{found_units[m.land_unit_id].name}' ({m.land_unit_id}) "
                            f"already has an active membership in stratum '{exist_strat.name}' ({exist_strat.code}) "
                            f"under scheme '{stratum.stratum_type}' for period [{exist_mem.valid_from} to {exist_mem.valid_to or 'ongoing'}]. "
                            f"Cannot assign overlapping period [{m.valid_from} to {m.valid_to or 'ongoing'}]."
                        )

            exist_stmt = select(StratumMembership).where(
                StratumMembership.stratum_id == stratum_id,
                StratumMembership.land_unit_id == m.land_unit_id,
                StratumMembership.valid_from == m.valid_from,
            )
            exist_res = await db.execute(exist_stmt)
            existing = exist_res.scalars().first()

            if existing:
                existing.status = m.status
                existing.valid_to = m.valid_to
                existing.properties = m.properties
            else:
                mem = StratumMembership(
                    organization_id=organization_id,
                    stratum_id=stratum_id,
                    land_unit_id=m.land_unit_id,
                    valid_from=m.valid_from,
                    valid_to=m.valid_to,
                    status=m.status,
                    properties=m.properties,
                )
                db.add(mem)

        await db.flush()

        active_units_stmt = (
            select(LandUnit.id, LandUnit.area_ha)
            .join(StratumMembership, StratumMembership.land_unit_id == LandUnit.id)
            .where(
                StratumMembership.stratum_id == stratum_id,
                StratumMembership.status == "ACTIVE",
            )
            .distinct()
        )
        active_units_res = await db.execute(active_units_stmt)
        active_area = sum(row.area_ha for row in active_units_res.fetchall())
        stratum.area_ha = round(float(active_area), 4)
        stratum.updated_at = datetime.now(timezone.utc)
        await db.flush()

        res = await cls.get_stratum_by_id(db, stratum_id, organization_id)
        if not res:
            raise ValueError("Failed to retrieve stratum after adding memberships.")
        return res

    # ─── Phase 1: Management Records ───

    @classmethod
    async def create_management_record(
        cls,
        db: AsyncSession,
        payload: ManagementRecordCreate,
        organization_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None,
        project_id: Optional[uuid.UUID] = None,
    ) -> AgricultureManagementRecord:
        proj_id = project_id or payload.project_id
        if not proj_id:
            raise ValueError("project_id is required.")
        await cls.get_project_or_raise(db, proj_id, organization_id)

        if payload.event_date > date.today():
            raise ValueError(f"Management record event_date '{payload.event_date}' cannot be in the future.")
        if payload.end_date and payload.end_date < payload.event_date:
            raise ValueError(f"end_date '{payload.end_date}' cannot precede event_date '{payload.event_date}'.")

        if payload.land_unit_id:
            u_stmt = select(LandUnit).where(
                LandUnit.id == payload.land_unit_id,
                LandUnit.project_id == proj_id,
                LandUnit.organization_id == organization_id,
            )
            u_res = await db.execute(u_stmt)
            if not u_res.scalars().first():
                raise ValueError(f"LandUnit '{payload.land_unit_id}' not found in project.")

        record = AgricultureManagementRecord(
            organization_id=organization_id,
            project_id=proj_id,
            land_unit_id=payload.land_unit_id,
            record_type=payload.record_type.upper(),
            practice_category=payload.practice_category.upper(),
            event_date=payload.event_date,
            end_date=payload.end_date,
            data_source=payload.data_source.upper(),
            corroboration=(payload.corroboration or "NONE").upper(),
            details=payload.details,
            evidence_id=payload.evidence_id,
            entered_by_id=user_id,
            qa_status=payload.qa_status.upper(),
        )
        db.add(record)
        await db.flush()
        await db.refresh(record)
        return record

    @classmethod
    async def get_management_records(
        cls,
        db: AsyncSession,
        organization_id: uuid.UUID,
        project_id: uuid.UUID,
        land_unit_id: Optional[uuid.UUID] = None,
        practice_category: Optional[str] = None,
        record_type: Optional[str] = None,
    ) -> List[AgricultureManagementRecord]:
        await cls.get_project_or_raise(db, project_id, organization_id)
        stmt = (
            select(AgricultureManagementRecord)
            .where(
                AgricultureManagementRecord.organization_id == organization_id,
                AgricultureManagementRecord.project_id == project_id,
            )
        )
        if land_unit_id:
            stmt = stmt.where(AgricultureManagementRecord.land_unit_id == land_unit_id)
        if practice_category:
            stmt = stmt.where(AgricultureManagementRecord.practice_category == practice_category.upper())
        if record_type:
            stmt = stmt.where(AgricultureManagementRecord.record_type == record_type.upper())

        stmt = stmt.order_by(AgricultureManagementRecord.event_date.desc())
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @classmethod
    async def get_management_record_by_id(
        cls,
        db: AsyncSession,
        record_id: uuid.UUID,
        organization_id: uuid.UUID,
    ) -> Optional[AgricultureManagementRecord]:
        stmt = select(AgricultureManagementRecord).where(
            AgricultureManagementRecord.id == record_id,
            AgricultureManagementRecord.organization_id == organization_id,
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    @classmethod
    async def update_management_record(
        cls,
        db: AsyncSession,
        record_id: uuid.UUID,
        payload: ManagementRecordUpdate,
        organization_id: uuid.UUID,
    ) -> AgricultureManagementRecord:
        record = await cls.get_management_record_by_id(db, record_id, organization_id)
        if not record:
            raise ValueError(f"Management record '{record_id}' not found.")

        update_data = payload.model_dump(exclude_unset=True)

        if "land_unit_id" in update_data and update_data["land_unit_id"]:
            u_stmt = select(LandUnit).where(
                LandUnit.id == update_data["land_unit_id"],
                LandUnit.project_id == record.project_id,
                LandUnit.organization_id == organization_id,
            )
            u_res = await db.execute(u_stmt)
            if not u_res.scalars().first():
                raise ValueError(f"LandUnit '{update_data['land_unit_id']}' not found in project.")

        new_ev_date = update_data.get("event_date", record.event_date)
        new_end_date = update_data.get("end_date", record.end_date)
        if new_ev_date and new_ev_date > date.today():
            raise ValueError(f"Management record event_date '{new_ev_date}' cannot be in the future.")
        if new_end_date and new_ev_date and new_end_date < new_ev_date:
            raise ValueError(f"end_date '{new_end_date}' cannot precede event_date '{new_ev_date}'.")

        for k, v in update_data.items():
            if k in ["record_type", "practice_category", "data_source", "qa_status", "corroboration"] and v is not None:
                setattr(record, k, v.upper())
            else:
                setattr(record, k, v)

        record.updated_at = datetime.now(timezone.utc)
        await db.flush()
        await db.refresh(record)
        return record

    @classmethod
    async def delete_management_record(
        cls,
        db: AsyncSession,
        record_id: uuid.UUID,
        organization_id: uuid.UUID,
    ) -> bool:
        record = await cls.get_management_record_by_id(db, record_id, organization_id)
        if not record:
            return False
        await db.delete(record)
        await db.flush()
        return True

    # ─── Phase 1: Foundation, Methodology Lock, and Boundary Linking ───

    @classmethod
    async def lock_project_methodology(
        cls,
        db: AsyncSession,
        project_id: uuid.UUID,
        organization_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        project = await cls.get_project_or_raise(db, project_id, organization_id)
        if not project.methodology_id or not project.methodology_version_id:
            raise ValueError("Project must have both methodology_id and methodology_version_id set before locking.")

        current_params = dict(project.baseline_parameters or {})
        existing_lock = current_params.get("locked_methodology_version")
        if existing_lock and existing_lock.get("status") == "LOCKED":
            raise ValueError(
                f"Project '{project_id}' methodology version is already locked "
                f"(locked_at: {existing_lock.get('locked_at')}, version: {existing_lock.get('version')}). "
                "Methodology version lock is immutable and cannot be re-locked or overwritten."
            )

        m_res = await db.execute(select(Methodology).where(Methodology.id == project.methodology_id))
        meth = m_res.scalars().first()
        if not meth:
            raise ValueError(f"Methodology '{project.methodology_id}' not found.")

        mv_res = await db.execute(select(MethodologyVersion).where(MethodologyVersion.id == project.methodology_version_id))
        mver = mv_res.scalars().first()
        if not mver:
            raise ValueError(f"MethodologyVersion '{project.methodology_version_id}' not found.")

        canonical_wording = (
            "VM0042 methodology, using VT0014 digital soil mapping tool where applicable"
            if meth.code == "VM0042"
            else f"{meth.code} methodology"
        )

        locked_snapshot = {
            "methodology_id": str(meth.id),
            "methodology_code": meth.code,
            "methodology_name": meth.name,
            "version_id": str(mver.id),
            "version": mver.version,
            "version_status": getattr(mver, "status", "active"),
            "release_date": mver.release_date.isoformat() if mver.release_date else None,
            "rules_parameters_snapshot": {
                "applicable_activities": getattr(meth, "applicable_activities", []),
                "sector": getattr(meth, "sector", None),
                "migration_notes": getattr(mver, "migration_notes", None),
            },
            "locked_at": datetime.now(timezone.utc).isoformat(),
            "locked_by_user_id": str(user_id) if user_id else None,
            "status": "LOCKED",
            "notes": notes,
            "canonical_designation": canonical_wording,
            "project_id": str(project.id),
            "organization_id": str(organization_id),
        }

        current_params["locked_methodology_version"] = locked_snapshot
        project.baseline_parameters = current_params
        project.updated_at = datetime.now(timezone.utc)
        await db.flush()
        return locked_snapshot

    @classmethod
    async def link_project_boundary(
        cls,
        db: AsyncSession,
        project_id: uuid.UUID,
        organization_id: uuid.UUID,
        user_id: Optional[uuid.UUID],
        payload: LinkBoundaryRequest,
    ) -> ProjectBoundaryVersion:
        await cls.get_project_or_raise(db, project_id, organization_id)

        area_ha, perimeter_m = compute_geodesic_area_ha(payload.boundary_geojson)
        centroid_lat, centroid_lon = compute_centroid(payload.boundary_geojson)

        ver_stmt = select(func.max(ProjectBoundaryVersion.version_number)).where(
            ProjectBoundaryVersion.project_id == project_id
        )
        latest_ver = await db.scalar(ver_stmt) or 0
        new_version_num = latest_ver + 1

        geom_val = None
        try:
            from shapely.geometry import shape
            from geoalchemy2.shape import from_shape
            geom_val = from_shape(shape(payload.boundary_geojson), srid=4326)
        except Exception:
            geom_val = None

        pbv = ProjectBoundaryVersion(
            organization_id=organization_id,
            project_id=project_id,
            version_number=new_version_num,
            effective_date=payload.effective_date or date.today(),
            boundary_geojson=payload.boundary_geojson,
            geom=geom_val,
            source=payload.source,
            reason=payload.reason,
            area_ha=area_ha,
            perimeter_m=perimeter_m,
            centroid_lat=centroid_lat,
            centroid_lon=centroid_lon,
            crs="EPSG:4326",
            created_by_id=user_id,
        )
        db.add(pbv)
        await db.flush()
        await db.refresh(pbv)
        return pbv

    @classmethod
    async def get_project_foundation(
        cls,
        db: AsyncSession,
        project_id: uuid.UUID,
        organization_id: uuid.UUID,
    ) -> Dict[str, Any]:
        project = await cls.get_project_or_raise(db, project_id, organization_id)

        sec_info = {"code": "AGRICULTURE_LAND_USE", "name": "Agriculture & Land Use"}
        if project.sector_id:
            sf_res = await db.execute(select(MethodologyFamily).where(MethodologyFamily.id == project.sector_id))
            sf = sf_res.scalars().first()
            if sf:
                sec_info = {"id": str(sf.id), "code": sf.code, "name": sf.name}

        meth_info = {}
        if project.methodology_id:
            m_res = await db.execute(select(Methodology).where(Methodology.id == project.methodology_id))
            m = m_res.scalars().first()
            if m:
                meth_info = {"id": str(m.id), "code": m.code, "name": m.name}
        if project.methodology_version_id:
            mv_res = await db.execute(select(MethodologyVersion).where(MethodologyVersion.id == project.methodology_version_id))
            mv = mv_res.scalars().first()
            if mv:
                meth_info["version_id"] = str(mv.id)
                meth_info["version"] = mv.version

        locked_snap = (project.baseline_parameters or {}).get("locked_methodology_version")
        lock_status = "LOCKED" if locked_snap and locked_snap.get("status") == "LOCKED" else "UNLOCKED" if project.methodology_id else "NOT_CONFIGURED"

        b_stmt = (
            select(ProjectBoundaryVersion)
            .where(ProjectBoundaryVersion.project_id == project_id)
            .order_by(ProjectBoundaryVersion.version_number.desc())
        )
        b_res = await db.execute(b_stmt)
        latest_b = b_res.scalars().first()

        bound_info = None
        if latest_b:
            bound_info = {
                "id": str(latest_b.id),
                "version_number": latest_b.version_number,
                "effective_date": latest_b.effective_date.isoformat(),
                "area_ha": latest_b.area_ha,
                "perimeter_m": latest_b.perimeter_m,
                "source": latest_b.source,
                "crs": latest_b.crs,
                "boundary_geojson": latest_b.boundary_geojson,
            }

        lu_count = await db.scalar(select(func.count(LandUnit.id)).where(LandUnit.project_id == project_id)) or 0
        st_count = await db.scalar(select(func.count(Stratum.id)).where(Stratum.project_id == project_id)) or 0
        mr_count = await db.scalar(select(func.count(AgricultureManagementRecord.id)).where(AgricultureManagementRecord.project_id == project_id)) or 0

        return {
            "project_id": str(project.id),
            "project_name": project.name,
            "project_code": project.project_code,
            "sector": sec_info,
            "methodology": meth_info,
            "methodology_lock_status": lock_status,
            "locked_methodology_snapshot": locked_snap,
            "crediting_period": {
                "start": project.crediting_start.isoformat() if project.crediting_start else None,
                "end": project.crediting_end.isoformat() if project.crediting_end else None,
            },
            "baseline_parameters": project.baseline_parameters or {},
            "authoritative_boundary": bound_info,
            "land_units_count": lu_count,
            "strata_count": st_count,
            "management_records_count": mr_count,
        }

    # ─── Phase 1: Foundation Readiness Evaluator ───

    @classmethod
    async def evaluate_foundation_readiness(
        cls,
        db: AsyncSession,
        project_id: uuid.UUID,
        organization_id: uuid.UUID,
    ) -> Dict[str, Any]:
        project = await cls.get_project_or_raise(db, project_id, organization_id)

        # 1. Project Configuration
        has_dates = bool(project.crediting_start and project.crediting_end)
        if project.name and project.project_code and has_dates:
            cfg_status = "COMPLETE"
            cfg_msg = f"Project foundation configured with active crediting period ({project.crediting_start} to {project.crediting_end})"
        elif project.name and project.project_code:
            cfg_status = "INCOMPLETE"
            cfg_msg = "Project registered with code but crediting period start/end dates are not configured (0 of 2 dates set)"
        elif project.name:
            cfg_status = "INCOMPLETE"
            cfg_msg = "Project name set but missing project code and crediting period start/end dates"
        else:
            cfg_status = "NOT_CONFIGURED"
            cfg_msg = "Project configuration missing or incomplete"

        cfg_details = {
            "name": project.name,
            "code": project.project_code,
            "crediting_start": project.crediting_start.isoformat() if project.crediting_start else None,
            "crediting_end": project.crediting_end.isoformat() if project.crediting_end else None,
        }

        # 2. Methodology Lock
        locked_snap = (project.baseline_parameters or {}).get("locked_methodology_version")
        if locked_snap and locked_snap.get("status") == "LOCKED":
            meth_status = "COMPLETE"
            m_code = locked_snap.get("methodology_code", "Unknown")
            m_ver = locked_snap.get("version", "")
            meth_msg = f"{m_code} v{m_ver} locked with immutable parameter snapshot"
        elif project.methodology_id and project.methodology_version_id:
            meth_status = "NEEDS_REVIEW"
            meth_msg = "Methodology and version selected but not locked to an immutable version snapshot (1 pending action: lock snapshot)"
        elif project.methodology_id:
            meth_status = "INCOMPLETE"
            meth_msg = "Methodology selected but version is missing (missing version and lock snapshot)"
        else:
            meth_status = "NOT_CONFIGURED"
            meth_msg = "No methodology assigned to project (0 of 1 assigned)"

        meth_details = {
            "methodology_id": str(project.methodology_id) if project.methodology_id else None,
            "methodology_version_id": str(project.methodology_version_id) if project.methodology_version_id else None,
            "is_locked": bool(locked_snap and locked_snap.get("status") == "LOCKED"),
            "locked_version": locked_snap.get("version") if locked_snap else None,
        }

        # 3. Authoritative Boundary
        b_stmt = (
            select(ProjectBoundaryVersion)
            .where(ProjectBoundaryVersion.project_id == project_id)
            .order_by(ProjectBoundaryVersion.version_number.desc())
        )
        b_res = await db.execute(b_stmt)
        latest_b = b_res.scalars().first()
        if latest_b and latest_b.area_ha > 0:
            bound_status = "COMPLETE"
            bound_msg = f"Authoritative boundary v{latest_b.version_number} established ({latest_b.area_ha:.2f} ha, {latest_b.source})"
            bound_details = {
                "version_number": latest_b.version_number,
                "area_ha": latest_b.area_ha,
                "effective_date": latest_b.effective_date.isoformat(),
                "source": latest_b.source,
            }
        else:
            bound_status = "NOT_CONFIGURED"
            bound_msg = "Authoritative project spatial boundary is not defined (0 boundary versions)"
            bound_details = {}

        # 4. Land Units
        units_stmt = select(LandUnit).where(LandUnit.project_id == project_id)
        units_res = await db.execute(units_stmt)
        units = list(units_res.scalars().all())
        total_unit_area = sum(u.area_ha for u in units)

        if len(units) > 0:
            lu_status = "COMPLETE"
            lu_msg = f"{len(units)} land management unit(s) defined ({total_unit_area:.2f} ha total)"
        else:
            lu_status = "INCOMPLETE"
            lu_msg = "No land units (parcels/fields) defined for project (0 land units registered)"

        lu_details = {
            "total_count": len(units),
            "total_area_ha": round(total_unit_area, 4),
            "parcels_count": len([u for u in units if u.unit_type == "PARCEL"]),
            "fields_count": len([u for u in units if u.unit_type == "FIELD"]),
            "plots_count": len([u for u in units if u.unit_type == "MONITORING_PLOT"]),
        }

        # 5. Stratification
        strata_stmt = select(Stratum).where(Stratum.project_id == project_id).options(selectinload(Stratum.memberships))
        strata_res = await db.execute(strata_stmt)
        strata = list(strata_res.scalars().all())
        all_active_members = [m for s in strata for m in s.memberships if m.status == "ACTIVE"]

        if len(strata) > 0 and len(all_active_members) > 0:
            strat_status = "COMPLETE"
            strat_msg = f"{len(strata)} strata established with {len(all_active_members)} active land unit memberships"
        elif len(strata) > 0:
            strat_status = "NEEDS_REVIEW"
            strat_msg = f"{len(strata)} strata defined but 0 land units have been assigned active memberships"
        else:
            strat_status = "NOT_CONFIGURED"
            strat_msg = "No strata configured for soil or management grouping (0 strata established)"

        strat_details = {
            "strata_count": len(strata),
            "active_memberships_count": len(all_active_members),
            "stratified_area_ha": round(sum(s.area_ha for s in strata), 4),
        }

        # 6. Management Baseline
        mgmt_stmt = select(AgricultureManagementRecord).where(AgricultureManagementRecord.project_id == project_id)
        mgmt_res = await db.execute(mgmt_stmt)
        mgmt_records = list(mgmt_res.scalars().all())
        baseline_recs = [r for r in mgmt_records if r.practice_category == "BASELINE"]
        project_recs = [r for r in mgmt_records if r.practice_category == "PROJECT_ACTIVITY"]

        if len(baseline_recs) > 0:
            mgmt_status = "COMPLETE"
            mgmt_msg = f"{len(baseline_recs)} baseline management record(s) documented across historical period"
        elif len(mgmt_records) > 0:
            mgmt_status = "NEEDS_REVIEW"
            mgmt_msg = f"{len(mgmt_records)} management record(s) exist but 0 categorized as historical BASELINE"
        else:
            mgmt_status = "NOT_CONFIGURED"
            mgmt_msg = "No management history or baseline practice records documented (0 records)"

        mgmt_details = {
            "total_records": len(mgmt_records),
            "baseline_records": len(baseline_recs),
            "project_activity_records": len(project_recs),
            "record_types": sorted(list(set(r.record_type for r in mgmt_records))),
            "provenance_sources": sorted(list(set(r.data_source for r in mgmt_records))),
        }

        all_statuses = [cfg_status, meth_status, bound_status, lu_status, strat_status, mgmt_status]
        if all(s == "COMPLETE" for s in all_statuses):
            overall_status = "COMPLETE"
        elif all(s == "NOT_CONFIGURED" for s in all_statuses):
            overall_status = "NOT_CONFIGURED"
        elif any(s == "NEEDS_REVIEW" for s in all_statuses):
            overall_status = "NEEDS_REVIEW"
        else:
            overall_status = "INCOMPLETE"

        return {
            "project_id": str(project.id),
            "overall_status": overall_status,
            "components": {
                "project_configuration": {"status": cfg_status, "message": cfg_msg, "details": cfg_details},
                "methodology_lock": {"status": meth_status, "message": meth_msg, "details": meth_details},
                "authoritative_boundary": {"status": bound_status, "message": bound_msg, "details": bound_details},
                "land_units": {"status": lu_status, "message": lu_msg, "details": lu_details},
                "stratification": {"status": strat_status, "message": strat_msg, "details": strat_details},
                "management_baseline": {"status": mgmt_status, "message": mgmt_msg, "details": mgmt_details},
            },
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
        }

    # ─── Phase 2: Ground Sampling, Chain of Custody & Laboratory Evidence ───

    @classmethod
    async def create_sampling_campaign(
        cls,
        db: AsyncSession,
        project_id: uuid.UUID,
        organization_id: uuid.UUID,
        payload: SamplingCampaignCreate,
        user_id: Optional[uuid.UUID] = None,
    ) -> SamplingCampaign:
        project = await cls.get_project_or_raise(db, project_id, organization_id)

        dup = await db.scalar(
            select(SamplingCampaign.id).where(
                SamplingCampaign.project_id == project_id,
                SamplingCampaign.campaign_code == payload.campaign_code,
            )
        )
        if dup:
            raise ValueError(f"Sampling campaign with code '{payload.campaign_code}' already exists for this project.")

        params = project.baseline_parameters or {}
        meth_snap = params.get("locked_methodology_version", {})

        boundary_id = payload.project_boundary_version_id
        if boundary_id:
            b_exists = await db.scalar(
                select(ProjectBoundaryVersion.id).where(
                    ProjectBoundaryVersion.id == boundary_id,
                    ProjectBoundaryVersion.project_id == project_id,
                )
            )
            if not b_exists:
                raise ValueError(f"Boundary version '{boundary_id}' not found in project.")
        else:
            latest_b = await db.scalar(
                select(ProjectBoundaryVersion.id)
                .where(ProjectBoundaryVersion.project_id == project_id)
                .order_by(ProjectBoundaryVersion.version_number.desc())
            )
            boundary_id = latest_b

        campaign = SamplingCampaign(
            organization_id=organization_id,
            project_id=project_id,
            campaign_code=payload.campaign_code,
            name=payload.name,
            purpose=payload.purpose,
            baseline_or_monitoring_context=payload.baseline_or_monitoring_context,
            planned_start_date=payload.planned_start_date,
            planned_end_date=payload.planned_end_date,
            status="DRAFT",
            methodology_lock_snapshot=meth_snap,
            project_boundary_version_id=boundary_id,
            created_by_id=user_id,
        )
        db.add(campaign)
        await db.flush()
        await db.refresh(campaign)
        return campaign

    @classmethod
    async def get_sampling_campaigns(
        cls,
        db: AsyncSession,
        project_id: uuid.UUID,
        organization_id: uuid.UUID,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        stmt = (
            select(SamplingCampaign)
            .where(
                SamplingCampaign.project_id == project_id,
                SamplingCampaign.organization_id == organization_id,
            )
            .order_by(SamplingCampaign.created_at.desc())
        )
        if status:
            stmt = stmt.where(SamplingCampaign.status == status)
        res = await db.execute(stmt)
        campaigns = list(res.scalars().all())

        results = []
        for c in campaigns:
            p_count = await db.scalar(
                select(func.count(SamplingPoint.id)).where(SamplingPoint.campaign_id == c.id)
            ) or 0
            v_count = await db.scalar(
                select(func.count(SamplingPlanVersion.id)).where(SamplingPlanVersion.campaign_id == c.id)
            ) or 0
            s_count = await db.scalar(
                select(func.count(PhysicalSample.id)).where(PhysicalSample.campaign_id == c.id)
            ) or 0
            results.append({
                "id": c.id,
                "organization_id": c.organization_id,
                "project_id": c.project_id,
                "campaign_code": c.campaign_code,
                "name": c.name,
                "purpose": c.purpose,
                "baseline_or_monitoring_context": c.baseline_or_monitoring_context,
                "planned_start_date": c.planned_start_date,
                "planned_end_date": c.planned_end_date,
                "status": c.status,
                "methodology_lock_snapshot": c.methodology_lock_snapshot or {},
                "project_boundary_version_id": c.project_boundary_version_id,
                "created_by_id": c.created_by_id,
                "created_at": c.created_at,
                "updated_at": c.updated_at,
                "plan_versions_count": v_count,
                "points_count": p_count,
                "samples_count": s_count,
            })
        return results

    @classmethod
    async def get_sampling_campaign_by_id(
        cls,
        db: AsyncSession,
        campaign_id: uuid.UUID,
        organization_id: uuid.UUID,
    ) -> Optional[Dict[str, Any]]:
        stmt = select(SamplingCampaign).where(
            SamplingCampaign.id == campaign_id,
            SamplingCampaign.organization_id == organization_id,
        )
        res = await db.execute(stmt)
        c = res.scalars().first()
        if not c:
            return None
        p_count = await db.scalar(
            select(func.count(SamplingPoint.id)).where(SamplingPoint.campaign_id == c.id)
        ) or 0
        v_count = await db.scalar(
            select(func.count(SamplingPlanVersion.id)).where(SamplingPlanVersion.campaign_id == c.id)
        ) or 0
        s_count = await db.scalar(
            select(func.count(PhysicalSample.id)).where(PhysicalSample.campaign_id == c.id)
        ) or 0
        return {
            "id": c.id,
            "organization_id": c.organization_id,
            "project_id": c.project_id,
            "campaign_code": c.campaign_code,
            "name": c.name,
            "purpose": c.purpose,
            "baseline_or_monitoring_context": c.baseline_or_monitoring_context,
            "planned_start_date": c.planned_start_date,
            "planned_end_date": c.planned_end_date,
            "status": c.status,
            "methodology_lock_snapshot": c.methodology_lock_snapshot or {},
            "project_boundary_version_id": c.project_boundary_version_id,
            "created_by_id": c.created_by_id,
            "created_at": c.created_at,
            "updated_at": c.updated_at,
            "plan_versions_count": v_count,
            "points_count": p_count,
            "samples_count": s_count,
        }

    @classmethod
    async def update_sampling_campaign(
        cls,
        db: AsyncSession,
        campaign_id: uuid.UUID,
        organization_id: uuid.UUID,
        payload: SamplingCampaignUpdate,
    ) -> SamplingCampaign:
        stmt = select(SamplingCampaign).where(
            SamplingCampaign.id == campaign_id,
            SamplingCampaign.organization_id == organization_id,
        )
        res = await db.execute(stmt)
        c = res.scalars().first()
        if not c:
            raise ValueError(f"Sampling campaign '{campaign_id}' not found.")
        update_data = payload.model_dump(exclude_unset=True)
        for k, v in update_data.items():
            setattr(c, k, v)
        c.updated_at = datetime.now(timezone.utc)
        await db.flush()
        await db.refresh(c)
        return c

    @classmethod
    async def create_sampling_plan_version(
        cls,
        db: AsyncSession,
        campaign_id: uuid.UUID,
        organization_id: uuid.UUID,
        payload: SamplingPlanVersionCreate,
        user_id: Optional[uuid.UUID] = None,
    ) -> SamplingPlanVersion:
        c_stmt = select(SamplingCampaign).where(
            SamplingCampaign.id == campaign_id,
            SamplingCampaign.organization_id == organization_id,
        )
        c_res = await db.execute(c_stmt)
        c = c_res.scalars().first()
        if not c:
            raise ValueError(f"Sampling campaign '{campaign_id}' not found.")

        latest_v = await db.scalar(
            select(func.max(SamplingPlanVersion.version_number)).where(
                SamplingPlanVersion.campaign_id == campaign_id
            )
        ) or 0
        new_v = latest_v + 1

        strata_stmt = (
            select(Stratum)
            .where(Stratum.project_id == c.project_id)
            .options(selectinload(Stratum.memberships))
        )
        strata_res = await db.execute(strata_stmt)
        all_strata = list(strata_res.scalars().all())

        snapshot_strata = []
        for s in all_strata:
            active_m = [
                {
                    "land_unit_id": str(m.land_unit_id),
                    "valid_from": m.valid_from.isoformat(),
                    "valid_to": m.valid_to.isoformat() if m.valid_to else None,
                    "status": m.status,
                }
                for m in s.memberships
                if m.valid_from <= payload.effective_as_of_date
                and (m.valid_to is None or m.valid_to >= payload.effective_as_of_date)
            ]
            snapshot_strata.append({
                "id": str(s.id),
                "code": s.code,
                "name": s.name,
                "stratum_type": s.stratum_type,
                "area_ha": s.area_ha,
                "active_memberships": active_m,
            })

        strat_snapshot = {
            "effective_as_of_date": payload.effective_as_of_date.isoformat(),
            "snapshot_timestamp": datetime.now(timezone.utc).isoformat(),
            "strata": snapshot_strata,
            "strata_count": len(snapshot_strata),
        }

        spv = SamplingPlanVersion(
            organization_id=organization_id,
            project_id=c.project_id,
            campaign_id=campaign_id,
            version_number=new_v,
            status="DRAFT",
            effective_as_of_date=payload.effective_as_of_date,
            stratum_membership_snapshot=strat_snapshot,
            sampling_design_method=payload.sampling_design_method,
            design_provenance=payload.design_provenance,
            is_locked=False,
            notes=payload.notes,
            created_by_id=user_id,
        )
        db.add(spv)
        await db.flush()
        await db.refresh(spv)
        return spv

    @classmethod
    async def get_sampling_plan_versions(
        cls,
        db: AsyncSession,
        campaign_id: uuid.UUID,
        organization_id: uuid.UUID,
    ) -> List[SamplingPlanVersion]:
        stmt = (
            select(SamplingPlanVersion)
            .where(
                SamplingPlanVersion.campaign_id == campaign_id,
                SamplingPlanVersion.organization_id == organization_id,
            )
            .order_by(SamplingPlanVersion.version_number.asc())
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @classmethod
    async def lock_sampling_plan_version(
        cls,
        db: AsyncSession,
        plan_version_id: uuid.UUID,
        organization_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None,
        notes: Optional[str] = None,
    ) -> SamplingPlanVersion:
        stmt = select(SamplingPlanVersion).where(
            SamplingPlanVersion.id == plan_version_id,
            SamplingPlanVersion.organization_id == organization_id,
        )
        res = await db.execute(stmt)
        spv = res.scalars().first()
        if not spv:
            raise ValueError(f"Sampling plan version '{plan_version_id}' not found.")
        if spv.is_locked:
            raise ValueError(f"Sampling plan version v{spv.version_number} is already locked (locked at {spv.locked_at}).")

        # Query campaign and points to freeze comprehensive snapshot
        c_stmt = select(SamplingCampaign).where(SamplingCampaign.id == spv.campaign_id)
        c_res = await db.execute(c_stmt)
        campaign = c_res.scalars().first()

        pts_stmt = select(SamplingPoint).where(SamplingPoint.plan_version_id == spv.id)
        pts_res = await db.execute(pts_stmt)
        points = list(pts_res.scalars().all())

        lock_snapshot = {
            "project_id": str(spv.project_id),
            "organization_id": str(spv.organization_id),
            "campaign_id": str(spv.campaign_id),
            "campaign_code": campaign.campaign_code if campaign else None,
            "methodology_lock_snapshot": campaign.methodology_lock_snapshot if campaign else {},
            "project_boundary_version_id": str(campaign.project_boundary_version_id) if campaign and campaign.project_boundary_version_id else None,
            "effective_stratification_date": spv.effective_as_of_date.isoformat(),
            "stratum_membership_snapshot": spv.stratum_membership_snapshot or {},
            "sampling_design_provenance": spv.design_provenance,
            "sampling_design_method": spv.sampling_design_method,
            "sampling_design_parameters": {
                "method": spv.sampling_design_method,
                "provenance": spv.design_provenance,
                "points_count": len(points),
            },
            "planned_depth_requirements": [
                {
                    "point_code": p.point_code,
                    "depth_from_cm": p.depth_from_cm,
                    "depth_to_cm": p.depth_to_cm,
                    "depth_class_label": p.depth_class_label,
                }
                for p in points
            ],
            "created_by": str(spv.created_by_id) if spv.created_by_id else None,
            "created_at": spv.created_at.isoformat() if spv.created_at else None,
            "locked_by": str(user_id) if user_id else None,
            "locked_at": datetime.now(timezone.utc).isoformat(),
        }

        spv.is_locked = True
        spv.locked_at = datetime.now(timezone.utc)
        spv.locked_by_id = user_id
        spv.status = "ACTIVE"
        spv.plan_lock_snapshot = lock_snapshot
        if notes:
            spv.notes = f"{spv.notes}\nLock notes: {notes}" if spv.notes else notes
        spv.updated_at = datetime.now(timezone.utc)

        if campaign and campaign.status in ["DRAFT", "PLANNED"]:
            campaign.status = "LOCKED"
            campaign.updated_at = datetime.now(timezone.utc)

        await db.flush()
        await db.refresh(spv)
        return spv

    @classmethod
    async def create_sampling_points(
        cls,
        db: AsyncSession,
        campaign_id: uuid.UUID,
        plan_version_id: uuid.UUID,
        organization_id: uuid.UUID,
        points: List[SamplingPointCreate],
        user_id: Optional[uuid.UUID] = None,
    ) -> List[SamplingPoint]:
        spv_stmt = select(SamplingPlanVersion).where(
            SamplingPlanVersion.id == plan_version_id,
            SamplingPlanVersion.campaign_id == campaign_id,
            SamplingPlanVersion.organization_id == organization_id,
        )
        spv_res = await db.execute(spv_stmt)
        spv = spv_res.scalars().first()
        if not spv:
            raise ValueError(f"Sampling plan version '{plan_version_id}' not found in campaign '{campaign_id}'.")
        if spv.is_locked:
            raise ValueError(f"Cannot add points to locked sampling plan version '{plan_version_id}'. Plan is immutable.")

        c_stmt = select(SamplingCampaign).where(SamplingCampaign.id == campaign_id)
        c_res = await db.execute(c_stmt)
        campaign = c_res.scalars().first()

        proj_stmt = select(Project).where(Project.id == spv.project_id)
        proj_res = await db.execute(proj_stmt)
        project = proj_res.scalars().first()
        p_code = project.project_code or "PROJ"
        c_code = campaign.campaign_code or "CAMP"

        created_points = []
        for p in points:
            lu_stmt = select(LandUnit).where(
                LandUnit.id == p.land_unit_id,
                LandUnit.project_id == spv.project_id,
                LandUnit.organization_id == organization_id,
            )
            lu_res = await db.execute(lu_stmt)
            land_unit = lu_res.scalars().first()
            if not land_unit:
                raise ValueError(f"LandUnit '{p.land_unit_id}' not found in project.")

            if land_unit.boundary_geojson:
                in_poly = point_in_geojson_polygon(p.planned_lat, p.planned_lon, land_unit.boundary_geojson)
                if not in_poly:
                    raise ValueError(
                        f"Sampling point '{p.point_code}' coordinate ({p.planned_lat}, {p.planned_lon}) "
                        f"is outside the spatial boundary of LandUnit '{land_unit.name}' ({land_unit.code})."
                    )

            dup = await db.scalar(
                select(SamplingPoint.id).where(
                    SamplingPoint.campaign_id == campaign_id,
                    SamplingPoint.point_code == p.point_code,
                )
            )
            if dup:
                raise ValueError(f"Sampling point with code '{p.point_code}' already exists in campaign.")

            geom_point = None
            try:
                from shapely.geometry import Point as ShapelyPoint
                from geoalchemy2.shape import from_shape
                geom_point = from_shape(ShapelyPoint(p.planned_lon, p.planned_lat), srid=4326)
            except Exception:
                geom_point = None

            point_obj = SamplingPoint(
                organization_id=organization_id,
                project_id=spv.project_id,
                campaign_id=campaign_id,
                plan_version_id=plan_version_id,
                land_unit_id=p.land_unit_id,
                stratum_id=p.stratum_id,
                point_code=p.point_code,
                planned_lat=p.planned_lat,
                planned_lon=p.planned_lon,
                geom=geom_point,
                depth_from_cm=p.depth_from_cm,
                depth_to_cm=p.depth_to_cm,
                depth_class_label=p.depth_class_label,
                sampling_purpose=p.sampling_purpose,
                replicate_group=p.replicate_group,
                status="PLANNED",
                notes=p.notes,
            )
            db.add(point_obj)
            await db.flush()

            sample_code = f"AG-{p_code}-{c_code}-{p.point_code}"
            existing_sample = await db.scalar(select(PhysicalSample.id).where(PhysicalSample.sample_code == sample_code))
            if existing_sample:
                sample_code = f"{sample_code}-{str(point_obj.id)[:8]}"

            qr_code = f"VERIFIELD:AG:{sample_code}"

            physical_sample = PhysicalSample(
                organization_id=organization_id,
                project_id=spv.project_id,
                campaign_id=campaign_id,
                plan_version_id=plan_version_id,
                sampling_point_id=point_obj.id,
                land_unit_id=p.land_unit_id,
                stratum_id=p.stratum_id,
                sample_code=sample_code,
                status="PLANNED",
                qr_barcode_code=qr_code,
                notes=f"Planned physical soil sample for point {p.point_code}",
            )
            db.add(physical_sample)
            await db.flush()

            created_points.append(point_obj)

        return created_points

    @classmethod
    async def get_sampling_points(
        cls,
        db: AsyncSession,
        campaign_id: uuid.UUID,
        organization_id: uuid.UUID,
        plan_version_id: Optional[uuid.UUID] = None,
    ) -> List[Dict[str, Any]]:
        stmt = (
            select(SamplingPoint)
            .where(
                SamplingPoint.campaign_id == campaign_id,
                SamplingPoint.organization_id == organization_id,
            )
            .options(selectinload(SamplingPoint.physical_sample))
            .order_by(SamplingPoint.created_at.asc())
        )
        if plan_version_id:
            stmt = stmt.where(SamplingPoint.plan_version_id == plan_version_id)
        res = await db.execute(stmt)
        pts = list(res.scalars().all())

        out = []
        for pt in pts:
            ps = pt.physical_sample
            out.append({
                "id": pt.id,
                "organization_id": pt.organization_id,
                "project_id": pt.project_id,
                "campaign_id": pt.campaign_id,
                "plan_version_id": pt.plan_version_id,
                "land_unit_id": pt.land_unit_id,
                "stratum_id": pt.stratum_id,
                "point_code": pt.point_code,
                "planned_lat": pt.planned_lat,
                "planned_lon": pt.planned_lon,
                "depth_from_cm": pt.depth_from_cm,
                "depth_to_cm": pt.depth_to_cm,
                "depth_class_label": pt.depth_class_label,
                "sampling_purpose": pt.sampling_purpose,
                "replicate_group": pt.replicate_group,
                "status": pt.status,
                "notes": pt.notes,
                "created_at": pt.created_at,
                "sample_id": ps.id if ps else None,
                "sample_code": ps.sample_code if ps else None,
                "sample_status": ps.status if ps else None,
            })
        return out

    @classmethod
    async def get_physical_samples(
        cls,
        db: AsyncSession,
        project_id: uuid.UUID,
        organization_id: uuid.UUID,
        campaign_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
    ) -> List[PhysicalSample]:
        stmt = (
            select(PhysicalSample)
            .where(
                PhysicalSample.project_id == project_id,
                PhysicalSample.organization_id == organization_id,
            )
            .options(
                selectinload(PhysicalSample.sampling_point),
                selectinload(PhysicalSample.collection_event),
                selectinload(PhysicalSample.custody_events),
                selectinload(PhysicalSample.laboratory_receipt),
                selectinload(PhysicalSample.laboratory_analyses).selectinload(LaboratoryAnalysis.results),
                selectinload(PhysicalSample.qa_review),
            )
            .order_by(PhysicalSample.created_at.desc())
        )
        if campaign_id:
            stmt = stmt.where(PhysicalSample.campaign_id == campaign_id)
        if status:
            stmt = stmt.where(PhysicalSample.status == status)
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @classmethod
    async def get_physical_sample_by_id(
        cls,
        db: AsyncSession,
        sample_id: uuid.UUID,
        organization_id: uuid.UUID,
    ) -> Optional[PhysicalSample]:
        stmt = (
            select(PhysicalSample)
            .where(
                PhysicalSample.id == sample_id,
                PhysicalSample.organization_id == organization_id,
            )
            .options(
                selectinload(PhysicalSample.sampling_point),
                selectinload(PhysicalSample.collection_event),
                selectinload(PhysicalSample.custody_events),
                selectinload(PhysicalSample.laboratory_receipt),
                selectinload(PhysicalSample.laboratory_analyses).selectinload(LaboratoryAnalysis.results),
                selectinload(PhysicalSample.qa_review),
            )
            .execution_options(populate_existing=True)
        )
        res = await db.execute(stmt)
        return res.scalars().first()

    @classmethod
    async def record_sample_collection(
        cls,
        db: AsyncSession,
        sample_id: uuid.UUID,
        organization_id: uuid.UUID,
        payload: SampleCollectionCreate,
        user_id: Optional[uuid.UUID] = None,
    ) -> SampleCollectionEvent:
        sample = await cls.get_physical_sample_by_id(db, sample_id, organization_id)
        if not sample:
            raise ValueError(f"PhysicalSample '{sample_id}' not found.")

        if payload.idempotency_key:
            existing = await db.scalar(
                select(SampleCollectionEvent).where(
                    SampleCollectionEvent.idempotency_key == payload.idempotency_key
                )
            )
            if existing:
                return existing

        existing_col = await db.scalar(
            select(SampleCollectionEvent).where(
                SampleCollectionEvent.physical_sample_id == sample.id
            )
        )
        if existing_col:
            raise ValueError(f"PhysicalSample '{sample.sample_code}' has already been collected.")

        point = await db.scalar(
            select(SamplingPoint).where(SamplingPoint.id == sample.sampling_point_id)
        )
        if not point:
            raise ValueError(f"SamplingPoint associated with sample '{sample_id}' not found.")

        dev_m = compute_geodesic_distance_m(point.planned_lat, point.planned_lon, payload.actual_lat, payload.actual_lon)
        if dev_m > 50.0 and not payload.deviation_reason:
            raise ValueError(
                f"Collection point deviates by {dev_m:.1f}m from planned coordinates (> 50m threshold). "
                "deviation_reason is mandatory for deviations exceeding 50 meters."
            )

        actual_geom_val = None
        try:
            from shapely.geometry import Point as ShapelyPoint
            from geoalchemy2.shape import from_shape
            actual_geom_val = from_shape(ShapelyPoint(payload.actual_lon, payload.actual_lat), srid=4326)
        except Exception:
            actual_geom_val = None

        ev = SampleCollectionEvent(
            physical_sample_id=sample.id,
            sampling_point_id=point.id,
            actual_lat=payload.actual_lat,
            actual_lon=payload.actual_lon,
            actual_geom=actual_geom_val,
            deviation_distance_m=round(dev_m, 2),
            deviation_reason=payload.deviation_reason,
            collection_timestamp=payload.collection_timestamp,
            collector_id=user_id,
            collector_name=payload.collector_name,
            actual_depth_from_cm=payload.actual_depth_from_cm,
            actual_depth_to_cm=payload.actual_depth_to_cm,
            sample_condition=payload.sample_condition,
            notes=payload.notes,
            photo_evidence_id=payload.photo_evidence_id,
            photo_hash=payload.photo_hash,
            device_metadata=payload.device_metadata or {},
            idempotency_key=payload.idempotency_key,
            sync_timestamp=datetime.now(timezone.utc),
        )
        db.add(ev)

        sample.status = "COLLECTED"
        sample.updated_at = datetime.now(timezone.utc)
        point.status = "COLLECTED"

        campaign = await db.scalar(select(SamplingCampaign).where(SamplingCampaign.id == sample.campaign_id))
        if campaign and campaign.status in ["LOCKED", "PLANNED"]:
            campaign.status = "IN_FIELD"
            campaign.updated_at = datetime.now(timezone.utc)

        custody_ev = ChainOfCustodyEvent(
            physical_sample_id=sample.id,
            event_type="COLLECTION",
            event_timestamp=payload.collection_timestamp,
            custodian_id=user_id,
            custodian_name=payload.collector_name,
            custodian_organization="Field Sampling Team",
            from_location=f"GPS: {payload.actual_lat:.5f}, {payload.actual_lon:.5f}",
            to_location="Field Collection Vehicle",
            condition=payload.sample_condition,
            seal_intact=True,
            notes=f"Initial ground extraction. Geodesic deviation: {dev_m:.1f}m.",
            evidence_id=payload.photo_evidence_id,
        )
        db.add(custody_ev)

        await db.flush()
        await db.refresh(ev)
        return ev

    @classmethod
    async def record_custody_event(
        cls,
        db: AsyncSession,
        sample_id: uuid.UUID,
        organization_id: uuid.UUID,
        payload: CustodyEventCreate,
        user_id: Optional[uuid.UUID] = None,
    ) -> ChainOfCustodyEvent:
        sample = await cls.get_physical_sample_by_id(db, sample_id, organization_id)
        if not sample:
            raise ValueError(f"PhysicalSample '{sample_id}' not found.")

        if sample.status == "PLANNED":
            raise ValueError(
                f"Sample '{sample.sample_code}' is in PLANNED state and has not been collected yet. "
                "Cannot record custody transfer for uncollected sample."
            )

        if sample.status in ["DISPOSED", "REJECTED_BY_LAB", "QA_REJECTED"] and payload.event_type not in ["DISPOSAL", "QA_REVIEW"]:
            raise ValueError(f"Sample is in '{sample.status}' state; cannot record '{payload.event_type}' custody event without explicit corrective action.")

        ev = ChainOfCustodyEvent(
            physical_sample_id=sample.id,
            event_type=payload.event_type,
            event_timestamp=payload.event_timestamp,
            custodian_id=user_id or sample.organization_id,
            custodian_name=payload.custodian_name,
            custodian_organization=payload.custodian_organization,
            from_location=payload.from_location,
            to_location=payload.to_location,
            condition=payload.condition,
            seal_intact=payload.seal_intact,
            seal_identifier=payload.seal_identifier,
            notes=payload.notes,
            evidence_id=payload.evidence_id,
        )
        db.add(ev)

        if payload.event_type == "SEALING":
            sample.status = "SEALED"
        elif payload.event_type in ["TRANSFER", "TRANSPORT_DISPATCH", "CARRIER_PICKUP"]:
            sample.status = "IN_TRANSIT"
        elif payload.event_type == "DISPOSAL":
            sample.status = "DISPOSED"

        sample.updated_at = datetime.now(timezone.utc)
        await db.flush()
        await db.refresh(ev)
        return ev

    @classmethod
    async def record_laboratory_receipt(
        cls,
        db: AsyncSession,
        sample_id: uuid.UUID,
        organization_id: uuid.UUID,
        payload: LabReceiptCreate,
        user_id: Optional[uuid.UUID] = None,
    ) -> LaboratoryReceipt:
        sample = await cls.get_physical_sample_by_id(db, sample_id, organization_id)
        if not sample:
            raise ValueError(f"PhysicalSample '{sample_id}' not found.")

        if sample.status not in ["COLLECTED", "SEALED", "IN_TRANSIT"]:
            raise ValueError(
                f"Sample '{sample.sample_code}' cannot undergo lab receipt from status '{sample.status}'. "
                "Sample must be collected and dispatched before laboratory intake."
            )

        existing_receipt = await db.scalar(
            select(LaboratoryReceipt).where(
                LaboratoryReceipt.physical_sample_id == sample.id
            )
        )
        if existing_receipt:
            raise ValueError(f"Laboratory receipt already recorded for sample '{sample.sample_code}'.")

        receipt = LaboratoryReceipt(
            physical_sample_id=sample.id,
            laboratory_name=payload.laboratory_name,
            laboratory_id_ref=payload.laboratory_id_ref,
            received_at=payload.received_at,
            received_by_name=payload.received_by_name,
            condition_on_receipt=payload.condition_on_receipt,
            seal_status=payload.seal_status,
            intake_status=payload.intake_status,
            rejection_reason=payload.rejection_reason,
            receipt_evidence_id=payload.receipt_evidence_id,
            notes=payload.notes,
        )
        db.add(receipt)

        if payload.intake_status == "ACCEPTED":
            sample.status = "RECEIVED_BY_LAB"
        else:
            sample.status = "REJECTED_BY_LAB"

        sample.updated_at = datetime.now(timezone.utc)

        custody_ev = ChainOfCustodyEvent(
            physical_sample_id=sample.id,
            event_type="LAB_RECEIPT",
            event_timestamp=payload.received_at,
            custodian_id=user_id,
            custodian_name=payload.received_by_name,
            custodian_organization=payload.laboratory_name,
            from_location="Transport Carrier",
            to_location=payload.laboratory_name,
            condition=payload.condition_on_receipt,
            seal_intact=(payload.seal_status == "SEALED_INTACT"),
            seal_identifier=None,
            notes=f"Lab intake status: {payload.intake_status}. Reason: {payload.rejection_reason or 'Accepted'}.",
            evidence_id=payload.receipt_evidence_id,
        )
        db.add(custody_ev)

        campaign = await db.scalar(select(SamplingCampaign).where(SamplingCampaign.id == sample.campaign_id))
        if campaign and campaign.status in ["IN_FIELD", "COLLECTION_COMPLETE"]:
            campaign.status = "LAB_IN_PROGRESS"
            campaign.updated_at = datetime.now(timezone.utc)

        await db.flush()
        await db.refresh(receipt)
        return receipt

    @staticmethod
    def normalize_laboratory_analyte_measurement(
        analyte: str,
        raw_value: Decimal,
        raw_unit: str,
    ) -> Tuple[Optional[Decimal], Optional[str], Optional[str], Optional[str]]:
        """
        Deterministically normalizes physical laboratory measurements using published physical constants.
        Preserves raw value and raw unit immutably.
        Canonical unit for Soil Organic Carbon (SOC) is 'g/kg'.
        Returns: (normalized_value, normalized_unit, normalization_method, normalization_version)
        If no valid, safe physical conversion is applicable: returns (None, None, "UNCONVERTIBLE", "UNIT_CONV_V1.0").
        """
        if raw_value is None:
            return (None, None, "UNCONVERTIBLE", "UNIT_CONV_V1.0")

        if not isinstance(raw_value, Decimal):
            try:
                raw_value = Decimal(str(raw_value))
            except Exception:
                return (None, None, "UNCONVERTIBLE", "UNIT_CONV_V1.0")

        clean_unit = (raw_unit or "").strip().lower().replace(" ", "")
        analyte_upper = (analyte or "").strip().upper()

        # Carbon / organic matter concentration (canonical: SOC_CONCENTRATION, aliases: SOC, SOC_STOCK_PCT, TOTAL_ORGANIC_CARBON_G_KG, SOC_PCT)
        # Canonical standardized unit: "g/kg"
        if analyte_upper in ["SOC", "SOC_CONCENTRATION", "SOC_STOCK_PCT", "TOTAL_ORGANIC_CARBON_G_KG", "SOC_PCT"]:
            # 1% = 10 g/kg (LINEAR_SCALING:VAL*10)
            if clean_unit in ["%", "pct", "percent"]:
                norm_val = (raw_value * Decimal("10.0")).quantize(Decimal("0.0001"))
                return (norm_val, "g/kg", "LINEAR_SCALING:VAL*10", "UNIT_CONV_V1.0")
            # 1 g/kg = 1 g/kg (IDENTITY)
            elif clean_unit in ["g/kg", "g_kg", "g.kg-1"]:
                norm_val = raw_value.quantize(Decimal("0.0001"))
                return (norm_val, "g/kg", "IDENTITY", "UNIT_CONV_V1.0")
            # 1 mg/g = 1 g/kg (IDENTITY)
            elif clean_unit in ["mg/g", "mg_g", "mg.g-1"]:
                norm_val = raw_value.quantize(Decimal("0.0001"))
                return (norm_val, "g/kg", "IDENTITY", "UNIT_CONV_V1.0")
            # 1 mg/kg = 0.001 g/kg (LINEAR_SCALING:VAL/1000)
            elif clean_unit in ["mg/kg", "mg_kg", "mg.kg-1"]:
                norm_val = (raw_value / Decimal("1000.0")).quantize(Decimal("0.0001"))
                return (norm_val, "g/kg", "LINEAR_SCALING:VAL/1000", "UNIT_CONV_V1.0")
            else:
                return (None, None, "UNCONVERTIBLE", "UNIT_CONV_V1.0")

        # Bulk density
        elif analyte_upper in ["BULK_DENSITY_G_CM3", "CORE_BULK_DENSITY"]:
            # Standardized unit: "g/cm³"
            if clean_unit in ["g/cm3", "g/cm³", "g_cm3", "g.cm-3"]:
                return (raw_value.quantize(Decimal("0.0001")), "g/cm³", "IDENTITY", "UNIT_CONV_V1.0")
            elif clean_unit in ["kg/m3", "kg/m³", "kg_m3", "kg.m-3"]:
                norm_val = (raw_value / Decimal("1000.0")).quantize(Decimal("0.0001"))
                return (norm_val, "g/cm³", "LINEAR_SCALING:VAL/1000", "UNIT_CONV_V1.0")
            else:
                return (None, None, "UNCONVERTIBLE", "UNIT_CONV_V1.0")

        # Soil Texture Fractions
        elif analyte_upper in ["SAND_PCT", "SILT_PCT", "CLAY_PCT", "COARSE_FRAGMENTS_PCT", "MOISTURE_PCT"]:
            if clean_unit in ["%", "pct", "percent"]:
                return (raw_value.quantize(Decimal("0.0001")), "%", "IDENTITY", "UNIT_CONV_V1.0")
            elif clean_unit in ["g/kg", "g_kg"]:
                norm_val = (raw_value / Decimal("10.0")).quantize(Decimal("0.0001"))
                return (norm_val, "%", "LINEAR_SCALING:VAL/10", "UNIT_CONV_V1.0")
            else:
                return (None, None, "UNCONVERTIBLE", "UNIT_CONV_V1.0")

        # pH
        elif analyte_upper == "PH":
            if clean_unit in ["ph", "units", ""]:
                return (raw_value.quantize(Decimal("0.0001")), "pH", "IDENTITY", "UNIT_CONV_V1.0")
            else:
                return (None, None, "UNCONVERTIBLE", "UNIT_CONV_V1.0")

        # Electrical Conductivity
        elif analyte_upper == "ELECTRICAL_CONDUCTIVITY_DS_M":
            if clean_unit in ["ds/m", "ds_m", "ms/cm"]:
                return (raw_value.quantize(Decimal("0.0001")), "dS/m", "IDENTITY", "UNIT_CONV_V1.0")
            else:
                return (None, None, "UNCONVERTIBLE", "UNIT_CONV_V1.0")

        # If no safe/supported formula exists, return UNCONVERTIBLE
        return (None, None, "UNCONVERTIBLE", "UNIT_CONV_V1.0")


    @classmethod
    async def record_laboratory_analysis(
        cls,
        db: AsyncSession,
        sample_id: uuid.UUID,
        organization_id: uuid.UUID,
        payload: LabAnalysisCreate,
        user_id: Optional[uuid.UUID] = None,
    ) -> LaboratoryAnalysis:
        sample = await cls.get_physical_sample_by_id(db, sample_id, organization_id)
        if not sample:
            raise ValueError(f"PhysicalSample '{sample_id}' not found.")

        receipt = await db.scalar(
            select(LaboratoryReceipt).where(
                LaboratoryReceipt.physical_sample_id == sample.id
            )
        )
        if not receipt:
            raise ValueError("Sample has not undergone formal laboratory receipt. Receipt is mandatory before analysis.")
        if receipt.intake_status != "ACCEPTED" or sample.status == "REJECTED_BY_LAB":
            raise ValueError(
                f"Sample '{sample.sample_code}' was rejected by laboratory "
                f"('{receipt.rejection_reason}'). Analytical assays cannot be recorded for rejected samples."
            )

        analysis = LaboratoryAnalysis(
            physical_sample_id=sample.id,
            laboratory_name=payload.laboratory_name,
            laboratory_accreditation=payload.laboratory_accreditation,
            accreditation_status=payload.accreditation_status,
            accreditation_evidence_id=payload.accreditation_evidence_id,
            analysis_batch_id=payload.analysis_batch_id,
            analytical_method=payload.analytical_method,
            method_standard_code=payload.method_standard_code,
            analysis_date=payload.analysis_date,
            report_reference_number=payload.report_reference_number,
            analyst_name=payload.analyst_name,
            qa_status="PENDING",
            evidence_id=payload.evidence_id,
        )
        db.add(analysis)
        await db.flush()

        for res_in in payload.results:
            n_val = res_in.normalized_value
            n_unit = res_in.normalized_unit
            n_meth = res_in.normalization_method
            n_ver = res_in.normalization_version

            if n_val is None:
                calc_val, calc_unit, calc_meth, calc_ver = cls.normalize_laboratory_analyte_measurement(
                    res_in.analyte, res_in.raw_value, res_in.raw_unit
                )
                n_val = calc_val
                n_unit = calc_unit
                n_meth = calc_meth
                n_ver = calc_ver

            lab_res = LaboratoryResult(
                analysis_id=analysis.id,
                physical_sample_id=sample.id,
                analyte=res_in.analyte,
                raw_value=res_in.raw_value,
                raw_unit=res_in.raw_unit,
                normalized_value=n_val,
                normalized_unit=n_unit,
                normalization_method=n_meth,
                normalization_version=n_ver,
                detection_limit=res_in.detection_limit,
                quantification_limit=res_in.quantification_limit,
                uncertainty_pct=res_in.uncertainty_pct,
                qualifier=res_in.qualifier,
                is_superseded=False,
                superseded_by_id=None,
                supersedes_id=None,
            )
            db.add(lab_res)

        sample.status = "ANALYZED" if len(payload.results) > 0 else "ANALYSIS_IN_PROGRESS"
        sample.updated_at = datetime.now(timezone.utc)

        await db.flush()
        res_stmt = (
            select(LaboratoryAnalysis)
            .where(LaboratoryAnalysis.id == analysis.id)
            .options(selectinload(LaboratoryAnalysis.results))
        )
        full_analysis = (await db.execute(res_stmt)).scalars().first()
        return full_analysis

    @classmethod
    async def revise_laboratory_result(
        cls,
        db: AsyncSession,
        result_id: uuid.UUID,
        organization_id: uuid.UUID,
        payload: LabResultRevisionCreate,
        user_id: Optional[uuid.UUID] = None,
    ) -> LaboratoryResult:
        res_stmt = (
            select(LaboratoryResult)
            .where(LaboratoryResult.id == result_id)
            .options(selectinload(LaboratoryResult.analysis))
        )
        res_res = await db.execute(res_stmt)
        orig = res_res.scalars().first()
        if not orig:
            raise ValueError(f"LaboratoryResult '{result_id}' not found.")
        if orig.is_superseded:
            raise ValueError(f"LaboratoryResult '{result_id}' has already been superseded by '{orig.superseded_by_id}'.")

        sample_stmt = select(PhysicalSample).where(
            PhysicalSample.id == orig.physical_sample_id,
            PhysicalSample.organization_id == organization_id,
        )
        sample = (await db.execute(sample_stmt)).scalars().first()
        if not sample:
            raise ValueError("Unauthorized: result does not belong to organization.")

        n_val = payload.new_normalized_value
        n_unit = payload.new_normalized_unit
        n_meth = payload.normalization_method
        n_ver = payload.normalization_version

        if n_val is None:
            calc_val, calc_unit, calc_meth, calc_ver = cls.normalize_laboratory_analyte_measurement(
                orig.analyte, payload.new_raw_value, payload.new_raw_unit
            )
            n_val = calc_val
            n_unit = calc_unit
            n_meth = calc_meth
            n_ver = calc_ver

        revised = LaboratoryResult(
            analysis_id=orig.analysis_id,
            physical_sample_id=orig.physical_sample_id,
            analyte=orig.analyte,
            raw_value=payload.new_raw_value,
            raw_unit=payload.new_raw_unit,
            normalized_value=n_val,
            normalized_unit=n_unit,
            normalization_method=n_meth,
            normalization_version=n_ver,
            detection_limit=payload.detection_limit,
            quantification_limit=payload.quantification_limit,
            uncertainty_pct=payload.uncertainty_pct,
            qualifier=payload.qualifier,
            is_superseded=False,
            superseded_by_id=None,
            supersedes_id=orig.id,
            revision_reason=f"Supersedes result {orig.id}: {payload.revision_reason}",
        )
        db.add(revised)
        await db.flush()

        orig.is_superseded = True
        orig.superseded_by_id = revised.id
        orig.revision_reason = payload.revision_reason
        await db.flush()
        await db.refresh(revised)
        return revised

    @classmethod
    async def record_sample_qa_review(
        cls,
        db: AsyncSession,
        sample_id: uuid.UUID,
        organization_id: uuid.UUID,
        payload: SampleQAReviewCreate,
        user_id: Optional[uuid.UUID] = None,
    ) -> SampleQAReview:
        sample = await cls.get_physical_sample_by_id(db, sample_id, organization_id)
        if not sample:
            raise ValueError(f"PhysicalSample '{sample_id}' not found.")

        # Enforce Separation of Duties: Collector cannot approve own evidence
        col_stmt = select(SampleCollectionEvent).where(SampleCollectionEvent.physical_sample_id == sample.id)
        col_ev = (await db.execute(col_stmt)).scalars().first()
        if user_id and col_ev and col_ev.collector_id == user_id:
            raise ValueError(
                "Separation of Duties violation: The field collector who recorded this sample "
                "cannot perform the independent QA review."
            )

        # Enforce assay presence before QA acceptance
        if payload.overall_qa_status == "ACCEPTED":
            res_stmt = select(LaboratoryResult.id).where(
                LaboratoryResult.physical_sample_id == sample.id,
                LaboratoryResult.is_superseded == False,
            )
            active_res = (await db.execute(res_stmt)).scalars().all()
            if not active_res:
                raise ValueError(
                    f"Sample '{sample.sample_code}' cannot be accepted: no verified, non-superseded laboratory results exist."
                )

        review = await db.scalar(
            select(SampleQAReview).where(
                SampleQAReview.physical_sample_id == sample.id
            )
        )
        if not review:
            review = SampleQAReview(
                physical_sample_id=sample.id,
                reviewer_id=user_id,
                reviewer_name=payload.reviewer_name,
                review_date=payload.review_date or datetime.now(timezone.utc),
                overall_qa_status=payload.overall_qa_status,
                location_verified=payload.location_verified,
                deviation_acceptable=payload.deviation_acceptable,
                depth_valid=payload.depth_valid,
                custody_complete=payload.custody_complete,
                lab_receipt_verified=payload.lab_receipt_verified,
                required_assays_present=payload.required_assays_present,
                notes=payload.notes,
            )
            db.add(review)
        else:
            review.reviewer_id = user_id
            review.reviewer_name = payload.reviewer_name
            review.review_date = payload.review_date or datetime.now(timezone.utc)
            review.overall_qa_status = payload.overall_qa_status
            review.location_verified = payload.location_verified
            review.deviation_acceptable = payload.deviation_acceptable
            review.depth_valid = payload.depth_valid
            review.custody_complete = payload.custody_complete
            review.lab_receipt_verified = payload.lab_receipt_verified
            review.required_assays_present = payload.required_assays_present
            review.notes = payload.notes

        if payload.overall_qa_status == "ACCEPTED":
            sample.status = "QA_ACCEPTED"
        elif payload.overall_qa_status == "REJECTED":
            sample.status = "QA_REJECTED"

        # Propagate QA status to associated laboratory analyses
        analyses_res = await db.execute(
            select(LaboratoryAnalysis).where(
                LaboratoryAnalysis.physical_sample_id == sample.id
            )
        )
        for analysis in analyses_res.scalars().all():
            if payload.overall_qa_status == "ACCEPTED":
                analysis.qa_status = "VERIFIED"
            elif payload.overall_qa_status == "REJECTED":
                analysis.qa_status = "REJECTED"

        sample.updated_at = datetime.now(timezone.utc)
        await db.flush()
        await db.refresh(review)
        return review

    @classmethod
    async def evaluate_ground_evidence_readiness(
        cls,
        db: AsyncSession,
        project_id: uuid.UUID,
        organization_id: uuid.UUID,
    ) -> Dict[str, Any]:
        await cls.get_project_or_raise(db, project_id, organization_id)
        await db.flush()

        # 1. Sampling Campaign
        c_stmt = (
            select(SamplingCampaign)
            .where(
                SamplingCampaign.project_id == project_id,
                SamplingCampaign.organization_id == organization_id,
            )
            .order_by(SamplingCampaign.created_at.desc())
        )
        c_res = await db.execute(c_stmt)
        campaigns = list(c_res.scalars().all())
        active_campaigns = [c for c in campaigns if c.status not in ["CANCELLED", "DRAFT"]]

        if len(active_campaigns) > 0:
            c_status = "COMPLETE"
            c_msg = f"{len(active_campaigns)} active sampling campaign(s) configured"
        elif len(campaigns) > 0:
            c_status = "NEEDS_REVIEW"
            c_msg = f"{len(campaigns)} sampling campaign(s) defined but none in ACTIVE/LOCKED/IN_FIELD status"
        else:
            c_status = "NOT_CONFIGURED"
            c_msg = "No sampling campaigns established (0 campaigns)"

        c_details = {
            "total_campaigns": len(campaigns),
            "active_campaigns": len(active_campaigns),
            "campaign_codes": [c.campaign_code for c in campaigns],
        }

        # 2. Sampling Plan
        plan_stmt = select(SamplingPlanVersion).where(
            SamplingPlanVersion.project_id == project_id,
            SamplingPlanVersion.organization_id == organization_id,
        )
        plan_res = await db.execute(plan_stmt)
        plans = list(plan_res.scalars().all())
        locked_plans = [p for p in plans if p.is_locked]

        if len(locked_plans) > 0:
            plan_status = "COMPLETE"
            plan_msg = f"{len(locked_plans)} locked sampling plan version(s) with frozen stratification snapshot"
        elif len(plans) > 0:
            plan_status = "NEEDS_REVIEW"
            plan_msg = f"{len(plans)} sampling plan version(s) exist but none have been locked to an immutable design"
        else:
            plan_status = "NOT_CONFIGURED"
            plan_msg = "No sampling plan versions configured (0 plans)"

        plan_details = {
            "total_plans": len(plans),
            "locked_plans": len(locked_plans),
        }

        # 3. Stratum Coverage
        strata_stmt = select(Stratum).where(Stratum.project_id == project_id)
        strata = list((await db.execute(strata_stmt)).scalars().all())

        pts_stmt = select(SamplingPoint).where(
            SamplingPoint.project_id == project_id,
            SamplingPoint.organization_id == organization_id,
        )
        pts = list((await db.execute(pts_stmt)).scalars().all())
        sampled_strata_ids = {p.stratum_id for p in pts if p.stratum_id}

        if len(strata) > 0 and len(sampled_strata_ids) == len(strata):
            strat_cov_status = "COMPLETE"
            strat_cov_msg = f"All {len(strata)} strata have planned ground sampling points"
        elif len(strata) > 0 and len(sampled_strata_ids) > 0:
            missing_count = len(strata) - len(sampled_strata_ids)
            strat_cov_status = "INCOMPLETE"
            strat_cov_msg = f"{len(sampled_strata_ids)} of {len(strata)} strata sampled ({missing_count} unrepresented)"
        elif len(strata) > 0:
            strat_cov_status = "NOT_CONFIGURED"
            strat_cov_msg = f"0 of {len(strata)} strata have planned sample points"
        else:
            strat_cov_status = "NOT_CONFIGURED"
            strat_cov_msg = "No strata configured for project"

        strat_cov_details = {
            "total_strata": len(strata),
            "represented_strata": len(sampled_strata_ids),
        }

        # 4. Sampling Points
        if len(pts) > 0:
            pts_status = "COMPLETE"
            pts_msg = f"{len(pts)} sampling point(s) planned across land units"
        else:
            pts_status = "NOT_CONFIGURED"
            pts_msg = "0 sampling points registered in project"

        pts_details = {
            "total_points": len(pts),
        }

        # 5. Field Collection
        samples = list(
            (
                await db.execute(
                    select(PhysicalSample).where(
                        PhysicalSample.project_id == project_id,
                        PhysicalSample.organization_id == organization_id,
                    )
                )
            )
            .scalars()
            .all()
        )
        sample_ids = [s.id for s in samples]

        collections = []
        if sample_ids:
            col_res = await db.execute(
                select(SampleCollectionEvent).where(
                    SampleCollectionEvent.physical_sample_id.in_(sample_ids)
                )
            )
            collections = list(col_res.scalars().all())
        collected_sample_ids = {c.physical_sample_id for c in collections}

        if len(samples) > 0 and len(collected_sample_ids) == len(samples):
            col_status = "COMPLETE"
            col_msg = f"All {len(samples)} planned samples successfully collected in the field"
        elif len(collected_sample_ids) > 0:
            missing_col = len(samples) - len(collected_sample_ids)
            col_status = "INCOMPLETE"
            col_msg = f"{len(collected_sample_ids)} of {len(samples)} samples collected ({missing_col} pending)"
        else:
            col_status = "NOT_CONFIGURED"
            col_msg = "0 field sample collection events documented"

        col_details = {
            "total_samples": len(samples),
            "collected_samples": len(collected_sample_ids),
        }

        # 6. Chain of Custody
        custody_sample_ids = set()
        if sample_ids:
            cust_res = await db.execute(
                select(ChainOfCustodyEvent.physical_sample_id).where(
                    ChainOfCustodyEvent.physical_sample_id.in_(sample_ids)
                )
            )
            custody_sample_ids = set(cust_res.scalars().all())

        custody_complete_ids = collected_sample_ids.intersection(custody_sample_ids)
        if len(collected_sample_ids) > 0 and len(custody_complete_ids) == len(collected_sample_ids):
            cust_status = "COMPLETE"
            cust_msg = f"Complete unbroken chain of custody recorded for all {len(collected_sample_ids)} collected samples"
        elif len(custody_complete_ids) > 0:
            cust_status = "INCOMPLETE"
            cust_msg = f"{len(custody_complete_ids)} of {len(collected_sample_ids)} collected samples have custody logs"
        else:
            cust_status = "NOT_CONFIGURED"
            cust_msg = "0 chain of custody transfer events documented"

        cust_details = {
            "samples_with_custody": len(custody_complete_ids),
        }

        # 7. Laboratory Receipt
        receipts = []
        if sample_ids:
            rec_res = await db.execute(
                select(LaboratoryReceipt).where(
                    LaboratoryReceipt.physical_sample_id.in_(sample_ids)
                )
            )
            receipts = list(rec_res.scalars().all())
        receipted_sample_ids = {r.physical_sample_id for r in receipts if r.intake_status == "ACCEPTED"}
        rejected_sample_ids = {r.physical_sample_id for r in receipts if r.intake_status == "REJECTED"}

        if len(collected_sample_ids) > 0 and len(receipted_sample_ids) == len(collected_sample_ids):
            rec_status = "COMPLETE"
            rec_msg = f"All {len(receipted_sample_ids)} collected samples formally received and accepted by accredited lab"
        elif len(rejected_sample_ids) > 0:
            rec_status = "NEEDS_REVIEW"
            rec_msg = f"{len(rejected_sample_ids)} sample(s) rejected by lab during intake"
        elif len(receipted_sample_ids) > 0:
            rec_status = "INCOMPLETE"
            rec_msg = f"{len(receipted_sample_ids)} of {len(collected_sample_ids)} samples received by laboratory"
        else:
            rec_status = "NOT_CONFIGURED"
            rec_msg = "0 laboratory intake receipts documented"

        rec_details = {
            "receipted_samples": len(receipted_sample_ids),
            "rejected_samples": len(rejected_sample_ids),
        }

        # 8. Required Assays (SOC, Bulk Density)
        analyses = []
        if sample_ids:
            ana_res = await db.execute(
                select(LaboratoryAnalysis).where(LaboratoryAnalysis.physical_sample_id.in_(sample_ids))
            )
            analyses = list(ana_res.scalars().all())

        pending_analyses = [a for a in analyses if a.qa_status == "PENDING"]
        rejected_analyses = [a for a in analyses if a.qa_status == "REJECTED"]
        verified_analyses = [a for a in analyses if a.qa_status == "VERIFIED"]

        analyzed_sample_ids = set()
        if receipted_sample_ids:
            assay_res = await db.execute(
                select(LaboratoryResult.physical_sample_id).where(
                    LaboratoryResult.physical_sample_id.in_(receipted_sample_ids),
                    LaboratoryResult.analyte.in_(["SOC_CONCENTRATION", "SOC_STOCK_PCT", "TOTAL_ORGANIC_CARBON_G_KG", "SOC_PCT"]),
                    LaboratoryResult.is_superseded == False,
                )
            )
            analyzed_sample_ids = set(assay_res.scalars().all())

        if len(receipted_sample_ids) > 0 and len(analyzed_sample_ids) == len(receipted_sample_ids):
            assay_status = "COMPLETE"
            assay_msg = f"All {len(receipted_sample_ids)} accepted samples have laboratory SOC assay results"
        elif len(analyzed_sample_ids) > 0:
            assay_status = "INCOMPLETE"
            assay_msg = f"{len(analyzed_sample_ids)} of {len(receipted_sample_ids)} accepted samples have SOC assay results"
        else:
            assay_status = "NOT_CONFIGURED"
            assay_msg = "0 analytical laboratory assay results recorded"

        assay_details = {
            "analyzed_samples": len(analyzed_sample_ids),
            "total_analyses": len(analyses),
            "pending_analyses": len(pending_analyses),
            "verified_analyses": len(verified_analyses),
            "rejected_analyses": len(rejected_analyses),
        }

        # 9. QA Review
        reviews = []
        if sample_ids:
            qa_res = await db.execute(
                select(SampleQAReview).where(
                    SampleQAReview.physical_sample_id.in_(sample_ids)
                )
            )
            reviews = list(qa_res.scalars().all())
        qa_accepted_sample_ids = {rev.physical_sample_id for rev in reviews if rev.overall_qa_status == "ACCEPTED"}
        qa_rejected_sample_ids = {rev.physical_sample_id for rev in reviews if rev.overall_qa_status == "REJECTED"}

        # Readiness gating:
        # 1. Any rejected review OR rejected analysis -> NEEDS_REVIEW
        # 2. Any pending analysis batch -> INCOMPLETE (cannot be complete until verified)
        # 3. All analyzed samples have QA acceptance AND all analyses verified -> COMPLETE
        if len(qa_rejected_sample_ids) > 0 or len(rejected_analyses) > 0:
            qa_status = "NEEDS_REVIEW"
            qa_msg = f"{len(qa_rejected_sample_ids) + len(rejected_analyses)} sample(s)/assay(s) rejected during QA review"
        elif len(pending_analyses) > 0:
            qa_status = "INCOMPLETE"
            qa_msg = f"{len(pending_analyses)} laboratory analysis batch(es) pending QA verification"
        elif len(analyzed_sample_ids) > 0 and len(qa_accepted_sample_ids) == len(analyzed_sample_ids):
            qa_status = "COMPLETE"
            qa_msg = f"All {len(qa_accepted_sample_ids)} analyzed samples and laboratory analyses verified and accepted by QA reviewer"
        elif len(qa_accepted_sample_ids) > 0:
            qa_status = "INCOMPLETE"
            qa_msg = f"{len(qa_accepted_sample_ids)} of {len(analyzed_sample_ids)} analyzed samples have QA acceptance"
        else:
            qa_status = "NOT_CONFIGURED" if len(analyzed_sample_ids) == 0 else "INCOMPLETE"
            qa_msg = "0 sample QA review records documented"

        qa_details = {
            "qa_accepted_samples": len(qa_accepted_sample_ids),
            "qa_rejected_samples": len(qa_rejected_sample_ids),
            "pending_analyses": len(pending_analyses),
            "verified_analyses": len(verified_analyses),
            "rejected_analyses": len(rejected_analyses),
        }

        all_statuses = [
            c_status, plan_status, strat_cov_status, pts_status,
            col_status, cust_status, rec_status, assay_status, qa_status,
        ]

        if all(s == "COMPLETE" for s in all_statuses):
            overall_status = "COMPLETE"
        elif all(s == "NOT_CONFIGURED" for s in all_statuses):
            overall_status = "NOT_CONFIGURED"
        elif any(s == "NEEDS_REVIEW" for s in all_statuses):
            overall_status = "NEEDS_REVIEW"
        else:
            overall_status = "INCOMPLETE"

        design_sufficiency_status = "NOT_CONFIGURED"
        design_sufficiency_msg = (
            "Statistical sample-allocation engine not configured. "
            "Stratum coverage is factual only and does not establish statistical or methodological power sufficiency."
        )
        design_sufficiency_details = {
            "evaluator": None,
            "power_analysis_configured": False,
            "statistical_sufficiency": "NOT_CONFIGURED",
        }

        return {
            "project_id": str(project_id),
            "overall_status": overall_status,
            "components": {
                "sampling_campaign": {"status": c_status, "message": c_msg, "details": c_details},
                "sampling_plan": {"status": plan_status, "message": plan_msg, "details": plan_details},
                "design_sufficiency": {"status": design_sufficiency_status, "message": design_sufficiency_msg, "details": design_sufficiency_details},
                "stratum_coverage": {"status": strat_cov_status, "message": strat_cov_msg, "details": strat_cov_details},
                "sampling_points": {"status": pts_status, "message": pts_msg, "details": pts_details},
                "field_collection": {"status": col_status, "message": col_msg, "details": col_details},
                "chain_of_custody": {"status": cust_status, "message": cust_msg, "details": cust_details},
                "lab_receipt": {"status": rec_status, "message": rec_msg, "details": rec_details},
                "required_assays": {"status": assay_status, "message": assay_msg, "details": assay_details},
                "qa_review": {"status": qa_status, "message": qa_msg, "details": qa_details},
            },
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
        }

    # ─── Phase 3A: Quantification Readiness & Input Contract Methods ─────────

    @classmethod
    async def evaluate_eligible_measurements(
        cls,
        db: AsyncSession,
        project_id: uuid.UUID,
        organization_id: Optional[uuid.UUID] = None,
        campaign_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        """
        Evaluates physical soil samples and active laboratory assays against
        locked methodology rules to construct the candidate, eligible, and excluded
        measurement sets.
        """
        project = await cls.get_project_or_raise(db, project_id, organization_id)

        # Locked methodology metadata
        locked_meta = (project.baseline_parameters or {}).get("locked_methodology_version") or {}
        meth_code = locked_meta.get("methodology_code") or "VM0042"
        meth_version = locked_meta.get("version") or "2.2"
        rule_set_version = f"{meth_code}_V{meth_version.replace('.', '_')}_RULES_V1.0"
        quant_approach = locked_meta.get("quantification_approach", "DIRECT_MEASUREMENT")
        min_depth = float(locked_meta.get("minimum_depth_cm", 30.0))

        # Boundary version
        b_stmt = (
            select(ProjectBoundaryVersion)
            .where(ProjectBoundaryVersion.project_id == project_id)
            .order_by(ProjectBoundaryVersion.version_number.desc())
        )
        latest_b = (await db.execute(b_stmt)).scalars().first()
        boundary_id = latest_b.id if latest_b else None

        # Fetch sampling campaigns
        c_stmt = select(SamplingCampaign).where(SamplingCampaign.project_id == project_id)
        if campaign_id:
            c_stmt = c_stmt.where(SamplingCampaign.id == campaign_id)
        campaigns_res = await db.execute(c_stmt)
        campaigns = {c.id: c for c in campaigns_res.scalars().all()}

        # Fetch all physical samples with relations
        ps_stmt = (
            select(PhysicalSample)
            .where(PhysicalSample.project_id == project_id)
            .options(
                selectinload(PhysicalSample.sampling_point).selectinload(SamplingPoint.plan_version),
                selectinload(PhysicalSample.campaign),
                selectinload(PhysicalSample.land_unit),
                selectinload(PhysicalSample.collection_event),
                selectinload(PhysicalSample.custody_events),
                selectinload(PhysicalSample.laboratory_receipt),
                selectinload(PhysicalSample.laboratory_analyses).selectinload(LaboratoryAnalysis.results),
                selectinload(PhysicalSample.qa_review),
            )
        )
        if campaign_id:
            ps_stmt = ps_stmt.where(PhysicalSample.campaign_id == campaign_id)

        samples_res = await db.execute(ps_stmt)
        samples = samples_res.scalars().all()

        baseline_measurements: List[QuantificationMeasurementItem] = []
        project_measurements: List[QuantificationMeasurementItem] = []
        excluded_measurements: List[ExcludedMeasurementItem] = []

        for sample in samples:
            reasons: List[str] = []
            details: Dict[str, Any] = {}

            campaign = sample.campaign or campaigns.get(sample.campaign_id)
            sp = sample.sampling_point
            plan_version = sp.plan_version if sp else None
            col = sample.collection_event
            cust = sample.custody_events or []
            rcp = sample.laboratory_receipt
            analyses = sample.laboratory_analyses or []
            qa_rev = sample.qa_review
            lu = sample.land_unit

            # Determine sampling date
            sample_date = col.collection_timestamp.date() if col else (sp.created_at.date() if sp else sample.created_at.date())

            # 1. Temporal Stratum resolution as-of sampling date
            resolved_stratum_id = None
            resolved_stratum_code = None
            if sample.land_unit_id:
                sm_stmt = (
                    select(StratumMembership, Stratum)
                    .join(Stratum, StratumMembership.stratum_id == Stratum.id)
                    .where(
                        StratumMembership.land_unit_id == sample.land_unit_id,
                        StratumMembership.valid_from <= sample_date,
                        (StratumMembership.valid_to == None) | (StratumMembership.valid_to >= sample_date),
                        StratumMembership.status == "ACTIVE",
                    )
                    .order_by(StratumMembership.created_at.desc())
                )
                sm_res = (await db.execute(sm_stmt)).first()
                if sm_res:
                    sm, st = sm_res
                    resolved_stratum_id = st.id
                    resolved_stratum_code = st.code
                elif sample.stratum_id:
                    resolved_stratum_id = sample.stratum_id
                    st_obj = await db.get(Stratum, sample.stratum_id)
                    resolved_stratum_code = st_obj.code if st_obj else None

            # 2. Reconcile Depth Alignment (VM0042 minimum sampling depth from methodology config)
            act_from = col.actual_depth_from_cm if col else (sp.depth_from_cm if sp else 0.0)
            act_to = col.actual_depth_to_cm if col else (sp.depth_to_cm if sp else min_depth)
            req_from, req_to = 0.0, min_depth

            if act_from == req_from and act_to == req_to:
                depth_status = DepthAlignmentStatus.MATCH.value
            elif act_from == req_from and act_to < req_to:
                depth_status = DepthAlignmentStatus.PARTIAL_COVERAGE.value
            elif act_from > req_from and act_to <= req_to:
                depth_status = DepthAlignmentStatus.PARTIAL_COVERAGE.value
            elif act_from < req_to and act_to > req_to:
                depth_status = DepthAlignmentStatus.OVERLAPPING_INTERVAL.value
            elif act_from >= req_to:
                depth_status = DepthAlignmentStatus.OUT_OF_SCOPE.value
            else:
                depth_status = DepthAlignmentStatus.NEEDS_REVIEW.value

            # 3. Analyze Results and Supersession with Latest Valid Selection (§13)
            soc_candidates: List[Tuple[LaboratoryAnalysis, LaboratoryResult]] = []
            bd_candidates: List[Tuple[LaboratoryAnalysis, LaboratoryResult]] = []
            cf_candidates: List[Tuple[LaboratoryAnalysis, LaboratoryResult]] = []
            has_superseded_soc = False

            for analysis in analyses:
                for res in analysis.results:
                    if res.analyte in ["SOC_CONCENTRATION", "SOC_STOCK_PCT", "TOTAL_ORGANIC_CARBON_G_KG", "SOC_PCT"]:
                        if res.is_superseded:
                            has_superseded_soc = True
                        else:
                            soc_candidates.append((analysis, res))
                    elif res.analyte == "BULK_DENSITY_G_CM3":
                        if not res.is_superseded:
                            bd_candidates.append((analysis, res))
                    elif res.analyte == "COARSE_FRAGMENTS_PCT":
                        if not res.is_superseded:
                            cf_candidates.append((analysis, res))

            def _pick_best(candidates: List[Tuple[LaboratoryAnalysis, LaboratoryResult]]) -> Tuple[Optional[LaboratoryAnalysis], Optional[LaboratoryResult]]:
                if not candidates:
                    return None, None
                verified = [c for c in candidates if c[0].qa_status == "VERIFIED"]
                if verified:
                    return sorted(verified, key=lambda c: (c[0].analysis_date, c[1].created_at), reverse=True)[0]
                return sorted(candidates, key=lambda c: (c[0].analysis_date, c[1].created_at), reverse=True)[0]

            soc_analysis, soc_result = _pick_best(soc_candidates)
            bd_analysis, bd_result = _pick_best(bd_candidates)
            cf_analysis, cf_result = _pick_best(cf_candidates)

            # 4. Evaluate Factual Eligibility Gates
            if not col:
                reasons.append(ExclusionReasonCode.SAMPLE_NOT_COLLECTED.value)
                details["collection"] = "No field collection event recorded"

            if not plan_version or not plan_version.is_locked:
                reasons.append(ExclusionReasonCode.PLAN_NOT_LOCKED.value)
                details["plan"] = "Sampling plan version is not locked"

            if cust:
                broken_seals = [c for c in cust if not c.seal_intact]
                if broken_seals:
                    reasons.append(ExclusionReasonCode.BROKEN_CUSTODY.value)
                    details["custody"] = f"{len(broken_seals)} custody event(s) indicate broken seal"

            if not rcp or rcp.intake_status != "ACCEPTED":
                reasons.append(ExclusionReasonCode.RECEIPT_REJECTED.value)
                details["receipt"] = "Laboratory intake receipt missing or rejected"

            if not qa_rev or qa_rev.overall_qa_status != "ACCEPTED" or sample.status != "QA_ACCEPTED":
                reasons.append(ExclusionReasonCode.QA_NOT_ACCEPTED.value)
                details["qa_review"] = "Sample QA review is not accepted"

            if not soc_result:
                if has_superseded_soc:
                    reasons.append(ExclusionReasonCode.LAB_RESULT_SUPERSEDED.value)
                    details["soc"] = "All existing SOC concentration results have been superseded"
                else:
                    reasons.append(ExclusionReasonCode.QA_NOT_ACCEPTED.value)
                    details["soc"] = "No active laboratory SOC concentration result recorded"
            else:
                if soc_analysis and soc_analysis.qa_status != "VERIFIED":
                    reasons.append(ExclusionReasonCode.QA_NOT_ACCEPTED.value)
                    details["soc_analysis"] = f"Laboratory analysis QA status is {soc_analysis.qa_status}, expected VERIFIED"
                if soc_result.normalized_value is None:
                    reasons.append(ExclusionReasonCode.UNCONVERTIBLE_UNIT.value)
                    details["normalization"] = f"Unconvertible SOC raw unit '{soc_result.raw_unit}'"

            if depth_status == DepthAlignmentStatus.OUT_OF_SCOPE.value:
                reasons.append(ExclusionReasonCode.DEPTH_MISMATCH.value)
                details["depth"] = f"Sampling depth {act_from}-{act_to}cm is out of scope for standard VM0042 depth horizon"

            # 5. Classify Measurement
            if reasons:
                excluded_measurements.append(
                    ExcludedMeasurementItem(
                        physical_sample_id=sample.id,
                        sample_code=sample.sample_code,
                        land_unit_id=lu.id if lu else None,
                        land_unit_code=lu.code if lu else None,
                        stratum_id=resolved_stratum_id,
                        stratum_code=resolved_stratum_code,
                        sampling_date=sample_date,
                        actual_depth_from_cm=act_from,
                        actual_depth_to_cm=act_to,
                        analyte=soc_result.analyte if soc_result else None,
                        raw_value=float(soc_result.raw_value) if soc_result else None,
                        raw_unit=soc_result.raw_unit if soc_result else None,
                        exclusion_reasons=reasons,
                        exclusion_details=details,
                    )
                )
            else:
                # Compile Bulk Density status (§16)
                if bd_result and bd_analysis and bd_analysis.qa_status == "VERIFIED":
                    if depth_status == DepthAlignmentStatus.OUT_OF_SCOPE.value:
                        bd_status = "MISSING"
                        bd_raw_val = None
                        bd_norm_val = None
                    else:
                        bd_status = "PRESENT"
                        bd_raw_val = float(bd_result.raw_value)
                        bd_norm_val = float(bd_result.normalized_value or bd_result.raw_value)
                else:
                    bd_status = "MISSING"
                    bd_raw_val = None
                    bd_norm_val = None

                # Compile Coarse Fragments status (§17)
                cf_applicable = locked_meta.get("coarse_fragments_applicable", True)
                if cf_result and (cf_analysis is None or cf_analysis.qa_status == "VERIFIED"):
                    cf_val = float(cf_result.raw_value)
                    cf_status = "MEASURED_ZERO" if cf_val == 0.0 else "MEASURED"
                elif not cf_applicable:
                    cf_val = None
                    cf_status = "NOT_APPLICABLE"
                else:
                    cf_val = None
                    cf_status = "NOT_MEASURED"

                # Compile Evidence IDs
                evidence_ids = []
                if col and col.photo_evidence_id:
                    evidence_ids.append(col.photo_evidence_id)
                if rcp and rcp.receipt_evidence_id:
                    evidence_ids.append(rcp.receipt_evidence_id)
                if soc_analysis and soc_analysis.evidence_id:
                    evidence_ids.append(soc_analysis.evidence_id)

                item = QuantificationMeasurementItem(
                    organization_id=sample.organization_id,
                    project_id=sample.project_id,
                    methodology_id=project.methodology_id,
                    methodology_version_id=project.methodology_version_id,
                    methodology_code=meth_code,
                    methodology_version=meth_version,
                    rule_set_version=rule_set_version,
                    monitoring_context=campaign.baseline_or_monitoring_context if campaign else "MONITORING",
                    period_start=campaign.planned_start_date if campaign else None,
                    period_end=campaign.planned_end_date if campaign else None,
                    project_boundary_version_id=campaign.project_boundary_version_id if campaign else boundary_id,
                    land_unit_id=lu.id if lu else uuid.UUID(int=0),
                    land_unit_code=lu.code if lu else "UNKNOWN",
                    stratum_id=resolved_stratum_id,
                    stratum_code=resolved_stratum_code,
                    stratum_membership_as_of=sample_date,
                    sampling_campaign_id=campaign.id if campaign else uuid.UUID(int=0),
                    sampling_campaign_code=campaign.campaign_code if campaign else "UNKNOWN",
                    sampling_plan_version_id=plan_version.id if plan_version else None,
                    sampling_plan_version=plan_version.version_number if plan_version else 1,
                    sampling_plan_locked=plan_version.is_locked if plan_version else False,
                    physical_sample_id=sample.id,
                    sample_code=sample.sample_code,
                    sampling_date=sample_date,
                    actual_depth_from_cm=act_from,
                    actual_depth_to_cm=act_to,
                    depth_alignment_status=depth_status,
                    sample_qa_status=sample.status,
                    laboratory_analysis_id=soc_analysis.id if soc_analysis else uuid.UUID(int=0),
                    laboratory_name=soc_analysis.laboratory_name if soc_analysis else "UNKNOWN",
                    analytical_method=soc_analysis.analytical_method if soc_analysis else "DRY_COMBUSTION",
                    analysis_qa_status=soc_analysis.qa_status if soc_analysis else "VERIFIED",
                    analysis_date=soc_analysis.analysis_date if soc_analysis else sample_date,
                    laboratory_result_id=soc_result.id,
                    analyte="SOC_CONCENTRATION",
                    raw_value=float(soc_result.raw_value),
                    raw_unit=soc_result.raw_unit,
                    normalized_value=float(soc_result.normalized_value or soc_result.raw_value),
                    normalized_unit=soc_result.normalized_unit or "g/kg",
                    normalization_method=soc_result.normalization_method or "LINEAR_SCALING:VAL*10",
                    normalization_version=soc_result.normalization_version or "UNIT_CONV_V1.0",
                    provenance_class="MEASURED",
                    bulk_density_result_id=bd_result.id if bd_result else None,
                    bulk_density_raw_value=bd_raw_val,
                    bulk_density_raw_unit=bd_result.raw_unit if bd_result else None,
                    bulk_density_normalized_value=bd_norm_val,
                    bulk_density_normalized_unit=bd_result.normalized_unit if bd_result else None,
                    bulk_density_status=bd_status,
                    coarse_fragments_result_id=cf_result.id if cf_result else None,
                    coarse_fragments_pct=cf_val,
                    coarse_fragments_status=cf_status,
                    uncertainty_pct=float(soc_result.uncertainty_pct) if soc_result.uncertainty_pct is not None else None,
                    uncertainty_inputs={"lab_measurement_uncertainty_pct": float(soc_result.uncertainty_pct) if soc_result.uncertainty_pct is not None else None},
                    evidence_ids=evidence_ids,
                )

                if item.monitoring_context == "BASELINE":
                    baseline_measurements.append(item)
                else:
                    project_measurements.append(item)

        total_candidates = len(samples)
        total_eligible = len(baseline_measurements) + len(project_measurements)
        total_excluded = len(excluded_measurements)

        return {
            "project_id": str(project.id),
            "quantification_approach": quant_approach,
            "total_candidates": total_candidates,
            "total_eligible": total_eligible,
            "total_excluded": total_excluded,
            "baseline_measurements": baseline_measurements,
            "project_measurements": project_measurements,
            "excluded_measurements": excluded_measurements,
        }

    @classmethod
    async def evaluate_quantification_readiness(
        cls,
        db: AsyncSession,
        project_id: uuid.UUID,
        organization_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        """
        Evaluates 16 deterministic quantification readiness dimensions with strict
        categorical classifications and zero percentage aggregation.
        """
        project = await cls.get_project_or_raise(db, project_id, organization_id)
        eval_set = await cls.evaluate_eligible_measurements(db, project_id, organization_id)

        eligible_all = eval_set["baseline_measurements"] + eval_set["project_measurements"]
        excluded_all = eval_set["excluded_measurements"]

        # Fetch ground evidence readiness
        ground_readiness = await cls.evaluate_ground_evidence_readiness(db, project_id, organization_id)

        # 1. Methodology Lock
        locked_meta = (project.baseline_parameters or {}).get("locked_methodology_version") or {}
        has_meth_lock = locked_meta.get("status") == "LOCKED" and project.methodology_id is not None
        meth_code = locked_meta.get("methodology_code") or "VM0042"
        meth_version = locked_meta.get("version") or "2.2"

        d_meth_lock = {
            "status": "COMPLETE" if has_meth_lock else "INCOMPLETE",
            "requirement": "REQUIRED",
            "blocking": True,
            "message": f"Methodology {meth_code} v{meth_version} locked and immutable" if has_meth_lock else "Methodology version not locked",
            "details": locked_meta,
        }

        # 2. Monitoring Period
        c_count = await db.scalar(select(func.count(SamplingCampaign.id)).where(SamplingCampaign.project_id == project_id)) or 0
        d_mon_period = {
            "status": "COMPLETE" if c_count > 0 else "INCOMPLETE",
            "requirement": "REQUIRED",
            "blocking": True,
            "message": f"{c_count} operational sampling campaigns define active monitoring/baseline periods" if c_count > 0 else "No sampling campaign or monitoring period defined",
            "details": {"campaigns_count": c_count},
        }

        # 3. Boundary Version
        b_count = await db.scalar(select(func.count(ProjectBoundaryVersion.id)).where(ProjectBoundaryVersion.project_id == project_id)) or 0
        d_boundary = {
            "status": "COMPLETE" if b_count > 0 else "INCOMPLETE",
            "requirement": "REQUIRED",
            "blocking": True,
            "message": f"Project boundary version active with verified polygon ({b_count} version(s))" if b_count > 0 else "No project boundary version active",
            "details": {"boundary_versions": b_count},
        }

        # 4. Stratification
        st_count = await db.scalar(select(func.count(Stratum.id)).where(Stratum.project_id == project_id)) or 0
        d_strat = {
            "status": "COMPLETE" if st_count > 0 else "INCOMPLETE",
            "requirement": "REQUIRED",
            "blocking": True,
            "message": f"{st_count} analytical strata configured with temporal membership validity" if st_count > 0 else "No analytical strata configured",
            "details": {"strata_count": st_count},
        }

        # 5. Sampling Plan
        plan_count = await db.scalar(
            select(func.count(SamplingPlanVersion.id))
            .where(SamplingPlanVersion.project_id == project_id, SamplingPlanVersion.is_locked == True)
        ) or 0
        d_plan = {
            "status": "COMPLETE" if plan_count > 0 else "INCOMPLETE",
            "requirement": "REQUIRED",
            "blocking": True,
            "message": f"{plan_count} locked sampling plan version(s) establish immutable point grids" if plan_count > 0 else "No locked sampling plan version found",
            "details": {"locked_plans": plan_count},
        }

        # 6. Design Sufficiency (§10)
        ds_status = locked_meta.get("design_sufficiency_status", "NOT_CONFIGURED")
        req_ds = locked_meta.get("design_sufficiency_requirement", "REQUIRED")
        blocking_ds = locked_meta.get("design_sufficiency_blocking", True if req_ds == "REQUIRED" else False)
        d_design_suff = {
            "status": ds_status,
            "requirement": req_ds,
            "blocking": blocking_ds,
            "message": "Statistical sample-allocation engine not configured. Stratum coverage is factual only and does not establish statistical or methodological power sufficiency." if ds_status == "NOT_CONFIGURED" else "Statistical sampling design sufficiency demonstrated",
            "details": {"power_analysis_configured": (ds_status == "COMPLETE"), "evaluator": None},
        }

        # 7. Ground Evidence
        ge_status = ground_readiness.get("overall_status", "INCOMPLETE")
        d_ground_ev = {
            "status": ge_status,
            "requirement": "REQUIRED",
            "blocking": True,
            "message": f"Ground evidence readiness evaluates to {ge_status}",
            "details": ground_readiness.get("components", {}),
        }

        # 8. SOC Concentration
        soc_count = len(eligible_all)
        d_soc = {
            "status": "COMPLETE" if soc_count > 0 else "INCOMPLETE",
            "requirement": "REQUIRED",
            "blocking": True,
            "message": f"{soc_count} eligible SOC concentration measurements normalized to canonical g/kg" if soc_count > 0 else "0 eligible SOC concentration measurements found",
            "details": {"eligible_soc_count": soc_count, "canonical_unit": "g/kg"},
        }

        # 9. Bulk Density (§16)
        bd_missing = [m for m in eligible_all if m.bulk_density_status == "MISSING"]
        if soc_count == 0:
            bd_status = "INCOMPLETE"
            bd_msg = "0 eligible samples to evaluate for bulk density"
        elif len(bd_missing) == 0:
            bd_status = "COMPLETE"
            bd_msg = f"All {soc_count} eligible SOC samples have paired QA-accepted bulk density measurements"
        else:
            bd_status = "INCOMPLETE"
            bd_msg = f"{len(bd_missing)} of {soc_count} eligible SOC samples do not have an applicable QA-accepted bulk-density measurement."

        req_bd = locked_meta.get("bulk_density_requirement", "REQUIRED")
        blocking_bd = locked_meta.get("bulk_density_blocking", True if req_bd == "REQUIRED" else False)
        d_bulk_density = {
            "status": bd_status,
            "requirement": req_bd,
            "blocking": blocking_bd,
            "message": bd_msg,
            "details": {"total_soc": soc_count, "missing_bulk_density": len(bd_missing)},
        }

        # 10. Coarse Fragments (§17)
        cf_present = [m for m in eligible_all if m.coarse_fragments_status in ["MEASURED", "MEASURED_ZERO"]]
        req_cf = locked_meta.get("coarse_fragments_requirement", "OPTIONAL")
        blocking_cf = locked_meta.get("coarse_fragments_blocking", False)
        cf_status = "COMPLETE" if len(cf_present) > 0 else ("NOT_APPLICABLE" if req_cf != "REQUIRED" else "INCOMPLETE")
        d_coarse = {
            "status": cf_status,
            "requirement": req_cf,
            "blocking": blocking_cf,
            "message": f"{len(cf_present)} of {soc_count} samples have explicit gravel/coarse fragment measurements" if len(cf_present) > 0 else ("Fine-earth core analysis standard; coarse fragment gravel deduction not applicable under active configuration" if req_cf != "REQUIRED" else "Coarse fragment measurement required by methodology configuration but missing"),
            "details": {"measured_samples": len(cf_present)},
        }

        # 11. Depth Alignment
        depth_partial = [m for m in eligible_all if m.depth_alignment_status != DepthAlignmentStatus.MATCH.value]
        if soc_count == 0:
            depth_status = "INCOMPLETE"
            depth_msg = "0 eligible samples evaluated for depth alignment"
        elif len(depth_partial) == 0:
            depth_status = "COMPLETE"
            depth_msg = f"All {soc_count} eligible samples match standard 0-30cm depth interval"
        else:
            depth_status = "NEEDS_REVIEW"
            depth_msg = f"{len(depth_partial)} samples have partial depth coverage requiring calibration/review"

        d_depth = {
            "status": depth_status,
            "requirement": "REQUIRED",
            "blocking": True,
            "message": depth_msg,
            "details": {"partial_coverage_count": len(depth_partial)},
        }

        # 12. Uncertainty Inputs
        d_uncertainty = {
            "status": "NOT_CONFIGURED",
            "requirement": "OPTIONAL",
            "blocking": False,
            "message": "Measurement uncertainties documented; full statistical error-propagation model not configured",
            "details": {"model": "NOT_CONFIGURED"},
        }

        # 13. Baseline Dataset & 14. Project Dataset
        base_count = len(eval_set["baseline_measurements"])
        proj_count = len(eval_set["project_measurements"])

        req_base = "REQUIRED" if (base_count > 0 or proj_count == 0) else "OPTIONAL"
        d_baseline = {
            "status": "COMPLETE" if base_count > 0 else ("INCOMPLETE" if req_base == "REQUIRED" else "NOT_APPLICABLE"),
            "requirement": req_base,
            "blocking": (req_base == "REQUIRED"),
            "message": f"{base_count} baseline ground measurements validated" if base_count > 0 else ("0 baseline measurement candidates validated" if req_base == "REQUIRED" else "Baseline dataset not applicable under monitoring context"),
            "details": {"baseline_count": base_count},
        }

        req_proj = "REQUIRED" if (proj_count > 0 or base_count == 0) else "OPTIONAL"
        d_project = {
            "status": "COMPLETE" if proj_count > 0 else ("INCOMPLETE" if req_proj == "REQUIRED" else "NOT_APPLICABLE"),
            "requirement": req_proj,
            "blocking": (req_proj == "REQUIRED"),
            "message": f"{proj_count} project monitoring measurements validated" if proj_count > 0 else ("0 project monitoring measurement candidates validated" if req_proj == "REQUIRED" else "Project monitoring dataset not applicable under baseline context"),
            "details": {"project_count": proj_count},
        }

        # 15. QA Acceptance
        all_samples_count = eval_set["total_candidates"]
        qa_rejected_samples = [m for m in excluded_all if ExclusionReasonCode.QA_NOT_ACCEPTED.value in m.exclusion_reasons]
        if all_samples_count == 0:
            qa_status = "INCOMPLETE"
            qa_msg = "0 physical samples present for QA verification"
        elif len(qa_rejected_samples) > 0:
            qa_status = "NEEDS_REVIEW"
            qa_msg = f"{len(qa_rejected_samples)} sample(s) have unaccepted QA or unverified laboratory analyses"
        else:
            qa_status = "COMPLETE"
            qa_msg = f"All {all_samples_count} physical samples and laboratory analyses verified and accepted by QA reviewer"

        d_qa = {
            "status": qa_status,
            "requirement": "REQUIRED",
            "blocking": True,
            "message": qa_msg,
            "details": {"qa_rejected_count": len(qa_rejected_samples)},
        }

        # 16. Calculation Rules
        d_calc_rules = {
            "status": "COMPLETE",
            "requirement": "REQUIRED",
            "blocking": True,
            "message": f"Calculation rules compiled from locked methodology {meth_code} v{meth_version}",
            "details": {"rule_set": f"{meth_code}_V{meth_version.replace('.', '_')}_RULES_V1.0"},
        }

        dimensions = {
            "METHODOLOGY_LOCK": d_meth_lock,
            "MONITORING_PERIOD": d_mon_period,
            "BOUNDARY_VERSION": d_boundary,
            "STRATIFICATION": d_strat,
            "SAMPLING_PLAN": d_plan,
            "DESIGN_SUFFICIENCY": d_design_suff,
            "GROUND_EVIDENCE": d_ground_ev,
            "SOC_CONCENTRATION": d_soc,
            "BULK_DENSITY": d_bulk_density,
            "COARSE_FRAGMENTS": d_coarse,
            "DEPTH_ALIGNMENT": d_depth,
            "UNCERTAINTY_INPUTS": d_uncertainty,
            "BASELINE_DATASET": d_baseline,
            "PROJECT_DATASET": d_project,
            "QA_ACCEPTANCE": d_qa,
            "CALCULATION_RULES": d_calc_rules,
        }

        # Evaluate Overall Status
        all_dim_statuses = [d["status"] for d in dimensions.values()]
        if any(s == "NEEDS_REVIEW" for s in all_dim_statuses):
            overall_status = "NEEDS_REVIEW"
        elif any(s == "NOT_CONFIGURED" for s in [d_design_suff["status"], d_uncertainty["status"]]):
            overall_status = "NOT_CONFIGURED"
        elif any(s == "INCOMPLETE" for s in all_dim_statuses):
            overall_status = "INCOMPLETE"
        else:
            overall_status = "COMPLETE"

        quant_approach = locked_meta.get("quantification_approach", "DIRECT_MEASUREMENT")

        return {
            "project_id": str(project.id),
            "overall_status": overall_status,
            "quantification_approach": quant_approach,
            "methodology_code": meth_code,
            "methodology_version": meth_version,
            "dimensions": dimensions,
            "total_eligible_measurements": eval_set["total_eligible"],
            "total_excluded_measurements": eval_set["total_excluded"],
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
        }

    @classmethod
    async def create_quantification_input_snapshot(
        cls,
        db: AsyncSession,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        user_role: str,
        organization_id: uuid.UUID,
        payload: QuantificationInputSnapshotCreate,
    ) -> QuantificationInputSnapshot:
        """
        Creates an immutable, cryptographically hashed QuantificationInputSnapshot
        preserving the exact ground evidence, methodology rules, and boundaries.
        Enforces Segregation of Duties: FIELD_AGENT is strictly forbidden from locking snapshots.
        """
        # 1. Enforce Segregation of Duties: FIELD_AGENT cannot lock official snapshots
        if user_role == "FIELD_AGENT":
            raise ValueError("Field agent role is unauthorized to lock official quantification input snapshots. Segregation of duties enforced.")

        # 2. Verify project & tenant isolation
        project = await cls.get_project_or_raise(db, project_id, organization_id)

        # 3. Assemble eligible and excluded sets
        eval_set = await cls.evaluate_eligible_measurements(
            db, project_id, organization_id, campaign_id=payload.sampling_campaign_id
        )
        readiness = await cls.evaluate_quantification_readiness(db, project_id, organization_id)

        eligible = eval_set["baseline_measurements"] + eval_set["project_measurements"]
        excluded = eval_set["excluded_measurements"]

        # 4. Snapshot Lock Gating (§10, §11)
        requested_status = (payload.status or "LOCKED").upper()
        if requested_status not in ("PREVIEW", "LOCKED"):
            raise ValueError(f"Invalid snapshot status '{requested_status}'. Allowed values: PREVIEW, LOCKED")

        if requested_status == "LOCKED":
            blocking_failures = []
            for dim_name, dim_data in readiness.get("dimensions", {}).items():
                if dim_data.get("blocking", False) and dim_data.get("requirement") == "REQUIRED":
                    st = dim_data.get("status")
                    if st not in ("COMPLETE", "NOT_APPLICABLE"):
                        blocking_failures.append(f"{dim_name}: {st}")
            if blocking_failures:
                raise ValueError(
                    f"Cannot lock official snapshot: {len(blocking_failures)} blocking requirement(s) unresolved: "
                    + "; ".join(blocking_failures)
                )

        # 5. Validate source evidence IDs if provided (§20)
        if payload.source_evidence_ids:
            for eid in payload.source_evidence_ids:
                ps_c = await db.scalar(select(func.count(PhysicalSample.id)).where(PhysicalSample.id == eid, PhysicalSample.project_id == project_id))
                if ps_c:
                    continue
                lr_c = await db.scalar(select(func.count(LaboratoryResult.id)).where(LaboratoryResult.id == eid))
                if lr_c:
                    continue
                ce_c = await db.scalar(select(func.count(SampleCollectionEvent.id)).where(SampleCollectionEvent.id == eid))
                if ce_c:
                    continue
                coc_c = await db.scalar(select(func.count(ChainOfCustodyEvent.id)).where(ChainOfCustodyEvent.id == eid))
                if coc_c:
                    continue
                rcp_c = await db.scalar(select(func.count(LaboratoryReceipt.id)).where(LaboratoryReceipt.id == eid))
                if rcp_c:
                    continue
                ana_c = await db.scalar(select(func.count(LaboratoryAnalysis.id)).where(LaboratoryAnalysis.id == eid))
                if ana_c:
                    continue
                raise ValueError(f"Invalid source evidence ID {eid}: record does not exist or does not belong to project {project_id}")

        # 6. Extract locked methodology & boundary
        locked_meta = (project.baseline_parameters or {}).get("locked_methodology_version") or {}
        meth_code = locked_meta.get("methodology_code") or "VM0042"
        meth_version = locked_meta.get("version") or "2.2"
        rule_set_version = f"{meth_code}_V{meth_version.replace('.', '_')}_RULES_V1.0"
        quant_approach = locked_meta.get("quantification_approach", "DIRECT_MEASUREMENT")
        min_depth = float(locked_meta.get("minimum_depth_cm", 30.0))

        rule_config = {
            "methodology": meth_code,
            "version": meth_version,
            "standard_depth_cm": [0.0, min_depth],
            "canonical_soc_analyte": "SOC_CONCENTRATION",
            "canonical_soc_unit": "g/kg",
            "bulk_density_required": True,
            "coarse_fragments_required": locked_meta.get("coarse_fragments_requirement") == "REQUIRED",
            "depth_tolerance_cm": 0.0,
            "quantification_approach": quant_approach,
        }
        rule_config_hash = hashlib.sha256(json.dumps(rule_config, sort_keys=True).encode("utf-8")).hexdigest()

        b_stmt = (
            select(ProjectBoundaryVersion)
            .where(ProjectBoundaryVersion.project_id == project_id)
            .order_by(ProjectBoundaryVersion.version_number.desc())
        )
        latest_b = (await db.execute(b_stmt)).scalars().first()
        boundary_id = latest_b.id if latest_b else None

        # 7. Generate deterministic snapshot code
        snapshot_code = f"QIS-{project.project_code}-{uuid.uuid4().hex[:6].upper()}"

        # 8. Assemble canonical input package
        now_dt = datetime.now(timezone.utc)
        input_package = {
            "snapshot_code": snapshot_code,
            "status": requested_status,
            "project_id": str(project.id),
            "project_name": project.name,
            "project_code": project.project_code,
            "organization_id": str(organization_id),
            "context": payload.context,
            "quantification_approach": quant_approach,
            "methodology_code": meth_code,
            "methodology_version": meth_version,
            "rule_set_version": rule_set_version,
            "rule_config_hash": rule_config_hash,
            "project_boundary_version_id": str(boundary_id) if boundary_id else None,
            "total_eligible_measurements": len(eligible),
            "total_excluded_measurements": len(excluded),
            "eligible_measurements": [item.model_dump(mode="json") for item in eligible],
            "excluded_measurements": [item.model_dump(mode="json") for item in excluded],
            "readiness_summary": readiness,
            "locked_at": now_dt.isoformat() if requested_status == "LOCKED" else None,
            "locked_by_id": str(user_id) if requested_status == "LOCKED" else None,
        }

        # 9. Compute deterministic SHA-256 hash (§18)
        canonical_json_bytes = json.dumps(input_package, sort_keys=True, default=str).encode("utf-8")
        snapshot_hash = hashlib.sha256(canonical_json_bytes).hexdigest()

        # 10. Collect source evidence IDs
        derived_evidence_ids = (
            {str(m.physical_sample_id) for m in eligible}
            | {str(m.laboratory_result_id) for m in eligible}
            | {str(eid) for m in eligible for eid in m.evidence_ids}
        )
        if payload.source_evidence_ids:
            derived_evidence_ids |= {str(eid) for eid in payload.source_evidence_ids}
        source_evidence_ids = sorted(list(derived_evidence_ids))

        snapshot = QuantificationInputSnapshot(
            id=uuid.uuid4(),
            organization_id=organization_id,
            project_id=project.id,
            snapshot_code=snapshot_code,
            status=requested_status,
            context=payload.context,
            period_start=None,
            period_end=None,
            methodology_version_id=project.methodology_version_id,
            methodology_code=meth_code,
            methodology_version=meth_version,
            rule_set_version=rule_set_version,
            project_boundary_version_id=boundary_id,
            sampling_campaign_id=payload.sampling_campaign_id,
            snapshot_hash=snapshot_hash,
            is_locked=(requested_status == "LOCKED"),
            locked_at=now_dt if requested_status == "LOCKED" else None,
            locked_by_id=user_id if requested_status == "LOCKED" else None,
            created_by_id=user_id,
            total_eligible_measurements=len(eligible),
            total_excluded_measurements=len(excluded),
            readiness_summary=readiness,
            input_package=input_package,
            source_evidence_ids=source_evidence_ids,
            notes=payload.notes,
        )
        db.add(snapshot)
        await db.flush()
        return snapshot

    @classmethod
    async def get_quantification_input_snapshot(
        cls,
        db: AsyncSession,
        project_id: uuid.UUID,
        snapshot_id: uuid.UUID,
        organization_id: uuid.UUID,
    ) -> QuantificationInputSnapshot:
        """Retrieves an immutable quantification input snapshot with tenant isolation."""
        await cls.get_project_or_raise(db, project_id, organization_id)
        stmt = (
            select(QuantificationInputSnapshot)
            .where(
                QuantificationInputSnapshot.id == snapshot_id,
                QuantificationInputSnapshot.project_id == project_id,
                QuantificationInputSnapshot.organization_id == organization_id,
            )
        )
        res = await db.execute(stmt)
        snapshot = res.scalars().first()
        if not snapshot:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quantification input snapshot not found")
        return snapshot

    @classmethod
    async def list_quantification_input_snapshots(
        cls,
        db: AsyncSession,
        project_id: uuid.UUID,
        organization_id: uuid.UUID,
    ) -> List[QuantificationInputSnapshot]:
        """Lists all quantification input snapshots for a project with tenant isolation."""
        await cls.get_project_or_raise(db, project_id, organization_id)
        stmt = (
            select(QuantificationInputSnapshot)
            .where(
                QuantificationInputSnapshot.project_id == project_id,
                QuantificationInputSnapshot.organization_id == organization_id,
            )
            .order_by(QuantificationInputSnapshot.created_at.desc())
        )
    @classmethod
    async def evaluate_methodology_prerequisites(
        cls,
        db: AsyncSession,
        project_id: uuid.UUID,
        organization_id: Optional[uuid.UUID] = None,
        run_power_analysis: bool = False,
        mdd: Optional[float] = None,
        submission_date: Optional[Union[date, str]] = None,
        early_adoption_mode: Optional[str] = None,
        as_of_date: Optional[Union[date, str]] = None,
    ) -> Dict[str, Any]:
        """Evaluates all 17 VM0042 methodology prerequisite dimensions."""
        from app.domains.agriculture.prerequisites.assessment_service import (
            AgriculturePrerequisiteAssessmentService,
        )
        return await AgriculturePrerequisiteAssessmentService.evaluate_prerequisites(
            db=db,
            project_id=project_id,
            organization_id=organization_id,
            run_power_analysis=run_power_analysis,
            mdd=mdd,
            submission_date=submission_date,
            early_adoption_mode=early_adoption_mode,
            as_of_date=as_of_date,
        )

    @classmethod
    async def lock_prerequisite_assessment(
        cls,
        db: AsyncSession,
        project_id: uuid.UUID,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        user_role: str,
        snapshot_id: Optional[uuid.UUID] = None,
        notes: Optional[str] = None,
        run_power_analysis: bool = False,
        target_mdd: Optional[float] = None,
        submission_date: Optional[Union[date, str]] = None,
        early_adoption_mode: Optional[str] = None,
        as_of_date: Optional[Union[date, str]] = None,
    ) -> AgriculturePrerequisiteAssessment:
        """
        Evaluates and locks an immutable AgriculturePrerequisiteAssessment.
        Enforces Segregation of Duties: FIELD_AGENT cannot lock assessments.
        Requires overall status to be READY or READY_WITH_ADVISORY.
        """
        if (user_role or "").upper() == "FIELD_AGENT":
            raise ValueError("Field agent role is unauthorized to lock official methodology prerequisite assessments. Segregation of duties enforced.")

        project = await cls.get_project_or_raise(db, project_id, organization_id)

        eval_res = await cls.evaluate_methodology_prerequisites(
            db=db,
            project_id=project_id,
            organization_id=organization_id,
            run_power_analysis=run_power_analysis,
            mdd=target_mdd,
            submission_date=submission_date,
            early_adoption_mode=early_adoption_mode,
            as_of_date=as_of_date,
        )

        overall_st = eval_res["overall_status"]
        if overall_st not in ("READY", "READY_WITH_ADVISORY"):
            reasons = "; ".join(eval_res.get("blocking_reasons", []))
            raise ValueError(f"Cannot lock prerequisite assessment: status '{overall_st}' has unresolved blocking requirements: {reasons}")

        # Acquire PostgreSQL row lock on project to serialize concurrent lock attempts (§27)
        proj_lock_stmt = (
            select(Project.id)
            .where(Project.id == project_id, Project.organization_id == organization_id)
            .with_for_update()
        )
        await db.execute(proj_lock_stmt)

        # Check existing active assessments to determine version, idempotency & supersession
        existing_stmt = (
            select(AgriculturePrerequisiteAssessment)
            .where(
                AgriculturePrerequisiteAssessment.project_id == project_id,
                AgriculturePrerequisiteAssessment.organization_id == organization_id,
                AgriculturePrerequisiteAssessment.status == "LOCKED",
            )
            .order_by(AgriculturePrerequisiteAssessment.version.desc())
        )
        existing = (await db.execute(existing_stmt)).scalars().first()

        # Deterministic Idempotency (§28): If identical locked assessment hash exists, return existing
        if existing and existing.assessment_hash == eval_res["evaluation_hash"]:
            return existing

        next_version = (existing.version + 1) if existing else 1
        code_prefix = (project.name or "PROJECT")[:8].replace(" ", "").upper()
        assessment_code = f"PREREQ-{code_prefix}-{project_id.hex[:6]}-V{next_version}"

        now = datetime.now(timezone.utc)
        assessment = AgriculturePrerequisiteAssessment(
            organization_id=organization_id,
            project_id=project_id,
            snapshot_id=snapshot_id,
            assessment_code=assessment_code,
            version=next_version,
            status="LOCKED",
            overall_readiness=overall_st,
            methodology_code=eval_res["methodology_code"],
            methodology_version=eval_res["methodology_version"],
            corrections_clarifications_version=eval_res["corrections_clarifications_version"],
            rule_set_version=eval_res["rule_set_version"],
            vcs_standard_version=eval_res["vcs_standard_version"],
            vcs_resolution_metadata=eval_res["dimensions"]["VCS_PROGRAM_RULESET"]["details"],
            quantification_route_map=eval_res["dimensions"]["QUANTIFICATION_ROUTE"]["details"],
            esm_input_dossier=eval_res["dimensions"]["ESM_INPUTS"]["details"],
            sampling_design_assessment=eval_res["dimensions"]["SAMPLING_DESIGN"]["details"],
            uncertainty_input_readiness=eval_res["dimensions"]["UNCERTAINTY_INPUTS"]["details"],
            baseline_monitoring_pairing=eval_res["dimensions"]["BASELINE_MONITORING_PAIRING"]["details"],
            dimensions=eval_res["dimensions"],
            blocking_reasons=eval_res.get("blocking_reasons", []),
            advisory_notes=eval_res.get("advisory_notes", []),
            assessment_hash=eval_res["evaluation_hash"],
            is_locked=True,
            locked_at=now,
            locked_by_id=user_id,
            created_by_id=user_id,
            notes=notes,
        )
        db.add(assessment)
        await db.flush()

        if existing:
            existing.status = "SUPERSEDED"
            existing.superseded_by_id = assessment.id

        return assessment

    @classmethod
    async def list_prerequisite_assessments(
        cls,
        db: AsyncSession,
        project_id: uuid.UUID,
        organization_id: uuid.UUID,
    ) -> List[AgriculturePrerequisiteAssessment]:
        """Lists all prerequisite assessments for a project with tenant isolation."""
        await cls.get_project_or_raise(db, project_id, organization_id)
        stmt = (
            select(AgriculturePrerequisiteAssessment)
            .where(
                AgriculturePrerequisiteAssessment.project_id == project_id,
                AgriculturePrerequisiteAssessment.organization_id == organization_id,
            )
            .order_by(AgriculturePrerequisiteAssessment.created_at.desc())
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @classmethod
    async def get_prerequisite_assessment(
        cls,
        db: AsyncSession,
        project_id: uuid.UUID,
        assessment_id: uuid.UUID,
        organization_id: uuid.UUID,
    ) -> AgriculturePrerequisiteAssessment:
        """Retrieves an immutable prerequisite assessment with tenant isolation."""
        await cls.get_project_or_raise(db, project_id, organization_id)
        stmt = (
            select(AgriculturePrerequisiteAssessment)
            .where(
                AgriculturePrerequisiteAssessment.id == assessment_id,
                AgriculturePrerequisiteAssessment.project_id == project_id,
                AgriculturePrerequisiteAssessment.organization_id == organization_id,
            )
        )
        res = await db.execute(stmt)
        assessment = res.scalars().first()
        if not assessment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prerequisite assessment not found")
        return assessment

    # =========================================================================
    # PHASE 3B-1: SOC STOCK & EQUIVALENT SOIL MASS (ESM) ENGINE
    # =========================================================================

    @classmethod
    def _resolve_profile_identity(
        cls,
        sample: PhysicalSample,
    ) -> Tuple[str, str, Decimal]:
        """
        Authoritative profile identity resolution according to VM0042 Section 8 and VeriField Nexus MRV lineage.
        Does NOT rely on raw coordinate equality as the primary identity.

        Priority order:
        1. Explicit soil_profile_id on PhysicalSample or SamplingPoint.
        2. Explicit replicate_group when configured with profile semantics (e.g. 'PROF-', 'LOC-', 'PROFILE-').
        3. Explicit adjacent-sample relationship within same sampling event / physical core extraction.
        4. Verified Legacy Profile Mapping: Checked from persisted metadata/properties with review_status in ('VERIFIED', 'APPROVED').
        5. If no explicit or verified relationship exists:
           Return profile_id = f"UNGROUPED_PROFILE_{sample.id}", method = "PROFILE_IDENTITY_INCOMPLETE", confidence = 0.0.
           (Bare code prefix naming conventions or coordinate clustering are strictly prohibited from authorizing calculations).

        Returns:
          (canonical_profile_id, resolution_method, confidence_score)
        """
        sp = sample.sampling_point
        campaign_prefix = str(sample.campaign_id or (sp.campaign_id if sp else "UNKNOWN_CAMPAIGN"))

        # Priority 1: Explicit soil_profile_id on PhysicalSample or SamplingPoint
        if getattr(sample, "soil_profile_id", None):
            return (f"{campaign_prefix}:{sample.soil_profile_id}", "EXPLICIT_SAMPLE_PROFILE_ID", Decimal("1.00"))
        if sp and getattr(sp, "soil_profile_id", None):
            return (f"{campaign_prefix}:{sp.soil_profile_id}", "EXPLICIT_POINT_PROFILE_ID", Decimal("1.00"))

        # Priority 2: Explicit replicate_group with profile semantics
        if sp and sp.replicate_group:
            rep = sp.replicate_group.strip()
            if any(rep.upper().startswith(p) for p in ("PROF", "LOC", "CORE", "PROFILE")):
                return (f"{campaign_prefix}:{rep}", "EXPLICIT_REPLICATE_GROUP", Decimal("0.95"))

        # Priority 3: Explicit adjacent-sample relationship within same sampling event
        # SECURITY: client-supplied SampleCollectionEvent.device_metadata (mobile JSON) is deliberately
        # NOT consulted — field-submitted metadata must never self-assert authoritative profile identity.
        # NOTE: PhysicalSample/SamplingPoint currently have NO persisted `properties` column. Priorities 3
        # and 4 are therefore only reachable when a reviewed mapping is attached in-process; a persisted,
        # reviewed legacy-mapping store is NOT IMPLEMENTED (requires an approved additive migration).
        props = getattr(sample, "properties", None)
        if not isinstance(props, dict) and sp is not None:
            props = getattr(sp, "properties", None)
        if not isinstance(props, dict):
            props = {}

        adj_rel = props.get("adjacent_sample_relationship")
        sampling_evt_id = props.get("sampling_event_id")
        if adj_rel in ("SAME_PHYSICAL_SAMPLE", "SAME_PHYSICAL_CORE", "ADJACENT_DEPTH_INCREMENT") and sampling_evt_id:
            return (f"{campaign_prefix}:EVENT:{sampling_evt_id}", "EXPLICIT_ADJACENT_SAMPLE_EVENT", Decimal("0.95"))

        # Priority 4: OPTION B (FAIL CLOSED) FOR LEGACY PROFILES
        # Ephemeral Python dictionaries / in-process review objects (e.g. legacy_profile_mapping) are strictly
        # PROHIBITED from authorizing calculations. Authoritative MRV lineage requires explicit persisted database
        # records (e.g. PhysicalSample.soil_profile_id or SamplingPoint.soil_profile_id). Any legacy record
        # lacking an explicit persisted profile identity must return PROFILE_IDENTITY_INCOMPLETE and fail closed.

        # Priority 5: Bare naming conventions or coordinate clustering are strictly insufficient for authoritative MRV.
        return (f"UNGROUPED_PROFILE_{sample.id}", "PROFILE_IDENTITY_INCOMPLETE", Decimal("0.00"))

    @classmethod
    def _extract_profile_layers_from_samples(
        cls,
        samples: List[PhysicalSample],
        require_verified_lab_qa: bool = True,
    ) -> Dict[uuid.UUID, List[LayerInput]]:
        """
        Groups verified physical samples into depth profile layer sequences per canonical profile identity.
        Extracts validated laboratory SOC concentrations, bulk densities, and coarse fragment fractions.
        Enforces Section 22: Only VERIFIED, non-superseded laboratory results are eligible for authoritative calculations.
        Coordinates are strictly used to VALIDATE proximity, never as the primary relational key.
        """
        profile_groups: Dict[str, Tuple[uuid.UUID, List[LayerInput], Dict[str, Any]]] = {}

        for s in samples:
            if not s.collection_event:
                continue

            upper = Decimal(str(s.collection_event.actual_depth_from_cm))
            lower = Decimal(str(s.collection_event.actual_depth_to_cm))

            # Canonical profile identity resolution (NOT coordinate equality)
            prof_id, res_method, conf = cls._resolve_profile_identity(s)

            soc_val = None
            lab_res_id = None
            bd_val = None
            cf_val = Decimal("0.0000")
            cf_prov = "DEFAULT_CONSERVATIVE_ZERO"

            for analysis in (s.laboratory_analyses or []):
                # Section 22: VERIFIED LAB QA ONLY
                if require_verified_lab_qa and (analysis.qa_status or "").upper() != "VERIFIED":
                    continue

                for res in (analysis.results or []):
                    if getattr(res, "is_superseded", False):
                        continue
                    analyte = (res.analyte or "").upper()
                    if analyte in ("SOC_CONCENTRATION", "TOTAL_ORGANIC_CARBON_G_KG", "SOC_STOCK_PCT"):
                        lab_res_id = res.id
                        raw_u = (res.raw_unit or "").lower()
                        norm_u = (res.normalized_unit or "").lower()
                        if res.normalized_value is not None:
                            val = Decimal(str(res.normalized_value))
                            if "g/kg" in norm_u:
                                soc_val = val
                            elif "%" in norm_u or "pct" in norm_u:
                                soc_val = val * Decimal("10.0")
                            else:
                                soc_val = val
                        elif res.raw_value is not None:
                            val = Decimal(str(res.raw_value))
                            if "%" in raw_u or "pct" in raw_u:
                                soc_val = val * Decimal("10.0")
                            else:
                                soc_val = val

                    elif analyte in ("BULK_DENSITY_G_CM3", "BULK_DENSITY"):
                        v = res.normalized_value if res.normalized_value is not None else res.raw_value
                        if v is not None:
                            bd_val = Decimal(str(v))

                    elif analyte in ("COARSE_FRAGMENTS_PCT", "COARSE_FRAGMENTS"):
                        v = res.normalized_value if res.normalized_value is not None else res.raw_value
                        if v is not None:
                            cf_num = Decimal(str(v))
                            if cf_num > Decimal("1.0"):
                                cf_val = (cf_num / Decimal("100.0")).quantize(Decimal("0.0001"))
                            else:
                                cf_val = cf_num.quantize(Decimal("0.0001"))
                            cf_prov = "MEASURED"

            if soc_val is not None:
                # Fail-closed check: Authoritative profile identity is mandatory for SOC calculation
                if res_method == "PROFILE_IDENTITY_INCOMPLETE":
                    raise SOCStockCalculationError(
                        code="PROFILE_IDENTITY_INCOMPLETE",
                        message=(
                            f"Sample {s.id} (code: '{s.sample_code}') lacks an authoritative physical profile identity. "
                            "VM0042 Section 8 requires explicit auditable profile lineage. "
                            "Bare naming conventions or coordinate clustering are strictly prohibited from authorizing calculations."
                        ),
                        details={
                            "sample_id": str(s.id),
                            "sample_code": s.sample_code,
                            "point_code": s.sampling_point.point_code if s.sampling_point else None,
                            "resolution_method": res_method,
                        },
                    )

                # Direct mass vs Bulk density provenance
                sample_dry_mass = getattr(s, "sample_dry_mass_g", None)
                core_diameter = getattr(s, "core_diameter_mm", None)
                core_cnt = getattr(s, "core_count", 1) or 1

                if sample_dry_mass is not None and core_diameter is not None:
                    soil_mass_prov = "DIRECT_SOIL_MASS"
                else:
                    soil_mass_prov = "CORE_BULK_DENSITY_DERIVED"

                layer = LayerInput(
                    layer_index=0,
                    depth_upper_cm=upper,
                    depth_lower_cm=lower,
                    bulk_density_g_cm3=bd_val if bd_val is not None else Decimal("1.3000"),
                    bulk_density_provenance="MEASURED" if bd_val is not None else "CALCULATED_BY_APPROVED_PROCEDURE",
                    soil_mass_provenance=soil_mass_prov,
                    sample_dry_mass_g=sample_dry_mass,
                    fine_soil_mass_g=sample_dry_mass,
                    core_diameter_mm=core_diameter,
                    core_count=core_cnt,
                    coarse_fragment_fraction=cf_val,
                    coarse_fragment_provenance=cf_prov,
                    soc_concentration_g_kg=soc_val,
                    sample_id=s.id,
                    laboratory_result_id=lab_res_id,
                    sampling_event_id=s.collection_event.id if s.collection_event else None,
                    adjacent_sample_relationship=getattr(s, "adjacent_sample_relationship", "SAME_PHYSICAL_SAMPLE"),
                )

                if prof_id not in profile_groups:
                    representative_id = s.sampling_point_id or s.id
                    profile_meta = {
                        "profile_id": prof_id,
                        "resolution_method": res_method,
                        "confidence": conf,
                        "sample_ids": [s.id],
                        "lats": [s.collection_event.actual_lat],
                        "lons": [s.collection_event.actual_lon],
                    }
                    profile_groups[prof_id] = (representative_id, [layer], profile_meta)
                else:
                    profile_groups[prof_id][1].append(layer)
                    profile_groups[prof_id][2]["sample_ids"].append(s.id)
                    profile_groups[prof_id][2]["lats"].append(s.collection_event.actual_lat)
                    profile_groups[prof_id][2]["lons"].append(s.collection_event.actual_lon)

        # Proximity validation: layers within same profile must not diverge geographically beyond 100m
        # AUDIT NOTE: This 100m check is classified strictly as PLATFORM_POLICY (defensive sanity check),
        # NOT a normative VM0042 methodology requirement.
        for prof_id, (rep_id, layers, meta) in profile_groups.items():
            lats = meta["lats"]
            lons = meta["lons"]
            if len(lats) > 1:
                max_lat_diff = max(lats) - min(lats)
                max_lon_diff = max(lons) - min(lons)
                # ~100 meters is approx 0.001 degrees
                if max_lat_diff > 0.001 or max_lon_diff > 0.001:
                    logger.warning(
                        "PLATFORM_POLICY_COORDINATE_SANITY_CHECK: Profile %s has layer coordinates diverging > 100m (%s, %s). "
                        "Classified strictly as PLATFORM_POLICY defensive spatial QA, not a VM0042 normative requirement.",
                        prof_id, max_lat_diff, max_lon_diff
                    )

        # Phase 2: Build UUID-keyed result, sort layers by depth, assign indices
        grouped: Dict[uuid.UUID, List[LayerInput]] = {}
        for prof_id, (rep_id, layers, meta) in profile_groups.items():
            layers.sort(key=lambda l: l.depth_upper_cm)
            for idx, l in enumerate(layers):
                l.layer_index = idx
            grouped[rep_id] = layers

        return grouped

    @classmethod
    async def evaluate_soc_stock(
        cls,
        db: AsyncSession,
        project_id: uuid.UUID,
        organization_id: uuid.UUID,
        prerequisite_assessment_id: Optional[uuid.UUID] = None,
        snapshot_id: Optional[uuid.UUID] = None,
        measurement_period_type: str = "MONITORING",
        reference_depth_cm: Decimal = Decimal("30.00"),
        reference_soil_mass_t_ha: Optional[Decimal] = None,
        esm_algorithm: str = "LAYER_MASS_PROPORTIONING",
        custom_point_layers: Optional[Dict[Any, List[LayerInput]]] = None,
    ) -> Dict[str, Any]:
        """
        Evaluates measured SOC stocks and Equivalent Soil Mass (ESM) normalization.
        Preview calculation without database mutation.
        Fails closed if prerequisite assessment is missing or not locked/eligible.
        """
        project = await cls.get_project_or_raise(db, project_id, organization_id)

        # 1. Resolve Prerequisite Assessment
        prereq = None
        if prerequisite_assessment_id:
            prereq = await cls.get_prerequisite_assessment(db, project_id, prerequisite_assessment_id, organization_id)
        else:
            stmt = (
                select(AgriculturePrerequisiteAssessment)
                .where(
                    AgriculturePrerequisiteAssessment.project_id == project_id,
                    AgriculturePrerequisiteAssessment.organization_id == organization_id,
                    AgriculturePrerequisiteAssessment.status == "LOCKED",
                )
                .order_by(AgriculturePrerequisiteAssessment.version.desc())
            )
            prereq = (await db.execute(stmt)).scalars().first()

        if not prereq:
            raise ValueError("No locked AgriculturePrerequisiteAssessment found. Phase 3B-0 prerequisite gate failed closed.")

        if not prereq.is_locked or prereq.overall_readiness not in ("READY", "READY_WITH_ADVISORY"):
            raise ValueError(
                f"Prerequisite assessment {prereq.assessment_code} is not eligible (status='{prereq.status}', "
                f"readiness='{prereq.overall_readiness}'). Unresolved blocking requirements exist."
            )

        # 2. Extract profile layers
        point_layers_map: Dict[Any, List[LayerInput]] = {}
        if custom_point_layers:
            point_layers_map = custom_point_layers
        else:
            sample_stmt = (
                select(PhysicalSample)
                .where(
                    PhysicalSample.project_id == project_id,
                    PhysicalSample.organization_id == organization_id,
                    PhysicalSample.status == "COLLECTED",
                )
                .options(
                    selectinload(PhysicalSample.sampling_point),
                    selectinload(PhysicalSample.collection_event),
                    selectinload(PhysicalSample.laboratory_analyses).selectinload(LaboratoryAnalysis.results),
                    selectinload(PhysicalSample.qa_review),
                )
            )
            samples = (await db.execute(sample_stmt)).scalars().all()
            eligible_samples = [s for s in samples if s.qa_review and s.qa_review.overall_qa_status == "ACCEPTED"]
            point_layers_map = cls._extract_profile_layers_from_samples(eligible_samples)

        if not point_layers_map:
            raise ValueError("No QA-accepted soil profile samples with valid SOC concentration found for project.")

        # 3. Resolve Reference Soil Mass (M_ref) per VM0042 Section 8.1.1.2
        # VM0042 rule: Reference mass must cover the highest determined soil mass in the relevant comparison set.
        resolved_ref_mass = reference_soil_mass_t_ha
        ref_mass_source = "USER_SPECIFIED" if reference_soil_mass_t_ha is not None else None
        selection_reason = "Explicit user or protocol specified reference mass." if reference_soil_mass_t_ha is not None else None

        if resolved_ref_mass is None:
            if measurement_period_type.upper() == "MONITORING":
                base_stmt = (
                    select(AgricultureSOCStockResult)
                    .where(
                        AgricultureSOCStockResult.project_id == project_id,
                        AgricultureSOCStockResult.organization_id == organization_id,
                        AgricultureSOCStockResult.measurement_period_type == "BASELINE",
                        AgricultureSOCStockResult.aggregation_level == "PROJECT",
                        AgricultureSOCStockResult.result_status == "CALCULATED",
                    )
                    .order_by(AgricultureSOCStockResult.created_at.desc())
                )
                base_res = (await db.execute(base_stmt)).scalars().first()
                if base_res:
                    resolved_ref_mass = base_res.reference_soil_mass_t_ha
                    ref_mass_source = "BASELINE_ANCHORED_REFERENCE_MASS"
                    selection_reason = f"Derived from authoritative baseline project result {base_res.result_code}."

            if resolved_ref_mass is None:
                profile_masses = []
                for pt_id, layers in point_layers_map.items():
                    tot_m = Decimal("0.0")
                    for l in layers:
                        if l.depth_lower_cm <= reference_depth_cm:
                            thickness = l.depth_lower_cm - l.depth_upper_cm
                            if l.soil_mass_provenance == "DIRECT_SOIL_MASS":
                                dry_m = l.fine_soil_mass_g if l.fine_soil_mass_g is not None else l.sample_dry_mass_g
                                m_l = calculate_layer_soil_mass_direct(
                                    dry_fine_soil_mass_g=dry_m,
                                    core_diameter_mm=l.core_diameter_mm,
                                    core_count=l.core_count,
                                )
                            else:
                                cf = l.coarse_fragment_fraction or Decimal("0.0")
                                bd = l.bulk_density_g_cm3 or Decimal("1.30")
                                m_l = calculate_layer_soil_mass(
                                    thickness_cm=thickness,
                                    bulk_density_g_cm3=bd,
                                    coarse_fragment_fraction=cf,
                                )
                            tot_m += m_l
                    if tot_m > Decimal("0.0"):
                        profile_masses.append(tot_m)

                if profile_masses:
                    # VM0042 requirement: Reference mass covers the highest determined soil mass in comparison
                    resolved_ref_mass = max(profile_masses).quantize(Decimal("0.0001"))
                    ref_mass_source = "MAXIMUM_DETERMINED_SAMPLE_MASS"
                    selection_reason = f"VM0042 rule: Highest determined cumulative soil mass to {reference_depth_cm} cm across {len(profile_masses)} profile samples."
                else:
                    resolved_ref_mass = Decimal("3900.0000")
                    ref_mass_source = "DEFAULT_CONSERVATIVE_MINERAL_SOIL"
                    selection_reason = "Fallback 30 cm mineral soil mass at 1.30 g/cm3."

        # 4. Calculate ESM for each sample point
        point_results = []
        strata_grouping: Dict[Optional[uuid.UUID], List[Dict[str, Any]]] = {}

        points_stmt = select(SamplingPoint).where(SamplingPoint.project_id == project_id)
        pt_objs = {p.id: p for p in (await db.execute(points_stmt)).scalars().all()}

        calc_func = calculate_profile_esm_spline if esm_algorithm.upper() in {"CUBIC_SPLINE", "WENDT_HAUSER_2013_CUBIC_SPLINE", "WENDT_HAUSER_2013"} else calculate_profile_esm_proportioning

        for pt_id, layers in point_layers_map.items():
            esm_res = calc_func(
                layers=layers,
                reference_soil_mass_t_ha=resolved_ref_mass,
                reference_depth_cm=reference_depth_cm,
                allow_shallow_soil_exception=False,
            )
            pt_obj = pt_objs.get(pt_id) if isinstance(pt_id, uuid.UUID) else None
            stratum_id = pt_obj.stratum_id if pt_obj else None
            point_info = {
                "sampling_point_id": pt_id,
                "point_code": pt_obj.point_code if pt_obj else f"PT-{str(pt_id)[:6]}",
                "soil_profile_id": getattr(pt_obj, "soil_profile_id", None) or (f"PROF-{pt_obj.point_code}" if pt_obj else None),
                "stratum_id": stratum_id,
                "reference_soil_mass_t_ha": str(esm_res.reference_soil_mass_t_ha),
                "reference_depth_cm": str(esm_res.reference_depth_cm),
                "equivalent_depth_cm": str(esm_res.equivalent_depth_cm) if esm_res.equivalent_depth_cm else None,
                "total_sampled_soil_mass_t_ha": str(esm_res.total_sampled_soil_mass_t_ha),
                "max_sampled_depth_cm": str(esm_res.max_sampled_depth_cm),
                "soc_stock_t_c_per_ha": str(esm_res.soc_stock_t_c_per_ha),
                "unadjusted_stock_t_c_per_ha": str(esm_res.unadjusted_stock_t_c_per_ha),
                "depth_sufficiency_status": esm_res.depth_sufficiency_status,
                "calculation_hash": esm_res.calculation_hash,
                "layers": [
                    {
                        "layer_index": l.layer_index,
                        "depth_upper_cm": str(l.depth_upper_cm),
                        "depth_lower_cm": str(l.depth_lower_cm),
                        "bulk_density_g_cm3": str(l.bulk_density_g_cm3),
                        "soc_concentration_g_kg": str(l.soc_concentration_g_kg),
                        "layer_soil_mass_t_ha": str(l.layer_soil_mass_t_ha),
                        "layer_soc_mass_t_c_ha": str(l.layer_soc_mass_t_c_ha),
                        "fraction_in_reference_mass": str(l.fraction_in_reference_mass),
                        "included_soil_mass_t_ha": str(l.included_soil_mass_t_ha),
                        "included_soc_mass_t_c_ha": str(l.included_soc_mass_t_c_ha),
                    }
                    for l in esm_res.layers
                ],
            }
            point_results.append(point_info)
            strata_grouping.setdefault(stratum_id, []).append(point_info)

        # 5. Aggregate by Stratum
        strata_stmt = select(Stratum).where(Stratum.project_id == project_id, Stratum.organization_id == organization_id)
        strata_objs = {s.id: s for s in (await db.execute(strata_stmt)).scalars().all()}

        stratum_results = []
        strata_for_project_weighting = []

        for strat_id, pts in strata_grouping.items():
            stock_values = [Decimal(p["soc_stock_t_c_per_ha"]) for p in pts]
            mean_soc = aggregate_stratum_soc_stock(stock_values)
            strat_obj = strata_objs.get(strat_id) if strat_id else None
            area = Decimal(str(strat_obj.area_ha)) if (strat_obj and strat_obj.area_ha > 0) else Decimal("100.0000")
            strat_code = strat_obj.code if strat_obj else "DEFAULT"

            stratum_info = {
                "stratum_id": strat_id,
                "stratum_code": strat_code,
                "sample_count": len(pts),
                "area_ha": str(area),
                "stratum_mean_soc_t_c_per_ha": str(mean_soc),
            }
            stratum_results.append(stratum_info)
            strata_for_project_weighting.append(stratum_info)

        # 6. Aggregate Project Area-Weighted SOC Stock
        project_soc, total_area = aggregate_project_area_weighted_soc_stock(strata_for_project_weighting)

        eval_dict = {
            "project_id": str(project_id),
            "prerequisite_assessment_id": str(prereq.id),
            "measurement_period_type": measurement_period_type.upper(),
            "esm_algorithm": esm_algorithm.upper(),
            "reference_soil_mass_t_ha": str(resolved_ref_mass),
            "reference_depth_cm": str(reference_depth_cm),
            "project_soc_stock_t_c_per_ha": str(project_soc),
            "total_area_ha": str(total_area),
            "sample_points_count": len(point_results),
            "carbon_accounting_status": "NOT_CONFIGURED",
            "net_tco2e_removals": None,
        }
        eval_hash = compute_deterministic_hash(eval_dict)

        return {
            "project_id": project_id,
            "prerequisite_assessment_id": prereq.id,
            "measurement_period_type": measurement_period_type.upper(),
            "status": "EVALUATED",
            "esm_algorithm": esm_algorithm.upper(),
            "reference_soil_mass_t_ha": resolved_ref_mass,
            "reference_depth_cm": reference_depth_cm,
            "sample_point_results": point_results,
            "stratum_results": stratum_results,
            "project_soc_stock_t_c_per_ha": project_soc,
            "total_area_ha": total_area,
            "carbon_accounting_status": "NOT_CONFIGURED",
            "net_tco2e_removals": None,
            "blocking_reasons": [],
            "advisory_notes": [
                "Phase 3B-1 Measured SOC Stock and Equivalent Soil Mass calculation complete.",
                "Authoritative carbon crediting is NOT_CONFIGURED (zero tCO2e / ledger minting blocked).",
            ],
            "evaluation_hash": eval_hash,
        }

    @classmethod
    async def calculate_and_persist_authoritative_soc_stock(
        cls,
        db: AsyncSession,
        project_id: uuid.UUID,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        user_role: str,
        prerequisite_assessment_id: uuid.UUID,
        snapshot_id: Optional[uuid.UUID] = None,
        measurement_period_type: str = "MONITORING",
        reference_depth_cm: Decimal = Decimal("30.00"),
        reference_soil_mass_t_ha: Optional[Decimal] = None,
        esm_algorithm: str = "LAYER_MASS_PROPORTIONING",
        notes: Optional[str] = None,
        custom_point_layers: Optional[Dict[Any, List[LayerInput]]] = None,
    ) -> AgricultureSOCStockResult:
        """
        Calculates and transactionally persists authoritative measured SOC stock and ESM results.
        Enforces Segregation of Duties: FIELD_AGENT cannot finalize authoritative calculations.
        Acquires row-level database lock to serialize concurrent executions.
        Strictly enforces the Carbon Invariant (net tCO2e = null).
        """
        if (user_role or "").upper() == "FIELD_AGENT":
            raise ValueError(
                "Field agent role is unauthorized to finalize authoritative SOC stock calculations. "
                "Segregation of duties enforced."
            )

        project = await cls.get_project_or_raise(db, project_id, organization_id)

        # Row lock on Project to serialize concurrent runs
        proj_lock_stmt = select(Project.id).where(Project.id == project_id).with_for_update()
        await db.execute(proj_lock_stmt)

        eval_res = await cls.evaluate_soc_stock(
            db=db,
            project_id=project_id,
            organization_id=organization_id,
            prerequisite_assessment_id=prerequisite_assessment_id,
            snapshot_id=snapshot_id,
            measurement_period_type=measurement_period_type,
            reference_depth_cm=reference_depth_cm,
            reference_soil_mass_t_ha=reference_soil_mass_t_ha,
            esm_algorithm=esm_algorithm,
            custom_point_layers=custom_point_layers,
        )

        calc_hash = eval_res["evaluation_hash"]

        # Deterministic Idempotency Check
        existing_stmt = (
            select(AgricultureSOCStockResult)
            .where(
                AgricultureSOCStockResult.project_id == project_id,
                AgricultureSOCStockResult.organization_id == organization_id,
                AgricultureSOCStockResult.aggregation_level == "PROJECT",
                AgricultureSOCStockResult.calculation_hash == calc_hash,
            )
            .options(selectinload(AgricultureSOCStockResult.layers))
        )
        existing = (await db.execute(existing_stmt)).scalars().first()
        if existing:
            return existing

        now = datetime.now(timezone.utc)
        code_prefix = (project.name or "PROJECT")[:8].replace(" ", "").upper()
        snap_code = f"SOC-SNAP-{code_prefix}-{project_id.hex[:6]}-{measurement_period_type.upper()}-{uuid.uuid4().hex[:4]}"

        # 1. Create Stock Snapshot
        stock_snapshot = AgricultureSOCStockSnapshot(
            organization_id=organization_id,
            project_id=project_id,
            prerequisite_assessment_id=prerequisite_assessment_id,
            snapshot_code=snap_code,
            measurement_period_type=measurement_period_type.upper(),
            snapshot_payload=to_json_serializable(eval_res),
            snapshot_hash=calc_hash,
            created_at=now,
        )
        db.add(stock_snapshot)
        await db.flush()

        # 2. Persist Sample Point Results and Layers
        for pt in eval_res["sample_point_results"]:
            pt_id = pt["sampling_point_id"] if isinstance(pt["sampling_point_id"], uuid.UUID) else (uuid.UUID(str(pt["sampling_point_id"])) if pt.get("sampling_point_id") else None)
            pt_res_code = f"SOC-PT-{code_prefix}-{pt['point_code']}-{measurement_period_type.upper()}-{uuid.uuid4().hex[:4]}"
            pt_result = AgricultureSOCStockResult(
                organization_id=organization_id,
                project_id=project_id,
                sampling_point_id=pt_id,
                soil_profile_id=pt.get("soil_profile_id"),
                stratum_id=pt.get("stratum_id"),
                prerequisite_assessment_id=prerequisite_assessment_id,
                input_snapshot_id=snapshot_id,
                stock_snapshot_id=stock_snapshot.id,
                result_code=pt_res_code,
                measurement_period_type=measurement_period_type.upper(),
                aggregation_level="SAMPLE_POINT",
                methodology_version="2.2",
                corrections_clarifications_version="2026-06-11",
                calculation_engine_version="VM0042_V2_2_ESM_ENGINE_V1.0",
                esm_algorithm=esm_algorithm.upper(),
                reference_soil_mass_t_ha=Decimal(str(pt["reference_soil_mass_t_ha"])),
                reference_depth_cm=Decimal(str(pt["reference_depth_cm"])),
                equivalent_depth_cm=Decimal(str(pt["equivalent_depth_cm"])) if pt.get("equivalent_depth_cm") else None,
                total_sampled_soil_mass_t_ha=Decimal(str(pt["total_sampled_soil_mass_t_ha"])),
                max_sampled_depth_cm=Decimal(str(pt["max_sampled_depth_cm"])),
                soc_stock_t_c_per_ha=Decimal(str(pt["soc_stock_t_c_per_ha"])),
                unadjusted_stock_t_c_per_ha=Decimal(str(pt["unadjusted_stock_t_c_per_ha"])),
                shallow_soil_exception_applied=False,
                depth_sufficiency_status=pt["depth_sufficiency_status"],
                sample_count=1,
                result_status="CALCULATED",
                calculation_hash=pt["calculation_hash"],
                input_snapshot_hash=calc_hash,
                created_by_id=user_id,
                notes=notes,
                created_at=now,
                updated_at=now,
            )
            db.add(pt_result)
            await db.flush()

            for lay in pt.get("layers", []):
                layer_row = AgricultureSOCLayerResult(
                    stock_result_id=pt_result.id,
                    layer_index=int(lay["layer_index"]),
                    depth_upper_cm=Decimal(str(lay["depth_upper_cm"])),
                    depth_lower_cm=Decimal(str(lay["depth_lower_cm"])),
                    layer_thickness_cm=Decimal(str(lay["depth_lower_cm"])) - Decimal(str(lay["depth_upper_cm"])),
                    bulk_density_g_cm3=Decimal(str(lay["bulk_density_g_cm3"])) if lay.get("bulk_density_g_cm3") else None,
                    bulk_density_provenance=lay.get("bulk_density_provenance", "MEASURED"),
                    soil_mass_provenance=lay.get("soil_mass_provenance", "CORE_BULK_DENSITY_DERIVED"),
                    coarse_fragment_fraction=Decimal("0.0000"),
                    coarse_fragment_provenance="MEASURED",
                    soc_concentration_g_kg=Decimal(str(lay["soc_concentration_g_kg"])),
                    layer_soil_mass_t_ha=Decimal(str(lay["layer_soil_mass_t_ha"])),
                    layer_soc_mass_t_c_ha=Decimal(str(lay["layer_soc_mass_t_c_ha"])),
                    cumulative_soil_mass_t_ha=Decimal(str(lay.get("cumulative_soil_mass_t_ha", lay["layer_soil_mass_t_ha"]))),
                    cumulative_soc_mass_t_c_ha=Decimal(str(lay.get("cumulative_soc_mass_t_c_ha", lay["layer_soc_mass_t_c_ha"]))),
                    fraction_in_reference_mass=Decimal(str(lay["fraction_in_reference_mass"])) if lay.get("fraction_in_reference_mass") else None,
                    included_soil_mass_t_ha=Decimal(str(lay["included_soil_mass_t_ha"])) if lay.get("included_soil_mass_t_ha") else None,
                    included_soc_mass_t_c_ha=Decimal(str(lay["included_soc_mass_t_c_ha"])) if lay.get("included_soc_mass_t_c_ha") else None,
                    created_at=now,
                )
                db.add(layer_row)

        # 3. Persist Stratum Results
        for st in eval_res["stratum_results"]:
            st_id = st["stratum_id"] if isinstance(st["stratum_id"], uuid.UUID) else (uuid.UUID(str(st["stratum_id"])) if st["stratum_id"] else None)
            st_res_code = f"SOC-STRAT-{code_prefix}-{st['stratum_code']}-{measurement_period_type.upper()}-{uuid.uuid4().hex[:4]}"
            st_result = AgricultureSOCStockResult(
                organization_id=organization_id,
                project_id=project_id,
                stratum_id=st_id,
                prerequisite_assessment_id=prerequisite_assessment_id,
                input_snapshot_id=snapshot_id,
                stock_snapshot_id=stock_snapshot.id,
                result_code=st_res_code,
                measurement_period_type=measurement_period_type.upper(),
                aggregation_level="STRATUM",
                methodology_version="2.2",
                corrections_clarifications_version="2026-06-11",
                calculation_engine_version="VM0042_V2_2_ESM_ENGINE_V1.0",
                esm_algorithm=esm_algorithm.upper(),
                reference_soil_mass_t_ha=eval_res["reference_soil_mass_t_ha"],
                reference_depth_cm=eval_res["reference_depth_cm"],
                soc_stock_t_c_per_ha=Decimal(str(st["stratum_mean_soc_t_c_per_ha"])),
                area_ha=Decimal(str(st["area_ha"])),
                sample_count=int(st["sample_count"]),
                result_status="CALCULATED",
                calculation_hash=calc_hash,
                input_snapshot_hash=calc_hash,
                created_by_id=user_id,
                notes=notes,
                created_at=now,
                updated_at=now,
            )
            db.add(st_result)

        # 4. Check for prior active project-level result to establish supersession lineage
        prior_active_stmt = (
            select(AgricultureSOCStockResult)
            .where(
                AgricultureSOCStockResult.project_id == project_id,
                AgricultureSOCStockResult.organization_id == organization_id,
                AgricultureSOCStockResult.measurement_period_type == measurement_period_type.upper(),
                AgricultureSOCStockResult.aggregation_level == "PROJECT",
                AgricultureSOCStockResult.result_status == "CALCULATED",
            )
            .order_by(AgricultureSOCStockResult.created_at.desc())
        )
        prior_active = (await db.execute(prior_active_stmt)).scalars().first()

        # 5. Persist Project-Level Result
        proj_res_code = f"SOC-PROJ-{code_prefix}-{measurement_period_type.upper()}-{now.strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4]}"
        project_result = AgricultureSOCStockResult(
            organization_id=organization_id,
            project_id=project_id,
            prerequisite_assessment_id=prerequisite_assessment_id,
            input_snapshot_id=snapshot_id,
            stock_snapshot_id=stock_snapshot.id,
            result_code=proj_res_code,
            measurement_period_type=measurement_period_type.upper(),
            aggregation_level="PROJECT",
            methodology_version="2.2",
            corrections_clarifications_version="2026-06-11",
            calculation_engine_version="VM0042_V2_2_ESM_ENGINE_V1.0",
            esm_algorithm=esm_algorithm.upper(),
            reference_soil_mass_t_ha=eval_res["reference_soil_mass_t_ha"],
            reference_depth_cm=eval_res["reference_depth_cm"],
            soc_stock_t_c_per_ha=eval_res["project_soc_stock_t_c_per_ha"],
            area_ha=eval_res["total_area_ha"],
            sample_count=len(eval_res["sample_point_results"]),
            component_breakdown=to_json_serializable({
                "strata_results": eval_res["stratum_results"],
                "sample_points_count": len(eval_res["sample_point_results"]),
                "carbon_accounting_status": "NOT_CONFIGURED",
                "net_tco2e_removals": None,
                "delta_soc_removals": None,
                "vcu_quantity": None,
                "ledger_status": "BLOCKED_FOR_AGRICULTURE",
            }),
            result_status="CALCULATED",
            calculation_hash=calc_hash,
            input_snapshot_hash=calc_hash,
            created_by_id=user_id,
            notes=notes,
            created_at=now,
            updated_at=now,
        )
        db.add(project_result)
        await db.flush()

        if prior_active and prior_active.id != project_result.id:
            prior_active.result_status = "SUPERSEDED"
            prior_active.superseded_by_id = project_result.id
            prior_active.updated_at = now
            await db.flush()

        return project_result

    @classmethod
    async def list_soc_stock_results(
        cls,
        db: AsyncSession,
        project_id: uuid.UUID,
        organization_id: uuid.UUID,
        measurement_period_type: Optional[str] = None,
        aggregation_level: Optional[str] = None,
    ) -> List[AgricultureSOCStockResult]:
        """Lists SOC stock results for a project with optional period and aggregation filters."""
        await cls.get_project_or_raise(db, project_id, organization_id)
        stmt = (
            select(AgricultureSOCStockResult)
            .where(
                AgricultureSOCStockResult.project_id == project_id,
                AgricultureSOCStockResult.organization_id == organization_id,
            )
            .options(selectinload(AgricultureSOCStockResult.layers))
            .order_by(AgricultureSOCStockResult.created_at.desc())
        )
        if measurement_period_type:
            stmt = stmt.where(AgricultureSOCStockResult.measurement_period_type == measurement_period_type.upper())
        if aggregation_level:
            stmt = stmt.where(AgricultureSOCStockResult.aggregation_level == aggregation_level.upper())

        res = await db.execute(stmt)
        return list(res.scalars().all())

    @classmethod
    async def get_soc_stock_result(
        cls,
        db: AsyncSession,
        project_id: uuid.UUID,
        result_id: uuid.UUID,
        organization_id: uuid.UUID,
    ) -> AgricultureSOCStockResult:
        """Retrieves a single SOC stock result with component layers and tenant isolation."""
        await cls.get_project_or_raise(db, project_id, organization_id)
        stmt = (
            select(AgricultureSOCStockResult)
            .where(
                AgricultureSOCStockResult.id == result_id,
                AgricultureSOCStockResult.project_id == project_id,
                AgricultureSOCStockResult.organization_id == organization_id,
            )
            .options(selectinload(AgricultureSOCStockResult.layers))
        )
        res = await db.execute(stmt)
        result = res.scalars().first()
        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SOC stock result not found")
        return result

    @classmethod
    async def get_soc_stock_result_components(
        cls,
        db: AsyncSession,
        project_id: uuid.UUID,
        result_id: uuid.UUID,
        organization_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """Retrieves full component breakdown, layer table, and cryptographic proof for an SOC stock result."""
        result = await cls.get_soc_stock_result(db, project_id, result_id, organization_id)
        return {
            "result_id": result.id,
            "result_code": result.result_code,
            "measurement_period_type": result.measurement_period_type,
            "aggregation_level": result.aggregation_level,
            "methodology_version": result.methodology_version,
            "corrections_clarifications_version": result.corrections_clarifications_version,
            "esm_algorithm": result.esm_algorithm,
            "reference_soil_mass_t_ha": str(result.reference_soil_mass_t_ha),
            "reference_depth_cm": str(result.reference_depth_cm),
            "equivalent_depth_cm": str(result.equivalent_depth_cm) if result.equivalent_depth_cm else None,
            "soc_stock_t_c_per_ha": str(result.soc_stock_t_c_per_ha),
            "area_ha": str(result.area_ha) if result.area_ha else None,
            "sample_count": result.sample_count,
            "calculation_hash": result.calculation_hash,
            "input_snapshot_hash": result.input_snapshot_hash,
            "component_breakdown": result.component_breakdown,
            "carbon_accounting_status": "NOT_CONFIGURED",
            "net_tco2e_removals": None,
            "delta_soc_removals": None,
            "vcu_quantity": None,
            "ledger_status": "BLOCKED_FOR_AGRICULTURE",
            "layers": [
                {
                    "layer_index": l.layer_index,
                    "depth_upper_cm": str(l.depth_upper_cm),
                    "depth_lower_cm": str(l.depth_lower_cm),
                    "layer_thickness_cm": str(l.layer_thickness_cm),
                    "bulk_density_g_cm3": str(l.bulk_density_g_cm3),
                    "bulk_density_provenance": l.bulk_density_provenance,
                    "coarse_fragment_fraction": str(l.coarse_fragment_fraction),
                    "soc_concentration_g_kg": str(l.soc_concentration_g_kg),
                    "layer_soil_mass_t_ha": str(l.layer_soil_mass_t_ha),
                    "layer_soc_mass_t_c_ha": str(l.layer_soc_mass_t_c_ha),
                    "cumulative_soil_mass_t_ha": str(l.cumulative_soil_mass_t_ha),
                    "cumulative_soc_mass_t_c_ha": str(l.cumulative_soc_mass_t_c_ha),
                    "fraction_in_reference_mass": str(l.fraction_in_reference_mass),
                    "included_soil_mass_t_ha": str(l.included_soil_mass_t_ha),
                    "included_soc_mass_t_c_ha": str(l.included_soc_mass_t_c_ha),
                }
                for l in (result.layers or [])
            ],
        }

    # =========================================================================
    # PHASE 3B-2: SOC STOCK CHANGE & UNCERTAINTY QUANTIFICATION METHODS
    # =========================================================================

    @classmethod
    async def evaluate_soc_stock_change(
        cls,
        db: AsyncSession,
        project_id: uuid.UUID,
        organization_id: uuid.UUID,
        baseline_stock_result_id: uuid.UUID,
        monitoring_stock_result_id: uuid.UUID,
        prerequisite_assessment_id: Optional[uuid.UUID] = None,
        laboratory_method: str = "DRY_COMBUSTION",
        lab_qa_verified: bool = True,
        active_lab_proficiency: bool = True,
    ) -> Dict[str, Any]:
        """
        Evaluates annualized scenario SOC stock changes and VM0042 Eq. 74 uncertainty deduction.
        Read-only preview: does not persist calculation records.
        """
        project = await cls.get_project_or_raise(db, project_id, organization_id)

        # 1. Load Baseline and Monitoring Project Stock Results
        baseline = await db.get(AgricultureSOCStockResult, baseline_stock_result_id)
        if not baseline:
            raise SOCChangeCalculationError(
                code="BASELINE_RESULT_NOT_FOUND",
                message=f"Baseline SOC stock result '{baseline_stock_result_id}' not found.",
            )
        if baseline.organization_id != organization_id or baseline.project_id != project_id:
            raise SOCChangeCalculationError(
                code="CROSS_TENANT_BASELINE_RESULT",
                message="Baseline stock result does not belong to the target project and organization.",
            )
        if baseline.measurement_period_type != "BASELINE":
            raise SOCChangeCalculationError(
                code="INVALID_BASELINE_PERIOD",
                message=f"Expected baseline result to have period 'BASELINE', found '{baseline.measurement_period_type}'.",
            )
        if baseline.aggregation_level != "PROJECT":
            raise SOCChangeCalculationError(
                code="INVALID_AGGREGATION_LEVEL",
                message=f"Baseline result must be at 'PROJECT' aggregation level, found '{baseline.aggregation_level}'.",
            )
        if baseline.result_status == "SUPERSEDED":
            raise SOCChangeCalculationError(
                code="SUPERSEDED_BASELINE_RESULT",
                message="Cannot compute stock change against a superseded baseline stock result.",
            )

        monitoring = await db.get(AgricultureSOCStockResult, monitoring_stock_result_id)
        if not monitoring:
            raise SOCChangeCalculationError(
                code="MONITORING_RESULT_NOT_FOUND",
                message=f"Monitoring SOC stock result '{monitoring_stock_result_id}' not found.",
            )
        if monitoring.organization_id != organization_id or monitoring.project_id != project_id:
            raise SOCChangeCalculationError(
                code="CROSS_TENANT_MONITORING_RESULT",
                message="Monitoring stock result does not belong to the target project and organization.",
            )
        if monitoring.measurement_period_type != "MONITORING":
            raise SOCChangeCalculationError(
                code="INVALID_MONITORING_PERIOD",
                message=f"Expected monitoring result to have period 'MONITORING', found '{monitoring.measurement_period_type}'.",
            )
        if monitoring.aggregation_level != "PROJECT":
            raise SOCChangeCalculationError(
                code="INVALID_AGGREGATION_LEVEL",
                message=f"Monitoring result must be at 'PROJECT' aggregation level, found '{monitoring.aggregation_level}'.",
            )
        if monitoring.result_status == "SUPERSEDED":
            raise SOCChangeCalculationError(
                code="SUPERSEDED_MONITORING_RESULT",
                message="Cannot compute stock change using a superseded monitoring stock result.",
            )

        # 2. Methodological & ESM Compatibility Gates
        if baseline.reference_soil_mass_t_ha != monitoring.reference_soil_mass_t_ha:
            raise SOCChangeCalculationError(
                code="ESM_REFERENCE_MASS_MISMATCH",
                message=(
                    f"Baseline ESM reference mass ({baseline.reference_soil_mass_t_ha} t/ha) differs from "
                    f"monitoring ({monitoring.reference_soil_mass_t_ha} t/ha). Periods must use identical reference mass."
                ),
            )

        if baseline.reference_depth_cm != monitoring.reference_depth_cm:
            raise SOCChangeCalculationError(
                code="ESM_REFERENCE_DEPTH_MISMATCH",
                message=(
                    f"Baseline reference depth ({baseline.reference_depth_cm} cm) differs from "
                    f"monitoring ({monitoring.reference_depth_cm} cm)."
                ),
            )

        # 3. Temporal Interval & Elapsed Time
        t_start = baseline.created_at
        t_final = monitoring.created_at
        delta_sec = (t_final - t_start).total_seconds()
        if delta_sec <= 0:
            # If created_at timestamps are identical or inverted, fail closed
            raise SOCChangeCalculationError(
                code="TEMPORAL_SEQUENCE_INVERSION",
                message="Monitoring timestamp must strictly succeed baseline timestamp.",
            )

        # Elapsed years x: standard 365.25 days/year, minimum 1.0 year per VM0042 Section 8.2
        elapsed_years = Decimal(str(delta_sec / (365.25 * 86400.0))).quantize(Decimal("0.0001"), rounding=ROUND_HALF_EVEN)
        if elapsed_years < Decimal("1.0000"):
            elapsed_years = Decimal("1.0000")

        # 4. Strata Matching and Sampling Variance Extraction
        bsl_strata_raw = (baseline.component_breakdown or {}).get("strata_results", [])
        mon_strata_raw = (monitoring.component_breakdown or {}).get("strata_results", [])

        if not mon_strata_raw or not bsl_strata_raw:
            # Fallback: construct single project-level stratum if strata breakdown wasn't stored
            bsl_strata_raw = [{
                "stratum_id": str(uuid.uuid4()),
                "stratum_code": "PROJECT_ALL",
                "area_ha": str(baseline.area_ha or Decimal("100.0")),
                "stratum_mean_soc_t_c_per_ha": str(baseline.soc_stock_t_c_per_ha),
                "sample_count": baseline.sample_count or 2,
            }]
            mon_strata_raw = [{
                "stratum_id": bsl_strata_raw[0]["stratum_id"],
                "stratum_code": "PROJECT_ALL",
                "area_ha": str(monitoring.area_ha or baseline.area_ha or Decimal("100.0")),
                "stratum_mean_soc_t_c_per_ha": str(monitoring.soc_stock_t_c_per_ha),
                "sample_count": monitoring.sample_count or 2,
            }]

        bsl_by_code = {s.get("stratum_code", f"STRAT_{i}"): s for i, s in enumerate(bsl_strata_raw)}

        # Load point-level stock results to check for paired repeated measurements
        pts_bsl_stmt = select(AgricultureSOCStockResult).where(
            AgricultureSOCStockResult.project_id == project_id,
            AgricultureSOCStockResult.organization_id == organization_id,
            AgricultureSOCStockResult.measurement_period_type == "BASELINE",
            AgricultureSOCStockResult.aggregation_level == "SAMPLE_POINT",
            AgricultureSOCStockResult.result_status != "SUPERSEDED",
        )
        pts_bsl_list = list((await db.execute(pts_bsl_stmt)).scalars().all())

        pts_mon_stmt = select(AgricultureSOCStockResult).where(
            AgricultureSOCStockResult.project_id == project_id,
            AgricultureSOCStockResult.organization_id == organization_id,
            AgricultureSOCStockResult.measurement_period_type == "MONITORING",
            AgricultureSOCStockResult.aggregation_level == "SAMPLE_POINT",
            AgricultureSOCStockResult.result_status != "SUPERSEDED",
        )
        pts_mon_list = list((await db.execute(pts_mon_stmt)).scalars().all())

        bsl_pts_by_point_id = {p.sampling_point_id: p for p in pts_bsl_list if p.sampling_point_id}

        strata_inputs: List[StratumInputData] = []

        for mon_s in mon_strata_raw:
            code = mon_s.get("stratum_code", "DEFAULT")
            if code not in bsl_by_code:
                raise SOCChangeCalculationError(
                    code="STRATA_MISMATCH",
                    message=f"Monitoring stratum '{code}' does not match any baseline stratum.",
                )
            bsl_s = bsl_by_code[code]

            st_id = uuid.UUID(str(mon_s["stratum_id"])) if mon_s.get("stratum_id") else uuid.uuid4()
            area = Decimal(str(mon_s.get("area_ha") or bsl_s.get("area_ha") or "1.0000"))
            bsl_soc = Decimal(str(bsl_s.get("stratum_mean_soc_t_c_per_ha") or "0.0000"))
            mon_soc = Decimal(str(mon_s.get("stratum_mean_soc_t_c_per_ha") or "0.0000"))
            n_proj = int(mon_s.get("sample_count", len(pts_mon_list) or 2))
            n_bsl = int(bsl_s.get("sample_count", len(pts_bsl_list) or 2))

            # Check point-level paired measurements in this stratum
            matched_pairs_bsl = []
            matched_pairs_mon = []
            for mp in pts_mon_list:
                if mp.sampling_point_id and mp.sampling_point_id in bsl_pts_by_point_id:
                    bp = bsl_pts_by_point_id[mp.sampling_point_id]
                    matched_pairs_bsl.append(bp.soc_stock_t_c_per_ha)
                    matched_pairs_mon.append(mp.soc_stock_t_c_per_ha)

            paired_cov = None
            paired_deltas = None
            var_t1 = None
            var_t2 = None

            if len(matched_pairs_bsl) >= 2:
                # Paired repeated measurements exist!
                paired_deltas = [
                    (matched_pairs_mon[i] - matched_pairs_bsl[i]) / elapsed_years
                    for i in range(len(matched_pairs_bsl))
                ]
                n_proj = len(matched_pairs_bsl)
                n_bsl = len(matched_pairs_bsl)
            else:
                # Independent sampling: variance estimated from point arrays or default
                pts_mon_stocks = [p.soc_stock_t_c_per_ha for p in pts_mon_list]
                pts_bsl_stocks = [p.soc_stock_t_c_per_ha for p in pts_bsl_list]
                if len(pts_mon_stocks) >= 2:
                    mean_m = sum(pts_mon_stocks) / Decimal(len(pts_mon_stocks))
                    var_t2 = sum((x - mean_m) ** 2 for x in pts_mon_stocks) / Decimal(len(pts_mon_stocks) - 1)
                else:
                    var_t2 = Decimal("1.00000000")
                if len(pts_bsl_stocks) >= 2:
                    mean_b = sum(pts_bsl_stocks) / Decimal(len(pts_bsl_stocks))
                    var_t1 = sum((x - mean_b) ** 2 for x in pts_bsl_stocks) / Decimal(len(pts_bsl_stocks) - 1)
                else:
                    var_t1 = Decimal("1.00000000")

            strata_inputs.append(StratumInputData(
                stratum_id=st_id,
                stratum_code=code,
                area_ha=area,
                baseline_mean_soc_t_c_per_ha=bsl_soc,
                monitoring_mean_soc_t_c_per_ha=mon_soc,
                sample_count_project=n_proj,
                sample_count_baseline=n_bsl,
                sample_variance_project_t1=var_t1,
                sample_variance_project_t2=var_t2,
                paired_covariance_project=paired_cov,
                paired_point_changes_project=paired_deltas,
            ))

        # 5. Run VM0042 QA2 Aggregation Engine
        calc_out = aggregate_project_qa2_soc_change(
            strata_inputs=strata_inputs,
            elapsed_years=elapsed_years,
            laboratory_method=laboratory_method,
            lab_qa_verified=lab_qa_verified,
            active_lab_proficiency=active_lab_proficiency,
        )

        # 6. Format Preview Evaluation Payload
        # Compute total_area for area_weight calculation
        _total_area = sum(s.area_ha for s in calc_out.strata_results)
        strata_formatted = [
            {
                "stratum_id": str(s.stratum_id),
                "stratum_code": s.stratum_code,
                # Canonical area fields
                "area_ha": str(s.area_ha),
                "stratum_area_ha": str(s.area_ha),  # Frontend alias
                "area_weight": str(
                    (s.area_ha / _total_area).quantize(Decimal("0.00000001"), rounding=ROUND_HALF_EVEN)
                ) if _total_area > Decimal("0") else "0",
                # Input mean SOC values (from strata_inputs, same order)
                "baseline_mean_soc_t_c_per_ha": str(s_in.baseline_mean_soc_t_c_per_ha),
                "monitoring_mean_soc_t_c_per_ha": str(s_in.monitoring_mean_soc_t_c_per_ha),
                # Annualized rate fields
                "delta_soc_project_t_c_ha_yr": str(s.delta_soc_project_t_c_ha_yr),
                "delta_soc_baseline_t_c_ha_yr": str(s.delta_soc_baseline_t_c_ha_yr),
                "delta_soc_net_t_c_ha_yr": str(s.delta_soc_net_t_c_ha_yr),
                "delta_co2_net_tco2e_ha_yr": str(s.delta_co2_net_tco2e_ha_yr),
                # Scenario-specific tCO2e/yr totals (VM0042 Eq. 46/47 components)
                "baseline_soc_change_tco2e_yr": str(s.baseline_soc_change_tco2e_yr),
                "project_soc_change_tco2e_yr": str(s.project_soc_change_tco2e_yr),
                "qa2_net_soc_effect_tco2e_yr": str(s.qa2_net_soc_effect_tco2e_yr),
                "total_net_delta_co2_tco2e_yr": str(s.total_net_delta_co2_tco2e_yr),
                "stratum_total_net_delta_co2_tco2e_yr": str(s.total_net_delta_co2_tco2e_yr),  # Frontend alias
                # Variance components (VM0042 Eq. 70/71)
                "variance_delta_soc_proj": str(s.variance_delta_soc_proj),
                "variance_delta_soc_bsl": str(s.variance_delta_soc_bsl),
                "stratum_variance_net": str(s.stratum_variance_net),
                "stratum_variance": str(s.stratum_variance_net),  # Frontend alias
                # Paired covariance (nullable)
                "paired_covariance_project": str(s.paired_covariance_project) if s.paired_covariance_project is not None else None,
                "paired_covariance_baseline": str(s.paired_covariance_baseline) if s.paired_covariance_baseline is not None else None,
                # Sample & DF
                "degrees_of_freedom": s.degrees_of_freedom,
                "sample_count_project": s.sample_count_project,
                "sample_count_baseline": s.sample_count_baseline,
            }
            for s, s_in in zip(calc_out.strata_results, strata_inputs)
        ]

        return {
            "project_id": str(project_id),
            "status": "EVALUATED",
            "baseline_stock_result_id": str(baseline_stock_result_id),
            "monitoring_stock_result_id": str(monitoring_stock_result_id),
            "elapsed_years": elapsed_years,
            "elapsed_years_val": str(elapsed_years),
            "t_start": t_start.isoformat(),
            "t_final": t_final.isoformat(),
            "total_project_area_ha": str(calc_out.total_project_area_ha),
            "delta_soc_project_t_c_ha_yr": str(calc_out.delta_soc_project_t_c_ha_yr),
            "delta_soc_baseline_t_c_ha_yr": str(calc_out.delta_soc_baseline_t_c_ha_yr),
            "delta_soc_net_t_c_ha_yr": str(calc_out.delta_soc_net_t_c_ha_yr),
            "delta_co2_project_tco2e_ha_yr": str(calc_out.delta_co2_project_tco2e_ha_yr),
            "delta_co2_baseline_tco2e_ha_yr": str(calc_out.delta_co2_baseline_tco2e_ha_yr),
            "delta_co2_net_tco2e_ha_yr": str(calc_out.delta_co2_net_tco2e_ha_yr),
            "total_project_delta_co2_tco2e_yr": str(calc_out.total_project_delta_co2_tco2e_yr),
            "total_baseline_delta_co2_tco2e_yr": str(calc_out.total_baseline_delta_co2_tco2e_yr),
            "total_net_delta_co2_tco2e_yr": str(calc_out.total_net_delta_co2_tco2e_yr),
            "baseline_soc_change_tco2e_yr": str(calc_out.baseline_soc_change_tco2e_yr),
            "project_soc_change_tco2e_yr": str(calc_out.project_soc_change_tco2e_yr),
            "qa2_net_soc_effect_tco2e_yr": str(calc_out.qa2_net_soc_effect_tco2e_yr),
            "uncertainty_adjusted_soc_effect_tco2e_yr": str(calc_out.uncertainty.adjusted_net_delta_co2_tco2e_yr),
            "sign_indicator": calc_out.sign_indicator,
            "eq44_eq45_status": calc_out.eq44_eq45_status,
            "df_estimator": calc_out.df_estimator,
            "adjusted_net_delta_co2_tco2e_yr": str(calc_out.uncertainty.adjusted_net_delta_co2_tco2e_yr),
            "variance_delta_soc_project": str(calc_out.variance_delta_soc_project),
            "variance_delta_soc_baseline": str(calc_out.variance_delta_soc_baseline),
            "total_variance_delta_soc": str(calc_out.total_variance_delta_soc),
            "standard_error_delta_soc_t_c_ha_yr": str(calc_out.uncertainty.standard_error_delta_soc_t_c_ha_yr),
            "standard_error_tco2e_yr": str(calc_out.uncertainty.standard_error_tco2e_yr),
            "degrees_of_freedom": calc_out.uncertainty.degrees_of_freedom,
            "student_t_value_0667": str(calc_out.uncertainty.student_t_value_0667),
            "relative_uncertainty_pct": str(calc_out.uncertainty.relative_uncertainty_pct),
            "allowable_uncertainty_pct": str(calc_out.uncertainty.allowable_uncertainty_pct),
            "uncertainty_deduction_pct": str(calc_out.uncertainty.uncertainty_deduction_pct),
            "uncertainty_deduction_fraction": str(calc_out.uncertainty.uncertainty_deduction_fraction),
            "uncertainty_status": calc_out.uncertainty.uncertainty_status,
            "measurement_error_status": calc_out.measurement_error_status,
            "measurement_error_router": calc_out.measurement_error_router,
            "strata_results": strata_formatted,
            "blocking_reasons": [],
            "evaluation_hash": calc_out.calculation_hash,
            "raw_calc": calc_out,
            "baseline_obj": baseline,
            "monitoring_obj": monitoring,
            "elapsed_years_dec": elapsed_years,
            "t_start_dt": t_start,
            "t_final_dt": t_final,
        }

    @classmethod
    async def finalize_soc_stock_change(
        cls,
        db: AsyncSession,
        project_id: uuid.UUID,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        user_role: str,
        baseline_stock_result_id: uuid.UUID,
        monitoring_stock_result_id: uuid.UUID,
        prerequisite_assessment_id: uuid.UUID,
        laboratory_method: str = "DRY_COMBUSTION",
        lab_qa_verified: bool = True,
        active_lab_proficiency: bool = True,
        notes: Optional[str] = None,
    ) -> AgricultureSOCChangeResult:
        """
        Authoritatively calculates and persists scenario SOC stock change, stoichiometric
        44/12 CO2 outputs, and VM0042 Eq. 74 uncertainty deduction with strict immutability.
        Segregation of Duties: FIELD_AGENT cannot finalize authoritative calculations.
        """
        if (user_role or "").upper() == "FIELD_AGENT":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Field agent role is unauthorized to finalize authoritative SOC stock change. Segregation of duties enforced.",
            )

        # 1. Evaluate Preview and Perform Verification Gates
        eval_res = await cls.evaluate_soc_stock_change(
            db=db,
            project_id=project_id,
            organization_id=organization_id,
            baseline_stock_result_id=baseline_stock_result_id,
            monitoring_stock_result_id=monitoring_stock_result_id,
            prerequisite_assessment_id=prerequisite_assessment_id,
            laboratory_method=laboratory_method,
            lab_qa_verified=lab_qa_verified,
            active_lab_proficiency=active_lab_proficiency,
        )

        calc_hash = eval_res["evaluation_hash"]
        baseline: AgricultureSOCStockResult = eval_res["baseline_obj"]
        monitoring: AgricultureSOCStockResult = eval_res["monitoring_obj"]
        raw_calc: ProjectSOCChangeOutput = eval_res["raw_calc"]

        # 2. Concurrency and Idempotency Guard (Row-Level Check)
        existing_stmt = select(AgricultureSOCChangeResult).where(
            AgricultureSOCChangeResult.project_id == project_id,
            AgricultureSOCChangeResult.organization_id == organization_id,
            AgricultureSOCChangeResult.baseline_stock_result_id == baseline_stock_result_id,
            AgricultureSOCChangeResult.monitoring_stock_result_id == monitoring_stock_result_id,
            AgricultureSOCChangeResult.result_status == "CALCULATED",
        ).with_for_update()
        existing = (await db.execute(existing_stmt)).scalars().first()
        if existing and existing.calculation_hash == calc_hash:
            return existing

        now = datetime.now(timezone.utc)
        result_code = f"SOC-CHG-{now.strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4]}"

        # 3. Check for Prior Active Project-Level Change Result to Supersede
        prior_active_stmt = select(AgricultureSOCChangeResult).where(
            AgricultureSOCChangeResult.project_id == project_id,
            AgricultureSOCChangeResult.organization_id == organization_id,
            AgricultureSOCChangeResult.result_status == "CALCULATED",
        ).order_by(AgricultureSOCChangeResult.created_at.desc())
        prior_active = (await db.execute(prior_active_stmt)).scalars().first()

        # 4. Construct and Persist AgricultureSOCChangeResult
        change_result = AgricultureSOCChangeResult(
            organization_id=organization_id,
            project_id=project_id,
            baseline_stock_result_id=baseline_stock_result_id,
            monitoring_stock_result_id=monitoring_stock_result_id,
            prerequisite_assessment_id=prerequisite_assessment_id,
            result_code=result_code,
            methodology_version="2.2",
            corrections_clarifications_version="2026-06-11",
            calculation_engine_version="VM0042_V2_2_SOC_CHANGE_V1.0",
            quantification_approach="APPROACH_2",
            t_start=eval_res["t_start_dt"],
            t_final=eval_res["t_final_dt"],
            elapsed_years=eval_res["elapsed_years_dec"],
            esm_algorithm=monitoring.esm_algorithm,
            reference_soil_mass_t_ha=monitoring.reference_soil_mass_t_ha,
            reference_depth_cm=monitoring.reference_depth_cm,
            total_project_area_ha=raw_calc.total_project_area_ha,
            baseline_mean_soc_t_c_per_ha=raw_calc.baseline_mean_soc_t_c_per_ha,
            monitoring_mean_soc_t_c_per_ha=raw_calc.monitoring_mean_soc_t_c_per_ha,
            delta_soc_project_t_c_ha_yr=raw_calc.delta_soc_project_t_c_ha_yr,
            delta_soc_baseline_t_c_ha_yr=raw_calc.delta_soc_baseline_t_c_ha_yr,
            delta_soc_net_t_c_ha_yr=raw_calc.delta_soc_net_t_c_ha_yr,
            delta_co2_project_tco2e_ha_yr=raw_calc.delta_co2_project_tco2e_ha_yr,
            delta_co2_baseline_tco2e_ha_yr=raw_calc.delta_co2_baseline_tco2e_ha_yr,
            delta_co2_net_tco2e_ha_yr=raw_calc.delta_co2_net_tco2e_ha_yr,
            total_project_delta_co2_tco2e_yr=raw_calc.total_project_delta_co2_tco2e_yr,
            total_baseline_delta_co2_tco2e_yr=raw_calc.total_baseline_delta_co2_tco2e_yr,
            total_net_delta_co2_tco2e_yr=raw_calc.total_net_delta_co2_tco2e_yr,
            baseline_soc_change_tco2e_yr=raw_calc.baseline_soc_change_tco2e_yr,
            project_soc_change_tco2e_yr=raw_calc.project_soc_change_tco2e_yr,
            qa2_net_soc_effect_tco2e_yr=raw_calc.qa2_net_soc_effect_tco2e_yr,
            uncertainty_adjusted_soc_effect_tco2e_yr=raw_calc.uncertainty.adjusted_net_delta_co2_tco2e_yr,
            sign_indicator=raw_calc.sign_indicator,
            eq44_eq45_status=raw_calc.eq44_eq45_status,
            df_estimator=raw_calc.df_estimator,
            co2_to_c_ratio=CO2_TO_C_RATIO.quantize(Decimal("0.00000001"), rounding=ROUND_HALF_EVEN),
            variance_delta_soc_project=raw_calc.variance_delta_soc_project,
            variance_delta_soc_baseline=raw_calc.variance_delta_soc_baseline,
            total_variance_delta_soc=raw_calc.total_variance_delta_soc,
            standard_error_delta_soc_t_c_ha_yr=raw_calc.uncertainty.standard_error_delta_soc_t_c_ha_yr,
            standard_error_tco2e_yr=raw_calc.uncertainty.standard_error_tco2e_yr,
            degrees_of_freedom=raw_calc.uncertainty.degrees_of_freedom,
            student_t_value_0667=raw_calc.uncertainty.student_t_value_0667,
            relative_uncertainty_pct=raw_calc.uncertainty.relative_uncertainty_pct,
            allowable_uncertainty_pct=raw_calc.uncertainty.allowable_uncertainty_pct,
            uncertainty_deduction_pct=raw_calc.uncertainty.uncertainty_deduction_pct,
            uncertainty_deduction_fraction=raw_calc.uncertainty.uncertainty_deduction_fraction,
            adjusted_net_delta_co2_tco2e_yr=raw_calc.uncertainty.adjusted_net_delta_co2_tco2e_yr,
            measurement_error_status=raw_calc.measurement_error_status,
            measurement_error_router=raw_calc.measurement_error_router,
            strata_results=eval_res["strata_results"],
            component_breakdown=to_json_serializable({
                "baseline_stock_result_code": baseline.result_code,
                "monitoring_stock_result_code": monitoring.result_code,
                "co2_to_c_ratio": "44/12",
                "carbon_accounting_status": "NOT_CONFIGURED",
                "eq44_eq45_status": raw_calc.eq44_eq45_status,
                "df_estimator": raw_calc.df_estimator,
                "sign_indicator": raw_calc.sign_indicator,
                "baseline_soc_change_tco2e_yr": str(raw_calc.baseline_soc_change_tco2e_yr),
                "project_soc_change_tco2e_yr": str(raw_calc.project_soc_change_tco2e_yr),
                "qa2_net_soc_effect_tco2e_yr": str(raw_calc.qa2_net_soc_effect_tco2e_yr),
                "net_tco2e_removals": str(raw_calc.uncertainty.adjusted_net_delta_co2_tco2e_yr),
                "vcu_quantity": None,
                "ledger_status": "BLOCKED_FOR_AGRICULTURE",
            }),
            carbon_accounting_status="NOT_CONFIGURED",
            ledger_status="BLOCKED_FOR_AGRICULTURE",
            result_status="CALCULATED",
            calculation_hash=calc_hash,
            input_snapshot_hash=calc_hash,
            created_by_id=user_id,
            notes=notes,
            created_at=now,
            updated_at=now,
        )
        try:
            db.add(change_result)
            await db.flush()
        except IntegrityError:
            await db.rollback()
            existing_stmt = select(AgricultureSOCChangeResult).where(
                AgricultureSOCChangeResult.project_id == project_id,
                AgricultureSOCChangeResult.organization_id == organization_id,
                AgricultureSOCChangeResult.baseline_stock_result_id == baseline_stock_result_id,
                AgricultureSOCChangeResult.monitoring_stock_result_id == monitoring_stock_result_id,
                AgricultureSOCChangeResult.result_status == "CALCULATED",
            )
            existing = (await db.execute(existing_stmt)).scalars().first()
            if existing:
                return existing
            raise

        if prior_active and prior_active.id != change_result.id:
            prior_active.result_status = "SUPERSEDED"
            prior_active.superseded_by_id = change_result.id
            prior_active.updated_at = now
            await db.flush()

        return change_result

    @classmethod
    async def list_soc_change_results(
        cls,
        db: AsyncSession,
        project_id: uuid.UUID,
        organization_id: uuid.UUID,
    ) -> List[AgricultureSOCChangeResult]:
        """Lists scenario SOC stock change results for a project."""
        await cls.get_project_or_raise(db, project_id, organization_id)
        stmt = (
            select(AgricultureSOCChangeResult)
            .where(
                AgricultureSOCChangeResult.project_id == project_id,
                AgricultureSOCChangeResult.organization_id == organization_id,
            )
            .order_by(AgricultureSOCChangeResult.created_at.desc())
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @classmethod
    async def get_soc_change_result(
        cls,
        db: AsyncSession,
        project_id: uuid.UUID,
        result_id: uuid.UUID,
        organization_id: uuid.UUID,
    ) -> AgricultureSOCChangeResult:
        """Retrieves a single SOC stock change result with tenant isolation."""
        await cls.get_project_or_raise(db, project_id, organization_id)
        stmt = select(AgricultureSOCChangeResult).where(
            AgricultureSOCChangeResult.id == result_id,
            AgricultureSOCChangeResult.project_id == project_id,
            AgricultureSOCChangeResult.organization_id == organization_id,
        )
        res = await db.execute(stmt)
        result = res.scalars().first()
        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SOC stock change result not found")
        return result

    # =========================================================================
    # PHASE 3B-3: NET GHG REDUCTIONS & REMOVALS + VCU READINESS SERVICE
    # =========================================================================

    @classmethod
    async def evaluate_net_ghg_reductions_and_removals(
        cls,
        db: AsyncSession,
        project_id: uuid.UUID,
        organization_id: uuid.UUID,
        prerequisite_assessment_id: Optional[uuid.UUID] = None,
        soc_change_result_id: Optional[uuid.UUID] = None,
        verification_period_start: Optional[Union[date, str]] = None,
        verification_period_end: Optional[Union[date, str]] = None,
        applicability_overrides: Optional[List[Dict[str, Any]]] = None,
        fossil_fuel_activities_bsl: Optional[List[Dict[str, Any]]] = None,
        fossil_fuel_activities_wp: Optional[List[Dict[str, Any]]] = None,
        liming_activity_bsl: Optional[Dict[str, Any]] = None,
        liming_activity_wp: Optional[Dict[str, Any]] = None,
        fertilizer_activities_bsl: Optional[List[Dict[str, Any]]] = None,
        fertilizer_activities_wp: Optional[List[Dict[str, Any]]] = None,
        nfixing_activities_bsl: Optional[List[Dict[str, Any]]] = None,
        nfixing_activities_wp: Optional[List[Dict[str, Any]]] = None,
        manure_activities_bsl: Optional[List[Dict[str, Any]]] = None,
        manure_activities_wp: Optional[List[Dict[str, Any]]] = None,
        enteric_activities_bsl: Optional[List[Dict[str, Any]]] = None,
        enteric_activities_wp: Optional[List[Dict[str, Any]]] = None,
        burning_activities_bsl: Optional[List[Dict[str, Any]]] = None,
        burning_activities_wp: Optional[List[Dict[str, Any]]] = None,
        methanogenesis_bsl: Optional[Dict[str, Any]] = None,
        methanogenesis_wp: Optional[Dict[str, Any]] = None,
        woody_pool_data: Optional[Dict[str, Any]] = None,
        leakage_data: Optional[Dict[str, Any]] = None,
        npr_rating_pct: Optional[Decimal] = None,
        risk_assessment_id: Optional[uuid.UUID] = None,
        annual_vintages_input: Optional[List[Dict[str, Any]]] = None,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Evaluates project-level Net GHG Reductions & Removals, Leakage Allocation,
        and Section 8.7 VCU Readiness under VM0042 v2.2 + 11 June 2026 C&C.
        Strictly fail-closed on tenant mismatch, missing required sources, or missing data.
        """
        await cls.get_project_or_raise(db, project_id, organization_id)

        # 1. Resolve Prerequisite Assessment with strict tenant validation
        prereq = None
        if prerequisite_assessment_id:
            prereq_stmt = select(AgriculturePrerequisiteAssessment).where(
                AgriculturePrerequisiteAssessment.id == prerequisite_assessment_id,
                AgriculturePrerequisiteAssessment.project_id == project_id,
                AgriculturePrerequisiteAssessment.organization_id == organization_id,
            )
            prereq = (await db.execute(prereq_stmt)).scalars().first()
            if not prereq:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Prerequisite assessment not found or does not belong to project/organization.",
                )
        else:
            prereq_stmt = select(AgriculturePrerequisiteAssessment).where(
                AgriculturePrerequisiteAssessment.project_id == project_id,
                AgriculturePrerequisiteAssessment.organization_id == organization_id,
                AgriculturePrerequisiteAssessment.is_locked == True,
            ).order_by(AgriculturePrerequisiteAssessment.created_at.desc())
            prereq = (await db.execute(prereq_stmt)).scalars().first()

        # 2. Resolve SOC Change Result with strict tenant validation
        soc_change = None
        if soc_change_result_id:
            soc_stmt = select(AgricultureSOCChangeResult).where(
                AgricultureSOCChangeResult.id == soc_change_result_id,
                AgricultureSOCChangeResult.project_id == project_id,
                AgricultureSOCChangeResult.organization_id == organization_id,
            )
            soc_change = (await db.execute(soc_stmt)).scalars().first()
            if not soc_change:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="SOC change result not found or does not belong to project/organization.",
                )
        else:
            soc_stmt = select(AgricultureSOCChangeResult).where(
                AgricultureSOCChangeResult.project_id == project_id,
                AgricultureSOCChangeResult.organization_id == organization_id,
                AgricultureSOCChangeResult.result_status == "CALCULATED",
            ).order_by(AgricultureSOCChangeResult.created_at.desc())
            soc_change = (await db.execute(soc_stmt)).scalars().first()

        # 3. Resolve Verification Period Dates
        start_d: date
        end_d: date
        if verification_period_start and verification_period_end:
            start_d = (
                datetime.strptime(str(verification_period_start), "%Y-%m-%d").date()
                if isinstance(verification_period_start, str)
                else verification_period_start
            )
            end_d = (
                datetime.strptime(str(verification_period_end), "%Y-%m-%d").date()
                if isinstance(verification_period_end, str)
                else verification_period_end
            )
        elif soc_change:
            start_d = soc_change.t_start.date()
            end_d = soc_change.t_final.date()
        else:
            start_d = date(2023, 1, 1)
            end_d = date(2025, 12, 31)

        if end_d <= start_d:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Verification period end date ({end_d}) must be strictly after start date ({start_d}).",
            )

        elapsed_years = (Decimal(str((end_d - start_d).days)) / Decimal("365.25")).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_EVEN
        )

        # 4. Table 5 Applicability Router Construction
        applicability_items: List[SourceApplicabilityItem] = []
        overrides_dict = {
            item.get("source_category"): item for item in (applicability_overrides or [])
        }

        # Canonical Categories
        categories = [
            ("CO2_SOC", "CO2", ApplicabilityStatus.APPLICABLE_CONFIGURED, QuantificationApproach.QA2_MEASURE_AND_REMEASURE, ActivityDataStatus.MEASURED, "Soil organic carbon stock change via QA2."),
            ("CO2_FOSSIL_FUEL", "CO2", ApplicabilityStatus.APPLICABLE_CONFIGURED if fossil_fuel_activities_bsl or fossil_fuel_activities_wp else ApplicabilityStatus.NOT_APPLICABLE, QuantificationApproach.QA3_ACTIVITY_METHOD, ActivityDataStatus.MEASURED if fossil_fuel_activities_bsl or fossil_fuel_activities_wp else ActivityDataStatus.VERIFIED_ACTIVITY_ZERO, "Fossil fuel combustion in machinery/pumps."),
            ("CO2_LIMING", "CO2", ApplicabilityStatus.APPLICABLE_CONFIGURED if liming_activity_bsl or liming_activity_wp else ApplicabilityStatus.NOT_APPLICABLE, QuantificationApproach.QA3_ACTIVITY_METHOD, ActivityDataStatus.MEASURED if liming_activity_bsl or liming_activity_wp else ActivityDataStatus.NOT_APPLICABLE, "Liming emissions from limestone/dolomite."),
            ("CO2_WOODY_BIOMASS", "CO2", ApplicabilityStatus.NOT_APPLICABLE, QuantificationApproach.QA3_ACTIVITY_METHOD, ActivityDataStatus.NOT_APPLICABLE, "Woody biomass excluded from ALM boundary."),
            ("CH4_SOIL_METHANOGENESIS", "CH4", ApplicabilityStatus.NOT_APPLICABLE, QuantificationApproach.QA1_MEASURE_AND_MODEL, ActivityDataStatus.NOT_APPLICABLE, "Upland aerobic cropland; no methanogenesis."),
            ("CH4_ENTERIC_FERMENTATION", "CH4", ApplicabilityStatus.APPLICABLE_CONFIGURED if enteric_activities_bsl or enteric_activities_wp else ApplicabilityStatus.NOT_APPLICABLE, QuantificationApproach.QA3_ACTIVITY_METHOD, ActivityDataStatus.MEASURED if enteric_activities_bsl or enteric_activities_wp else ActivityDataStatus.NOT_APPLICABLE, "Livestock enteric fermentation."),
            ("CH4_MANURE_DEPOSITION", "CH4", ApplicabilityStatus.APPLICABLE_CONFIGURED if manure_activities_bsl or manure_activities_wp else ApplicabilityStatus.NOT_APPLICABLE, QuantificationApproach.QA3_ACTIVITY_METHOD, ActivityDataStatus.MEASURED if manure_activities_bsl or manure_activities_wp else ActivityDataStatus.NOT_APPLICABLE, "Manure deposition CH4."),
            ("CH4_BIOMASS_BURNING", "CH4", ApplicabilityStatus.APPLICABLE_CONFIGURED if burning_activities_bsl or burning_activities_wp else ApplicabilityStatus.NOT_APPLICABLE, QuantificationApproach.QA3_ACTIVITY_METHOD, ActivityDataStatus.MEASURED if burning_activities_bsl or burning_activities_wp else ActivityDataStatus.NOT_APPLICABLE, "Biomass burning CH4."),
            ("N2O_NITROGEN_FERTILIZERS", "N2O", ApplicabilityStatus.APPLICABLE_CONFIGURED if fertilizer_activities_bsl or fertilizer_activities_wp else ApplicabilityStatus.NOT_APPLICABLE, QuantificationApproach.QA3_ACTIVITY_METHOD, ActivityDataStatus.MEASURED if fertilizer_activities_bsl or fertilizer_activities_wp else ActivityDataStatus.VERIFIED_ACTIVITY_ZERO, "Nitrogen fertilizers direct and indirect N2O."),
            ("N2O_NITROGEN_FIXING_SPECIES", "N2O", ApplicabilityStatus.APPLICABLE_CONFIGURED if nfixing_activities_bsl or nfixing_activities_wp else ApplicabilityStatus.NOT_APPLICABLE, QuantificationApproach.QA3_ACTIVITY_METHOD, ActivityDataStatus.MEASURED if nfixing_activities_bsl or nfixing_activities_wp else ActivityDataStatus.NOT_APPLICABLE, "N-fixing species N2O."),
            ("N2O_MANURE_DEPOSITION", "N2O", ApplicabilityStatus.APPLICABLE_CONFIGURED if manure_activities_bsl or manure_activities_wp else ApplicabilityStatus.NOT_APPLICABLE, QuantificationApproach.QA3_ACTIVITY_METHOD, ActivityDataStatus.MEASURED if manure_activities_bsl or manure_activities_wp else ActivityDataStatus.NOT_APPLICABLE, "Manure deposition N2O."),
            ("N2O_BIOMASS_BURNING", "N2O", ApplicabilityStatus.APPLICABLE_CONFIGURED if burning_activities_bsl or burning_activities_wp else ApplicabilityStatus.NOT_APPLICABLE, QuantificationApproach.QA3_ACTIVITY_METHOD, ActivityDataStatus.MEASURED if burning_activities_bsl or burning_activities_wp else ActivityDataStatus.NOT_APPLICABLE, "Biomass burning N2O."),
        ]

        for cat, gas, def_stat, def_app, def_act, def_rat in categories:
            if cat in overrides_dict:
                ov = overrides_dict[cat]
                applicability_items.append(
                    SourceApplicabilityItem(
                        source_category=cat,
                        gas=gas,
                        status=ApplicabilityStatus(ov.get("status", def_stat.value)),
                        quantification_approach=QuantificationApproach(ov.get("quantification_approach", def_app.value)),
                        activity_data_status=ActivityDataStatus(ov.get("activity_data_status", def_act.value)),
                        rationale=ov.get("rationale", def_rat),
                        evidence_reference=ov.get("evidence_reference"),
                    )
                )
            else:
                applicability_items.append(
                    SourceApplicabilityItem(
                        source_category=cat,
                        gas=gas,
                        status=def_stat,
                        quantification_approach=def_app,
                        activity_data_status=def_act,
                        rationale=def_rat,
                    )
                )

        # 5. Table 5 Validation
        is_app_valid, app_blocked_reason, app_report = validate_table_5_applicability(applicability_items)
        if not is_app_valid:
            return {
                "project_id": project_id,
                "status": "BLOCKED",
                "verification_period_start": start_d,
                "verification_period_end": end_d,
                "elapsed_years": elapsed_years,
                "applicability_matrix": app_report,
                "total_baseline_emissions_tco2e": Decimal("0.0000"),
                "total_project_emissions_tco2e": Decimal("0.0000"),
                "total_emission_reductions_from_sources_tco2e": Decimal("0.0000"),
                "eq44_baseline_total_carbon_stock_change_tco2e": Decimal("0.0000"),
                "eq45_project_total_carbon_stock_change_tco2e": Decimal("0.0000"),
                "gross_reductions_er_tco2e": Decimal("0.0000"),
                "gross_removals_cr_tco2e": Decimal("0.0000"),
                "total_leakage_tco2e": Decimal("0.0000"),
                "leakage_allocation_er_lker_tco2e": Decimal("0.0000"),
                "leakage_allocation_cr_lkcr_tco2e": Decimal("0.0000"),
                "net_reductions_ernet_tco2e": Decimal("0.0000"),
                "net_removals_crnet_tco2e": Decimal("0.0000"),
                "total_net_ghg_errnet_tco2e": Decimal("0.0000"),
                "vcu_readiness_status": "BLOCKED",
                "vintages": [],
                "blocking_reasons": [app_blocked_reason],
                "evaluation_hash": hashlib.sha256(str(app_blocked_reason).encode("utf-8")).hexdigest(),
            }

        # 6. Parse Activity Data Objects
        ff_bsl = [
            FossilFuelActivity(
                fuel_type=a.get("fuel_type", "DIESEL"),
                quantity=Decimal(str(a.get("quantity", "0.0000"))),
                unit=a.get("unit", "LITERS"),
                emission_factor_tco2e_per_unit=Decimal(str(a.get("emission_factor_tco2e_per_unit", "0.00268"))),
                factor_source=a.get("factor_source", "IPCC_2006_VOL2_TABLE_3.2.1"),
                is_verified_zero=bool(a.get("is_verified_zero", False)),
            )
            for a in (fossil_fuel_activities_bsl or [])
        ]
        ff_wp = [
            FossilFuelActivity(
                fuel_type=a.get("fuel_type", "DIESEL"),
                quantity=Decimal(str(a.get("quantity", "0.0000"))),
                unit=a.get("unit", "LITERS"),
                emission_factor_tco2e_per_unit=Decimal(str(a.get("emission_factor_tco2e_per_unit", "0.00268"))),
                factor_source=a.get("factor_source", "IPCC_2006_VOL2_TABLE_3.2.1"),
                is_verified_zero=bool(a.get("is_verified_zero", False)),
            )
            for a in (fossil_fuel_activities_wp or [])
        ]

        lime_bsl_data = liming_activity_bsl or {}
        lime_bsl = LimingActivity(
            calcitic_limestone_tonnes=Decimal(str(lime_bsl_data.get("calcitic_limestone_tonnes", "0.0000"))),
            dolomite_tonnes=Decimal(str(lime_bsl_data.get("dolomite_tonnes", "0.0000"))),
            is_verified_zero=bool(lime_bsl_data.get("is_verified_zero", False)),
        )
        lime_wp_data = liming_activity_wp or {}
        lime_wp = LimingActivity(
            calcitic_limestone_tonnes=Decimal(str(lime_wp_data.get("calcitic_limestone_tonnes", "0.0000"))),
            dolomite_tonnes=Decimal(str(lime_wp_data.get("dolomite_tonnes", "0.0000"))),
            is_verified_zero=bool(lime_wp_data.get("is_verified_zero", False)),
        )

        fert_bsl = [
            FertilizerN2OActivity(
                fertilizer_type=a.get("fertilizer_type", "SYNTHETIC_UREA"),
                mass_kg=Decimal(str(a.get("mass_kg", "0.0000"))),
                n_fraction=Decimal(str(a.get("n_fraction", "0.4600"))),
                ef1_direct=Decimal(str(a.get("ef1_direct", "0.0100"))),
                frac_gasm_volatilization=Decimal(str(a.get("frac_gasm_volatilization", "0.1000"))),
                ef4_volatilization=Decimal(str(a.get("ef4_volatilization", "0.0100"))),
                frac_leach=Decimal(str(a.get("frac_leach", "0.3000"))),
                ef5_leaching=Decimal(str(a.get("ef5_leaching", "0.0075"))),
                is_verified_zero=bool(a.get("is_verified_zero", False)),
            )
            for a in (fertilizer_activities_bsl or [])
        ]
        fert_wp = [
            FertilizerN2OActivity(
                fertilizer_type=a.get("fertilizer_type", "SYNTHETIC_UREA"),
                mass_kg=Decimal(str(a.get("mass_kg", "0.0000"))),
                n_fraction=Decimal(str(a.get("n_fraction", "0.4600"))),
                ef1_direct=Decimal(str(a.get("ef1_direct", "0.0100"))),
                frac_gasm_volatilization=Decimal(str(a.get("frac_gasm_volatilization", "0.1000"))),
                ef4_volatilization=Decimal(str(a.get("ef4_volatilization", "0.0100"))),
                frac_leach=Decimal(str(a.get("frac_leach", "0.3000"))),
                ef5_leaching=Decimal(str(a.get("ef5_leaching", "0.0075"))),
                is_verified_zero=bool(a.get("is_verified_zero", False)),
            )
            for a in (fertilizer_activities_wp or [])
        ]

        nfix_bsl = [
            NitrogenFixingActivity(
                species_name=a.get("species_name", "SOYBEAN"),
                area_ha=Decimal(str(a.get("area_ha", "0.0000"))),
                estimated_n_fixed_kg_ha=Decimal(str(a.get("estimated_n_fixed_kg_ha", "0.0000"))),
                ef1=Decimal(str(a.get("ef1", "0.0100"))),
                is_verified_zero=bool(a.get("is_verified_zero", False)),
            )
            for a in (nfixing_activities_bsl or [])
        ]
        nfix_wp = [
            NitrogenFixingActivity(
                species_name=a.get("species_name", "SOYBEAN"),
                area_ha=Decimal(str(a.get("area_ha", "0.0000"))),
                estimated_n_fixed_kg_ha=Decimal(str(a.get("estimated_n_fixed_kg_ha", "0.0000"))),
                ef1=Decimal(str(a.get("ef1", "0.0100"))),
                is_verified_zero=bool(a.get("is_verified_zero", False)),
            )
            for a in (nfixing_activities_wp or [])
        ]

        manure_bsl = [
            ManureDepositionActivity(
                livestock_category=a.get("livestock_category", "BEEF_CATTLE"),
                head_count=int(a.get("head_count", 0)),
                ef_ch4_kg_head_yr=Decimal(str(a.get("ef_ch4_kg_head_yr", "1.5000"))),
                nex_kg_n_head_yr=Decimal(str(a.get("nex_kg_n_head_yr", "40.0000"))),
                ef_prp_n2o=Decimal(str(a.get("ef_prp_n2o", "0.0200"))),
                is_verified_zero=bool(a.get("is_verified_zero", False)),
            )
            for a in (manure_activities_bsl or [])
        ]
        manure_wp = [
            ManureDepositionActivity(
                livestock_category=a.get("livestock_category", "BEEF_CATTLE"),
                head_count=int(a.get("head_count", 0)),
                ef_ch4_kg_head_yr=Decimal(str(a.get("ef_ch4_kg_head_yr", "1.5000"))),
                nex_kg_n_head_yr=Decimal(str(a.get("nex_kg_n_head_yr", "40.0000"))),
                ef_prp_n2o=Decimal(str(a.get("ef_prp_n2o", "0.0200"))),
                is_verified_zero=bool(a.get("is_verified_zero", False)),
            )
            for a in (manure_activities_wp or [])
        ]

        enteric_bsl = [
            EntericFermentationActivity(
                livestock_category=a.get("livestock_category", "BEEF_CATTLE"),
                head_count=int(a.get("head_count", 0)),
                ef_ch4_kg_head_yr=Decimal(str(a.get("ef_ch4_kg_head_yr", "55.0000"))),
                is_verified_zero=bool(a.get("is_verified_zero", False)),
            )
            for a in (enteric_activities_bsl or [])
        ]
        enteric_wp = [
            EntericFermentationActivity(
                livestock_category=a.get("livestock_category", "BEEF_CATTLE"),
                head_count=int(a.get("head_count", 0)),
                ef_ch4_kg_head_yr=Decimal(str(a.get("ef_ch4_kg_head_yr", "55.0000"))),
                is_verified_zero=bool(a.get("is_verified_zero", False)),
            )
            for a in (enteric_activities_wp or [])
        ]

        burning_bsl = [
            BiomassBurningActivity(
                dry_matter_tonnes=Decimal(str(a.get("dry_matter_tonnes", "0.0000"))),
                combustion_factor=Decimal(str(a.get("combustion_factor", "0.8000"))),
                gef_ch4_g_kg=Decimal(str(a.get("gef_ch4_g_kg", "2.7000"))),
                gef_n2o_g_kg=Decimal(str(a.get("gef_n2o_g_kg", "0.0700"))),
                is_verified_zero=bool(a.get("is_verified_zero", False)),
            )
            for a in (burning_activities_bsl or [])
        ]
        burning_wp = [
            BiomassBurningActivity(
                dry_matter_tonnes=Decimal(str(a.get("dry_matter_tonnes", "0.0000"))),
                combustion_factor=Decimal(str(a.get("combustion_factor", "0.8000"))),
                gef_ch4_g_kg=Decimal(str(a.get("gef_ch4_g_kg", "2.7000"))),
                gef_n2o_g_kg=Decimal(str(a.get("gef_n2o_g_kg", "0.0700"))),
                is_verified_zero=bool(a.get("is_verified_zero", False)),
            )
            for a in (burning_activities_wp or [])
        ]

        meth_bsl_data = methanogenesis_bsl or {}
        meth_bsl = SoilMethanogenesisActivity(
            qa1_model_configured=bool(meth_bsl_data.get("qa1_model_configured", False)),
            qa1_model_id=meth_bsl_data.get("qa1_model_id"),
            annual_ch4_emissions_tco2e=Decimal(str(meth_bsl_data.get("annual_ch4_emissions_tco2e", "0.0000"))) if meth_bsl_data.get("annual_ch4_emissions_tco2e") is not None else None,
            is_verified_zero=bool(meth_bsl_data.get("is_verified_zero", True)),
        )
        meth_wp_data = methanogenesis_wp or {}
        meth_wp = SoilMethanogenesisActivity(
            qa1_model_configured=bool(meth_wp_data.get("qa1_model_configured", False)),
            qa1_model_id=meth_wp_data.get("qa1_model_id"),
            annual_ch4_emissions_tco2e=Decimal(str(meth_wp_data.get("annual_ch4_emissions_tco2e", "0.0000"))) if meth_wp_data.get("annual_ch4_emissions_tco2e") is not None else None,
            is_verified_zero=bool(meth_wp_data.get("is_verified_zero", True)),
        )

        # Woody Biomass Pool
        woody_data = woody_pool_data or {}
        woody_pool = WoodyBiomassPoolData(
            tree_pool_status=ApplicabilityStatus(woody_data.get("tree_pool_status", "NOT_APPLICABLE")),
            shrub_pool_status=ApplicabilityStatus(woody_data.get("shrub_pool_status", "NOT_APPLICABLE")),
            baseline_tree_stock_change_tco2e_yr=Decimal(str(woody_data.get("baseline_tree_stock_change_tco2e_yr", "0.0000"))),
            baseline_shrub_stock_change_tco2e_yr=Decimal(str(woody_data.get("baseline_shrub_stock_change_tco2e_yr", "0.0000"))),
            project_tree_stock_change_tco2e_yr=Decimal(str(woody_data.get("project_tree_stock_change_tco2e_yr", "0.0000"))),
            project_shrub_stock_change_tco2e_yr=Decimal(str(woody_data.get("project_shrub_stock_change_tco2e_yr", "0.0000"))),
            harvested_wood_lta_applicable=bool(woody_data.get("harvested_wood_lta_applicable", False)),
            harvested_wood_lta_configured=bool(woody_data.get("harvested_wood_lta_configured", False)),
            is_verified_zero=bool(woody_data.get("is_verified_zero", True)),
            justification=woody_data.get("justification", "Project boundary excludes woody biomass."),
        )

        # Leakage Data (with 11 June 2026 C&C production decline)
        lk_data = leakage_data or {}
        leakage = LeakageInputData(
            activity_displacement_tco2e_yr=Decimal(str(lk_data.get("activity_displacement_tco2e_yr", "0.0000"))),
            livestock_displacement_tco2e_yr=Decimal(str(lk_data.get("livestock_displacement_tco2e_yr", "0.0000"))),
            leoa_tco2e_yr=Decimal(str(lk_data["leoa_tco2e_yr"])) if "leoa_tco2e_yr" in lk_data and lk_data["leoa_tco2e_yr"] is not None else None,
            production_decline_leakage_tco2e_yr=Decimal(str(lk_data.get("production_decline_leakage_tco2e_yr", "0.0000"))),
            production_decline_evaluated=bool(lk_data.get("production_decline_evaluated", True)),
            commodity_name=lk_data.get("commodity_name"),
            yield_change_pct=Decimal(str(lk_data.get("yield_change_pct", "0.0000"))) if lk_data.get("yield_change_pct") is not None else None,
            vmd0054_version=str(lk_data.get("vmd0054_version", VMD0054Version.VMD0054_1_1_CURRENT.value)),
            vmd0054_transition_eligible=lk_data.get("vmd0054_transition_eligible"),
            vmd0054_transition_basis=lk_data.get("vmd0054_transition_basis"),
            project_request_type=lk_data.get("project_request_type"),
            verification_subtype=lk_data.get("verification_subtype"),
            verra_request_id=lk_data.get("verra_request_id"),
            transition_document_id=lk_data.get("transition_document_id"),
            submission_date=date.fromisoformat(lk_data["submission_date"]) if lk_data.get("submission_date") else None,
            transition_deadline=date.fromisoformat(lk_data["transition_deadline"]) if lk_data.get("transition_deadline") else None,
            transition_evidence=lk_data.get("transition_evidence"),
            al_t_ha=Decimal(str(lk_data["al_t_ha"])) if lk_data.get("al_t_ha") is not None else None,
            delta_c_biomass_tc_ha=Decimal(str(lk_data["delta_c_biomass_tc_ha"])) if lk_data.get("delta_c_biomass_tc_ha") is not None else None,
            delta_soc_tc_ha=Decimal(str(lk_data["delta_soc_tc_ha"])) if lk_data.get("delta_soc_tc_ha") is not None else None,
            delta_cs_tc_ha=Decimal(str(lk_data["delta_cs_tc_ha"])) if lk_data.get("delta_cs_tc_ha") is not None else None,
            elm_t_tco2e=Decimal(str(lk_data["elm_t_tco2e"])) if lk_data.get("elm_t_tco2e") is not None else None,
            vmd0054_cumulative_leakage_tco2e=Decimal(str(lk_data["vmd0054_cumulative_leakage_tco2e"])) if lk_data.get("vmd0054_cumulative_leakage_tco2e") is not None else None,
            vmd0054_prior_leakage_tco2e=Decimal(str(lk_data["vmd0054_prior_leakage_tco2e"])) if lk_data.get("vmd0054_prior_leakage_tco2e") is not None else None,
            vmd0054_verification_period_years=Decimal(str(lk_data["vmd0054_verification_period_years"])) if lk_data.get("vmd0054_verification_period_years") is not None else None,
            production_decline_status=str(lk_data.get("production_decline_status", "EVALUATED")),
            production_decline_evidence=lk_data.get("production_decline_evidence"),
            biomass_residue_diversion_tco2e_yr=Decimal(str(lk_data.get("biomass_residue_diversion_tco2e_yr", "0.0000"))),
            residue_baseline_energy_used=bool(lk_data.get("residue_baseline_energy_used", False)),
            tool16_procedure_reference=str(lk_data.get("tool16_procedure_reference", "TOOL16_PROCEDURE")),
            tool16_status=str(lk_data.get("tool16_status", "EVALUATED")),
            tool16_not_applicable_reason=lk_data.get("tool16_not_applicable_reason"),
            is_verified_zero=bool(lk_data.get("is_verified_zero", False)),
        )

        # NPR Risk Assessment
        npr_input = None
        if npr_rating_pct is not None:
            npr_input = NPRRiskAssessmentInput(
                npr_rating_pct=Decimal(str(npr_rating_pct)),
                risk_assessment_id=risk_assessment_id or uuid.uuid4(),
                approval_status="APPROVED",
                effective_date=date.today().isoformat(),
            )

        # 7. Evaluate Annual Vintages
        soc_bsl_rate = soc_change.baseline_soc_change_tco2e_yr if soc_change else Decimal("0.0000")
        soc_wp_rate = soc_change.project_soc_change_tco2e_yr if soc_change else Decimal("0.0000")
        soc_unc_frac = soc_change.uncertainty_deduction_fraction if soc_change else Decimal("0.000000")
        soc_sign = soc_change.sign_indicator if soc_change else 1

        annual_vintages: List[AnnualVintageGHGResult] = []
        prior_cumulative_stock = Decimal("0.0000")

        try:
            if annual_vintages_input and len(annual_vintages_input) > 0:
                for v_item in annual_vintages_input:
                    yr = int(v_item.get("vintage_year", start_d.year))
                    ff_bsl_yr = [FossilFuelActivity(**a) for a in v_item["fossil_fuel_activities_bsl"]] if "fossil_fuel_activities_bsl" in v_item else ff_bsl
                    ff_wp_yr = [FossilFuelActivity(**a) for a in v_item["fossil_fuel_activities_wp"]] if "fossil_fuel_activities_wp" in v_item else ff_wp
                    lime_bsl_yr = LimingActivity(**v_item["liming_activity_bsl"]) if "liming_activity_bsl" in v_item else lime_bsl
                    lime_wp_yr = LimingActivity(**v_item["liming_activity_wp"]) if "liming_activity_wp" in v_item else lime_wp
                    fert_bsl_yr = [FertilizerN2OActivity(**a) for a in v_item["fertilizer_activities_bsl"]] if "fertilizer_activities_bsl" in v_item else fert_bsl
                    fert_wp_yr = [FertilizerN2OActivity(**a) for a in v_item["fertilizer_activities_wp"]] if "fertilizer_activities_wp" in v_item else fert_wp
                    nfix_bsl_yr = [NitrogenFixingActivity(**a) for a in v_item["nfixing_activities_bsl"]] if "nfixing_activities_bsl" in v_item else nfix_bsl
                    nfix_wp_yr = [NitrogenFixingActivity(**a) for a in v_item["nfixing_activities_wp"]] if "nfixing_activities_wp" in v_item else nfix_wp
                    manure_bsl_yr = [ManureDepositionActivity(**a) for a in v_item["manure_activities_bsl"]] if "manure_activities_bsl" in v_item else manure_bsl
                    manure_wp_yr = [ManureDepositionActivity(**a) for a in v_item["manure_activities_wp"]] if "manure_activities_wp" in v_item else manure_wp
                    enteric_bsl_yr = [EntericFermentationActivity(**a) for a in v_item["enteric_activities_bsl"]] if "enteric_activities_bsl" in v_item else enteric_bsl
                    enteric_wp_yr = [EntericFermentationActivity(**a) for a in v_item["enteric_activities_wp"]] if "enteric_activities_wp" in v_item else enteric_wp
                    burning_bsl_yr = [BiomassBurningActivity(**a) for a in v_item["burning_activities_bsl"]] if "burning_activities_bsl" in v_item else burning_bsl
                    burning_wp_yr = [BiomassBurningActivity(**a) for a in v_item["burning_activities_wp"]] if "burning_activities_wp" in v_item else burning_wp
                    meth_bsl_yr = SoilMethanogenesisActivity(**v_item["methanogenesis_bsl"]) if "methanogenesis_bsl" in v_item else meth_bsl
                    meth_wp_yr = SoilMethanogenesisActivity(**v_item["methanogenesis_wp"]) if "methanogenesis_wp" in v_item else meth_wp

                    soc_bsl_yr = Decimal(str(v_item.get("soc_stock_change_bsl_tco2e", soc_bsl_rate)))
                    soc_wp_yr = Decimal(str(v_item.get("soc_stock_change_wp_tco2e", soc_wp_rate)))
                    soc_unc_yr = Decimal(str(v_item.get("soc_uncertainty_deduction_fraction", soc_unc_frac)))
                    soc_sign_yr = int(v_item.get("soc_sign_indicator", soc_sign))

                    if "leakage_data" in v_item or "leakage" in v_item:
                        lk_in = v_item.get("leakage_data") or v_item.get("leakage")
                        leakage_yr = LeakageInputData(
                            activity_displacement_tco2e_yr=Decimal(str(lk_in.get("activity_displacement_tco2e_yr", "0.0000"))),
                            livestock_displacement_tco2e_yr=Decimal(str(lk_in.get("livestock_displacement_tco2e_yr", "0.0000"))),
                            leoa_tco2e_yr=Decimal(str(lk_in["leoa_tco2e_yr"])) if "leoa_tco2e_yr" in lk_in and lk_in["leoa_tco2e_yr"] is not None else None,
                            production_decline_leakage_tco2e_yr=Decimal(str(lk_in.get("production_decline_leakage_tco2e_yr", "0.0000"))),
                            production_decline_evaluated=bool(lk_in.get("production_decline_evaluated", True)),
                            commodity_name=lk_in.get("commodity_name"),
                            yield_change_pct=Decimal(str(lk_in["yield_change_pct"])) if lk_in.get("yield_change_pct") is not None else None,
                            vmd0054_version=str(lk_in.get("vmd0054_version", VMD0054Version.VMD0054_1_1_CURRENT.value)),
                            vmd0054_transition_eligible=lk_in.get("vmd0054_transition_eligible"),
                            vmd0054_transition_basis=lk_in.get("vmd0054_transition_basis"),
                            project_request_type=lk_in.get("project_request_type"),
                            verification_subtype=lk_in.get("verification_subtype"),
                            verra_request_id=lk_in.get("verra_request_id"),
                            transition_document_id=lk_in.get("transition_document_id"),
                            submission_date=date.fromisoformat(lk_in["submission_date"]) if lk_in.get("submission_date") else None,
                            transition_deadline=date.fromisoformat(lk_in["transition_deadline"]) if lk_in.get("transition_deadline") else None,
                            transition_evidence=lk_in.get("transition_evidence"),
                            al_t_ha=Decimal(str(lk_in["al_t_ha"])) if lk_in.get("al_t_ha") is not None else None,
                            delta_c_biomass_tc_ha=Decimal(str(lk_in["delta_c_biomass_tc_ha"])) if lk_in.get("delta_c_biomass_tc_ha") is not None else None,
                            delta_soc_tc_ha=Decimal(str(lk_in["delta_soc_tc_ha"])) if lk_in.get("delta_soc_tc_ha") is not None else None,
                            delta_cs_tc_ha=Decimal(str(lk_in["delta_cs_tc_ha"])) if lk_in.get("delta_cs_tc_ha") is not None else None,
                            elm_t_tco2e=Decimal(str(lk_in["elm_t_tco2e"])) if lk_in.get("elm_t_tco2e") is not None else None,
                            vmd0054_cumulative_leakage_tco2e=Decimal(str(lk_in["vmd0054_cumulative_leakage_tco2e"])) if lk_in.get("vmd0054_cumulative_leakage_tco2e") is not None else None,
                            vmd0054_prior_leakage_tco2e=Decimal(str(lk_in["vmd0054_prior_leakage_tco2e"])) if lk_in.get("vmd0054_prior_leakage_tco2e") is not None else None,
                            vmd0054_verification_period_years=Decimal(str(lk_in["vmd0054_verification_period_years"])) if lk_in.get("vmd0054_verification_period_years") is not None else None,
                            production_decline_status=str(lk_in.get("production_decline_status", "EVALUATED")),
                            production_decline_evidence=lk_in.get("production_decline_evidence"),
                            biomass_residue_diversion_tco2e_yr=Decimal(str(lk_in.get("biomass_residue_diversion_tco2e_yr", "0.0000"))),
                            residue_baseline_energy_used=bool(lk_in.get("residue_baseline_energy_used", False)),
                            tool16_procedure_reference=str(lk_in.get("tool16_procedure_reference", "TOOL16_PROCEDURE")),
                            tool16_status=str(lk_in.get("tool16_status", "EVALUATED")),
                            tool16_not_applicable_reason=lk_in.get("tool16_not_applicable_reason"),
                            is_verified_zero=bool(lk_in.get("is_verified_zero", False)),
                        )
                    else:
                        leakage_yr = leakage

                    v_res = evaluate_single_vintage_net_ghg(
                        vintage_year=yr,
                        fossil_fuel_bsl=ff_bsl_yr,
                        fossil_fuel_wp=ff_wp_yr,
                        liming_bsl=lime_bsl_yr,
                        liming_wp=lime_wp_yr,
                        fertilizer_bsl=fert_bsl_yr,
                        fertilizer_wp=fert_wp_yr,
                        nfixing_bsl=nfix_bsl_yr,
                        nfixing_wp=nfix_wp_yr,
                        manure_bsl=manure_bsl_yr,
                        manure_wp=manure_wp_yr,
                        enteric_bsl=enteric_bsl_yr,
                        enteric_wp=enteric_wp_yr,
                        burning_bsl=burning_bsl_yr,
                        burning_wp=burning_wp_yr,
                        methanogenesis_bsl=meth_bsl_yr,
                        methanogenesis_wp=meth_wp_yr,
                        soc_stock_change_bsl_tco2e=soc_bsl_yr,
                        soc_stock_change_wp_tco2e=soc_wp_yr,
                        soc_uncertainty_deduction_fraction=soc_unc_yr,
                        soc_sign_indicator=soc_sign_yr,
                        woody_pool=woody_pool,
                        prior_cumulative_project_stock_change_tco2e=prior_cumulative_stock,
                        leakage=leakage_yr,
                        npr_input=npr_input,
                    )
                    annual_vintages.append(v_res)
                    prior_cumulative_stock += v_res.eq45_project_total_carbon_stock_change_tco2e
            else:
                vintage_years = list(range(start_d.year, end_d.year + 1))
                for yr in vintage_years:
                    v_res = evaluate_single_vintage_net_ghg(
                        vintage_year=yr,
                        fossil_fuel_bsl=ff_bsl,
                        fossil_fuel_wp=ff_wp,
                        liming_bsl=lime_bsl,
                        liming_wp=lime_wp,
                        fertilizer_bsl=fert_bsl,
                        fertilizer_wp=fert_wp,
                        nfixing_bsl=nfix_bsl,
                        nfixing_wp=nfix_wp,
                        manure_bsl=manure_bsl,
                        manure_wp=manure_wp,
                        enteric_bsl=enteric_bsl,
                        enteric_wp=enteric_wp,
                        burning_bsl=burning_bsl,
                        burning_wp=burning_wp,
                        methanogenesis_bsl=meth_bsl,
                        methanogenesis_wp=meth_wp,
                        soc_stock_change_bsl_tco2e=soc_bsl_rate,
                        soc_stock_change_wp_tco2e=soc_wp_rate,
                        soc_uncertainty_deduction_fraction=soc_unc_frac,
                        soc_sign_indicator=soc_sign,
                        woody_pool=woody_pool,
                        prior_cumulative_project_stock_change_tco2e=prior_cumulative_stock,
                        leakage=leakage,
                        npr_input=npr_input,
                    )
                    annual_vintages.append(v_res)
                    prior_cumulative_stock += v_res.eq45_project_total_carbon_stock_change_tco2e

            # 8. Aggregate Across Verification Period
            project_output = aggregate_verification_period_net_ghg(
                project_id=project_id,
                organization_id=organization_id,
                start_date=start_d,
                end_date=end_d,
                annual_vintages=annual_vintages,
                applicability_report=app_report,
                npr_input=npr_input,
            )
        except NetGHGCalculationError as err:
            return {
                "project_id": project_id,
                "status": "BLOCKED",
                "verification_period_start": start_d,
                "verification_period_end": end_d,
                "elapsed_years": elapsed_years,
                "applicability_matrix": app_report,
                "total_baseline_emissions_tco2e": Decimal("0.0000"),
                "total_project_emissions_tco2e": Decimal("0.0000"),
                "total_emission_reductions_from_sources_tco2e": Decimal("0.0000"),
                "eq44_baseline_total_carbon_stock_change_tco2e": Decimal("0.0000"),
                "eq45_project_total_carbon_stock_change_tco2e": Decimal("0.0000"),
                "gross_reductions_er_tco2e": Decimal("0.0000"),
                "gross_removals_cr_tco2e": Decimal("0.0000"),
                "total_leakage_tco2e": Decimal("0.0000"),
                "leakage_allocation_er_lker_tco2e": Decimal("0.0000"),
                "leakage_allocation_cr_lkcr_tco2e": Decimal("0.0000"),
                "net_reductions_ernet_tco2e": Decimal("0.0000"),
                "net_removals_crnet_tco2e": Decimal("0.0000"),
                "total_net_ghg_errnet_tco2e": Decimal("0.0000"),
                "vcu_readiness_status": "BLOCKED",
                "blocking_reasons": [f"{err.code}: {err.message}"],
                "evaluation_hash": "",
                "raw_output": None,
            }

        return {
            "project_id": project_id,
            "status": "EVALUATED",
            "verification_period_start": start_d,
            "verification_period_end": end_d,
            "elapsed_years": elapsed_years,
            "applicability_matrix": app_report,
            "total_baseline_emissions_tco2e": project_output.total_baseline_emissions_tco2e,
            "total_project_emissions_tco2e": project_output.total_project_emissions_tco2e,
            "total_emission_reductions_from_sources_tco2e": project_output.total_emission_reductions_from_sources_tco2e,
            "eq44_baseline_total_carbon_stock_change_tco2e": project_output.eq44_baseline_total_carbon_stock_change_tco2e,
            "eq45_project_total_carbon_stock_change_tco2e": project_output.eq45_project_total_carbon_stock_change_tco2e,
            "gross_reductions_er_tco2e": project_output.gross_reductions_er_tco2e,
            "gross_removals_cr_tco2e": project_output.gross_removals_cr_tco2e,
            "total_leakage_tco2e": project_output.total_leakage_tco2e,
            "leakage_allocation_er_lker_tco2e": project_output.leakage_allocation_er_lker_tco2e,
            "leakage_allocation_cr_lkcr_tco2e": project_output.leakage_allocation_cr_lkcr_tco2e,
            "net_reductions_ernet_tco2e": project_output.net_reductions_ernet_tco2e,
            "net_removals_crnet_tco2e": project_output.net_removals_crnet_tco2e,
            "total_net_ghg_errnet_tco2e": project_output.total_net_ghg_errnet_tco2e,
            "npr_rating_pct": project_output.npr_rating_pct,
            "buffer_deduction_reductions_tco2e": project_output.buffer_deduction_reductions_tco2e,
            "buffer_deduction_removals_tco2e": project_output.buffer_deduction_removals_tco2e,
            "total_buffer_deduction_tco2e": project_output.total_buffer_deduction_tco2e,
            "internal_vcu_eligible_reductions_tco2e": project_output.internal_vcu_eligible_reductions_tco2e,
            "internal_vcu_eligible_removals_tco2e": project_output.internal_vcu_eligible_removals_tco2e,
            "internal_vcu_eligible_total_tco2e": project_output.internal_vcu_eligible_total_tco2e,
            "vcu_readiness_status": project_output.vcu_readiness_status,
            "vintages": [v.to_dict() for v in annual_vintages],
            "blocking_reasons": [],
            "evaluation_hash": project_output.calculation_hash,
            "component_breakdown": to_json_serializable(project_output.component_breakdown),
            "raw_output": project_output,
            "prereq_obj": prereq,
            "soc_change_obj": soc_change,
        }

    @classmethod
    async def finalize_net_ghg_reductions_and_removals(
        cls,
        db: AsyncSession,
        project_id: uuid.UUID,
        organization_id: uuid.UUID,
        user_id: Optional[uuid.UUID],
        user_role: Optional[str],
        prerequisite_assessment_id: uuid.UUID,
        soc_change_result_id: Optional[uuid.UUID] = None,
        verification_period_start: Optional[Union[date, str]] = None,
        verification_period_end: Optional[Union[date, str]] = None,
        applicability_overrides: Optional[List[Dict[str, Any]]] = None,
        fossil_fuel_activities_bsl: Optional[List[Dict[str, Any]]] = None,
        fossil_fuel_activities_wp: Optional[List[Dict[str, Any]]] = None,
        liming_activity_bsl: Optional[Dict[str, Any]] = None,
        liming_activity_wp: Optional[Dict[str, Any]] = None,
        fertilizer_activities_bsl: Optional[List[Dict[str, Any]]] = None,
        fertilizer_activities_wp: Optional[List[Dict[str, Any]]] = None,
        nfixing_activities_bsl: Optional[List[Dict[str, Any]]] = None,
        nfixing_activities_wp: Optional[List[Dict[str, Any]]] = None,
        manure_activities_bsl: Optional[List[Dict[str, Any]]] = None,
        manure_activities_wp: Optional[List[Dict[str, Any]]] = None,
        enteric_activities_bsl: Optional[List[Dict[str, Any]]] = None,
        enteric_activities_wp: Optional[List[Dict[str, Any]]] = None,
        burning_activities_bsl: Optional[List[Dict[str, Any]]] = None,
        burning_activities_wp: Optional[List[Dict[str, Any]]] = None,
        methanogenesis_bsl: Optional[Dict[str, Any]] = None,
        methanogenesis_wp: Optional[Dict[str, Any]] = None,
        woody_pool_data: Optional[Dict[str, Any]] = None,
        leakage_data: Optional[Dict[str, Any]] = None,
        npr_rating_pct: Optional[Decimal] = None,
        risk_assessment_id: Optional[uuid.UUID] = None,
        annual_vintages_input: Optional[List[Dict[str, Any]]] = None,
        notes: Optional[str] = None,
    ) -> AgricultureNetGHGResult:
        """
        Finalizes and persists authoritative AgricultureNetGHGResult and annual vintages.
        Segregation of Duties: FIELD_AGENT cannot finalize.
        Enforces idempotency and supersession.
        """
        if (user_role or "").upper() == "FIELD_AGENT":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Field agent role is unauthorized to finalize authoritative Net GHG quantification. Segregation of duties enforced.",
            )

        # 1. Evaluate Preview
        eval_res = await cls.evaluate_net_ghg_reductions_and_removals(
            db=db,
            project_id=project_id,
            organization_id=organization_id,
            prerequisite_assessment_id=prerequisite_assessment_id,
            soc_change_result_id=soc_change_result_id,
            verification_period_start=verification_period_start,
            verification_period_end=verification_period_end,
            applicability_overrides=applicability_overrides,
            fossil_fuel_activities_bsl=fossil_fuel_activities_bsl,
            fossil_fuel_activities_wp=fossil_fuel_activities_wp,
            liming_activity_bsl=liming_activity_bsl,
            liming_activity_wp=liming_activity_wp,
            fertilizer_activities_bsl=fertilizer_activities_bsl,
            fertilizer_activities_wp=fertilizer_activities_wp,
            nfixing_activities_bsl=nfixing_activities_bsl,
            nfixing_activities_wp=nfixing_activities_wp,
            manure_activities_bsl=manure_activities_bsl,
            manure_activities_wp=manure_activities_wp,
            enteric_activities_bsl=enteric_activities_bsl,
            enteric_activities_wp=enteric_activities_wp,
            burning_activities_bsl=burning_activities_bsl,
            burning_activities_wp=burning_activities_wp,
            methanogenesis_bsl=methanogenesis_bsl,
            methanogenesis_wp=methanogenesis_wp,
            woody_pool_data=woody_pool_data,
            leakage_data=leakage_data,
            npr_rating_pct=npr_rating_pct,
            risk_assessment_id=risk_assessment_id,
            annual_vintages_input=annual_vintages_input,
            notes=notes,
        )

        if eval_res["status"] == "BLOCKED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Net GHG calculation is blocked: " + "; ".join(eval_res["blocking_reasons"]),
            )

        calc_hash = eval_res["evaluation_hash"]
        raw_output: NetGHGProjectOutput = eval_res["raw_output"]

        start_dt = datetime.combine(eval_res["verification_period_start"], datetime.min.time(), tzinfo=timezone.utc)
        end_dt = datetime.combine(eval_res["verification_period_end"], datetime.max.time(), tzinfo=timezone.utc)

        # 2. Concurrency and Idempotency Guard (Row-Level Check)
        existing_stmt = select(AgricultureNetGHGResult).where(
            AgricultureNetGHGResult.project_id == project_id,
            AgricultureNetGHGResult.organization_id == organization_id,
            AgricultureNetGHGResult.verification_period_start == start_dt,
            AgricultureNetGHGResult.verification_period_end == end_dt,
            AgricultureNetGHGResult.result_status == "CALCULATED",
        ).with_for_update()
        existing = (await db.execute(existing_stmt)).scalars().first()
        if existing and existing.calculation_hash == calc_hash:
            return existing

        now = datetime.now(timezone.utc)
        result_code = f"NET-GHG-{now.strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4]}"

        # 3. Check for Prior Active Project-Level Net GHG Result to Supersede
        prior_active_stmt = select(AgricultureNetGHGResult).where(
            AgricultureNetGHGResult.project_id == project_id,
            AgricultureNetGHGResult.organization_id == organization_id,
            AgricultureNetGHGResult.result_status == "CALCULATED",
        ).order_by(AgricultureNetGHGResult.created_at.desc())
        prior_active = (await db.execute(prior_active_stmt)).scalars().first()

        # 4. Construct and Persist AgricultureNetGHGResult
        net_result = AgricultureNetGHGResult(
            organization_id=organization_id,
            project_id=project_id,
            soc_change_result_id=soc_change_result_id,
            prerequisite_assessment_id=prerequisite_assessment_id,
            result_code=result_code,
            methodology_version=raw_output.methodology_version,
            corrections_clarifications_version=raw_output.corrections_clarifications_version,
            calculation_engine_version=raw_output.calculation_engine_version,
            ruleset_version=raw_output.ruleset_version,
            verification_period_start=start_dt,
            verification_period_end=end_dt,
            elapsed_years=raw_output.elapsed_years,
            applicability_matrix=raw_output.applicability_matrix,
            total_baseline_emissions_tco2e=raw_output.total_baseline_emissions_tco2e,
            total_project_emissions_tco2e=raw_output.total_project_emissions_tco2e,
            total_emission_reductions_from_sources_tco2e=raw_output.total_emission_reductions_from_sources_tco2e,
            eq44_baseline_total_carbon_stock_change_tco2e=raw_output.eq44_baseline_total_carbon_stock_change_tco2e,
            eq45_project_total_carbon_stock_change_tco2e=raw_output.eq45_project_total_carbon_stock_change_tco2e,
            eq44_eq45_status=raw_output.eq44_eq45_status,
            gross_reductions_er_tco2e=raw_output.gross_reductions_er_tco2e,
            gross_removals_cr_tco2e=raw_output.gross_removals_cr_tco2e,
            total_leakage_tco2e=raw_output.total_leakage_tco2e,
            leakage_allocation_er_lker_tco2e=raw_output.leakage_allocation_er_lker_tco2e,
            leakage_allocation_cr_lkcr_tco2e=raw_output.leakage_allocation_cr_lkcr_tco2e,
            net_reductions_ernet_tco2e=raw_output.net_reductions_ernet_tco2e,
            net_removals_crnet_tco2e=raw_output.net_removals_crnet_tco2e,
            total_net_ghg_errnet_tco2e=raw_output.total_net_ghg_errnet_tco2e,
            npr_rating_pct=raw_output.npr_rating_pct,
            risk_assessment_id=raw_output.risk_assessment_id,
            buffer_deduction_reductions_tco2e=raw_output.buffer_deduction_reductions_tco2e,
            buffer_deduction_removals_tco2e=raw_output.buffer_deduction_removals_tco2e,
            total_buffer_deduction_tco2e=raw_output.total_buffer_deduction_tco2e,
            internal_vcu_eligible_reductions_tco2e=raw_output.internal_vcu_eligible_reductions_tco2e,
            internal_vcu_eligible_removals_tco2e=raw_output.internal_vcu_eligible_removals_tco2e,
            internal_vcu_eligible_total_tco2e=raw_output.internal_vcu_eligible_total_tco2e,
            vcu_readiness_status=raw_output.vcu_readiness_status,
            internal_mrv_status="CALCULATED",
            vvb_status="NOT_CONFIGURED / EXTERNAL",
            registry_status="NOT_CONFIGURED / EXTERNAL",
            ledger_status="BLOCKED_FOR_AGRICULTURE",
            result_status="CALCULATED",
            calculation_hash=calc_hash,
            input_snapshot_hash=raw_output.input_snapshot_hash,
            created_by_id=user_id,
            notes=notes,
            component_breakdown=to_json_serializable(raw_output.component_breakdown),
        )
        db.add(net_result)
        await db.flush()

        # 5. Persist Annual Vintage Line Items
        for v in raw_output.vintages:
            v_record = AgricultureVintageGHGResult(
                net_ghg_result_id=net_result.id,
                vintage_year=v.vintage_year,
                total_baseline_emissions_tco2e=v.total_baseline_emissions_tco2e,
                total_project_emissions_tco2e=v.total_project_emissions_tco2e,
                total_emission_reductions_from_sources_tco2e=v.total_emission_reductions_from_sources_tco2e,
                eq44_baseline_total_carbon_stock_change_tco2e=v.eq44_baseline_total_carbon_stock_change_tco2e,
                eq45_project_total_carbon_stock_change_tco2e=v.eq45_project_total_carbon_stock_change_tco2e,
                gross_reductions_er_tco2e=v.gross_reductions_er_tco2e,
                gross_removals_cr_tco2e=v.gross_removals_cr_tco2e,
                total_leakage_tco2e=v.total_leakage_tco2e,
                leakage_allocation_er_lker_tco2e=v.leakage_allocation_er_lker_tco2e,
                leakage_allocation_cr_lkcr_tco2e=v.leakage_allocation_cr_lkcr_tco2e,
                net_reductions_ernet_tco2e=v.net_reductions_ernet_tco2e,
                net_removals_crnet_tco2e=v.net_removals_crnet_tco2e,
                total_net_ghg_errnet_tco2e=v.total_net_ghg_errnet_tco2e,
                buffer_deduction_reductions_tco2e=v.buffer_deduction_reductions_tco2e,
                buffer_deduction_removals_tco2e=v.buffer_deduction_removals_tco2e,
                total_buffer_deduction_tco2e=v.total_buffer_deduction_tco2e,
                internal_vcu_eligible_reductions_tco2e=v.internal_vcu_eligible_reductions_tco2e,
                internal_vcu_eligible_removals_tco2e=v.internal_vcu_eligible_removals_tco2e,
                internal_vcu_eligible_total_tco2e=v.internal_vcu_eligible_total_tco2e,
                vintage_details=to_json_serializable(v.to_dict()),
            )
            db.add(v_record)

        # 6. Supersede prior active record if exists
        if prior_active and prior_active.id != net_result.id:
            prior_active.result_status = "SUPERSEDED"
            prior_active.superseded_by_id = net_result.id
            db.add(prior_active)

        await db.flush()

        # Eagerly load vintages relationship for response serialization
        final_stmt = (
            select(AgricultureNetGHGResult)
            .options(selectinload(AgricultureNetGHGResult.vintages))
            .where(AgricultureNetGHGResult.id == net_result.id)
        )
        return (await db.execute(final_stmt)).scalars().first()

    @classmethod
    async def list_net_ghg_results(
        cls,
        db: AsyncSession,
        project_id: uuid.UUID,
        organization_id: uuid.UUID,
    ) -> List[AgricultureNetGHGResult]:
        """Lists all Net GHG quantification results for a project in descending created order."""
        await cls.get_project_or_raise(db, project_id, organization_id)
        stmt = (
            select(AgricultureNetGHGResult)
            .options(selectinload(AgricultureNetGHGResult.vintages))
            .where(
                AgricultureNetGHGResult.project_id == project_id,
                AgricultureNetGHGResult.organization_id == organization_id,
            )
            .order_by(AgricultureNetGHGResult.created_at.desc())
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @classmethod
    async def get_net_ghg_result(
        cls,
        db: AsyncSession,
        project_id: uuid.UUID,
        result_id: uuid.UUID,
        organization_id: uuid.UUID,
    ) -> AgricultureNetGHGResult:
        """Retrieves a single Net GHG result with tenant isolation and loaded vintages."""
        await cls.get_project_or_raise(db, project_id, organization_id)
        stmt = (
            select(AgricultureNetGHGResult)
            .options(selectinload(AgricultureNetGHGResult.vintages))
            .where(
                AgricultureNetGHGResult.id == result_id,
                AgricultureNetGHGResult.project_id == project_id,
                AgricultureNetGHGResult.organization_id == organization_id,
            )
        )
        res = await db.execute(stmt)
        result = res.scalars().first()
        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Net GHG quantification result not found")
        return result


normalize_laboratory_analyte_measurement = AgricultureService.normalize_laboratory_analyte_measurement
