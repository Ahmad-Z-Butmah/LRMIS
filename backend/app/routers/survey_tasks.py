from fastapi import APIRouter, HTTPException, status

from app.schemas.survey_task_schema import (
    ManualReassignRequest,
    SurveyMilestoneUpdate,
    SurveyTaskResponse,
)
from app.services.survey_task_service import (
    advance_milestone,
    auto_assign_surveyor,
    get_tasks_for_surveyor,
    reassign_surveyor,
)

router = APIRouter(tags=["Survey Tasks"])


# ── Task 6 + 7: auto-assign (with duplicate prevention) ──────────────────────

@router.post(
    "/applications/{application_id}/auto-assign-surveyor",
    status_code=status.HTTP_201_CREATED,
    summary="Auto-assign the best surveyor to a survey_required application",
)
def post_auto_assign(application_id: str):
    try:
        result = auto_assign_surveyor(application_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    return result


# ── Task 8: manual reassign ───────────────────────────────────────────────────

@router.patch(
    "/applications/{application_id}/reassign-surveyor",
    summary="Manually reassign a survey task to a different surveyor",
)
def patch_reassign(application_id: str, payload: ManualReassignRequest):
    try:
        result = reassign_surveyor(
            application_id=application_id,
            new_surveyor_id=payload.new_surveyor_id,
            reassigned_by=payload.reassigned_by,
            reason=payload.reason,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    return result


# ── Task 10: survey milestone ─────────────────────────────────────────────────

@router.patch(
    "/applications/{application_id}/survey-milestone",
    response_model=SurveyTaskResponse,
    summary="Advance survey task to the next milestone (sequential order enforced)",
)
def patch_survey_milestone(application_id: str, payload: SurveyMilestoneUpdate):
    try:
        result = advance_milestone(
            application_id=application_id,
            milestone=payload.milestone,
            by=payload.by,
            note=payload.note,
            meta=payload.meta,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    return result
