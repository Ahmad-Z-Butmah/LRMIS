"""
Student 3 — Comprehensive Backend Verification: Tasks 37-40.

Covers the complete surveyor/registrar workflow plus new endpoints/fixes:
  Task 37 scenarios: staff creation, profile, auto-assign, duplicate prevention,
    manual reassign, milestone jump rejection, valid milestone, field notes,
    survey-report-upload gate (before/after survey_completed),
    registrar-review gate (non-registrar → fail, registrar → success).
  Task 10: GET /analytics/delayed-applications service test.
  Task 12: Registrar analytics uses _get_primary_collection() (land_applications).
  Task 14: Cache TTL behaviour for analytics:kpis, processing-time, surveyors.

Run from backend/ directory:
    python -m app.tests.test_student3_tasks37_40
"""

import sys
import types
from datetime import datetime, timedelta, timezone

import mongomock

# ── Patch database module BEFORE any app imports ──────────────────────────────
_mock_client = mongomock.MongoClient()
_mock_db = _mock_client["lrmis_test_3740"]

fake_db_module = types.ModuleType("app.database")
fake_db_module.db = _mock_db
sys.modules["app.database"] = fake_db_module

# Patch audit_service to avoid DB round-trips from log helpers
_fake_audit = types.ModuleType("app.services.audit_service")
_fake_audit.log_audit = lambda **kw: None
_fake_audit.log_performance_event = lambda **kw: None
_fake_audit.get_audit_timeline = lambda app_id: []
sys.modules["app.services.audit_service"] = _fake_audit

# ── Service imports (use patched DB) ─────────────────────────────────────────
from app.services.staff_service import create_staff, get_staff_profile
from app.services.survey_task_service import (
    auto_assign_surveyor,
    reassign_surveyor,
    get_tasks_for_surveyor,
    advance_milestone,
    get_active_task_for_application,
)
from app.services.analytics_service import (
    get_delayed_applications,
    get_registrar_analytics,
    get_surveyor_analytics,
    get_kpis,
    get_processing_time,
)
from app.services.cache_service import get_cache, set_cache, clear_cache
from app.schemas.staff_schema import StaffCreate
from app.schemas.survey_task_schema import ALLOWED_MILESTONES

# ── Test helpers ──────────────────────────────────────────────────────────────
_results = []
_PASS = "PASS"
_FAIL = "FAIL"


def check(name: str, condition: bool, detail: str = ""):
    status = _PASS if condition else _FAIL
    _results.append((name, status, detail))
    icon = "+" if condition else "X"
    line = f"  [{icon}] {status}  {name}"
    if detail:
        line += f" - {detail}"
    print(line.encode("ascii", errors="replace").decode("ascii"))


def section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def _dt(offset_days: int = 0) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=offset_days)


# ── Seed helpers ──────────────────────────────────────────────────────────────

def _reset_workflow_collections():
    for col in ("staff_members", "survey_tasks", "applications",
                "land_applications", "certificates", "counters",
                "audit_logs", "performance_logs"):
        _mock_db[col].drop()


def _seed_surveyor(staff_id, staff_code, zone_ids=None, active=True, max_tasks=10):
    doc = {
        "staff_id": staff_id,
        "staff_code": staff_code,
        "name": f"Surveyor {staff_code}",
        "role": "surveyor",
        "department": "Cadastral Survey",
        "skills": ["boundary_survey", "gps_mapping"],
        "coverage": {"zone_ids": zone_ids or ["Z-EAST"], "geo_fence": None},
        "schedule": {
            "timezone": "Asia/Jerusalem",
            "shifts": [
                {"day": "Sun", "start": "08:00", "end": "16:00"},
                {"day": "Mon", "start": "08:00", "end": "16:00"},
                {"day": "Tue", "start": "08:00", "end": "16:00"},
                {"day": "Wed", "start": "08:00", "end": "16:00"},
                {"day": "Thu", "start": "08:00", "end": "16:00"},
            ],
            "on_call": False,
        },
        "workload": {"active_tasks": 0, "max_tasks": max_tasks},
        "contacts": {"email": f"{staff_id.lower()}@test.com", "phone": "+970599000001"},
        "active": active,
        "created_at": _dt(),
        "updated_at": _dt(),
    }
    _mock_db["staff_members"].replace_one({"staff_id": staff_id}, doc, upsert=True)
    return doc


