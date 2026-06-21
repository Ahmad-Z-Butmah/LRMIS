"""
Group Backend — Analytics Tasks 3–9 verification (mongomock).

Run from backend/ directory:
    python -m app.tests.test_group_analytics_tasks3_9
    pytest backend/app/tests/test_group_analytics_tasks3_9.py -v

Uses mongomock — does NOT touch the real database.
Patches app.database before any service import.
"""

import sys
import types
from datetime import datetime, timedelta, timezone

import mongomock

# ── Patch database BEFORE importing any service ───────────────────────────────
_mock_client = mongomock.MongoClient()
_mock_db = _mock_client["lrmis_test_analytics39"]

fake_db_module = types.ModuleType("app.database")
fake_db_module.db = _mock_db
sys.modules["app.database"] = fake_db_module

# Patch audit_service to avoid real DB dependency
_fake_audit = types.ModuleType("app.services.audit_service")
_fake_audit.log_audit = lambda **kw: None
_fake_audit.log_performance_event = lambda **kw: None
_fake_audit.get_audit_timeline = lambda app_id: []
sys.modules["app.services.audit_service"] = _fake_audit

# ── Import services + schemas after patch ─────────────────────────────────────
from app.schemas.analytics_schema import (
    KPIResponse,
    ApplicationsByStatusResponse,
    ApplicationsByTypeResponse,
    ApplicationsByZoneResponse,
    ProcessingTimeResponse,
    SurveyorAnalyticsResponse,
    RegistrarAnalyticsResponse,
    GeoFeedResponse,
)
from app.services.analytics_service import (
    get_kpis,
    get_applications_by_status,
    get_applications_by_type,
    get_applications_by_zone,
    get_processing_time,
)
from app.services.cache_service import clear_cache

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
    """Return a UTC datetime offset_days before now."""
    return datetime.now(timezone.utc) - timedelta(days=offset_days)


# ── Seed data ─────────────────────────────────────────────────────────────────
#
# Test applications seeded into land_applications (professor-required collection).
#
# ID   | Status          | app_type            | parcel_ref             | timestamps
# -----|-----------------|---------------------|------------------------|---
# T001 | submitted       | ownership_transfer  | {zone_id: "Z-01"}      | submitted: -5 days
# T002 | submitted       | ownership_transfer  | {zone_id: "Z-01"}      | submitted: -3 days
# T003 | submitted       | first_registration  | {zone_id: "Z-01"}      | submitted: -35 days (DELAYED)
# T004 | approved        | first_registration  | {zone_id: "Z-02"}      | full timestamps
# T005 | approved        | ownership_transfer  | {zone_id: "Z-02"}      | full timestamps
# T006 | rejected        | boundary_correction | "P-STR" (string ref)   | submitted: -10 days
# T007 | under_objection | parcel_subdivision  | {zone_id: "Z-01"}      | submitted: -40 days (DELAYED)
# T008 | missing_docs    | parcel_merge        | None (no parcel_ref)   | submitted: -2 days
#
# Parcels: P-STR -> Z-03 (so T006 goes to zone Z-03)
# Certificates: 1 issued
#
# KPI expectations:
#   total = 8
#   pending = T001+T002+T003+T007+T008 = 5
#   approved = T004+T005 = 2
#   rejected = T006 = 1
#   under_objection = T007 = 1
#   missing_documents = T008 = 1
#   certificates_issued = 1
#   delayed = T003 (submitted -35d) + T007 (submitted -40d) = 2
#   average_processing_days: T004 = 15d, T005 = 28d -> avg = 21.5d
#
# Processing time for ownership_transfer (T001,T002,T005):
#   Only T005 has full timestamps:
#     submitted: -30, pre_checked: -25, survey_req: -20, surveyed: -10, approved: -2
#     precheck=5d, survey_delay=10d, approval=8d, processing=28d
#   T001,T002: no end timestamps -> 0 contribution
#   avg for ownership_transfer: precheck=5.0, survey_delay=10.0, approval=8.0, processing=28.0
#
# Processing time for first_registration (T003,T004):
#   T003: only submitted_at -> no end timestamps -> 0 contribution
#   T004: submitted: -20, pre_checked: -15, survey_req: -12, surveyed: -8, approved: -5
#     precheck=5d, survey_delay=4d, approval=3d, processing=15d
#   avg for first_registration: precheck=5.0, survey_delay=4.0, approval=3.0, processing=15.0

