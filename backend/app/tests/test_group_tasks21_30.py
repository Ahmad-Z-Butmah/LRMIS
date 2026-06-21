"""
test_group_tasks21_30.py — Group Backend Tests: Tasks 21–30

Tests cover:
  Task 21: Spatial filter params on all 5 geofeed endpoints
  Task 22: Nearby endpoint — $geoNear not supported by mongomock (documented fallback)
  Task 23: GET /analytics/export/applications.csv → text/csv, correct columns
  Task 24: GET /analytics/export/surveyors.csv → text/csv, correct columns
  Task 25: GET /analytics/export/management-report → JSON with all required keys
  Task 28: Seed data structure — verifies all required collections are seeded
  Task 29: Indexes — verifies create_indexes() runs without error
  Task 30: --reset flag — verifies reset_demo_collections() drops collections

Run from the backend/ directory:
    pytest app/tests/test_group_tasks21_30.py -v

NOTE (Task 22): $geoNear is NOT supported by mongomock. The nearby endpoint is
tested for graceful fallback — it must return a valid FeatureCollection (possibly
empty) with an 'error' or 'note' key, not raise an unhandled exception.
"""

import csv
import io
import sys
import types
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

# ── Mongomock patch — must run before importing anything from app.* ───────────
import mongomock

_fake_client = mongomock.MongoClient()
_fake_db = _fake_client["lrmis_test"]

_db_module = types.ModuleType("app.database")
_db_module.db = _fake_db
sys.modules["app.database"] = _db_module


# ── Now safe to import app modules ────────────────────────────────────────────
from fastapi.testclient import TestClient

from app.main import app  # noqa: E402

client = TestClient(app)

# ── Helpers ───────────────────────────────────────────────────────────────────

def _dt(offset_days: int = 0) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=offset_days)


def _polygon(base_lng: float, base_lat: float) -> dict:
    d = 0.01
    return {
        "type": "Polygon",
        "coordinates": [[
            [base_lng,     base_lat],
            [base_lng + d, base_lat],
            [base_lng + d, base_lat + d],
            [base_lng,     base_lat + d],
            [base_lng,     base_lat],
        ]],
    }


def _seed_parcels():
    _fake_db["parcels"].drop()
    _fake_db["parcels"].insert_many([
        {"parcel_code": "P-001", "parcel_number": "P-001", "zone_id": "Z-WEST",
         "geometry": _polygon(35.18, 31.98)},
        {"parcel_code": "P-002", "parcel_number": "P-002", "zone_id": "Z-WEST",
         "geometry": _polygon(35.20, 31.97)},
        {"parcel_code": "P-003", "parcel_number": "P-003", "zone_id": "Z-EAST",
         "geometry": _polygon(35.22, 31.96)},
    ])


def _seed_applications():
    _fake_db["applications"].drop()
    _fake_db["land_applications"].drop()
    now = _dt(0)
    apps = [
        {"application_id": "APP-001", "status": "submitted",
         "application_type": "ownership", "parcel_ref": "P-001",
         "submitted_at": _dt(10), "updated_at": _dt(10)},
        {"application_id": "APP-002", "status": "survey_required",
         "application_type": "first_registration", "parcel_ref": "P-002",
         "submitted_at": _dt(20), "updated_at": _dt(20)},
        {"application_id": "APP-003", "status": "under_objection",
         "application_type": "subdivision", "parcel_ref": "P-003",
         "submitted_at": _dt(15), "updated_at": _dt(15)},
    ]
    for a in apps:
        _fake_db["applications"].insert_one(dict(a))
        _fake_db["land_applications"].insert_one(dict(a))


def _seed_staff():
    _fake_db["staff"].drop()
    _fake_db["staff"].insert_many([
        {"staff_id": "SURV-001", "name": "Alice", "role": "surveyor",
         "workload": {"active_tasks": 2, "max_tasks": 10}},
        {"staff_id": "REG-001", "name": "Bob", "role": "registrar",
         "workload": {"active_tasks": 1, "max_tasks": 20}},
    ])


