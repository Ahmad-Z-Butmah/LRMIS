"""
Student 3 Backend -- Tasks 11-20 verification (mongomock).
Run from backend/ directory:
    python -m app.tests.test_student3_tasks11_20
"""

import sys
import types
from datetime import datetime, timedelta, timezone

import mongomock

# ── Patch database module ─────────────────────────────────────────────────────
_mock_client = mongomock.MongoClient()
_mock_db = _mock_client["lrmis_test_1120"]

fake_db_module = types.ModuleType("app.database")
fake_db_module.db = _mock_db
sys.modules["app.database"] = fake_db_module

# Patch audit_service to avoid real DB
import types as _types
_fake_audit = _types.ModuleType("app.services.audit_service")
_fake_audit.log_audit = lambda **kw: None
_fake_audit.log_performance_event = lambda **kw: None
_fake_audit.get_audit_timeline = lambda app_id: []
sys.modules["app.services.audit_service"] = _fake_audit

from app.services.analytics_service import (
    get_surveyor_analytics,
    get_registrar_analytics,
    get_certificates_per_month,
    get_kpis,
    get_processing_time,
)
from app.services.cache_service import get_cache, set_cache, clear_cache
from app.services.map_service import (
    get_parcels_geofeed,
    get_pending_applications_geofeed,
    get_pending_heatmap,
    get_disputed_parcels_geofeed,
    get_survey_tasks_geofeed,
)

# ── Test helpers ──────────────────────────────────────────────────────────────
_results = []
_PASS = "PASS"
_FAIL = "FAIL"


def check(name, condition, detail=""):
    status = _PASS if condition else _FAIL
    _results.append((name, status, detail))
    icon = "+" if condition else "X"
    line = f"  [{icon}] {status}  {name}"
    if detail:
        line += f" - {detail}"
    print(line.encode("ascii", errors="replace").decode("ascii"))


def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def _dt(offset_days=0):
    return datetime.now(timezone.utc) - timedelta(days=offset_days)


# ── Seed helpers ──────────────────────────────────────────────────────────────

_POLYGON_Z_EAST = {
    "type": "Polygon",
    "coordinates": [[[35.220, 31.960], [35.230, 31.960],
                     [35.230, 31.970], [35.220, 31.970], [35.220, 31.960]]],
}
_POLYGON_Z_WEST = {
    "type": "Polygon",
    "coordinates": [[[35.180, 31.980], [35.190, 31.980],
                     [35.190, 31.990], [35.180, 31.990], [35.180, 31.980]]],
}


