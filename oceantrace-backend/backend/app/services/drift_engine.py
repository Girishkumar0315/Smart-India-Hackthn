"""
DriftEngine — PROTOTYPE physically-inspired backward/forward drift model.

Real production version would replace estimate_origin()'s simplified
bearing/distance projection with an actual particle-tracking hindcast over
gridded current + wind fields (e.g. OpenDrift / HYCOM + ERA5). The public
method signatures below are kept stable so that swap is a drop-in change.
"""
import time
import numpy as np

from app.services.geo import dest_point


class DriftEngine:
    def __init__(self, wind_dir_deg: float, wind_speed_kt: float, current_dir_deg: float, current_speed_kt: float):
        self.wind_dir_deg = wind_dir_deg
        self.wind_speed_kt = wind_speed_kt
        self.current_dir_deg = current_dir_deg
        self.current_speed_kt = current_speed_kt
        # Simple wind-drift-factor model: ~3% of wind speed adds to surface current.
        wx = current_speed_kt * np.sin(np.radians(current_dir_deg)) + 0.03 * wind_speed_kt * np.sin(np.radians(wind_dir_deg))
        wy = current_speed_kt * np.cos(np.radians(current_dir_deg)) + 0.03 * wind_speed_kt * np.cos(np.radians(wind_dir_deg))
        self.net_bearing_deg = float((np.degrees(np.arctan2(wx, wy)) + 360) % 360)
        self.net_speed_kt = float(np.hypot(wx, wy))

    def forward_simulation(self, origin_lat, origin_lon, hours: float):
        dist_km = self.net_speed_kt * 1.852 * hours
        return dest_point(origin_lat, origin_lon, self.net_bearing_deg, dist_km)

    def backward_simulation(self, observed_lat, observed_lon, hours: float):
        dist_km = self.net_speed_kt * 1.852 * hours
        return dest_point(observed_lat, observed_lon, (self.net_bearing_deg + 180) % 360, dist_km)

    def generate_probability_field(self, origin_lat, origin_lon, n_bands: int = 3):
        bands = []
        levels = ["HIGH", "MEDIUM", "LOW"][:n_bands]
        for i, level in enumerate(levels):
            bands.append({"center": [origin_lat, origin_lon], "radius_km": 6 + i * 5, "level": level})
        return bands

    def estimate_origin(self, observed_lat, observed_lon, area_km2: float):
        t0 = time.perf_counter()
        # Larger / more diffuse slicks are treated as (weakly) older -> further back-projected.
        age_h = float(np.clip(20 + np.sqrt(max(area_km2, 0.1)) * 3, 24, 52))
        origin_lat, origin_lon = self.backward_simulation(observed_lat, observed_lon, age_h)
        window = f"T-{int(age_h+6)}h to T-{int(age_h-6)}h"
        compute_ms = (time.perf_counter() - t0) * 1000
        return {
            "origin_lat": origin_lat, "origin_lon": origin_lon,
            "age_h": age_h, "window": window, "compute_ms": compute_ms,
        }
