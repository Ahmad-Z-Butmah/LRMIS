from datetime import datetime, timezone
from typing import Optional

from pymongo import ReturnDocument

from app.database import db

_NOTIF_LOGS = "notification_logs"
_COUNTERS = "counters"

# Supported notification events
NOTIFICATION_EVENTS = [
    "status_changed",
    "missing_documents_requested",
    "document_reviewed",
    "objection_submitted",
    "certificate_ready",
]


def _next_notification_id() -> str:
    year = datetime.now(timezone.utc).year
    result = db[_COUNTERS].find_one_and_update(
        {"_id": f"notifications_{year}"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return f"NOTIF-{year}-{result['seq']:04d}"


def _serialize(doc: dict) -> dict:
    doc = dict(doc)
    doc.pop("_id", None)
    return doc


# ── Task 13: notification stub ────────────────────────────────────────────────

def create_notification_stub(
    event_type: str,
    applicant_id: str,
    application_id: Optional[str] = None,
    channel: str = "email",
    email: Optional[str] = None,
    phone: Optional[str] = None,
    message: Optional[str] = None,
) -> dict:
    """
    Creates a notification stub and logs it to notification_logs.
    No real message is sent — status is always 'stub'.
    """
    now = datetime.now(timezone.utc)
    notification_id = _next_notification_id()

    notification = {
        "notification_id": notification_id,
        "applicant_id": applicant_id,
        "application_id": application_id,
        "event_type": event_type,
        "channel": channel,
        "email": email,
        "phone": phone,
        "message": message or f"[STUB] Notification for event: {event_type}",
        "status": "stub",
        "created_at": now,
    }

    db[_NOTIF_LOGS].insert_one(notification)
    return _serialize(notification)