# ═══════════════════════════════════════════════════════════════════════════════
# Task 21 — Spatial filter params
# ═══════════════════════════════════════════════════════════════════════════════

class TestTask21SpatialFilters(unittest.TestCase):

    def setUp(self):
        _seed_parcels()
        _seed_applications()

    # ── /parcels ──────────────────────────────────────────────────────────────

    def test_parcels_no_filter_returns_all(self):
        r = client.get("/analytics/geofeeds/parcels")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["type"], "FeatureCollection")
        self.assertIsInstance(data["features"], list)
        self.assertGreaterEqual(len(data["features"]), 1)

    def test_parcels_zone_filter_reduces_results(self):
        r_all  = client.get("/analytics/geofeeds/parcels")
        r_west = client.get("/analytics/geofeeds/parcels?zone_id=Z-WEST")
        self.assertEqual(r_west.status_code, 200)
        all_features  = r_all.json()["features"]
        west_features = r_west.json()["features"]
        self.assertLessEqual(len(west_features), len(all_features))
        for f in west_features:
            self.assertEqual(f["properties"]["zone_id"], "Z-WEST")

    def test_parcels_unknown_zone_returns_empty(self):
        r = client.get("/analytics/geofeeds/parcels?zone_id=NONEXISTENT")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["features"], [])

    def test_parcels_dispute_state_param_accepted(self):
        r = client.get("/analytics/geofeeds/parcels?dispute_state=none")
        self.assertEqual(r.status_code, 200)
        self.assertIn("features", r.json())

    # ── /pending-applications ─────────────────────────────────────────────────

    def test_pending_apps_no_filter(self):
        r = client.get("/analytics/geofeeds/pending-applications")
        self.assertEqual(r.status_code, 200)
        self.assertIn("features", r.json())

    def test_pending_apps_zone_filter(self):
        r = client.get("/analytics/geofeeds/pending-applications?zone_id=Z-WEST")
        self.assertEqual(r.status_code, 200)
        for f in r.json()["features"]:
            self.assertEqual(f["properties"]["zone_id"], "Z-WEST")

    def test_pending_apps_application_type_filter(self):
        r = client.get("/analytics/geofeeds/pending-applications?application_type=ownership")
        self.assertEqual(r.status_code, 200)
        for f in r.json()["features"]:
            self.assertEqual(f["properties"]["status"], "submitted")  # only ownership app is submitted

    def test_pending_apps_status_filter(self):
        r = client.get("/analytics/geofeeds/pending-applications?status=submitted")
        self.assertEqual(r.status_code, 200)
        for f in r.json()["features"]:
            self.assertEqual(f["properties"]["status"], "submitted")

    def test_pending_apps_invalid_status_returns_all_pending(self):
        r_all   = client.get("/analytics/geofeeds/pending-applications")
        r_bogus = client.get("/analytics/geofeeds/pending-applications?status=approved")
        self.assertEqual(r_bogus.status_code, 200)
        # non-pending status falls back to all-pending query
        self.assertEqual(len(r_bogus.json()["features"]), len(r_all.json()["features"]))

    # ── /pending-heatmap ──────────────────────────────────────────────────────

    def test_heatmap_no_filter(self):
        r = client.get("/analytics/geofeeds/pending-heatmap")
        self.assertEqual(r.status_code, 200)
        self.assertIn("features", r.json())

    def test_heatmap_zone_filter(self):
        r = client.get("/analytics/geofeeds/pending-heatmap?zone_id=Z-WEST")
        self.assertEqual(r.status_code, 200)
        for f in r.json()["features"]:
            self.assertEqual(f["properties"]["zone_id"], "Z-WEST")

    # ── /disputed-parcels ─────────────────────────────────────────────────────

    def test_disputed_parcels_no_filter(self):
        r = client.get("/analytics/geofeeds/disputed-parcels")
        self.assertEqual(r.status_code, 200)
        self.assertIn("features", r.json())

    def test_disputed_parcels_zone_filter(self):
        r = client.get("/analytics/geofeeds/disputed-parcels?zone_id=Z-EAST")
        self.assertEqual(r.status_code, 200)
        for f in r.json()["features"]:
            self.assertIn(f["properties"]["zone_id"], ["Z-EAST", None])

    # ── /survey-tasks ─────────────────────────────────────────────────────────

    def test_survey_tasks_no_filter(self):
        r = client.get("/analytics/geofeeds/survey-tasks")
        self.assertEqual(r.status_code, 200)
        self.assertIn("features", r.json())

    def test_survey_tasks_zone_filter(self):
        r = client.get("/analytics/geofeeds/survey-tasks?zone_id=Z-NORTH")
        self.assertEqual(r.status_code, 200)
        self.assertIsInstance(r.json()["features"], list)

    def test_all_5_endpoints_accept_all_filter_params(self):
        """Smoke test: all filter params accepted without 422."""
        endpoints = [
            "/analytics/geofeeds/parcels?zone_id=Z-WEST&status=submitted&dispute_state=none",
            "/analytics/geofeeds/pending-applications?zone_id=Z-WEST&status=submitted&application_type=ownership",
            "/analytics/geofeeds/pending-heatmap?zone_id=Z-WEST&status=submitted",
            "/analytics/geofeeds/disputed-parcels?zone_id=Z-EAST&dispute_state=disputed",
            "/analytics/geofeeds/survey-tasks?zone_id=Z-NORTH&status=assigned",
        ]
        for url in endpoints:
            r = client.get(url)
            self.assertEqual(r.status_code, 200, msg=f"422 on {url}")


