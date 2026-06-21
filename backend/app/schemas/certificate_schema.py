from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class IssuedTo(BaseModel):
    full_name: str = Field(..., description="Full legal name of the certificate holder")
    national_id: str = Field(..., description="National ID number of the holder")
    address: str = Field(..., description="Registered address of the holder")


# application_id and parcel_id are derived server-side from the application document;
# only the fields the client must supply are included here.
class CertificateCreate(BaseModel):
    certificate_type: str = Field(..., description="E.g. ownership, lease, provisional")
    issued_to: IssuedTo
    issued_by: str = Field(..., description="Name or ID of the issuing officer")
    qr_code_url: Optional[str] = Field(default=None)
    digital_signature_stub: Optional[str] = Field(default=None)


class CertificateResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    certificate_id: str = Field(..., description="Unique certificate identifier (CERT-YYYY-NNNN)")
    application_id: str
    applicant_ref: str
    parcel_id: str
    certificate_type: str
    status: str = Field(default="issued", description="Current status: issued | revoked | expired")
    issued_to: IssuedTo
    issued_at: datetime
    issued_by: str
    qr_code_url: Optional[str] = None
    digital_signature_stub: Optional[str] = None


class CertificateVerification(BaseModel):
    certificate_id: str
    parcel_id: str
    certificate_type: str
    status: str
    issued_to: IssuedTo
    issued_at: datetime
    is_valid: bool = Field(..., description="True if the certificate is currently active and unrevoked")
