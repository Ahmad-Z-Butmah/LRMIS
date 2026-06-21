"""
Analytics service — Tasks 11–14 (original) + Tasks 5–9 (new group analytics).

Collection source of truth:
  Tasks 5–9  : PRIMARY = 'land_applications' (professor-required collection).
               FALLBACK = 'applications' when land_applications is empty.
  Tasks 11–14: 'applications' (Student 1 authoritative workflow collection).
  certificates: queried directly by both sets of tasks.

Fallback is automatic: _get_primary_collection() checks count at call time.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from app.database import db

# ── Collection name constants ─────────────────────────────────────────────────
_LAND_APPLICATIONS = "land_applications"   # professor-required collection
_APPLICATIONS = "applications"             # Student-1 operational collection
_CERTIFICATES = "certificates"
_STAFF = "staff_members"
_SURVEY_TASKS = "survey_tasks"
_SURVEY_REPORTS = "survey_reports"
_PERFORMANCE = "performance_logs"
_OBJECTIONS = "objections"
_PARCELS = "parcels"

# Survey task status sets
_COMPLETED_STATUSES = {"survey_completed", "report_uploaded", "registrar_reviewed"}
_TERMINAL_STATUSES = {"registrar_reviewed", "cancelled"}

# Application statuses
_PENDING_STATUSES = [
    "submitted", "pre_checked", "survey_required",
    "missing_documents", "under_objection",
]
_TERMINAL_APP_STATUSES = {"approved", "certificate_issued", "closed", "rejected"}

# Application types the professor requires
_KNOWN_APP_TYPES = [
    "first_registration",
    "ownership_transfer",
    "parcel_subdivision",
    "parcel_merge",
    "boundary_correction",
    "certificate_request",
]

# Delayed threshold (days): applications pending longer than this are considered delayed
_DELAYED_THRESHOLD_DAYS = 30


# ── Internal helpers ──────────────────────────────────────────────────────────

def _days_between(start: Optional[datetime], end: Optional[datetime]) -> Optional[float]:
    """Return elapsed days between two datetimes, or None if either is missing."""
    if start is None or end is None:
        return None
    delta = end - start
    return round(delta.total_seconds() / 86400, 2)


def _parse_dt(val: Any) -> Optional[datetime]:
    """
    Coerce a value to a NAIVE UTC datetime.
    Accepts datetime objects (aware or naive) or ISO-8601 strings.
    Timezone info is stripped so comparisons are always naive-to-naive,
    avoiding TypeError when mongomock returns naive datetimes.
    """
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.replace(tzinfo=None)
    if isinstance(val, str):
        try:
            dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
            return dt.replace(tzinfo=None)
        except ValueError:
            return None
    return None


def _get_primary_collection():
    """
    Return the analytics source collection.
    Prefers 'land_applications' (professor spec).
    Falls back to 'applications' when land_applications is empty or missing.
    """
    try:
        count = db[_LAND_APPLICATIONS].count_documents({})
    except Exception:
        count = 0
    if count > 0:
        return db[_LAND_APPLICATIONS]
    return db[_APPLICATIONS]


def _compute_average_processing_days(col) -> float:
    """
    Average days from timestamps.submitted_at to timestamps.closed_at
    (preferred) or timestamps.approved_at (fallback) across all docs in col.
    Returns 0.0 when no documents have valid start+end timestamps.
    """
    samples: List[float] = []
    for doc in col.find(
        {},
        {"timestamps": 1, "submitted_at": 1, "_id": 0},
    ):
        ts = doc.get("timestamps") or {}
        start = _parse_dt(ts.get("submitted_at") or doc.get("submitted_at"))
        end = _parse_dt(
            ts.get("closed_at") or ts.get("approved_at")
        )
        d = _days_between(start, end)
        if d is not None and d >= 0:
            samples.append(d)
    return round(sum(samples) / len(samples), 2) if samples else 0.0


def _count_delayed(col) -> int:
    """
    Count non-terminal applications that have been pending longer than
    _DELAYED_THRESHOLD_DAYS. Uses timestamps.submitted_at first, then
    root-level submitted_at as fallback.
    Threshold: {_DELAYED_THRESHOLD_DAYS} days (no SLA defined; professor default).
    """
    # Naive UTC threshold — matches the naive datetimes returned by _parse_dt
    threshold = (datetime.now(timezone.utc) - timedelta(days=_DELAYED_THRESHOLD_DAYS)).replace(tzinfo=None)
    count = 0
    for doc in col.find(
        {"status": {"$nin": list(_TERMINAL_APP_STATUSES)}},
        {"timestamps": 1, "submitted_at": 1, "_id": 0},
    ):
        ts = doc.get("timestamps") or {}
        submitted = _parse_dt(ts.get("submitted_at") or doc.get("submitted_at"))
        if submitted is not None and submitted < threshold:
            count += 1
    return count


# ── Task 11: Surveyor analytics ────────────────────────────────────────────────

def get_surveyor_analytics() -> List[Dict[str, Any]]:
    """
    For each surveyor in staff_members, compute:
      active_tasks, completed_tasks, workload_percentage,
      reports_uploaded, average_task_completion_days.
    """
    surveyors = list(db[_STAFF].find({"role": "surveyor"}, {"_id": 0}))
    result = []

    for s in surveyors:
        sid = s["staff_id"]

        tasks = list(db[_SURVEY_TASKS].find({"assigned_surveyor_id": sid}, {"_id": 0}))

        active_tasks = sum(
            1 for t in tasks if t.get("status") not in _TERMINAL_STATUSES
        )
        completed_tasks = sum(
            1 for t in tasks if t.get("status") in _COMPLETED_STATUSES
        )

        sr_count = db[_SURVEY_REPORTS].count_documents({"surveyor_id": sid})
        if sr_count > 0:
            reports_uploaded = sr_count
            reports_uploaded_source = "survey_reports"
        else:
            reports_uploaded = sum(1 for t in tasks if t.get("report_uploaded") is True)
            reports_uploaded_source = "survey_tasks.report_uploaded"

        completion_days = []
        for t in tasks:
            if t.get("status") in _COMPLETED_STATUSES:
                d = _days_between(t.get("created_at"), t.get("updated_at"))
                if d is not None:
                    completion_days.append(d)
        avg_days = (
            round(sum(completion_days) / len(completion_days), 2)
            if completion_days else 0
        )

        workload = s.get("workload") or {}
        max_tasks = workload.get("max_tasks") or 1
        workload_pct = round(active_tasks / max_tasks * 100, 1)

        result.append({
            "surveyor_id": sid,
            "surveyor_name": s.get("name", ""),
            "active_tasks": active_tasks,
            "completed_tasks": completed_tasks,
            "max_tasks": workload.get("max_tasks", 0),
            "workload_percentage": workload_pct,
            "reports_uploaded": reports_uploaded,
            "reports_uploaded_source": reports_uploaded_source,
            "average_task_completion_days": avg_days,
        })

    return result


# ── Task 12: Registrar analytics ───────────────────────────────────────────────

def get_registrar_analytics() -> List[Dict[str, Any]]:
    """
    For each registrar in staff_members compute review stats.
    assigned_reviews is a GLOBAL proxy (no assigned_registrar_id in schema).

    Task 12: Uses _get_primary_collection() so land_applications is preferred
    over applications when populated.  survey_reports has no registrar fields
    (only task_id, surveyor_id, findings) and is intentionally not queried here.
    """
    registrars = list(db[_STAFF].find({"role": "registrar"}, {"_id": 0}))
    col = _get_primary_collection()
    result = []

    for r in registrars:
        rid = r["staff_id"]

        assigned_reviews = col.count_documents({"status": "legal_review"})

        approved_count = col.count_documents({
            "status": {"$in": ["approved", "certificate_issued", "closed"]},
            "$or": [{"issued_by": rid}, {"rejected_by": rid}],
        })
        rejected_count = col.count_documents({
            "status": "rejected",
            "rejected_by": rid,
        })
        completed_reviews = approved_count + rejected_count

        perf_docs = list(db[_PERFORMANCE].find({"event_stream.by.actor_id": rid}, {"_id": 0}))
        review_times = []
        for pdoc in perf_docs:
            events = pdoc.get("event_stream") or []
            submitted_evt = next(
                (e for e in events if e.get("type") == "application_created"), None
            )
            registrar_evt = next(
                (e for e in events
                 if e.get("by", {}).get("actor_id") == rid
                 and e.get("type") in {"status_changed", "certificate_issued"}),
                None,
            )
            if submitted_evt and registrar_evt:
                d = _days_between(submitted_evt.get("at"), registrar_evt.get("at"))
                if d is not None:
                    review_times.append(d)

        avg_review_time = (
            round(sum(review_times) / len(review_times), 2)
            if review_times else 0
        )

        result.append({
            "registrar_id": rid,
            "registrar_name": r.get("name", ""),
            "assigned_reviews": assigned_reviews,
            "assigned_reviews_is_proxy": True,
            "completed_reviews": completed_reviews,
            "approved_count": approved_count,
            "rejected_count": rejected_count,
            "average_review_time": avg_review_time,
        })

    return result


# ── Task 13: Certificates issued per month ────────────────────────────────────

def get_certificates_per_month() -> List[Dict[str, Any]]:
    """
    Group certificates by issued_at month (YYYY-MM) sorted ascending.
    Primary source: 'certificates' collection (status = 'issued').
    Fallback: performance_logs events of type 'certificate_issued'.
    """
    certs = list(
        db[_CERTIFICATES].find({"status": "issued"}, {"issued_at": 1, "_id": 0})
    )

    month_counts: Dict[str, int] = {}

    if certs:
        for c in certs:
            issued_at = c.get("issued_at")
            if isinstance(issued_at, datetime):
                month_key = issued_at.strftime("%Y-%m")
                month_counts[month_key] = month_counts.get(month_key, 0) + 1
    else:
        for pdoc in db[_PERFORMANCE].find({}, {"event_stream": 1, "_id": 0}):
            for evt in pdoc.get("event_stream") or []:
                if evt.get("type") == "certificate_issued":
                    at = evt.get("at")
                    if isinstance(at, datetime):
                        mk = at.strftime("%Y-%m")
                        month_counts[mk] = month_counts.get(mk, 0) + 1

    return [
        {"month": m, "count": month_counts[m]}
        for m in sorted(month_counts.keys())
    ]


# ── Task 5 (updated): KPI summary ────────────────────────────────────────────

def get_kpis() -> Dict[str, Any]:
    """
    System-wide KPI snapshot.

    Primary collection: land_applications (professor spec).
    Fallback: applications (when land_applications is empty).

    Status groupings:
      pending       = submitted | pre_checked | survey_required |
                      missing_documents | under_objection
      approved      = approved
      rejected      = rejected
      under_objection = under_objection
      missing_docs  = missing_documents

    Delayed threshold: {_DELAYED_THRESHOLD_DAYS} days from submitted_at.
    Terminal statuses (not counted as delayed):
      approved, certificate_issued, closed, rejected.

    Backward-compat fields kept: approved_count, rejected_count,
    survey_required, active_surveyors, active_survey_tasks.
    """
    col = _get_primary_collection()

    total = col.count_documents({})
    pending = col.count_documents({"status": {"$in": _PENDING_STATUSES}})
    approved = col.count_documents({"status": "approved"})
    rejected = col.count_documents({"status": "rejected"})
    under_objection = col.count_documents({"status": "under_objection"})
    missing_docs = col.count_documents({"status": "missing_documents"})
    survey_req = col.count_documents({"status": "survey_required"})

    certs_issued = db[_CERTIFICATES].count_documents({"status": "issued"})
    active_surveyors = db[_STAFF].count_documents({"role": "surveyor", "active": True})
    active_tasks = db[_SURVEY_TASKS].count_documents(
        {"status": {"$nin": list(_TERMINAL_STATUSES)}}
    )

    avg_days = _compute_average_processing_days(col)
    delayed = _count_delayed(col)

    return {
        # Required fields (Tasks 5–9 spec)
        "total_applications": total,
        "pending_applications": pending,
        "approved_applications": approved,
        "rejected_applications": rejected,
        "under_objection_applications": under_objection,
        "missing_documents_applications": missing_docs,
        "certificates_issued": certs_issued,
        "average_processing_days": avg_days,
        "delayed_applications": delayed,
        # Backward-compat fields (existing frontend / Task 11–14 tests)
        "approved_count": approved,
        "rejected_count": rejected,
        "survey_required": survey_req,
        "active_surveyors": active_surveyors,
        "active_survey_tasks": active_tasks,
    }


# ── Task 6: Applications by status ───────────────────────────────────────────

def get_applications_by_status() -> List[Dict[str, Any]]:
    """
    Group applications by status, count each group, sort by count descending.

    Documents with missing status are grouped as 'unknown'.

    Primary collection: land_applications.
    Fallback: applications.
    """
    col = _get_primary_collection()
    pipeline = [
        {
            "$group": {
                "_id": {"$ifNull": ["$status", "unknown"]},
                "count": {"$sum": 1},
            }
        },
        {"$sort": {"count": -1}},
        {"$project": {"_id": 0, "status": "$_id", "count": 1}},
    ]
    return list(col.aggregate(pipeline))


# ── Task 7: Applications by type ─────────────────────────────────────────────

def get_applications_by_type() -> List[Dict[str, Any]]:
    """
    Group applications by application_type.

    Field fallbacks (in order): application_type → type → request_type → 'unknown'.
    All six professor-required types are included even when count = 0.
    Result is sorted by count descending; zero-count types appear last.

    Primary collection: land_applications.
    Fallback: applications.
    """
    col = _get_primary_collection()

    # Use $ifNull chain to support older field names
    pipeline = [
        {
            "$addFields": {
                "_app_type": {
                    "$ifNull": [
                        "$application_type",
                        {"$ifNull": ["$type", {"$ifNull": ["$request_type", "unknown"]}]},
                    ]
                }
            }
        },
        {"$group": {"_id": "$_app_type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$project": {"_id": 0, "application_type": "$_id", "count": 1}},
    ]
    rows = list(col.aggregate(pipeline))

    seen = {r["application_type"] for r in rows}
    for t in _KNOWN_APP_TYPES:
        if t not in seen:
            rows.append({"application_type": t, "count": 0})

    return rows


# ── Task 8: Applications by zone ─────────────────────────────────────────────

def get_applications_by_zone() -> List[Dict[str, Any]]:
    """
    Group applications by parcel zone, returning per-zone counts.

    Zone resolution order:
      1. parcel_ref.zone_id  (when parcel_ref is an embedded dict)
      2. parcels collection lookup by parcel_ref string
      3. 'unknown' when resolution fails

    pending  = submitted | pre_checked | survey_required |
               missing_documents | under_objection
    approved = approved
    rejected = rejected

    Primary collection: land_applications.
    Fallback: applications.
    """
    col = _get_primary_collection()

    # Build parcel_number → zone_id map from parcels collection
    parcel_zone_map: Dict[str, str] = {}
    for p in db[_PARCELS].find(
        {},
        {"parcel_number": 1, "parcel_code": 1, "zone_id": 1, "_id": 0},
    ):
        zone = p.get("zone_id")
        for key in ("parcel_number", "parcel_code"):
            pn = p.get(key)
            if pn and zone:
                parcel_zone_map[pn] = zone

    zone_data: Dict[str, Dict[str, Any]] = {}

    for doc in col.find({}, {"status": 1, "parcel_ref": 1, "_id": 0}):
        status = doc.get("status") or "unknown"
        pr = doc.get("parcel_ref")

        if isinstance(pr, dict):
            zone_id = pr.get("zone_id") or "unknown"
        elif isinstance(pr, str) and pr:
            zone_id = parcel_zone_map.get(pr, "unknown")
        else:
            zone_id = "unknown"

        if zone_id not in zone_data:
            zone_data[zone_id] = {
                "zone_id": zone_id,
                "count": 0,
                "pending": 0,
                "approved": 0,
                "rejected": 0,
            }

        zone_data[zone_id]["count"] += 1

        if status in set(_PENDING_STATUSES):
            zone_data[zone_id]["pending"] += 1
        elif status == "approved":
            zone_data[zone_id]["approved"] += 1
        elif status == "rejected":
            zone_data[zone_id]["rejected"] += 1

    return sorted(zone_data.values(), key=lambda x: x["count"], reverse=True)


# ── Task 9 (replaced): Processing time per application type ──────────────────

def get_processing_time() -> List[Dict[str, Any]]:
    """
    Average processing-time metrics per application_type.

    Timestamp fields used (all from timestamps sub-document):
      submitted_at       — application entry point
      pre_checked_at     — end of pre-check phase
      survey_required_at — survey phase starts
      surveyed_at        — survey completed
      approved_at        — approval decision
      closed_at          — application closed (preferred end for processing)

    Metrics per type:
      average_processing_days   = submitted_at → closed_at (or approved_at)
      average_precheck_days     = submitted_at → pre_checked_at
      average_survey_delay_days = survey_required_at → surveyed_at
      average_approval_days     = surveyed_at → approved_at

    Each metric is computed only from records that have BOTH required timestamps.
    Returns 0.0 for any metric with no valid samples.
    Values are rounded to 2 decimal places.
    sample_count = total applications of that type in the collection.

    All six professor-required application types are always included.
    Primary collection: land_applications. Fallback: applications.
    """
    col = _get_primary_collection()

    # Accumulators keyed by application_type
    buckets: Dict[str, Dict[str, Any]] = {}

    for doc in col.find(
        {},
        {
            "application_type": 1,
            "type": 1,
            "request_type": 1,
            "timestamps": 1,
            "_id": 0,
        },
    ):
        app_type = (
            doc.get("application_type")
            or doc.get("type")
            or doc.get("request_type")
            or "unknown"
        )

        ts = doc.get("timestamps") or {}
        submitted = _parse_dt(ts.get("submitted_at"))
        pre_checked = _parse_dt(ts.get("pre_checked_at"))
        survey_req = _parse_dt(ts.get("survey_required_at"))
        surveyed = _parse_dt(ts.get("surveyed_at"))
        approved = _parse_dt(ts.get("approved_at"))
        closed = _parse_dt(ts.get("closed_at"))

        if app_type not in buckets:
            buckets[app_type] = {
                "processing": [],
                "precheck": [],
                "survey_delay": [],
                "approval": [],
                "sample_count": 0,
            }

        b = buckets[app_type]
        b["sample_count"] += 1

        # processing: submitted → closed (preferred) or approved
        end = closed or approved
        d = _days_between(submitted, end)
        if d is not None and d >= 0:
            b["processing"].append(d)

        # precheck: submitted → pre_checked
        d = _days_between(submitted, pre_checked)
        if d is not None and d >= 0:
            b["precheck"].append(d)

        # survey delay: survey_required → surveyed
        d = _days_between(survey_req, surveyed)
        if d is not None and d >= 0:
            b["survey_delay"].append(d)

        # approval: surveyed → approved
        d = _days_between(surveyed, approved)
        if d is not None and d >= 0:
            b["approval"].append(d)

    def _avg(lst: list) -> float:
        return round(sum(lst) / len(lst), 2) if lst else 0.0

    result = []
    seen_types = set(buckets.keys())

    for app_type, b in buckets.items():
        result.append({
            "application_type": app_type,
            "average_processing_days": _avg(b["processing"]),
            "average_precheck_days": _avg(b["precheck"]),
            "average_survey_delay_days": _avg(b["survey_delay"]),
            "average_approval_days": _avg(b["approval"]),
            "sample_count": b["sample_count"],
        })

    # Ensure all known types appear (with zeroes if not in collection)
    for app_type in _KNOWN_APP_TYPES:
        if app_type not in seen_types:
            result.append({
                "application_type": app_type,
                "average_processing_days": 0.0,
                "average_precheck_days": 0.0,
                "average_survey_delay_days": 0.0,
                "average_approval_days": 0.0,
                "sample_count": 0,
            })

    return sorted(result, key=lambda x: x["sample_count"], reverse=True)


# ── Task 10: Delayed applications list ───────────────────────────────────────

# Terminal statuses for the delayed-applications ENDPOINT (not same as KPI delayed count).
# "approved" is intentionally NOT excluded — an approved app still awaiting certificate is delayed.
_DELAYED_ENDPOINT_TERMINAL = {"closed", "rejected", "certificate_issued"}


def get_delayed_applications(days: int = 7) -> List[Dict[str, Any]]:
    """
    Return non-terminal applications pending longer than `days` days.

    Terminal (excluded): closed, rejected, certificate_issued.
    Note: 'approved' is included — approval alone does not close the workflow.

    Submitted timestamp: timestamps.submitted_at (preferred) → root submitted_at.
    Uses _get_primary_collection() so land_applications is preferred.
    Result is sorted by delayed_days descending.
    """
    col = _get_primary_collection()
    threshold = (datetime.now(timezone.utc) - timedelta(days=days)).replace(tzinfo=None)
    now_naive = datetime.now(timezone.utc).replace(tzinfo=None)

    result = []
    for doc in col.find(
        {"status": {"$nin": list(_DELAYED_ENDPOINT_TERMINAL)}},
        {
            "application_id": 1, "status": 1,
            "application_type": 1, "type": 1, "request_type": 1,
            "parcel_ref": 1, "submitted_at": 1, "timestamps": 1,
            "_id": 0,
        },
    ):
        ts = doc.get("timestamps") or {}
        submitted = _parse_dt(ts.get("submitted_at") or doc.get("submitted_at"))
        if submitted is None or submitted >= threshold:
            continue

        delayed_days_val = round((now_naive - submitted).total_seconds() / 86400, 1)

        pr = doc.get("parcel_ref")
        if isinstance(pr, dict):
            parcel_number = pr.get("parcel_number") or pr.get("parcel_code")
            zone_id = pr.get("zone_id")
        elif isinstance(pr, str) and pr:
            parcel_number = pr
            zone_id = None
        else:
            parcel_number = None
            zone_id = None

        app_type = (
            doc.get("application_type")
            or doc.get("type")
            or doc.get("request_type")
            or "unknown"
        )

        result.append({
            "application_id": doc.get("application_id", ""),
            "status": doc.get("status", "unknown"),
            "application_type": app_type,
            "parcel_number": parcel_number,
            "zone_id": zone_id,
            "submitted_at": submitted.isoformat() if submitted else None,
            "delayed_days": delayed_days_val,
        })

    return sorted(result, key=lambda x: x["delayed_days"], reverse=True)
