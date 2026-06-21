from typing import Optional
from pydantic import BaseModel

# Phase 0 placeholder — Student 3: Survey Reports
# Collection: survey_reports


class SurveyReportBase(BaseModel):
    task_id: str
    surveyor_id: Optional[str] = None
    findings: Optional[str] = None


class SurveyReportCreate(SurveyReportBase):
    pass


class SurveyReportResponse(SurveyReportBase):
    report_id: str