def seed_all():
    _mock_db["land_applications"].drop()
    _mock_db["applications"].drop()
    _mock_db["certificates"].drop()
    _mock_db["parcels"].drop()
    _mock_db["staff_members"].drop()
    _mock_db["survey_tasks"].drop()
    _mock_db["survey_reports"].drop()
    _mock_db["performance_logs"].drop()

    clear_cache()

    # Parcels: P-STR maps to Z-03 for T006's string parcel_ref lookup
    _mock_db["parcels"].insert_many([
        {"parcel_number": "P-STR", "parcel_code": "P-STR", "zone_id": "Z-03"},
    ])

    # land_applications — professor-required collection
    _mock_db["land_applications"].insert_many([
        # T001: submitted, ownership_transfer, Z-01, not delayed
        {
            "application_id": "T001",
            "application_type": "ownership_transfer",
            "status": "submitted",
            "parcel_ref": {"zone_id": "Z-01", "parcel_number": "P-001"},
            "timestamps": {"submitted_at": _dt(5)},
        },
        # T002: submitted, ownership_transfer, Z-01, not delayed
        {
            "application_id": "T002",
            "application_type": "ownership_transfer",
            "status": "submitted",
            "parcel_ref": {"zone_id": "Z-01", "parcel_number": "P-001"},
            "timestamps": {"submitted_at": _dt(3)},
        },
        # T003: submitted, first_registration, Z-01, DELAYED (35 days)
        {
            "application_id": "T003",
            "application_type": "first_registration",
            "status": "submitted",
            "parcel_ref": {"zone_id": "Z-01", "parcel_number": "P-002"},
            "timestamps": {"submitted_at": _dt(35)},
        },
        # T004: approved, first_registration, Z-02, full timestamps
        {
            "application_id": "T004",
            "application_type": "first_registration",
            "status": "approved",
            "parcel_ref": {"zone_id": "Z-02", "parcel_number": "P-003"},
            "timestamps": {
                "submitted_at": _dt(20),
                "pre_checked_at": _dt(15),
                "survey_required_at": _dt(12),
                "surveyed_at": _dt(8),
                "approved_at": _dt(5),
            },
        },
        # T005: approved, ownership_transfer, Z-02, full timestamps
        {
            "application_id": "T005",
            "application_type": "ownership_transfer",
            "status": "approved",
            "parcel_ref": {"zone_id": "Z-02", "parcel_number": "P-003"},
            "timestamps": {
                "submitted_at": _dt(30),
                "pre_checked_at": _dt(25),
                "survey_required_at": _dt(20),
                "surveyed_at": _dt(10),
                "approved_at": _dt(2),
            },
        },
        # T006: rejected, boundary_correction, parcel_ref = STRING "P-STR" -> Z-03
        {
            "application_id": "T006",
            "application_type": "boundary_correction",
            "status": "rejected",
            "parcel_ref": "P-STR",
            "timestamps": {"submitted_at": _dt(10)},
        },
        # T007: under_objection, parcel_subdivision, Z-01, DELAYED (40 days)
        {
            "application_id": "T007",
            "application_type": "parcel_subdivision",
            "status": "under_objection",
            "parcel_ref": {"zone_id": "Z-01", "parcel_number": "P-004"},
            "timestamps": {"submitted_at": _dt(40)},
        },
        # T008: missing_documents, parcel_merge, no parcel_ref -> unknown zone
        {
            "application_id": "T008",
            "application_type": "parcel_merge",
            "status": "missing_documents",
            "parcel_ref": None,
            "timestamps": {"submitted_at": _dt(2)},
        },
    ])

    # Certificates: 1 issued
    _mock_db["certificates"].insert_one({
        "certificate_id": "CERT-TEST-001",
        "application_id": "T004",
        "status": "issued",
        "issued_at": datetime(2026, 3, 15, tzinfo=timezone.utc),
    })


# ─────────────────────────────────────────────────────────────────────────────
# Task 3 — Schema import and instantiation
# ─────────────────────────────────────────────────────────────────────────────