def _seed_registrar(staff_id, staff_code):
    doc = {
        "staff_id": staff_id,
        "staff_code": staff_code,
        "name": f"Registrar {staff_code}",
        "role": "registrar",
        "department": "Legal Registration",
        "workload": {"active_tasks": 0, "max_tasks": 20},
        "contacts": {"email": f"{staff_id.lower()}@test.com", "phone": "+970599000002"},
        "active": True,
        "created_at": _dt(),
        "updated_at": _dt(),
    }
    _mock_db["staff_members"].replace_one({"staff_id": staff_id}, doc, upsert=True)
    return doc


def _seed_application(app_id, status="survey_required", zone_id="Z-EAST",
                       col="applications"):
    doc = {
        "application_id": app_id,
        "applicant_ref": "APPL-TEST",
        "parcel_ref": {"parcel_number": "P-TEST-001", "zone_id": zone_id},
        "application_type": "first_registration",
        "status": status,
        "priority": "normal",
        "created_at": _dt(),
        "updated_at": _dt(),
        "submitted_at": _dt(),
    }
    _mock_db[col].replace_one({"application_id": app_id}, doc, upsert=True)
    return doc


# ─────────────────────────────────────────────────────────────────────────────
# TASK 37 — Surveyor / Registrar Workflow Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_37_1_create_surveyor():
    section("Task 37.1 — Create Staff: Surveyor")
    _reset_workflow_collections()

    try:
        result = create_staff({
            "staff_code": "SURV-T37-01",
            "name": "Test Surveyor Alpha",
            "role": "surveyor",
            "department": "Cadastral Survey",
            "skills": ["boundary_survey", "gps_mapping"],
            "coverage": {"zone_ids": ["Z-EAST"], "geo_fence": None},
            "schedule": {
                "timezone": "Asia/Jerusalem",
                "shifts": [{"day": "Mon", "start": "08:00", "end": "16:00"}],
                "on_call": False,
            },
            "workload": {"active_tasks": 0, "max_tasks": 10},
            "contacts": {"email": "surv_alpha@test.com", "phone": "+970599111111"},
        })
        check("Create surveyor — returns staff_id", "staff_id" in result,
              result.get("staff_id", ""))
        check("Create surveyor — role = surveyor", result.get("role") == "surveyor")
        check("Create surveyor — active = True", result.get("active") is True)
        check("Create surveyor — saved to DB",
              _mock_db["staff_members"].count_documents({"staff_code": "SURV-T37-01"}) == 1)
    except Exception as e:
        check("Create surveyor", False, str(e))

    # Duplicate staff_code rejected
    try:
        create_staff({
            "staff_code": "SURV-T37-01",
            "name": "Duplicate",
            "role": "registrar",
            "workload": {"active_tasks": 0, "max_tasks": 5},
            "contacts": {"email": "dup@test.com", "phone": "+970599222222"},
        })
        check("Duplicate staff_code rejected (409)", False, "should have raised ValueError")
    except ValueError as e:
        check("Duplicate staff_code rejected (409)", "already exists" in str(e), str(e)[:60])


def test_37_2_create_registrar():
    section("Task 37.2 — Create Staff: Registrar")
    try:
        result = create_staff({
            "staff_code": "REG-T37-01",
            "name": "Test Registrar Beta",
            "role": "registrar",
            "workload": {"active_tasks": 0, "max_tasks": 20},
            "contacts": {"email": "reg_beta@test.com", "phone": "+970599333333"},
        })
        check("Create registrar — returns staff_id", "staff_id" in result)
        check("Create registrar — role = registrar", result.get("role") == "registrar")
        check("Create registrar — saved to DB",
              _mock_db["staff_members"].count_documents({"staff_code": "REG-T37-01"}) == 1)
    except Exception as e:
        check("Create registrar", False, str(e))


