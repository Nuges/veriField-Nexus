import logging
import math
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.workspaces.models import Property
# from app.models.sensor_reading import SensorReading
from app.core.config import settings
from app.domains.activities.models import Activity
from app.domains.ai_trust_engine.models import TrustLog

logger = logging.getLogger("verifield.trust")


class GPSDetector:
    def evaluate(
        self, activity: Activity, property_coord: Optional[Tuple[float, float]] = None
    ) -> Tuple[float, float, Dict[str, Any]]:
        findings = {}
        score = 30.0  # Base dimension weight
        confidence = 1.0

        if activity.latitude is None or activity.longitude is None:
            findings["gps_missing"] = True
            return (
                0.0,
                1.0,
                {"severity": "CRITICAL", "message": "GPS coordinates are missing."},
            )

        # Check accuracy
        if activity.gps_accuracy is not None:
            if activity.gps_accuracy > 100:
                score -= 15.0
                findings["gps_low_accuracy"] = True
            elif activity.gps_accuracy > 50:
                score -= 7.5
                findings["gps_moderate_accuracy"] = True

        # Check distance from property
        if property_coord:
            prop_lat, prop_lon = property_coord
            distance = self._haversine_distance(
                activity.latitude, activity.longitude, prop_lat, prop_lon
            )
            max_dist = settings.trust_gps_max_distance_km
            if distance > max_dist:
                score -= 19.5
                findings["gps_too_far"] = True
                findings["gps_distance_km"] = round(distance, 2)
            elif distance > max_dist * 0.5:
                score -= 7.5
                findings["gps_distance_warning"] = True
                findings["gps_distance_km"] = round(distance, 2)

        return max(0.0, score), confidence, findings

    @staticmethod
    def _haversine_distance(
        lat1: float, lon1: float, lat2: float, lon2: float
    ) -> float:
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


class ImageDetector:
    def evaluate(self, activity: Activity) -> Tuple[float, float, Dict[str, Any]]:
        findings = {}
        score = 40.0

        if not activity.image_url:
            findings["image_missing"] = True
            return 16.0, 1.0, findings

        if not activity.image_hash:
            findings["image_hash_missing"] = True
            return 16.0, 1.0, findings

        return score, 1.0, findings


class DuplicateDetector:
    async def evaluate(
        self, db: AsyncSession, activity: Activity
    ) -> Tuple[float, float, Dict[str, Any]]:
        findings = {}
        deduction = 0.0

        if not activity.image_hash:
            return 0.0, 1.0, {}

        # Query last 100 hashes
        stmt = (
            select(Activity.image_hash)
            .where(Activity.id != activity.id, Activity.image_hash.isnot(None))
            .order_by(Activity.created_at.desc())
            .limit(100)
        )
        res = await db.execute(stmt)
        hashes = [r[0] for r in res.all()]

        if not hashes:
            return 0.0, 1.0, {}

        min_dist = 64
        for prev in hashes:
            dist = self._hamming_distance(activity.image_hash, prev)
            min_dist = min(min_dist, dist)

        sim = ((64 - min_dist) / 64) * 100.0
        threshold = settings.trust_image_hash_threshold
        if min_dist < threshold:
            if sim >= 95:
                deduction = 32.0
                findings["image_duplicate"] = True
            elif sim >= 80:
                deduction = 20.0
                findings["image_very_similar"] = True
            else:
                deduction = 10.0
                findings["image_similar"] = True
            findings["image_similarity"] = round(sim, 1)

        return -deduction, 1.0, findings

    @staticmethod
    def _hamming_distance(h1: str, h2: str) -> int:
        try:
            return bin(int(h1, 16) ^ int(h2, 16)).count("1")
        except Exception:
            return 64


class TimestampDetector:
    def evaluate(self, activity: Activity) -> Tuple[float, float, Dict[str, Any]]:
        findings = {}
        score = 0.0
        hour = activity.captured_at.hour
        sus_start = settings.trust_suspicious_hours_start
        sus_end = settings.trust_suspicious_hours_end

        if sus_start <= hour <= sus_end:
            score -= 9.0
            findings["suspicious_time"] = True
            findings["capture_hour"] = hour

        return score, 1.0, findings