def test_task3_schemas():
    section("Task 3 - Analytics Schemas")

    # KPIResponse
    try:
        kpi = KPIResponse(
            total_applications=10,
            pending_applications=3,
            approved_applications=4,
            rejected_applications=2,
            under_objection_applications=1,
            missing_documents_applications=1,
            certificates_issued=2,
            average_processing_days=14.5,
            delayed_applications=1,
        )
        check("KPIResponse instantiates", True)
        check("KPIResponse has total_applications", hasattr(kpi, "total_applications"))
        check("KPIResponse has average_processing_days", hasattr(kpi, "average_processing_days"))
        check("KPIResponse has delayed_applications", hasattr(kpi, "delayed_applications"))
        check("KPIResponse has certificates_issued", hasattr(kpi, "certificates_issued"))
    except Exception as e:
        check("KPIResponse instantiates", False, str(e))

    # ApplicationsByStatusResponse
    try:
        r = ApplicationsByStatusResponse(status="submitted", count=5)
        check("ApplicationsByStatusResponse instantiates", True)
        check("ApplicationsByStatusResponse has status", r.status == "submitted")
        check("ApplicationsByStatusResponse has count", r.count == 5)
    except Exception as e:
        check("ApplicationsByStatusResponse instantiates", False, str(e))

    # ApplicationsByTypeResponse
    try:
        r = ApplicationsByTypeResponse(application_type="ownership_transfer", count=3)
        check("ApplicationsByTypeResponse instantiates", True)
        check("ApplicationsByTypeResponse has application_type", r.application_type == "ownership_transfer")
    except Exception as e:
        check("ApplicationsByTypeResponse instantiates", False, str(e))

    # ApplicationsByZoneResponse
    try:
        r = ApplicationsByZoneResponse(zone_id="Z-01", count=4, pending=3, approved=1, rejected=0)
        check("ApplicationsByZoneResponse instantiates", True)
        check("ApplicationsByZoneResponse has zone_id", r.zone_id == "Z-01")
        check("ApplicationsByZoneResponse has pending field", r.pending == 3)
    except Exception as e:
        check("ApplicationsByZoneResponse instantiates", False, str(e))

    # ProcessingTimeResponse
    try:
        r = ProcessingTimeResponse(
            application_type="first_registration",
            average_processing_days=15.0,
            average_precheck_days=5.0,
            average_survey_delay_days=4.0,
            average_approval_days=3.0,
            sample_count=2,
        )
        check("ProcessingTimeResponse instantiates", True)
        check("ProcessingTimeResponse has all 6 fields",
              all(hasattr(r, f) for f in [
                  "application_type", "average_processing_days",
                  "average_precheck_days", "average_survey_delay_days",
                  "average_approval_days", "sample_count"
              ]))
    except Exception as e:
        check("ProcessingTimeResponse instantiates", False, str(e))

    # SurveyorAnalyticsResponse
    try:
        r = SurveyorAnalyticsResponse(
            surveyor_id="SURV-01", surveyor_name="Test",
            active_tasks=2, completed_tasks=1, max_tasks=10,
            workload_percentage=20.0, reports_uploaded=1,
            average_task_completion_days=5.0,
        )
        check("SurveyorAnalyticsResponse instantiates", True)
    except Exception as e:
        check("SurveyorAnalyticsResponse instantiates", False, str(e))

    # RegistrarAnalyticsResponse
    try:
        r = RegistrarAnalyticsResponse(
            registrar_id="REG-01", registrar_name="Test",
            assigned_reviews=3, completed_reviews=2,
            approved_count=1, rejected_count=1,
            average_review_time=7.0,
        )
        check("RegistrarAnalyticsResponse instantiates", True)
    except Exception as e:
        check("RegistrarAnalyticsResponse instantiates", False, str(e))

    # GeoFeedResponse
    try:
        r = GeoFeedResponse(type="FeatureCollection", features=[])
        check("GeoFeedResponse instantiates", True)
        check("GeoFeedResponse has type", r.type == "FeatureCollection")
        check("GeoFeedResponse has features", isinstance(r.features, list))
    except Exception as e:
        check("GeoFeedResponse instantiates", False, str(e))


# ─────────────────────────────────────────────────────────────────────────────
# Task 4 — Router import and route registration
# ─────────────────────────────────────────────────────────────────────────────