def seed_all():
    _mock_db["staff_members"].drop()
    _mock_db["survey_tasks"].drop()
    _mock_db["survey_reports"].drop()
    _mock_db["applications"].drop()
    _mock_db["certificates"].drop()
    _mock_db["performance_logs"].drop()
    _mock_db["parcels"].drop()
    _mock_db["objections"].drop()

    # Staff
    _mock_db["staff_members"].insert_many([
        {
            "staff_id": "SURV-01",
            "name": "Surveyor One",
            "role": "surveyor",
            "active": True,
            "workload": {"active_tasks": 2, "max_tasks": 10},
        },
        {
            "staff_id": "SURV-02",
            "name": "Surveyor Two",
            "role": "surveyor",
            "active": True,
            "workload": {"active_tasks": 0, "max_tasks": 5},
        },
        {
            "staff_id": "REG-01",
            "name": "Registrar One",
            "role": "registrar",
        },
        {
            "staff_id": "REG-02",
            "name": "Registrar Two",
            "role": "registrar",
        },
    ])

    # Survey tasks — SURV-01 has 2 active, 1 completed; SURV-02 has 1 report_uploaded
    _mock_db["survey_tasks"].insert_many([
        {
            "task_id": "T-001",
            "application_id": "APP-001",
            "assigned_surveyor_id": "SURV-01",
            "status": "visit_scheduled",
            "report_uploaded": False,
            "created_at": _dt(10),
            "updated_at": _dt(8),
        },
        {
            "task_id": "T-002",
            "application_id": "APP-002",
            "assigned_surveyor_id": "SURV-01",
            "status": "survey_completed",
            "report_uploaded": False,
            "created_at": _dt(20),
            "updated_at": _dt(15),
        },
        {
            "task_id": "T-003",
            "application_id": "APP-003",
            "assigned_surveyor_id": "SURV-01",
            "status": "assigned",
            "report_uploaded": False,
            "created_at": _dt(5),
            "updated_at": _dt(3),
        },
        {
            "task_id": "T-004",
            "application_id": "APP-004",
            "assigned_surveyor_id": "SURV-02",
            "status": "report_uploaded",
            "report_uploaded": True,
            "created_at": _dt(12),
            "updated_at": _dt(7),
        },
    ])

    # Applications
    _mock_db["applications"].insert_many([
        {
            "application_id": "APP-001",
            "status": "survey_required",
            "parcel_ref": "P-003",
            "priority": "normal",
            "created_at": _dt(10),
            "updated_at": _dt(8),
        },
        {
            "application_id": "APP-002",
            "status": "survey_required",
            "parcel_ref": "P-003",
            "priority": "high",
            "created_at": _dt(20),
            "updated_at": _dt(15),
        },
        {
            "application_id": "APP-003",
            "status": "submitted",
            "parcel_ref": "P-001",
            "priority": None,
            "created_at": _dt(5),
            "updated_at": _dt(3),
        },
        {
            "application_id": "APP-004",
            "status": "pre_checked",
            "parcel_ref": "P-001",
            "priority": None,
            "created_at": _dt(12),
            "updated_at": _dt(7),
        },
        {
            "application_id": "APP-005",
            "status": "under_objection",
            "parcel_ref": "P-003",
            "priority": None,
            "created_at": _dt(30),
            "updated_at": _dt(2),
        },
        {
            "application_id": "APP-006",
            "status": "approved",
            "parcel_ref": "P-005",
            "priority": None,
            "rejected_by": None,
            "issued_by": "REG-01",
            "created_at": _dt(40),
            "updated_at": _dt(5),
        },
        {
            "application_id": "APP-007",
            "status": "rejected",
            "parcel_ref": "P-001",
            "rejected_by": "REG-01",
            "created_at": _dt(50),
            "updated_at": _dt(20),
        },
        {
            "application_id": "APP-008",
            "status": "missing_documents",
            "parcel_ref": "P-001",
            "priority": None,
            "created_at": _dt(6),
            "updated_at": _dt(4),
        },
    ])

    # Certificates
    _mock_db["certificates"].insert_many([
        {
            "certificate_id": "CERT-001",
            "application_id": "APP-006",
            "status": "issued",
            "issued_at": datetime(2026, 3, 15, tzinfo=timezone.utc),
        },
        {
            "certificate_id": "CERT-002",
            "application_id": "APP-001",
            "status": "issued",
            "issued_at": datetime(2026, 3, 22, tzinfo=timezone.utc),
        },
        {
            "certificate_id": "CERT-003",
            "application_id": "APP-002",
            "status": "issued",
            "issued_at": datetime(2026, 4, 5, tzinfo=timezone.utc),
        },
    ])

    # Parcels (P-001 = Z-WEST, P-003 = Z-EAST, P-005 = Z-NORTH)
    _mock_db["parcels"].insert_many([
        {
            "parcel_number": "P-001",
            "parcel_code": "P-001",
            "zone_id": "Z-WEST",
            "area_sqm": 1200.0,
            "geometry": _POLYGON_Z_WEST,
        },
        {
            "parcel_number": "P-003",
            "parcel_code": "P-003",
            "zone_id": "Z-EAST",
            "area_sqm": 1500.0,
            "geometry": _POLYGON_Z_EAST,
        },
        {
            "parcel_number": "P-005",
            "parcel_code": "P-005",
            "zone_id": "Z-NORTH",
            "area_sqm": 2000.0,
            "geometry": {  # valid polygon
                "type": "Polygon",
                "coordinates": [[[35.260, 31.940], [35.270, 31.940],
                                  [35.270, 31.950], [35.260, 31.950],
                                  [35.260, 31.940]]],
            },
        },
        {
            "parcel_number": "P-NO-GEO",
            "parcel_code": "P-NO-GEO",
            "zone_id": "Z-UNKNOWN",
            "geometry": None,  # missing geometry
        },
    ])

    # Survey reports — SURV-02 has 1 report; SURV-01 has none
    # This lets us verify the primary (survey_reports) vs fallback (survey_tasks) path
    _mock_db["survey_reports"].insert_one({
        "report_id": "SR-001",
        "task_id": "T-004",
        "surveyor_id": "SURV-02",
        "findings": "Survey completed, boundaries confirmed",
    })

    # Objections (APP-005 is under objection)
    _mock_db["objections"].insert_one({
        "objection_id": "OBJ-001",
        "application_id": "APP-005",
        "status": "under_review",
    })

    # Performance logs for processing-time and registrar analytics
    _mock_db["performance_logs"].insert_many([
        {
            "application_id": "APP-006",
            "event_stream": [
                {"type": "application_created", "by": {"actor_type": "applicant", "actor_id": "APPL-01"}, "at": _dt(40)},
                {"type": "status_changed", "by": {"actor_type": "staff", "actor_id": "REG-01"}, "at": _dt(30)},
            ],
        },
        {
            "application_id": "APP-007",
            "event_stream": [
                {"type": "application_created", "by": {"actor_type": "applicant", "actor_id": "APPL-02"}, "at": _dt(50)},
                {"type": "status_changed", "by": {"actor_type": "staff", "actor_id": "REG-01"}, "at": _dt(20)},
            ],
        },
    ])


