"""
Analytics Pydantic schemas — Tasks 3–9.

Schemas for KPI, status/type/zone breakdowns, processing time,
and compatibility schemas for existing surveyor/registrar/geofeed endpoints.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel


# ── Task 5: KPI snapshot ──────────────────────────────────────────────────────

class KPIResponse(BaseModel):
    # Required new fields
    total_applications: int
    pending_applications: int
    approved_applications: int
    rejected_applications: int
    under_objection_applications: int
    missing_documents_applications: int
    certificates_issued: int
    average_processing_days: float
    delayed_applications: int
    # Backward-compat fields kept for existing frontend/tests
    approved_count: int = 0
    rejected_count: int = 0
    survey_required: int = 0
    active_surveyors: int = 0
    active_survey_tasks: int = 0


# ── Task 6: Applications by status ───────────────────────────────────────────

class ApplicationsByStatusResponse(BaseModel):
    status: str
    count: int


# ── Task 7: Applications by type ─────────────────────────────────────────────

class ApplicationsByTypeResponse(BaseModel):
    application_type: str
    count: int


# ── Task 8: Applications by zone ─────────────────────────────────────────────

class ApplicationsByZoneResponse(BaseModel):
    zone_id: str
    count: int
    pending: int
    approved: int
    rejected: int


# ── Task 9: Processing time per application type ──────────────────────────────

class ProcessingTimeResponse(BaseModel):
    application_type: str
    average_processing_days: float
    average_precheck_days: float
    average_survey_delay_days: float
    average_approval_days: float
    sample_count: int


# ── Task 11 compat: Surveyor analytics ───────────────────────────────────────

class SurveyorAnalyticsResponse(BaseModel):
    surveyor_id: str
    surveyor_name: str
    active_tasks: int
    completed_tasks: int
    max_tasks: int
    workload_percentage: float
    reports_uploaded: int
    average_task_completion_days: float
    reports_uploaded_source: Optional[str] = None


# ── Task 12 compat: Registrar analytics ──────────────────────────────────────

class RegistrarAnalyticsResponse(BaseModel):
    registrar_id: str
    registrar_name: str
    assigned_reviews: int
    completed_reviews: int
    approved_count: int
    rejected_count: int
    average_review_time: float
    assigned_reviews_is_proxy: Optional[bool] = None


# ── Task 10: Delayed applications ────────────────────────────────────────────

class DelayedApplicationResponse(BaseModel):
    application_id: str
    status: str
    application_type: str
    parcel_number: Optional[str] = None
    zone_id: Optional[str] = None
    submitted_at: Optional[str] = None
    delayed_days: float


# ── Task 15/16/17/18/19/20 compat: GeoJSON wrapper ───────────────────────────

class GeoFeedResponse(BaseModel):
    type: str
    features: List[Any]
