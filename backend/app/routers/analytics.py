import csv
import io
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query
from fastapi.responses import Response

from app.database import db
from app.services.analytics_service import (
    get_applications_by_status,
    get_applications_by_type,
    get_applications_by_zone,
    get_certificates_per_month,
    get_delayed_applications,
    get_kpis,
    get_processing_time,
    get_registrar_analytics,
    get_surveyor_analytics,
)
from app.services.cache_service import get_cache, set_cache

router = APIRouter(prefix="/analytics", tags=["Analytics"])

_CACHE_TTL = 60  # seconds


# ── Task 11: surveyor analytics ───────────────────────────────────────────────

@router.get(
    "/surveyors",
    summary="Surveyor workload and performance analytics",
)
def get_surveyors_analytics():
    key = "analytics:surveyors"
    cached = get_cache(key)
    if cached is not None:
        return cached
    data = get_surveyor_analytics()
    result = {"surveyors": data, "total": len(data)}
    set_cache(key, result, ttl_seconds=_CACHE_TTL)
    return result


# ── Task 12: registrar analytics ──────────────────────────────────────────────

@router.get(
    "/registrars",
    summary="Registrar workload and review analytics",
)
def get_registrars_analytics():
    key = "analytics:registrars"
    cached = get_cache(key)
    if cached is not None:
        return cached
    data = get_registrar_analytics()
    result = {"registrars": data, "total": len(data)}
    set_cache(key, result, ttl_seconds=_CACHE_TTL)
    return result


# ── Task 13: certificates per month ──────────────────────────────────────────

@router.get(
    "/certificates-per-month",
    summary="Certificates issued per calendar month (YYYY-MM)",
)
def get_certs_per_month():
    return get_certificates_per_month()


# ── Task 5: KPI endpoint ──────────────────────────────────────────────────────

@router.get(
    "/kpis",
    summary="System-wide KPI snapshot (cached 60 s)",
)
def get_kpis_endpoint():
    key = "analytics:kpis"
    cached = get_cache(key)
    if cached is not None:
        return cached
    data = get_kpis()
    set_cache(key, data, ttl_seconds=_CACHE_TTL)
    return data


# ── Task 6: Applications by status ───────────────────────────────────────────

@router.get(
    "/applications-by-status",
    summary="Application counts grouped by status, sorted by count descending",
)
def get_applications_by_status_endpoint():
    key = "analytics:applications-by-status"
    cached = get_cache(key)
    if cached is not None:
        return cached
    data = get_applications_by_status()
    set_cache(key, data, ttl_seconds=_CACHE_TTL)
    return data


# ── Task 7: Applications by type ─────────────────────────────────────────────

@router.get(
    "/applications-by-type",
    summary="Application counts grouped by application_type",
)
def get_applications_by_type_endpoint():
    key = "analytics:applications-by-type"
    cached = get_cache(key)
    if cached is not None:
        return cached
    data = get_applications_by_type()
    set_cache(key, data, ttl_seconds=_CACHE_TTL)
    return data


# ── Task 8: Applications by zone ─────────────────────────────────────────────

@router.get(
    "/applications-by-zone",
    summary="Application counts grouped by parcel zone with pending/approved/rejected breakdown",
)
def get_applications_by_zone_endpoint():
    key = "analytics:applications-by-zone"
    cached = get_cache(key)
    if cached is not None:
        return cached
    data = get_applications_by_zone()
    set_cache(key, data, ttl_seconds=_CACHE_TTL)
    return data


# ── Task 10: Delayed applications ────────────────────────────────────────────

@router.get(
    "/delayed-applications",
    summary="Applications delayed beyond the specified threshold (default 7 days)",
)
def get_delayed_applications_endpoint(days: int = 7):
    key = f"analytics:delayed:{days}"
    cached = get_cache(key)
    if cached is not None:
        return cached
    data = get_delayed_applications(days)
    set_cache(key, data, ttl_seconds=_CACHE_TTL)
    return data


# ── Task 9: Processing time ───────────────────────────────────────────────────

