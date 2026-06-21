# LRMIS — Land Registration and Management Information System

---

## Student 1 Module: Land Application Management

### 1. Module Overview

Student 1 implemented the **Land Application Management** backend module for LRMIS using **FastAPI**, **MongoDB**, and **PyMongo**. The module handles the full lifecycle of a land application, from initial submission through pre-check, survey, legal review, approval, certificate generation, and closure. It enforces strict workflow transitions, idempotent creation, parcel validation, and full audit logging.

---

### 2. Implemented Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/applications/` | Create a new land application with idempotency key support |
| `GET` | `/applications/` | List applications with pagination, filtering, and sorting |
| `GET` | `/applications/{application_id}` | Get full application details including workflow, parcel, documents, survey, objection, certificate, notes, and audit timeline |
| `PATCH` | `/applications/{application_id}/transition` | Move an application through the workflow using strict transition rules |
| `POST` | `/applications/{application_id}/hold` | Put an application on hold with a reason |
| `POST` | `/applications/{application_id}/reject` | Reject an application with a required reason |
| `POST` | `/applications/{application_id}/missing-documents` | Mark required documents as missing and add an applicant-facing note |
| `POST` | `/applications/{application_id}/certificate` | Generate a certificate after approval |

---

### 3. Workflow States

| State | Description |
|-------|-------------|
| `submitted` | Application has been submitted by the applicant |
| `pre_checked` | Initial pre-check completed by staff |
| `survey_required` | A land survey has been requested |
| `surveyed` | Survey report has been submitted and attached |
| `legal_review` | Application is under legal review |
| `approved` | Application has been approved and is ready for certificate generation |
| `certificate_issued` | An ownership certificate has been generated |
| `closed` | Application is fully closed after certificate issuance |
| `rejected` | Application has been rejected with a reason |
| `on_hold` | Application is paused pending external action |
| `missing_documents` | Required documents are missing; applicant has been notified |
| `under_objection` | An objection has been filed against the application |

---

### 4. Transition Rules

#### Main Workflow

```
submitted → pre_checked → survey_required → surveyed → legal_review → approved → certificate_issued → closed
```

#### Alternative States

`rejected`, `on_hold`, `missing_documents`, and `under_objection` can be reached from active states as side-branches. They are not part of the linear approval path.

#### Invalid Transition Examples

| Attempted Transition | Result |
|----------------------|--------|
| `submitted → approved` | Not allowed — intermediate steps are required |
| `survey_required → surveyed` without a survey report | Fails validation |
| `legal_review → approved` without legal review completion | Fails validation |
| Certificate generation before `approved` state | Rejected |
| `certificate_issued → closed` without an issued certificate | Rejected |

---

### 5. Validation Rules

Parcel validation checks that the following fields are present and valid:

- `parcel_number`
- `block_number`
- `basin_number`
- `zone_id`
- GeoJSON `Polygon` geometry type
- Coordinates array exists and is non-empty
- Polygon ring is closed (first and last coordinate must match)
- Coordinates use `[longitude, latitude]` ordering

---

### 6. MongoDB Collections

| Collection | Purpose |
|------------|---------|
| `applications` | Core application records (alias used in some routes) |
| `land_applications` | Primary collection for land application documents |
| `parcels` | Parcel definitions with GeoJSON geometry |
| `certificates` | Issued ownership certificates |
| `audit_logs` | Full audit trail of all state changes and actions |
| `performance_logs` | Endpoint response time and performance tracking |
| `notes` | Internal staff notes attached to applications |
| `documents` | Document metadata and upload references |
| `counters` | Auto-incrementing sequence generator for application IDs |

---

### 7. MongoDB Indexes

| Collection | Field(s) | Type |
|------------|----------|------|
| `land_applications` | `application_id` | Unique |
| `land_applications` | `status` | Standard |
| `land_applications` | `application_type` | Standard |
| `land_applications` | `parcel_ref.parcel_number` | Standard |
| `land_applications` | `parcel_ref.zone_id` | Standard |
| `land_applications` | `timestamps.submitted_at` | Standard |
| `parcels` | `parcel_code` | Unique |
| `parcels` | `geometry` | 2dsphere |
| `certificates` | `certificate_id` | Unique |

---

### 8. Seed Data

`seed_data.py` populates the database with a consistent baseline for testing:

- **5 parcels** with valid GeoJSON polygons
- **6 land applications** covering different workflow states (submitted, pre_checked, approved, certificate_issued, etc.)
- **2 certificates** linked to approved applications
- **Performance logs** for sample requests
- All required **MongoDB indexes**

