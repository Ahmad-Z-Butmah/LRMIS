"""
Task 27 — Backend Test Cases
12 scenarios executed in declaration order.

Fixtures (from conftest.py):
  client   — FastAPI TestClient backed by mongomock
  test_db  — direct pymongo handle to the same in-memory DB
  ctx      — dict with applicant_id and application_id for the main test user
"""

# ─────────────────────────── test data ───────────────────────────────────────

# A separate applicant used only for the create / duplicate tests (1 & 2).
# national_id must differ from the main fixture applicant ("111111111").
_NEW_APPLICANT = {
    "full_name": "Khaled Omar",
    "applicant_type": "citizen",
    "identity": {"national_id": "222222222"},
    "contacts": {"email": "khaled@example.com", "phone": "0592000002"},
    "address": {"city": "Nablus", "neighborhood": "Old City", "zone_id": "Z-002"},
    "preferences": {
        "preferred_language": "ar",
        "preferred_contact": "email",
        "notifications": {
            "on_status_change": True,
            "on_missing_documents": False,
            "on_certificate_ready": True,
        },
    },
    "privacy_settings": {"show_phone_to_staff": False, "show_email_to_staff": True},
}

# Shared document_id — written by test 5, read by test 6
_doc: dict = {}


# ════════════════════════ TEST 1 ═════════════════════════════════════════════

def test_01_create_applicant_profile_success(client):
    """POST /applicants/ with valid data → 201 Created."""
    resp = client.post("/applicants/", json=_NEW_APPLICANT)
    assert resp.status_code == 201
    body = resp.json()
    assert body["applicant_id"].startswith("APL-")
    assert body["full_name"] == "Khaled Omar"
    assert body["verification_state"] == "unverified"


# ════════════════════════ TEST 2 ═════════════════════════════════════════════

def test_02_create_applicant_duplicate_national_id(client):
    """POST /applicants/ with an already-used national_id → 409 Conflict."""
    resp = client.post("/applicants/", json=_NEW_APPLICANT)
    assert resp.status_code == 409
    assert "national_id" in resp.json()["detail"].lower()


# ════════════════════════ TEST 3 ═════════════════════════════════════════════

def test_03_get_applicant_profile_success(client, ctx):
    """GET /applicants/{id}?viewer_role=applicant → 200 with full (unmasked) profile."""
    applicant_id = ctx["applicant_id"]
    resp = client.get(f"/applicants/{applicant_id}?viewer_role=applicant")
    assert resp.status_code == 200
    body = resp.json()
    assert body["applicant_id"] == applicant_id
    assert body["full_name"] == "Fatima Nasser"
    # Self-view must return the real national_id, not masked
    assert body["identity"]["national_id"] == "111111111"


# ════════════════════════ TEST 4 ═════════════════════════════════════════════

def test_04_get_applicant_applications_success(client, ctx):
    """GET /applicants/{id}/applications → 200 with the linked application."""
    applicant_id = ctx["applicant_id"]
    resp = client.get(f"/applicants/{applicant_id}/applications")
    assert resp.status_code == 200
    body = resp.json()
    assert body["applicant_id"] == applicant_id
    assert body["total"] >= 1
    ids = [a["application_id"] for a in body["applications"]]
    assert ctx["application_id"] in ids


# ════════════════════════ TEST 5 ═════════════════════════════════════════════

def test_05_upload_document_metadata_success(client, ctx):
    """POST /applications/{id}/documents → 201 with pending_review status."""
    application_id = ctx["application_id"]
    payload = {
        "applicant_id": ctx["applicant_id"],
        "document_type": "id_copy",
        "filename": "national_id.pdf",
        "file_url": "https://storage.example.com/docs/national_id.pdf",
        "mime_type": "application/pdf",
        "size_bytes": 204800,
        "uploaded_by": ctx["applicant_id"],
    }
    resp = client.post(f"/applications/{application_id}/documents", json=payload)
    assert resp.status_code == 201
    body = resp.json()
    assert body["document_id"].startswith("DOC-")
    assert body["status"] == "pending_review"
    assert body["document_type"] == "id_copy"
    assert body["application_id"] == application_id
    _doc["document_id"] = body["document_id"]


# ════════════════════════ TEST 6 ═════════════════════════════════════════════

