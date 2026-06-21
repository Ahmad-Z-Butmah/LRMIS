from fastapi import APIRouter, HTTPException, status

from typing import List

from app.schemas.comment_schema import CommentCreate, CommentResponse
from app.services.comment_service import add_comment, get_comments_for_application

router = APIRouter(prefix="/applications", tags=["comments"])


# ── GET comments for an application ─────────────────────────────────────────

@router.get(
    "/{application_id}/comments",
    response_model=List[CommentResponse],
    summary="List all comments for an application",
)
def get_comments(application_id: str):
    result = get_comments_for_application(application_id=application_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application '{application_id}' not found",
        )
    return result


# ── Task 9: add applicant comment ─────────────────────────────────────────────

@router.post(
    "/{application_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a comment or response to an application",
)
def post_comment(application_id: str, payload: CommentCreate):
    result = add_comment(application_id=application_id, data=payload)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application '{application_id}' not found",
        )
    return result