---

### 9. How to Run and Test

#### Start MongoDB

```bash
docker start lrmis-mongo
```

If the container does not exist yet:

```bash
docker run -d --name lrmis-mongo -p 27017:27017 mongo:7
```

#### Run the Backend

```bash
cd backend
python -m uvicorn app.main:app --reload --port 8001
```

#### Run Seed Data

```bash
python -m app.seed.seed_data
```

#### Open Swagger UI

```
http://127.0.0.1:8001/docs
```

#### Postman Collection

```
docs/postman/Student1_Land_Application_Management.postman_collection.json
```

Import this file into Postman to test all endpoints manually. Some requests mutate application state (transitions, hold, reject, certificate generation). Reset the seed before repeated testing to restore the expected starting states.

---

### 10. Example API Requests

#### Create Application

```http
POST /applications/
Content-Type: application/json
Idempotency-Key: test-create-001
```

```json
{
  "applicant_ref": "APPL-TEST-001",
  "parcel_ref": "P-001",
  "required_documents": ["national_id", "ownership_deed"]
}
```

#### Valid Transition

```http
PATCH /applications/LRMIS-2026-0001/transition
Content-Type: application/json
```

```json
{
  "target_state": "pre_checked",
  "actor_type": "staff",
  "actor_id": "staff_14",
  "note": "Initial pre-check completed"
}
```

#### Generate Certificate

```http
POST /applications/LRMIS-2026-0004/certificate
Content-Type: application/json
```

```json
{
  "certificate_type": "ownership",
  "issued_to": {
    "full_name": "Test User",
    "national_id": "999999999",
    "address": "Ramallah"
  },
  "issued_by": "registrar_09"
}
```

> **Prerequisite:** The application must be in `approved` state and must not already have a certificate issued. Run `seed_data.py` to restore this state if needed.

---

### 11. Testing Summary

The following cases were verified through Swagger and the Postman collection:

| Test Case | Expected Result |
|-----------|----------------|
| Create application | 201 Created with new application ID |
| Duplicate create with same idempotency key | Returns existing application (no duplicate) |
| List applications with filters | 200 OK with filtered, paginated list |
| Get application details | 200 OK with full application object |
| `submitted → pre_checked` | Success |
| `submitted → approved` | Fail — invalid transition |
| `survey_required → surveyed` without survey report | Fail — validation error |
| `legal_review → approved` without legal review completion | Fail — validation error |
| Reject without reason | Fail — validation error |
| Certificate before `approved` | Fail — precondition not met |
| Certificate after `approved` | Success |
| `certificate_issued → closed` | Success |

---

### 12. Integration Points with Student 2 and Student 3

#### Student 2 (Frontend)

Student 2 built the frontend UI that consumes Student 1 backend endpoints. The following pages and components depend directly on these APIs:

- **Applicant Dashboard** — lists applications via `GET /applications/`
- **Submit Application** — creates applications via `POST /applications/`
- **Application Confirmation** — displays result from create response
- **Track Application** — fetches details via `GET /applications/{application_id}`
- **Upload Documents UI** — uses document and missing-documents endpoints
- **Submit Objection UI** — uses the `under_objection` workflow state
- **Timeline component** — renders audit history from application detail response
- **StatusBadge component** — maps application state to UI label and color

Frontend API integration lives in `frontend/src/api/applicationsApi.js`.

#### Student 3 / Other Modules

The following integration points are available for Student 3 or other downstream modules:

- Document upload and review hooks
- Survey report submission (triggers `survey_required → surveyed`)
- Legal review completion (triggers `legal_review → approved`)
- Objection filing and resolution
- Certificate verification
- Authentication and role-based access (actor type enforcement per transition)
- Admin and staff workflow management screens

---

## Student 2 Module: Applicant Portal and Profiles

### 1. Module Overview

Student 2 implemented the **Applicant Portal and Profiles** module for LRMIS. This module manages applicant identity, document lifecycle, comments, objections, timeline aggregation, and notification stubs. It integrates directly with the land applications created by Student 1 and provides the Staff Console frontend for processing applications end-to-end.

The module is built on **FastAPI** (port 8001), **MongoDB** via **PyMongo**, and a **React/Vite** frontend (port 5173).

---

