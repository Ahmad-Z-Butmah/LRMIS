"""
LRMIS — Unified Seed Script (Tasks 16, 17, 28, 29, 30)

Creates indexes then inserts demo data.  Safe to run multiple times.

Usage (from the backend/ directory):
    python -m app.seed.seed_data            # seed all collections
    python -m app.seed.seed_data --reset    # drop demo collections then reseed

Collection naming note
----------------------
The professor's specification uses the collection name  'land_applications'.
The existing service layer uses 'applications'.
This script creates the professor-required indexes on 'land_applications' AND
seeds that collection, while also maintaining the 'applications' collection
(with root-level timestamp aliases) so existing API endpoints continue to work.

Task 28 additions: applicants (5), staff_members (4), parcels (8 total),
land_applications (10 total), application_documents (5), comments (3),
objections (2), survey_tasks (3), survey_reports (2), notification_logs (4).

Task 29: idempotent indexes for all 11 collections.
Task 30: --reset flag drops demo collections then reseeds; prints counts summary.
"""

import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from pymongo import ASCENDING, GEOSPHERE, MongoClient

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "lrmis_db")

_client = MongoClient(MONGO_URL)
db = _client[DB_NAME]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _dt(offset_days: int = 0) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=offset_days)


def _workflow(status: str) -> dict:
    _next = {
        "submitted":          ["pre_checked", "missing_documents", "on_hold", "rejected"],
        "pre_checked":        ["survey_required", "missing_documents", "on_hold", "rejected"],
        "missing_documents":  ["pre_checked", "rejected"],
        "on_hold":            ["pre_checked", "rejected"],
        "survey_required":    ["surveyed", "on_hold", "rejected"],
        "surveyed":           ["legal_review", "on_hold", "rejected"],
        "legal_review":       ["approved", "under_objection", "rejected"],
        "under_objection":    ["legal_review", "rejected"],
        "approved":           ["certificate_issued"],
        "certificate_issued": ["closed"],
        "closed":             [],
        "rejected":           [],
    }
    return {"current_state": status, "allowed_next": _next.get(status, [])}


def _perf(event_type, actor_type, actor_id, meta, offset_days=0):
    return {
        "type": event_type,
        "by": {"actor_type": actor_type, "actor_id": actor_id},
        "at": _dt(offset_days),
        "meta": meta,
    }


def _upsert(collection: str, key: str, doc: dict) -> None:
    db[collection].replace_one({key: doc[key]}, doc, upsert=True)


# ---------------------------------------------------------------------------
# Task 16 / 29 — Indexes (idempotent — create_index is a no-op if exists)
# ---------------------------------------------------------------------------

def create_indexes() -> None:
    print("[indexes] Creating indexes ...")

    # ── PROFESSOR-REQUIRED INDEXES ────────────────────────────────────────────

    # land_applications
    db["land_applications"].create_index("application_id", unique=True)
    db["land_applications"].create_index("status")
    db["land_applications"].create_index("application_type")
    db["land_applications"].create_index("parcel_ref.parcel_number")
    db["land_applications"].create_index("parcel_ref.zone_id")
    db["land_applications"].create_index("timestamps.submitted_at")

    # parcels — 2dsphere for $geoNear queries (Task 22 / 29)
    db["parcels"].create_index("parcel_code", unique=True)
    db["parcels"].create_index([("geometry", GEOSPHERE)])

    # certificates
    db["certificates"].create_index("certificate_id", unique=True)

    # ── COMPATIBILITY INDEXES ─────────────────────────────────────────────────

    db["applications"].create_index("application_id", unique=True)
    db["applications"].create_index("status")
    db["applications"].create_index("application_type")
    db["applications"].create_index("parcel_ref.parcel_number")
    db["applications"].create_index("parcel_ref.zone_id")
    db["applications"].create_index("submitted_at")

    db["parcels"].create_index("parcel_number", unique=True)
    db["parcels"].create_index("zone_id")

    db["certificates"].create_index("application_id")

    # ── TASK 28/29 — NEW COLLECTION INDEXES ──────────────────────────────────

    # applicants
    db["applicants"].create_index("applicant_id", unique=True)
    db["applicants"].create_index("national_id")

    # staff_members
    db["staff_members"].create_index("staff_id", unique=True)
    db["staff_members"].create_index("role")
    db["staff_members"].create_index("staff_code", unique=True)

    # survey_tasks
    db["survey_tasks"].create_index("task_id", unique=True)
    db["survey_tasks"].create_index("application_id")
    db["survey_tasks"].create_index("status")
    db["survey_tasks"].create_index("assigned_surveyor_id")

    # survey_reports
    db["survey_reports"].create_index("report_id", unique=True)
    db["survey_reports"].create_index("task_id")
    db["survey_reports"].create_index("application_id")

    # application_documents
    db["application_documents"].create_index("document_id", unique=True)
    db["application_documents"].create_index("application_id")

    # comments
    db["comments"].create_index("comment_id", unique=True)
    db["comments"].create_index("application_id")

    # objections
    db["objections"].create_index("objection_id", unique=True)
    db["objections"].create_index("application_id")

    # performance_logs + audit_logs + notification_logs
    db["performance_logs"].create_index("application_id", unique=True)
    db["audit_logs"].create_index(
        [("application_id", ASCENDING), ("timestamp", ASCENDING)]
    )
    db["notification_logs"].create_index("application_id")
    db["notification_logs"].create_index("recipient_id")

    # notes + documents (legacy)
    db["notes"].create_index("application_id")
    db["documents"].create_index(
        [("application_id", ASCENDING), ("name", ASCENDING)]
    )

    print("[indexes] Done.")


