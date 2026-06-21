from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.database import db

_STAFF = "staff_members"
_SURVEY_TASKS = "survey_tasks"
_PERFORMANCE = "performance_logs"
_COUNTERS = "counters"


# ── Internal helpers ──────────────────────────────────────────────────────────

def _next_staff_id() -> str:
    from pymongo import ReturnDocument
    result = db[_COUNTERS].find_one_and_update(
        {"_id": "staff_members"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return f"STAFF-{result['seq']:05d}"


def _serialize(doc: dict) -> dict:
    doc = dict(doc)
    doc.pop("_id", None)
    return doc


# ── Task 2: create staff ──────────────────────────────────────────────────────

def create_staff(data: dict) -> dict:
    # Check for duplicate staff_code
    if db[_STAFF].find_one({"staff_code": data["staff_code"]}):
        raise ValueError(f"staff_code '{data['staff_code']}' already exists")

    staff_id = _next_staff_id()
    now = datetime.now(timezone.utc)

    doc = {
        "staff_id": staff_id,
        **data,
        "active": True,
        "created_at": now,
        "updated_at": now,
    }

    db[_STAFF].insert_one(doc)
    return _serialize(doc)


# ── Task 3: get staff profile ─────────────────────────────────────────────────

def get_staff_profile(staff_id: str) -> Optional[Dict[str, Any]]:
    staff = db[_STAFF].find_one({"staff_id": staff_id})
    if staff is None:
        return None

    staff = _serialize(staff)

    # Count and list assigned survey tasks
    tasks_cursor = db[_SURVEY_TASKS].find(
        {"assigned_surveyor_id": staff_id},
        {"_id": 0},
    )
    assigned_tasks = list(tasks_cursor)
    assigned_task_count = len(assigned_tasks)

    # Performance summary from performance_logs
    perf_doc = db[_PERFORMANCE].find_one({"staff_id": staff_id}, {"_id": 0})
    if perf_doc:
        performance_summary = {
            "total_events": len(perf_doc.get("event_stream", [])),
            "events": perf_doc.get("event_stream", [])[-10:],  # last 10 events
        }
    else:
        performance_summary = {
            "total_events": 0,
            "events": [],
        }

    return {
        **staff,
        "assigned_task_count": assigned_task_count,
        "assigned_tasks": assigned_tasks,
        "performance_summary": performance_summary,
    }
