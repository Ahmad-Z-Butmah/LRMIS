from fastapi import APIRouter, HTTPException, status

from app.schemas.objection_schema import ObjectionCreate, ObjectionResponse
from app.services.objection_service import submit_objection

router = APIRouter(prefix="/applications", tags=["objections"])


# ── Task 11: submit objection ──────────────────────────────────────────────────

@router.post(
    "/{application_id}/objections",
    response_model=ObjectionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit an objection for an application",
)
def post_objection(application_id: str, payload: ObjectionCreate):
    result = submit_objection(application_id=application_id, data=payload)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application '{application_id}' not found",
        )
    return result
