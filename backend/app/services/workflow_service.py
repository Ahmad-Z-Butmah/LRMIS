from typing import List

# ---------------------------------------------------------------------------
# State-transition graph
# ---------------------------------------------------------------------------

ALLOWED_TRANSITIONS: dict[str, List[str]] = {
    "submitted":          ["pre_checked", "missing_documents", "on_hold", "rejected"],
    "pre_checked":        ["survey_required", "missing_documents", "on_hold", "rejected"],
    "missing_documents":  ["pre_checked", "rejected"],
    "on_hold":            ["pre_checked", "rejected"],
    "survey_required":    ["surveyed", "on_hold", "rejected"],
    "surveyed":           ["legal_review", "on_hold", "rejected"],
    "legal_review":       ["approved", "under_objection", "rejected"],
    "under_objection":    ["legal_review", "rejected"],
    "approved":           ["certificate_issued"],
    "certificate_issued": ["closed"],
    "closed":             [],
    "rejected":           [],
}


def get_allowed_next_states(current_state: str) -> List[str]:
    """Return the list of states reachable from *current_state*."""
    return list(ALLOWED_TRANSITIONS.get(current_state, []))


def validate_transition(current_state: str, target_state: str) -> None:
    """
    Raise ValueError if *target_state* is not a legal successor of *current_state*
    according to ALLOWED_TRANSITIONS.
    """
    allowed = ALLOWED_TRANSITIONS.get(current_state)
    if allowed is None:
        raise ValueError(f"Unknown state '{current_state}'")
    if target_state not in allowed:
        next_hint = allowed if allowed else ["none — terminal state"]
        raise ValueError(
            f"Transition from '{current_state}' to '{target_state}' is not allowed. "
            f"Allowed next states: {next_hint}"
        )


# ---------------------------------------------------------------------------
# Business-rule pre-condition checks per target state
# ---------------------------------------------------------------------------

def check_transition_requirements(application: dict, target_state: str) -> None:
    """
    Validate that *application* satisfies all pre-conditions required to enter
    *target_state*.  Always calls validate_transition first so callers need
    only this single function.

    *application* may be the plain serialised document (from _serialize) or the
    fully enriched detail dict (from get_application_detail); all lookups use
    .get() so missing keys degrade gracefully.

    Raises ValueError with a descriptive message on the first failed condition.
    """
    current_state = (
        (application.get("workflow") or {}).get("current_state")
        or application.get("status", "")
    )

    # Graph edge check — must pass before business rules are evaluated
    validate_transition(current_state, target_state)

    # ── Pre-conditions per target state ─────────────────────────────────────

    if target_state == "pre_checked":
        if not application.get("applicant_ref"):
            raise ValueError(
                "Cannot move to 'pre_checked': applicant_ref is missing"
            )
        if not application.get("parcel_ref"):
            raise ValueError(
                "Cannot move to 'pre_checked': parcel_ref is missing"
            )

    elif target_state == "survey_required":
        # Parcel must be present; full GeoJSON validation is done by
        # resolve_and_validate_parcel before calling this function.
        if not application.get("parcel_ref"):
            raise ValueError(
                "Cannot move to 'survey_required': parcel_ref is missing"
            )

    elif target_state == "surveyed":
        has_report = bool(application.get("survey_report"))
        has_status = bool(application.get("survey_status"))
        if not has_report and not has_status:
            raise ValueError(
                "Cannot move to 'surveyed': a survey_report or survey_status is required"
            )

    elif target_state == "legal_review":
        # Ownership documents must have been uploaded.
        # Works with the enriched 'documents' list from get_application_detail;
        # if the plain doc is passed, falls back to required_documents strings.
        documents: List[dict] = application.get("documents") or []
        required: List[str] = application.get("required_documents") or []
        ownership_required = [r for r in required if "ownership" in r.lower()]
        if ownership_required:
            uploaded = [
                d for d in documents
                if "ownership" in (d.get("name") or "").lower() and d.get("submitted")
            ]
            if not uploaded:
                raise ValueError(
                    "Cannot move to 'legal_review': ownership documents have not been uploaded"
                )

    elif target_state == "approved":
        if not application.get("legal_review_completed"):
            raise ValueError(
                "Cannot move to 'approved': legal_review_completed must be set to true"
            )

    elif target_state == "certificate_issued":
        # Belt-and-suspenders: the graph already enforces approved -> certificate_issued,
        # but an explicit status check makes the error message unambiguous.
        if current_state != "approved":
            raise ValueError(
                "Cannot move to 'certificate_issued': application must be in 'approved' state"
            )

    elif target_state == "closed":
        if not application.get("certificate_status"):
            raise ValueError(
                "Cannot move to 'closed': no certificate record exists for this application"
            )

    elif target_state == "rejected":
        if not application.get("rejection_reason"):
            raise ValueError(
                "Cannot move to 'rejected': rejection_reason must be provided"
            )

    elif target_state == "under_objection":
        if not application.get("objection_status"):
            raise ValueError(
                "Cannot move to 'under_objection': an objection record must exist "
                "for this application"
            )
