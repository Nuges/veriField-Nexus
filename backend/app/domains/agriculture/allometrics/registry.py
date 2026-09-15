"""
=============================================================================
VeriField Nexus — Allometric Model Registry
=============================================================================
Defines the authoritative Allometric Model Registry for forestry and agroforestry (VM0047 / BM FR05.002):
- Strictly separates ABOVEGROUND_BIOMASS (AGB) from BELOWGROUND_BIOMASS (BGB).
- Prohibits hardcoding a single universal equation (e.g. Chave 2014 is one selectable model).
- Prohibits conflating AGB and BGB; belowground biomass requires an approved root-to-shoot or belowground model.
- Maintains full provenance: model ID, version, citation, parameter source, and review status.
=============================================================================
"""

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class BiomassPoolType(str, Enum):
    ABOVEGROUND_BIOMASS = "ABOVEGROUND_BIOMASS"
    BELOWGROUND_BIOMASS = "BELOWGROUND_BIOMASS"


class ModelReviewStatus(str, Enum):
    APPROVED = "APPROVED"
    PEER_REVIEWED = "PEER_REVIEWED"
    PROJECT_SPECIFIC = "PROJECT_SPECIFIC"
    PROVISIONAL = "PROVISIONAL"


@dataclass
class AllometricModelDefinition:
    model_id: str
    name: str
    citation: str
    version: str
    pool_type: BiomassPoolType
    geographic_applicability: str
    species_applicability: str
    required_inputs: List[str]
    methodology_compatibility: List[str]
    parameter_source: str
    review_status: ModelReviewStatus
    compute_fn: Optional[Callable[..., float]] = field(default=None, repr=False)

    def to_metadata(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "name": self.name,
            "citation": self.citation,
            "version": self.version,
            "pool_type": self.pool_type.value,
            "geographic_applicability": self.geographic_applicability,
            "species_applicability": self.species_applicability,
            "required_inputs": self.required_inputs,
            "methodology_compatibility": self.methodology_compatibility,
            "parameter_source": self.parameter_source,
            "review_status": self.review_status.value,
        }


# ─── Compute Implementations ───

def _compute_chave_2014_agb(
    dbh_cm: float,
    height_m: Optional[float] = None,
    wood_density_g_cm3: float = 0.60,
    **kwargs,
) -> float:
    """
    Chave et al. (2014) Pantropical Aboveground Biomass Equation:
    - If height measured: AGB (kg) = 0.0673 * (rho * D^2 * H)^0.976
    - If height not measured: ln(AGB) = -1.803 + 0.976*ln(rho) + 2.673*ln(D) - 0.0299*(ln(D))^2
    """
    if dbh_cm <= 0 or wood_density_g_cm3 <= 0:
        return 0.0

    if height_m and height_m > 0:
        compound = wood_density_g_cm3 * (dbh_cm**2) * height_m
        return round(float(0.0673 * (compound**0.976)), 2)
    else:
        ln_d = math.log(dbh_cm)
        ln_rho = math.log(wood_density_g_cm3)
        ln_agb = -1.803 + 0.976 * ln_rho + 2.673 * ln_d - 0.0299 * (ln_d**2)
        return round(float(math.exp(ln_agb)), 2)


def _compute_ipcc_2006_agb(
    dbh_cm: float,
    **kwargs,
) -> float:
    """
    IPCC 2006 / Brown (1997) Tropical Moist Hardwood Equation:
    AGB (kg) = exp(-2.289 + 2.649 * ln(D) - 0.021 * (ln(D))^2)
    """
    if dbh_cm <= 0:
        return 0.0
    ln_d = math.log(dbh_cm)
    ln_agb = -2.289 + 2.649 * ln_d - 0.021 * (ln_d**2)
    return round(float(math.exp(ln_agb)), 2)


def _compute_cairns_1997_bgb(
    agb_kg: float,
    **kwargs,
) -> float:
    """
    Cairns et al. (1997) Root Biomass Allocation Equation:
    BGB (t/ha) = exp(-1.085 + 0.9256 * ln(AGB_t))
    For individual tree: BGB (kg) = exp(-1.085 + 0.9256 * ln(agb_kg / 1000.0)) * 1000.0
    """
    if agb_kg <= 0:
        return 0.0
    agb_t = agb_kg / 1000.0
    bgb_t = math.exp(-1.085 + 0.9256 * math.log(agb_t))
    return round(float(bgb_t * 1000.0), 2)


