from datetime import datetime, timezone
from typing import Optional

from pymongo import ReturnDocument

from app.database import db
from app.schemas.objection_schema import ObjectionCreate
from app.services.audit_service import log_audit, log_performance_event

_OBJECTIONS = "objections"
_LAND_APPLICATIONS = "land_applications"
_COUNTERS = "counters"

_UNDER_OBJECTION_ALLOWED_NEXT = ["legal_review", "rejected"]


def _next_objection_id() -> str:
    year = datetime.now(timezone.utc).year
    result = db[_COUNTERS].find_one_and_update(
        {"_id": f"objections_{year}"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return f"OBJ-{year}-{result['seq']:04d}"


def _serialize(doc: dict) -> dict:
    doc = dict(doc)
    doc.pop("_id", None)
    return doc


# ── Task 11: submit objection ──────────────────────────────────────────────────

def submit_objection(application_id: str, data: ObjectionCreate) -> Optional[dict]:
    if db[_LAND_APPLICATIONS].find_one({"application_id": application_id}, {"_id": 1}) is None:
        return None

    now = datetime.now(timezone.utc)
    objection_id = _next_objection_id()

    doc = {
        "objection_id": objection_id,
        "application_id": application_id,
        "submitted_by_applicant_id": data.submitted_by_applicant_id,
        "reason": data.reason,
        "supporting_documents": data.supporting_documents,
        "status": "submitted",
        "submitted_at": now,
        "reviewed_by": None,
        "reviewed_at": None,
        "decision_note": None,
    }

    db[_OBJECTIONS].insert_one(doc)

    # Update land_applications: move to under_objection and record the objection
    db[_LAND_APPLICATIONS].update_one(
        {"application_id": application_id},
        {
            "$set": {
                "status": "under_objection",
                "workflow.current_state": "under_objection",
                "workflow.allowed_next": _UNDER_OBJECTION_ALLOWED_NEXT,
                "objection.has_objection": True,
                "updated_at": now,
            },
            "$addToSet": {"objection.objection_ids": objection_id},
        },
    )

    log_audit(
        application_id=application_id,
        action="objection_submitted",
        state="under_objection",
        performed_by=data.submitted_by_applicant_id,
    )
    log_performance_event(
        application_id=application_id,
        event_type="objection_submitted",
        actor_type="applicant",
        actor_id=data.submitted_by_applicant_id,
        meta={"objection_id": objection_id, "reason": data.reason},
    )

    return _serialize(doc)
