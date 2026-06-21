from fastapi import APIRouter, HTTPException, Query, status

from app.schemas.applicant_schema import (
    ApplicantApplicationsResponse,
    ApplicantCreate,
    ApplicantResponse,
)
from app.services.applicant_service import (
    create_applicant,
    get_applicant,
    get_applicant_applications,
)

router = APIRouter(prefix="/applicants", tags=["applicants"])


# ── Task 2: create applicant profile ──────────────────────────────────────────

@router.post(
    "/",
    response_model=ApplicantResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new applicant profile",
)
def post_applicant(payload: ApplicantCreate):
    try:
        return create_applicant(data=payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )


# ── Task 3: get applicant profile with restricted fields ──────────────────────

@router.get(
    "/{applicant_id}",
    summary="Get applicant profile — full for self, restricted for staff",
)
def get_applicant_profile(
    applicant_id: str,
    viewer_role: str = Query(
        default="staff",
        description="Pass 'applicant' for the full self-view, 'staff' for the privacy-filtered staff view",
    ),
):
    result = get_applicant(applicant_id=applicant_id, viewer_role=viewer_role)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Applicant '{applicant_id}' not found",
        )
    return result


# ── Task 4: get applications linked to an applicant ───────────────────────────

@router.get(
    "/{applicant_id}/applications",
    response_model=ApplicantApplicationsResponse,
    summary="Get all applications linked to an applicant, sorted newest first",
)
def get_applicant_apps(applicant_id: str):
    result = get_applicant_applications(applicant_id=applicant_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Applicant '{applicant_id}' not found",
        )
    return result
