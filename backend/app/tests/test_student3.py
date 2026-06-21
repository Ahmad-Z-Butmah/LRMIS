"""
Student 3 — Backend verification tests using mongomock.

Run from backend/ directory:
    python -m app.tests.test_student3

Uses mongomock so MongoDB does NOT need to be running.
Does NOT touch the real database.
"""

import sys
import os
from datetime import datetime, timezone

# ── Patch database module to use mongomock before anything else imports it ────

import mongomock

_mock_client = mongomock.MongoClient()
_mock_db = _mock_client["lrmis_test"]

# Monkey-patch app.database so all service imports get the mock db
import importlib
import types

# Create a fake database module
fake_db_module = types.ModuleType("app.database")
fake_db_module.db = _mock_db
sys.modules["app.database"] = fake_db_module

# Now import services (they will use _mock_db)
from app.services.staff_service import create_staff, get_staff_profile
from app.services.assignment_service import find_best_surveyor, score_surveyor
from app.services.survey_task_service import (
    auto_assign_surveyor,
    reassign_surveyor,
    get_tasks_for_surveyor,
    advance_milestone,
    get_active_task_for_application,
)
from app.schemas.staff_schema import StaffCreate
from app.schemas.survey_task_schema import SurveyMilestoneUpdate, ManualReassignRequest


# ── Test helpers ──────────────────────────────────────────────────────────────

_PASS = "PASS"
_FAIL = "FAIL"
_results = []


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


# ── Seed helpers ──────────────────────────────────────────────────────────────

