from datetime import datetime, timezone
from typing import Optional

from app.database import db

AUDIT_COLLECTION = "audit_logs"
_PERFORMANCE_COLLECTION = "performance_logs"


def log_audit(
    application_id: str,
    action: str,
    state: str,
    performed_by: str = "system",
) -> None:
    db[AUDIT_COLLECTION].insert_one(
        {
            "application_id": application_id,
            "action": action,
            "state": state,
            "performed_by": performed_by,
            "timestamp": datetime.now(timezone.utc),
        }
    )


def get_audit_timeline(application_id: str) -> list:
    """Return all audit entries for an application sorted oldest-first."""
    cursor = (
        db[AUDIT_COLLECTION]
        .find({"application_id": application_id}, {"_id": 0})
        .sort("timestamp", 1)
    )
    return list(cursor)


def log_performance_event(
    application_id: str,
    event_type: str,
    actor_type: str = "system",
    actor_id: str = "system",
    meta: Optional[dict] = None,
) -> None:
    """Append a structured event to performance_logs.event_stream.
    Uses upsert so the document is created automatically on first event.
    """
    event = {
        "type": event_type,
        "by": {"actor_type": actor_type, "actor_id": actor_id},
        "at": datetime.now(timezone.utc),
        "meta": meta or {},
    }
    db[_PERFORMANCE_COLLECTION].update_one(
        {"application_id": application_id},
        {
            "$setOnInsert": {"application_id": application_id},
            "$push": {"event_stream": event},
        },
        upsert=True,
    )
