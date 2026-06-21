from datetime import datetime, timezone
from typing import Optional

from pymongo import ReturnDocument

from app.database import db
from app.schemas.document_schema import DocumentReviewRequest, DocumentUploadPayload
from app.services.audit_service import log_audit, log_performance_event

_APP_DOCS = "application_documents"
_LAND_APPLICATIONS = "land_applications"
_COUNTERS = "counters"
# Compatibility: Student 1's detail endpoint reads from "documents" by name
_COMPAT_DOCS = "documents"


def _next_document_id() -> str:
    year = datetime.now(timezone.utc).year
    result = db[_COUNTERS].find_one_and_update(
        {"_id": f"documents_{year}"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return f"DOC-{year}-{result['seq']:04d}"


def _serialize(doc: dict) -> dict:
    doc = dict(doc)
    doc.pop("_id", None)
    return doc


# ── GET documents for application ─────────────────────────────────────────────

def get_documents_for_application(application_id: str) -> Optional[list]:
    if db[_LAND_APPLICATIONS].find_one({"application_id": application_id}, {"_id": 1}) is None:
        return None
    docs = list(db[_APP_DOCS].find({"application_id": application_id}))
    return [_serialize(d) for d in docs]


# ── Task 6: upload document ────────────────────────────────────────────────────

def upload_document(application_id: str, data: DocumentUploadPayload) -> Optional[dict]:
    app_check = db[_LAND_APPLICATIONS].find_one(
        {"application_id": application_id},
        {"_id": 0, "required_documents": 1},
    )
    if app_check is None:
        return None

    required_docs = app_check.get("required_documents") or []

    now = datetime.now(timezone.utc)
    document_id = _next_document_id()

    doc = {
        "document_id": document_id,
        "application_id": application_id,
        "applicant_id": data.applicant_id,
        "document_type": data.document_type,
        "filename": data.filename,
        "file_url": data.file_url,
        "file_path": data.file_path,
        "mime_type": data.mime_type,
        "size_bytes": data.size_bytes,
        "status": "pending_review",
        "uploaded_at": now,
        "uploaded_by": data.uploaded_by,
        "reviewed_by": None,
        "reviewed_at": None,
        "review_note": None,
    }

    db[_APP_DOCS].insert_one(doc)

    # Track submitted_document_types; also update document_status_map for
    # required document types to reflect the current status (pending_review).
    la_set = {"updated_at": now}
    if data.document_type in required_docs:
        la_set[f"document_status_map.{data.document_type}"] = "pending_review"

    db[_LAND_APPLICATIONS].update_one(
        {"application_id": application_id},
        {
            "$addToSet": {"submitted_document_types": data.document_type},
            "$set": la_set,
        },
    )

    # Write a stub to Student 1's documents collection so the existing
    # GET /applications/{id} detail endpoint reflects this document as submitted
    db[_COMPAT_DOCS].update_one(
        {"application_id": application_id, "name": data.document_type},
        {"$set": {"application_id": application_id, "name": data.document_type,
                  "document_id": document_id}},
        upsert=True,
    )

    log_audit(
        application_id=application_id,
        action="document_uploaded",
        state="document_uploaded",
        performed_by=data.uploaded_by or "applicant",
    )
    log_performance_event(
        application_id=application_id,
        event_type="document_uploaded",
        actor_type="applicant",
        actor_id=data.uploaded_by or "applicant",
        meta={"document_type": data.document_type, "document_id": document_id,
              "filename": data.filename},
    )

    return _serialize(doc)


# ── Task 7: review document ────────────────────────────────────────────────────

def review_document(
    application_id: str,
    document_id: str,
    data: DocumentReviewRequest,
) -> Optional[dict]:
    now = datetime.now(timezone.utc)

    result = db[_APP_DOCS].find_one_and_update(
        {"document_id": document_id, "application_id": application_id},
        {
            "$set": {
                "status": data.status,
                "reviewed_by": data.reviewed_by,
                "reviewed_at": now,
                "review_note": data.review_note,
            }
        },
        return_document=ReturnDocument.AFTER,
    )

    if result is None:
        return None

    # Keep document_status_map in land_applications in sync with the reviewed status
    doc_type = result.get("document_type")
    if doc_type:
        db[_LAND_APPLICATIONS].update_one(
            {"application_id": application_id},
            {"$set": {f"document_status_map.{doc_type}": str(data.status)}},
        )

    log_audit(
        application_id=application_id,
        action=f"document_{data.status}",
        state=f"document_{data.status}",
        performed_by=data.reviewed_by,
    )

    return _serialize(result)