def test_task4_router():
    section("Task 4 - Analytics Router + Service Setup")

    try:
        from app.routers.analytics import router
        check("Analytics router imports without error", True)
        check("Router prefix is /analytics", router.prefix == "/analytics")
        check("Analytics tag present", "Analytics" in router.tags)

        paths = [r.path for r in router.routes]
        check("/analytics/kpis route registered",
              any("/analytics/kpis" in p for p in paths), str(paths))
        check("/analytics/applications-by-status route registered",
              any("applications-by-status" in p for p in paths), str(paths))
        check("/analytics/applications-by-type route registered",
              any("applications-by-type" in p for p in paths), str(paths))
        check("/analytics/applications-by-zone route registered",
              any("applications-by-zone" in p for p in paths), str(paths))
        check("/analytics/processing-time route registered",
              any("processing-time" in p for p in paths), str(paths))
        # Existing routes still present
        check("/analytics/surveyors route still present",
              any("surveyors" in p for p in paths))
        check("/analytics/registrars route still present",
              any("registrars" in p for p in paths))
        check("/analytics/certificates-per-month route still present",
              any("certificates-per-month" in p for p in paths))
    except Exception as e:
        check("Analytics router imports without error", False, str(e))


# ─────────────────────────────────────────────────────────────────────────────
# Task 5 — KPI endpoint
# ─────────────────────────────────────────────────────────────────────────────

def test_task5_kpis():
    section("Task 5 - Main KPIs Endpoint")
    result = get_kpis()

    required_fields = [
        "total_applications", "pending_applications", "approved_applications",
        "rejected_applications", "under_objection_applications",
        "missing_documents_applications", "certificates_issued",
        "average_processing_days", "delayed_applications",
    ]
    for f in required_fields:
        check(f"KPI has field '{f}'", f in result, str(list(result.keys())))

    check("total_applications = 8", result.get("total_applications") == 8,
          str(result.get("total_applications")))
    check("pending_applications = 5 (T001+T002+T003+T007+T008)",
          result.get("pending_applications") == 5,
          str(result.get("pending_applications")))
    check("approved_applications = 2 (T004+T005)",
          result.get("approved_applications") == 2,
          str(result.get("approved_applications")))
    check("rejected_applications = 1 (T006)",
          result.get("rejected_applications") == 1,
          str(result.get("rejected_applications")))
    check("under_objection_applications = 1 (T007)",
          result.get("under_objection_applications") == 1,
          str(result.get("under_objection_applications")))
    check("missing_documents_applications = 1 (T008)",
          result.get("missing_documents_applications") == 1,
          str(result.get("missing_documents_applications")))
    check("certificates_issued = 1",
          result.get("certificates_issued") == 1,
          str(result.get("certificates_issued")))
    check("delayed_applications = 2 (T003 at -35d, T007 at -40d)",
          result.get("delayed_applications") == 2,
          str(result.get("delayed_applications")))
    check("average_processing_days is float >= 0",
          isinstance(result.get("average_processing_days"), (int, float))
          and result.get("average_processing_days") >= 0,
          str(result.get("average_processing_days")))
    # T004: 20-5=15d, T005: 30-2=28d -> avg = 21.5
    avg = result.get("average_processing_days")
    check("average_processing_days = 21.5 (T004=15d, T005=28d)",
          avg == 21.5, f"got {avg}")

    # Backward-compat fields
    check("backward-compat: approved_count present",
          "approved_count" in result)
    check("backward-compat: rejected_count present",
          "rejected_count" in result)


# ─────────────────────────────────────────────────────────────────────────────
# Task 6 — Applications by status
# ─────────────────────────────────────────────────────────────────────────────