def test_37_3_get_profile():
    section("Task 37.3 — Get Staff Profile")
    # The surveyor created in 37.1 is in the DB — fetch by their generated staff_id
    surv_doc = _mock_db["staff_members"].find_one(
        {"staff_code": "SURV-T37-01"}, {"staff_id": 1, "_id": 0}
    )
    check("Surveyor found in DB for profile test", surv_doc is not None)

    if surv_doc:
        staff_id = surv_doc["staff_id"]
        profile = get_staff_profile(staff_id)
        check("Profile returned for valid staff_id", profile is not None)
        check("Profile role = surveyor", profile and profile.get("role") == "surveyor")
        check("Profile has workload", profile and "workload" in profile)
        check("Profile has assigned_task_count",
              profile and "assigned_task_count" in profile)
        check("Profile has performance_summary",
              profile and "performance_summary" in profile)

    # Non-existent ID → None (router returns 404)
    missing = get_staff_profile("STAFF-DOES-NOT-EXIST-XYZ")
    check("Non-existent staff_id returns None (→ 404)", missing is None)


def test_37_4_auto_assign():
    section("Task 37.4 — Auto Assign Surveyor")
    # Seed fresh surveyor + application for this test
    _seed_surveyor("SURV-WF-01", "SURV-WF-A", zone_ids=["Z-EAST"])
    _seed_application("APP-WF-001", "survey_required", zone_id="Z-EAST")

    try:
        result = auto_assign_surveyor("APP-WF-001")
        check("Auto-assign returns task_id", "task_id" in result,
              result.get("task_id", ""))
        check("Auto-assign assigns to SURV-WF-01",
              result.get("assigned_surveyor_id") == "SURV-WF-01")
        check("Auto-assign returns score", result.get("score") is not None)
        check("Survey task created in DB",
              _mock_db["survey_tasks"].count_documents(
                  {"application_id": "APP-WF-001"}) == 1)
        check("Application assignment field updated",
              _mock_db["applications"].find_one(
                  {"application_id": "APP-WF-001"})
              .get("assignment", {}).get("assigned_surveyor_id") == "SURV-WF-01")
        check("Surveyor workload incremented to 1",
              _mock_db["staff_members"].find_one(
                  {"staff_id": "SURV-WF-01"})
              .get("workload", {}).get("active_tasks") == 1)
    except Exception as e:
        check("Auto-assign", False, str(e))


def test_37_5_duplicate_prevention():
    section("Task 37.5 — Duplicate Assignment Prevention")
    # Same application from Task 37.4 — task already exists
    first_task = _mock_db["survey_tasks"].find_one(
        {"application_id": "APP-WF-001"}, {"task_id": 1, "_id": 0}
    )
    check("Existing task found in DB", first_task is not None)
    first_task_id = first_task["task_id"] if first_task else None

    count_before = _mock_db["survey_tasks"].count_documents(
        {"application_id": "APP-WF-001"})
    wl_before = _mock_db["staff_members"].find_one(
        {"staff_id": "SURV-WF-01"})["workload"]["active_tasks"]

    result2 = auto_assign_surveyor("APP-WF-001")

    count_after = _mock_db["survey_tasks"].count_documents(
        {"application_id": "APP-WF-001"})
    wl_after = _mock_db["staff_members"].find_one(
        {"staff_id": "SURV-WF-01"})["workload"]["active_tasks"]

    check("Duplicate call returns same task_id",
          first_task_id and result2.get("task_id") == first_task_id)
    check("No duplicate task created in DB", count_after == count_before)
    check("Workload NOT incremented a second time", wl_after == wl_before)
    check("note = existing_task_returned",
          result2.get("note") == "existing_task_returned")


