from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

# ── Constants ─────────────────────────────────────────────────────────────────

ALLOWED_ROLES = {"surveyor", "registrar", "manager", "land_officer"}


# ── Sub-models ────────────────────────────────────────────────────────────────

class Shift(BaseModel):
    day: str = Field(..., description="Day abbreviation e.g. Mon, Tue")
    start: str = Field(..., description="Start time HH:MM")
    end: str = Field(..., description="End time HH:MM")


class StaffSchedule(BaseModel):
    timezone: str = Field(..., description="IANA timezone e.g. Asia/Jerusalem")
    shifts: List[Shift] = Field(default_factory=list)
    on_call: bool = False


class CoverageZone(BaseModel):
    zone_ids: List[str] = Field(..., min_length=1, description="List of zone IDs this surveyor covers")
    geo_fence: Optional[Dict[str, Any]] = Field(
        default=None,
        description="GeoJSON Polygon defining the geo-fence boundary",
    )

    @field_validator("geo_fence")
    @classmethod
    def validate_geo_fence(cls, v: Optional[Dict]) -> Optional[Dict]:
        if v is None:
            return v
        if v.get("type") != "Polygon":
            raise ValueError("geo_fence must be a GeoJSON Polygon (type='Polygon')")
        if "coordinates" not in v or not isinstance(v["coordinates"], list):
            raise ValueError("geo_fence.coordinates is required and must be a list")
        return v


class StaffWorkload(BaseModel):
    active_tasks: int = Field(default=0, ge=0, description="Current number of active tasks")
    max_tasks: int = Field(default=10, ge=0, description="Maximum allowed concurrent tasks")


class StaffContacts(BaseModel):
    email: EmailStr = Field(..., description="Staff email address")
    phone: str = Field(..., min_length=7, description="Staff phone number")


# ── Request schemas ───────────────────────────────────────────────────────────

class StaffCreate(BaseModel):
    staff_code: str = Field(..., min_length=1, description="Unique staff identifier code")
    name: str = Field(..., min_length=1)
    role: str = Field(..., description="Staff role: surveyor | registrar | manager | land_officer")
    department: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    coverage: Optional[CoverageZone] = None
    schedule: Optional[StaffSchedule] = None
    workload: StaffWorkload = Field(default_factory=StaffWorkload)
    contacts: StaffContacts

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in ALLOWED_ROLES:
            raise ValueError(
                f"Invalid role '{v}'. Allowed roles: {sorted(ALLOWED_ROLES)}"
            )
        return v

    @model_validator(mode="after")
    def surveyor_requires_coverage(self) -> "StaffCreate":
        if self.role == "surveyor":
            if self.coverage is None:
                raise ValueError("Surveyors must have a coverage zone (coverage is required)")
            if not self.coverage.zone_ids:
                raise ValueError("Surveyors must have at least one coverage.zone_ids entry")
        return self


# ── Response schemas ──────────────────────────────────────────────────────────

class StaffResponse(BaseModel):
    staff_id: str
    staff_code: str
    name: str
    role: str
    department: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    coverage: Optional[CoverageZone] = None
    schedule: Optional[StaffSchedule] = None
    workload: StaffWorkload = Field(default_factory=StaffWorkload)
    contacts: StaffContacts
    active: bool = True
    created_at: datetime


class StaffProfileResponse(StaffResponse):
    assigned_task_count: int = 0
    assigned_tasks: List[Dict[str, Any]] = Field(default_factory=list)
    performance_summary: Dict[str, Any] = Field(default_factory=dict)
