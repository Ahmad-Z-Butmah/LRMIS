from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, ConfigDict


class WorkflowState(BaseModel):
    current_state: str
    allowed_next: List[str]


class ApplicationCreate(BaseModel):
    applicant_ref: str = Field(..., description="Reference to the applicant")
    parcel_ref: Union[Dict, str] = Field(
        ...,
        description=(
            "Either a plain string parcel ID (reference only) "
            "or a full parcel object — when an object is supplied the GeoJSON "
            "geometry and required fields are validated before saving."
        ),
    )
    required_documents: List[str] = Field(default=[], description="Required document identifiers")


class ApplicationResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    application_id: str
    applicant_ref: str
    parcel_ref: Union[Dict, str]
    required_documents: List[str]
    status: str
    workflow: WorkflowState
    created_at: datetime
    updated_at: datetime
    submitted_at: datetime
    application_type: Optional[str] = None
    priority: Optional[str] = None


# ── Task 5 ────────────────────────────────────────────────────────────────────

class ApplicationListResponse(BaseModel):
    items: List[ApplicationResponse]
    total: int
    page: int
    limit: int


# ── Task 6 ────────────────────────────────────────────────────────────────────

class AuditEntry(BaseModel):
    action: str
    state: str
    performed_by: str
    timestamp: datetime


class DocumentStatus(BaseModel):
    name: str
    submitted: bool = False


class ApplicationDetailResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    # Core application fields
    application_id: str
    applicant_ref: str
    parcel_ref: Union[Dict, str]
    required_documents: List[str]
    status: str
    workflow: WorkflowState

    # Timestamps
    created_at: datetime
    updated_at: datetime
    submitted_at: datetime
    application_type: Optional[str] = None
    priority: Optional[str] = None

    # Resolved parcel data (includes GeoJSON geometry)
    parcel_data: Optional[Dict[str, Any]] = None

    # Related statuses (None until the relevant module creates its record)
    documents: List[DocumentStatus] = []
    survey_status: Optional[str] = None
    objection_status: Optional[str] = None
    certificate_status: Optional[str] = None

    # Internal notes — visibility field on each note is left for frontend role filtering
    internal_notes: List[Dict[str, Any]] = []

    # Full audit trail sorted oldest-first
    audit_timeline: List[AuditEntry] = []


# ── Tasks 8/9: transition ─────────────────────────────────────────────────────

class TransitionRequest(BaseModel):
    target_state: str
    actor_type: str
    actor_id: str
    note: Optional[str] = None
    rejection_reason: Optional[str] = None


# ── Task 10: hold ─────────────────────────────────────────────────────────────

class HoldRequest(BaseModel):
    reason: str = Field(..., min_length=1, description="Reason the application is being placed on hold")
    held_by: str = Field(..., description="ID of the staff member placing the hold")


# ── Task 11: reject ───────────────────────────────────────────────────────────

class RejectRequest(BaseModel):
    reason: str = Field(..., min_length=1, description="Reason the application is being rejected")
    rejected_by: str = Field(..., description="ID of the staff member rejecting the application")


# ── Task 12: missing documents ────────────────────────────────────────────────

class MissingDocumentsRequest(BaseModel):
    missing_documents: List[str] = Field(..., min_length=1, description="List of missing document identifiers")
    note_to_applicant: Optional[str] = None