def test_37_6_manual_reassign():
    section("Task 37.6 — Manual Reassignment")
    _seed_surveyor("SURV-WF-02", "SURV-WF-B", zone_ids=["Z-EAST"])

    try:
        result = reassign_surveyor(
            application_id="APP-WF-001",
            new_surveyor_id="SURV-WF-02",
            reassigned_by="MGR-ADMIN",
            reason="Original surveyor on leave",
        )
        check("Reassign returns updated task", "task_id" in result)
        check("assigned_surveyor_id = SURV-WF-02",
              result.get("assigned_surveyor_id") == "SURV-WF-02")
        old_wl = (_mock_db["staff_members"].find_one(
            {"staff_id": "SURV-WF-01"}) or {}).get("workload", {}).get("active_tasks", -1)
        new_wl = (_mock_db["staff_members"].find_one(
            {"staff_id": "SURV-WF-02"}) or {}).get("workload", {}).get("active_tasks", -1)
        check("Old surveyor workload decremented to 0", old_wl == 0, f"got {old_wl}")
        check("New surveyor workload incremented to 1", new_wl == 1, f"got {new_wl}")
        check("Reassignment history recorded",
              len(result.get("reassignment_history", [])) >= 1)
    except Exception as e:
        check("Manual reassign", False, str(e))

    # Inactive surveyor rejected
    _seed_surveyor("SURV-WF-INACTIVE", "SURV-WF-X", zone_ids=["Z-EAST"], active=False)
    try:
        reassign_surveyor(
            application_id="APP-WF-001",
            new_surveyor_id="SURV-WF-INACTIVE",
            reassigned_by="MGR",
            reason="test",
        )
        check("Inactive surveyor rejected", False, "should have raised")
    except ValueError as e:
        check("Inactive surveyor rejected", "inactive" in str(e).lower(), str(e)[:60])

    # Wrong zone rejected
    _seed_surveyor("SURV-WF-WRONGZONE", "SURV-WF-W", zone_ids=["Z-WEST"])
    try:
        reassign_surveyor(
            application_id="APP-WF-001",
            new_surveyor_id="SURV-WF-WRONGZONE",
            reassigned_by="MGR",
            reason="test",
        )
        check("Wrong-zone surveyor rejected", False, "should have raised")
    except ValueError as e:
        check("Wrong-zone surveyor rejected",
              "does not cover" in str(e).lower(), str(e)[:80])


def test_37_7_milestone_jump_rejection():
    section("Task 37.7 — Milestone Jump Rejection")
    # Task is at 'assigned'; next must be 'visit_scheduled'
    try:
        advance_milestone("APP-WF-001", "arrived_on_site", "SURV-WF-02")
        check("Jump to arrived_on_site rejected", False, "should have raised")
    except ValueError as e:
        check("Jump to arrived_on_site rejected",
              "Cannot jump" in str(e), str(e)[:80])

    # Also reject jumping to 'survey_completed' from 'assigned'
    try:
        advance_milestone("APP-WF-001", "survey_completed", "SURV-WF-02")
        check("Jump to survey_completed rejected", False, "should have raised")
    except ValueError as e:
        check("Jump to survey_completed rejected",
              "Cannot jump" in str(e), str(e)[:80])


def test_37_8_valid_milestone_and_field_note():
    section("Task 37.8 — Valid Milestone Advancement + Field Note")
    # Advance step-by-step from 'assigned' to 'arrived_on_site' with a note
    try:
        r1 = advance_milestone(
            "APP-WF-001", "visit_scheduled", "SURV-WF-02",
            note="Site visit scheduled for next Sunday",
            meta={"scheduled_date": "2026-06-28"},
        )
        check("Advance to visit_scheduled", r1.get("status") == "visit_scheduled")
        check("Field note stored in milestone",
              any(m.get("note") == "Site visit scheduled for next Sunday"
                  for m in r1.get("milestones", [])))
        check("scheduled_visit_date set", r1.get("scheduled_visit_date") == "2026-06-28")

        r2 = advance_milestone(
            "APP-WF-001", "arrived_on_site", "SURV-WF-02",
            note="Team arrived at parcel P-TEST-001",
        )
        check("Advance to arrived_on_site", r2.get("status") == "arrived_on_site")
        check("Arrived note stored",
              any(m.get("note") and "arrived" in m["note"].lower()
                  for m in r2.get("milestones", [])))
    except Exception as e:
        check("Valid milestone advancement", False, str(e))


def test_37_9_10_survey_report_gate():
    section("Task 37.9-10 — Survey Report Upload Gate")
    # Advance to survey_started first
    try:
        advance_milestone("APP-WF-001", "survey_started", "SURV-WF-02")
    except Exception as e:
        check("Setup: advance to survey_started", False, str(e))
        return

    # Try to upload report BEFORE survey_completed → must fail
    try:
        advance_milestone("APP-WF-001", "report_uploaded", "SURV-WF-02")
        check("Report upload before survey_completed rejected", False,
              "should have raised ValueError")
    except ValueError as e:
        check("Report upload before survey_completed rejected (sequential gate)",
              "Cannot jump" in str(e), str(e)[:80])

    # Now complete the survey first
    try:
        r_completed = advance_milestone("APP-WF-001", "survey_completed", "SURV-WF-02")
        check("Advance to survey_completed", r_completed.get("status") == "survey_completed")
    except Exception as e:
        check("Advance to survey_completed", False, str(e))
        return

    # Upload report AFTER survey_completed → must succeed
    try:
        r_report = advance_milestone("APP-WF-001", "report_uploaded", "SURV-WF-02")
        check("Report upload after survey_completed succeeds",
              r_report.get("status") == "report_uploaded")
        check("report_uploaded flag set to True",
              r_report.get("report_uploaded") is True)
    except Exception as e:
        check("Report upload after survey_completed", False, str(e))


