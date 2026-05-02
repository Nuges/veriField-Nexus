"""
=============================================================================
VeriField Nexus — Trust Engine
=============================================================================
The core verification engine that generates trust scores (0-100) for
each field activity submission. Evaluates three dimensions:

    1. GPS Consistency (0-30 points)
       - Distance from expected property location
       - GPS accuracy reading quality
       - Historical GPS pattern matching

    2. Image Uniqueness (0-35 points)
       - Perceptual hash comparison against previous submissions
       - EXIF data presence check
       - Duplicate detection using hamming distance

    3. Submission Frequency (0-35 points)
       - Rate of submissions per hour
       - Suspicious time-of-day patterns
       - Consistency of daily submission patterns

Final Score = GPS + Image + Frequency
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
    
    Usage:
        engine = TrustEngine(db_session)
        score, flags = await engine.calculate_trust_score(activity)
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # =========================================================================
    # Public API
    # =========================================================================

    async def calculate_trust_score(
        self, activity: Activity
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Calculate the complete trust score for an activity.
        
        Args:
            activity: The Activity model instance to score
            
        Returns:
            Tuple of (final_score, flags_dict)
        """
        flags: Dict[str, Any] = {}

        # Calculate individual components
        gps_score, gps_flags = await self._calculate_gps_score(activity)
        image_score, image_flags = await self._calculate_image_score(activity)
        frequency_score, freq_flags = await self._calculate_frequency_score(activity)

        # Merge all flags
        flags.update(gps_flags)
        flags.update(image_flags)
        flags.update(freq_flags)

        # Calculate final composite score
        final_score = round(gps_score + image_score + frequency_score, 2)

        # Apply Cross-Verification Bonuses
        cross_verif_bonus, cross_verif_flags = await self._calculate_cross_verification_bonus(activity)
        final_score += cross_verif_bonus
        flags.update(cross_verif_flags)

        # Cap at 100
        final_score = min(100.0, final_score)

        # Determine status based on score
        status = self._determine_status(final_score)

        # Persist the trust log
        trust_log = TrustLog(
            activity_id=activity.id,
            gps_score=gps_score,
            image_score=image_score,
            frequency_score=frequency_score,
            final_score=final_score,
            flags=flags,
        )
        self.db.add(trust_log)

        # Update the activity with trust results
        activity.trust_score = final_score
        activity.trust_flags = flags
        activity.status = status

        await self.db.commit()
        await self.db.refresh(activity)

        return final_score, flags

    # =========================================================================
    # GPS Consistency Score (0-30 points)
    # =========================================================================

    async def _calculate_gps_score(
        self, activity: Activity
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Evaluate GPS data quality and consistency.
        
        Scoring breakdown:
        - No GPS data at all: 0/30
        - GPS accuracy > 100m: Penalty applied
        - Distance from property: Penalty if > threshold
        - Historical consistency: Bonus for consistent locations
        """
        flags: Dict[str, Any] = {}
        score = 30.0  # Start at max, apply penalties

        # --- No GPS data: immediate zero ---
        if activity.latitude is None or activity.longitude is None:
            flags["gps_missing"] = True
            return 0.0, flags

        # --- GPS accuracy penalty ---
        if activity.gps_accuracy is not None:
            if activity.gps_accuracy > 100:
                # Very poor accuracy — major penalty
                score -= 15.0
                flags["gps_low_accuracy"] = True
            elif activity.gps_accuracy > 50:
                # Poor accuracy — moderate penalty
                score -= 8.0
                flags["gps_moderate_accuracy"] = True

        # --- Distance from assigned property ---
        if activity.property_id:
            from app.models.property import Property
            result = await self.db.execute(
                select(Property).where(Property.id == activity.property_id)
            )
            prop = result.scalar_one_or_none()

            if prop and prop.latitude and prop.longitude:
                distance_km = self._haversine_distance(
                    activity.latitude, activity.longitude,
                    prop.latitude, prop.longitude
                )
                max_distance = settings.trust_gps_max_distance_km

                if distance_km > max_distance:
                    # Activity location too far from property
                    score -= 20.0
                    flags["gps_too_far"] = True
                    flags["gps_distance_km"] = round(distance_km, 2)
                elif distance_km > max_distance * 0.5:
                    # Somewhat far — moderate penalty
                    score -= 8.0
                    flags["gps_distance_warning"] = True
                    flags["gps_distance_km"] = round(distance_km, 2)

        # --- Check for impossible travel speed ---
        speed_penalty, speed_flags = await self._check_movement_speed(activity)
        score += speed_penalty
        flags.update(speed_flags)

        # --- Historical GPS consistency ---
        # Check if user's recent activities are in similar locations
        consistency_bonus = await self._check_gps_consistency(activity)
        score += consistency_bonus

        return max(0.0, min(30.0, score)), flags

    async def _check_gps_consistency(self, activity: Activity) -> float:
        """
        Compare this activity's GPS to the user's recent submission
        locations. Consistent patterns earn a bonus.
        
        Returns:
            float: Bonus points (-5 to +5)
        """
        # Fetch last 10 activities from this user with GPS data
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
        recent_activities = result.scalars().all()

        if len(recent_activities) < 3:
            return 0.0  # Not enough history to evaluate

        # Calculate average distance from recent activities
        distances = [
            self._haversine_distance(
                activity.latitude, activity.longitude,
                a.latitude, a.longitude,
            )
            for a in recent_activities
        ]
        avg_distance = sum(distances) / len(distances)

        # Consistent location patterns earn a bonus
        if avg_distance < 2.0:
            return 3.0  # Very consistent
        elif avg_distance < 5.0:
            return 1.0  # Reasonably consistent
        elif avg_distance > 50.0:
            return -5.0  # Suspicious jumping around
        return 0.0

    async def _check_movement_speed(self, activity: Activity) -> Tuple[float, Dict[str, Any]]:
        """
        Check for impossible travel speed between this submission
        and the user's immediately previous submission.
        """
        flags: Dict[str, Any] = {}
        penalty = 0.0

        if activity.latitude is None or activity.longitude is None:
            return 0.0, flags

        # Get the immediate previous activity with GPS from this user
        result = await self.db.execute(
            select(Activity)
            .where(
                Activity.user_id == activity.user_id,
                Activity.id != activity.id,
                Activity.latitude.isnot(None),
                Activity.longitude.isnot(None),
                Activity.captured_at <= activity.captured_at
            )
            .order_by(Activity.captured_at.desc())
            .limit(1)
        )
        prev_activity = result.scalar_one_or_none()

        if not prev_activity or not prev_activity.latitude or not prev_activity.longitude:
            return 0.0, flags

        distance_km = self._haversine_distance(
            activity.latitude, activity.longitude,
            prev_activity.latitude, prev_activity.longitude
        )
        
        # Calculate time difference in hours
        time_diff = activity.captured_at - prev_activity.captured_at
        hours = time_diff.total_seconds() / 3600.0

        if hours <= 0:
            return 0.0, flags

        speed_kmh = distance_km / hours

        # Impossible speed (> 150 km/h)
        if speed_kmh > 150:
            penalty = -30.0
            flags["impossible_travel"] = True
            flags["travel_speed_kmh"] = round(speed_kmh, 1)
        # Unlikely speed (> 80 km/h in rural/field settings)
        elif speed_kmh > 80:
            penalty = -10.0
            flags["fast_travel_warning"] = True
            flags["travel_speed_kmh"] = round(speed_kmh, 1)

        return penalty, flags

    # =========================================================================
    # Image Uniqueness Score (0-35 points)
    # =========================================================================

    async def _calculate_image_score(
        self, activity: Activity
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Evaluate image uniqueness using perceptual hashing.
        
        Scoring breakdown:
        - No image: 0/35
        - Duplicate image detected: Heavy penalty
        - Similar image detected: Moderate penalty
        - Unique image: Full score
        """
        flags: Dict[str, Any] = {}
        score = 35.0

        # --- No image provided ---
        if not activity.image_url:
            flags["image_missing"] = True
            return 0.0, flags

        # --- No hash available (can't verify uniqueness) ---
        if not activity.image_hash:
            flags["image_hash_missing"] = True
            return 15.0, flags  # Partial credit — image exists but can't verify

        # --- Check for duplicate/similar images ---
        duplicate_found, similarity = await self._check_image_similarity(activity)

        if duplicate_found:
            if similarity >= 95:
                # Exact or near-exact duplicate
                score -= 30.0
                flags["image_duplicate"] = True
                flags["image_similarity"] = similarity
            elif similarity >= 80:
                # Very similar image
                score -= 20.0
                flags["image_very_similar"] = True
                flags["image_similarity"] = similarity
            elif similarity >= 60:
                # Somewhat similar
                score -= 10.0
                flags["image_similar"] = True
                flags["image_similarity"] = similarity

        return max(0.0, min(35.0, score)), flags

    async def _check_image_similarity(
        self, activity: Activity
    ) -> Tuple[bool, float]:
        """
        Compare this activity's image hash against all previous
        submissions from the same user.
        
        Uses hamming distance between perceptual hashes:
        - Distance 0: Identical images
        - Distance < 5: Near-duplicate (suspicious)
        - Distance < 10: Similar (worth noting)
        - Distance >= 10: Different images
        
        Returns:
            Tuple of (is_suspicious, similarity_percentage)
        """
        if not activity.image_hash:
            return False, 0.0

        # Fetch all image hashes from this user's previous activities
        result = await self.db.execute(
            select(Activity.image_hash)
            .where(
                Activity.user_id == activity.user_id,
                Activity.id != activity.id,
                Activity.image_hash.isnot(None),
            )
            .order_by(Activity.created_at.desc())
            .limit(100)  # Check last 100 submissions
        )
        previous_hashes = [row[0] for row in result.all()]

        if not previous_hashes:
            return False, 0.0

        # Find the minimum hamming distance
        min_distance = float("inf")
        for prev_hash in previous_hashes:
            distance = self._hamming_distance(activity.image_hash, prev_hash)
            min_distance = min(min_distance, distance)

        # Convert distance to similarity percentage
        # Hash length is typically 64 bits for pHash
        hash_length = max(len(activity.image_hash), 1)
        similarity = ((hash_length - min_distance) / hash_length) * 100

        threshold = settings.trust_image_hash_threshold
        is_suspicious = min_distance < threshold

        return is_suspicious, round(similarity, 1)

    # =========================================================================
    # Submission Frequency Score (0-35 points)
    # =========================================================================

    async def _calculate_frequency_score(
        self, activity: Activity
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Evaluate submission frequency patterns.
        
        Scoring breakdown:
        - Too many submissions per hour: Penalty
        - Submissions at suspicious hours (2-5 AM): Penalty
        - Consistent daily patterns: Bonus
        """
        flags: Dict[str, Any] = {}
        score = 35.0

        # --- Check submissions in the last hour ---
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        result = await self.db.execute(
            select(func.count(Activity.id))
            .where(
                Activity.user_id == activity.user_id,
                Activity.created_at >= one_hour_ago,
            )
        )
        hourly_count = result.scalar() or 0

        max_per_hour = settings.trust_max_submissions_per_hour
        if hourly_count > max_per_hour:
            # Too many submissions — likely automated
            score -= 25.0
            flags["high_frequency"] = True
            flags["submissions_last_hour"] = hourly_count
        elif hourly_count > max_per_hour * 0.7:
            # Approaching limit
            score -= 10.0
            flags["frequency_warning"] = True
            flags["submissions_last_hour"] = hourly_count

        # --- Check for suspicious time of day ---
        capture_hour = activity.captured_at.hour
        suspicious_start = settings.trust_suspicious_hours_start
        suspicious_end = settings.trust_suspicious_hours_end

        if suspicious_start <= capture_hour <= suspicious_end:
            score -= 10.0
            flags["suspicious_time"] = True
            flags["capture_hour"] = capture_hour

        # --- Check daily consistency bonus ---
        consistency_bonus = await self._check_daily_consistency(activity)
        score += consistency_bonus

        return max(0.0, min(35.0, score)), flags

    async def _check_daily_consistency(self, activity: Activity) -> float:
        """
        Reward users who submit consistently over multiple days.
        
        Returns:
            float: Bonus points (0 to 5)
        """
        # Check how many of the last 7 days had submissions
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
        result = await self.db.execute(
            select(func.count(func.distinct(func.date_trunc("day", Activity.created_at))))
            .where(
                Activity.user_id == activity.user_id,
                Activity.created_at >= seven_days_ago,
            )
        )
        active_days = result.scalar() or 0

        if active_days >= 5:
            return 5.0  # Very consistent user
        elif active_days >= 3:
            return 2.0  # Reasonably active
        return 0.0

    # =========================================================================
    # Cross-Verification Extension
    # =========================================================================

    async def _calculate_cross_verification_bonus(self, activity: Activity) -> Tuple[float, Dict[str, Any]]:
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

        # 1. Check for Sensor Data
        sensor_result = await self.db.execute(
            select(SensorReading).where(SensorReading.asset_id == activity.property_id).limit(1)
        )
        if sensor_result.scalar_one_or_none():
            bonus += 10.0
            flags["sensor_data_present"] = True

        # 2. Check for Community Validation
        community_result = await self.db.execute(
            select(CommunityValidation).where(
                CommunityValidation.asset_id == activity.property_id,
                CommunityValidation.response == "yes"
            ).limit(1)
        )
        if community_result.scalar_one_or_none():
            bonus += 10.0
            flags["community_validation_positive"] = True

        # 3. Check for Audit Passed
        audit_result = await self.db.execute(
            select(AuditTask).where(
                AuditTask.asset_id == activity.property_id,
                AuditTask.status == "completed"
            ).limit(1)
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
        
        Args:
            lat1, lon1: First coordinate pair (degrees)
            lat2, lon2: Second coordinate pair (degrees)
            
        Returns:
            float: Distance in kilometers
        """
        R = 6371.0  # Earth's radius in kilometers

        # Convert to radians
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)

        # Haversine formula
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
        
        The hamming distance is the number of bit positions where the
        two hashes differ. Lower distance = more similar images.
        
        Args:
            hash1: First hex-encoded hash string
            hash2: Second hex-encoded hash string
            
        Returns:
            int: Number of differing bits
        """
        try:
            # Convert hex strings to integers for XOR comparison
            val1 = int(hash1, 16)
            val2 = int(hash2, 16)
            # XOR and count set bits (differing positions)
            return bin(val1 ^ val2).count("1")
        except (ValueError, TypeError):
            return 64  # Max distance if hashes are invalid
