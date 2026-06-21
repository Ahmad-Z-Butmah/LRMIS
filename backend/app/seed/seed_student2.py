"""
LRMIS — Student 2 Seed Script (Tasks 15 & 16)

Creates Student 2 indexes then inserts demo data linked to Student 1 applications.
Safe to run multiple times (upsert-based).

Usage (from backend/ directory):
    python -m app.seed.seed_student2
    python app/seed/seed_student2.py
"""

import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from pymongo import ASCENDING, MongoClient

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "lrmis_db")

_client = MongoClient(MONGO_URL)
db = _client[DB_NAME]


def _dt(offset_days: int = 0) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=offset_days)


def _upsert(collection: str, key: str, doc: dict) -> None:
    db[collection].replace_one({key: doc[key]}, doc, upsert=True)


# ── Task 15: Student 2 Indexes ─────────────────────────────────────────────────

def _safe_index(collection: str, key, **kwargs) -> None:
    """Create index, silently skip if an equivalent index already exists."""
    try:
        db[collection].create_index(key, **kwargs)
    except Exception as exc:
        print(f"  [skip] {collection} {key}: {exc}")


def create_student2_indexes() -> None:
    print("[indexes] Creating Student 2 indexes ...")

    # applicants
    _safe_index("applicants", "identity.national_id", unique=True, sparse=True)
    _safe_index("applicants", "contacts.email")
    _safe_index("applicants", "applicant_type")
    _safe_index("applicants", "verification_state")

    # application_documents
    _safe_index("application_documents", "application_id")
    _safe_index("application_documents", "applicant_id")
    _safe_index("application_documents", "document_type")
    _safe_index("application_documents", "status")
    _safe_index("application_documents", "document_id", unique=True)

    # objections
    _safe_index("objections", "application_id")
    _safe_index("objections", "submitted_by_applicant_id")
    _safe_index("objections", "status")
    _safe_index("objections", "objection_id", unique=True)

    # application_comments
    _safe_index("application_comments", "application_id")
    _safe_index("application_comments", "comment_id", unique=True)

    # notification_logs
    _safe_index("notification_logs", "applicant_id")
    _safe_index("notification_logs", "application_id")

    # performance_logs — Student 1 already created this with unique=True; skip safely
    _safe_index("performance_logs", "application_id")

    print("[indexes] Student 2 indexes done.")


# ── Task 15: Index verification ────────────────────────────────────────────────

_REQUIRED_INDEXES = [
    # (collection, field_key_in_index_info)
    ("applicants",            "identity.national_id_1"),
    ("applicants",            "contacts.email_1"),
    ("applicants",            "applicant_type_1"),
    ("applicants",            "verification_state_1"),
    ("application_documents", "application_id_1"),
    ("application_documents", "applicant_id_1"),
    ("application_documents", "document_type_1"),
    ("application_documents", "status_1"),
    ("objections",            "application_id_1"),
    ("objections",            "submitted_by_applicant_id_1"),
    ("objections",            "status_1"),
    ("performance_logs",      "application_id_1"),
]


def verify_indexes() -> bool:
    print("[indexes] Verifying required indexes ...")
    all_ok = True
    for collection, idx_name in _REQUIRED_INDEXES:
        info = db[collection].index_information()
        if idx_name in info:
            print(f"  [OK]   {collection}.{idx_name}")
        else:
            print(f"  [MISS] {collection}.{idx_name}  -- NOT FOUND")
            all_ok = False
    if all_ok:
        print("[indexes] All required indexes verified.")
    else:
        print("[indexes] WARNING: some required indexes are missing.")
    return all_ok


# ── Task 16: Student 2 Seed Data ──────────────────────────────────────────────