# ---------------------------------------------------------------------------
# Task 17 / 28 — Parcels (8 total)
# ---------------------------------------------------------------------------

PARCELS = [
    {
        "parcel_code":   "P-001",
        "parcel_number": "P-001",
        "block_number":  "B-10",
        "basin_number":  "BA-03",
        "zone_id":       "Z-WEST",
        "area_sqm":      1200.0,
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [35.180, 31.980],
                [35.190, 31.980],
                [35.190, 31.990],
                [35.180, 31.990],
                [35.180, 31.980],
            ]],
        },
    },
    {
        "parcel_code":   "P-002",
        "parcel_number": "P-002",
        "block_number":  "B-11",
        "basin_number":  "BA-03",
        "zone_id":       "Z-WEST",
        "area_sqm":      900.0,
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [35.200, 31.970],
                [35.210, 31.970],
                [35.210, 31.980],
                [35.200, 31.980],
                [35.200, 31.970],
            ]],
        },
    },
    {
        "parcel_code":   "P-003",
        "parcel_number": "P-003",
        "block_number":  "B-12",
        "basin_number":  "BA-04",
        "zone_id":       "Z-EAST",
        "area_sqm":      1500.0,
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [35.220, 31.960],
                [35.230, 31.960],
                [35.230, 31.970],
                [35.220, 31.970],
                [35.220, 31.960],
            ]],
        },
    },
    {
        "parcel_code":   "P-004",
        "parcel_number": "P-004",
        "block_number":  "B-13",
        "basin_number":  "BA-04",
        "zone_id":       "Z-EAST",
        "area_sqm":      800.0,
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [35.240, 31.950],
                [35.250, 31.950],
                [35.250, 31.960],
                [35.240, 31.960],
                [35.240, 31.950],
            ]],
        },
    },
    {
        "parcel_code":   "P-005",
        "parcel_number": "P-005",
        "block_number":  "B-14",
        "basin_number":  "BA-05",
        "zone_id":       "Z-NORTH",
        "area_sqm":      2000.0,
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [35.260, 31.940],
                [35.270, 31.940],
                [35.270, 31.950],
                [35.260, 31.950],
                [35.260, 31.940],
            ]],
        },
    },
    # Task 28 — 3 additional parcels (P-006 to P-008)
    {
        "parcel_code":   "P-006",
        "parcel_number": "P-006",
        "block_number":  "B-20",
        "basin_number":  "BA-06",
        "zone_id":       "Z-SOUTH",
        "area_sqm":      1100.0,
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [35.170, 31.920],
                [35.180, 31.920],
                [35.180, 31.930],
                [35.170, 31.930],
                [35.170, 31.920],
            ]],
        },
    },
    {
        "parcel_code":   "P-007",
        "parcel_number": "P-007",
        "block_number":  "B-21",
        "basin_number":  "BA-06",
        "zone_id":       "Z-NORTH",
        "area_sqm":      1750.0,
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [35.280, 31.955],
                [35.290, 31.955],
                [35.290, 31.965],
                [35.280, 31.965],
                [35.280, 31.955],
            ]],
        },
    },
    {
        "parcel_code":   "P-008",
        "parcel_number": "P-008",
        "block_number":  "B-22",
        "basin_number":  "BA-07",
        "zone_id":       "Z-EAST",
        "area_sqm":      650.0,
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [35.235, 31.945],
                [35.245, 31.945],
                [35.245, 31.955],
                [35.235, 31.955],
                [35.235, 31.945],
            ]],
        },
    },
]