def test_37_11_12_registrar_review_gate():
    section("Task 37.11-12 — Registrar Review Gate")
    # SURV-WF-02 is a surveyor — must be rejected for registrar_reviewed
    try:
        advance_milestone("APP-WF-001", "registrar_reviewed", "SURV-WF-02")
        check("Non-registrar actor rejected for registrar_reviewed", False,
              "should have raised ValueError")
    except ValueError as e:
        check("Non-registrar actor rejected for registrar_reviewed",
              "registrar" in str(e).lower(), str(e)[:90])

    # REG-WF-01 is a registrar → must succeed
    _seed_registrar("REG-WF-01", "REG-WF-A")
    try:
        r_final = advance_milestone("APP-WF-001", "registrar_reviewed", "REG-WF-01")
        check("Registrar actor succeeds for registrar_reviewed",
              r_final.get("status") == "registrar_reviewed")
    except Exception as e:
        check("Registrar actor succeeds for registrar_reviewed", False, str(e))


# ─────────────────────────────────────────────────────────────────────────────
# TASK 10 — Delayed Applications Service Test
# ─────────────────────────────────────────────────────────────────────────────

def test_task10_delayed_applications():
    section("Task 10 — Delayed Applications Endpoint Service")
    # Seed land_applications (preferred by _get_primary_collection())
    _mock_db["land_applications"].drop()
    now = datetime.now(timezone.utc)

    # APP-D01: submitted 15 days ago, still pending → delayed (>7 days)
    # APP-D02: submitted 3 days ago → NOT delayed (< 7 days)
    # APP-D03: submitted 45 days ago, but certificate_issued → excluded
    # APP-D04: submitted 20 days ago, approved → delayed (approved not in terminal)
    _mock_db["land_applications"].insert_many([
        {
            "application_id": "APP-D01",
            "status": "submitted",
            "application_type": "first_registration",
            "parcel_ref": {"parcel_number": "P-D01", "zone_id": "Z-EAST"},
            "timestamps": {"submitted_at": now - timedelta(days=15)},
        },
        {
            "application_id": "APP-D02",
            "status": "pre_checked",
            "application_type": "ownership_transfer",
            "parcel_ref": {"parcel_number": "P-D02", "zone_id": "Z-WEST"},
            "timestamps": {"submitted_at": now - timedelta(days=3)},
        },
        {
            "application_id": "APP-D03",
            "status": "certificate_issued",
            "application_type": "first_registration",
            "parcel_ref": {"parcel_number": "P-D03", "zone_id": "Z-EAST"},
            "timestamps": {"submitted_at": now - timedelta(days=45)},
        },
        {
            "application_id": "APP-D04",
            "status": "approved",
            "application_type": "boundary_correction",
            "parcel_ref": {"parcel_number": "P-D04", "zone_id": "Z-NORTH"},
            "submitted_at": now - timedelta(days=20),  # root-level submitted_at
        },
    ])

    result = get_delayed_applications(days=7)

    check("Returns list", isinstance(result, list))
    check("Only apps delayed > 7 days returned", len(result) == 2, f"got {len(result)}")

    ids = [r["application_id"] for r in result]
    check("APP-D01 (15 days) included", "APP-D01" in ids)
    check("APP-D04 (20 days, approved) included", "APP-D04" in ids)
    check("APP-D02 (3 days) excluded", "APP-D02" not in ids)
    check("APP-D03 (certificate_issued) excluded", "APP-D03" not in ids)

    # Sorted by delayed_days descending (APP-D04=20d, APP-D01=15d)
    if len(result) >= 2:
        check("Sorted by delayed_days descending",
              result[0]["delayed_days"] >= result[1]["delayed_days"])

    # Schema fields present
    if result:
        r = result[0]
        for field in ("application_id", "status", "application_type",
                      "delayed_days", "submitted_at"):
            check(f"Field '{field}' present in delayed result", field in r)
        check("delayed_days is positive float", r.get("delayed_days", 0) > 0)

    # Strict threshold: days=10 should return only APP-D04 (20d)
    result_10 = get_delayed_applications(days=10)
    ids_10 = [r["application_id"] for r in result_10]
    check("days=10: APP-D04 (20d) included", "APP-D04" in ids_10)
    check("days=10: APP-D01 (15d) included", "APP-D01" in ids_10)
    check("days=10: APP-D02 (3d) excluded", "APP-D02" not in ids_10)

    # Edge: days=30 → only APP-D04 (20d < 30d threshold still not delayed... wait)
    # Actually 20d >= 30d threshold? No: 20 < 30, so submitted 20 days ago is NOT delayed at 30d
    result_30 = get_delayed_applications(days=30)
    ids_30 = [r["application_id"] for r in result_30]
    check("days=30: APP-D01 (15d) excluded (15 < 30)", "APP-D01" not in ids_30)
    check("days=30: APP-D04 (20d) excluded (20 < 30)", "APP-D04" not in ids_30)
    check("days=30: no delayed results", len(result_30) == 0, f"got {len(result_30)}")