# 5 Applicants — use applicant_ids that match Student 1 applicant_refs
APPLICANTS = [
    {
        "applicant_id": "APPL-001",
        "full_name": "Ahmad Khalil",
        "applicant_type": "citizen",
        "identity": {"national_id": "900512345", "registration_number": None},
        "contacts": {"email": "ahmad.khalil@example.com", "phone": "+970591100001"},
        "address": {"city": "Birzeit", "neighborhood": "Al Masayef", "zone_id": "Z-WEST"},
        "preferences": {
            "preferred_language": "ar",
            "preferred_contact": "email",
            "notifications": {"on_status_change": True, "on_missing_documents": True,
                              "on_certificate_ready": True},
        },
        "privacy_settings": {"show_phone_to_staff": True, "show_email_to_staff": True},
        "verification_state": "verified",
        "linked_applications": ["LRMIS-2026-0001"],
        "created_at": _dt(30),
        "updated_at": _dt(10),
    },
    {
        "applicant_id": "APPL-002",
        "full_name": "Nour Ibrahim",
        "applicant_type": "citizen",
        "identity": {"national_id": "870634512", "registration_number": None},
        "contacts": {"email": "nour.ibrahim@example.com", "phone": "+970591100002"},
        "address": {"city": "Ramallah", "neighborhood": "Al Bireh", "zone_id": "Z-WEST"},
        "preferences": {
            "preferred_language": "ar",
            "preferred_contact": "phone",
            "notifications": {"on_status_change": True, "on_missing_documents": True,
                              "on_certificate_ready": True},
        },
        "privacy_settings": {"show_phone_to_staff": True, "show_email_to_staff": False},
        "verification_state": "verified",
        "linked_applications": ["LRMIS-2026-0002"],
        "created_at": _dt(40),
        "updated_at": _dt(8),
    },
    {
        "applicant_id": "APPL-003",
        "full_name": "Samer Haddad",
        "applicant_type": "company",
        "identity": {"national_id": None, "registration_number": "REG-2020-0045"},
        "contacts": {"email": "samer.haddad@co.example.com", "phone": "+970592200003"},
        "address": {"city": "Nablus", "neighborhood": "Old City", "zone_id": "Z-EAST"},
        "preferences": {
            "preferred_language": "en",
            "preferred_contact": "email",
            "notifications": {"on_status_change": True, "on_missing_documents": False,
                              "on_certificate_ready": True},
        },
        "privacy_settings": {"show_phone_to_staff": False, "show_email_to_staff": True},
        "verification_state": "verified",
        "linked_applications": ["LRMIS-2026-0003"],
        "created_at": _dt(50),
        "updated_at": _dt(15),
    },
    {
        "applicant_id": "APPL-004",
        "full_name": "Rania Saleh",
        "applicant_type": "lawyer",
        "identity": {"national_id": "880123456", "registration_number": "BAR-0221"},
        "contacts": {"email": "rania.saleh@law.example.com", "phone": "+970593300004"},
        "address": {"city": "Hebron", "neighborhood": "Beit Kahil", "zone_id": "Z-EAST"},
        "preferences": {
            "preferred_language": "ar",
            "preferred_contact": "email",
            "notifications": {"on_status_change": True, "on_missing_documents": True,
                              "on_certificate_ready": True},
        },
        "privacy_settings": {"show_phone_to_staff": True, "show_email_to_staff": True},
        "verification_state": "verified",
        "linked_applications": ["LRMIS-2026-0004", "LRMIS-2026-0005"],
        "created_at": _dt(60),
        "updated_at": _dt(5),
    },
    {
        "applicant_id": "APPL-005",
        "full_name": "Khalid Mansour",
        "applicant_type": "surveyor",
        "identity": {"national_id": "920987654", "registration_number": None},
        "contacts": {"email": "khalid.mansour@survey.example.com", "phone": "+970594400005"},
        "address": {"city": "Jericho", "neighborhood": "Ein Sultan", "zone_id": "Z-NORTH"},
        "preferences": {
            "preferred_language": "ar",
            "preferred_contact": "email",
            "notifications": {"on_status_change": True, "on_missing_documents": True,
                              "on_certificate_ready": True},
        },
        "privacy_settings": {"show_phone_to_staff": True, "show_email_to_staff": True},
        "verification_state": "unverified",
        "linked_applications": ["LRMIS-2026-0006"],
        "created_at": _dt(55),
        "updated_at": _dt(3),
    },
]