def _seed_surveyor(staff_id="STAFF-00001", staff_code="SURV-RM-04",
                   zone_ids=None, active=True, active_tasks=0, max_tasks=10,
                   skills=None):
    zone_ids = zone_ids or ["Z-EAST"]
    skills = skills or ["boundary_survey", "gps_mapping"]
    doc = {
        "staff_id": staff_id,
        "staff_code": staff_code,
        "name": "Survey Team A",
        "role": "surveyor",
        "department": "Cadastral Survey",
        "skills": skills,
        "coverage": {"zone_ids": zone_ids, "geo_fence": None},
        "schedule": {
            "timezone": "Asia/Jerusalem",
            "shifts": [
                {"day": "Mon", "start": "08:00", "end": "16:00"},
                {"day": "Tue", "start": "08:00", "end": "16:00"},
                {"day": "Wed", "start": "08:00", "end": "16:00"},
                {"day": "Thu", "start": "08:00", "end": "16:00"},
                {"day": "Sun", "start": "08:00", "end": "16:00"},
            ],
            "on_call": False,
        },
        "workload": {"active_tasks": active_tasks, "max_tasks": max_tasks},
        "contacts": {"email": f"{staff_code.lower()}@test.com", "phone": "+970599000000"},
        "active": active,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    _mock_db["staff_members"].replace_one({"staff_id": staff_id}, doc, upsert=True)
    return doc


def _seed_application(app_id="LRMIS-TEST-0001", status="survey_required",
                       zone_id="Z-EAST", priority="normal"):
    doc = {
        "application_id": app_id,
        "applicant_ref": "APPL-TEST",
        "parcel_ref": {
            "parcel_number": "P-TEST-001",
            "zone_id": zone_id,
        },
        "status": status,
        "workflow": {"current_state": status, "allowed_next": []},
        "required_documents": ["ownership_deed"],
        "priority": priority,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "submitted_at": datetime.now(timezone.utc),
    }
    _mock_db["applications"].replace_one({"application_id": app_id}, doc, upsert=True)
    return doc


# ─────────────────────────────────────────────────────────────────────────────
# TESTS
# ─────────────────────────────────────────────────────────────────────────────

def test_task1_schema_validation():
    section("Task 1 — Staff Schema Validation")
    from pydantic import ValidationError

    # Missing role
    try:
        StaffCreate(
            staff_code="S1", name="Test",
            contacts={"email": "a@b.com", "phone": "+1234567"}
        )
        check("Reject missing role", False, "should have raised")
    except ValidationError:
        check("Reject missing role", True)

    # Invalid role
    try:
        StaffCreate(
            staff_code="S1", name="Test", role="hacker",
            contacts={"email": "a@b.com", "phone": "+1234567"}
        )
        check("Reject invalid role", False, "should have raised")
    except ValidationError as e:
        check("Reject invalid role", True, str(e.errors()[0]["msg"])[:50])

    # Missing staff_code
    try:
        StaffCreate(
            name="Test", role="registrar",
            contacts={"email": "a@b.com", "phone": "+1234567"}
        )
        check("Reject missing staff_code", False, "should have raised")
    except ValidationError:
        check("Reject missing staff_code", True)

    # Surveyor without coverage
    try:
        StaffCreate(
            staff_code="S1", name="Test", role="surveyor",
            contacts={"email": "a@b.com", "phone": "+1234567"}
        )
        check("Reject surveyor without coverage", False, "should have raised")
    except ValidationError as e:
        check("Reject surveyor without coverage", True)

    # Surveyor with empty zone_ids
    try:
        StaffCreate(
            staff_code="S1", name="Test", role="surveyor",
            coverage={"zone_ids": []},
            contacts={"email": "a@b.com", "phone": "+1234567"}
        )
        check("Reject surveyor empty zone_ids", False, "should have raised")
    except ValidationError:
        check("Reject surveyor empty zone_ids", True)

    # Valid geo_fence Polygon
    try:
        s = StaffCreate(
            staff_code="SURV-01", name="A", role="surveyor",
            coverage={
                "zone_ids": ["Z-01"],
                "geo_fence": {
                    "type": "Polygon",
                    "coordinates": [[[35.19, 31.89], [35.22, 31.89], [35.22, 31.92], [35.19, 31.92], [35.19, 31.89]]]
                }
            },
            contacts={"email": "a@b.com", "phone": "+1234567"},
            workload={"active_tasks": 0, "max_tasks": 10}
        )
        check("Accept valid GeoJSON Polygon geo_fence", True, s.staff_code)
    except Exception as e:
        check("Accept valid GeoJSON Polygon geo_fence", False, str(e)[:60])

    # Invalid geo_fence type
    try:
        StaffCreate(
            staff_code="S1", name="A", role="surveyor",
            coverage={"zone_ids": ["Z-01"], "geo_fence": {"type": "Point", "coordinates": []}},
            contacts={"email": "a@b.com", "phone": "+1234567"}
        )
        check("Reject geo_fence non-Polygon", False, "should have raised")
    except ValidationError:
        check("Reject geo_fence non-Polygon", True)

    # Non-negative workload
    try:
        StaffCreate(
            staff_code="S1", name="A", role="registrar",
            workload={"active_tasks": -1, "max_tasks": 5},
            contacts={"email": "a@b.com", "phone": "+1234567"}
        )
        check("Reject negative active_tasks", False, "should have raised")
    except ValidationError:
        check("Reject negative active_tasks", True)


def test_task2_create_staff():
    section("Task 2 — Create Staff (POST /staff/)")
    _mock_db["staff_members"].drop()
    _mock_db["counters"].drop()

    # Create valid surveyor
    try:
        result = create_staff({
            "staff_code": "SURV-RM-04",
            "name": "Survey Team A",
            "role": "surveyor",
            "department": "Cadastral Survey",
            "skills": ["boundary_survey", "gps_mapping"],
            "coverage": {"zone_ids": ["ZONE-RM-01"], "geo_fence": None},
            "schedule": {"timezone": "Asia/Jerusalem", "shifts": [{"day": "Mon", "start": "08:00", "end": "16:00"}], "on_call": False},
            "workload": {"active_tasks": 0, "max_tasks": 10},
            "contacts": {"email": "survey_a@test.com", "phone": "+970599111111"},
        })
        check("Create surveyor — returns staff_id", "staff_id" in result, result.get("staff_id"))
        check("Create surveyor — returns staff_code", result.get("staff_code") == "SURV-RM-04")
        check("Create surveyor — saved to DB", _mock_db["staff_members"].count_documents({"staff_code": "SURV-RM-04"}) == 1)
        check("Create surveyor — active=True", result.get("active") is True)
    except Exception as e:
        check("Create surveyor", False, str(e))

    # Duplicate staff_code — must raise ValueError (409 in router)
    try:
        create_staff({
            "staff_code": "SURV-RM-04",
            "name": "Duplicate",
            "role": "registrar",
            "workload": {"active_tasks": 0, "max_tasks": 5},
            "contacts": {"email": "dup@test.com", "phone": "+970599222222"},
        })
        check("Duplicate staff_code returns 409", False, "should have raised ValueError")
    except ValueError as e:
        check("Duplicate staff_code returns 409", "already exists" in str(e), str(e)[:60])

    # DB count still 1
    check("No duplicate in DB", _mock_db["staff_members"].count_documents({}) == 1)


def test_task3_staff_profile():
    section("Task 3 — Get Staff Profile (GET /staff/{staff_id})")
    _mock_db["staff_members"].drop()
    _mock_db["survey_tasks"].drop()
    _mock_db["performance_logs"].drop()

    # Seed staff and a task
    _seed_surveyor("STAFF-00001", "SURV-T3")
    _mock_db["survey_tasks"].insert_one({
        "task_id": "TASK-T3-001",
        "application_id": "LRMIS-T3-0001",
        "assigned_surveyor_id": "STAFF-00001",
        "status": "assigned",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    })

    profile = get_staff_profile("STAFF-00001")
    check("Profile not None", profile is not None)
    check("Profile has role", profile.get("role") == "surveyor")
    check("Profile has skills", isinstance(profile.get("skills"), list))
    check("Profile has workload", "workload" in profile)
    check("Profile has assigned_task_count = 1", profile.get("assigned_task_count") == 1)
    check("Profile has assigned_tasks list (len 1)", len(profile.get("assigned_tasks", [])) == 1)
    check("Profile has performance_summary", "performance_summary" in profile)

    # 404 case
    missing = get_staff_profile("STAFF-DOES-NOT-EXIST")
    check("Missing staff returns None", missing is None)


def test_task4_survey_task_schemas():
    section("Task 4 — Survey Task Schemas")
    from pydantic import ValidationError
    from app.schemas.survey_task_schema import (
        SurveyMilestoneUpdate, ManualReassignRequest, ALLOWED_MILESTONES
    )

    # Valid milestones list
    check("ALLOWED_MILESTONES has 7 entries", len(ALLOWED_MILESTONES) == 7)
    check("First milestone is 'assigned'", ALLOWED_MILESTONES[0] == "assigned")
    check("Last milestone is 'registrar_reviewed'", ALLOWED_MILESTONES[-1] == "registrar_reviewed")

    # Invalid milestone
    try:
        SurveyMilestoneUpdate(milestone="hacked_state", by="me")
        check("Reject invalid milestone", False)
    except ValidationError:
        check("Reject invalid milestone", True)

    # Valid milestone
    try:
        m = SurveyMilestoneUpdate(milestone="visit_scheduled", by="SURV-01", note="Next Monday")
        check("Accept valid milestone", True, m.milestone)
    except Exception as e:
        check("Accept valid milestone", False, str(e))

    # ManualReassignRequest missing reason
    try:
        ManualReassignRequest(new_surveyor_id="S1", reassigned_by="MGR-01", reason="")
        check("Reject empty reason", False)
    except ValidationError:
        check("Reject empty reason", True)

    # ManualReassignRequest valid
    try:
        r = ManualReassignRequest(
            new_surveyor_id="S1", reassigned_by="MGR-01",
            reason="Original surveyor unavailable"
        )
        check("Accept valid ManualReassignRequest", True, r.reason[:30])
    except Exception as e:
        check("Accept valid ManualReassignRequest", False, str(e))


def test_task5_assignment_scoring():
    section("Task 5 — Assignment Scoring")

    # Full surveyor doc (active, zone match, available today, has skills, 0 active tasks)
    import datetime as dt_module
    today_num = datetime.now(timezone.utc).weekday()
    weekday_map = {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun"}
    today_abbr = weekday_map[today_num]

    surveyor_full = {
        "staff_id": "SURV-SCORE-01",
        "staff_code": "S-01",
        "name": "Full Match Surveyor",
        "role": "surveyor",
        "active": True,
        "skills": ["boundary_survey", "gps_mapping", "parcel_subdivision"],
        "coverage": {"zone_ids": ["Z-EAST", "Z-WEST"]},
        "schedule": {
            "shifts": [{"day": today_abbr, "start": "08:00", "end": "16:00"}],
        },
        "workload": {"active_tasks": 0, "max_tasks": 10},
    }

    # Temporarily seed this doc for _active_task_count
    _mock_db["staff_members"].replace_one({"staff_id": "SURV-SCORE-01"}, surveyor_full, upsert=True)
    _mock_db["survey_tasks"].delete_many({"assigned_surveyor_id": "SURV-SCORE-01"})

    result = score_surveyor(
        surveyor=surveyor_full,
        zone_id="Z-EAST",
        required_skills=["boundary_survey", "gps_mapping"],
        priority="high",
    )
    check("Eligible surveyor — eligible=True", result["eligible"] is True)
    check("Zone match +50", result["breakdown"].get("zone_match") == 50)
    check("Available today +20", result["breakdown"].get("available_today") == 20)
    check("Skill match +20 (with required_skills)", result["breakdown"].get("skill_match") == 20)
    check("High priority +10", result["breakdown"].get("high_priority") == 10)
    check("Active tasks penalty = 0", result["breakdown"].get("active_task_penalty") == 0)
    expected_score = 50 + 20 + 20 + 10
    check(f"Total score = {expected_score}", result["score"] == expected_score,
          f"got {result['score']}")

    # Skill match with no skills = 0
    result_no_skill = score_surveyor(
        surveyor=surveyor_full,
        zone_id="Z-EAST",
        required_skills=["laser_scan"],  # not in surveyor.skills
        priority=None,
    )
    check("No skill match = 0", result_no_skill["breakdown"].get("skill_match") == 0)

    # Inactive surveyor → reject
    inactive = dict(surveyor_full, active=False)
    r_inactive = score_surveyor(inactive, "Z-EAST", [], None)
    check("Inactive surveyor rejected", r_inactive["eligible"] is False,
          r_inactive.get("rejection_reason"))

    # Workload full → reject
    full_wl = dict(surveyor_full, active=True, workload={"active_tasks": 10, "max_tasks": 10})
    # Must insert active tasks so _active_task_count returns 10
    _mock_db["survey_tasks"].delete_many({"assigned_surveyor_id": "SURV-SCORE-01"})
    for i in range(10):
        _mock_db["survey_tasks"].insert_one({
            "task_id": f"TASK-SCORE-{i:03d}",
            "assigned_surveyor_id": "SURV-SCORE-01",
            "status": "assigned",
        })
    r_full = score_surveyor(full_wl, "Z-EAST", [], None)
    check("Full workload rejected", r_full["eligible"] is False,
          r_full.get("rejection_reason"))

    # Active task penalty — 2 tasks = -10
    _mock_db["survey_tasks"].delete_many({"assigned_surveyor_id": "SURV-SCORE-01"})
    for i in range(2):
        _mock_db["survey_tasks"].insert_one({
            "task_id": f"TASK-PEN-{i:03d}",
            "assigned_surveyor_id": "SURV-SCORE-01",
            "status": "assigned",
        })
    r_pen = score_surveyor(dict(surveyor_full, workload={"active_tasks": 0, "max_tasks": 10}),
                           "Z-EAST", [], None)
    check("2 active tasks → penalty -10", r_pen["breakdown"].get("active_task_penalty") == -10,
          f"got {r_pen['breakdown'].get('active_task_penalty')}")


def test_task6_auto_assign():
    section("Task 6 — Auto Assign Surveyor")
    _mock_db["staff_members"].drop()
    _mock_db["survey_tasks"].drop()
    _mock_db["applications"].drop()
    _mock_db["counters"].drop()
    _mock_db["performance_logs"].drop()
    _mock_db["audit_logs"].drop()

    _seed_surveyor("STAFF-00001", "SURV-A1", zone_ids=["Z-EAST"])
    _seed_application("LRMIS-T6-0001", "survey_required", zone_id="Z-EAST")

    try:
        result = auto_assign_surveyor("LRMIS-T6-0001")
        check("Auto-assign returns task_id", "task_id" in result, result.get("task_id"))
        check("Auto-assign returns assigned_surveyor_id",
              result.get("assigned_surveyor_id") == "STAFF-00001")
        check("Auto-assign returns score", result.get("score") is not None)
        check("Survey task created in DB",
              _mock_db["survey_tasks"].count_documents({"application_id": "LRMIS-T6-0001"}) == 1)
        check("Application assignment updated",
              _mock_db["applications"].find_one(
                  {"application_id": "LRMIS-T6-0001"})
              .get("assignment", {}).get("assigned_surveyor_id") == "STAFF-00001")
        check("Workload incremented",
              _mock_db["staff_members"].find_one(
                  {"staff_id": "STAFF-00001"})
              .get("workload", {}).get("active_tasks") == 1)
        check("Audit log written",
              _mock_db["audit_logs"].count_documents({"application_id": "LRMIS-T6-0001"}) >= 1)
    except Exception as e:
        check("Auto-assign success", False, str(e))

    # Wrong status
    _seed_application("LRMIS-T6-BAD", "submitted")
    try:
        auto_assign_surveyor("LRMIS-T6-BAD")
        check("Reject non-survey_required application", False)
    except ValueError as e:
        check("Reject non-survey_required application", True, str(e)[:60])


def test_task7_duplicate_prevention():
    section("Task 7 — Duplicate Assignment Prevention")

    # Use same state from Task 6 — task already exists for LRMIS-T6-0001
    first_task_id = _mock_db["survey_tasks"].find_one(
        {"application_id": "LRMIS-T6-0001"}, {"task_id": 1, "_id": 0}
    )["task_id"]

    task_count_before = _mock_db["survey_tasks"].count_documents(
        {"application_id": "LRMIS-T6-0001"})
    workload_before = _mock_db["staff_members"].find_one(
        {"staff_id": "STAFF-00001"})["workload"]["active_tasks"]

    result2 = auto_assign_surveyor("LRMIS-T6-0001")

    task_count_after = _mock_db["survey_tasks"].count_documents(
        {"application_id": "LRMIS-T6-0001"})
    workload_after = _mock_db["staff_members"].find_one(
        {"staff_id": "STAFF-00001"})["workload"]["active_tasks"]

    check("Second call returns same task_id", result2.get("task_id") == first_task_id)
    check("No duplicate task created", task_count_after == task_count_before)
    check("Workload NOT incremented twice", workload_after == workload_before)
    check("note = existing_task_returned", result2.get("note") == "existing_task_returned")


def test_task8_manual_reassign():
    section("Task 8 — Manual Reassignment")
    # Seed a second surveyor covering same zone
    _seed_surveyor("STAFF-00002", "SURV-B2", zone_ids=["Z-EAST"])

    # Valid reassign
    try:
        result = reassign_surveyor(
            application_id="LRMIS-T6-0001",
            new_surveyor_id="STAFF-00002",
            reassigned_by="MGR-01",
            reason="Original surveyor unavailable",
        )
        check("Reassign returns updated task", "task_id" in result)
        check("Task assigned_surveyor_id updated",
              result.get("assigned_surveyor_id") == "STAFF-00002")
        # Old surveyor workload should decrease
        old_wl = _mock_db["staff_members"].find_one(
            {"staff_id": "STAFF-00001"})["workload"]["active_tasks"]
        new_wl = _mock_db["staff_members"].find_one(
            {"staff_id": "STAFF-00002"})["workload"]["active_tasks"]
        check("Old surveyor workload decreased", old_wl == 0, f"old={old_wl}")
        check("New surveyor workload increased", new_wl == 1, f"new={new_wl}")
        check("Reassignment history recorded",
              len(result.get("reassignment_history", [])) == 1)
        check("Audit log for reassignment",
              _mock_db["audit_logs"].count_documents({
                  "application_id": "LRMIS-T6-0001",
                  "action": "survey_reassigned"
              }) >= 1)
    except Exception as e:
        check("Valid reassign", False, str(e))

    # Zone rejection — seed surveyor with different zone
    _seed_surveyor("STAFF-00003", "SURV-C3", zone_ids=["Z-WEST"])  # wrong zone
    try:
        reassign_surveyor(
            application_id="LRMIS-T6-0001",
            new_surveyor_id="STAFF-00003",
            reassigned_by="MGR-01",
            reason="Testing zone rejection",
        )
        check("Zone mismatch rejected", False, "should have raised")
    except ValueError as e:
        check("Zone mismatch rejected (strict)", "does not cover" in str(e), str(e)[:80])

    # Inactive surveyor rejection
    _seed_surveyor("STAFF-00004", "SURV-D4", zone_ids=["Z-EAST"], active=False)
    try:
        reassign_surveyor(
            application_id="LRMIS-T6-0001",
            new_surveyor_id="STAFF-00004",
            reassigned_by="MGR-01",
            reason="Testing inactive rejection",
        )
        check("Inactive surveyor rejected", False)
    except ValueError as e:
        check("Inactive surveyor rejected", "inactive" in str(e), str(e)[:60])

    # Missing reason (schema level — test schema directly)
    try:
        ManualReassignRequest(new_surveyor_id="S1", reassigned_by="MGR", reason="")
        check("Empty reason rejected by schema", False)
    except Exception:
        check("Empty reason rejected by schema", True)


def test_task9_surveyor_tasks():
    section("Task 9 — Get Surveyor Tasks (GET /staff/{staff_id}/survey-tasks)")
    tasks = get_tasks_for_surveyor("STAFF-00002")
    check("Returns list", isinstance(tasks, list))
    check("Returns 1 task (STAFF-00002 now holds the task)", len(tasks) == 1,
          f"got {len(tasks)}")
    if tasks:
        t = tasks[0]
        check("task_id present", "task_id" in t)
        check("application_id present", "application_id" in t)
        check("current_milestone present", "current_milestone" in t)
        check("report_uploaded present", "report_uploaded" in t)

    # Empty list for surveyor with no tasks
    empty = get_tasks_for_surveyor("STAFF-00001")
    check("Surveyor with no tasks → empty list", empty == [])

    # Non-existent staff profile → None (router returns 404)
    profile = get_staff_profile("STAFF-GHOST")
    check("Non-existent staff → None (would be 404)", profile is None)


def test_task10_survey_milestone():
    section("Task 10 — Survey Milestone (PATCH /applications/{id}/survey-milestone)")
    # Current task status: "assigned" (reassigned to STAFF-00002)
    # Next allowed: visit_scheduled

    # Valid next step
    try:
        result = advance_milestone(
            application_id="LRMIS-T6-0001",
            milestone="visit_scheduled",
            by="SURV-B2",
            note="Scheduled for Monday",
            meta={"scheduled_date": "2026-06-23"},
        )
        check("Advance to visit_scheduled — OK", result.get("status") == "visit_scheduled")
        check("scheduled_visit_date set",
              result.get("scheduled_visit_date") == "2026-06-23")
        check("Milestone appended to list",
              any(m.get("milestone") == "visit_scheduled"
                  for m in result.get("milestones", [])))
        check("updated_at refreshed", result.get("updated_at") is not None)
    except Exception as e:
        check("Advance to visit_scheduled", False, str(e))

    # Invalid jump — try to skip arrived_on_site
    try:
        advance_milestone(
            application_id="LRMIS-T6-0001",
            milestone="survey_started",  # skips arrived_on_site
            by="SURV-B2",
        )
        check("Reject milestone jump (visit_scheduled → survey_started)", False,
              "should have raised")
    except ValueError as e:
        check("Reject milestone jump (visit_scheduled → survey_started)", True, str(e)[:70])

    # Advance sequentially to arrived_on_site
    try:
        r2 = advance_milestone("LRMIS-T6-0001", "arrived_on_site", "SURV-B2")
        check("Advance to arrived_on_site — OK", r2.get("status") == "arrived_on_site")
    except Exception as e:
        check("Advance to arrived_on_site", False, str(e))

    # survey_started → survey_completed → report_uploaded
    advance_milestone("LRMIS-T6-0001", "survey_started", "SURV-B2")
    advance_milestone("LRMIS-T6-0001", "survey_completed", "SURV-B2")
    r_report = advance_milestone("LRMIS-T6-0001", "report_uploaded", "SURV-B2")
    check("report_uploaded milestone sets flag=True", r_report.get("report_uploaded") is True)

    # No task exists for unknown application
    try:
        advance_milestone("LRMIS-T6-NONE", "visit_scheduled", "someone")
        check("No task → error", False)
    except ValueError as e:
        check("No task → error returned", True, str(e)[:60])


# ── Summary ───────────────────────────────────────────────────────────────────

def run_all():
    print("\n" + "=" * 60)
    print("  Student 3 Backend - Mongomock Verification Suite")
    print("=" * 60)

    test_task1_schema_validation()
    test_task2_create_staff()
    test_task3_staff_profile()
    test_task4_survey_task_schemas()
    test_task5_assignment_scoring()
    test_task6_auto_assign()
    test_task7_duplicate_prevention()
    test_task8_manual_reassign()
    test_task9_surveyor_tasks()
    test_task10_survey_milestone()

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
