from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Query, status

from app.schemas.application_schema import (
    ApplicationCreate,
    ApplicationDetailResponse,
    ApplicationListResponse,
    ApplicationResponse,
    HoldRequest,
    MissingDocumentsRequest,
    RejectRequest,
    TransitionRequest,
)
from app.services.application_service import (
    create_application,
    flag_missing_documents,
    get_application_detail,
    hold_application,
    list_applications,
    reject_application,
    transition_application,
)

router = APIRouter(prefix="/applications", tags=["Applications"])


# ── Task 3: create ────────────────────────────────────────────────────────────

@router.post(
    "/",
    response_model=ApplicationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a new land application",
)
def post_application(
    payload: ApplicationCreate,
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
):
    return create_application(data=payload, idempotency_key=idempotency_key)


# ── Task 5: list ──────────────────────────────────────────────────────────────

@router.get(
    "/",
    response_model=ApplicationListResponse,
    summary="List applications with pagination, filtering, and sorting",
)
def get_applications(
    page: int = Query(default=1, ge=1, description="Page number (1-based)"),
    limit: int = Query(default=10, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(default=None, description="Filter by status"),
    application_type: Optional[str] = Query(default=None, description="Filter by application type"),
    zone_id: Optional[str] = Query(default=None, description="Filter by zone ID"),
    parcel_number: Optional[str] = Query(default=None, description="Filter by parcel number"),
    priority: Optional[str] = Query(default=None, description="Filter by priority"),
    date_from: Optional[datetime] = Query(default=None, description="Filter created_at >= date_from"),
    date_to: Optional[datetime] = Query(default=None, description="Filter created_at <= date_to"),
    sort_by: str = Query(default="created_at", description="Field to sort by"),
    sort_order: str = Query(default="desc", description="Sort direction: asc or desc"),
):
    return list_applications(
        page=page,
        limit=limit,
        status=status,
        application_type=application_type,
        zone_id=zone_id,
        parcel_number=parcel_number,
        priority=priority,
        date_from=date_from,
        date_to=date_to,
        sort_by=sort_by,
        sort_order=sort_order,
    )


# ── Task 6: detail ────────────────────────────────────────────────────────────

@router.get(
    "/{application_id}",
    response_model=ApplicationDetailResponse,
    summary="Get full details of a single application",
)
def get_application(application_id: str):
    detail = get_application_detail(application_id)
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application '{application_id}' not found",
        )
    return detail


# ── Tasks 8/9: transition ─────────────────────────────────────────────────────

@router.patch(
    "/{application_id}/transition",
    response_model=ApplicationResponse,
    summary="Transition application to the next workflow state",
)
def patch_transition(application_id: str, payload: TransitionRequest):
    try:
        result = transition_application(
            application_id=application_id,
            target_state=payload.target_state,
            actor_type=payload.actor_type,
            actor_id=payload.actor_id,
            note=payload.note,
            rejection_reason=payload.rejection_reason,
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


# ── Task 10: hold ─────────────────────────────────────────────────────────────

@router.post(
    "/{application_id}/hold",
    response_model=ApplicationResponse,
    summary="Place an application on hold",
)
def post_hold(application_id: str, payload: HoldRequest):
    try:
        result = hold_application(
            application_id=application_id,
            reason=payload.reason,
            held_by=payload.held_by,
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


# ── Task 11: reject ───────────────────────────────────────────────────────────

@router.post(
    "/{application_id}/reject",
    response_model=ApplicationResponse,
    summary="Reject an application",
)
def post_reject(application_id: str, payload: RejectRequest):
    try:
        result = reject_application(
            application_id=application_id,
            reason=payload.reason,
            rejected_by=payload.rejected_by,
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


# ── Task 12: missing documents ────────────────────────────────────────────────

@router.post(
    "/{application_id}/missing-documents",
    response_model=ApplicationResponse,
    summary="Flag an application as having missing documents",
)
def post_missing_documents(application_id: str, payload: MissingDocumentsRequest):
    try:
        result = flag_missing_documents(
            application_id=application_id,
            missing_documents=payload.missing_documents,
            note_to_applicant=payload.note_to_applicant,
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