# 5 Application Documents
APPLICATION_DOCUMENTS = [
    {
        "document_id": "DOC-2026-S001",
        "application_id": "LRMIS-2026-0001",
        "applicant_id": "APPL-001",
        "document_type": "ownership_deed",
        "filename": "ownership_deed_001.pdf",
        "file_url": "/uploads/LRMIS-2026-0001/ownership_deed_001.pdf",
        "file_path": None,
        "mime_type": "application/pdf",
        "size_bytes": 204800,
        "status": "verified",
        "uploaded_at": _dt(9),
        "uploaded_by": "APPL-001",
        "reviewed_by": "staff_01",
        "reviewed_at": _dt(7),
        "review_note": "Ownership deed is valid and matches parcel records.",
    },
    {
        "document_id": "DOC-2026-S002",
        "application_id": "LRMIS-2026-0001",
        "applicant_id": "APPL-001",
        "document_type": "national_id",
        "filename": "national_id_001.jpg",
        "file_url": "/uploads/LRMIS-2026-0001/national_id_001.jpg",
        "file_path": None,
        "mime_type": "image/jpeg",
        "size_bytes": 51200,
        "status": "verified",
        "uploaded_at": _dt(9),
        "uploaded_by": "APPL-001",
        "reviewed_by": "staff_01",
        "reviewed_at": _dt(7),
        "review_note": "National ID is clear and valid.",
    },
    {
        "document_id": "DOC-2026-S003",
        "application_id": "LRMIS-2026-0002",
        "applicant_id": "APPL-002",
        "document_type": "ownership_deed",
        "filename": "ownership_deed_002.pdf",
        "file_url": "/uploads/LRMIS-2026-0002/ownership_deed_002.pdf",
        "file_path": None,
        "mime_type": "application/pdf",
        "size_bytes": 307200,
        "status": "pending_review",
        "uploaded_at": _dt(7),
        "uploaded_by": "APPL-002",
        "reviewed_by": None,
        "reviewed_at": None,
        "review_note": None,
    },
    {
        "document_id": "DOC-2026-S004",
        "application_id": "LRMIS-2026-0003",
        "applicant_id": "APPL-003",
        "document_type": "national_id",
        "filename": "company_registration_003.pdf",
        "file_url": "/uploads/LRMIS-2026-0003/company_registration_003.pdf",
        "file_path": None,
        "mime_type": "application/pdf",
        "size_bytes": 102400,
        "status": "rejected",
        "uploaded_at": _dt(14),
        "uploaded_by": "APPL-003",
        "reviewed_by": "staff_02",
        "reviewed_at": _dt(12),
        "review_note": "Company registration number on document does not match records.",
    },
    {
        "document_id": "DOC-2026-S005",
        "application_id": "LRMIS-2026-0004",
        "applicant_id": "APPL-004",
        "document_type": "ownership_deed",
        "filename": "ownership_deed_004.pdf",
        "file_url": "/uploads/LRMIS-2026-0004/ownership_deed_004.pdf",
        "file_path": None,
        "mime_type": "application/pdf",
        "size_bytes": 256000,
        "status": "verified",
        "uploaded_at": _dt(39),
        "uploaded_by": "APPL-004",
        "reviewed_by": "staff_02",
        "reviewed_at": _dt(36),
        "review_note": "Deed verified against land registry.",
    },
]

# 3 Application Comments
APPLICATION_COMMENTS = [
    {
        "comment_id": "CMT-2026-S001",
        "application_id": "LRMIS-2026-0001",
        "comment_text": "I have submitted all required documents. Please review at your earliest convenience.",
        "created_by": "APPL-001",
        "actor_type": "applicant",
        "created_at": _dt(8),
        "visibility": "applicant_visible",
    },
    {
        "comment_id": "CMT-2026-S002",
        "application_id": "LRMIS-2026-0003",
        "comment_text": "The company registration document has been updated and resubmitted.",
        "created_by": "APPL-003",
        "actor_type": "applicant",
        "created_at": _dt(11),
        "visibility": "applicant_visible",
    },
    {
        "comment_id": "CMT-2026-S003",
        "application_id": "LRMIS-2026-0002",
        "comment_text": "Internal note: applicant needs to resubmit site plan with coordinates.",
        "created_by": "staff_01",
        "actor_type": "staff",
        "created_at": _dt(6),
        "visibility": "staff_only",
    },
]

