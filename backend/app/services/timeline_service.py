from datetime import datetime, timezone
from typing import Optional

from app.database import db

_LAND_APPLICATIONS = "land_applications"


def _safe_dt(value) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value
    return None


def get_timeline(application_id: str) -> Optional[dict]:
    app = db[_LAND_APPLICATIONS].find_one({"application_id": application_id})
    if app is None:
        return None

    events = []

    # ── 1a. performance_logs — application lifecycle events ───────────────────
    perf = db["performance_logs"].find_one({"application_id": application_id})
    if perf:
        for e in perf.get("event_stream", []):
            events.append({
                "type": e.get("type"),
                "at": _safe_dt(e.get("at")),
                "actor_type": e.get("by", {}).get("actor_type"),
                "actor_id": e.get("by", {}).get("actor_id"),
                "note": e.get("meta", {}).get("note"),
            })

    # ── 1b. land_applications.timestamps — always included ────────────────────
    timestamps = app.get("timestamps") or {}
    applicant_ref = app.get("applicant_ref")
    submitted_at = _safe_dt(timestamps.get("submitted_at") or app.get("submitted_at"))
    if submitted_at:
        events.append({
            "type": "submitted",
            "at": submitted_at,
            "actor_type": "applicant",
            "actor_id": applicant_ref,
            "note": "Application submitted",
        })
    # Map other named timestamps to events
    _TS_MAP = [
        ("pre_checked_at", "pre_checked", "Application pre-checked"),
        ("approved_at",    "approved",    "Application approved"),
        ("rejected_at",    "rejected",    "Application rejected"),
        ("completed_at",   "completed",   "Application completed"),
    ]
    for ts_key, ev_type, ev_note in _TS_MAP:
        ts_val = _safe_dt(timestamps.get(ts_key))
        if ts_val:
            events.append({
                "type": ev_type,
                "at": ts_val,
                "actor_type": "staff",
                "actor_id": None,
                "note": ev_note,
            })

    # ── 2. application_documents — uploads and reviews ────────────────────────
    for doc in db["application_documents"].find(
        {"application_id": application_id}, {"_id": 0}
    ):
        events.append({
            "type": "document_uploaded",
            "at": _safe_dt(doc.get("uploaded_at")),
            "actor_type": "applicant",
            "actor_id": doc.get("uploaded_by") or doc.get("applicant_id"),
            "note": f"{doc.get('document_type')} uploaded — {doc.get('filename')}",
        })
        if doc.get("reviewed_at"):
            events.append({
                "type": f"document_{doc.get('status')}",
                "at": _safe_dt(doc.get("reviewed_at")),
                "actor_type": "staff",
                "actor_id": doc.get("reviewed_by"),
                "note": doc.get("review_note"),
            })

    # ── 3. application_comments ───────────────────────────────────────────────
    for comment in db["application_comments"].find(
        {"application_id": application_id}, {"_id": 0}
    ):
        events.append({
            "type": "comment_added",
            "at": _safe_dt(comment.get("created_at")),
            "actor_type": comment.get("actor_type"),
            "actor_id": comment.get("created_by"),
            "note": comment.get("comment_text"),
        })

    # ── 4. objections ─────────────────────────────────────────────────────────
    for obj in db["objections"].find(
        {"application_id": application_id}, {"_id": 0}
    ):
        events.append({
            "type": "objection_submitted",
            "at": _safe_dt(obj.get("submitted_at")),
            "actor_type": "applicant",
            "actor_id": obj.get("submitted_by_applicant_id"),
            "note": obj.get("reason"),
        })

    # Sort all events chronologically (None timestamps go first as epoch)
    _epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    events.sort(key=lambda e: e.get("at") or _epoch)

    return {
        "application_id": application_id,
        "current_status": app.get("status"),
        "timeline": events,
    }