### 2. Implemented Backend Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/applicants/` | Create a new applicant profile |
| `GET` | `/applicants/{applicant_id}` | Get applicant profile — full for self-view, privacy-filtered for staff view |
| `GET` | `/applicants/{applicant_id}/applications` | List all land applications linked to an applicant, sorted newest first |
| `GET` | `/applications/{application_id}/documents` | List all documents uploaded for an application |
| `POST` | `/applications/{application_id}/documents` | Upload a supporting document for an application |
| `PATCH` | `/applications/{application_id}/documents/{document_id}/review` | Staff reviews a document and sets its status (verified / rejected) |
| `GET` | `/applications/{application_id}/comments` | List all comments for an application |
| `POST` | `/applications/{application_id}/comments` | Add a comment or internal note to an application |
| `POST` | `/applications/{application_id}/objections` | Submit a formal objection against an application |
| `GET` | `/applications/{application_id}/timeline` | Get the full chronological event timeline for an application |

The `viewer_role` query parameter on `GET /applicants/{applicant_id}` controls data visibility:
- `viewer_role=applicant` — full self-view including preferences and privacy_settings
- `viewer_role=staff` — privacy-filtered: national_id masked, email/phone hidden per applicant's privacy_settings

---

### 3. MongoDB Collections

| Collection | Purpose |
|------------|---------|
| `applicants` | Applicant identity, contacts, address, preferences, privacy_settings, verification_state |
| `application_documents` | Document metadata, upload records, review status — primary Student 2 document store |
| `application_comments` | Applicant and staff comments with visibility control |
| `objections` | Formal objection records linked to land applications |
| `performance_logs` | Workflow event stream used by the timeline endpoint (shared with Student 1) |
| `notification_logs` | Notification stub records — populated by seed_student2.py and notification_service |
| `documents` | Compatibility collection — Student 1's detail endpoint reads stubs from here; Student 2 writes to both |
| `counters` | Auto-incrementing sequence generator for applicant_id, document_id, comment_id, objection_id, notification_id |

---

### 4. Applicant Types

| Type | Description |
|------|-------------|
| `citizen` | Individual Palestinian citizen |
| `lawyer` | Licensed legal representative |
| `company` | Registered corporate entity |
| `surveyor` | Licensed land surveyor |
| `authorized_representative` | Agent acting on behalf of another party |

At least one of `national_id` or `registration_number` is required in the `identity` object. Companies typically use `registration_number`; citizens and surveyors use `national_id`.

---

### 5. Verification States

| State | Description |
|-------|-------------|
| `unverified` | Default on creation — identity not yet confirmed |
| `verified` | Identity confirmed by staff — applicant can proceed |
| `suspended` | Account suspended — applicant cannot submit or track applications |

New applicants always start as `unverified`.

---

### 6. Document Statuses

| Status | Description |
|--------|-------------|
| `uploaded` | Document received but not yet queued for review |
| `pending_review` | Set automatically on upload — document is in the review queue |
| `verified` | Staff confirmed the document is valid |
| `rejected` | Staff rejected the document — applicant must resubmit |
| `missing` | Flagged as absent — applicant has been notified |

---

### 7. Objection Flow

**Successful objection (reason provided):**
1. Applicant submits `POST /applications/{application_id}/objections` with a non-empty `reason`
2. Objection record created in `objections` collection with `status: submitted`
3. Application moves to `status: under_objection`
4. `workflow.allowed_next` becomes `["legal_review", "rejected"]`
5. `objection.has_objection` set to `true` on the application

**Failed objection (empty reason):**
- Pydantic schema rejects the request at the API layer (`min_length=1`)
- Response: `422 Unprocessable Entity` — no database write occurs

**After `under_objection`:**
- Staff can transition to `legal_review` or `rejected`

---

### 8. Timeline Source

`GET /applications/{application_id}/timeline` aggregates events from five sources:

| Source | Event Types |
|--------|-------------|
| `performance_logs.event_stream` | Workflow lifecycle events logged by audit_service |
| `land_applications.timestamps` | `submitted`, `pre_checked`, `approved`, `rejected`, `completed` |
| `application_documents` | `document_uploaded`, `document_verified`, `document_rejected` |
| `application_comments` | `comment_added` |
| `objections` | `objection_submitted` |

All events are sorted chronologically by their `at` timestamp.

---

### 9. Notification Stubs

There is **no direct HTTP endpoint** for notification stubs.

The notification system is implemented as an internal service in `backend/app/services/notification_service.py`. When triggered it writes a record to `notification_logs` with `status: "stub"` — no real email or SMS is sent.

**Designed trigger events:**

