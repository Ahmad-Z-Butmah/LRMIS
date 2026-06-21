from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pymongo import ReturnDocument

from app.database import db
from app.services.audit_service import log_audit, log_performance_event
from app.schemas.survey_task_schema import ALLOWED_MILESTONES, TERMINAL_STATUSES

_SURVEY_TASKS = "survey_tasks"
_STAFF = "staff_members"
_APPLICATIONS = "applications"
_COUNTERS = "counters"
_PERFORMANCE = "performance_logs"


# ── Internal helpers ──────────────────────────────────────────────────────────

def _next_task_id() -> str:
    result = db[_COUNTERS].find_one_and_update(
        {"_id": "survey_tasks"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return f"TASK-{result['seq']:05d}"


def _serialize(doc: dict) -> dict:
    doc = dict(doc)
    doc.pop("_id", None)
    return doc


# ── Active task check (Task 7) ────────────────────────────────────────────────

def get_active_task_for_application(application_id: str) -> Optional[dict]:
    """Return an existing non-terminal survey task for this application, or None."""
    task = db[_SURVEY_TASKS].find_one({
        "application_id": application_id,
        "status": {"$nin": list(TERMINAL_STATUSES)},
    }, {"_id": 0})
    return task


# ── Task 6: auto-assign surveyor ──────────────────────────────────────────────

def auto_assign_surveyor(application_id: str) -> Dict[str, Any]:
    """
    Find the best surveyor, create a survey task, update application and workload.
    Implements Task 6 + Task 7 (duplicate prevention).
    """
    # 1. Fetch application
    app = db[_APPLICATIONS].find_one({"application_id": application_id}, {"_id": 0})
    if app is None:
        raise ValueError(f"Application '{application_id}' not found")

    # 2. Check status = survey_required
    status = app.get("status") or app.get("workflow", {}).get("current_state")
    if status != "survey_required":
        raise ValueError(
            f"Application '{application_id}' is not in 'survey_required' status "
            f"(current: '{status}')"
        )

    # 3. Task 7 — duplicate prevention: return existing active task if one exists
    existing_task = get_active_task_for_application(application_id)
    if existing_task:
        return {
            "application_id": application_id,
            "task_id": existing_task["task_id"],
            "assigned_surveyor_id": existing_task["assigned_surveyor_id"],
            "assigned_surveyor_code": existing_task.get("assigned_surveyor_code", ""),
            "score": None,
            "scoring_breakdown": None,
            "status": existing_task["status"],
            "note": "existing_task_returned",
        }

    # 4. Extract zone and skills from application's parcel_ref
    parcel_ref = app.get("parcel_ref") or {}
    if isinstance(parcel_ref, dict):
        zone_id = parcel_ref.get("zone_id")
        parcel_id = parcel_ref.get("parcel_number") or parcel_ref.get("parcel_id")
    else:
        zone_id = None
        parcel_id = str(parcel_ref)

    priority = app.get("priority")

    # 5. Find best surveyor using scoring service
    from app.services.assignment_service import find_best_surveyor
    assignment = find_best_surveyor(
        zone_id=zone_id,
        required_skills=[],
        priority=priority,
    )
    surveyor = assignment["surveyor"]
    surveyor_id = surveyor["staff_id"]
    surveyor_code = surveyor.get("staff_code", "")

    # 6. Create survey task
    task_id = _next_task_id()
    now = datetime.now(timezone.utc)

    initial_milestone = {
        "milestone": "assigned",
        "by": "system",
        "note": "Auto-assigned by system",
        "meta": {},
        "timestamp": now,
    }

    task_doc = {
        "task_id": task_id,
        "application_id": application_id,
        "parcel_id": parcel_id,
        "assigned_surveyor_id": surveyor_id,
        "assigned_surveyor_code": surveyor_code,
        "status": "assigned",
        "milestones": [initial_milestone],
        "field_notes": None,
        "report_uploaded": False,
        "scheduled_visit_date": None,
        "priority": priority,
        "created_at": now,
        "updated_at": now,
    }

    db[_SURVEY_TASKS].insert_one(task_doc)

    # 7. Update application.assignment
    db[_APPLICATIONS].update_one(
        {"application_id": application_id},
        {"$set": {
            "assignment.assigned_surveyor_id": surveyor_id,
            "assignment.task_id": task_id,
            "assignment.assigned_at": now,
            "updated_at": now,
        }},
    )

    # 8. Increase surveyor workload.active_tasks
    db[_STAFF].update_one(
        {"staff_id": surveyor_id},
        {"$inc": {"workload.active_tasks": 1}, "$set": {"updated_at": now}},
    )

    # 9. Audit log
    log_audit(
        application_id=application_id,
        action="survey_assigned",
        state="survey_required",
        performed_by=f"system:{surveyor_id}",
    )
    log_performance_event(
        application_id=application_id,
        event_type="survey_assigned",
        actor_type="system",
        actor_id="system",
        meta={
            "task_id": task_id,
            "assigned_surveyor_id": surveyor_id,
            "score": assignment["score"],
            "scoring_breakdown": assignment["scoring_breakdown"],
        },
    )

    return {
        "application_id": application_id,
        "task_id": task_id,
        "assigned_surveyor_id": surveyor_id,
        "assigned_surveyor_code": surveyor_code,
        "score": assignment["score"],
        "scoring_breakdown": assignment["scoring_breakdown"],
        "status": "assigned",
    }


# ── Task 8: manual reassign ───────────────────────────────────────────────────

def reassign_surveyor(
    application_id: str,
    new_surveyor_id: str,
    reassigned_by: str,
    reason: str,
) -> Dict[str, Any]:
    """Manually reassign an active survey task to a new surveyor."""

    # 1. Verify new surveyor exists and is active
    new_surveyor = db[_STAFF].find_one({"staff_id": new_surveyor_id}, {"_id": 0})
    if new_surveyor is None:
        raise ValueError(f"New surveyor '{new_surveyor_id}' not found")
    if not new_surveyor.get("active", True):
        raise ValueError(f"New surveyor '{new_surveyor_id}' is inactive")

    # 2. Strict zone coverage check — fetch application to get parcel zone_id
    app = db[_APPLICATIONS].find_one({"application_id": application_id}, {"_id": 0})
    if app is None:
        raise ValueError(f"Application '{application_id}' not found")

    parcel_ref = app.get("parcel_ref") or {}
    app_zone_id = parcel_ref.get("zone_id") if isinstance(parcel_ref, dict) else None

    coverage = new_surveyor.get("coverage") or {}
    surveyor_zones = set(coverage.get("zone_ids") or [])

    if app_zone_id and app_zone_id not in surveyor_zones:
        raise ValueError(
            f"Reassignment rejected: new surveyor '{new_surveyor_id}' does not cover "
            f"zone '{app_zone_id}'. Surveyor covers: {sorted(surveyor_zones)}"
        )

    # 3. Find existing active task
    task = get_active_task_for_application(application_id)
    if task is None:
        raise ValueError(
            f"No active survey task found for application '{application_id}'"
        )

    old_surveyor_id = task["assigned_surveyor_id"]
    now = datetime.now(timezone.utc)

    reassign_entry = {
        "reassigned_from": old_surveyor_id,
        "reassigned_to": new_surveyor_id,
        "reassigned_by": reassigned_by,
        "reason": reason,
        "timestamp": now,
    }

    # 4. Update task
    db[_SURVEY_TASKS].update_one(
        {"task_id": task["task_id"]},
        {
            "$set": {
                "assigned_surveyor_id": new_surveyor_id,
                "assigned_surveyor_code": new_surveyor.get("staff_code", ""),
                "updated_at": now,
            },
            "$push": {"reassignment_history": reassign_entry},
        },
    )

    # 5. Decrease old surveyor workload
    db[_STAFF].update_one(
        {"staff_id": old_surveyor_id},
        {"$inc": {"workload.active_tasks": -1}, "$set": {"updated_at": now}},
    )

    # 6. Increase new surveyor workload
    db[_STAFF].update_one(
        {"staff_id": new_surveyor_id},
        {"$inc": {"workload.active_tasks": 1}, "$set": {"updated_at": now}},
    )

    # 7. Update application assignment
    db[_APPLICATIONS].update_one(
        {"application_id": application_id},
        {"$set": {
            "assignment.assigned_surveyor_id": new_surveyor_id,
            "assignment.reassigned_at": now,
            "updated_at": now,
        }},
    )

    # 8. Audit log
    log_audit(
        application_id=application_id,
        action="survey_reassigned",
        state="survey_required",
        performed_by=reassigned_by,
    )
    log_performance_event(
        application_id=application_id,
        event_type="survey_reassigned",
        actor_type="staff",
        actor_id=reassigned_by,
        meta={
            "task_id": task["task_id"],
            "from_surveyor": old_surveyor_id,
            "to_surveyor": new_surveyor_id,
            "reason": reason,
        },
    )

    updated_task = db[_SURVEY_TASKS].find_one({"task_id": task["task_id"]}, {"_id": 0})
    return _serialize(updated_task)


# ── Task 9: get tasks for a surveyor ─────────────────────────────────────────

def get_tasks_for_surveyor(staff_id: str) -> List[Dict[str, Any]]:
    """Return all survey tasks assigned to a staff member with joined application data."""
    tasks = list(db[_SURVEY_TASKS].find({"assigned_surveyor_id": staff_id}, {"_id": 0}))

    enriched = []
    for task in tasks:
        app_id = task.get("application_id")
        app = db[_APPLICATIONS].find_one({"application_id": app_id}, {"_id": 0}) or {}

        # Extract parcel fields
        parcel_ref = app.get("parcel_ref") or {}
        if isinstance(parcel_ref, dict):
            parcel_number = parcel_ref.get("parcel_number") or parcel_ref.get("parcel_id")
            zone = parcel_ref.get("zone_id")
        else:
            parcel_number = str(parcel_ref)
            zone = None

        enriched.append({
            "task_id": task.get("task_id"),
            "application_id": app_id,
            "parcel_number": parcel_number,
            "zone": zone,
            "priority": task.get("priority") or app.get("priority"),
            "scheduled_visit_date": task.get("scheduled_visit_date"),
            "status": task.get("status"),
            "current_milestone": task.get("status"),
            "report_uploaded": task.get("report_uploaded", False),
            "milestones": task.get("milestones", []),
            "created_at": task.get("created_at"),
            "updated_at": task.get("updated_at"),
        })

    return enriched


# ── Task 10: advance milestone ────────────────────────────────────────────────

def advance_milestone(
    application_id: str,
    milestone: str,
    by: str,
    note: Optional[str] = None,
    meta: Optional[dict] = None,
) -> Dict[str, Any]:
    """
    Advance the survey task for application_id to the given milestone.
    Enforces strict sequential order — no skipping.
    """
    task = get_active_task_for_application(application_id)
    if task is None:
        raise ValueError(f"No active survey task found for application '{application_id}'")

    current_status = task.get("status", "assigned")

    # Validate milestone is in allowed list
    if milestone not in ALLOWED_MILESTONES:
        raise ValueError(
            f"Invalid milestone '{milestone}'. Allowed: {ALLOWED_MILESTONES}"
        )

    # Enforce sequential order — milestone must be exactly the next one
    try:
        current_idx = ALLOWED_MILESTONES.index(current_status)
    except ValueError:
        current_idx = -1

    expected_idx = current_idx + 1
    if expected_idx >= len(ALLOWED_MILESTONES):
        raise ValueError(
            f"Task is already at the final milestone '{current_status}'. No further progress possible."
        )

    expected_milestone = ALLOWED_MILESTONES[expected_idx]
    requested_idx = ALLOWED_MILESTONES.index(milestone)

    if requested_idx != expected_idx:
        raise ValueError(
            f"Cannot jump to milestone '{milestone}'. "
            f"Current: '{current_status}'. Next allowed: '{expected_milestone}'."
        )

    # Only registrars may mark a task as registrar_reviewed
    if milestone == "registrar_reviewed":
        actor = db[_STAFF].find_one({"staff_id": by}, {"role": 1, "_id": 0})
        if actor and actor.get("role") != "registrar":
            raise ValueError(
                f"Milestone 'registrar_reviewed' can only be set by a registrar. "
                f"Actor '{by}' has role '{actor.get('role')}'."
            )

    now = datetime.now(timezone.utc)
    milestone_entry = {
        "milestone": milestone,
        "by": by,
        "note": note,
        "meta": meta or {},
        "timestamp": now,
    }

    update_fields: Dict[str, Any] = {
        "status": milestone,
        "updated_at": now,
    }

    # If visit_scheduled and meta has scheduled_date, store it
    if milestone == "visit_scheduled" and meta and meta.get("scheduled_date"):
        update_fields["scheduled_visit_date"] = meta["scheduled_date"]

    # If report_uploaded, set flag
    if milestone == "report_uploaded":
        update_fields["report_uploaded"] = True

    db[_SURVEY_TASKS].update_one(
        {"task_id": task["task_id"]},
        {
            "$set": update_fields,
            "$push": {"milestones": milestone_entry},
        },
    )

    # Audit log
    log_audit(
        application_id=application_id,
        action=f"survey_milestone_{milestone}",
        state=milestone,
        performed_by=by,
    )
    log_performance_event(
        application_id=application_id,
        event_type=f"survey_milestone_{milestone}",
        actor_type="staff",
        actor_id=by,
        meta={"task_id": task["task_id"], "milestone": milestone, "note": note},
    )

    updated = db[_SURVEY_TASKS].find_one({"task_id": task["task_id"]}, {"_id": 0})
    return _serialize(updated)