# ---------------------------------------------------------------------------
# Task 17 / 28 — Applications (10 total across 6 application types)
# ---------------------------------------------------------------------------

def _app(app_id, applicant, parcel, docs, status, app_type, days_old,
         days_updated=None, extra=None):
    t_created   = _dt(days_old)
    t_updated   = _dt(days_updated if days_updated is not None else days_old)
    t_submitted = _dt(days_old)
    base = {
        "application_id":     app_id,
        "application_type":   app_type,
        "applicant_ref":      applicant,
        "parcel_ref":         parcel,
        "required_documents": docs,
        "status":             status,
        "workflow":           _workflow(status),
        "timestamps": {
            "submitted_at": t_submitted,
            "created_at":   t_created,
            "updated_at":   t_updated,
        },
        "submitted_at": t_submitted,
        "created_at":   t_created,
        "updated_at":   t_updated,
    }
    if extra:
        base.update(extra)
    return base


APPLICATIONS = [
    # 1 — submitted (ownership, 10 days — delayed > 7 days)
    _app("LRMIS-2026-0001", "APPL-001", "P-001",
         ["national_id", "ownership_deed"],
         "submitted", "ownership", days_old=10),

    # 2 — pre_checked (ownership, 20 days)
    _app("LRMIS-2026-0002", "APPL-002", "P-002",
         ["national_id", "ownership_deed", "site_plan"],
         "pre_checked", "ownership", days_old=20, days_updated=8),

    # 3 — survey_required (ownership, 30 days — delayed > 7 days)
    _app("LRMIS-2026-0003", "APPL-003", "P-003",
         ["national_id", "ownership_deed"],
         "survey_required", "ownership", days_old=30, days_updated=15),

    # 4 — approved (ownership, 40 days)
    _app("LRMIS-2026-0004", "APPL-004", "P-004",
         ["national_id", "ownership_deed"],
         "approved", "ownership", days_old=40, days_updated=5,
         extra={"legal_review_completed": True}),

    # 5 — certificate_issued (ownership, 60 days)
    _app("LRMIS-2026-0005", "APPL-005", "P-005",
         ["national_id", "ownership_deed"],
         "certificate_issued", "ownership", days_old=60, days_updated=2,
         extra={"legal_review_completed": True}),

    # 6 — rejected (ownership, 50 days)
    _app("LRMIS-2026-0006", "APPL-006", "P-001",
         ["national_id"],
         "rejected", "ownership", days_old=50, days_updated=3,
         extra={
             "rejection_reason": "Ownership document is invalid.",
             "rejected_by": "REG-001",
             "rejected_at": _dt(3),
         }),

    # 7 — first_registration, submitted, 15 days — delayed > 7 days (Task 28)
    _app("LRMIS-2026-0007", "APPL-001", "P-006",
         ["national_id", "birth_certificate", "land_survey"],
         "submitted", "first_registration", days_old=15, days_updated=15),

    # 8 — ownership_transfer, survey_required, 45 days — significantly delayed (Task 28)
    _app("LRMIS-2026-0008", "APPL-002", "P-007",
         ["national_id", "transfer_deed", "seller_id"],
         "survey_required", "ownership_transfer", days_old=45, days_updated=20),

    # 9 — subdivision, under_objection, 20 days (Task 28)
    _app("LRMIS-2026-0009", "APPL-003", "P-008",
         ["national_id", "subdivision_plan"],
         "under_objection", "subdivision", days_old=20, days_updated=5),

    # 10 — inheritance, legal_review, 8 days (Task 28)
    _app("LRMIS-2026-0010", "APPL-004", "P-003",
         ["national_id", "death_certificate", "inheritance_document"],
         "legal_review", "inheritance", days_old=8, days_updated=2),
]


# ---------------------------------------------------------------------------
# Task 28 — Applicants (5)
# ---------------------------------------------------------------------------

