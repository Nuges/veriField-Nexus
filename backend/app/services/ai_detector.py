"""
=============================================================================
VeriField Nexus — AI Anomaly Detection Engine
=============================================================================
Two-layer anomaly detection system for field activity submissions.
Layer 1: Rule-based checks (GPS spoofing, impossible travel, etc.)
Layer 2: Optional ML using sklearn IsolationForest
=============================================================================
"""

import math
from datetime import datetime, timedelta, timezone
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.activity import Activity
from app.models.anomaly_flag import AnomalyFlag
from app.core.config import settings


class AnomalyDetector:
    """AI-powered anomaly detection for field activity submissions."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def analyze_activity(self, activity: Activity) -> List[AnomalyFlag]:
        """Run all anomaly detection checks on an activity."""
        flags: List[AnomalyFlag] = []
        flags.extend(await self._detect_gps_spoofing(activity))
        flags.extend(await self._detect_impossible_travel(activity))
        flags.extend(await self._detect_image_recycling(activity))
        flags.extend(await self._detect_bot_patterns(activity))
        flags.extend(await self._detect_time_anomalies(activity))
        for flag in flags:
            self.db.add(flag)
        if flags:
            await self.db.commit()
        return flags

    async def _detect_gps_spoofing(self, activity: Activity) -> List[AnomalyFlag]:
        """Detect fabricated GPS coordinates (too round, zero accuracy)."""
        flags = []
        if activity.latitude is None or activity.longitude is None:
            return flags
        lat_str = f"{activity.latitude:.6f}"
        lon_str = f"{activity.longitude:.6f}"
        if lat_str.endswith("000000") or lon_str.endswith("000000"):
            flags.append(AnomalyFlag(
                activity_id=activity.id, user_id=activity.user_id,
                flag_type="gps_spoofing", severity="medium",
                description=f"GPS coordinates appear fabricated: ({activity.latitude}, {activity.longitude}).",
            ))
        if activity.gps_accuracy is not None and activity.gps_accuracy == 0.0:
            flags.append(AnomalyFlag(
                activity_id=activity.id, user_id=activity.user_id,
                flag_type="gps_spoofing", severity="high",
                description="GPS accuracy exactly 0.0m — impossible for real devices.",
            ))
        return flags

    async def _detect_impossible_travel(self, activity: Activity) -> List[AnomalyFlag]:
        """Detect impossible travel speed between consecutive submissions."""
        flags = []
        if activity.latitude is None or activity.longitude is None:
            return flags
        result = await self.db.execute(
            select(Activity).where(
                Activity.user_id == activity.user_id, Activity.id != activity.id,
                Activity.latitude.isnot(None), Activity.longitude.isnot(None),
            ).order_by(Activity.created_at.desc()).limit(1)
        )
        previous = result.scalar_one_or_none()
        if previous is None:
            return flags
        distance_km = self._haversine(activity.latitude, activity.longitude, previous.latitude, previous.longitude)
        time_diff = max(abs((activity.captured_at - previous.captured_at).total_seconds()), 1)
        speed_kmh = (distance_km / time_diff) * 3600
        if speed_kmh > 900 and distance_km > 10:
            flags.append(AnomalyFlag(
                activity_id=activity.id, user_id=activity.user_id,
                flag_type="impossible_travel", severity="high",
                description=f"Impossible travel: {distance_km:.1f}km in {time_diff/60:.1f}min = {speed_kmh:.0f}km/h.",
            ))
        elif speed_kmh > 200 and distance_km > 5:
            flags.append(AnomalyFlag(
                activity_id=activity.id, user_id=activity.user_id,
                flag_type="impossible_travel", severity="medium",
                description=f"Fast travel: {distance_km:.1f}km in {time_diff/60:.1f}min = {speed_kmh:.0f}km/h.",
            ))
        return flags

    async def _detect_image_recycling(self, activity: Activity) -> List[AnomalyFlag]:
        """Detect exact image hash duplicates across user submissions."""
        flags = []
        if not activity.image_hash:
            return flags
        result = await self.db.execute(
            select(Activity).where(
                Activity.user_id == activity.user_id, Activity.id != activity.id,
                Activity.image_hash == activity.image_hash,
            ).limit(1)
        )
        match = result.scalar_one_or_none()
        if match:
            flags.append(AnomalyFlag(
                activity_id=activity.id, user_id=activity.user_id,
                flag_type="image_duplicate", severity="critical",
                description=f"Exact image duplicate of activity {match.id} from {match.created_at.isoformat()}.",
            ))
        return flags

    async def _detect_bot_patterns(self, activity: Activity) -> List[AnomalyFlag]:
        """Detect bot-like submission patterns (high volume, regular intervals)."""
        flags = []
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        result = await self.db.execute(
            select(Activity.created_at).where(
                Activity.user_id == activity.user_id, Activity.created_at >= one_hour_ago,
            ).order_by(Activity.created_at.asc())
        )
        timestamps = [row[0] for row in result.all()]
        if len(timestamps) > settings.trust_max_submissions_per_hour * 2:
            flags.append(AnomalyFlag(
                activity_id=activity.id, user_id=activity.user_id,
                flag_type="pattern_anomaly", severity="critical",
                description=f"Extreme volume: {len(timestamps)} submissions in 1 hour.",
            ))
        if len(timestamps) >= 5:
            intervals = [(timestamps[i+1]-timestamps[i]).total_seconds() for i in range(len(timestamps)-1)]
            avg = sum(intervals) / len(intervals)
            if avg > 0:
                variance = sum((x - avg)**2 for x in intervals) / len(intervals)
                cv = math.sqrt(variance) / avg
                if cv < 0.1 and len(intervals) >= 4:
                    flags.append(AnomalyFlag(
                        activity_id=activity.id, user_id=activity.user_id,
                        flag_type="pattern_anomaly", severity="high",
                        description=f"Regular intervals detected (CV={cv:.3f}). Likely automated.",
                    ))
        return flags

    async def _detect_time_anomalies(self, activity: Activity) -> List[AnomalyFlag]:
        """Detect suspicious submission times and large capture-submit gaps."""
        flags = []
        hour = activity.captured_at.hour
        if settings.trust_suspicious_hours_start <= hour <= settings.trust_suspicious_hours_end:
            flags.append(AnomalyFlag(
                activity_id=activity.id, user_id=activity.user_id,
                flag_type="time_anomaly", severity="low",
                description=f"Activity captured at {hour}:00 (suspicious hours window).",
            ))
        if activity.submitted_at and activity.captured_at:
            gap = abs((activity.submitted_at - activity.captured_at).total_seconds())
            if gap > 7 * 86400:
                flags.append(AnomalyFlag(
                    activity_id=activity.id, user_id=activity.user_id,
                    flag_type="time_anomaly", severity="medium",
                    description=f"Large capture-submit gap: {gap/86400:.1f} days.",
                ))
        return flags

    @staticmethod
    def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Haversine distance between two GPS coordinates in kilometers."""
        R = 6371.0
        la1, la2 = math.radians(lat1), math.radians(lat2)
        dlat, dlon = math.radians(lat2-lat1), math.radians(lon2-lon1)
        a = math.sin(dlat/2)**2 + math.cos(la1)*math.cos(la2)*math.sin(dlon/2)**2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
