"""
Pytest configuration for Task 27 backend tests.

mongomock.patch() is activated at module-import time — before any application
module is imported — so that app.database.db is backed by an in-memory client
for the entire test session.
"""

# ── Activate mongomock BEFORE any app imports ─────────────────────────────────
import mongomock

_patcher = mongomock.patch(servers=(("localhost", 27017),))
_patcher.start()

# ── App imports (safe now that MongoClient is mocked) ─────────────────────────
from datetime import datetime, timezone  # noqa: E402

import pymongo  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

_MAIN_APPLICANT = {
    "full_name": "Fatima Nasser",
    "applicant_type": "citizen",
    "identity": {"national_id": "111111111"},
    "contacts": {"email": "fatima@example.com", "phone": "0591000001"},
    "address": {"city": "Ramallah", "neighborhood": "Al-Irsal", "zone_id": "Z-001"},
    "preferences": {
        "preferred_language": "ar",
        "preferred_contact": "email",
        "notifications": {
            "on_status_change": True,
            "on_missing_documents": True,
            "on_certificate_ready": True,
        },
    },
    "privacy_settings": {"show_phone_to_staff": True, "show_email_to_staff": True},
}


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def test_db():
    """Direct access to the shared in-memory MongoDB (same instance the app uses)."""
    return pymongo.MongoClient("mongodb://localhost:27017")["lrmis_db"]


@pytest.fixture(scope="session")
def ctx(client, test_db):
    """
    Creates the main test applicant and inserts a test application into
    land_applications (the collection that document/comment/objection services
    read from). Used by tests 3–12.
    """
    resp = client.post("/applicants/", json=_MAIN_APPLICANT)
    assert resp.status_code == 201, f"ctx setup failed: {resp.text}"
    applicant_id = resp.json()["applicant_id"]

    # Insert application directly — application_service writes to 'applications',
    # but document/comment/objection/timeline services read from 'land_applications'.
    now = datetime.now(timezone.utc)
    application_id = "LRMIS-TEST-0001"
    test_db["land_applications"].insert_one({
        "application_id": application_id,
        "applicant_ref": applicant_id,
        "parcel_ref": "PARCEL-001",
        "required_documents": ["id_copy", "ownership_deed"],
        "status": "submitted",
        "workflow": {
            "current_state": "submitted",
            "allowed_next": ["pre_checked", "missing_documents", "on_hold", "rejected"],
        },
        "submitted_at": now,
        "created_at": now,
        "updated_at": now,
    })

    # Link the application to the applicant so get_applicant_applications returns it
    test_db["applicants"].update_one(
        {"applicant_id": applicant_id},
        {"$addToSet": {"linked_applications": application_id}},
    )

    return {"applicant_id": applicant_id, "application_id": application_id}