APPLICANTS = [
    {
        "applicant_id":  "APPL-001",
        "full_name":     "Ahmad Khalil",
        "national_id":   "900512345",
        "email":         "ahmad.khalil@example.ps",
        "phone":         "+970599001001",
        "address":       "Birzeit, West Bank",
        "created_at":    _dt(120),
    },
    {
        "applicant_id":  "APPL-002",
        "full_name":     "Nour Ibrahim",
        "national_id":   "870634512",
        "email":         "nour.ibrahim@example.ps",
        "phone":         "+970599001002",
        "address":       "Ramallah, West Bank",
        "created_at":    _dt(100),
    },
    {
        "applicant_id":  "APPL-003",
        "full_name":     "Fatima Hassan",
        "national_id":   "950123456",
        "email":         "fatima.hassan@example.ps",
        "phone":         "+970599001003",
        "address":       "Nablus, West Bank",
        "created_at":    _dt(90),
    },
    {
        "applicant_id":  "APPL-004",
        "full_name":     "Omar Saleh",
        "national_id":   "880765432",
        "email":         "omar.saleh@example.ps",
        "phone":         "+970599001004",
        "address":       "Jericho, West Bank",
        "created_at":    _dt(80),
    },
    {
        "applicant_id":  "APPL-005",
        "full_name":     "Layla Abu Zaid",
        "national_id":   "920345678",
        "email":         "layla.abuzaid@example.ps",
        "phone":         "+970599001005",
        "address":       "Hebron, West Bank",
        "created_at":    _dt(70),
    },
]


# ---------------------------------------------------------------------------
# Task 28 — Staff Members (4: 2 surveyors + 2 registrars)
# ---------------------------------------------------------------------------

STAFF_MEMBERS = [
    {
        "staff_id":    "SURV-001",
        "staff_code":  "SURV-001",
        "name":        "Yousef Nasser",
        "role":        "surveyor",
        "department":  "Cadastral Survey",
        "skills":      ["boundary_survey", "gps_mapping"],
        "coverage":    {"zone_ids": ["Z-WEST", "Z-EAST"], "geo_fence": None},
        "workload":    {"active_tasks": 2, "max_tasks": 10},
        "contacts":    {"email": "yousef.nasser@lrmis.ps", "phone": "+970599200001"},
        "created_at":  _dt(200),
    },
    {
        "staff_id":    "SURV-002",
        "staff_code":  "SURV-002",
        "name":        "Rania Mustafa",
        "role":        "surveyor",
        "department":  "Cadastral Survey",
        "skills":      ["aerial_survey", "boundary_survey"],
        "coverage":    {"zone_ids": ["Z-NORTH", "Z-SOUTH"], "geo_fence": None},
        "workload":    {"active_tasks": 1, "max_tasks": 10},
        "contacts":    {"email": "rania.mustafa@lrmis.ps", "phone": "+970599200002"},
        "created_at":  _dt(180),
    },
    {
        "staff_id":    "REG-001",
        "staff_code":  "REG-001",
        "name":        "Khalid Barakat",
        "role":        "registrar",
        "department":  "Land Registration",
        "skills":      ["legal_review", "certificate_issuance"],
        "coverage":    {"zone_ids": [], "geo_fence": None},
        "workload":    {"active_tasks": 3, "max_tasks": 20},
        "contacts":    {"email": "khalid.barakat@lrmis.ps", "phone": "+970599300001"},
        "created_at":  _dt(365),
    },
    {
        "staff_id":    "REG-002",
        "staff_code":  "REG-002",
        "name":        "Samira Odeh",
        "role":        "registrar",
        "department":  "Land Registration",
        "skills":      ["legal_review", "objection_handling"],
        "coverage":    {"zone_ids": [], "geo_fence": None},
        "workload":    {"active_tasks": 2, "max_tasks": 20},
        "contacts":    {"email": "samira.odeh@lrmis.ps", "phone": "+970599300002"},
        "created_at":  _dt(300),
    },
]


# ---------------------------------------------------------------------------
# Task 28 — Certificates (2 — unchanged from Task 17)
# ---------------------------------------------------------------------------

CERTIFICATES = [
    {
        "certificate_id":         "CERT-2026-0001",
        "application_id":         "LRMIS-2026-0005",
        "applicant_ref":          "APPL-005",
        "parcel_id":              "P-005",
        "certificate_type":       "ownership",
        "status":                 "issued",
        "issued_to": {
            "full_name":   "Ahmad Khalil",
            "national_id": "900512345",
            "address":     "Birzeit, West Bank",
        },
        "issued_at":              _dt(2),
        "issued_by":              "REG-001",
        "qr_code_url":            "/certificates/CERT-2026-0001/qr",
        "digital_signature_stub": "SIG-CERT-2026-0001-20260619",
    },
    {
        "certificate_id":         "CERT-2026-0002",
        "application_id":         "LRMIS-2026-0004",
        "applicant_ref":          "APPL-004",
        "parcel_id":              "P-004",
        "certificate_type":       "ownership",
        "status":                 "issued",
        "issued_to": {
            "full_name":   "Nour Ibrahim",
            "national_id": "870634512",
            "address":     "Ramallah, West Bank",
        },
        "issued_at":              _dt(4),
        "issued_by":              "REG-002",
        "qr_code_url":            "/certificates/CERT-2026-0002/qr",
        "digital_signature_stub": "SIG-CERT-2026-0002-20260617",
    },
]


