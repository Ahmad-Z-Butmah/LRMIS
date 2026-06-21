"""
Map / GeoFeed service — Tasks 15–20, 21, 22.

GeoJSON is built here; routers in map.py expose the endpoints.

Data sources:
  'parcels'      — GeoJSON Polygon geometry per parcel
  'applications' — application status, parcel_ref (string or dict), priority
  'survey_tasks' — task assignment, milestone, report_uploaded
  'objections'   — submitted objections (disputed parcels)

Collection source of truth for applications:
  'applications' — same as Student 1 service layer.
  Both 'applications' and 'land_applications' are seeded identically.
  Student 3 analytics use 'applications' for consistency.
"""

from typing import Any, Dict, List, Optional

from app.database import db

_PARCELS = "parcels"
_APPLICATIONS = "applications"
_SURVEY_TASKS = "survey_tasks"
_OBJECTIONS = "objections"

# Application statuses considered "pending"
_PENDING_STATUSES = [
    "submitted",
    "pre_checked",
    "survey_required",
    "missing_documents",
    "under_objection",
]

# Survey task statuses that are "active"
_ACTIVE_TASK_STATUSES = [
    "assigned",
    "visit_scheduled",
    "arrived_on_site",
    "survey_started",
    "survey_completed",
    "report_uploaded",
]


# ── Internal helpers ──────────────────────────────────────────────────────────

def _is_valid_polygon(geometry: Any) -> bool:
    """Return True if geometry is a non-empty GeoJSON Polygon."""
    if not isinstance(geometry, dict):
        return False
    if geometry.get("type") != "Polygon":
        return False
    coords = geometry.get("coordinates")
    if not coords or not isinstance(coords, list):
        return False
    ring = coords[0] if coords else []
    return isinstance(ring, list) and len(ring) >= 4


def _centroid_of_polygon(geometry: dict) -> Optional[List[float]]:
    """Return [lon, lat] centroid of a GeoJSON Polygon exterior ring."""
    try:
        ring = geometry["coordinates"][0]
        lons = [pt[0] for pt in ring]
        lats = [pt[1] for pt in ring]
        return [round(sum(lons) / len(lons), 6), round(sum(lats) / len(lats), 6)]
    except (KeyError, IndexError, TypeError, ZeroDivisionError):
        return None


def _parcel_lookup_by_ref(parcel_ref: Any) -> Optional[dict]:
    """Resolve a parcel_ref (string or dict) to its parcels document."""
    if isinstance(parcel_ref, dict):
        pn = parcel_ref.get("parcel_number") or parcel_ref.get("parcel_id")
    else:
        pn = str(parcel_ref) if parcel_ref else None
    if not pn:
        return None
    return db[_PARCELS].find_one({"parcel_number": pn}, {"_id": 0})


def _empty_collection() -> dict:
    return {"type": "FeatureCollection", "features": []}


def _make_feature(geometry: dict, properties: dict) -> dict:
    return {"type": "Feature", "geometry": geometry, "properties": properties}


# ── Task 16 + 21: Parcel GeoJSON Feed ─────────────────────────────────────────

def get_parcels_geofeed(
    zone_id: Optional[str] = None,
    status: Optional[str] = None,
    dispute_state: Optional[str] = None,
) -> dict:
    """
    Return a GeoJSON FeatureCollection of all parcels with Polygon geometry.
    Properties: parcel_id, parcel_number, zone_id, registration_status, dispute_state.
    Task 21: accepts optional zone_id, status, dispute_state filter params.
    """
    query: Dict[str, Any] = {}
    if zone_id:
        query["zone_id"] = zone_id

    parcels = list(db[_PARCELS].find(query, {"_id": 0}))
    features = []

    disputed_parcel_refs = set(
        a.get("parcel_ref") if isinstance(a.get("parcel_ref"), str)
        else (a.get("parcel_ref") or {}).get("parcel_number")
        for a in db[_APPLICATIONS].find(
            {"status": "under_objection"},
            {"parcel_ref": 1, "_id": 0}
        )
    )

    for p in parcels:
        geometry = p.get("geometry")
        if not _is_valid_polygon(geometry):
            continue

        pn = p.get("parcel_number") or p.get("parcel_code")

        app = db[_APPLICATIONS].find_one(
            {"$or": [
                {"parcel_ref": pn},
                {"parcel_ref.parcel_number": pn},
            ]},
            {"status": 1, "_id": 0},
            sort=[("updated_at", -1)],
        )
        registration_status = app.get("status", "registered") if app else "registered"
        ds = "disputed" if pn in disputed_parcel_refs else "none"

        if status and registration_status != status:
            continue
        if dispute_state and ds != dispute_state:
            continue

        features.append(_make_feature(
            geometry=geometry,
            properties={
                "parcel_id": p.get("parcel_code") or pn,
                "parcel_number": pn,
                "zone_id": p.get("zone_id"),
                "registration_status": registration_status,
                "dispute_state": ds,
            },
        ))

    return {"type": "FeatureCollection", "features": features}


