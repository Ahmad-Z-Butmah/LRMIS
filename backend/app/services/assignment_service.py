from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.database import db

_STAFF = "staff_members"
_SURVEY_TASKS = "survey_tasks"


# ── Scoring constants ─────────────────────────────────────────────────────────

SCORE_ZONE_MATCH = 50
SCORE_AVAILABLE_TODAY = 20
SCORE_SKILL_MATCH = 20
SCORE_HIGH_PRIORITY = 10
SCORE_PER_ACTIVE_TASK = -5

# Day abbreviations used in schedule.shifts (Mon, Tue, Wed, Thu, Fri, Sat, Sun)
_WEEKDAY_MAP = {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun"}


def _today_abbr() -> str:
    return _WEEKDAY_MAP[datetime.now(timezone.utc).weekday()]


# ── Internal helpers ──────────────────────────────────────────────────────────

def _is_available_today(surveyor: dict) -> bool:
    """Return True if the surveyor has a shift scheduled for today."""
    schedule = surveyor.get("schedule") or {}
    shifts = schedule.get("shifts") or []
    today = _today_abbr()
    return any(s.get("day") == today for s in shifts)


def _active_task_count(surveyor_id: str) -> int:
    """Count non-terminal tasks currently assigned to this surveyor."""
    from app.schemas.survey_task_schema import TERMINAL_STATUSES
    return db[_SURVEY_TASKS].count_documents({
        "assigned_surveyor_id": surveyor_id,
        "status": {"$nin": list(TERMINAL_STATUSES)},
    })


# ── Main scoring function ─────────────────────────────────────────────────────

def score_surveyor(
    surveyor: dict,
    zone_id: Optional[str],
    required_skills: List[str],
    priority: Optional[str],
) -> Dict[str, Any]:
    """
    Score a single surveyor candidate.
    Returns a dict with:
      - score (int)
      - breakdown (dict of rule -> points applied)
      - eligible (bool)
      - rejection_reason (str | None)
    """
    breakdown: Dict[str, int] = {}
    score = 0

    # Hard reject: inactive surveyor
    if not surveyor.get("active", True):
        return {"score": 0, "breakdown": {}, "eligible": False, "rejection_reason": "surveyor is inactive"}

    # Hard reject: workload full
    workload = surveyor.get("workload") or {}
    max_tasks = workload.get("max_tasks", 10)
    active_tasks = _active_task_count(surveyor["staff_id"])

    if active_tasks >= max_tasks:
        return {
            "score": 0,
            "breakdown": {},
            "eligible": False,
            "rejection_reason": f"workload full ({active_tasks}/{max_tasks} tasks)",
        }

    # Zone match
    coverage = surveyor.get("coverage") or {}
    zone_ids = coverage.get("zone_ids") or []
    if zone_id and zone_id in zone_ids:
        score += SCORE_ZONE_MATCH
        breakdown["zone_match"] = SCORE_ZONE_MATCH
    else:
        breakdown["zone_match"] = 0

    # Available today
    if _is_available_today(surveyor):
        score += SCORE_AVAILABLE_TODAY
        breakdown["available_today"] = SCORE_AVAILABLE_TODAY
    else:
        breakdown["available_today"] = 0

    # Skill match — each matching skill adds to a shared +20 pool
    surveyor_skills = set(surveyor.get("skills") or [])
    matched_skills = surveyor_skills.intersection(set(required_skills)) if required_skills else set()
    if matched_skills:
        score += SCORE_SKILL_MATCH
        breakdown["skill_match"] = SCORE_SKILL_MATCH
    else:
        breakdown["skill_match"] = 0

    # High priority bonus
    if priority == "high":
        score += SCORE_HIGH_PRIORITY
        breakdown["high_priority"] = SCORE_HIGH_PRIORITY
    else:
        breakdown["high_priority"] = 0

    # Active task penalty
    task_penalty = active_tasks * abs(SCORE_PER_ACTIVE_TASK)
    score -= task_penalty
    breakdown["active_task_penalty"] = -task_penalty

    return {
        "score": score,
        "breakdown": breakdown,
        "eligible": True,
        "rejection_reason": None,
        "active_tasks": active_tasks,
    }


# ── Public API ────────────────────────────────────────────────────────────────

def find_best_surveyor(
    zone_id: Optional[str],
    required_skills: Optional[List[str]] = None,
    priority: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Evaluate all active surveyors and return the best match with scoring breakdown.

    Returns:
      {
        "surveyor": <staff doc>,
        "score": int,
        "scoring_breakdown": dict,
        "all_candidates": list of {staff_id, score, breakdown, eligible}
      }

    Raises ValueError if no eligible surveyor is found.
    """
    required_skills = required_skills or []

    surveyors = list(db[_STAFF].find({"role": "surveyor"}, {"_id": 0}))
    if not surveyors:
        raise ValueError("No surveyors found in staff_members collection")

    candidates = []
    for s in surveyors:
        result = score_surveyor(
            surveyor=s,
            zone_id=zone_id,
            required_skills=required_skills,
            priority=priority,
        )
        candidates.append({
            "staff_id": s["staff_id"],
            "staff_code": s.get("staff_code", ""),
            "name": s.get("name", ""),
            "score": result["score"],
            "breakdown": result["breakdown"],
            "eligible": result["eligible"],
            "rejection_reason": result.get("rejection_reason"),
            "active_tasks": result.get("active_tasks"),
        })

    eligible = [c for c in candidates if c["eligible"]]
    if not eligible:
        reasons = [
            f"{c['staff_id']}: {c['rejection_reason']}"
            for c in candidates
            if not c["eligible"]
        ]
        raise ValueError(
            f"No eligible surveyor found. Rejection reasons: {reasons}"
        )

    # Pick highest score — deterministic (stable sort by staff_id as tiebreaker)
    best = max(eligible, key=lambda c: (c["score"], c["staff_id"]))
    surveyor_doc = db[_STAFF].find_one({"staff_id": best["staff_id"]}, {"_id": 0})

    return {
        "surveyor": surveyor_doc,
        "score": best["score"],
        "scoring_breakdown": best["breakdown"],
        "all_candidates": candidates,
    }