# ---------------------------------------------------------------------------
# Task 28 — Application Documents (5)
# ---------------------------------------------------------------------------

APPLICATION_DOCUMENTS = [
    {
        "document_id":    "DOC-001",
        "application_id": "LRMIS-2026-0001",
        "name":           "national_id",
        "file_url":       "/docs/LRMIS-2026-0001/national_id.pdf",
        "uploaded_at":    _dt(10),
        "verified":       True,
    },
    {
        "document_id":    "DOC-002",
        "application_id": "LRMIS-2026-0001",
        "name":           "ownership_deed",
        "file_url":       "/docs/LRMIS-2026-0001/ownership_deed.pdf",
        "uploaded_at":    _dt(10),
        "verified":       False,
    },
    {
        "document_id":    "DOC-003",
        "application_id": "LRMIS-2026-0003",
        "name":           "national_id",
        "file_url":       "/docs/LRMIS-2026-0003/national_id.pdf",
        "uploaded_at":    _dt(30),
        "verified":       True,
    },
    {
        "document_id":    "DOC-004",
        "application_id": "LRMIS-2026-0007",
        "name":           "land_survey",
        "file_url":       "/docs/LRMIS-2026-0007/land_survey.pdf",
        "uploaded_at":    _dt(15),
        "verified":       False,
    },
    {
        "document_id":    "DOC-005",
        "application_id": "LRMIS-2026-0009",
        "name":           "subdivision_plan",
        "file_url":       "/docs/LRMIS-2026-0009/subdivision_plan.pdf",
        "uploaded_at":    _dt(20),
        "verified":       True,
    },
]


# ---------------------------------------------------------------------------
# Task 28 — Comments (3)
# ---------------------------------------------------------------------------

COMMENTS = [
    {
        "comment_id":     "CMT-001",
        "application_id": "LRMIS-2026-0002",
        "author_id":      "REG-001",
        "author_role":    "registrar",
        "text":           "Pre-check complete. Site plan is acceptable.",
        "created_at":     _dt(8),
    },
    {
        "comment_id":     "CMT-002",
        "application_id": "LRMIS-2026-0009",
        "author_id":      "APPL-003",
        "author_role":    "applicant",
        "text":           "Submitted objection response documentation.",
        "created_at":     _dt(5),
    },
    {
        "comment_id":     "CMT-003",
        "application_id": "LRMIS-2026-0010",
        "author_id":      "REG-002",
        "author_role":    "registrar",
        "text":           "Under legal review. Inheritance documents look complete.",
        "created_at":     _dt(2),
    },
]


# ---------------------------------------------------------------------------
# Task 28 — Objections (2)
# ---------------------------------------------------------------------------

OBJECTIONS = [
    {
        "objection_id":   "OBJ-001",
        "application_id": "LRMIS-2026-0009",
        "objector_id":    "APPL-002",
        "reason":         "Boundary dispute — parcel P-008 encroaches on adjacent land.",
        "status":         "submitted",
        "submitted_at":   _dt(18),
        "resolved_at":    None,
    },
    {
        "objection_id":   "OBJ-002",
        "application_id": "LRMIS-2026-0003",
        "objector_id":    "APPL-001",
        "reason":         "Survey report contains incorrect measurements.",
        "status":         "under_review",
        "submitted_at":   _dt(25),
        "resolved_at":    None,
    },
]


# ---------------------------------------------------------------------------
# Task 28 — Survey Tasks (3)
# ---------------------------------------------------------------------------