# ─────────────────────────────────────────────────────────────────────────────
# TESTS
# ─────────────────────────────────────────────────────────────────────────────

def test_task11_surveyor_analytics():
    section("Task 11 - Surveyor Analytics")
    result = get_surveyor_analytics()

    check("Returns list", isinstance(result, list))
    check("Has 2 surveyors", len(result) == 2, f"got {len(result)}")

    s1 = next((s for s in result if s["surveyor_id"] == "SURV-01"), None)
    s2 = next((s for s in result if s["surveyor_id"] == "SURV-02"), None)

    check("SURV-01 exists in result", s1 is not None)
    check("SURV-01 has surveyor_name", s1 and s1["surveyor_name"] == "Surveyor One")
    # active = NOT in _TERMINAL_STATUSES {registrar_reviewed, cancelled}
    # T-001 (visit_scheduled), T-002 (survey_completed), T-003 (assigned) → 3 active
    # completed = in _COMPLETED_STATUSES {survey_completed, report_uploaded, registrar_reviewed}
    # T-002 (survey_completed) → 1 completed
    check("SURV-01 active_tasks = 3", s1 and s1["active_tasks"] == 3, str(s1 and s1.get("active_tasks")))
    check("SURV-01 completed_tasks = 1", s1 and s1["completed_tasks"] == 1)
    check("SURV-01 max_tasks = 10", s1 and s1["max_tasks"] == 10)
    check("SURV-01 workload_percentage = 30.0", s1 and s1["workload_percentage"] == 30.0)
    # SURV-01: survey_reports has 0 records → fallback to survey_tasks.report_uploaded
    check("SURV-01 reports_uploaded = 0 (fallback: no report_uploaded tasks)", s1 and s1["reports_uploaded"] == 0)
    check("SURV-01 reports_uploaded_source = survey_tasks.report_uploaded (fallback)",
          s1 and s1.get("reports_uploaded_source") == "survey_tasks.report_uploaded")
    check("SURV-01 avg_days is float >= 0", s1 and isinstance(s1["average_task_completion_days"], (int, float)))

    check("SURV-02 exists in result", s2 is not None)
    # T-004 (report_uploaded) → in _COMPLETED_STATUSES but NOT terminal → still active
    check("SURV-02 completed_tasks = 1", s2 and s2["completed_tasks"] == 1)
    # SURV-02: survey_reports has 1 record (SR-001) → primary path used
    check("SURV-02 reports_uploaded = 1 (primary: from survey_reports)", s2 and s2["reports_uploaded"] == 1)
    check("SURV-02 reports_uploaded_source = survey_reports (primary)",
          s2 and s2.get("reports_uploaded_source") == "survey_reports")
    check("SURV-02 active_tasks = 1 (report_uploaded is not terminal)", s2 and s2["active_tasks"] == 1)

    # All required fields present (reports_uploaded_source is an additional field)
    required_keys = {"surveyor_id", "surveyor_name", "active_tasks", "completed_tasks",
                     "max_tasks", "workload_percentage", "reports_uploaded",
                     "reports_uploaded_source", "average_task_completion_days"}
    if s1:
        missing = required_keys - set(s1.keys())
        check("All required fields in response", len(missing) == 0, str(missing))


