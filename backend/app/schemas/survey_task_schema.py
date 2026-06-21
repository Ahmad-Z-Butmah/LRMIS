from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

# ── Milestone definitions ─────────────────────────────────────────────────────

ALLOWED_MILESTONES: List[str] = [
    "assigned",
    "visit_scheduled",
    "arrived_on_site",
    "survey_started",
    "survey_completed",
    "report_uploaded",
    "registrar_reviewed",
]

# Terminal statuses — a task in these states is considered closed
TERMINAL_STATUSES = {"registrar_reviewed", "cancelled"}


# ── Sub-models ────────────────────────────────────────────────────────────────

class MilestoneEntry(BaseModel):
    milestone: str
    by: str
    note: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None
    timestamp: datetime


# ── Request schemas ───────────────────────────────────────────────────────────

class SurveyTaskCreate(BaseModel):
    application_id: str
    parcel_id: Optional[str] = None
    assigned_surveyor_id: str
    priority: Optional[str] = None
    scheduled_visit_date: Optional[str] = None


class SurveyMilestoneUpdate(BaseModel):
    milestone: str = Field(..., description="Must be the immediate next milestone in sequence")
    by: str = Field(..., description="Staff ID or code performing this update")
    note: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None

    @field_validator("milestone")
    @classmethod
    def validate_milestone(cls, v: str) -> str:
        if v not in ALLOWED_MILESTONES:
            raise ValueError(
                f"Invalid milestone '{v}'. "
                f"Allowed milestones: {ALLOWED_MILESTONES}"
            )
        return v


class ManualReassignRequest(BaseModel):
    new_surveyor_id: str = Field(..., description="staff_id of the new surveyor")
    reassigned_by: str = Field(..., description="staff_id or manager ID performing the reassignment")
    reason: str = Field(..., min_length=1, description="Reason for reassignment — required")


# ── Response schemas ──────────────────────────────────────────────────────────

class SurveyTaskResponse(BaseModel):
    task_id: str
    application_id: str
    parcel_id: Optional[str] = None
    assigned_surveyor_id: str
    status: str
    milestones: List[MilestoneEntry] = Field(default_factory=list)
    field_notes: Optional[str] = None
    report_uploaded: bool = False
    scheduled_visit_date: Optional[str] = None
    priority: Optional[str] = None
    created_at: datetime
    updated_at: datetime