SURVEY_TASKS = [
    {
        "task_id":              "TASK-001",
        "application_id":       "LRMIS-2026-0003",
        "assigned_surveyor_id": "SURV-001",
        "status":               "visit_scheduled",
        "priority":             "high",
        "scheduled_visit_date": (_dt(0) + timedelta(days=3)).isoformat(),
        "report_uploaded":      False,
        "milestones": {
            "assigned":          _dt(14).isoformat(),
            "visit_scheduled":   _dt(12).isoformat(),
        },
        "created_at": _dt(14),
    },
    {
        "task_id":              "TASK-002",
        "application_id":       "LRMIS-2026-0008",
        "assigned_surveyor_id": "SURV-002",
        "status":               "survey_started",
        "priority":             "high",
        "scheduled_visit_date": _dt(5).isoformat(),
        "report_uploaded":      False,
        "milestones": {
            "assigned":          _dt(40).isoformat(),
            "visit_scheduled":   _dt(35).isoformat(),
            "arrived_on_site":   _dt(30).isoformat(),
            "survey_started":    _dt(25).isoformat(),
        },
        "created_at": _dt(40),
    },
    {
        "task_id":              "TASK-003",
        "application_id":       "LRMIS-2026-0007",
        "assigned_surveyor_id": "SURV-001",
        "status":               "assigned",
        "priority":             "normal",
        "scheduled_visit_date": None,
        "report_uploaded":      False,
        "milestones": {
            "assigned": _dt(13).isoformat(),
        },
        "created_at": _dt(13),
    },
]


# ---------------------------------------------------------------------------
# Task 28 — Survey Reports (2)
# ---------------------------------------------------------------------------

SURVEY_REPORTS = [
    {
        "report_id":      "REPORT-001",
        "task_id":        "TASK-002",
        "application_id": "LRMIS-2026-0008",
        "surveyor_id":    "SURV-002",
        "status":         "draft",
        "field_notes":    "Initial survey started. GPS coordinates confirmed.",
        "measurements":   {"area_sqm": 1748.5, "perimeter_m": 168.2},
        "submitted_at":   None,
        "created_at":     _dt(20),
    },
    {
        "report_id":      "REPORT-002",
        "task_id":        "TASK-001",
        "application_id": "LRMIS-2026-0003",
        "surveyor_id":    "SURV-001",
        "status":         "pending_review",
        "field_notes":    "Site visit completed. Boundary markers confirmed with GPS.",
        "measurements":   {"area_sqm": 1498.0, "perimeter_m": 154.8},
        "submitted_at":   _dt(10),
        "created_at":     _dt(11),
    },
]


# ---------------------------------------------------------------------------
# Task 28 — Performance logs (6, one per original application)
# ---------------------------------------------------------------------------

PERFORMANCE_LOGS = [
    {
        "application_id": "LRMIS-2026-0001",
        "event_stream": [
            _perf("application_created", "applicant", "APPL-001",
                  {"parcel_ref": "P-001"}, 10),
        ],
    },
    {
        "application_id": "LRMIS-2026-0002",
        "event_stream": [
            _perf("application_created", "applicant", "APPL-002",
                  {"parcel_ref": "P-002"}, 20),
            _perf("status_changed", "staff", "REG-001",
                  {"from": "submitted", "to": "pre_checked"}, 18),
        ],
    },
    {
        "application_id": "LRMIS-2026-0003",
        "event_stream": [
            _perf("application_created", "applicant", "APPL-003",
                  {"parcel_ref": "P-003"}, 30),
            _perf("status_changed", "staff", "REG-001",
                  {"from": "submitted", "to": "pre_checked"}, 28),
            _perf("status_changed", "staff", "REG-001",
                  {"from": "pre_checked", "to": "survey_required"}, 25),
        ],
    },
    {
        "application_id": "LRMIS-2026-0004",
        "event_stream": [
            _perf("application_created", "applicant", "APPL-004",
                  {"parcel_ref": "P-004"}, 40),
            _perf("status_changed", "staff", "REG-002",
                  {"from": "submitted", "to": "pre_checked"}, 38),
            _perf("status_changed", "staff", "REG-002",
                  {"from": "pre_checked", "to": "survey_required"}, 35),
            _perf("status_changed", "staff", "SURV-001",
                  {"from": "survey_required", "to": "surveyed"}, 25),
            _perf("status_changed", "staff", "REG-001",
                  {"from": "surveyed", "to": "legal_review"}, 15),
            _perf("status_changed", "staff", "REG-001",
                  {"from": "legal_review", "to": "approved"}, 5),
            _perf("certificate_issued", "staff", "REG-002",
                  {"certificate_id": "CERT-2026-0002"}, 4),
        ],
    },
    {
        "application_id": "LRMIS-2026-0005",
        "event_stream": [
            _perf("application_created", "applicant", "APPL-005",
                  {"parcel_ref": "P-005"}, 60),
            _perf("status_changed", "staff", "REG-001",
                  {"from": "submitted", "to": "pre_checked"}, 58),
            _perf("status_changed", "staff", "REG-001",
                  {"from": "pre_checked", "to": "survey_required"}, 55),
            _perf("status_changed", "staff", "SURV-002",
                  {"from": "survey_required", "to": "surveyed"}, 45),
            _perf("status_changed", "staff", "REG-002",
                  {"from": "surveyed", "to": "legal_review"}, 30),
            _perf("status_changed", "staff", "REG-001",
                  {"from": "legal_review", "to": "approved"}, 10),
            _perf("certificate_issued", "staff", "REG-001",
                  {"certificate_id": "CERT-2026-0001"}, 2),
        ],
    },
    {
        "application_id": "LRMIS-2026-0006",
        "event_stream": [
            _perf("application_created", "applicant", "APPL-006",
                  {"parcel_ref": "P-001"}, 50),
            _perf("status_changed", "staff", "REG-002",
                  {"from": "submitted", "to": "pre_checked"}, 48),
            _perf("application_rejected", "staff", "REG-001",
                  {"reason": "Ownership document is invalid."}, 3),
        ],
    },
]