def test_06_review_document_success(client, ctx):
    """PATCH /applications/{id}/documents/{doc_id}/review → 200 verified."""
    application_id = ctx["application_id"]
    document_id = _doc["document_id"]
    payload = {
        "status": "verified",
        "reviewed_by": "staff-001",
        "review_note": "Document is clear and valid.",
    }
    resp = client.patch(
        f"/applications/{application_id}/documents/{document_id}/review",
        json=payload,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "verified"
    assert body["reviewed_by"] == "staff-001"
    assert body["document_id"] == document_id


# ════════════════════════ TEST 7 ═════════════════════════════════════════════

def test_07_add_comment_success(client, ctx):
    """POST /applications/{id}/comments → 201 with comment_id."""
    application_id = ctx["application_id"]
    payload = {
        "comment_text": "Please verify the ownership deed as well.",
        "created_by": ctx["applicant_id"],
        "actor_type": "applicant",
        "visibility": "applicant_visible",
    }
    resp = client.post(f"/applications/{application_id}/comments", json=payload)
    assert resp.status_code == 201
    body = resp.json()
    assert body["comment_id"].startswith("CMT-")
    assert body["comment_text"] == "Please verify the ownership deed as well."
    assert body["application_id"] == application_id
    assert body["visibility"] == "applicant_visible"


# ════════════════════════ TEST 8 ═════════════════════════════════════════════

def test_08_submit_objection_without_reason_fails(client, ctx):
    """POST /applications/{id}/objections with empty reason → 422 Unprocessable."""
    application_id = ctx["application_id"]
    payload = {
        "submitted_by_applicant_id": ctx["applicant_id"],
        "reason": "",           # violates min_length=1 on ObjectionCreate.reason
        "supporting_documents": [],
    }
    resp = client.post(f"/applications/{application_id}/objections", json=payload)
    assert resp.status_code == 422


# ════════════════════════ TEST 9 ═════════════════════════════════════════════

def test_09_submit_objection_with_reason_success(client, ctx):
    """POST /applications/{id}/objections with a valid reason → 201."""
    application_id = ctx["application_id"]
    payload = {
        "submitted_by_applicant_id": ctx["applicant_id"],
        "reason": "The parcel boundaries in the survey do not match the ownership deed.",
        "supporting_documents": [],
    }
    resp = client.post(f"/applications/{application_id}/objections", json=payload)
    assert resp.status_code == 201
    body = resp.json()
    assert body["objection_id"].startswith("OBJ-")
    assert body["status"] == "submitted"
    assert body["application_id"] == application_id
    assert body["reason"] != ""


# ════════════════════════ TEST 10 ════════════════════════════════════════════

def test_10_application_moves_to_under_objection(test_db, ctx):
    """After objection submission, land_applications.status → 'under_objection'."""
    app_doc = test_db["land_applications"].find_one(
        {"application_id": ctx["application_id"]},
        {"status": 1, "workflow": 1, "_id": 0},
    )
    assert app_doc is not None
    assert app_doc["status"] == "under_objection"
    assert app_doc["workflow"]["current_state"] == "under_objection"
    assert "legal_review" in app_doc["workflow"]["allowed_next"]


# ════════════════════════ TEST 11 ════════════════════════════════════════════

def test_11_get_application_timeline_success(client, ctx):
    """GET /applications/{id}/timeline → 200 with sorted event list."""
    application_id = ctx["application_id"]
    resp = client.get(f"/applications/{application_id}/timeline")
    assert resp.status_code == 200
    body = resp.json()
    assert body["application_id"] == application_id
    assert body["current_status"] == "under_objection"
    assert "timeline" in body
    assert isinstance(body["timeline"], list)
    # At minimum: submitted + document uploaded + document reviewed + comment + objection
    assert len(body["timeline"]) >= 5
    event_types = {e["type"] for e in body["timeline"]}
    assert "document_uploaded" in event_types
    assert "objection_submitted" in event_types
    assert "comment_added" in event_types


# ════════════════════════ TEST 12 ════════════════════════════════════════════

def test_12_notification_stub_created(test_db, ctx):
    """notification_service.create_notification_stub() persists to notification_logs."""
    from app.services.notification_service import create_notification_stub

    result = create_notification_stub(
        event_type="objection_submitted",
        applicant_id=ctx["applicant_id"],
        application_id=ctx["application_id"],
        channel="email",
        email="fatima@example.com",
        message="Your objection has been received and is under review.",
    )

    assert result["notification_id"].startswith("NOTIF-")
    assert result["status"] == "stub"
    assert result["event_type"] == "objection_submitted"
    assert result["application_id"] == ctx["application_id"]
    assert result["applicant_id"] == ctx["applicant_id"]

    stored = test_db["notification_logs"].find_one(
        {"notification_id": result["notification_id"]}, {"_id": 0}
    )
    assert stored is not None
    assert stored["status"] == "stub"
    assert stored["channel"] == "email"
