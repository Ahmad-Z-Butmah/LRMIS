from datetime import datetime, timezone
from typing import Optional
import uuid

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.database import db

router = APIRouter(prefix="/applications", tags=["Survey Reports"])


class SurveyReportUpload(BaseModel):
    surveyor_id: str
    task_id: str
    field_notes: str
    measurements: Optional[dict] = None
    status: str = "pending_review"


@router.post(
    "/{application_id}/survey-report",
    status_code=status.HTTP_201_CREATED,
    summary="Upload a survey report for an application",
)
def post_survey_report(application_id: str, payload: SurveyReportUpload):
    app_doc = db["land_applications"].find_one({"application_id": application_id})
    if app_doc is None:
        app_doc = db["applications"].find_one({"application_id": application_id})
    if app_doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application '{application_id}' not found",
        )
    now = datetime.now(timezone.utc)
    report = {
        "report_id": f"REPORT-{uuid.uuid4().hex[:8].upper()}",
        "application_id": application_id,
        "task_id": payload.task_id,
        "surveyor_id": payload.surveyor_id,
        "status": payload.status,
        "field_notes": payload.field_notes,
        "measurements": payload.measurements or {},
        "submitted_at": now,
        "created_at": now,
    }
    db["survey_reports"].insert_one(report)
    report.pop("_id", None)
    return report