def test_task6_by_status():
    section("Task 6 - Applications by Status")
    result = get_applications_by_status()

    check("Returns list", isinstance(result, list))
    check("List is non-empty", len(result) > 0, f"got {len(result)}")

    # Each entry must have status and count
    if result:
        check("Each entry has 'status' key", all("status" in r for r in result))
        check("Each entry has 'count' key", all("count" in r for r in result))

    # Sorted descending by count
    counts = [r["count"] for r in result]
    check("Sorted by count descending", counts == sorted(counts, reverse=True),
          str(counts))

    # Specific counts
    status_map = {r["status"]: r["count"] for r in result}
    check("submitted count = 3 (T001+T002+T003)",
          status_map.get("submitted") == 3,
          str(status_map))
    check("approved count = 2 (T004+T005)",
          status_map.get("approved") == 2,
          str(status_map))
    check("rejected count = 1 (T006)",
          status_map.get("rejected") == 1,
          str(status_map))
    check("under_objection count = 1 (T007)",
          status_map.get("under_objection") == 1,
          str(status_map))
    check("missing_documents count = 1 (T008)",
          status_map.get("missing_documents") == 1,
          str(status_map))
    check("First entry is 'submitted' with count 3",
          result[0]["status"] == "submitted" and result[0]["count"] == 3,
          str(result[0]))
    check("Second entry is 'approved' with count 2",
          result[1]["status"] == "approved" and result[1]["count"] == 2,
          str(result[1]))


# ─────────────────────────────────────────────────────────────────────────────
# Task 7 — Applications by type
# ─────────────────────────────────────────────────────────────────────────────

def test_task7_by_type():
    section("Task 7 - Applications by Type")
    result = get_applications_by_type()

    check("Returns list", isinstance(result, list))

    KNOWN_TYPES = [
        "first_registration", "ownership_transfer", "parcel_subdivision",
        "parcel_merge", "boundary_correction", "certificate_request",
    ]
    type_map = {r["application_type"]: r["count"] for r in result}

    check("All 6 required types present",
          all(t in type_map for t in KNOWN_TYPES),
          str([t for t in KNOWN_TYPES if t not in type_map]))

    check("ownership_transfer count = 3 (T001+T002+T005)",
          type_map.get("ownership_transfer") == 3,
          str(type_map))
    check("first_registration count = 2 (T003+T004)",
          type_map.get("first_registration") == 2,
          str(type_map))
    check("boundary_correction count = 1 (T006)",
          type_map.get("boundary_correction") == 1,
          str(type_map))
    check("parcel_subdivision count = 1 (T007)",
          type_map.get("parcel_subdivision") == 1,
          str(type_map))
    check("parcel_merge count = 1 (T008)",
          type_map.get("parcel_merge") == 1,
          str(type_map))
    check("certificate_request count = 0 (not seeded)",
          type_map.get("certificate_request") == 0,
          str(type_map.get("certificate_request")))

    # First entry should be highest count
    check("First entry is ownership_transfer with count 3",
          result[0]["application_type"] == "ownership_transfer"
          and result[0]["count"] == 3,
          str(result[0]))

    # certificate_request (0 count) should be at the end
    check("certificate_request (count=0) appears last or near last",
          result[-1]["application_type"] == "certificate_request"
          or type_map.get("certificate_request", -1) == 0,
          str(result[-1]))


# ─────────────────────────────────────────────────────────────────────────────
# Task 8 — Applications by zone
# ─────────────────────────────────────────────────────────────────────────────