# ═══════════════════════════════════════════════════════════════════════════════
# Task 22 — Nearby endpoint ($geoNear fallback under mongomock)
# ═══════════════════════════════════════════════════════════════════════════════

class TestTask22Nearby(unittest.TestCase):

    def setUp(self):
        _seed_parcels()

    def test_nearby_endpoint_exists_and_returns_200(self):
        """
        /nearby must exist and return 200.
        Under mongomock $geoNear is not supported — the endpoint must return a
        valid FeatureCollection (empty) with an 'error' key, not crash with 500.
        """
        r = client.get("/analytics/geofeeds/nearby?lng=35.18&lat=31.98&max_distance=5000")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["type"], "FeatureCollection")
        self.assertIsInstance(data["features"], list)
        # Under mongomock the result is empty with an error/note key
        if not data["features"]:
            self.assertTrue(
                "error" in data or "note" in data,
                "Empty features under mongomock should include 'error' or 'note' key"
            )

    def test_nearby_requires_lng_and_lat(self):
        """Missing required params → 422."""
        r = client.get("/analytics/geofeeds/nearby?lng=35.18")
        self.assertEqual(r.status_code, 422)

    def test_nearby_max_distance_default(self):
        """max_distance defaults to 1000 — endpoint should still return 200."""
        r = client.get("/analytics/geofeeds/nearby?lng=35.18&lat=31.98")
        self.assertEqual(r.status_code, 200)

    def test_nearby_response_shape(self):
        r = client.get("/analytics/geofeeds/nearby?lng=35.0&lat=31.9&max_distance=100")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("type", data)
        self.assertIn("features", data)


# ═══════════════════════════════════════════════════════════════════════════════
# Task 23 — CSV export: applications.csv
# ═══════════════════════════════════════════════════════════════════════════════

