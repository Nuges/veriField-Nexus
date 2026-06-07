"""
=============================================================================
VeriField Nexus — Trust Engine v3 Proportional Penalty Tests
=============================================================================
Validates that:
  1. Same violation → same % deduction regardless of weight config
  2. Increasing weight does not reduce penalty severity proportionally
  3. Total score remains within [0, max_weight] per dimension
  4. Structured audit breakdown is returned
  5. Backward compatibility with existing weight configs
=============================================================================
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta
from uuid import uuid4

# ---------------------------------------------------------------------------
# Lightweight stubs so tests run without a real database
# ---------------------------------------------------------------------------

class FakeActivity:
    """Minimal Activity stand-in for unit testing."""
    def __init__(self, **kwargs):
        self.id = kwargs.get("id", uuid4())
        self.user_id = kwargs.get("user_id", uuid4())
        self.property_id = kwargs.get("property_id", None)
        self.latitude = kwargs.get("latitude", 6.5244)
        self.longitude = kwargs.get("longitude", 3.3792)
        self.gps_accuracy = kwargs.get("gps_accuracy", 5.0)
        self.image_url = kwargs.get("image_url", "https://example.com/img.jpg")
        self.image_hash = kwargs.get("image_hash", "abcdef1234567890")
        self.captured_at = kwargs.get("captured_at", datetime.now(timezone.utc))
        self.created_at = kwargs.get("created_at", datetime.now(timezone.utc))
        self.submitted_at = kwargs.get("submitted_at", datetime.now(timezone.utc))
        self.activity_type = kwargs.get("activity_type", "CLEAN_COOKING")
        self.activity_data = kwargs.get("activity_data", {})
        self.trust_score = None
        self.trust_flags = {}
        self.status = "pending"


# ---------------------------------------------------------------------------
# Import the engine (relies on app structure being on PYTHONPATH)
# ---------------------------------------------------------------------------
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.trust_engine import TrustEngine


# ===========================================================================
# 1. Penalty helper tests — pure unit tests (no DB)
# ===========================================================================

class TestPenaltyHelpers:
    """Test _record_penalty and _record_bonus produce correct proportional values."""

    def test_penalty_scales_with_weight(self):
        """Same tier% produces different absolute values for different weights."""
        ledger_a, ledger_b = [], []
        val_30 = TrustEngine._record_penalty(30.0, TrustEngine.PENALTY_MAJOR, "test", ledger_a)
        val_50 = TrustEngine._record_penalty(50.0, TrustEngine.PENALTY_MAJOR, "test", ledger_b)

        assert val_30 == 15.0   # 50% of 30
        assert val_50 == 25.0   # 50% of 50
        # Same percentage
        assert ledger_a[0]["impact_percent"] == ledger_b[0]["impact_percent"] == 50.0

    def test_all_tiers_produce_correct_fractions(self):
        """Each tier constant maps to the correct percentage of max_weight."""
        weight = 40.0
        cases = [
            (TrustEngine.PENALTY_MINOR, 4.0),
            (TrustEngine.PENALTY_MODERATE, 10.0),
            (TrustEngine.PENALTY_MAJOR, 20.0),
            (TrustEngine.PENALTY_CRITICAL, 32.0),
            (TrustEngine.PENALTY_ABSOLUTE, 40.0),
        ]
        for tier, expected in cases:
            ledger = []
            result = TrustEngine._record_penalty(weight, tier, "t", ledger)
            assert result == expected, f"Tier {tier}: expected {expected}, got {result}"

    def test_bonus_scales_with_weight(self):
        """Bonus values scale proportionally."""
        ledger = []
        val = TrustEngine._record_bonus(60.0, TrustEngine.BONUS_MODERATE, "test", ledger)
        assert val == 6.0  # 10% of 60
        assert ledger[0]["bonus"] == 6.0

    def test_penalty_records_audit_entry(self):
        """Each penalty call appends a structured record to the ledger."""
        ledger = []
        TrustEngine._record_penalty(30.0, 0.25, "gps_low_accuracy", ledger)
        assert len(ledger) == 1
        entry = ledger[0]
        assert entry["type"] == "gps_low_accuracy"
        assert entry["impact_percent"] == 25.0
        assert entry["deduction"] == 7.5


# ===========================================================================
# 2. Proportional consistency: same violation, different weights
# ===========================================================================

class TestProportionalConsistency:
    """Verify the same violation produces the same % deduction across weights."""

    def test_same_percentage_different_weights(self):
        """A MAJOR penalty is always 50% regardless of the weight value."""
        for weight in [10.0, 25.0, 30.0, 40.0, 50.0, 75.0, 100.0]:
            ledger = []
            deduction = TrustEngine._record_penalty(
                weight, TrustEngine.PENALTY_MAJOR, "test", ledger
            )
            pct = deduction / weight
            assert abs(pct - 0.50) < 0.001, (
                f"Weight {weight}: expected 50%, got {pct*100:.1f}%"
            )

    def test_increasing_weight_increases_absolute_deduction(self):
        """Higher weight → larger absolute deduction (same % though)."""
        ledger_lo, ledger_hi = [], []
        d_lo = TrustEngine._record_penalty(20.0, TrustEngine.PENALTY_CRITICAL, "t", ledger_lo)
        d_hi = TrustEngine._record_penalty(80.0, TrustEngine.PENALTY_CRITICAL, "t", ledger_hi)
        assert d_hi > d_lo
        # Both are 80%
        assert d_lo / 20.0 == d_hi / 80.0 == 0.80


# ===========================================================================
# 3. Score clamping — never below 0, never above max_weight
# ===========================================================================

class TestScoreClamping:
    """Ensure dimension scores stay within [0, max_weight]."""

    def test_multiple_penalties_cannot_go_negative(self):
        """Even with stacked penalties the minimum is 0."""
        weight = 30.0
        score = weight
        ledger = []
        # Stack: 50% + 50% + 25% = 125% — should clamp to 0
        score -= TrustEngine._record_penalty(weight, 0.50, "a", ledger)
        score -= TrustEngine._record_penalty(weight, 0.50, "b", ledger)
        score -= TrustEngine._record_penalty(weight, 0.25, "c", ledger)
        clamped = max(0.0, min(weight, score))
        assert clamped == 0.0

    def test_bonuses_cannot_exceed_max(self):
        """Bonuses cannot push score above max_weight."""
        weight = 30.0
        score = weight
        ledger = []
        score += TrustEngine._record_bonus(weight, 0.50, "a", ledger)
        score += TrustEngine._record_bonus(weight, 0.50, "b", ledger)
        clamped = max(0.0, min(weight, score))
        assert clamped == weight


# ===========================================================================
# 4. Backward compatibility — known weight configs
# ===========================================================================

class TestBackwardCompatibility:
    """Existing weight distributions must continue to work."""

    @pytest.mark.parametrize(
        "gps,img,freq",
        [
            (30.0, 40.0, 30.0),   # original default
            (50.0, 25.0, 25.0),   # current DB value
            (20.0, 50.0, 30.0),   # hypothetical
            (33.3, 33.3, 33.4),   # equal split
        ],
    )
    def test_weight_configs_produce_valid_penalties(self, gps, img, freq):
        """All tier penalties are valid for any weight configuration."""
        for weight in [gps, img, freq]:
            for tier in [
                TrustEngine.PENALTY_MINOR,
                TrustEngine.PENALTY_MODERATE,
                TrustEngine.PENALTY_MAJOR,
                TrustEngine.PENALTY_CRITICAL,
                TrustEngine.PENALTY_ABSOLUTE,
            ]:
                ledger = []
                val = TrustEngine._record_penalty(weight, tier, "test", ledger)
                assert 0 <= val <= weight, (
                    f"Penalty {tier} on weight {weight} produced {val}"
                )


# ===========================================================================
# 5. Example output verification
# ===========================================================================

class TestExampleOutputs:
    """Verify expected scores for concrete scenarios."""

    def test_gps_low_accuracy_with_weight_30(self):
        """GPS accuracy > 100m with weight 30 → 50% penalty = 15 deduction."""
        weight = 30.0
        score = weight
        ledger = []
        score -= TrustEngine._record_penalty(
            weight, TrustEngine.PENALTY_MAJOR, "gps_low_accuracy", ledger
        )
        assert score == 15.0
        assert ledger[0]["deduction"] == 15.0
        assert ledger[0]["impact_percent"] == 50.0

    def test_gps_low_accuracy_with_weight_50(self):
        """Same violation with weight 50 → 50% penalty = 25 deduction."""
        weight = 50.0
        score = weight
        ledger = []
        score -= TrustEngine._record_penalty(
            weight, TrustEngine.PENALTY_MAJOR, "gps_low_accuracy", ledger
        )
        assert score == 25.0
        assert ledger[0]["deduction"] == 25.0
        assert ledger[0]["impact_percent"] == 50.0

    def test_image_duplicate_critical(self):
        """Image duplicate (>=95% similarity) → 80% penalty."""
        weight = 40.0
        score = weight
        ledger = []
        score -= TrustEngine._record_penalty(
            weight, TrustEngine.PENALTY_CRITICAL, "image_duplicate", ledger
        )
        assert score == 8.0   # 40 - 32
        assert ledger[0]["deduction"] == 32.0

    def test_frequency_burst_with_low_weight(self):
        """Burst with weight=25 → 80% penalty = 20 deduction."""
        weight = 25.0
        score = weight
        ledger = []
        score -= TrustEngine._record_penalty(
            weight, TrustEngine.PENALTY_CRITICAL, "burst_detected", ledger
        )
        assert score == 5.0
        assert ledger[0]["deduction"] == 20.0

    def test_full_scenario_30_40_30(self):
        """
        Default config (30/40/30):
        GPS: low accuracy (MAJOR 50%) → 30 - 15 = 15
        Image: similar (MODERATE 25%) → 40 - 10 = 30
        Freq: suspicious time (30%) → 30 - 9 = 21
        Total: 15 + 30 + 21 = 66 → status "review"
        """
        ledger = []
        gps = 30.0 - TrustEngine._record_penalty(30.0, 0.50, "gps", ledger)
        img = 40.0 - TrustEngine._record_penalty(40.0, 0.25, "img", ledger)
        freq = 30.0 - TrustEngine._record_penalty(30.0, 0.30, "freq", ledger)
        total = gps + img + freq
        assert total == 66.0
        assert TrustEngine._determine_status(total) == "review"

    def test_full_scenario_50_25_25(self):
        """
        Custom config (50/25/25) — same violations:
        GPS: MAJOR 50% → 50 - 25 = 25
        Image: MODERATE 25% → 25 - 6.25 = 18.75
        Freq: 30% → 25 - 7.5 = 17.5
        Total: 25 + 18.75 + 17.5 = 61.25 → status "review"
        """
        ledger = []
        gps = 50.0 - TrustEngine._record_penalty(50.0, 0.50, "gps", ledger)
        img = 25.0 - TrustEngine._record_penalty(25.0, 0.25, "img", ledger)
        freq = 25.0 - TrustEngine._record_penalty(25.0, 0.30, "freq", ledger)
        total = gps + img + freq
        assert total == 61.25
        assert TrustEngine._determine_status(total) == "review"


# ===========================================================================
# 6. Multi-Photo Verification Rules Engine Tests
# ===========================================================================

class TestMultiPhotoVerificationRules:
    """Verify trust engine deductions for the new Multi-Photo Verification Rules."""

    @pytest.mark.anyio
    @patch("app.services.trust_engine.select")
    async def test_hybrid_energy_all_photos_present(self, mock_select):
        mock_db = AsyncMock()
        mock_setting = MagicMock()
        mock_setting.gps_weight = 30.0
        mock_setting.image_weight = 40.0
        mock_setting.frequency_weight = 30.0
        mock_setting.gps_max_distance_km = 5.0
        mock_setting.image_hash_threshold = 12
        mock_setting.max_submissions_per_hour = 10
        mock_setting.suspicious_hours_start = 22
        mock_setting.suspicious_hours_end = 5
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_setting
        mock_db.execute.return_value = mock_result
        
        engine = TrustEngine(mock_db)
        
        activity = FakeActivity(
            activity_type="HYBRID_ENERGY",
            activity_data={
                "baseline_generator_image_url": "https://example.com/diesel.jpg",
                "inverter_label_image_url": "https://example.com/label.jpg"
            }
        )
        
        with patch.object(engine, "_calculate_gps_score", return_value=(30.0, {}, [])), \
             patch.object(engine, "_calculate_image_score", return_value=(40.0, {}, [])), \
             patch.object(engine, "_calculate_frequency_score", return_value=(30.0, {}, [])), \
             patch.object(engine, "_calculate_cross_verification_bonus", return_value=(0.0, {})):
             
            score, flags = await engine.calculate_trust_score(activity)
            
            assert score == 100.0
            assert "missing_baseline_generator_photo" not in flags
            assert "missing_inverter_label_photo" not in flags
            assert flags["scoring_breakdown"]["mrv_penalties"] == []

    @pytest.mark.anyio
    @patch("app.services.trust_engine.select")
    async def test_hybrid_energy_missing_baseline_and_inverter(self, mock_select):
        mock_db = AsyncMock()
        mock_setting = MagicMock()
        mock_setting.gps_weight = 30.0
        mock_setting.image_weight = 40.0
        mock_setting.frequency_weight = 30.0
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_setting
        mock_db.execute.return_value = mock_result
        
        engine = TrustEngine(mock_db)
        
        activity = FakeActivity(
            activity_type="HYBRID_ENERGY",
            activity_data={}
        )
        
        with patch.object(engine, "_calculate_gps_score", return_value=(30.0, {}, [])), \
             patch.object(engine, "_calculate_image_score", return_value=(40.0, {}, [])), \
             patch.object(engine, "_calculate_frequency_score", return_value=(30.0, {}, [])), \
             patch.object(engine, "_calculate_cross_verification_bonus", return_value=(0.0, {})):
             
            score, flags = await engine.calculate_trust_score(activity)
            
            assert score == 65.0
            assert flags["missing_baseline_generator_photo"] is True
            assert flags["missing_inverter_label_photo"] is True
            
            penalties = flags["scoring_breakdown"]["mrv_penalties"]
            assert len(penalties) == 2
            assert penalties[0]["deduction"] == 30.0
            assert penalties[1]["deduction"] == 5.0

    @pytest.mark.anyio
    @patch("app.services.trust_engine.select")
    async def test_gps_mismatch_penalty(self, mock_select):
        mock_db = AsyncMock()
        mock_setting = MagicMock()
        mock_setting.gps_weight = 30.0
        mock_setting.image_weight = 40.0
        mock_setting.frequency_weight = 30.0
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_setting
        mock_db.execute.return_value = mock_result
        
        engine = TrustEngine(mock_db)
        activity = FakeActivity(activity_type="CLEAN_COOKING")
        
        with patch.object(engine, "_calculate_gps_score", return_value=(10.0, {"gps_too_far": True}, [])), \
             patch.object(engine, "_calculate_image_score", return_value=(40.0, {}, [])), \
             patch.object(engine, "_calculate_frequency_score", return_value=(30.0, {}, [])), \
             patch.object(engine, "_calculate_cross_verification_bonus", return_value=(0.0, {})):
             
            score, flags = await engine.calculate_trust_score(activity)
            
            assert score == 60.0
            assert flags["gps_mismatch_penalty"] is True

    @pytest.mark.anyio
    @patch("app.services.trust_engine.select")
    async def test_duplicate_image_fraud_status(self, mock_select):
        mock_db = AsyncMock()
        mock_setting = MagicMock()
        mock_setting.gps_weight = 30.0
        mock_setting.image_weight = 40.0
        mock_setting.frequency_weight = 30.0
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_setting
        mock_db.execute.return_value = mock_result
        
        engine = TrustEngine(mock_db)
        activity = FakeActivity(activity_type="CLEAN_COOKING")
        
        with patch.object(engine, "_calculate_gps_score", return_value=(30.0, {}, [])), \
             patch.object(engine, "_calculate_image_score", return_value=(8.0, {"image_duplicate": True}, [])), \
             patch.object(engine, "_calculate_frequency_score", return_value=(30.0, {}, [])), \
             patch.object(engine, "_calculate_cross_verification_bonus", return_value=(0.0, {})):
             
            score, flags = await engine.calculate_trust_score(activity)
            
            assert flags["fraud_flag"] is True
            assert activity.status == "flagged"


# ===========================================================================
# Run with:  pytest tests/test_trust_engine.py -v
# ===========================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
