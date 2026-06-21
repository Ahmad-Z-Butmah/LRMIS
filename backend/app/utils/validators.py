"""
Pure parcel and GeoJSON validation functions.
No MongoDB access — the service layer is responsible for fetching data before calling these.
"""

from typing import Any


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _require(data: dict, field: str) -> Any:
    value = data.get(field)
    if value is None:
        raise ValueError(f"parcel field '{field}' is required")
    return value


# ---------------------------------------------------------------------------
# Coordinate-level validation
# ---------------------------------------------------------------------------

def validate_coordinate(point: Any, index: int) -> None:
    """Validate a single [longitude, latitude] coordinate point."""
    if not isinstance(point, (list, tuple)) or len(point) != 2:
        raise ValueError(
            f"coordinate at index {index} must be a list of exactly 2 values "
            "[longitude, latitude]"
        )
    lon, lat = point[0], point[1]
    if not isinstance(lon, (int, float)) or not isinstance(lat, (int, float)):
        raise ValueError(
            f"coordinate at index {index}: longitude and latitude must be numeric"
        )
    if not (-180 <= lon <= 180):
        raise ValueError(
            f"coordinate at index {index}: longitude {lon} is out of range [-180, 180]"
        )
    if not (-90 <= lat <= 90):
        raise ValueError(
            f"coordinate at index {index}: latitude {lat} is out of range [-90, 90]"
        )


# ---------------------------------------------------------------------------
# GeoJSON Polygon validation
# ---------------------------------------------------------------------------

def validate_geojson_polygon(geometry: Any) -> None:
    """Validate a GeoJSON geometry object as a closed Polygon."""
    if not isinstance(geometry, dict):
        raise ValueError("geometry must be an object")

    geo_type = geometry.get("type")
    if geo_type != "Polygon":
        raise ValueError(
            f"geometry.type must be 'Polygon', got '{geo_type}'"
        )

    coordinates = geometry.get("coordinates")
    if coordinates is None:
        raise ValueError("geometry.coordinates is required")

    if not isinstance(coordinates, list) or len(coordinates) == 0:
        raise ValueError("geometry.coordinates must be a non-empty list")

    # A GeoJSON Polygon's first element is the exterior ring.
    exterior_ring = coordinates[0]
    if not isinstance(exterior_ring, list) or len(exterior_ring) < 4:
        raise ValueError(
            "geometry.coordinates exterior ring must have at least 4 points "
            "(3 unique vertices + the closing repeat)"
        )

    for i, point in enumerate(exterior_ring):
        validate_coordinate(point, i)

    # Closed-ring rule: first and last coordinate must be identical.
    if exterior_ring[0] != exterior_ring[-1]:
        raise ValueError(
            "geometry.coordinates: the first and last coordinate must be the same "
            "(the ring must be closed)"
        )


# ---------------------------------------------------------------------------
# Full parcel validation
# ---------------------------------------------------------------------------

def validate_parcel(parcel: dict) -> None:
    """
    Validate that a parcel object contains all required fields and a valid
    GeoJSON Polygon geometry.

    Raises ValueError with a descriptive message on the first failure found.
    """
    if not isinstance(parcel, dict):
        raise ValueError("parcel data must be an object")

    for field in ("parcel_number", "block_number", "basin_number", "zone_id"):
        _require(parcel, field)

    geometry = _require(parcel, "geometry")
    validate_geojson_polygon(geometry)