| Event Type | Trigger Action |
|------------|---------------|
| `status_changed` | Workflow state transitions |
| `missing_documents_requested` | `POST /applications/{id}/missing-documents` |
| `document_reviewed` | `PATCH /applications/{id}/documents/{doc_id}/review` |
| `objection_submitted` | `POST /applications/{id}/objections` |
| `certificate_ready` | `POST /applications/{id}/certificate` |

**Current status:** The `create_notification_stub()` function is fully defined and correctly writes to `notification_logs`, but the wiring between trigger services and the notification service is not yet implemented. No service currently calls it.

Running `python -m app.seed.seed_student2` populates `notification_logs` with 5 pre-seeded stubs (NOTIF-2026-S001 to NOTIF-2026-S005) covering all 5 event types, each with `status: "stub"` and `message: "[STUB] ..."`.

---

### 10. Staff Console UI Pages

| Route | Component | Purpose |
|-------|-----------|---------|
| `/staff/dashboard` | `StaffDashboard.jsx` | KPI summary of application counts by status; filterable list with navigation to individual applications |
| `/staff/applications` | `ApplicationManagement.jsx` | Full paginated application list with status, type, and zone filters |
| `/staff/applications/:id` | `ApplicationDetails.jsx` | Full application detail: parcel map, workflow action buttons (pre-check, survey, legal review, approve, hold, reject, missing-docs), document review panel, internal notes, timeline |
| `/staff/registrar-review` | `RegistrarReview.jsx` | Registrar queue for applications in `legal_review` state with document review and transition controls |
| `/staff/registrar-review/:applicationId` | `RegistrarReview.jsx` | Same page pre-loaded for a specific application |
| `/staff/certificates` | `CertificateIssuance.jsx` | Lists applications in `approved` state and allows certificate generation |

The `DocumentReviewPanel` component is embedded in both `ApplicationDetails` and `RegistrarReview` and calls `PATCH /applications/{id}/documents/{doc_id}/review` directly. The `Timeline` component renders events from `GET /applications/{id}/timeline`.

---

### 11. Integration with Student 1

Student 2 extends Student 1's infrastructure without modifying it:

| Student 1 Asset | How Student 2 Uses It |
|-----------------|----------------------|
| `POST /applications/` | Applicant portal creates applications; `applicant_ref` links to the applicant profile |
| `GET /applications/{id}` | `ApplicationDetails.jsx` and `TrackApplication.jsx` read full application state |
| `GET /applications/` | `StaffDashboard.jsx` and `ApplicationManagement.jsx` list and filter applications |
| `PATCH /applications/{id}/transition` | Staff Console triggers all workflow state transitions |
| `POST /applications/{id}/hold` | Staff Console places applications on hold |
| `POST /applications/{id}/reject` | Staff Console rejects applications |
| `POST /applications/{id}/missing-documents` | Staff Console flags missing documents |
| `POST /applications/{id}/certificate` | `CertificateIssuance.jsx` generates certificates after approval |
| `land_applications` collection | Document service reads `required_documents` and updates `submitted_document_types` and `document_status_map` |
| `performance_logs` collection | Timeline service reads `event_stream` created by Student 1's audit_service |
| `documents` collection | Document service writes compatibility stubs so Student 1's detail endpoint reflects uploaded documents |
| Application `status` field | `StatusBadge` component maps all 12 workflow states to UI colors and labels |

---

### 12. How to Test

#### Start MongoDB

```bash
docker start lrmis-mongo
```

#### Run the Backend

```bash
cd backend
python -m uvicorn app.main:app --reload --port 8001
```

#### Run Seed Data

```bash
# From the backend/ directory
python -m app.seed.seed_data        # Student 1 seed — land_applications, parcels, certificates
python -m app.seed.seed_student2    # Student 2 seed — applicants, documents, comments, objections, notification_logs
```

#### Open Swagger UI

```
http://127.0.0.1:8001/docs
```

Student 2 endpoints appear under tags: `applicants`, `documents`, `comments`, `objections`, `timeline`.

#### Run the Frontend

