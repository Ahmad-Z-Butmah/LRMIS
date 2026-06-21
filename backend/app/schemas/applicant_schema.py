from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ApplicantType(str, Enum):
    citizen = "citizen"
    lawyer = "lawyer"
    company = "company"
    surveyor = "surveyor"
    authorized_representative = "authorized_representative"


class VerificationState(str, Enum):
    unverified = "unverified"
    verified = "verified"
    suspended = "suspended"


class IdentityInfo(BaseModel):
    national_id: Optional[str] = None
    registration_number: Optional[str] = None

    @model_validator(mode="after")
    def require_at_least_one_id(self) -> "IdentityInfo":
        if not self.national_id and not self.registration_number:
            raise ValueError(
                "At least one of national_id or registration_number is required"
            )
        return self


class ContactInfo(BaseModel):
    email: str = Field(..., min_length=1)
    phone: str = Field(...)


class AddressInfo(BaseModel):
    city: str = Field(...)
    neighborhood: str = Field(...)
    zone_id: str = Field(...)


class NotificationPreferences(BaseModel):
    on_status_change: bool
    on_missing_documents: bool
    on_certificate_ready: bool


class ApplicantPreferences(BaseModel):
    preferred_language: str = Field(...)
    preferred_contact: Optional[str] = None
    notifications: NotificationPreferences


class PrivacySettings(BaseModel):
    show_phone_to_staff: bool
    show_email_to_staff: bool


# ── Task 2: create request schema ─────────────────────────────────────────────

class ApplicantCreate(BaseModel):
    full_name: str = Field(..., min_length=1)
    applicant_type: ApplicantType
    identity: IdentityInfo
    contacts: ContactInfo
    address: AddressInfo
    preferences: ApplicantPreferences
    privacy_settings: PrivacySettings
    verification_state: VerificationState = VerificationState.unverified
    linked_applications: List[str] = Field(default_factory=list)


# ── Task 2: create response schema ────────────────────────────────────────────

class ApplicantResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    applicant_id: str
    full_name: str
    applicant_type: str
    identity: IdentityInfo
    contacts: ContactInfo
    address: AddressInfo
    preferences: ApplicantPreferences
    privacy_settings: PrivacySettings
    verification_state: str
    linked_applications: List[str]
    created_at: datetime
    updated_at: datetime


# ── Task 3: profile view response (self or staff) ─────────────────────────────
# identity and contacts are typed as Any because their shape changes based on
# viewer_role: full dict for self-view, masked/filtered dict for staff-view.

class ApplicantProfileResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    applicant_id: str
    full_name: str
    applicant_type: str
    identity: Any              # full for self, masked for staff
    contacts: Any              # full for self, privacy-filtered for staff
    address: Any
    verification_state: str
    preferred_language: str
    linked_applications: List[str]
    # Present in self-view only; omitted from staff-view
    preferences: Optional[Any] = None
    privacy_settings: Optional[Any] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ── Task 4: applicant applications response ───────────────────────────────────

class ApplicantApplicationItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    application_id: str
    application_type: Optional[str] = None
    status: str
    parcel_number: Optional[str] = None
    zone_id: Optional[str] = None
    submitted_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    required_next_step: Optional[str] = None


class ApplicantApplicationsResponse(BaseModel):
    applicant_id: str
    total: int
    applications: List[ApplicantApplicationItem]