# 2 Objections
OBJECTIONS = [
    {
        "objection_id": "OBJ-2026-S001",
        "application_id": "LRMIS-2026-0003",
        "submitted_by_applicant_id": "APPL-003",
        "reason": "The rejected document matches our official company registration. We request a review.",
        "supporting_documents": ["DOC-2026-S004"],
        "status": "under_review",
        "submitted_at": _dt(10),
        "reviewed_by": "legal_01",
        "reviewed_at": _dt(8),
        "decision_note": "Under review by legal team.",
    },
    {
        "objection_id": "OBJ-2026-S002",
        "application_id": "LRMIS-2026-0006",
        "submitted_by_applicant_id": "APPL-005",
        "reason": "Application was rejected unfairly. Ownership document is authentic.",
        "supporting_documents": [],
        "status": "submitted",
        "submitted_at": _dt(2),
        "reviewed_by": None,
        "reviewed_at": None,
        "decision_note": None,
    },
]

# 5 Notification Stubs
NOTIFICATION_STUBS = [
    {
        "notification_id": "NOTIF-2026-S001",
        "applicant_id": "APPL-001",
        "application_id": "LRMIS-2026-0001",
        "event_type": "status_changed",
        "channel": "email",
        "email": "ahmad.khalil@example.com",
        "phone": None,
        "message": "[STUB] Your application LRMIS-2026-0001 status changed to pre_checked.",
        "status": "stub",
        "created_at": _dt(8),
    },
    {
        "notification_id": "NOTIF-2026-S002",
        "applicant_id": "APPL-002",
        "application_id": "LRMIS-2026-0002",
        "event_type": "missing_documents_requested",
        "channel": "email",
        "email": "nour.ibrahim@example.com",
        "phone": None,
        "message": "[STUB] Your application LRMIS-2026-0002 requires additional documents.",
        "status": "stub",
        "created_at": _dt(7),
    },
    {
        "notification_id": "NOTIF-2026-S003",
        "applicant_id": "APPL-001",
        "application_id": "LRMIS-2026-0001",
        "event_type": "document_reviewed",
        "channel": "email",
        "email": "ahmad.khalil@example.com",
        "phone": None,
        "message": "[STUB] Your document ownership_deed for LRMIS-2026-0001 has been verified.",
        "status": "stub",
        "created_at": _dt(7),
    },
    {
        "notification_id": "NOTIF-2026-S004",
        "applicant_id": "APPL-003",
        "application_id": "LRMIS-2026-0003",
        "event_type": "objection_submitted",
        "channel": "email",
        "email": "samer.haddad@co.example.com",
        "phone": None,
        "message": "[STUB] Your objection OBJ-2026-S001 for LRMIS-2026-0003 has been received.",
        "status": "stub",
        "created_at": _dt(10),
    },
    {
        "notification_id": "NOTIF-2026-S005",
        "applicant_id": "APPL-004",
        "application_id": "LRMIS-2026-0005",
        "event_type": "certificate_ready",
        "channel": "email",
        "email": "rania.saleh@law.example.com",
        "phone": None,
        "message": "[STUB] Your certificate CERT-2026-0001 for LRMIS-2026-0005 is ready.",
        "status": "stub",
        "created_at": _dt(2),
    },
]


# ── Seeding functions ──────────────────────────────────────────────────────────

def seed_applicants() -> None:
    print(f"[applicants] Seeding {len(APPLICANTS)} applicants ...")
    for a in APPLICANTS:
        _upsert("applicants", "applicant_id", a)
    # Advance counter so API-created applicants don't collide with seeded ones
    db["counters"].update_one(
        {"_id": "applicants_2026"},
        {"$max": {"seq": len(APPLICANTS)}},
        upsert=True,
    )
    print("[applicants] Done.")