```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

#### Postman Collection

```
docs/postman/Student2_Applicant_Portal_and_Profiles.postman_collection.json
```

Import into Postman and set variables: `base_url`, `applicant_id`, `application_id`, `document_id`.

#### Testing Checklist

| Test Case | Expected Result |
|-----------|----------------|
| Create applicant | 201 Created with generated `applicant_id` (APL-YYYY-NNNN) |
| Create applicant with duplicate `national_id` | 409 Conflict — service checks for duplicate national_id and returns explicit conflict error |
| Get applicant `viewer_role=applicant` | 200 with full profile |
| Get applicant `viewer_role=staff` | 200 with masked national_id, filtered contacts |
| Get applicant applications | 200 with linked application list |
| Upload document to existing application | 201 Created with `status: pending_review` |
| Upload document to non-existent application | 404 Not Found |
| Review document — verify | 200 OK with updated status and `reviewed_at` |
| Review document — reject | 200 OK with rejection note |
| Add applicant comment | 201 Created, appears in timeline |
| Add staff-only comment | 201 Created with `visibility: staff_only` |
| Submit objection with reason | 201 Created; application moves to `under_objection` |
| Submit objection with empty reason | 422 Unprocessable Entity |
| Get timeline | 200 OK with sorted events from all 5 sources |
| Notification stubs | Inspect `notification_logs` collection after running seed_student2.py |

---

### 13. Known Integration Points with Student 3

| Area | Details |
|------|---------|
| **Registrar backend extension** | `legal_review → approved` transition may be extended with a dedicated registrar review endpoint |
| **Survey tasks and reports** | `survey_required → surveyed` transition may be linked to a survey assignment system for `surveyor` applicant type |
| **Map and live analytics** | `ApplicationDetails.jsx` uses Leaflet for parcel maps; Student 3 may add live GIS overlays or a map analytics dashboard |
| **Staff assignments** | `reviewed_by` and `actor_id` fields use free-text IDs; Student 3 may introduce a staff users collection and assignment system |
| **Notification delivery** | `create_notification_stub()` is ready to be wired to a real email/SMS delivery backend; Student 3 can convert `status: stub` to `status: sent` |
| **Applicant authentication** | Current system uses `applicant_id` strings without authentication; Student 3 may add JWT auth and enforce `viewer_role` server-side |
| **Advanced objection review** | `objections` collection has `reviewed_by`, `reviewed_at`, `decision_note` fields ready for a full legal review workflow via new endpoints |

---

## Student 3 Module: Surveyor Assignment, Map Analytics, and Group Analytics

### 1. Module Overview

Student 3 implemented the **Survey Team Management**, **GIS Map Analytics**, and **Group Analytics** backend modules for LRMIS. The module covers the full surveyor assignment lifecycle, real-time geospatial feeds, a comprehensive analytics dashboard, and an in-memory cache layer.

---

### 2. Implemented Backend Endpoints

#### Staff Management (Tasks 1–3)

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/staff/` | Create a new staff member (surveyor or registrar) with schema validation |
| `GET` | `/staff/{staff_id}` | Get staff profile with assigned task count and performance summary |
| `GET` | `/staff/{staff_id}/survey-tasks` | List all survey tasks assigned to a staff member |

#### Survey Task Assignment (Tasks 6–10)

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/applications/{app_id}/auto-assign-surveyor` | Auto-assign the best available surveyor using scoring algorithm |
| `PATCH` | `/applications/{app_id}/reassign-surveyor` | Manually reassign survey task to a different surveyor |
| `PATCH` | `/applications/{app_id}/survey-milestone` | Advance survey task to the next milestone (sequential order enforced) |

#### Analytics Endpoints (Tasks 5–14)

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/analytics/kpis` | System-wide KPI snapshot (9 required fields + compat fields, cached 60s) |
| `GET` | `/analytics/applications-by-status` | Application counts grouped by status, sorted descending |
| `GET` | `/analytics/applications-by-type` | All 6 known application types always included, zero-count included |
| `GET` | `/analytics/applications-by-zone` | Zone breakdown with pending/approved/rejected counts |
| `GET` | `/analytics/processing-time` | Average processing time per application type (4 metrics) |
| `GET` | `/analytics/delayed-applications` | Applications pending longer than `?days=7` (default 7) |
| `GET` | `/analytics/surveyors` | Per-surveyor workload and performance metrics |
| `GET` | `/analytics/registrars` | Per-registrar review stats (global proxy count) |
| `GET` | `/analytics/certificates-per-month` | Certificates issued per calendar month |