# ---------------------------------------------------------------------------
# Task 28 — Notification Logs (4)
# ---------------------------------------------------------------------------

NOTIFICATION_LOGS = [
    {
        "notification_id": "NOTIF-001",
        "application_id":  "LRMIS-2026-0001",
        "recipient_id":    "APPL-001",
        "type":            "status_change",
        "message":         "Your application LRMIS-2026-0001 has been received and is under review.",
        "sent_at":         _dt(10),
        "read":            True,
    },
    {
        "notification_id": "NOTIF-002",
        "application_id":  "LRMIS-2026-0003",
        "recipient_id":    "APPL-003",
        "type":            "survey_scheduled",
        "message":         "A surveyor has been assigned to your application LRMIS-2026-0003.",
        "sent_at":         _dt(14),
        "read":            False,
    },
    {
        "notification_id": "NOTIF-003",
        "application_id":  "LRMIS-2026-0009",
        "recipient_id":    "APPL-003",
        "type":            "objection_filed",
        "message":         "An objection has been filed against your application LRMIS-2026-0009.",
        "sent_at":         _dt(18),
        "read":            False,
    },
    {
        "notification_id": "NOTIF-004",
        "application_id":  "LRMIS-2026-0005",
        "recipient_id":    "APPL-005",
        "type":            "certificate_issued",
        "message":         "Your land registration certificate CERT-2026-0001 is ready for collection.",
        "sent_at":         _dt(2),
        "read":            True,
    },
]


# ---------------------------------------------------------------------------
# Seeding functions
# ---------------------------------------------------------------------------

def seed_parcels() -> None:
    print(f"[parcels] Seeding {len(PARCELS)} parcels ...")
    for p in PARCELS:
        _upsert("parcels", "parcel_code", p)
    print("[parcels] Done.")


def seed_applications() -> None:
    """Seed into both collections so the professor spec AND existing services work."""
    print(f"[applications] Seeding {len(APPLICATIONS)} applications ...")
    for a in APPLICATIONS:
        _upsert("applications", "application_id", a)
        _upsert("land_applications", "application_id", a)
    print("[applications] Done.")


def seed_applicants() -> None:
    print(f"[applicants] Seeding {len(APPLICANTS)} applicants ...")
    for a in APPLICANTS:
        _upsert("applicants", "applicant_id", a)
    print("[applicants] Done.")


def seed_staff_members() -> None:
    print(f"[staff_members] Seeding {len(STAFF_MEMBERS)} staff members ...")
    for s in STAFF_MEMBERS:
        _upsert("staff_members", "staff_id", s)
    print("[staff_members] Done.")


def seed_certificates() -> None:
    print(f"[certificates] Seeding {len(CERTIFICATES)} certificates ...")
    for c in CERTIFICATES:
        _upsert("certificates", "certificate_id", c)
    print("[certificates] Done.")


def seed_application_documents() -> None:
    print(f"[application_documents] Seeding {len(APPLICATION_DOCUMENTS)} docs ...")
    for d in APPLICATION_DOCUMENTS:
        _upsert("application_documents", "document_id", d)
    print("[application_documents] Done.")


def seed_comments() -> None:
    print(f"[comments] Seeding {len(COMMENTS)} comments ...")
    for c in COMMENTS:
        _upsert("comments", "comment_id", c)
    print("[comments] Done.")