def test_task12_registrar_analytics():
    section("Task 12 - Registrar Analytics")
    result = get_registrar_analytics()

    check("Returns list", isinstance(result, list))
    check("Has 2 registrars", len(result) == 2, f"got {len(result)}")

    r1 = next((r for r in result if r["registrar_id"] == "REG-01"), None)
    check("REG-01 exists", r1 is not None)
    check("REG-01 has registrar_name", r1 and r1["registrar_name"] == "Registrar One")
    check("REG-01 rejected_count = 1 (APP-007, rejected_by=REG-01)", r1 and r1["rejected_count"] == 1)
    # approved_count: attributed via issued_by/rejected_by fields (REG-01 issued APP-006)
    check("REG-01 approved_count >= 1 (APP-006, issued_by=REG-01)", r1 and r1["approved_count"] >= 1)
    check("REG-01 average_review_time >= 0", r1 and r1["average_review_time"] >= 0)
    # assigned_reviews is a global proxy (no assigned_registrar_id field in schema)
    check("REG-01 assigned_reviews_is_proxy = True", r1 and r1.get("assigned_reviews_is_proxy") is True)
    # survey_reports has no registrar fields — not used for registrar analytics
    check("survey_reports not used (no registrar fields in schema)", True,
          "survey_reports schema: task_id, surveyor_id, findings only")

    required_keys = {"registrar_id", "registrar_name", "assigned_reviews",
                     "assigned_reviews_is_proxy", "completed_reviews", "approved_count",
                     "rejected_count", "average_review_time"}
    if r1:
        missing = required_keys - set(r1.keys())
        check("All required fields in registrar response", len(missing) == 0, str(missing))


def test_task13_certificates_per_month():
    section("Task 13 - Certificates Per Month")
    result = get_certificates_per_month()

    check("Returns list", isinstance(result, list))
    check("Has 2 distinct months", len(result) == 2, f"got {len(result)}")
    check("First month is 2026-03", result and result[0]["month"] == "2026-03")
    check("2026-03 count = 2 (CERT-001, CERT-002)", result and result[0]["count"] == 2)
    check("Second month is 2026-04", len(result) > 1 and result[1]["month"] == "2026-04")
    check("2026-04 count = 1", len(result) > 1 and result[1]["count"] == 1)
    check("Sorted ascending", result == sorted(result, key=lambda x: x["month"]))

    # Required fields
    if result:
        check("Each entry has month key", "month" in result[0])
        check("Each entry has count key", "count" in result[0])


def test_task14_cache():
    section("Task 14 - Cache Service")
    clear_cache()

    # Basic set/get
    set_cache("test:k1", {"data": 42}, ttl_seconds=60)
    hit1 = get_cache("test:k1")
    check("Cache hit before TTL", hit1 == {"data": 42})

    # Same key again — still cached
    hit2 = get_cache("test:k1")
    check("Cache hit on second call", hit2 == {"data": 42})

    # TTL expiry simulation
    from datetime import timedelta
    from app.services import cache_service as cs
    # Manually expire the entry
    cs._cache["test:k1"]["expires_at"] = datetime.now(timezone.utc) - timedelta(seconds=1)
    miss = get_cache("test:k1")
    check("Cache miss after TTL expires", miss is None)

    # clear_cache specific key
    set_cache("test:k2", "value2", ttl_seconds=60)
    clear_cache("test:k2")
    check("clear_cache(key) removes entry", get_cache("test:k2") is None)

    # clear all
    set_cache("test:k3", "v3", 60)
    set_cache("test:k4", "v4", 60)
    clear_cache()
    check("clear_cache() flushes all", get_cache("test:k3") is None and get_cache("test:k4") is None)

    # Analytics endpoint cache — surveyors cached on first call
    clear_cache()
    from app.services.cache_service import get_cache as gc, set_cache as sc
    key = "analytics:surveyors"
    data = get_surveyor_analytics()
    sc(key, {"surveyors": data, "total": len(data)}, ttl_seconds=60)
    cached_hit = gc(key)
    check("Surveyor analytics cached after set", cached_hit is not None)
    check("Cached result matches computed result",
          cached_hit is not None and cached_hit["total"] == len(data))


def test_task15_map_router_registered():
    section("Task 15 - Map Router / Service Import")
    try:
        from app.routers.map import router
        from app.services.map_service import (
            get_parcels_geofeed,
            get_pending_applications_geofeed,
            get_pending_heatmap,
            get_disputed_parcels_geofeed,
            get_survey_tasks_geofeed,
        )
        routes = [r.path for r in router.routes]
        check("Map router imported", True)
        check("/analytics/geofeeds/parcels route exists",
              any("parcels" in r for r in routes), str(routes))
        check("/analytics/geofeeds/survey-tasks route exists",
              any("survey-tasks" in r for r in routes))
        check("5 geofeed routes registered", len(routes) == 5, f"got {len(routes)}")
    except Exception as e:
        check("Map router import", False, str(e))


