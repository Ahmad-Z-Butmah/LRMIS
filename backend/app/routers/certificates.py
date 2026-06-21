from fastapi import APIRouter, HTTPException, status

from app.schemas.certificate_schema import CertificateCreate, CertificateResponse
from app.services.certificate_service import generate_certificate

router = APIRouter(prefix="/applications", tags=["Certificates"])


@router.post(
    "/{application_id}/certificate",
    response_model=CertificateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a land title certificate for an approved application",
)
def post_certificate(application_id: str, payload: CertificateCreate):
    try:
        result = generate_certificate(
            application_id=application_id,
            certificate_type=payload.certificate_type,
            issued_to=payload.issued_to.model_dump(),
            issued_by=payload.issued_by,
            qr_code_url=payload.qr_code_url,
            digital_signature_stub=payload.digital_signature_stub,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application '{application_id}' not found",
        )
    return result