def _compute_ipcc_2019_default_bgb(
    agb_kg: float,
    root_to_shoot_ratio: float = 0.235,
    **kwargs,
) -> float:
    """
    IPCC (2019 Refinement) Root:Shoot Default Ratio Model:
    BGB (kg) = AGB (kg) * RootToShootRatio
    """
    if agb_kg <= 0 or root_to_shoot_ratio <= 0:
        return 0.0
    return round(float(agb_kg * root_to_shoot_ratio), 2)


class AllometricModelRegistry:
    """
    Registry of approved and peer-reviewed allometric biomass equations.
    """

    _MODELS: Dict[str, AllometricModelDefinition] = {}

    @classmethod
    def register(cls, model: AllometricModelDefinition) -> None:
        cls._MODELS[model.model_id] = model

    @classmethod
    def get(cls, model_id: str) -> Optional[AllometricModelDefinition]:
        cls._ensure_initialized()
        return cls._MODELS.get(model_id)

    @classmethod
    def list_models(
        cls,
        pool_type: Optional[BiomassPoolType] = None,
        methodology: Optional[str] = None,
    ) -> List[AllometricModelDefinition]:
        cls._ensure_initialized()
        models = list(cls._MODELS.values())
        if pool_type:
            models = [m for m in models if m.pool_type == pool_type]
        if methodology:
            models = [m for m in models if methodology.upper() in [x.upper() for x in m.methodology_compatibility]]
        return models

    @classmethod
    def _ensure_initialized(cls) -> None:
        if cls._MODELS:
            return

        # 1. Chave et al. (2014) Pantropical AGB Model
        cls.register(
            AllometricModelDefinition(
                model_id="CHAVE_2014_PANTROPICAL_AGB",
                name="Chave et al. (2014) Pantropical Aboveground Biomass Model",
                citation="Chave, J. et al. (2014). Improved allometric models to estimate the aboveground biomass of tropical trees. Global Change Biology, 20(10), 3177-3190.",
                version="2014.1",
                pool_type=BiomassPoolType.ABOVEGROUND_BIOMASS,
                geographic_applicability="Pantropical (lowland and montane tropical forests)",
                species_applicability="Mixed broadleaf tropical species",
                required_inputs=["dbh_cm", "wood_density_g_cm3"],
                methodology_compatibility=["VM0047", "BM_FR05_002", "AR-ACM0003"],
                parameter_source="Global Wood Density Database (Zanne et al., 2009)",
                review_status=ModelReviewStatus.APPROVED,
                compute_fn=_compute_chave_2014_agb,
            )
        )

        # 2. IPCC (2006) Tropical Hardwood AGB Model
        cls.register(
            AllometricModelDefinition(
                model_id="IPCC_2006_TROPICAL_HARDWOOD_AGB",
                name="IPCC (2006) Tropical Hardwood AGB Model (Brown 1997)",
                citation="IPCC Guidelines for National GHG Inventories (2006), Vol 4 AFOLU / Brown, S. (1997). Estimating biomass and biomass change of tropical forests.",
                version="2006.1",
                pool_type=BiomassPoolType.ABOVEGROUND_BIOMASS,
                geographic_applicability="Tropical moist and wet forests",
                species_applicability="Tropical hardwood angiosperms",
                required_inputs=["dbh_cm"],
                methodology_compatibility=["VM0047", "BM_FR05_002"],
                parameter_source="IPCC 2006 AFOLU Chapter 4 Table 4.4",
                review_status=ModelReviewStatus.APPROVED,
                compute_fn=_compute_ipcc_2006_agb,
            )
        )

        # 3. Cairns et al. (1997) Root:Shoot BGB Model
        cls.register(
            AllometricModelDefinition(
                model_id="CAIRNS_1997_ROOT_SHOOT_BGB",
                name="Cairns et al. (1997) Root-to-Shoot Belowground Biomass Model",
                citation="Cairns, M.A. et al. (1997). Root biomass allocation in the world's upland forests. Oecologia, 111(1), 1-11.",
                version="1997.1",
                pool_type=BiomassPoolType.BELOWGROUND_BIOMASS,
                geographic_applicability="Global upland forests",
                species_applicability="Mixed forest species",
                required_inputs=["agb_kg"],
                methodology_compatibility=["VM0047", "BM_FR05_002"],
                parameter_source="Cairns et al. (1997) / IPCC 2006 Table 4.4",
                review_status=ModelReviewStatus.APPROVED,
                compute_fn=_compute_cairns_1997_bgb,
            )
        )

        # 4. IPCC (2019 Refinement) Default Root:Shoot Ratio BGB Model
        cls.register(
            AllometricModelDefinition(
                model_id="IPCC_2019_DEFAULT_ROOT_SHOOT_BGB",
                name="IPCC (2019 Refinement) Default Root:Shoot Ratio BGB Model",
                citation="2019 Refinement to the 2006 IPCC Guidelines for National GHG Inventories, Volume 4 AFOLU, Chapter 4.",
                version="2019.1",
                pool_type=BiomassPoolType.BELOWGROUND_BIOMASS,
                geographic_applicability="Tropical / Subtropical moist forests",
                species_applicability="Tropical forest vegetation",
                required_inputs=["agb_kg"],
                methodology_compatibility=["VM0047", "BM_FR05_002"],
                parameter_source="IPCC 2019 Refinement Table 4.4 (Default R = 0.235)",
                review_status=ModelReviewStatus.APPROVED,
                compute_fn=_compute_ipcc_2019_default_bgb,
            )
        )


