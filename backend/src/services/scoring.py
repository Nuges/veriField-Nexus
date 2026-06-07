"""
=============================================================================
VeriField Nexus — Trust Engine Scoring Service
=============================================================================
Heuristic-based trust engine that evaluates environmental metadata inputs and
assigns a reliability score (0-100) for carbon credit reviews.
=============================================================================
"""


def calculate_trust_score(
    asset_type: str,
    latitude: float,
    longitude: float,
    image_hash: str
) -> int:
    """
    Computes a Trust Score (0-100) from physical evidence parameters.
    
    Heuristics:
        - Baseline score: 100
        - Deduct if evidence hash format is weak (simulated)
        - Deduct if location deviates from target projects (simulated Port Harcourt bounds)
        - Deduct if inputs are missing or default
        
    Args:
        asset_type: "cookstove" or "hybrid_energy"
        latitude: Capture latitude coord
        longitude: Capture longitude coord
        image_hash: Photometric evidence hash string
        
    Returns:
        Integer score between 0 and 100 inclusive.
    """
    score = 100

    # 1. Image Hash verification check
    if not image_hash or len(image_hash) != 64:
        score -= 40
    elif image_hash.startswith("000000"):
        # Simulated duplicate/placeholder image penalty
        score -= 30

    # 2. Location bounding box verification check
    # Check if within target project bounds (e.g. Sub-Saharan Africa / Port Harcourt range)
    # Latitude target: [-10.0, 15.0], Longitude target: [3.0, 15.0]
    in_target_range = (-15.0 <= latitude <= 20.0) and (2.0 <= longitude <= 20.0)
    if not in_target_range:
        score -= 25

    # 3. Asset-specific parameters validation check
    if asset_type not in ["cookstove", "hybrid_energy"]:
        score -= 30

    # Guarantee score bounds
    return max(0, min(100, score))