class TestTask23CSVApplications(unittest.TestCase):

    def setUp(self):
        _seed_applications()

    def test_returns_200(self):
        r = client.get("/analytics/export/applications.csv")
        self.assertEqual(r.status_code, 200)

    def test_content_type_is_csv(self):
        r = client.get("/analytics/export/applications.csv")
        self.assertIn("text/csv", r.headers["content-type"])

    def test_content_disposition_attachment(self):
        r = client.get("/analytics/export/applications.csv")
        cd = r.headers.get("content-disposition", "")
        self.assertIn("attachment", cd)
        self.assertIn("applications.csv", cd)

    def test_csv_has_correct_columns(self):
        r = client.get("/analytics/export/applications.csv")
        reader = csv.DictReader(io.StringIO(r.text))
        expected_cols = {
            "application_id", "status", "application_type", "parcel_number",
            "zone_id", "submitted_at", "updated_at", "applicant_ref", "priority",
        }
        self.assertEqual(set(reader.fieldnames), expected_cols)

    def test_csv_has_data_rows(self):
        r = client.get("/analytics/export/applications.csv")
        reader = csv.DictReader(io.StringIO(r.text))
        rows = list(reader)
        self.assertGreater(len(rows), 0)

    def test_csv_application_id_column_populated(self):
        r = client.get("/analytics/export/applications.csv")
        reader = csv.DictReader(io.StringIO(r.text))
        for row in reader:
            self.assertNotEqual(row["application_id"], "")


# ═══════════════════════════════════════════════════════════════════════════════
# Task 24 — CSV export: surveyors.csv
# ═══════════════════════════════════════════════════════════════════════════════

class TestTask24CSVSurveyors(unittest.TestCase):

    def setUp(self):
        _seed_staff()
        _seed_applications()
        _seed_parcels()

    def test_returns_200(self):
        r = client.get("/analytics/export/surveyors.csv")
        self.assertEqual(r.status_code, 200)

    def test_content_type_is_csv(self):
        r = client.get("/analytics/export/surveyors.csv")
        self.assertIn("text/csv", r.headers["content-type"])

    def test_content_disposition_attachment(self):
        r = client.get("/analytics/export/surveyors.csv")
        cd = r.headers.get("content-disposition", "")
        self.assertIn("attachment", cd)
        self.assertIn("surveyors.csv", cd)

    def test_csv_has_correct_columns(self):
        r = client.get("/analytics/export/surveyors.csv")
        reader = csv.DictReader(io.StringIO(r.text))
        expected_cols = {
            "surveyor_id", "name", "active_tasks", "completed_tasks",
            "max_tasks", "workload_percentage",
        }
        self.assertEqual(set(reader.fieldnames), expected_cols)

    def test_csv_is_valid_even_with_no_surveyors(self):
        _fake_db["staff"].drop()
        r = client.get("/analytics/export/surveyors.csv")
        self.assertEqual(r.status_code, 200)
        reader = csv.DictReader(io.StringIO(r.text))
        self.assertIsNotNone(reader.fieldnames)


# ═══════════════════════════════════════════════════════════════════════════════
# Task 25 — Management report JSON
# ═══════════════════════════════════════════════════════════════════════════════

