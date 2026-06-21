from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class ObjectionStatus(str, Enum):
    submitted = "submitted"
    under_review = "under_review"
    accepted = "accepted"
    rejected = "rejected"
    resolved = "resolved"


# ── Task 10: objection schemas ────────────────────────────────────────────────

class ObjectionCreate(BaseModel):
    submitted_by_applicant_id: str = Field(...)
    reason: str = Field(..., min_length=1, description="Reason for objection — must not be empty")
    supporting_documents: List[str] = Field(default_factory=list)


class ObjectionResponse(BaseModel):
    objection_id: str
    application_id: str
    submitted_by_applicant_id: str
    reason: str
    supporting_documents: List[str]
    status: str
    submitted_at: datetime
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    decision_note: Optional[str] = None
