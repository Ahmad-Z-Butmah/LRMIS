from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from pymongo import ASCENDING, DESCENDING, ReturnDocument

from app.database import db
from app.schemas.application_schema import ApplicationCreate
from app.services.audit_service import get_audit_timeline, log_audit, log_performance_event
from app.utils.validators import validate_parcel
from app.services.workflow_service import (
    check_transition_requirements,
    get_allowed_next_states,
    validate_transition,
)

_APPLICATIONS = "applications"
_COUNTERS = "counters"
_PARCELS = "parcels"

_ALLOWED_SORT_FIELDS = frozenset(
    {"created_at", "updated_at", "submitted_at", "status", "application_id", "applicant_ref"}
)


# ── Internal helpers ──────────────────────────────────────────────────────────

def _next_application_id() -> str:
    year = datetime.now(timezone.utc).year
    result = db[_COUNTERS].find_one_and_update(
        {"_id": f"applications_{year}"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return f"LRMIS-{year}-{result['seq']:04d}"


def _serialize(doc: dict) -> dict:
    """Strip internal MongoDB fields before returning to the caller."""
    doc = dict(doc)
    doc.pop("_id", None)
    doc.pop("idempotency_key", None)
    return doc


# ── Shared validation helper (also used before survey_required transition) ────

def resolve_and_validate_parcel(parcel_ref: Union[str, dict]) -> dict:
    """
    Resolve a parcel reference to its full data and validate it.

    - dict  → validate directly (parcel data embedded in the request).
    - str   → look up the parcel by parcel_number in the parcels collection,
              raise ValueError if not found, then validate.

    Returns the validated parcel dict.
    Reusable before any workflow transition that requires confirmed parcel
    geometry (e.g. survey_required).
    """
    if isinstance(parcel_ref, dict):
        parcel = parcel_ref
    else:
        parcel = db[_PARCELS].find_one({"parcel_number": parcel_ref})
        if parcel is None:
            raise ValueError(
                f"parcel '{parcel_ref}' not found — "
                "create the parcel record before submitting an application"
            )

    validate_parcel(parcel)
    return parcel


# ── Task 3: create ────────────────────────────────────────────────────────────

def create_application(
    data: ApplicationCreate,
    idempotency_key: Optional[str] = None,
) -> dict:
    # Idempotency: return the existing record unchanged if this key was already used.
    # Validation is skipped — the stored record was already validated on first write.
    if idempotency_key:
        existing = db[_APPLICATIONS].find_one({"idempotency_key": idempotency_key})
        if existing:
            return _serialize(existing)

    # Parcel + GeoJSON validation — always runs, for both string refs and embedded objects.
    resolve_and_validate_parcel(data.parcel_ref)

    now = datetime.now(timezone.utc)
    application_id = _next_application_id()

    doc = {
        "application_id": application_id,
        "applicant_ref": data.applicant_ref,
        "parcel_ref": data.parcel_ref,
        "required_documents": data.required_documents,
        "status": "submitted",
        "workflow": {
            "current_state": "submitted",
            "allowed_next": [
                "pre_checked",
                "missing_documents",
                "on_hold",
                "rejected",
            ],
        },
        "created_at": now,
        "updated_at": now,
        "submitted_at": now,
        "idempotency_key": idempotency_key,
    }

    db[_APPLICATIONS].insert_one(doc)
    log_audit(application_id=application_id, action="submitted", state="submitted")
    log_performance_event(
        application_id=application_id,
        event_type="application_created",
        actor_type="applicant",
        actor_id=data.applicant_ref,
        meta={"parcel_ref": str(data.parcel_ref)},
    )

    return _serialize(doc)


# ── Task 5: list ──────────────────────────────────────────────────────────────

def list_applications(
    page: int = 1,
    limit: int = 10,
    status: Optional[str] = None,
    application_type: Optional[str] = None,
    zone_id: Optional[str] = None,
    parcel_number: Optional[str] = None,
    priority: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
) -> dict:
    query: Dict[str, Any] = {}

    # Direct equality filters
    if status:
        query["status"] = status
    if application_type:
        query["application_type"] = application_type
    if priority:
        query["priority"] = priority

    # Date range on created_at
    date_range: Dict[str, datetime] = {}
    if date_from:
        date_range["$gte"] = date_from
    if date_to:
        date_range["$lte"] = date_to
    if date_range:
        query["created_at"] = date_range

    # Filters that require $or (embedded dict vs string ref) go into $and
    # so they don't overwrite each other on the query dict.
    compound: List[Dict] = []

    if zone_id:
        # Match embedded parcel_ref.zone_id OR string refs whose parcel belongs to this zone
        zone_parcel_numbers = [
            p["parcel_number"]
            for p in db[_PARCELS].find({"zone_id": zone_id}, {"parcel_number": 1, "_id": 0})
            if "parcel_number" in p
        ]
        zone_or: List[Dict] = [{"parcel_ref.zone_id": zone_id}]
        if zone_parcel_numbers:
            zone_or.append({"parcel_ref": {"$in": zone_parcel_numbers}})
        compound.append({"$or": zone_or})

    if parcel_number:
        compound.append(
            {"$or": [
                {"parcel_ref.parcel_number": parcel_number},
                {"parcel_ref": parcel_number},
            ]}
        )

    if compound:
        query["$and"] = compound

    # Sort — reject unknown fields to prevent injection-style abuse
    if sort_by not in _ALLOWED_SORT_FIELDS:
        sort_by = "created_at"
    sort_direction = DESCENDING if sort_order.lower() != "asc" else ASCENDING
    skip = (page - 1) * limit

    total = db[_APPLICATIONS].count_documents(query)
    cursor = (
        db[_APPLICATIONS]
        .find(query, {"_id": 0, "idempotency_key": 0})
        .sort(sort_by, sort_direction)
        .skip(skip)
        .limit(limit)
    )

    return {
        "items": list(cursor),
        "total": total,
        "page": page,
        "limit": limit,
    }


# ── Task 6: detail ────────────────────────────────────────────────────────────

def get_application_detail(application_id: str) -> Optional[dict]:
    app = db[_APPLICATIONS].find_one({"application_id": application_id})
    if app is None:
        return None

    app = _serialize(app)

    # Resolve full parcel data including GeoJSON geometry
    parcel_data: Optional[dict] = None
    parcel_ref = app.get("parcel_ref")
    if isinstance(parcel_ref, dict):
        parcel_data = dict(parcel_ref)
    elif isinstance(parcel_ref, str):
        raw = db[_PARCELS].find_one({"parcel_number": parcel_ref})
        if raw:
            raw.pop("_id", None)
            parcel_data = raw

    # Documents status — compare required list against submitted records
    required_docs = app.get("required_documents", [])
    submitted_names = {
        d["name"]
        for d in db["documents"].find(
            {"application_id": application_id}, {"name": 1, "_id": 0}
        )
        if "name" in d
    }
    documents = [
        {"name": name, "submitted": name in submitted_names}
        for name in required_docs
    ]

    # Survey status (populated by survey module in a later task)
    survey = db["surveys"].find_one(
        {"application_id": application_id}, {"status": 1, "_id": 0}
    )
    survey_status: Optional[str] = survey["status"] if survey else None

    # Objection status
    objection = db["objections"].find_one(
        {"application_id": application_id}, {"status": 1, "_id": 0}
    )
    objection_status: Optional[str] = objection["status"] if objection else None

    # Certificate status
    certificate = db["certificates"].find_one(
        {"application_id": application_id}, {"status": 1, "_id": 0}
    )
    certificate_status: Optional[str] = certificate["status"] if certificate else None

    # Internal notes — each note may carry a `visibility` field ("public" | "internal")
    # for role-based display; all notes are returned here, frontend filters by role.
    notes = [
        {k: v for k, v in n.items() if k != "_id"}
        for n in db["notes"].find({"application_id": application_id})
    ]

    return {
        **app,
        "parcel_data": parcel_data,
        "documents": documents,
        "survey_status": survey_status,
        "objection_status": objection_status,
        "certificate_status": certificate_status,
        "internal_notes": notes,
        "audit_timeline": get_audit_timeline(application_id),
    }


# ── Tasks 8/9: transition ─────────────────────────────────────────────────────

def transition_application(
    application_id: str,
    target_state: str,
    actor_type: str,
    actor_id: str,
    note: Optional[str] = None,
    rejection_reason: Optional[str] = None,
) -> Optional[dict]:
    # 1. Confirm application exists before doing anything
    if db[_APPLICATIONS].find_one({"application_id": application_id}, {"_id": 1}) is None:
        return None

    # 2. Load enriched detail so check_transition_requirements can see documents,
    #    survey_status, objection_status, certificate_status, etc.
    detail = get_application_detail(application_id)
    from_state = (detail.get("workflow") or {}).get("current_state") or detail.get("status", "")

    # Merge request-level fields that the requirement checker needs but aren't
    # stored yet (rejection_reason is written to the DB only after checks pass).
    if rejection_reason:
        detail["rejection_reason"] = rejection_reason

    # 3. Graph-edge validation + business-rule pre-conditions (single call).
    #    Raises ValueError with a human-readable message on any failure.
    check_transition_requirements(detail, target_state)

    # 3b. survey_required requires a fully valid GeoJSON Polygon — run the full
    #     parcel + geometry validation now, not just a presence check.
    if target_state == "survey_required":
        resolve_and_validate_parcel(detail.get("parcel_ref"))

    # 3c. closed requires a certificate that is specifically in "issued" status.
    #     check_transition_requirements only verifies certificate_status is truthy;
    #     this stricter check prevents closing on a revoked or pending certificate.
    if target_state == "closed":
        cert = db["certificates"].find_one(
            {"application_id": application_id}, {"status": 1, "_id": 0}
        )
        if not cert:
            raise ValueError(
                "Cannot move to 'closed': no certificate record exists for this application"
            )
        if cert.get("status") != "issued":
            raise ValueError(
                f"Cannot move to 'closed': certificate status is "
                f"'{cert.get('status')}', must be 'issued'"
            )

    # 4. Atomically update the application document
    now = datetime.now(timezone.utc)
    allowed_next = get_allowed_next_states(target_state)

    set_fields: Dict[str, Any] = {
        "status": target_state,
        "workflow.current_state": target_state,
        "workflow.allowed_next": allowed_next,
        "updated_at": now,
    }
    if rejection_reason:
        set_fields["rejection_reason"] = rejection_reason

    db[_APPLICATIONS].update_one(
        {"application_id": application_id},
        {"$set": set_fields},
    )

    # 5. Persist note in the notes collection (get_application_detail reads from there)
    if note:
        db["notes"].insert_one({
            "application_id": application_id,
            "text": note,
            "actor_type": actor_type,
            "actor_id": actor_id,
            "timestamp": now,
            "visibility": "internal",
        })

    # 6. Audit entry
    log_audit(
        application_id=application_id,
        action=f"transition_to_{target_state}",
        state=target_state,
        performed_by=f"{actor_type}:{actor_id}",
    )
    log_performance_event(
        application_id=application_id,
        event_type="application_closed" if target_state == "closed" else "status_changed",
        actor_type=actor_type,
        actor_id=actor_id,
        meta={"from": from_state, "to": target_state, "note": note},
    )

    # 7. Return the updated application (plain serialised doc, not detail)
    updated = db[_APPLICATIONS].find_one({"application_id": application_id})
    return _serialize(updated)


# ── Task 10: hold ─────────────────────────────────────────────────────────────

def hold_application(
    application_id: str,
    reason: str,
    held_by: str,
) -> Optional[dict]:
    # 1. Confirm the application exists
    app = db[_APPLICATIONS].find_one({"application_id": application_id})
    if app is None:
        return None

    app_data = _serialize(app)

    # 2. Validate the graph edge — on_hold must be reachable from the current state
    current_state = (
        (app_data.get("workflow") or {}).get("current_state")
        or app_data.get("status", "")
    )
    validate_transition(current_state, "on_hold")  # raises ValueError if not allowed

    # 3. Update the application document
    now = datetime.now(timezone.utc)
    allowed_next = get_allowed_next_states("on_hold")

    db[_APPLICATIONS].update_one(
        {"application_id": application_id},
        {"$set": {
            "status": "on_hold",
            "workflow.current_state": "on_hold",
            "workflow.allowed_next": allowed_next,
            "hold_reason": reason,
            "held_by": held_by,
            "held_at": now,
            "updated_at": now,
        }},
    )

    # 4. Internal note
    db["notes"].insert_one({
        "application_id": application_id,
        "text": f"Application placed on hold: {reason}",
        "actor_type": "staff",
        "actor_id": held_by,
        "timestamp": now,
        "visibility": "internal",
    })

    # 5. Audit
    log_audit(
        application_id=application_id,
        action="placed_on_hold",
        state="on_hold",
        performed_by=held_by,
    )
    log_performance_event(
        application_id=application_id,
        event_type="application_on_hold",
        actor_type="staff",
        actor_id=held_by,
        meta={"reason": reason},
    )

    # 6. Return updated document
    updated = db[_APPLICATIONS].find_one({"application_id": application_id})
    return _serialize(updated)


# ── Task 11: reject ───────────────────────────────────────────────────────────

def reject_application(
    application_id: str,
    reason: str,
    rejected_by: str,
) -> Optional[dict]:
    # 1. Confirm the application exists
    app = db[_APPLICATIONS].find_one({"application_id": application_id})
    if app is None:
        return None

    app_data = _serialize(app)

    # 2. Validate the graph edge — rejected must be reachable from the current state
    current_state = (
        (app_data.get("workflow") or {}).get("current_state")
        or app_data.get("status", "")
    )
    validate_transition(current_state, "rejected")

    # 3. Update the application document
    now = datetime.now(timezone.utc)

    db[_APPLICATIONS].update_one(
        {"application_id": application_id},
        {"$set": {
            "status": "rejected",
            "workflow.current_state": "rejected",
            "workflow.allowed_next": get_allowed_next_states("rejected"),
            "rejection_reason": reason,
            "rejected_by": rejected_by,
            "rejected_at": now,
            "updated_at": now,
        }},
    )

    # 4. Audit
    log_audit(
        application_id=application_id,
        action="rejected",
        state="rejected",
        performed_by=rejected_by,
    )
    log_performance_event(
        application_id=application_id,
        event_type="application_rejected",
        actor_type="staff",
        actor_id=rejected_by,
        meta={"reason": reason},
    )

    # 5. Return updated document
    updated = db[_APPLICATIONS].find_one({"application_id": application_id})
    return _serialize(updated)


# ── Task 12: missing documents ────────────────────────────────────────────────

def flag_missing_documents(
    application_id: str,
    missing_documents: list,
    note_to_applicant: Optional[str] = None,
) -> Optional[dict]:
    # 1. Confirm the application exists
    app = db[_APPLICATIONS].find_one({"application_id": application_id})
    if app is None:
        return None

    app_data = _serialize(app)

    # 2. Validate the graph edge
    current_state = (
        (app_data.get("workflow") or {}).get("current_state")
        or app_data.get("status", "")
    )
    validate_transition(current_state, "missing_documents")

    # 3. Update the application document
    now = datetime.now(timezone.utc)
    allowed_next = get_allowed_next_states("missing_documents")

    db[_APPLICATIONS].update_one(
        {"application_id": application_id},
        {"$set": {
            "status": "missing_documents",
            "workflow.current_state": "missing_documents",
            "workflow.allowed_next": allowed_next,
            "missing_documents": missing_documents,
            "updated_at": now,
        }},
    )

    # 4. Applicant-visible note (visibility = "public" so the applicant portal can show it)
    if note_to_applicant:
        db["notes"].insert_one({
            "application_id": application_id,
            "text": note_to_applicant,
            "actor_type": "system",
            "actor_id": "system",
            "timestamp": now,
            "visibility": "public",
        })

    # 5. Audit
    log_audit(
        application_id=application_id,
        action="missing_documents_flagged",
        state="missing_documents",
        performed_by="system",
    )
    log_performance_event(
        application_id=application_id,
        event_type="missing_documents_requested",
        actor_type="system",
        actor_id="system",
        meta={"missing_documents": missing_documents},
    )

    # 6. Return updated document
    updated = db[_APPLICATIONS].find_one({"application_id": application_id})
    return _serialize(updated)