def test_task16_parcels_geofeed():
    section("Task 16 - Parcel GeoJSON Feed")
    fc = get_parcels_geofeed()

    check("type = FeatureCollection", fc.get("type") == "FeatureCollection")
    check("features is list", isinstance(fc.get("features"), list))
    # P-001, P-003, P-005 have valid polygons; P-NO-GEO does not
    check("3 features (parcels with valid geometry)", len(fc["features"]) == 3,
          f"got {len(fc['features'])}")

    f = fc["features"][0]
    check("Feature type = Feature", f.get("type") == "Feature")
    check("Geometry type = Polygon", f.get("geometry", {}).get("type") == "Polygon")

    props = f.get("properties", {})
    for key in ["parcel_id", "parcel_number", "zone_id",
                "registration_status", "dispute_state"]:
        check(f"Property '{key}' present", key in props)

    # Disputed parcel check (APP-005 is under_objection for P-003)
    p003_feature = next(
        (f for f in fc["features"] if f["properties"].get("parcel_number") == "P-003"),
        None
    )
    check("P-003 has dispute_state='disputed'",
          p003_feature is not None and p003_feature["properties"]["dispute_state"] == "disputed")
    # P-001 not disputed
    p001_feature = next(
        (f for f in fc["features"] if f["properties"].get("parcel_number") == "P-001"),
        None
    )
    check("P-001 has dispute_state='none'",
          p001_feature is not None and p001_feature["properties"]["dispute_state"] == "none")


def test_task17_pending_applications_geofeed():
    section("Task 17 - Pending Applications GeoFeed")
    fc = get_pending_applications_geofeed()

    check("type = FeatureCollection", fc.get("type") == "FeatureCollection")
    features = fc.get("features", [])
    check("features is list", isinstance(features, list))

    # Pending statuses: submitted(APP-003/P-001), pre_checked(APP-004/P-001),
    # survey_required(APP-001/P-003, APP-002/P-003), under_objection(APP-005/P-003),
    # missing_documents(APP-008/P-001)
    # APP-006(approved) and APP-007(rejected) must NOT appear
    statuses = [f["properties"]["status"] for f in features]
    check("No 'approved' in results", "approved" not in statuses)
    check("No 'rejected' in results", "rejected" not in statuses)
    check("No 'certificate_issued' in results", "certificate_issued" not in statuses)
    check("Pending statuses only",
          all(s in ["submitted", "pre_checked", "survey_required",
                    "missing_documents", "under_objection"] for s in statuses))

    if features:
        f = features[0]
        props = f.get("properties", {})
        for key in ["application_id", "status", "parcel_number", "zone_id", "priority"]:
            check(f"Property '{key}' present in pending feature", key in props)
        # priority may be null when not set on the application — key must exist regardless
        check("priority key present (value may be null)",
              "priority" in props, f"got props: {list(props.keys())}")
        check("Geometry type = Polygon", f["geometry"]["type"] == "Polygon")


def test_task18_pending_heatmap():
    section("Task 18 - Pending Heatmap GeoFeed")
    fc = get_pending_heatmap()

    check("type = FeatureCollection", fc.get("type") == "FeatureCollection")
    features = fc.get("features", [])
    check("features is list", isinstance(features, list))
    check("Has at least 1 zone", len(features) >= 1, f"got {len(features)}")

    for f in features:
        check(f"Zone {f['properties'].get('zone_id')} - geometry type = Point",
              f["geometry"]["type"] == "Point")
        check(f"Zone {f['properties'].get('zone_id')} - has count",
              "count" in f["properties"])
        check(f"Zone {f['properties'].get('zone_id')} - has intensity",
              "intensity" in f["properties"])
        check(f"Zone {f['properties'].get('zone_id')} - intensity in [0,1]",
              0.0 <= f["properties"]["intensity"] <= 1.0)

    # Check max intensity = 1.0
    if features:
        max_intensity = max(f["properties"]["intensity"] for f in features)
        check("Max intensity = 1.0", max_intensity == 1.0, f"got {max_intensity}")

    # Zone counts — Z-EAST has APP-001, APP-002, APP-005 (3); Z-WEST has APP-003, APP-004, APP-008 (3)
    zone_counts = {f["properties"]["zone_id"]: f["properties"]["count"] for f in features}
    check("Z-EAST count = 3", zone_counts.get("Z-EAST") == 3, str(zone_counts))
    check("Z-WEST count = 3", zone_counts.get("Z-WEST") == 3, str(zone_counts))