#### GIS/Map Endpoints (Tasks 15–20)

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/analytics/geofeeds/parcels` | GeoJSON FeatureCollection of all parcels with dispute state |
| `GET` | `/analytics/geofeeds/pending-applications` | Pending applications with zone_id as GeoJSON features |
| `GET` | `/analytics/geofeeds/pending-heatmap` | Zone-level heatmap (count + intensity [0,1]) |
| `GET` | `/analytics/geofeeds/disputed-parcels` | Parcels with active objections |
| `GET` | `/analytics/geofeeds/survey-tasks` | Active survey tasks with parcel geometry |

---

### 3. Surveyor Assignment Algorithm (Task 5)

Surveyors are scored on four weighted criteria:

| Criterion | Points |
|-----------|--------|
| Zone coverage match | +50 |
| Available today (schedule shift) | +20 |
| Skill match (required skills all present) | +20 |
| High-priority application | +10 |
| Active task penalty (per task above 0) | −5 each |

Ineligible if: `active=False`, or `active_tasks >= max_tasks`.

---

### 4. Survey Milestone Workflow

Milestones advance **strictly sequentially** — no jumping allowed:

```
assigned → visit_scheduled → arrived_on_site → survey_started
         → survey_completed → report_uploaded → registrar_reviewed
```

**Role enforcement:**  
Only staff members with `role: registrar` may advance to `registrar_reviewed`. A surveyor actor is rejected with HTTP 422.

**Report upload gate:**  
`report_uploaded` is only reachable after `survey_completed`. Attempting to jump directly from `survey_started` to `report_uploaded` is rejected.

---

### 5. Analytics Collection Strategy

| Collection | Role |
|------------|------|
| `land_applications` | Primary analytics source (professor-required). Used when count > 0. |
| `applications` | Fallback when `land_applications` is empty (Student 1 operational collection). |

`_get_primary_collection()` checks `land_applications.count_documents({})` at call time and returns the appropriate collection. All Tasks 5–9 and 12 use this strategy.

---

### 6. Delayed Applications (Task 10)

`GET /analytics/delayed-applications?days=7`

- Excludes terminal statuses: `closed`, `rejected`, `certificate_issued`
- `approved` is included (awaiting certificate issuance)
- Submitted timestamp: `timestamps.submitted_at` (preferred) → root `submitted_at`
- Returns: `[{ application_id, status, application_type, parcel_number, zone_id, submitted_at, delayed_days }]`
- Sorted by `delayed_days` descending
- Cache key includes the `days` parameter (e.g., `analytics:delayed:7`)

---

### 7. Cache Service (Task 14)

In-memory TTL cache in `backend/app/services/cache_service.py`:

- Default TTL: 60 seconds
- All analytics endpoints use `get_cache` / `set_cache` with key prefix `analytics:`
- Delayed applications cache key includes the `days` parameter to avoid cross-parameter collisions
- `clear_cache()` flushes all; `clear_cache(key)` removes a single key

---

### 8. MongoDB Collections

| Collection | Purpose |
|------------|---------|
| `staff_members` | Surveyor and registrar profiles with workload and coverage |
| `survey_tasks` | Per-application survey task with milestone history |
| `survey_reports` | Survey findings linked to tasks (task_id, surveyor_id, findings) |
| `land_applications` | Primary analytics collection (professor spec) |
| `applications` | Student 1 operational collection (fallback) |
| `parcels` | Parcel geometries with zone_id for GIS feeds |
| `certificates` | Issued certificates for KPI and certificates-per-month |

---

### 9. Frontend Analytics Dashboard

The React/Vite frontend at `http://localhost:5173/staff/analytics` renders:

- **KPI Cards** — total, pending, survey_required, active tasks, approved, rejected, certs issued, active surveyors
- **Applications Over Time** — vertical bar chart grouped by YYYY-MM
- **Certificates per Month** — vertical bar chart
- **Applications by Status** — coloured horizontal bar chart
- **Pending Applications by Zone** — horizontal bar chart (source: geofeed or parcel_ref fallback)
- **Average Processing Time by Application Type** — horizontal bar chart (`application_type` / `average_processing_days`)
- **Surveyor Workload** — table with workload progress bars
- **Registrar Analytics** — table with global proxy note
- **Delayed Applications** — table (status badges, delayed_days coloured by severity)

All sections use `Promise.allSettled` — a single API failure shows a per-section error without blocking others.

---

### 10. How to Run and Test

#### Start MongoDB

```bash
docker start lrmis-mongo
```

#### Run the Backend

```bash
cd backend
python -m uvicorn app.main:app --reload --port 8001
```

#### Run Seed Data

```bash
python -m app.seed.seed_data
```

#### Run Backend Tests

```bash
cd backend
python -m app.tests.test_student3                # Tasks 1-10 (workflow)
python -m app.tests.test_student3_tasks11_20     # Tasks 11-20 (analytics + map)
python -m app.tests.test_group_analytics_tasks3_9  # Group analytics Tasks 3-9
python -m app.tests.test_student3_tasks37_40     # Comprehensive verification
```