@router.get(
    "/processing-time",
    summary="Average processing time per application type and workflow stage (cached 60 s)",
)
def get_processing_time_endpoint():
    key = "analytics:processing-time"
    cached = get_cache(key)
    if cached is not None:
        return cached
    data = get_processing_time()
    set_cache(key, data, ttl_seconds=_CACHE_TTL)
    return data


# ── Task 23: CSV export — all applications ────────────────────────────────────

@router.get(
    "/export/applications.csv",
    summary="Export all applications as CSV (9 columns)",
    response_class=Response,
)
def export_applications_csv():
    """
    Returns a downloadable CSV with columns:
    application_id, status, application_type, parcel_number, zone_id,
    submitted_at, updated_at, applicant_ref, priority
    """
    cols = [
        "application_id", "status", "application_type", "parcel_number",
        "zone_id", "submitted_at", "updated_at", "applicant_ref", "priority",
    ]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
    writer.writeheader()

    for doc in db["applications"].find({}, {"_id": 0}):
        parcel_ref = doc.get("parcel_ref")
        if isinstance(parcel_ref, dict):
            parcel_number = parcel_ref.get("parcel_number") or parcel_ref.get("parcel_code")
            zone_id = parcel_ref.get("zone_id")
        else:
            parcel_number = str(parcel_ref) if parcel_ref else ""
            zone_id = ""

        ts = doc.get("timestamps") or {}
        submitted_at = doc.get("submitted_at") or ts.get("submitted_at") or ""
        updated_at = doc.get("updated_at") or ts.get("updated_at") or ""

        writer.writerow({
            "application_id":   doc.get("application_id", ""),
            "status":           doc.get("status", ""),
            "application_type": doc.get("application_type", ""),
            "parcel_number":    parcel_number or "",
            "zone_id":          zone_id or "",
            "submitted_at":     str(submitted_at),
            "updated_at":       str(updated_at),
            "applicant_ref":    str(doc.get("applicant_ref", "")),
            "priority":         str(doc.get("priority", "")),
        })

    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=applications.csv"},
    )


# ── Task 24: CSV export — surveyor workload ───────────────────────────────────

@router.get(
    "/export/surveyors.csv",
    summary="Export surveyor workload as CSV (6 columns)",
    response_class=Response,
)
def export_surveyors_csv():
    """
    Returns a downloadable CSV with columns:
    surveyor_id, name, active_tasks, completed_tasks, max_tasks, workload_percentage
    """
    cols = [
        "surveyor_id", "name", "active_tasks", "completed_tasks",
        "max_tasks", "workload_percentage",
    ]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
    writer.writeheader()

    rows = get_surveyor_analytics()
    for r in rows:
        writer.writerow({
            "surveyor_id":        r.get("surveyor_id", ""),
            "name":               r.get("name", ""),
            "active_tasks":       r.get("active_tasks", 0),
            "completed_tasks":    r.get("completed_tasks", 0),
            "max_tasks":          r.get("max_tasks", 0),
            "workload_percentage": r.get("workload_percentage", 0),
        })

    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=surveyors.csv"},
    )


# ── Task 25: Management report (JSON stub) ────────────────────────────────────

@router.get(
    "/export/management-report",
    summary="Structured management report JSON with all analytics sections",
)
def export_management_report(threshold_days: int = Query(30, description="Delayed-application threshold in days")):
    """
    Returns a JSON report combining all analytics sections.
    report_type, generated_at, threshold_days plus all analytic payloads.
    Not a PDF — JSON stub as per Task 25 specification.
    """
    surveyor_data = get_surveyor_analytics()
    registrar_data = get_registrar_analytics()
    return {
        "report_type":           "management_summary",
        "generated_at":         datetime.now(timezone.utc).isoformat(),
        "threshold_days":        threshold_days,
        "kpis":                  get_kpis(),
        "applications_by_status": get_applications_by_status(),
        "applications_by_type":  get_applications_by_type(),
        "applications_by_zone":  get_applications_by_zone(),
        "processing_time":       get_processing_time(),
        "surveyors":             {"surveyors": surveyor_data, "total": len(surveyor_data)},
        "registrars":            {"registrars": registrar_data, "total": len(registrar_data)},
        "delayed_applications":  get_delayed_applications(days=threshold_days),
    }
