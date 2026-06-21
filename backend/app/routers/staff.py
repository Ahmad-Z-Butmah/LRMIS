from fastapi import APIRouter, HTTPException, status
from typing import List

from app.schemas.staff_schema import StaffCreate, StaffProfileResponse, StaffResponse
from app.services.staff_service import create_staff, get_staff_profile
from app.services.survey_task_service import get_tasks_for_surveyor

router = APIRouter(prefix="/staff", tags=["Staff"])


# ── Task 2: create staff ──────────────────────────────────────────────────────

@router.post(
    "/",
    response_model=StaffResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a staff member (surveyor / registrar / manager / land_officer)",
)
def post_staff(payload: StaffCreate):
    try:
        result = create_staff(payload.model_dump())
    except ValueError as exc:
        err = str(exc)
        status_code = (
            status.HTTP_409_CONFLICT if "already exists" in err
            else status.HTTP_422_UNPROCESSABLE_ENTITY
        )
        raise HTTPException(status_code=status_code, detail=err)
    return result


# ── Task 3: staff profile ─────────────────────────────────────────────────────

@router.get(
    "/{staff_id}",
    response_model=StaffProfileResponse,
    summary="Get staff profile with workload, assigned tasks and performance summary",
)
def get_staff(staff_id: str):
    profile = get_staff_profile(staff_id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Staff member '{staff_id}' not found",
        )
    return profile


# ── Task 9: surveyor's assigned tasks ────────────────────────────────────────

@router.get(
    "/{staff_id}/survey-tasks",
    summary="Get all survey tasks assigned to a specific staff member",
)
def get_staff_survey_tasks(staff_id: str):
    profile = get_staff_profile(staff_id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Staff member '{staff_id}' not found",
        )
    tasks = get_tasks_for_surveyor(staff_id)
    return {"staff_id": staff_id, "tasks": tasks, "total": len(tasks)}
