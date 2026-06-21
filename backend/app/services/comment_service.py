from datetime import datetime, timezone
from typing import Optional

from pymongo import ReturnDocument

from app.database import db
from app.schemas.comment_schema import CommentCreate
from app.services.audit_service import log_audit

_APP_COMMENTS = "application_comments"
_LAND_APPLICATIONS = "land_applications"
_COUNTERS = "counters"


def _next_comment_id() -> str:
    year = datetime.now(timezone.utc).year
    result = db[_COUNTERS].find_one_and_update(
        {"_id": f"comments_{year}"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return f"CMT-{year}-{result['seq']:04d}"


def _serialize(doc: dict) -> dict:
    doc = dict(doc)
    doc.pop("_id", None)
    return doc


# ── GET comments for an application ──────────────────────────────────────────

def get_comments_for_application(application_id: str) -> Optional[list]:
    if db[_LAND_APPLICATIONS].find_one({"application_id": application_id}, {"_id": 1}) is None:
        return None
    comments = list(db[_APP_COMMENTS].find({"application_id": application_id}).sort("created_at", 1))
    return [_serialize(c) for c in comments]


# ── Task 9: add applicant comment ─────────────────────────────────────────────

def add_comment(application_id: str, data: CommentCreate) -> Optional[dict]:
    if db[_LAND_APPLICATIONS].find_one({"application_id": application_id}, {"_id": 1}) is None:
        return None

    now = datetime.now(timezone.utc)
    comment_id = _next_comment_id()

    doc = {
        "comment_id": comment_id,
        "application_id": application_id,
        "comment_text": data.comment_text,
        "created_by": data.created_by,
        "actor_type": data.actor_type,
        "created_at": now,
        "visibility": data.visibility,
    }

    db[_APP_COMMENTS].insert_one(doc)

    log_audit(
        application_id=application_id,
        action="applicant_comment_added",
        state="applicant_comment_added",
        performed_by=data.created_by,
    )

    return _serialize(doc)