class TestTask25ManagementReport(unittest.TestCase):

    def setUp(self):
        _seed_applications()
        _seed_parcels()
        _seed_staff()

    def test_returns_200(self):
        r = client.get("/analytics/export/management-report")
        self.assertEqual(r.status_code, 200)

    def test_response_is_json(self):
        r = client.get("/analytics/export/management-report")
        data = r.json()
        self.assertIsInstance(data, dict)

    def test_required_top_level_keys(self):
        r = client.get("/analytics/export/management-report")
        data = r.json()
        required_keys = {
            "report_type", "generated_at", "threshold_days",
            "kpis", "applications_by_status", "applications_by_type",
            "applications_by_zone", "processing_time",
            "surveyors", "registrars", "delayed_applications",
        }
        for key in required_keys:
            self.assertIn(key, data, msg=f"Missing key: {key}")

    def test_report_type_value(self):
        r = client.get("/analytics/export/management-report")
        self.assertEqual(r.json()["report_type"], "management_summary")

    def test_generated_at_is_iso_string(self):
        r = client.get("/analytics/export/management-report")
        generated_at = r.json()["generated_at"]
        self.assertIsInstance(generated_at, str)
        datetime.fromisoformat(generated_at.replace("Z", "+00:00"))

    def test_threshold_days_default_30(self):
        r = client.get("/analytics/export/management-report")
        self.assertEqual(r.json()["threshold_days"], 30)

    def test_threshold_days_custom(self):
        r = client.get("/analytics/export/management-report?threshold_days=14")
        self.assertEqual(r.json()["threshold_days"], 14)

    def test_surveyors_has_total_key(self):
        r = client.get("/analytics/export/management-report")
        surveyors = r.json()["surveyors"]
        self.assertIn("total", surveyors)
        self.assertIn("surveyors", surveyors)

    def test_registrars_has_total_key(self):
        r = client.get("/analytics/export/management-report")
        registrars = r.json()["registrars"]
        self.assertIn("total", registrars)
        self.assertIn("registrars", registrars)

    def test_kpis_contains_required_fields(self):
        r = client.get("/analytics/export/management-report")
        kpis = r.json()["kpis"]
        for field in ["total_applications", "pending_applications", "approved_applications"]:
            self.assertIn(field, kpis, msg=f"KPI field missing: {field}")

    def test_delayed_applications_is_list(self):
        r = client.get("/analytics/export/management-report")
        self.assertIsInstance(r.json()["delayed_applications"], list)


# ═══════════════════════════════════════════════════════════════════════════════
# Task 28 — Seed data structure
# ═══════════════════════════════════════════════════════════════════════════════

class TestTask28SeedStructure(unittest.TestCase):
    """
    Verifies seed data constants have the required counts and fields.
    Does NOT run against real MongoDB — checks the seed module's data structures.
    """

    def setUp(self):
        from app.seed import seed_data as sd
        self.sd = sd

    def test_has_8_parcels(self):
        self.assertEqual(len(self.sd.PARCELS), 8)

    def test_has_10_applications(self):
        self.assertEqual(len(self.sd.APPLICATIONS), 10)

    def test_has_5_applicants(self):
        self.assertEqual(len(self.sd.APPLICANTS), 5)

    def test_has_4_staff_members(self):
        self.assertEqual(len(self.sd.STAFF_MEMBERS), 4)

    def test_has_2_certificates(self):
        self.assertEqual(len(self.sd.CERTIFICATES), 2)

    def test_has_5_documents(self):
        self.assertEqual(len(self.sd.APPLICATION_DOCUMENTS), 5)

    def test_has_3_comments(self):
        self.assertEqual(len(self.sd.COMMENTS), 3)

    def test_has_2_objections(self):
        self.assertEqual(len(self.sd.OBJECTIONS), 2)

    def test_has_3_survey_tasks(self):
        self.assertEqual(len(self.sd.SURVEY_TASKS), 3)

    def test_has_2_survey_reports(self):
        self.assertEqual(len(self.sd.SURVEY_REPORTS), 2)

    def test_has_notification_logs(self):
        self.assertGreater(len(self.sd.NOTIFICATION_LOGS), 0)

    def test_parcels_have_geometry(self):
        for p in self.sd.PARCELS:
            self.assertIn("geometry", p)
            self.assertEqual(p["geometry"]["type"], "Polygon")

    def test_applications_cover_multiple_types(self):
        types = {a["application_type"] for a in self.sd.APPLICATIONS}
        self.assertGreater(len(types), 1, "Should have multiple application_types")

    def test_applications_cover_multiple_statuses(self):
        statuses = {a["status"] for a in self.sd.APPLICATIONS}
        expected = {"submitted", "approved", "certificate_issued", "rejected"}
        self.assertTrue(expected.issubset(statuses))

    def test_at_least_one_delayed_application_in_non_terminal_status(self):
        terminal = {"approved", "certificate_issued", "closed", "rejected"}
        delayed = [
            a for a in self.sd.APPLICATIONS
            if a["status"] not in terminal
        ]
        self.assertGreater(len(delayed), 0)
        oldest = max(
            (datetime.now(timezone.utc) - a["submitted_at"].replace(tzinfo=timezone.utc)
             if a["submitted_at"].tzinfo is None
             else datetime.now(timezone.utc) - a["submitted_at"]).days
            for a in delayed
        )
        self.assertGreater(oldest, 7, "Should have at least one application delayed > 7 days")

    def test_staff_roles_include_surveyor_and_registrar(self):
        roles = {s["role"] for s in self.sd.STAFF_MEMBERS}
        self.assertIn("surveyor", roles)
        self.assertIn("registrar", roles)

    def test_demo_collections_list_defined(self):
        self.assertIsInstance(self.sd.DEMO_COLLECTIONS, list)
        self.assertGreater(len(self.sd.DEMO_COLLECTIONS), 5)


