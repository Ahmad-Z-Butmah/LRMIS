from fastapi import APIRouter, HTTPException, status

from app.schemas.document_schema import (
    DocumentResponse,
    DocumentReviewRequest,
    DocumentUploadPayload,
)
from app.services.document_service import get_documents_for_application, review_document, upload_document

router = APIRouter(prefix="/applications", tags=["documents"])


# ── GET documents for an application ─────────────────────────────────────────

@router.get(
    "/{application_id}/documents",
    response_model=list[DocumentResponse],
    summary="List all uploaded documents for an application (includes real document_id)",
)
def get_documents(application_id: str):
    result = get_documents_for_application(application_id=application_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application '{application_id}' not found",
        )
    return result


# ── Task 6: upload document ────────────────────────────────────────────────────

@router.post(
    "/{application_id}/documents",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a supporting document for an application",
)
def post_document(application_id: str, payload: DocumentUploadPayload):
    result = upload_document(application_id=application_id, data=payload)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application '{application_id}' not found in land_applications",
        )
    return result


# ── Task 7: review document ────────────────────────────────────────────────────

@router.patch(
    "/{application_id}/documents/{document_id}/review",
    response_model=DocumentResponse,
    summary="Review a document — staff changes status to verified or rejected",
)
def patch_document_review(
    application_id: str,
    document_id: str,
    payload: DocumentReviewRequest,
):
    result = review_document(
        application_id=application_id,
        document_id=document_id,
        data=payload,
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found for application '{application_id}'",
        )
    return result
