from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class CommentVisibility(str, Enum):
    applicant_visible = "applicant_visible"
    staff_only = "staff_only"


# ── Task 8: comment schemas ───────────────────────────────────────────────────

class CommentCreate(BaseModel):
    comment_text: str = Field(..., min_length=1, description="Comment body — must not be empty")
    created_by: str = Field(...)
    actor_type: str = Field(...)
    visibility: CommentVisibility = CommentVisibility.applicant_visible


class CommentResponse(BaseModel):
    comment_id: str
    application_id: str
    comment_text: str
    created_by: str
    actor_type: str
    created_at: datetime
    visibility: str
