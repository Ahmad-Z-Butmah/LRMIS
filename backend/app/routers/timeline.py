from fastapi import APIRouter, HTTPException, status

from app.services.timeline_service import get_timeline

router = APIRouter(prefix="/applications", tags=["timeline"])


# ── Task 12: application timeline ─────────────────────────────────────────────

@router.get(
    "/{application_id}/timeline",
    summary="Get the full status timeline and event history for an application",
)
def get_application_timeline(application_id: str):
    result = get_timeline(application_id=application_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application '{application_id}' not found",
        )
    return result