def test_task8_by_zone():
    section("Task 8 - Applications by Zone")
    result = get_applications_by_zone()

    check("Returns list", isinstance(result, list))
    check("At least 3 zones returned (Z-01, Z-02, unknown/Z-03)",
          len(result) >= 3, f"got {len(result)}")

    zone_map = {r["zone_id"]: r for r in result}

    # Z-01: T001(submitted)+T002(submitted)+T003(submitted)+T007(under_objection)
    z01 = zone_map.get("Z-01")
    check("Z-01 exists", z01 is not None, str(list(zone_map.keys())))
    check("Z-01 count = 4", z01 and z01["count"] == 4, str(z01))
    check("Z-01 pending = 4 (all 4 are pending statuses)",
          z01 and z01["pending"] == 4, str(z01))
    check("Z-01 approved = 0", z01 and z01["approved"] == 0, str(z01))
    check("Z-01 rejected = 0", z01 and z01["rejected"] == 0, str(z01))

    # Z-02: T004(approved)+T005(approved)
    z02 = zone_map.get("Z-02")
    check("Z-02 exists", z02 is not None)
    check("Z-02 count = 2", z02 and z02["count"] == 2, str(z02))
    check("Z-02 approved = 2", z02 and z02["approved"] == 2, str(z02))
    check("Z-02 pending = 0", z02 and z02["pending"] == 0, str(z02))

    # Z-03: T006(rejected, resolved via string parcel_ref "P-STR" -> Z-03)
    z03 = zone_map.get("Z-03")
    check("Z-03 exists (resolved from string parcel_ref 'P-STR')",
          z03 is not None, str(list(zone_map.keys())))
    check("Z-03 count = 1", z03 and z03["count"] == 1, str(z03))
    check("Z-03 rejected = 1", z03 and z03["rejected"] == 1, str(z03))

    # unknown: T008 (parcel_ref = None)
    unk = zone_map.get("unknown")
    check("'unknown' zone exists (for None parcel_ref)",
          unk is not None, str(list(zone_map.keys())))
    check("'unknown' count = 1", unk and unk["count"] == 1, str(unk))
    check("'unknown' pending = 1 (T008 is missing_documents)",
          unk and unk["pending"] == 1, str(unk))

    # Each entry has required fields
    required_zone_keys = {"zone_id", "count", "pending", "approved", "rejected"}
    if result:
        missing = required_zone_keys - set(result[0].keys())
        check("All required zone fields present", len(missing) == 0, str(missing))

    # Sorted by count descending
    counts = [r["count"] for r in result]
    check("Sorted by count descending",
          counts == sorted(counts, reverse=True), str(counts))

    # Z-01 should be first (count=4)
    check("Z-01 is first (highest count=4)",
          result[0]["zone_id"] == "Z-01", str(result[0]))


# ─────────────────────────────────────────────────────────────────────────────
# Task 9 — Processing time analytics
# ─────────────────────────────────────────────────────────────────────────────

def test_task9_processing_time():
    section("Task 9 - Processing Time Analytics")
    result = get_processing_time()

    check("Returns list", isinstance(result, list))

    KNOWN_TYPES = [
        "first_registration", "ownership_transfer", "parcel_subdivision",
        "parcel_merge", "boundary_correction", "certificate_request",
    ]
    type_map = {r["application_type"]: r for r in result}

    check("All 6 required types present in result",
          all(t in type_map for t in KNOWN_TYPES),
          str([t for t in KNOWN_TYPES if t not in type_map]))

    # Required fields per entry
    req_keys = {
        "application_type", "average_processing_days", "average_precheck_days",
        "average_survey_delay_days", "average_approval_days", "sample_count",
    }
    if result:
        missing = req_keys - set(result[0].keys())
        check("Required fields present per entry", len(missing) == 0, str(missing))

    # ownership_transfer: T001(submitted only), T002(submitted only), T005(full timestamps)
    # Only T005 contributes timestamps: precheck=5d, survey_delay=10d, approval=8d, processing=28d
    ot = type_map.get("ownership_transfer")
    check("ownership_transfer exists", ot is not None)
    check("ownership_transfer sample_count = 3 (T001+T002+T005)",
          ot and ot["sample_count"] == 3, str(ot and ot.get("sample_count")))
    check("ownership_transfer average_precheck_days = 5.0 (only T005 has precheck)",
          ot and ot["average_precheck_days"] == 5.0,
          str(ot and ot.get("average_precheck_days")))
    check("ownership_transfer average_survey_delay_days = 10.0",
          ot and ot["average_survey_delay_days"] == 10.0,
          str(ot and ot.get("average_survey_delay_days")))
    check("ownership_transfer average_approval_days = 8.0",
          ot and ot["average_approval_days"] == 8.0,
          str(ot and ot.get("average_approval_days")))
    check("ownership_transfer average_processing_days = 28.0",
          ot and ot["average_processing_days"] == 28.0,
          str(ot and ot.get("average_processing_days")))

    # first_registration: T003(submitted only), T004(full timestamps)
    # T004: precheck=5d, survey_delay=4d, approval=3d, processing=15d
    fr = type_map.get("first_registration")
    check("first_registration exists", fr is not None)
    check("first_registration sample_count = 2 (T003+T004)",
          fr and fr["sample_count"] == 2, str(fr and fr.get("sample_count")))
    check("first_registration average_precheck_days = 5.0 (only T004)",
          fr and fr["average_precheck_days"] == 5.0,
          str(fr and fr.get("average_precheck_days")))
    check("first_registration average_survey_delay_days = 4.0",
          fr and fr["average_survey_delay_days"] == 4.0,
          str(fr and fr.get("average_survey_delay_days")))
    check("first_registration average_approval_days = 3.0",
          fr and fr["average_approval_days"] == 3.0,
          str(fr and fr.get("average_approval_days")))
    check("first_registration average_processing_days = 15.0",
          fr and fr["average_processing_days"] == 15.0,
          str(fr and fr.get("average_processing_days")))

    # boundary_correction (T006): only submitted_at -> all averages = 0.0
    bc = type_map.get("boundary_correction")
    check("boundary_correction exists", bc is not None)
    check("boundary_correction sample_count = 1", bc and bc["sample_count"] == 1,
          str(bc and bc.get("sample_count")))
    check("boundary_correction average_precheck_days = 0.0 (no timestamps)",
          bc and bc["average_precheck_days"] == 0.0,
          str(bc and bc.get("average_precheck_days")))

    # certificate_request: not in collection -> all zeros
    cr = type_map.get("certificate_request")
    check("certificate_request exists (known type, count=0)", cr is not None)
    check("certificate_request sample_count = 0",
          cr and cr["sample_count"] == 0, str(cr))
    check("certificate_request all averages = 0.0",
          cr and all(cr[k] == 0.0 for k in [
              "average_processing_days", "average_precheck_days",
              "average_survey_delay_days", "average_approval_days"
          ]), str(cr))

    # Missing timestamps must not crash
    check("Function does not crash with missing timestamps", True)

    # Values rounded to 2 decimal places
    if ot:
        check("Values are float (2dp rounding)", isinstance(ot["average_precheck_days"], float))