#### Run Frontend

```bash
cd frontend
npm run dev
# → http://localhost:5173/staff/analytics
```

#### Postman Collection

```
docs/postman/Student3_Surveyor_Registrar_Assignment.postman_collection.json
```

Import into Postman and set variables: `base_url`, `app_id`, `staff_id`, `registrar_id`.

#### Frontend Test Cases

See `docs/testing/Student3_Frontend_Test_Cases.md` for 10 manual test cases covering the analytics dashboard.

---

### 11. Testing Summary

| Test Suite | Checks | Covers |
|------------|--------|--------|
| `test_student3.py` | 40+ | Staff schema, create staff, profile, scoring, auto-assign, duplicate prevention, reassign, milestone advancement |
| `test_student3_tasks11_20.py` | 50+ | Surveyor/registrar analytics, cache, map GeoJSON feeds |
| `test_group_analytics_tasks3_9.py` | 120 | KPI (9 fields), by-status, by-type, by-zone, processing-time |
| `test_student3_tasks37_40.py` | 60+ | Full workflow end-to-end, delayed applications, collection alignment, cache TTL |

---

### 12. Integration with Student 1 and Student 2

| Student 1 Asset | How Student 3 Uses It |
|-----------------|----------------------|
| `applications` collection | Survey task auto-assign reads `parcel_ref.zone_id`; milestone updates mark `assignment.assigned_surveyor_id` |
| `PATCH /applications/{id}/transition` | `transitionApplication()` in frontend reused for `survey_required → surveyed` and `surveyed → legal_review` |
| `land_applications` collection | Primary analytics source (KPI, by-status, by-type, by-zone, processing-time, delayed) |
| `parcels` collection | GIS feeds and zone resolution for by-zone analytics |
| `certificates` collection | KPI `certificates_issued` count and `certificates-per-month` |
| `performance_logs` collection | Registrar analytics review time computation |

| Student 2 Asset | How Student 3 Uses It |
|-----------------|----------------------|
| `objections` collection | Disputed parcels GeoJSON feed; under-objection KPI counter |
| `ApplicationDetails.jsx` | Survey report section embedded within existing application detail page |
| `RegistrarReview.jsx` | Student 3 registrar review panel coexists with existing Student 2 document review panel |

---

## Group Tasks 21–30: Spatial Filters, Auth, Export & Seed

### Overview

Tasks 21–30 extend the system with backend spatial filtering, CSV/JSON exports, a demo authentication system, and a comprehensive unified seed script.

---

### Task 21 — Spatial Filters on GeoFeeds

All 5 geofeed endpoints now accept optional query parameters:

| Endpoint | Accepted Params |
|----------|----------------|
| `GET /analytics/geofeeds/parcels` | `zone_id`, `status`, `dispute_state` |
| `GET /analytics/geofeeds/pending-applications` | `zone_id`, `application_type`, `status` |
| `GET /analytics/geofeeds/pending-heatmap` | `zone_id`, `status` |
| `GET /analytics/geofeeds/disputed-parcels` | `zone_id`, `dispute_state` |
| `GET /analytics/geofeeds/survey-tasks` | `zone_id`, `status` |

The Live Map frontend re-fetches from the backend whenever zone, application type, status, or dispute-state filters change. A new "Application Type" dropdown has been added to `MapFilters.jsx`.

---

### Task 22 — Nearby Endpoint (`$geoNear`)

```
GET /analytics/geofeeds/nearby?lng=35.18&lat=31.98&max_distance=1000
```

Uses MongoDB `$geoNear` aggregation with the existing 2dsphere index on `parcels.geometry`.

**Important**: `$geoNear` requires a real MongoDB instance. Under the in-memory test environment (mongomock), the endpoint returns `{"type":"FeatureCollection","features":[],"error":"...","note":"$geoNear requires..."}` — HTTP 200, no crash.

---

### Tasks 23–24 — CSV Exports

```
GET /analytics/export/applications.csv
```
Downloads all applications as CSV with 9 columns: `application_id, status, application_type, parcel_number, zone_id, submitted_at, updated_at, applicant_ref, priority`.

```
GET /analytics/export/surveyors.csv
```
Downloads surveyor workload as CSV with 6 columns: `surveyor_id, name, active_tasks, completed_tasks, max_tasks, workload_percentage`.

