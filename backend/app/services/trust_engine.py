"""
=============================================================================
VeriField Nexus — Trust Engine (v3 — Proportional Penalty System)
=============================================================================
The core verification engine that generates trust scores (0-100) for
each field activity submission. Evaluates three dimensions:

    1. GPS Consistency   (configurable weight, default 30)
    2. Image Uniqueness  (configurable weight, default 40)
    3. Submission Frequency (configurable weight, default 30)

v3 Changes:
    - ALL penalties are now percentage-based relative to max_weight
    - Penalty tiers: MINOR(10%), MODERATE(25%), MAJOR(50%), CRITICAL(80%)
    - Structured audit breakdown returned for every calculation
    - Same violation produces same % deduction regardless of weight config

Final Score = GPS + Image + Frequency + Cross-Verification Bonus
Status: HIGH (80-100) | MEDIUM (50-79) | LOW (0-49)
=============================================================================
"""

import math
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.activity import Activity
from app.models.trust_log import TrustLog
from app.core.config import settings


class TrustEngine:
    """
    Calculates and assigns trust scores to field activity submissions.

    All penalties scale proportionally with configured weights using
    standardized penalty tiers.

    Usage:
        engine = TrustEngine(db_session)
        score, flags = await engine.calculate_trust_score(activity)
    """

    # =========================================================================
    # Penalty Tier Constants (fraction of max_weight)
    # =========================================================================
    PENALTY_MINOR = 0.10       # 10% — minor quality issues
    PENALTY_MODERATE = 0.25    # 25% — notable concerns
    PENALTY_MAJOR = 0.50       # 50% — serious issues
    PENALTY_CRITICAL = 0.80    # 80% — near-disqualifying
    PENALTY_ABSOLUTE = 1.00    # 100% — complete dimension failure

    BONUS_SMALL = 0.03         # 3%  — slight positive signal
    BONUS_MINOR = 0.05         # 5%
    BONUS_MODERATE = 0.10      # 10%
    BONUS_MAJOR = 0.15         # 15%

    def __init__(self, db: AsyncSession):
        self.db = db

    # =========================================================================
    # Penalty / Bonus Helpers
    # =========================================================================

    @staticmethod
    def _record_penalty(
        max_weight: float, tier: float, label: str, ledger: list
    ) -> float:
        """Calculate a proportional penalty deduction and record it."""
        deduction = round(max_weight * tier, 2)
        ledger.append({
            "type": label,
            "impact_percent": round(tier * 100, 1),
            "deduction": deduction,
        })
        return deduction

    @staticmethod
    def _record_bonus(
        max_weight: float, tier: float, label: str, ledger: list
    ) -> float:
        """Calculate a proportional bonus and record it."""
        bonus_val = round(max_weight * tier, 2)
        ledger.append({
            "type": label,
            "impact_percent": round(tier * 100, 1),
            "bonus": bonus_val,
        })
        return bonus_val

    # =========================================================================
    # Public API
    # =========================================================================

    async def calculate_trust_score(
        self, activity: Activity
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Calculate the complete trust score for an activity.
        All penalties scale proportionally with configured weights.
        """
        flags: Dict[str, Any] = {}

        # Get system settings weights
        from app.models.system_setting import SystemSetting
        result = await self.db.execute(
            select(SystemSetting).where(SystemSetting.id == 1)
        )
        sys_settings = result.scalar_one_or_none()

        gps_weight = sys_settings.gps_weight if sys_settings else 30.0
        image_weight = sys_settings.image_weight if sys_settings else 40.0
        frequency_weight = sys_settings.frequency_weight if sys_settings else 30.0

        # Calculate individual components with structured breakdowns
        gps_score, gps_flags, gps_pen = await self._calculate_gps_score(
            activity, gps_weight, sys_settings
        )
        image_score, img_flags, img_pen = await self._calculate_image_score(
            activity, image_weight, sys_settings
        )
        freq_score, frq_flags, frq_pen = await self._calculate_frequency_score(
            activity, frequency_weight, sys_settings
        )

        flags.update(gps_flags)
        flags.update(img_flags)
        flags.update(frq_flags)

        # --- Base final score calculation ---
        base_score = round(gps_score + image_score + freq_score, 2)

        # --- Multi-Photo Verification Rules Engine ---
        mrv_penalties = []
        mrv_deduction = 0.0

        if activity.activity_type == "HYBRID_ENERGY":
            act_data = activity.activity_data or {}
            
            # Missing baseline photo (baseline_generator_image_url) -> -30 score
            if not act_data.get("baseline_generator_image_url"):
                deduction = 30.0
                mrv_deduction += deduction
                mrv_penalties.append({
                    "type": "missing_baseline_generator_photo",
                    "deduction": deduction,
                    "label": "Missing Baseline Diesel Generator Photo"
                })
                flags["missing_baseline_generator_photo"] = True
                
            # Missing inverter label photo (inverter_label_image_url) -> -5 score
            if not act_data.get("inverter_label_image_url"):
                deduction = 5.0
                mrv_deduction += deduction
                mrv_penalties.append({
                    "type": "missing_inverter_label_photo",
                    "deduction": deduction,
                    "label": "Missing Inverter Label Photo"
                })
                flags["missing_inverter_label_photo"] = True

        # GPS mismatch penalty -> -20 score
        if flags.get("gps_too_far"):
            deduction = 20.0
            mrv_deduction += deduction
            mrv_penalties.append({
                "type": "gps_mismatch_penalty",
                "deduction": deduction,
                "label": "Mismatched GPS coordinates (far from site)"
            })
            flags["gps_mismatch_penalty"] = True

        # Duplicate image -> fraud flag
        if flags.get("image_duplicate"):
            flags["fraud_flag"] = True
            
        final_score = base_score - mrv_deduction
        
        # Cross-Verification Bonuses (additive, not weight-dependent)
        cross_bonus, cross_flags = await self._calculate_cross_verification_bonus(
            activity
        )
        final_score += cross_bonus
        final_score = max(0.0, min(100.0, final_score))

        # Status determination (Duplicates automatically flagged as fraud)
        if flags.get("fraud_flag"):
            status = "flagged"
        else:
            status = self._determine_status(final_score)

        # Audit-transparent scoring breakdown
        flags["scoring_breakdown"] = {
            "gps": {
                "dimension": "GPS",
                "max_weight": gps_weight,
                "final_score": gps_score,
                "penalties": gps_pen,
            },
            "image": {
                "dimension": "Image",
                "max_weight": image_weight,
                "final_score": image_score,
                "penalties": img_pen,
            },
            "frequency": {
                "dimension": "Frequency",
                "max_weight": frequency_weight,
                "final_score": freq_score,
                "penalties": frq_pen,
            },
            "mrv_penalties": mrv_penalties,
            "cross_verification_bonus": cross_bonus,
            "composite_score": final_score,
        }

        # Persist the trust log
        trust_log = TrustLog(
            activity_id=activity.id,
            gps_score=gps_score,
            image_score=image_score,
            frequency_score=freq_score,
            final_score=final_score,
            flags=flags,
        )
        self.db.add(trust_log)

        activity.trust_score = final_score
        activity.trust_flags = flags
        activity.status = status

        await self.db.commit()
        await self.db.refresh(activity)

        return final_score, flags

    # =========================================================================
    # GPS Consistency Score
    # =========================================================================

    async def _calculate_gps_score(
        self, activity: Activity, max_weight: float = 30.0, sys_settings = None
    ) -> Tuple[float, Dict[str, Any], List[Dict]]:
        """
        Evaluate GPS data quality and consistency.
        All penalties are proportional to max_weight.
        """
        flags: Dict[str, Any] = {}
        pen: List[Dict] = []
        score = max_weight

        # No GPS → absolute zero
        if activity.latitude is None or activity.longitude is None:
            flags["gps_missing"] = True
            self._record_penalty(max_weight, self.PENALTY_ABSOLUTE, "gps_missing", pen)
            return 0.0, flags, pen

        # GPS accuracy
        if activity.gps_accuracy is not None:
            if activity.gps_accuracy > 100:
                score -= self._record_penalty(
                    max_weight, self.PENALTY_MAJOR, "gps_low_accuracy", pen
                )
                flags["gps_low_accuracy"] = True
            elif activity.gps_accuracy > 50:
                score -= self._record_penalty(
                    max_weight, self.PENALTY_MODERATE, "gps_moderate_accuracy", pen
                )
                flags["gps_moderate_accuracy"] = True

        # Distance from assigned property
        if activity.property_id:
            from app.models.property import Property
            result = await self.db.execute(
                select(Property).where(Property.id == activity.property_id)
            )
            prop = result.scalar_one_or_none()
            if prop and prop.latitude and prop.longitude:
                distance_km = self._haversine_distance(
                    activity.latitude, activity.longitude,
                    prop.latitude, prop.longitude,
                )
                max_distance = sys_settings.gps_max_distance_km if (sys_settings and sys_settings.gps_max_distance_km is not None) else settings.trust_gps_max_distance_km
                if distance_km > max_distance:
                    score -= self._record_penalty(
                        max_weight, 0.65, "gps_too_far", pen
                    )
                    flags["gps_too_far"] = True
                    flags["gps_distance_km"] = round(distance_km, 2)
                elif distance_km > max_distance * 0.5:
                    score -= self._record_penalty(
                        max_weight, self.PENALTY_MODERATE, "gps_distance_warning", pen
                    )
                    flags["gps_distance_warning"] = True
                    flags["gps_distance_km"] = round(distance_km, 2)

        # Impossible travel speed
        spd_adj, spd_flags, spd_pen = await self._check_movement_speed(
            activity, max_weight
        )
        score += spd_adj
        flags.update(spd_flags)
        pen.extend(spd_pen)

        # Historical GPS consistency
        con_adj, con_pen = await self._check_gps_consistency(activity, max_weight)
        score += con_adj
        pen.extend(con_pen)

        # Geo-clustering
        clu_adj, clu_flags, clu_pen = await self._check_geo_clustering(
            activity, max_weight
        )
        score += clu_adj
        flags.update(clu_flags)
        pen.extend(clu_pen)

        return max(0.0, min(max_weight, score)), flags, pen

    async def _check_gps_consistency(
        self, activity: Activity, max_weight: float
    ) -> Tuple[float, List[Dict]]:
        """GPS consistency bonus/penalty — proportional to max_weight."""
        pen: List[Dict] = []
        result = await self.db.execute(
            select(Activity)
            .where(
                Activity.user_id == activity.user_id,
                Activity.id != activity.id,
                Activity.latitude.isnot(None),
                Activity.longitude.isnot(None),
            )
            .order_by(Activity.created_at.desc())
            .limit(10)
        )
        recent = result.scalars().all()
        if len(recent) < 3:
            return 0.0, pen

        distances = [
            self._haversine_distance(
                activity.latitude, activity.longitude, a.latitude, a.longitude
            )
            for a in recent
        ]
        avg_distance = sum(distances) / len(distances)

        if avg_distance < 2.0:
            return self._record_bonus(
                max_weight, self.BONUS_MODERATE, "gps_very_consistent", pen
            ), pen
        elif avg_distance < 5.0:
            return self._record_bonus(
                max_weight, self.BONUS_SMALL, "gps_consistent", pen
            ), pen
        elif avg_distance > 50.0:
            return -self._record_penalty(
                max_weight, self.BONUS_MAJOR, "gps_erratic_movement", pen
            ), pen
        return 0.0, pen

    async def _check_movement_speed(
        self, activity: Activity, max_weight: float
    ) -> Tuple[float, Dict[str, Any], List[Dict]]:
        """Impossible travel detection — proportional penalties."""
        flags: Dict[str, Any] = {}
        pen: List[Dict] = []

        if activity.latitude is None or activity.longitude is None:
            return 0.0, flags, pen

        result = await self.db.execute(
            select(Activity)
            .where(
                Activity.user_id == activity.user_id,
                Activity.id != activity.id,
                Activity.latitude.isnot(None),
                Activity.longitude.isnot(None),
                Activity.captured_at <= activity.captured_at,
            )
            .order_by(Activity.captured_at.desc())
            .limit(1)
        )
        prev = result.scalar_one_or_none()
        if not prev or not prev.latitude or not prev.longitude:
            return 0.0, flags, pen

        distance_km = self._haversine_distance(
            activity.latitude, activity.longitude, prev.latitude, prev.longitude
        )
        hours = (activity.captured_at - prev.captured_at).total_seconds() / 3600.0
        if hours <= 0:
            return 0.0, flags, pen

        speed_kmh = distance_km / hours

        if speed_kmh > 150:
            adj = -self._record_penalty(
                max_weight, self.PENALTY_ABSOLUTE, "impossible_travel", pen
            )
            flags["impossible_travel"] = True
            flags["travel_speed_kmh"] = round(speed_kmh, 1)
            return adj, flags, pen
        elif speed_kmh > 80:
            adj = -self._record_penalty(
                max_weight, 0.30, "fast_travel_warning", pen
            )
            flags["fast_travel_warning"] = True
            flags["travel_speed_kmh"] = round(speed_kmh, 1)
            return adj, flags, pen

        return 0.0, flags, pen

    # =========================================================================
    # Image Uniqueness Score
    # =========================================================================

    async def _calculate_image_score(
        self, activity: Activity, max_weight: float = 40.0, sys_settings = None
    ) -> Tuple[float, Dict[str, Any], List[Dict]]:
        """
        Evaluate image uniqueness using perceptual hashing.
        All penalties are proportional to max_weight.
        """
        flags: Dict[str, Any] = {}
        pen: List[Dict] = []
        score = max_weight

        if not activity.image_url:
            flags["image_missing"] = True
            self._record_penalty(max_weight, 0.60, "image_missing", pen)
            return round(max_weight * 0.4, 2), flags, pen

        if not activity.image_hash:
            flags["image_hash_missing"] = True
            self._record_penalty(max_weight, 0.60, "image_hash_missing", pen)
            return round(max_weight * 0.4, 2), flags, pen

        dup_found, similarity = await self._check_image_similarity(activity, sys_settings)
        if dup_found:
            if similarity >= 95:
                score -= self._record_penalty(
                    max_weight, self.PENALTY_CRITICAL, "image_duplicate", pen
                )
                flags["image_duplicate"] = True
                flags["image_similarity"] = similarity
            elif similarity >= 80:
                score -= self._record_penalty(
                    max_weight, self.PENALTY_MAJOR, "image_very_similar", pen
                )
                flags["image_very_similar"] = True
                flags["image_similarity"] = similarity
            elif similarity >= 60:
                score -= self._record_penalty(
                    max_weight, self.PENALTY_MODERATE, "image_similar", pen
                )
                flags["image_similar"] = True
                flags["image_similarity"] = similarity

        return max(0.0, min(max_weight, score)), flags, pen

    async def _check_image_similarity(
        self, activity: Activity, sys_settings = None
    ) -> Tuple[bool, float]:
        """
        Compare this activity's image hash against all previous
        submissions globally using hamming distance.
        """
        if not activity.image_hash:
            return False, 0.0

        result = await self.db.execute(
            select(Activity.image_hash)
            .where(
                Activity.id != activity.id,
                Activity.image_hash.isnot(None),
            )
            .order_by(Activity.created_at.desc())
            .limit(1000)
        )
        previous_hashes = [row[0] for row in result.all()]
        if not previous_hashes:
            return False, 0.0

        min_distance = float("inf")
        for prev_hash in previous_hashes:
            distance = self._hamming_distance(activity.image_hash, prev_hash)
            min_distance = min(min_distance, distance)

        hash_length = max(len(activity.image_hash), 1)
        similarity = ((hash_length - min_distance) / hash_length) * 100
        threshold = sys_settings.image_hash_threshold if (sys_settings and sys_settings.image_hash_threshold is not None) else settings.trust_image_hash_threshold
        return min_distance < threshold, round(similarity, 1)

    # =========================================================================
    # Submission Frequency Score
    # =========================================================================

    async def _calculate_frequency_score(
        self, activity: Activity, max_weight: float = 30.0, sys_settings = None
    ) -> Tuple[float, Dict[str, Any], List[Dict]]:
        """
        Evaluate submission frequency patterns.
        All penalties are proportional to max_weight.
        """
        flags: Dict[str, Any] = {}
        pen: List[Dict] = []
        score = max_weight

        # Hourly rate check
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        result = await self.db.execute(
            select(func.count(Activity.id)).where(
                Activity.user_id == activity.user_id,
                Activity.created_at >= one_hour_ago,
            )
        )
        hourly_count = result.scalar() or 0
        max_per_hour = sys_settings.max_submissions_per_hour if (sys_settings and sys_settings.max_submissions_per_hour is not None) else settings.trust_max_submissions_per_hour

        if hourly_count > max_per_hour:
            score -= self._record_penalty(
                max_weight, self.PENALTY_CRITICAL, "high_frequency", pen
            )
            flags["high_frequency"] = True
            flags["submissions_last_hour"] = hourly_count
        elif hourly_count > max_per_hour * 0.7:
            score -= self._record_penalty(
                max_weight, self.PENALTY_MODERATE, "frequency_warning", pen
            )
            flags["frequency_warning"] = True
            flags["submissions_last_hour"] = hourly_count

        # Burst detection
        burst_adj, burst_flags, burst_pen = await self._check_burst_submissions(
            activity, max_weight
        )
        score += burst_adj
        flags.update(burst_flags)
        pen.extend(burst_pen)

        # Suspicious time of day
        capture_hour = activity.captured_at.hour
        sus_start = sys_settings.suspicious_hours_start if (sys_settings and sys_settings.suspicious_hours_start is not None) else settings.trust_suspicious_hours_start
        sus_end = sys_settings.suspicious_hours_end if (sys_settings and sys_settings.suspicious_hours_end is not None) else settings.trust_suspicious_hours_end
        if sus_start <= capture_hour <= sus_end:
            score -= self._record_penalty(
                max_weight, 0.30, "suspicious_time", pen
            )
            flags["suspicious_time"] = True
            flags["capture_hour"] = capture_hour

        # Daily consistency bonus
        con_adj, con_pen = await self._check_daily_consistency(
            activity, max_weight
        )
        score += con_adj
        pen.extend(con_pen)

        return max(0.0, min(max_weight, score)), flags, pen

    async def _check_daily_consistency(
        self, activity: Activity, max_weight: float
    ) -> Tuple[float, List[Dict]]:
        """Reward consistent multi-day submission patterns."""
        pen: List[Dict] = []
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
        result = await self.db.execute(
            select(
                func.count(
                    func.distinct(func.date_trunc("day", Activity.created_at))
                )
            ).where(
                Activity.user_id == activity.user_id,
                Activity.created_at >= seven_days_ago,
            )
        )
        active_days = result.scalar() or 0

        if active_days >= 5:
            return self._record_bonus(
                max_weight, self.BONUS_MAJOR, "very_consistent_submitter", pen
            ), pen
        elif active_days >= 3:
            return self._record_bonus(
                max_weight, self.BONUS_MINOR, "consistent_submitter", pen
            ), pen
        return 0.0, pen

    async def _check_burst_submissions(
        self, activity: Activity, max_weight: float
    ) -> Tuple[float, Dict[str, Any], List[Dict]]:
        """Detect burst submission patterns — proportional penalties."""
        flags: Dict[str, Any] = {}
        pen: List[Dict] = []

        five_min_ago = datetime.now(timezone.utc) - timedelta(minutes=5)
        result = await self.db.execute(
            select(func.count(Activity.id)).where(
                Activity.user_id == activity.user_id,
                Activity.created_at >= five_min_ago,
            )
        )
        burst_count = result.scalar() or 0

        if burst_count >= 50:
            adj = -self._record_penalty(
                max_weight, self.PENALTY_CRITICAL, "burst_detected", pen
            )
            flags["burst_detected"] = True
            flags["submissions_last_5min"] = burst_count
            return adj, flags, pen
        elif burst_count >= 20:
            adj = -self._record_penalty(
                max_weight, self.PENALTY_MAJOR, "burst_warning", pen
            )
            flags["burst_warning"] = True
            flags["submissions_last_5min"] = burst_count
            return adj, flags, pen

        return 0.0, flags, pen

    async def _check_geo_clustering(
        self, activity: Activity, max_weight: float
    ) -> Tuple[float, Dict[str, Any], List[Dict]]:
        """Detect suspicious geo-clustering — proportional penalties."""
        flags: Dict[str, Any] = {}
        pen: List[Dict] = []

        if activity.latitude is None or activity.longitude is None:
            return 0.0, flags, pen

        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        result = await self.db.execute(
            select(Activity).where(
                Activity.user_id == activity.user_id,
                Activity.id != activity.id,
                Activity.latitude.isnot(None),
                Activity.longitude.isnot(None),
                Activity.created_at >= one_hour_ago,
            )
        )
        recent = result.scalars().all()

        clustered = sum(
            1
            for other in recent
            if self._haversine_distance(
                activity.latitude, activity.longitude,
                other.latitude, other.longitude,
            )
            < 0.05
        )

        if clustered >= 10:
            adj = -self._record_penalty(
                max_weight, self.PENALTY_MAJOR, "geo_cluster_critical", pen
            )
            flags["geo_cluster_critical"] = True
            flags["clustered_submissions"] = clustered
            return adj, flags, pen
        elif clustered >= 5:
            adj = -self._record_penalty(
                max_weight, self.PENALTY_MODERATE, "geo_cluster_warning", pen
            )
            flags["geo_cluster_warning"] = True
            flags["clustered_submissions"] = clustered
            return adj, flags, pen

        return 0.0, flags, pen

    # =========================================================================
    # Cross-Verification Extension (unchanged — additive bonuses)
    # =========================================================================

    async def _calculate_cross_verification_bonus(
        self, activity: Activity
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Check for 3 additional verification layers:
        - Sensor Data (+10 points)
        - Community Validation (+10 points)
        - Audit Passed (+20 points)
        """
        flags: Dict[str, Any] = {}
        bonus = 0.0

        if not activity.property_id:
            return 0.0, flags

        from app.models.sensor_reading import SensorReading
        from app.models.community_validation import CommunityValidation
        from app.models.audit_task import AuditTask

        sensor_result = await self.db.execute(
            select(SensorReading)
            .where(SensorReading.asset_id == activity.property_id)
            .limit(1)
        )
        if sensor_result.scalar_one_or_none():
            bonus += 10.0
            flags["sensor_data_present"] = True

        community_result = await self.db.execute(
            select(CommunityValidation)
            .where(
                CommunityValidation.asset_id == activity.property_id,
                CommunityValidation.response == "yes",
            )
            .limit(1)
        )
        if community_result.scalar_one_or_none():
            bonus += 10.0
            flags["community_validation_positive"] = True

        audit_result = await self.db.execute(
            select(AuditTask)
            .where(
                AuditTask.asset_id == activity.property_id,
                AuditTask.status == "completed",
            )
            .limit(1)
        )
        if audit_result.scalar_one_or_none():
            bonus += 20.0
            flags["audit_passed"] = True

        return bonus, flags

    # =========================================================================
    # Utility Methods
    # =========================================================================

    @staticmethod
    def _determine_status(score: float) -> str:
        """Map trust score to activity status."""
        if score >= 80:
            return "verified"
        elif score >= 50:
            return "review"
        else:
            return "flagged"

    @staticmethod
    def _haversine_distance(
        lat1: float, lon1: float, lat2: float, lon2: float
    ) -> float:
        """
        Calculate the great-circle distance between two GPS coordinates
        using the Haversine formula.

        Returns:
            float: Distance in kilometers
        """
        R = 6371.0
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    @staticmethod
    def _hamming_distance(hash1: str, hash2: str) -> int:
        """
        Calculate the hamming distance between two hex-encoded hashes.
        Lower distance = more similar images.
        """
        try:
            val1 = int(hash1, 16)
            val2 = int(hash2, 16)
            return bin(val1 ^ val2).count("1")
        except (ValueError, TypeError):
            return 64