def estimate_tree_biomass_pools(
    dbh_cm: float,
    height_m: Optional[float] = None,
    wood_density_g_cm3: float = 0.60,
    agb_model_id: str = "CHAVE_2014_PANTROPICAL_AGB",
    bgb_model_id: Optional[str] = None,
    carbon_fraction: float = 0.47,
    wood_density_source: str = "Global Wood Density Database (Zanne et al. 2009)",
) -> Dict[str, Any]:
    """
    Estimates tree biomass pools adhering strictly to VM0047:
    1. Derives Aboveground Biomass (AGB) using specified agb_model_id.
    2. Derives Belowground Biomass (BGB) ONLY IF an approved bgb_model_id is provided.
       Does NOT conflate AGB with BGB or automatically infer root biomass without an approved model.
    3. Quantifies carbon stock in t CO2e with complete model provenance.
    """
    AllometricModelRegistry._ensure_initialized()

    # 1. Resolve AGB Model
    agb_model = AllometricModelRegistry.get(agb_model_id)
    if not agb_model or agb_model.pool_type != BiomassPoolType.ABOVEGROUND_BIOMASS:
        raise ValueError(f"Invalid or unapproved AGB allometric model: '{agb_model_id}'")

    agb_kg = agb_model.compute_fn(
        dbh_cm=dbh_cm,
        height_m=height_m,
        wood_density_g_cm3=wood_density_g_cm3,
    )

    # 2. Resolve BGB Model (if explicitly requested)
    bgb_kg = None
    bgb_provenance = None
    if bgb_model_id:
        bgb_model = AllometricModelRegistry.get(bgb_model_id)
        if not bgb_model or bgb_model.pool_type != BiomassPoolType.BELOWGROUND_BIOMASS:
            raise ValueError(f"Invalid or unapproved BGB allometric model: '{bgb_model_id}'")
        bgb_kg = bgb_model.compute_fn(agb_kg=agb_kg)
        bgb_provenance = {
            "model_id": bgb_model.model_id,
            "name": bgb_model.name,
            "version": bgb_model.version,
            "citation": bgb_model.citation,
            "parameter_source": bgb_model.parameter_source,
        }

    # 3. Total Biomass & Carbon Stock Calculation
    total_biomass_kg = agb_kg + (bgb_kg if bgb_kg is not None else 0.0)
    total_biomass_tonnes = total_biomass_kg / 1000.0

    # Carbon stock (t CO2e) = Biomass (t) * Carbon Fraction * (44 / 12)
    carbon_stock_t_co2e = round(total_biomass_tonnes * carbon_fraction * (44.0 / 12.0), 4)

    return {
        "agb_kg": round(agb_kg, 2),
        "bgb_kg": round(bgb_kg, 2) if bgb_kg is not None else None,
        "total_biomass_kg": round(total_biomass_kg, 2),
        "carbon_stock_t_co2e": carbon_stock_t_co2e,
        "carbon_fraction": carbon_fraction,
        "provenance": {
            "agb_model": {
                "model_id": agb_model.model_id,
                "name": agb_model.name,
                "version": agb_model.version,
                "citation": agb_model.citation,
                "parameter_source": agb_model.parameter_source,
            },
            "bgb_model": bgb_provenance,
            "wood_density_g_cm3": wood_density_g_cm3,
            "wood_density_source": wood_density_source,
            "height_measured": bool(height_m and height_m > 0),
        },
    }
