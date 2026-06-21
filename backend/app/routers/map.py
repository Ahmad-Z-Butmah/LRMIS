"""
Map / GeoFeed router — Tasks 15–20, 21, 22.
Prefix: /analytics/geofeeds (appears under /analytics in Swagger).
"""

from typing import Optional

from fastapi import APIRouter, Query

from app.services.map_service import (
    get_disputed_parcels_geofeed,
    get_nearby_parcels,
    get_parcels_geofeed,
    get_pending_applications_geofeed,
    get_pending_heatmap,
    get_survey_tasks_geofeed,
)

router = APIRouter(prefix="/analytics/geofeeds", tags=["Map / GeoFeeds"])


# ── Task 16 + 21: Parcel GeoJSON feed ─────────────────────────────────────────

@router.get(
    "/parcels",
    summary="GeoJSON FeatureCollection of all parcels with Polygon geometry",
)
def get_parcels(
    zone_id: Optional[str] = Query(None, description="Filter by zone_id"),
    status: Optional[str] = Query(None, description="Filter by registration_status"),
    dispute_state: Optional[str] = Query(None, description="Filter by dispute_state (disputed|none)"),
):
    return get_parcels_geofeed(zone_id=zone_id, status=status, dispute_state=dispute_state)


# ── Task 17 + 21: Pending applications GeoFeed ───────────────────────────────

@router.get(
    "/pending-applications",
    summary="GeoJSON FeatureCollection of pending applications (5 statuses)",
)
def get_pending_apps(
    zone_id: Optional[str] = Query(None, description="Filter by zone_id"),
    application_type: Optional[str] = Query(None, description="Filter by application_type"),
    status: Optional[str] = Query(None, description="Filter by status (must be a pending status)"),
):
    return get_pending_applications_geofeed(
        zone_id=zone_id, application_type=application_type, status=status
    )


# ── Task 18 + 21: Pending heatmap ─────────────────────────────────────────────

@router.get(
    "/pending-heatmap",
    summary="GeoJSON Point FeatureCollection for pending-application heatmap by zone",
)
def get_heatmap(
    zone_id: Optional[str] = Query(None, description="Filter by zone_id"),
    status: Optional[str] = Query(None, description="Filter by status"),
):
    return get_pending_heatmap(zone_id=zone_id, status=status)


# ── Task 19 + 21: Disputed parcels GeoFeed ───────────────────────────────────

@router.get(
    "/disputed-parcels",
    summary="GeoJSON FeatureCollection of disputed / under-objection parcels",
)
def get_disputed(
    zone_id: Optional[str] = Query(None, description="Filter by zone_id"),
    dispute_state: Optional[str] = Query(None, description="Filter by dispute_state"),
):
    return get_disputed_parcels_geofeed(zone_id=zone_id, dispute_state=dispute_state)


# ── Task 20 + 21: Survey tasks GeoFeed ───────────────────────────────────────

@router.get(
    "/survey-tasks",
    summary="GeoJSON FeatureCollection of active survey tasks",
)
def get_survey_tasks(
    zone_id: Optional[str] = Query(None, description="Filter by zone_id"),
    status: Optional[str] = Query(None, description="Filter by task status"),
):
    return get_survey_tasks_geofeed(zone_id=zone_id, status=status)


# ── Task 22: Nearby parcels via $geoNear ─────────────────────────────────────

@router.get(
    "/nearby",
    summary="Find parcels near a coordinate using $geoNear (requires real MongoDB + 2dsphere index)",
)
def get_nearby(
    lng: float = Query(..., description="Longitude of the query point (e.g. 35.18)"),
    lat: float = Query(..., description="Latitude of the query point (e.g. 31.98)"),
    max_distance: int = Query(1000, description="Maximum search radius in metres"),
):
    return get_nearby_parcels(lng=lng, lat=lat, max_distance=max_distance)