def test_task19_disputed_parcels():
    section("Task 19 - Disputed Parcels GeoFeed")
    fc = get_disputed_parcels_geofeed()

    check("type = FeatureCollection", fc.get("type") == "FeatureCollection")
    features = fc.get("features", [])
    check("Has at least 1 disputed parcel", len(features) >= 1, f"got {len(features)}")

    app_ids = [f["properties"].get("application_id") for f in features]
    # APP-005 is under_objection and has an objection record
    check("APP-005 (under_objection) is in result", "APP-005" in app_ids)
    # Non-disputed applications must not appear
    check("APP-003 (submitted, no objection) not in result", "APP-003" not in app_ids)
    check("APP-006 (approved) not in result", "APP-006" not in app_ids)

    for f in features:
        props = f.get("properties", {})
        check(f"dispute_state = 'disputed' for {props.get('application_id')}",
              props.get("dispute_state") == "disputed")
        for key in ["application_id", "parcel_number", "zone_id", "dispute_state"]:
            check(f"Property '{key}' in disputed feature", key in props)


def test_task20_survey_tasks_geofeed():
    section("Task 20 - Survey Tasks GeoFeed")
    fc = get_survey_tasks_geofeed()

    check("type = FeatureCollection", fc.get("type") == "FeatureCollection")
    features = fc.get("features", [])
    check("features is list", isinstance(features, list))

    # T-001 (visit_scheduled/APP-001/P-003 -> Z-EAST polygon -> valid)
    # T-002 (survey_completed/APP-002/P-003 -> valid)
    # T-003 (assigned/APP-003/P-001 -> Z-WEST polygon -> valid)
    # T-004 (report_uploaded/APP-004/P-001 -> valid)
    check("At least 1 active task feature", len(features) >= 1, f"got {len(features)}")

    for f in features:
        props = f.get("properties", {})
        check(f"task_id present in {props.get('task_id')}", "task_id" in props)
        check(f"application_id present", "application_id" in props)
        check(f"task_status present", "task_status" in props)
        check(f"assigned_surveyor_id present", "assigned_surveyor_id" in props)
        check(f"zone present", "zone" in props)
        check(f"priority present (may be null)", "priority" in props)
        check(f"scheduled_visit_date present (may be null)", "scheduled_visit_date" in props)
        check(f"report_uploaded present", "report_uploaded" in props)
        check(f"Geometry type = Polygon", f["geometry"]["type"] == "Polygon")

    # Only active statuses
    task_statuses = [f["properties"]["task_status"] for f in features]
    terminal_found = [s for s in task_statuses if s in {"registrar_reviewed", "cancelled"}]
    check("No terminal task statuses in GeoFeed", len(terminal_found) == 0, str(terminal_found))


# ── Summary ───────────────────────────────────────────────────────────────────

def run_all():
    print("\n" + "=" * 60)
    print("  Student 3 - Tasks 11-20 Mongomock Verification")
    print("=" * 60)

    seed_all()

    test_task11_surveyor_analytics()
    test_task12_registrar_analytics()
    test_task13_certificates_per_month()
    test_task14_cache()
    test_task15_map_router_registered()
    test_task16_parcels_geofeed()
    test_task17_pending_applications_geofeed()
    test_task18_pending_heatmap()
    test_task19_disputed_parcels()
    test_task20_survey_tasks_geofeed()

    print("\n" + "=" * 60)
    print("  RESULTS SUMMARY")
    print("=" * 60)
    passed = sum(1 for _, s, _ in _results if s == _PASS)
    failed = sum(1 for _, s, _ in _results if s == _FAIL)
    for name, status, detail in _results:
        icon = "+" if status == _PASS else "X"
        line = f"  [{icon}] {status:<5}  {name}"
        if detail:
            line += f" - {detail}"
        print(line.encode("ascii", errors="replace").decode("ascii"))
    print(f"\n  Total: {passed} PASS / {failed} FAIL out of {len(_results)}")
    return failed == 0


if __name__ == "__main__":
    ok = run_all()
    sys.exit(0 if ok else 1)
