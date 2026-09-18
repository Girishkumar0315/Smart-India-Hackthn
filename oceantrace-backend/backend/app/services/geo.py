"""
Vectorised geospatial helpers.

These operate on whole numpy arrays at once (all vessels in a single
investigation scored together) rather than looping per-vessel in Python,
which is the main "efficiency" difference versus the client-side JS demo
logic — this scales to a real AIS corpus without a per-row Python loop.
"""
import numpy as np

R_EARTH_KM = 6371.0088


def haversine_km_vec(lat1, lon1, lat2, lon2):
    """Vectorised haversine distance in km. Any argument may be a scalar
    or a numpy array; broadcasting applies."""
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2.0) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2.0) ** 2
    return 2 * R_EARTH_KM * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def bearing_deg_vec(lat1, lon1, lat2, lon2):
    """Vectorised initial bearing in degrees, 0-360."""
    lat1r, lat2r = np.radians(lat1), np.radians(lat2)
    dlon = np.radians(lon2 - lon1)
    y = np.sin(dlon) * np.cos(lat2r)
    x = np.cos(lat1r) * np.sin(lat2r) - np.sin(lat1r) * np.cos(lat2r) * np.cos(dlon)
    brng = np.degrees(np.arctan2(y, x))
    return (brng + 360.0) % 360.0


def dest_point(lat, lon, bearing_deg, dist_km):
    """Single-point destination given bearing + distance (used for polygon generation)."""
    lat1 = np.radians(lat)
    lon1 = np.radians(lon)
    brng = np.radians(bearing_deg)
    ang_dist = dist_km / R_EARTH_KM
    lat2 = np.arcsin(np.sin(lat1) * np.cos(ang_dist) + np.cos(lat1) * np.sin(ang_dist) * np.cos(brng))
    lon2 = lon1 + np.arctan2(
        np.sin(brng) * np.sin(ang_dist) * np.cos(lat1),
        np.cos(ang_dist) - np.sin(lat1) * np.sin(lat2),
    )
    return float(np.degrees(lat2)), float(np.degrees(lon2))


def angular_alignment_vec(bearing_a, bearing_b):
    """cos(delta) in [-1, 1] — 1 means same direction, -1 means opposite."""
    return np.cos(np.radians(bearing_a - bearing_b))