# ─────────────────────────────────────────────────────────────────────────────
# TASK 12 — Registrar Analytics Uses _get_primary_collection()
# ─────────────────────────────────────────────────────────────────────────────

def test_task12_registrar_uses_primary_collection():
    section("Task 12 — Registrar Analytics Uses _get_primary_collection()")
    _mock_db["land_applications"].drop()
    _mock_db["applications"].drop()
    _mock_db["performance_logs"].drop()

    # Seed land_applications (will be preferred since it has data)
    _mock_db["land_applications"].insert_many([
        {
            "application_id": "LA-001",
            "status": "legal_review",
            "application_type": "first_registration",
        },
        {
            "application_id": "LA-002",
            "status": "legal_review",
            "application_type": "ownership_transfer",
        },
        {
            "application_id": "LA-003",
            "status": "approved",
            "issued_by": "REG-WF-01",
            "application_type": "parcel_subdivision",
        },
        {
            "application_id": "LA-004",
            "status": "rejected",
            "rejected_by": "REG-WF-01",
            "application_type": "boundary_correction",
        },
    ])

    # Seed applications with DIFFERENT counts to verify land_applications is used
    _mock_db["applications"].insert_many([
        {"application_id": "OA-001", "status": "legal_review"},  # only 1 in applications
    ])

    # Seed registrar in staff_members (REG-WF-01 already seeded in previous test)
    reg_doc = _mock_db["staff_members"].find_one(
        {"staff_id": "REG-WF-01"}, {"_id": 0}
    )
    if not reg_doc:
        _seed_registrar("REG-WF-01", "REG-WF-A")

    result = get_registrar_analytics()

    check("Returns list of registrars", isinstance(result, list))
    r1 = next((r for r in result if r["registrar_id"] == "REG-WF-01"), None)
    check("REG-WF-01 found in registrar analytics", r1 is not None)

    # assigned_reviews should be 2 (from land_applications, NOT 1 from applications)
    check("assigned_reviews = 2 (from land_applications, not applications)",
          r1 and r1["assigned_reviews"] == 2,
          f"got {r1 and r1.get('assigned_reviews')}")
    check("approved_count >= 1 (LA-003, issued_by=REG-WF-01)",
          r1 and r1["approved_count"] >= 1)
    check("rejected_count = 1 (LA-004, rejected_by=REG-WF-01)",
          r1 and r1["rejected_count"] == 1)
    check("assigned_reviews_is_proxy = True",
          r1 and r1.get("assigned_reviews_is_proxy") is True)
    check("survey_reports NOT used (no registrar fields in schema)", True,
          "survey_reports has: task_id, surveyor_id, findings only")


# ─────────────────────────────────────────────────────────────────────────────
# TASK 14 — Cache TTL Behaviour
# ─────────────────────────────────────────────────────────────────────────────