# ═══════════════════════════════════════════════════════════════════════════════
# Task 29 — Indexes (run create_indexes on mongomock without raising)
# ═══════════════════════════════════════════════════════════════════════════════

class TestTask29Indexes(unittest.TestCase):

    def test_create_indexes_runs_without_error(self):
        """
        create_indexes() must not raise under mongomock.
        GEOSPHERE (2dsphere) index creation is silently ignored by mongomock.
        """
        from app.seed import seed_data as sd
        original_db = sd.db
        try:
            sd.db = _fake_db
            # Should not raise
            sd.create_indexes()
        except Exception as exc:
            self.fail(f"create_indexes() raised: {exc}")
        finally:
            sd.db = original_db

    def test_create_indexes_idempotent(self):
        """Running create_indexes() twice must not raise."""
        from app.seed import seed_data as sd
        original_db = sd.db
        try:
            sd.db = _fake_db
            sd.create_indexes()
            sd.create_indexes()
        except Exception as exc:
            self.fail(f"Second create_indexes() call raised: {exc}")
        finally:
            sd.db = original_db


# ═══════════════════════════════════════════════════════════════════════════════
# Task 30 — --reset flag
# ═══════════════════════════════════════════════════════════════════════════════

class TestTask30Reset(unittest.TestCase):

    def test_reset_demo_collections_drops_all_listed(self):
        """
        reset_demo_collections() must call drop() on every collection in
        DEMO_COLLECTIONS and not raise.
        """
        from app.seed import seed_data as sd
        original_db = sd.db

        # Insert something in a couple of collections first
        _fake_db["applicants"].insert_one({"applicant_id": "TEST-RESET"})
        _fake_db["parcels"].insert_one({"parcel_code": "RESET-TEST"})

        try:
            sd.db = _fake_db
            sd.reset_demo_collections()
            # After reset, seeded item should be gone
            self.assertIsNone(
                _fake_db["applicants"].find_one({"applicant_id": "TEST-RESET"})
            )
        except Exception as exc:
            self.fail(f"reset_demo_collections() raised: {exc}")
        finally:
            sd.db = original_db

    def test_reset_then_run_seeds_fresh_data(self):
        """After reset, run() should re-populate collections."""
        from app.seed import seed_data as sd
        original_db = sd.db
        try:
            sd.db = _fake_db
            sd.reset_demo_collections()
            sd.run()
            self.assertGreater(_fake_db["parcels"].count_documents({}), 0)
            self.assertGreater(_fake_db["applications"].count_documents({}), 0)
        except Exception as exc:
            self.fail(f"reset + run raised: {exc}")
        finally:
            sd.db = original_db

    def test_demo_collections_constant_exists(self):
        from app.seed import seed_data as sd
        self.assertTrue(hasattr(sd, "DEMO_COLLECTIONS"))
        self.assertIn("parcels", sd.DEMO_COLLECTIONS)
        self.assertIn("land_applications", sd.DEMO_COLLECTIONS)
        self.assertIn("applications", sd.DEMO_COLLECTIONS)

    def test_reset_function_defined(self):
        from app.seed import seed_data as sd
        self.assertTrue(callable(getattr(sd, "reset_demo_collections", None)))


# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    unittest.main()