Both endpoints return `Content-Type: text/csv` with `Content-Disposition: attachment`.

---

### Task 25 — Management Report (JSON stub)

```
GET /analytics/export/management-report?threshold_days=30
```

Returns a structured JSON combining all analytics sections:

```json
{
  "report_type": "management_summary",
  "generated_at": "2026-06-21T...",
  "threshold_days": 30,
  "kpis": {...},
  "applications_by_status": [...],
  "applications_by_type": [...],
  "applications_by_zone": [...],
  "processing_time": [...],
  "surveyors": {"surveyors": [...], "total": N},
  "registrars": {"registrars": [...], "total": N},
  "delayed_applications": [...]
}
```

*Note: JSON stub only — PDF generation is out of scope per Task 25 specification.*

---

### Task 26 — Login Page

A demo role-selection page at `/login` (`frontend/src/pages/auth/Login.jsx`):

- 4 role buttons: **Applicant**, **Staff/Registrar**, **Surveyor**, **Manager**
- Stores `{role, user_id, display_name}` to `localStorage` key `lrmis_user`
- Redirects: Applicant → `/applicant`, Staff → `/staff/dashboard`, Surveyor → `/surveyor/tasks`, Manager → `/analytics`
- Matches existing green/gold design theme
- No password required (demo system)

---

### Task 27 — Route Protection

`frontend/src/components/ProtectedRoute.jsx` guards all routes using localStorage:
- No user → redirect to `/login`
- Wrong role → redirect to `/login`

`App.jsx` updated: all routes wrapped with `<ProtectedRoute allowedRoles={[...]}>`.

Role access matrix:
| Route prefix | Allowed roles |
|-------------|--------------|
| `/applicant/*` | `applicant` |
| `/staff/*` | `staff` |
| `/surveyor/*` | `surveyor`, `staff` |
| `/map/live` | `staff`, `surveyor`, `manager` |
| `/analytics` | `manager`, `staff` |

---

### Tasks 28–30 — Unified Seed Script

```bash
python -m app.seed.seed_data           # seed all collections
python -m app.seed.seed_data --reset   # drop demo collections then reseed
```

**Seeded collections (Task 28):**

| Collection | Count | Notes |
|-----------|-------|-------|
| `parcels` | 8 | P-001..P-008, 4 zones |
| `land_applications` + `applications` | 10 | 6 application types, all workflow statuses |
| `applicants` | 5 | APPL-001..005 |
| `staff_members` | 4 | 2 surveyors + 2 registrars |
| `certificates` | 2 | CERT-2026-0001, CERT-2026-0002 |
| `application_documents` | 5 | DOC-001..005 |
| `comments` | 3 | CMT-001..003 |
| `objections` | 2 | OBJ-001..002 |
| `survey_tasks` | 3 | TASK-001..003, various milestones |
| `survey_reports` | 2 | REPORT-001..002 |
| `notification_logs` | 4 | NOTIF-001..004 |
| `performance_logs` | 6 | one per original application |

At least one application is delayed > 7 days (e.g., LRMIS-2026-0001: submitted 10 days ago, status=submitted).

**Indexes (Task 29):** Idempotent `create_index()` calls for all 11+ collections including `2dsphere` on `parcels.geometry`.

**Reset (Task 30):** `--reset` drops all demo collections then runs full seed; prints per-collection counts.

---

### Running Tests (Tasks 21–30)

```bash
cd backend
pytest app/tests/test_group_tasks21_30.py -v
```

**Results: 65/65 PASS**

| Class | Tests | Coverage |
|-------|-------|---------|
| `TestTask21SpatialFilters` | 16 | All 5 endpoints with filter params |
| `TestTask22Nearby` | 4 | `/nearby` endpoint (mongomock fallback) |
| `TestTask23CSVApplications` | 6 | CSV content-type, columns, data rows |
| `TestTask24CSVSurveyors` | 5 | CSV content-type, columns |
| `TestTask25ManagementReport` | 11 | JSON structure, required keys, threshold param |
| `TestTask28SeedStructure` | 16 | Counts, types, statuses, delayed app check |
| `TestTask29Indexes` | 2 | create_indexes() idempotent |
| `TestTask30Reset` | 4 | reset_demo_collections() + reseed |

Frontend test cases: `docs/testing/Group_Tasks21_30_Frontend_Test_Cases.md`

Postman collection: `docs/postman/Student3_Surveyor_Registrar_Assignment.postman_collection.json` (17 requests total — 10 original + 7 new)