# ── Task 17 + 21: Pending Applications GeoFeed ───────────────────────────────

def get_pending_applications_geofeed(
    zone_id: Optional[str] = None,
    application_type: Optional[str] = None,
    status: Optional[str] = None,
) -> dict:
    """
    GeoJSON FeatureCollection of pending applications.
    Task 21: accepts optional zone_id, application_type, status filter params.
    """
    query: Dict[str, Any] = {}
    if status and status in _PENDING_STATUSES:
        query["status"] = status
    else:
        query["status"] = {"$in": _PENDING_STATUSES}
    if application_type:
        query["application_type"] = application_type

    apps = list(db[_APPLICATIONS].find(query, {"_id": 0}))
    features = []

    for app in apps:
        parcel = _parcel_lookup_by_ref(app.get("parcel_ref"))
        geometry = None
        if parcel:
            g = parcel.get("geometry")
            if _is_valid_polygon(g):
                geometry = g

        if geometry is None:
            continue

        parcel_ref = app.get("parcel_ref")
        pn = (
            parcel_ref.get("parcel_number")
            if isinstance(parcel_ref, dict)
            else str(parcel_ref) if parcel_ref else None
        )
        app_zone_id = (
            parcel_ref.get("zone_id")
            if isinstance(parcel_ref, dict)
            else (parcel.get("zone_id") if parcel else None)
        )

        if zone_id and app_zone_id != zone_id:
            continue

        features.append(_make_feature(
            geometry=geometry,
            properties={
                "application_id": app.get("application_id"),
                "status": app.get("status"),
                "parcel_number": pn,
                "zone_id": app_zone_id,
                "priority": app.get("priority"),
            },
        ))

    return {"type": "FeatureCollection", "features": features}


# ── Task 18 + 21: Pending Applications Heatmap ───────────────────────────────

def get_pending_heatmap(
    zone_id: Optional[str] = None,
    status: Optional[str] = None,
) -> dict:
    """
    Point-per-zone GeoJSON FeatureCollection for heatmap rendering.
    Task 21: accepts optional zone_id, status filter params.
    """
    query: Dict[str, Any] = {}
    if status and status in _PENDING_STATUSES:
        query["status"] = status
    else:
        query["status"] = {"$in": _PENDING_STATUSES}

    apps = list(db[_APPLICATIONS].find(query, {"parcel_ref": 1, "_id": 0}))

    zone_data: Dict[str, Dict] = {}

    for app in apps:
        parcel = _parcel_lookup_by_ref(app.get("parcel_ref"))
        if not parcel:
            continue
        zid = parcel.get("zone_id")
        if not zid:
            continue
        if zone_id and zid != zone_id:
            continue

        if zid not in zone_data:
            zone_data[zid] = {"count": 0, "centroids": [], "parcel": parcel}
        zone_data[zid]["count"] += 1
        g = parcel.get("geometry")
        if _is_valid_polygon(g):
            c = _centroid_of_polygon(g)
            if c:
                zone_data[zid]["centroids"].append(c)

    if not zone_data:
        return _empty_collection()

    max_count = max(z["count"] for z in zone_data.values()) or 1
    features = []

    for zid, data in zone_data.items():
        centroids = data["centroids"]
        if not centroids:
            continue

        lon = round(sum(c[0] for c in centroids) / len(centroids), 6)
        lat = round(sum(c[1] for c in centroids) / len(centroids), 6)
        intensity = round(data["count"] / max_count, 4)

        features.append(_make_feature(
            geometry={"type": "Point", "coordinates": [lon, lat]},
            properties={
                "zone_id": zid,
                "count": data["count"],
                "intensity": intensity,
            },
        ))

    return {"type": "FeatureCollection", "features": features}


# ── Task 19 + 21: Disputed Parcels GeoFeed ───────────────────────────────────

