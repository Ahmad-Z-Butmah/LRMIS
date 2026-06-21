from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class DocumentStatus(str, Enum):
    uploaded = "uploaded"
    pending_review = "pending_review"
    verified = "verified"
    rejected = "rejected"
    missing = "missing"


# ── Task 5: document schemas ──────────────────────────────────────────────────

class DocumentCreate(BaseModel):
    application_id: str = Field(...)
    applicant_id: Optional[str] = None
    document_type: str = Field(...)
    filename: str = Field(...)
    file_url: Optional[str] = None
    file_path: Optional[str] = None
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = None
    uploaded_by: Optional[str] = None


class DocumentResponse(BaseModel):
    document_id: str
    application_id: str
    applicant_id: Optional[str] = None
    document_type: str
    filename: str
    file_url: Optional[str] = None
    file_path: Optional[str] = None
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = None
    status: DocumentStatus
    uploaded_at: datetime
    uploaded_by: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_note: Optional[str] = None


class DocumentReviewRequest(BaseModel):
    status: DocumentStatus
    reviewed_by: str = Field(...)
    review_note: Optional[str] = None


class DocumentUploadPayload(BaseModel):
    """Upload body — application_id is taken from the URL path, not the body."""
    applicant_id: Optional[str] = None
    document_type: str = Field(...)
    filename: str = Field(...)
    file_url: Optional[str] = None
    file_path: Optional[str] = None
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = None
    uploaded_by: Optional[str] = None
