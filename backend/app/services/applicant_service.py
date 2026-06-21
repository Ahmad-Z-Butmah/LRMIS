from datetime import datetime, timezone
from typing import Optional

from pymongo import DESCENDING, ReturnDocument

from app.database import db
from app.schemas.applicant_schema import ApplicantCreate

_APPLICANTS = "applicants"
_COUNTERS = "counters"
_LAND_APPLICATIONS = "land_applications"


# ── Internal helpers ───────────────────────────────────────────────────────────

def _next_applicant_id() -> str:
    year = datetime.now(timezone.utc).year
    result = db[_COUNTERS].find_one_and_update(
        {"_id": f"applicants_{year}"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return f"APL-{year}-{result['seq']:04d}"


def _serialize(doc: dict) -> dict:
    doc = dict(doc)
    doc.pop("_id", None)
    return doc


def _mask_id(value: Optional[str]) -> Optional[str]:
    """Mask all but the first 2 and last 2 characters of an ID string."""
    if not value:
        return value
    if len(value) <= 4:
        return "***"
    return value[:2] + "*" * (len(value) - 4) + value[-2:]


# ── Task 2: create applicant profile ──────────────────────────────────────────

def create_applicant(data: ApplicantCreate) -> dict:
    if data.identity.national_id:
        if db[_APPLICANTS].find_one(
            {"identity.national_id": data.identity.national_id}, {"_id": 1}
        ) is not None:
            raise ValueError(
                f"national_id '{data.identity.national_id}' already registered"
            )

    now = datetime.now(timezone.utc)
    applicant_id = _next_applicant_id()

    doc = {
        "applicant_id": applicant_id,
        "full_name": data.full_name,
        "applicant_type": data.applicant_type,
        "identity": data.identity.model_dump(),
        "contacts": data.contacts.model_dump(),
        "address": data.address.model_dump(),
        "preferences": data.preferences.model_dump(),
        "privacy_settings": data.privacy_settings.model_dump(),
        "verification_state": "unverified",
        "linked_applications": data.linked_applications,
        "created_at": now,
        "updated_at": now,
    }

    db[_APPLICANTS].insert_one(doc)
    return _serialize(doc)


# ── Task 3: get applicant profile with field restrictions ─────────────────────

def get_applicant(applicant_id: str, viewer_role: str = "staff") -> Optional[dict]:
    doc = db[_APPLICANTS].find_one({"applicant_id": applicant_id})
    if doc is None:
        return None
    doc = _serialize(doc)

    preferences = doc.get("preferences", {})

    if viewer_role == "applicant":
        # Self-view: return complete profile
        return doc

    # Staff view: restrict sensitive fields
    privacy = doc.get("privacy_settings", {})
    identity = doc.get("identity", {})
    contacts = doc.get("contacts", {})

    masked_identity = {
        "national_id": _mask_id(identity.get("national_id")),
        "registration_number": _mask_id(identity.get("registration_number")),
    }

    # Respect privacy_settings — null means staff cannot see the field
    staff_contacts = {
        "email": contacts.get("email") if privacy.get("show_email_to_staff", True) else None,
        "phone": contacts.get("phone") if privacy.get("show_phone_to_staff", True) else None,
    }

    return {
        "applicant_id": doc["applicant_id"],
        "full_name": doc["full_name"],
        "applicant_type": doc["applicant_type"],
        "identity": masked_identity,
        "contacts": staff_contacts,
        "address": doc.get("address"),
        "verification_state": doc.get("verification_state"),
        "preferred_language": preferences.get("preferred_language"),
        "linked_applications": doc.get("linked_applications", []),
    }


# ── Task 4: get applications linked to an applicant ───────────────────────────

def get_applicant_applications(applicant_id: str) -> Optional[dict]:
    if db[_APPLICANTS].find_one({"applicant_id": applicant_id}, {"_id": 1}) is None:
        return None

    cursor = (
        db[_LAND_APPLICATIONS]
        .find(
            {"applicant_ref": applicant_id},
            {"_id": 0, "idempotency_key": 0},
        )
        .sort("submitted_at", DESCENDING)
    )

    applications = []
    for app in cursor:
        parcel_ref = app.get("parcel_ref")
        if isinstance(parcel_ref, str):
            parcel_number = parcel_ref
            zone_id = None
        elif isinstance(parcel_ref, dict):
            parcel_number = parcel_ref.get("parcel_number")
            zone_id = parcel_ref.get("zone_id")
        else:
            parcel_number = None
            zone_id = None

        workflow = app.get("workflow", {})
        allowed_next = workflow.get("allowed_next", [])

        applications.append({
            "application_id": app.get("application_id"),
            "application_type": app.get("application_type"),
            "status": app.get("status"),
            "parcel_number": parcel_number,
            "zone_id": zone_id,
            "submitted_at": app.get("submitted_at"),
            "updated_at": app.get("updated_at"),
            # First allowed transition represents the required next step
            "required_next_step": allowed_next[0] if allowed_next else None,
        })

    return {
        "applicant_id": applicant_id,
        "total": len(applications),
        "applications": applications,
    }