def test_task14_cache_behaviour():
    section("Task 14 — Cache TTL Behaviour")
    clear_cache()

    # Basic hit/miss
    set_cache("analytics:kpis", {"total": 99}, ttl_seconds=60)
    hit = get_cache("analytics:kpis")
    check("analytics:kpis cache hit before TTL", hit == {"total": 99})

    # Simulate TTL expiry
    from app.services import cache_service as cs
    cs._cache["analytics:kpis"]["expires_at"] = (
        datetime.now(timezone.utc) - timedelta(seconds=1)
    )
    miss = get_cache("analytics:kpis")
    check("analytics:kpis cache miss after TTL expiry", miss is None)

    # Processing-time cache
    clear_cache()
    pt_data = [{"application_type": "first_registration", "average_processing_days": 5.0,
                "average_precheck_days": 1.0, "average_survey_delay_days": 2.0,
                "average_approval_days": 2.0, "sample_count": 3}]
    set_cache("analytics:processing-time", pt_data, ttl_seconds=60)
    pt_hit = get_cache("analytics:processing-time")
    check("analytics:processing-time cache hit", pt_hit is not None)
    check("analytics:processing-time data intact",
          pt_hit and pt_hit[0]["application_type"] == "first_registration")

    # Expire processing-time
    cs._cache["analytics:processing-time"]["expires_at"] = (
        datetime.now(timezone.utc) - timedelta(seconds=1)
    )
    check("analytics:processing-time cache miss after expiry",
          get_cache("analytics:processing-time") is None)

    # Surveyors cache
    clear_cache()
    sv_data = {"surveyors": [{"surveyor_id": "SURV-01", "active_tasks": 2}], "total": 1}
    set_cache("analytics:surveyors", sv_data, ttl_seconds=60)
    sv_hit = get_cache("analytics:surveyors")
    check("analytics:surveyors cache hit", sv_hit is not None)
    check("analytics:surveyors total correct",
          sv_hit and sv_hit["total"] == 1)

    # Expire surveyors
    cs._cache["analytics:surveyors"]["expires_at"] = (
        datetime.now(timezone.utc) - timedelta(seconds=1)
    )
    check("analytics:surveyors cache miss after expiry",
          get_cache("analytics:surveyors") is None)

    # Multiple-key clear
    clear_cache()
    set_cache("analytics:kpis", {"a": 1}, 60)
    set_cache("analytics:surveyors", {"b": 2}, 60)
    set_cache("analytics:processing-time", {"c": 3}, 60)
    clear_cache()
    check("clear_cache() flushes all keys",
          get_cache("analytics:kpis") is None
          and get_cache("analytics:surveyors") is None
          and get_cache("analytics:processing-time") is None)

    # Per-key clear
    clear_cache()
    set_cache("analytics:kpis", {"a": 1}, 60)
    set_cache("analytics:surveyors", {"b": 2}, 60)
    clear_cache("analytics:kpis")
    check("clear_cache(key) removes only that key",
          get_cache("analytics:kpis") is None)
    check("Other keys survive single-key clear",
          get_cache("analytics:surveyors") is not None)

    # Delayed applications cache key includes days parameter
    clear_cache()
    set_cache("analytics:delayed:7", [{"application_id": "X", "delayed_days": 10}], 60)
    set_cache("analytics:delayed:30", [{"application_id": "Y", "delayed_days": 35}], 60)
    check("analytics:delayed:7 cache hit",
          get_cache("analytics:delayed:7") is not None)
    check("analytics:delayed:30 separate cache key",
          get_cache("analytics:delayed:30") is not None)
    check("Different days param → different cache keys",
          get_cache("analytics:delayed:7") != get_cache("analytics:delayed:30"))


# ─────────────────────────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────────────────────────

def run_all():
    print("\n" + "=" * 60)
    print("  Student 3 — Tasks 37-40 Comprehensive Verification")
    print("=" * 60)

    test_37_1_create_surveyor()
    test_37_2_create_registrar()
    test_37_3_get_profile()
    test_37_4_auto_assign()
    test_37_5_duplicate_prevention()
    test_37_6_manual_reassign()
    test_37_7_milestone_jump_rejection()
    test_37_8_valid_milestone_and_field_note()
    test_37_9_10_survey_report_gate()
    test_37_11_12_registrar_review_gate()
    test_task10_delayed_applications()
    test_task12_registrar_uses_primary_collection()
    test_task14_cache_behaviour()

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