def get_disputed_parcels_geofeed(
    zone_id: Optional[str] = None,
    dispute_state: Optional[str] = None,
) -> dict:
    """
    GeoJSON FeatureCollection of disputed parcels.
    Task 21: accepts optional zone_id, dispute_state filter params.
    """
    objected_app_ids = set(
        o["application_id"]
        for o in db[_OBJECTIONS].find({}, {"application_id": 1, "_id": 0})
        if o.get("application_id")
    )

    query = {
        "$or": [
            {"status": "under_objection"},
            {"application_id": {"$in": list(objected_app_ids)}},
            {"objection.has_objection": True},
        ]
    }
    apps = list(db[_APPLICATIONS].find(query, {"_id": 0}))

    features = []
    seen_parcel_refs = set()

    for app in apps:
        parcel_ref = app.get("parcel_ref")
        parcel_key = (
            parcel_ref.get("parcel_number")
            if isinstance(parcel_ref, dict)
            else str(parcel_ref) if parcel_ref else None
        )
        if parcel_key in seen_parcel_refs:
            continue
        seen_parcel_refs.add(parcel_key)

        parcel = _parcel_lookup_by_ref(parcel_ref)
        geometry = None
        if parcel:
            g = parcel.get("geometry")
            if _is_valid_polygon(g):
                geometry = g

        if geometry is None:
            continue

        app_zone_id = (
            parcel_ref.get("zone_id")
            if isinstance(parcel_ref, dict)
            else (parcel.get("zone_id") if parcel else None)
        )

        if zone_id and app_zone_id != zone_id:
            continue

        obj = db[_OBJECTIONS].find_one(
            {"application_id": app.get("application_id")},
            {"status": 1, "_id": 0},
        )
        objection_status = obj.get("status") if obj else None

        ds = "disputed"
        if dispute_state and ds != dispute_state:
            continue

        features.append(_make_feature(
            geometry=geometry,
            properties={
                "application_id": app.get("application_id"),
                "parcel_number": parcel_key,
                "zone_id": app_zone_id,
                "dispute_state": ds,
                "objection_status": objection_status,
            },
        ))

    return {"type": "FeatureCollection", "features": features}


# ── Task 20 + 21: Survey Tasks GeoFeed ───────────────────────────────────────

def get_survey_tasks_geofeed(
    zone_id: Optional[str] = None,
    status: Optional[str] = None,
) -> dict:
    """
    GeoJSON FeatureCollection of active survey tasks.
    Task 21: accepts optional zone_id, status filter params.
    """
    query: Dict[str, Any] = {}
    if status and status in _ACTIVE_TASK_STATUSES:
        query["status"] = status
    else:
        query["status"] = {"$in": _ACTIVE_TASK_STATUSES}

    tasks = list(db[_SURVEY_TASKS].find(query, {"_id": 0}))
    features = []

    for task in tasks:
        app_id = task.get("application_id")
        app = db[_APPLICATIONS].find_one({"application_id": app_id}, {"_id": 0}) or {}

        parcel = _parcel_lookup_by_ref(app.get("parcel_ref"))
        geometry = None
        if parcel:
            g = parcel.get("geometry")
            if _is_valid_polygon(g):
                geometry = g

        if geometry is None:
            continue

        parcel_ref = app.get("parcel_ref")
        task_zone_id = (
            parcel_ref.get("zone_id")
            if isinstance(parcel_ref, dict)
            else (parcel.get("zone_id") if parcel else None)
        )

        if zone_id and task_zone_id != zone_id:
            continue

        features.append(_make_feature(
            geometry=geometry,
            properties={
                "task_id": task.get("task_id"),
                "application_id": app_id,
                "task_status": task.get("status"),
                "assigned_surveyor_id": task.get("assigned_surveyor_id"),
                "zone": task_zone_id,
                "priority": task.get("priority") or app.get("priority"),
                "scheduled_visit_date": task.get("scheduled_visit_date"),
                "report_uploaded": task.get("report_uploaded", False),
            },
        ))

    return {"type": "FeatureCollection", "features": features}


# ── Task 22: Nearby parcels via $geoNear ─────────────────────────────────────

def get_nearby_parcels(lng: float, lat: float, max_distance: int = 1000) -> dict:
    """
    Return parcels within max_distance metres of (lng, lat) using $geoNear.
    Requires a 2dsphere index on parcels.geometry (created by seed_data.py).
    NOTE: $geoNear is NOT supported by mongomock — when running under mongomock
    or without the 2dsphere index, returns an empty FeatureCollection with an
    'error' key explaining the limitation instead of raising an exception.
    """
    try:
        pipeline = [
            {
                "$geoNear": {
                    "near": {"type": "Point", "coordinates": [lng, lat]},
                    "distanceField": "distance_meters",
                    "maxDistance": max_distance,
                    "spherical": True,
                }
            }
        ]
        results = list(db[_PARCELS].aggregate(pipeline))
        features = []
        for p in results:
            p.pop("_id", None)
            geometry = p.get("geometry")
            if not _is_valid_polygon(geometry):
                continue
            features.append(_make_feature(
                geometry=geometry,
                properties={
                    "parcel_id": p.get("parcel_code") or p.get("parcel_number"),
                    "parcel_number": p.get("parcel_number"),
                    "zone_id": p.get("zone_id"),
                    "distance_meters": round(p.get("distance_meters", 0), 1),
                },
            ))
        return {"type": "FeatureCollection", "features": features}
    except Exception as exc:
        return {
            "type": "FeatureCollection",
            "features": [],
            "error": str(exc),
            "note": "$geoNear requires a real MongoDB instance with 2dsphere index on parcels.geometry",
        }