class SensorDetector:
    async def evaluate(
        self, db: AsyncSession, activity: Activity
    ) -> Tuple[float, float, Dict[str, Any]]:
        # SensorReading model is deprecated/missing in new architecture.
        # Skip telemetry check for now.
        return 0.0, 1.0, {}


class BehaviouralDetector:
    async def evaluate(
        self, db: AsyncSession, activity: Activity
    ) -> Tuple[float, float, Dict[str, Any]]:
        findings = {}
        score = 30.0  # Base dimension weight

        # Check hourly count
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        stmt = select(func.count(Activity.id)).where(
            Activity.user_id == activity.user_id, Activity.created_at >= one_hour_ago
        )
        res = await db.execute(stmt)
        count = res.scalar() or 0
        max_hour = settings.trust_max_submissions_per_hour

        if count > max_hour:
            score -= 24.0
            findings["high_frequency"] = True
            findings["submissions_last_hour"] = count
        elif count > max_hour * 0.7:
            score -= 7.5
            findings["frequency_warning"] = True
            findings["submissions_last_hour"] = count

        return max(0.0, score), 1.0, findings


class TrustEngineService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def calculate_trust(self, activity: Activity) -> Tuple[float, Dict[str, Any]]:
        findings = {}

        # Resolve property coords if linked
        prop_coord = None
        if activity.property_id:
            prop = await self.db.get(Property, activity.property_id)
            if prop and prop.latitude and prop.longitude:
                prop_coord = (prop.latitude, prop.longitude)

        # 1. Run GPS Detector
        gps_dec = GPSDetector()
        gps_score, _, gps_find = gps_dec.evaluate(activity, prop_coord)
        findings.update(gps_find)

        # 2. Run Image Detector
        img_dec = ImageDetector()
        img_score, _, img_find = img_dec.evaluate(activity)
        findings.update(img_find)

        # 3. Run Duplicate Detector
        dup_dec = DuplicateDetector()
        dup_score_change, _, dup_find = await dup_dec.evaluate(self.db, activity)
        findings.update(dup_find)

        # 4. Run Timestamp Detector
        time_dec = TimestampDetector()
        time_score_change, _, time_find = time_dec.evaluate(activity)
        findings.update(time_find)

        # 5. Run Sensor Detector
        sens_dec = SensorDetector()
        sens_score_change, _, sens_find = await sens_dec.evaluate(self.db, activity)
        findings.update(sens_find)

        # 6. Run Behavioural Detector
        beh_dec = BehaviouralDetector()
        beh_score, _, beh_find = await beh_dec.evaluate(self.db, activity)
        findings.update(beh_find)

        # Aggregate Score
        # GPS (max 30) + Image (max 40) + Behavioural (max 30) + Changes + Bonus
        final_score = (
            gps_score
            + img_score
            + beh_score
            + dup_score_change
            + time_score_change
            + sens_score_change
        )
        final_score = max(0.0, min(100.0, round(final_score, 2)))

        if findings.get("image_duplicate"):
            status = "flagged"
            findings["fraud_flag"] = True
        elif final_score >= 80.0:
            status = "verified"
        elif final_score >= 50.0:
            status = "review"
        else:
            status = "flagged"

        # Update activity model
        activity.trust_score = final_score
        activity.trust_flags = findings
        activity.status = status

        # Save to trust log
        log = TrustLog(
            activity_id=activity.id,
            gps_score=gps_score,
            image_score=img_score,
            frequency_score=beh_score,
            final_score=final_score,
            flags=findings,
        )
        self.db.add(log)
        await self.db.commit()

        return final_score, findings


class TelemetryAnomalyDetector:
    async def evaluate(self, db: AsyncSession, property_id: str) -> Dict[str, Any]:
        """
        Analyzes historical telemetry data to detect potential anomalies
        (e.g. sensor spoofing, massive unexpected drops).
        """
        # SensorReading is deprecated/missing in new architecture.
        return {"status": "INSUFFICIENT_DATA"}
