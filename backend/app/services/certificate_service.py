from datetime import datetime, timezone
from typing import Optional

from pymongo import ReturnDocument

from app.database import db
from app.services.audit_service import log_audit, log_performance_event
from app.services.workflow_service import get_allowed_next_states

_CERTIFICATES = "certificates"
_COUNTERS = "counters"
_APPLICATIONS = "applications"


def _next_certificate_id() -> str:
    year = datetime.now(timezone.utc).year
    result = db[_COUNTERS].find_one_and_update(
        {"_id": f"certificates_{year}"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return f"CERT-{year}-{result['seq']:04d}"


def _serialize(doc: dict) -> dict:
    doc = dict(doc)
    doc.pop("_id", None)
    return doc


def generate_certificate(
    application_id: str,
    certificate_type: str,
    issued_to: dict,
    issued_by: str,
    qr_code_url: Optional[str] = None,
    digital_signature_stub: Optional[str] = None,
) -> Optional[dict]:
    # 1. Verify application exists
    app = db[_APPLICATIONS].find_one({"application_id": application_id})
    if app is None:
        return None  # → 404 at router

    # 2. Application must be in "approved" status
    current_status = app.get("status")
    if current_status != "approved":
        raise ValueError(
            f"Certificate can only be generated for approved applications "
            f"(current status: '{current_status}')"
        )

    # 3. Prevent duplicate certificates
    if db[_CERTIFICATES].find_one({"application_id": application_id}):
        raise ValueError(
            f"A certificate already exists for application '{application_id}'"
        )

    # 4. Required fields must be present on the application
    applicant_ref = app.get("applicant_ref")
    parcel_ref = app.get("parcel_ref")
    if not applicant_ref:
        raise ValueError("Cannot generate certificate: applicant_ref is missing on the application")
    if not parcel_ref:
        raise ValueError("Cannot generate certificate: parcel_ref is missing on the application")

    # Normalise parcel_ref to a string for the certificate's parcel_id field
    if isinstance(parcel_ref, dict):
        parcel_id = parcel_ref.get("parcel_number") or str(parcel_ref)
    else:
        parcel_id = parcel_ref

    # 5. Build and insert the certificate document
    now = datetime.now(timezone.utc)
    certificate_id = _next_certificate_id()

    cert_doc = {
        "certificate_id": certificate_id,
        "application_id": application_id,
        "applicant_ref": applicant_ref,
        "parcel_id": parcel_id,
        "certificate_type": certificate_type,
        "status": "issued",
        "issued_to": issued_to,
        "issued_at": now,
        "issued_by": issued_by,
        "qr_code_url": qr_code_url or f"/certificates/{certificate_id}/qr",
        "digital_signature_stub": (
            digital_signature_stub or f"SIG-{certificate_id}-{now.strftime('%Y%m%d')}"
        ),
    }

    db[_CERTIFICATES].insert_one(cert_doc)

    # 6. Advance the application to "certificate_issued"
    db[_APPLICATIONS].update_one(
        {"application_id": application_id},
        {"$set": {
            "status": "certificate_issued",
            "workflow.current_state": "certificate_issued",
            "workflow.allowed_next": get_allowed_next_states("certificate_issued"),
            "updated_at": now,
        }},
    )

    # 7. Audit log
    log_audit(
        application_id=application_id,
        action="certificate_issued",
        state="certificate_issued",
        performed_by=issued_by,
    )
    log_performance_event(
        application_id=application_id,
        event_type="certificate_issued",
        actor_type="staff",
        actor_id=issued_by,
        meta={"certificate_id": certificate_id},
    )

    return _serialize(cert_doc)