def seed_objections() -> None:
    print(f"[objections] Seeding {len(OBJECTIONS)} objections ...")
    for o in OBJECTIONS:
        _upsert("objections", "objection_id", o)
    print("[objections] Done.")


def seed_survey_tasks() -> None:
    print(f"[survey_tasks] Seeding {len(SURVEY_TASKS)} survey tasks ...")
    for t in SURVEY_TASKS:
        _upsert("survey_tasks", "task_id", t)
    print("[survey_tasks] Done.")


def seed_survey_reports() -> None:
    print(f"[survey_reports] Seeding {len(SURVEY_REPORTS)} survey reports ...")
    for r in SURVEY_REPORTS:
        _upsert("survey_reports", "report_id", r)
    print("[survey_reports] Done.")


def seed_performance_logs() -> None:
    print(f"[performance_logs] Seeding {len(PERFORMANCE_LOGS)} log documents ...")
    app_ids = [doc["application_id"] for doc in PERFORMANCE_LOGS]
    db["performance_logs"].delete_many({"application_id": {"$in": app_ids}})
    db["performance_logs"].insert_many(PERFORMANCE_LOGS)
    print("[performance_logs] Done.")


def seed_notification_logs() -> None:
    print(f"[notification_logs] Seeding {len(NOTIFICATION_LOGS)} notifications ...")
    for n in NOTIFICATION_LOGS:
        _upsert("notification_logs", "notification_id", n)
    print("[notification_logs] Done.")


def seed_counters() -> None:
    """Advance counters so API-generated IDs never collide with seeded documents."""
    print("[counters] Updating counters ...")
    db["counters"].update_one(
        {"_id": "applications_2026"},
        {"$max": {"seq": len(APPLICATIONS)}},
        upsert=True,
    )
    db["counters"].update_one(
        {"_id": "certificates_2026"},
        {"$max": {"seq": len(CERTIFICATES)}},
        upsert=True,
    )
    print("[counters] Done.")


# ---------------------------------------------------------------------------
# Task 30 — Reset command
# ---------------------------------------------------------------------------

DEMO_COLLECTIONS = [
    "applicants",
    "staff_members",
    "parcels",
    "land_applications",
    "applications",
    "certificates",
    "application_documents",
    "comments",
    "objections",
    "survey_tasks",
    "survey_reports",
    "performance_logs",
    "notification_logs",
    "counters",
]


def reset_demo_collections() -> None:
    """Drop all demo collections.  Called when --reset flag is passed."""
    print("=" * 60)
    print("LRMIS — RESET: Dropping demo collections ...")
    for col in DEMO_COLLECTIONS:
        db[col].drop()
        print(f"  [reset] Dropped: {col}")
    print("Reset complete.")
    print("=" * 60)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run() -> None:
    print("=" * 60)
    print("LRMIS — Unified Seed Script (Tasks 17, 28, 29, 30)")
    print(f"  database : {DB_NAME}")
    print(f"  host     : {MONGO_URL}")
    print("=" * 60)

    create_indexes()
    seed_parcels()
    seed_applications()
    seed_applicants()
    seed_staff_members()
    seed_certificates()
    seed_application_documents()
    seed_comments()
    seed_objections()
    seed_survey_tasks()
    seed_survey_reports()
    seed_performance_logs()
    seed_notification_logs()
    seed_counters()

    print("=" * 60)
    print("Seed complete — collection counts:")
    print(f"  parcels              : {db['parcels'].count_documents({})}")
    print(f"  land_applications    : {db['land_applications'].count_documents({})}")
    print(f"  applications         : {db['applications'].count_documents({})}")
    print(f"  applicants           : {db['applicants'].count_documents({})}")
    print(f"  staff_members        : {db['staff_members'].count_documents({})}")
    print(f"  certificates         : {db['certificates'].count_documents({})}")
    print(f"  application_documents: {db['application_documents'].count_documents({})}")
    print(f"  comments             : {db['comments'].count_documents({})}")
    print(f"  objections           : {db['objections'].count_documents({})}")
    print(f"  survey_tasks         : {db['survey_tasks'].count_documents({})}")
    print(f"  survey_reports       : {db['survey_reports'].count_documents({})}")
    print(f"  performance_logs     : {db['performance_logs'].count_documents({})}")
    print(f"  notification_logs    : {db['notification_logs'].count_documents({})}")
    print("=" * 60)


if __name__ == "__main__":
    if "--reset" in sys.argv:
        reset_demo_collections()
    run()
