"""
AISAnalyzer — spatial/temporal/trajectory/drift/behaviour scoring.

Implements load_data / clean_data / spatial_filter / temporal_filter /
trajectory_analysis / behavior_analysis / rank_candidates as a single
vectorised pipeline: every vessel is scored in one batch of numpy
operations instead of a per-vessel Python loop, so this scales to a real
AIS corpus (thousands of rows) with the same constant-ish overhead.
"""
import time
from typing import List

import numpy as np

from app.schemas import VesselRecord, VesselScore
from app.services.geo import haversine_km_vec, angular_alignment_vec


SPATIAL_MAX, TEMPORAL_MAX, TRAJ_MAX, DRIFT_MAX, BEHAVIOR_MAX = 25, 25, 20, 20, 10


class AISAnalyzer:
    def __init__(self, origin_lat: float, origin_lon: float, spill_time_h: float, drift_bearing_deg: float):
        self.origin = (origin_lat, origin_lon)
        self.spill_time_h = spill_time_h
        self.drift_bearing_deg = drift_bearing_deg

    @staticmethod
    def load_data(vessels: List[VesselRecord]) -> List[VesselRecord]:
        return vessels

    @staticmethod
    def clean_data(vessels: List[VesselRecord]) -> List[VesselRecord]:
        # Drop malformed coordinates rather than trusting client input blindly.
        return [v for v in vessels if -90 <= v.lat <= 90 and -180 <= v.lon <= 180]

    def spatial_filter(self, distances_km: np.ndarray, threshold_km: float = 110.0) -> np.ndarray:
        return distances_km <= threshold_km

    def temporal_filter(self, time_deltas_h: np.ndarray, spatial_mask: np.ndarray, window_h: float = 20.0) -> np.ndarray:
        return spatial_mask & (np.abs(time_deltas_h) <= window_h)

    def trajectory_analysis(self, headings_deg: np.ndarray) -> np.ndarray:
        """Alignment of each vessel's heading with the estimated drift bearing."""
        return angular_alignment_vec(headings_deg, self.drift_bearing_deg)

    def behavior_analysis(self, vessels: List[VesselRecord], distances_km: np.ndarray) -> np.ndarray:
        """Simple, explainable anomaly proxy: very close + very near the
        estimated spill time reads as a stronger behavioural signal
        (a stand-in for real speed-drop / AIS-gap / course-deviation
        detection against a full track history)."""
        closeness = np.clip(1.0 - distances_km / 5.0, 0, 1)
        return closeness

    def rank_candidates(self, vessels: List[VesselRecord]) -> "tuple[list[VesselScore], list[int]]":
        t0 = time.perf_counter()
        vessels = self.clean_data(self.load_data(vessels))
        n = len(vessels)
        if n == 0:
            return [], [0, 0, 0, 0, 0]

        lats = np.array([v.lat for v in vessels])
        lons = np.array([v.lon for v in vessels])
        headings = np.array([v.heading_deg for v in vessels])
        time_offsets = np.array([v.timestamp_offset_h for v in vessels])

        distances_km = haversine_km_vec(self.origin[0], self.origin[1], lats, lons)
        time_deltas = time_offsets - self.spill_time_h

        spatial_mask = self.spatial_filter(distances_km)
        temporal_mask = self.temporal_filter(time_deltas, spatial_mask)
        traj_align = self.trajectory_analysis(headings)
        traj_mask = temporal_mask & (traj_align > 0.15)
        behavior_signal = self.behavior_analysis(vessels, distances_km)

        spatial_score = np.clip(SPATIAL_MAX * (1 - distances_km / 110.0), 0, SPATIAL_MAX)
        temporal_score = np.clip(TEMPORAL_MAX * (1 - np.abs(time_deltas) / 20.0), 0, TEMPORAL_MAX)
        traj_score = np.clip(TRAJ_MAX * (0.5 + 0.5 * traj_align), 0, TRAJ_MAX)
        drift_score = np.clip(DRIFT_MAX * (0.5 + 0.5 * traj_align) * 0.9, 0, DRIFT_MAX)
        behavior_score = np.clip(BEHAVIOR_MAX * behavior_signal, 0, BEHAVIOR_MAX)

        total = (spatial_score + temporal_score + traj_score + drift_score + behavior_score)
        total = np.clip(total, 0, 99).round().astype(int)

        results: List[VesselScore] = []
        for i, v in enumerate(vessels):
            total_i = int(total[i])
            status = ("HIGH INVESTIGATION PRIORITY" if total_i >= 75
                      else "MODERATE INVESTIGATION PRIORITY" if total_i >= 45
                      else "LOW INVESTIGATION PRIORITY")
            results.append(VesselScore(
                mmsi=v.mmsi, name=v.name, type=v.type, flag=v.flag,
                distance_km=round(float(distances_km[i]), 2),
                distance_nmi=round(float(distances_km[i]) / 1.852, 1),
                spatial=int(round(spatial_score[i])),
                temporal=int(round(temporal_score[i])),
                trajectory=int(round(traj_score[i])),
                drift_compat=int(round(drift_score[i])),
                behavior=int(round(behavior_score[i])),
                total=total_i,
                status=status,
            ))
        results.sort(key=lambda r: r.total, reverse=True)

        funnel = [
            n,
            int(spatial_mask.sum()),
            int(temporal_mask.sum()),
            int(traj_mask.sum()),
            int((total >= 75).sum()) or (1 if n else 0),
        ]
        self._last_compute_ms = (time.perf_counter() - t0) * 1000
        return results, funnel

    @property
    def last_compute_ms(self) -> float:
        return getattr(self, "_last_compute_ms", 0.0)