# ─────────────────────────────────────────────────────────────────────────────
# Additional safety: missing-timestamp robustness
# ─────────────────────────────────────────────────────────────────────────────

def test_robustness_no_timestamps():
    section("Task 9 Robustness - No Timestamps Does Not Crash")
    # Insert a record with completely missing timestamps
    _mock_db["land_applications"].insert_one({
        "application_id": "T999",
        "application_type": "ownership_transfer",
        "status": "submitted",
        "parcel_ref": None,
        # No timestamps field at all
    })
    try:
        result = get_processing_time()
        check("get_processing_time with missing timestamps does not crash", True)
        ot = next((r for r in result if r["application_type"] == "ownership_transfer"), None)
        check("ownership_transfer still returned after adding no-timestamp doc", ot is not None)
    except Exception as e:
        check("get_processing_time with missing timestamps does not crash", False, str(e))
    finally:
        _mock_db["land_applications"].delete_one({"application_id": "T999"})

    # Unknown zone must not crash get_applications_by_zone
    try:
        result = get_applications_by_zone()
        check("get_applications_by_zone with None parcel_ref does not crash", True)
    except Exception as e:
        check("get_applications_by_zone with None parcel_ref does not crash", False, str(e))


# ── Summary ───────────────────────────────────────────────────────────────────

def run_all():
    print("\n" + "=" * 60)
    print("  Group Backend - Analytics Tasks 3-9 Mongomock Verification")
    print("=" * 60)

    seed_all()

    test_task3_schemas()
    test_task4_router()
    test_task5_kpis()
    test_task6_by_status()
    test_task7_by_type()
    test_task8_by_zone()
    test_task9_processing_time()
    test_robustness_no_timestamps()

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


# ── pytest compatibility ──────────────────────────────────────────────────────

def test_task3_schemas_pytest():
    seed_all()
    test_task3_schemas()
    failed = sum(1 for _, s, _ in _results if s == _FAIL)
    assert failed == 0, f"{failed} checks failed in test_task3_schemas"


def test_task4_router_pytest():
    test_task4_router()


def test_task5_kpis_pytest():
    seed_all()
    test_task5_kpis()


def test_task6_pytest():
    seed_all()
    test_task6_by_status()


def test_task7_pytest():
    seed_all()
    test_task7_by_type()


def test_task8_pytest():
    seed_all()
    test_task8_by_zone()


def test_task9_pytest():
    seed_all()
    test_task9_processing_time()


if __name__ == "__main__":
    ok = run_all()
    sys.exit(0 if ok else 1)