def seed_application_documents() -> None:
    print(f"[application_documents] Seeding {len(APPLICATION_DOCUMENTS)} documents ...")
    for d in APPLICATION_DOCUMENTS:
        _upsert("application_documents", "document_id", d)
    db["counters"].update_one(
        {"_id": "documents_2026"},
        {"$max": {"seq": len(APPLICATION_DOCUMENTS)}},
        upsert=True,
    )
    # Also write stubs to Student 1 documents collection for compatibility
    for d in APPLICATION_DOCUMENTS:
        db["documents"].update_one(
            {"application_id": d["application_id"], "name": d["document_type"]},
            {"$set": {"application_id": d["application_id"], "name": d["document_type"],
                      "document_id": d["document_id"]}},
            upsert=True,
        )
    print("[application_documents] Done.")


def seed_comments() -> None:
    print(f"[application_comments] Seeding {len(APPLICATION_COMMENTS)} comments ...")
    for c in APPLICATION_COMMENTS:
        _upsert("application_comments", "comment_id", c)
    db["counters"].update_one(
        {"_id": "comments_2026"},
        {"$max": {"seq": len(APPLICATION_COMMENTS)}},
        upsert=True,
    )
    print("[application_comments] Done.")


def seed_objections() -> None:
    print(f"[objections] Seeding {len(OBJECTIONS)} objections ...")
    for o in OBJECTIONS:
        _upsert("objections", "objection_id", o)
    db["counters"].update_one(
        {"_id": "objections_2026"},
        {"$max": {"seq": len(OBJECTIONS)}},
        upsert=True,
    )
    print("[objections] Done.")


def seed_notification_stubs() -> None:
    print(f"[notification_logs] Seeding {len(NOTIFICATION_STUBS)} notification stubs ...")
    for n in NOTIFICATION_STUBS:
        _upsert("notification_logs", "notification_id", n)
    db["counters"].update_one(
        {"_id": "notifications_2026"},
        {"$max": {"seq": len(NOTIFICATION_STUBS)}},
        upsert=True,
    )
    print("[notification_logs] Done.")


# ── Entry point ────────────────────────────────────────────────────────────────

def run() -> None:
    print("=" * 60)
    print("LRMIS -- Student 2 Seed Script")
    print(f"  database : {DB_NAME}")
    print(f"  host     : {MONGO_URL}")
    print("=" * 60)

    create_student2_indexes()
    seed_applicants()
    seed_application_documents()
    seed_comments()
    seed_objections()
    seed_notification_stubs()

    print()
    verify_indexes()

    print()
    print("=" * 60)
    print("Student 2 seed complete.")
    print(f"  applicants           : {db['applicants'].count_documents({})}")
    print(f"  application_documents: {db['application_documents'].count_documents({})}")
    print(f"  application_comments : {db['application_comments'].count_documents({})}")
    print(f"  objections           : {db['objections'].count_documents({})}")
    print(f"  notification_logs    : {db['notification_logs'].count_documents({})}")
    print()

    # Linked application IDs in seed data
    doc_app_ids = sorted(set(
        d["application_id"] for d in db["application_documents"].find({}, {"application_id": 1, "_id": 0})
    ))
    cmt_app_ids = sorted(set(
        c["application_id"] for c in db["application_comments"].find({}, {"application_id": 1, "_id": 0})
    ))
    obj_app_ids = sorted(set(
        o["application_id"] for o in db["objections"].find({}, {"application_id": 1, "_id": 0})
    ))
    notif_app_ids = sorted(set(
        n["application_id"] for n in db["notification_logs"].find(
            {"application_id": {"$ne": None}}, {"application_id": 1, "_id": 0})
    ))
    print(f"  document app IDs     : {doc_app_ids}")
    print(f"  comment  app IDs     : {cmt_app_ids}")
    print(f"  objection app IDs    : {obj_app_ids}")
    print(f"  notif    app IDs     : {notif_app_ids}")
    print("=" * 60)


if __name__ == "__main__":
    run()
