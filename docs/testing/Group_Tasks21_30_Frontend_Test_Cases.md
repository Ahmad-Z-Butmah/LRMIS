# Group Tasks 21–30 — Frontend Test Cases

**Module:** Spatial Filters, Auth, Seed & Export  
**Frontend URL:** http://localhost:5173  
**Backend URL:** http://127.0.0.1:8001

---

## Prerequisites

1. MongoDB running (`docker start lrmis-mongo`)
2. Seed data loaded: `cd backend && python -m app.seed.seed_data`
3. Backend running: `python -m uvicorn app.main:app --reload --port 8001`
4. Frontend running: `cd frontend && npm run dev`
5. Clear localStorage before each auth test: `localStorage.clear()` in browser console

---

## TC-21-01 — Map Filters: Zone Filter Applied to Backend

**Task:** 21  
**Path:** `/map/live`  
**Steps:**
1. Open the Live Map page
2. In the sidebar, type `Z-WEST` in the Zone ID input
3. Wait for the map to reload

**Expected:**
- Network tab shows requests to `/analytics/geofeeds/parcels?zone_id=Z-WEST`
- Only parcels in zone Z-WEST are displayed
- Parcel count badge updates to reflect filtered count

---

## TC-21-02 — Map Filters: Application Type Filter

**Task:** 21  
**Path:** `/map/live`  
**Steps:**
1. Open the Live Map page
2. Select "Ownership Transfer" from the Application Type dropdown
3. Wait for reload

**Expected:**
- Pending applications layer shows only `ownership_transfer` type features
- Backend request includes `application_type=ownership_transfer` in query string

---

## TC-21-03 — Map Filters: Status Filter

**Task:** 21  
**Path:** `/map/live`  
**Steps:**
1. Open the Live Map page
2. Select "Survey Required" from the Filter by Status dropdown

**Expected:**
- Pending applications layer shows only features with `status=survey_required`
- Backend request includes `status=survey_required`

---

## TC-21-04 — Map Filters: Dispute State Filter

**Task:** 21  
**Path:** `/map/live`  
**Steps:**
1. Open the Live Map page
2. Select "Disputed Only" from the Dispute State dropdown

**Expected:**
- Disputed parcels layer filters to show only disputed features
- Backend request to `/analytics/geofeeds/disputed-parcels?dispute_state=disputed`

---

## TC-21-05 — Map Filters: Reset Button Clears All Filters

**Task:** 21  
**Path:** `/map/live`  
**Steps:**
1. Set zone=Z-WEST, status=submitted
2. Click "Reset Filters"

**Expected:**
- All filter inputs cleared to empty/default
- Map re-fetches without filter params
- All layers visible again

---

## TC-22-01 — Nearby Endpoint (Manual API Test)

**Task:** 22  
**Method:** Browser / Postman  
**URL:** `http://127.0.0.1:8001/analytics/geofeeds/nearby?lng=35.18&lat=31.98&max_distance=5000`

**Expected (real MongoDB):**
- Returns GeoJSON FeatureCollection with `distance_meters` property per feature
- Features within 5000m of (35.18, 31.98)

**Expected (mongomock / no 2dsphere index):**
- Returns `{"type": "FeatureCollection", "features": [], "error": "...", "note": "$geoNear requires..."}`
- HTTP 200 (no 500 crash)

---

## TC-22-02 — Nearby Requires lng and lat

**Task:** 22  
**URL:** `http://127.0.0.1:8001/analytics/geofeeds/nearby?lng=35.18`

**Expected:**
- HTTP 422 Unprocessable Entity
- Response body explains missing `lat` parameter

---

## TC-23-01 — Download Applications CSV

**Task:** 23  
**URL:** `http://127.0.0.1:8001/analytics/export/applications.csv`

**Steps:**
1. Open the URL in a browser or Postman

**Expected:**
- File downloads as `applications.csv`
- File opens in spreadsheet with 9 columns:
  `application_id, status, application_type, parcel_number, zone_id, submitted_at, updated_at, applicant_ref, priority`
- At least 10 data rows (from seed data)
- Content-Type header: `text/csv`
- Content-Disposition: `attachment; filename=applications.csv`

---

## TC-24-01 — Download Surveyors CSV

**Task:** 24  
**URL:** `http://127.0.0.1:8001/analytics/export/surveyors.csv`

**Expected:**
- File downloads as `surveyors.csv`
- 6 columns: `surveyor_id, name, active_tasks, completed_tasks, max_tasks, workload_percentage`
- One row per surveyor in the system
- All numeric columns contain numbers (not empty strings)

---

## TC-25-01 — Management Report JSON Structure

**Task:** 25  
**URL:** `http://127.0.0.1:8001/analytics/export/management-report`

**Expected:**
- HTTP 200, Content-Type: application/json
- Response contains all required keys:
  - `report_type` = `"management_summary"`
  - `generated_at` (ISO 8601 string)
  - `threshold_days` = 30
  - `kpis` (object with total_applications, pending, etc.)
  - `applications_by_status` (array)
  - `applications_by_type` (array)
  - `applications_by_zone` (array)
  - `processing_time` (array)
  - `surveyors` (object with surveyors array + total)
  - `registrars` (object with registrars array + total)
  - `delayed_applications` (array)

---

## TC-25-02 — Management Report Custom Threshold

**Task:** 25  
**URL:** `http://127.0.0.1:8001/analytics/export/management-report?threshold_days=14`

**Expected:**
- `threshold_days` = 14 in response
- `delayed_applications` returns apps delayed > 14 days

---

## TC-26-01 — Login Page Renders

**Task:** 26  
**Path:** `/login`  
**Steps:**
1. Navigate to `http://localhost:5173/login` (clear localStorage first)

**Expected:**
- Login card with LRMIS badge displayed
- 4 role buttons: Applicant, Staff / Registrar, Surveyor, Manager
- "Enter System" button is disabled (grey) when no role selected

---

## TC-26-02 — Role Selection Enables Enter Button

**Task:** 26  
**Path:** `/login`  
**Steps:**
1. Click "Applicant"
2. Observe the Enter System button

**Expected:**
- Selected role button shows active styling (green border, green background)
- Enter System button becomes enabled (green)

---

## TC-26-03 — Applicant Role Redirects to /applicant

**Task:** 26  
**Path:** `/login`  
**Steps:**
1. Select "Applicant"
2. Click "Enter System"

**Expected:**
- Redirected to `/applicant`
- `localStorage.getItem('lrmis_user')` in console returns:
  `{"role":"applicant","user_id":"demo_applicant","display_name":"Applicant"}`

---

## TC-26-04 — All Role Redirects Work

**Task:** 26  
**Steps per role:**

| Role | Expected Redirect |
|------|-------------------|
| Applicant | `/applicant` |
| Staff / Registrar | `/staff/dashboard` |
| Surveyor | `/surveyor/tasks` |
| Manager | `/analytics` |

---

## TC-27-01 — Unauthenticated Access Redirects to /login

**Task:** 27  
**Steps:**
1. Clear localStorage: `localStorage.clear()`
2. Navigate to `http://localhost:5173/applicant`

**Expected:**
- Redirected to `/login`
- No flash of the applicant dashboard

---

## TC-27-02 — Wrong Role Redirects to /login

**Task:** 27  
**Steps:**
1. Set localStorage: `localStorage.setItem('lrmis_user', JSON.stringify({role:'applicant',user_id:'x',display_name:'Test'}))`
2. Navigate to `http://localhost:5173/staff/dashboard`

**Expected:**
- Redirected to `/login` (applicant cannot access staff routes)

---

## TC-27-03 — Correct Role Grants Access

**Task:** 27  
**Steps:**
1. Set localStorage: `localStorage.setItem('lrmis_user', JSON.stringify({role:'staff',user_id:'x',display_name:'Staff'}))`
2. Navigate to `http://localhost:5173/staff/dashboard`

**Expected:**
- Staff Dashboard page renders without redirect

---

## TC-27-04 — Manager Accesses Analytics

**Task:** 27  
**Steps:**
1. Set localStorage: `localStorage.setItem('lrmis_user', JSON.stringify({role:'manager',user_id:'x',display_name:'Mgr'}))`
2. Navigate to `http://localhost:5173/analytics`

**Expected:**
- Analytics Dashboard renders

---

## TC-27-05 — Surveyor Can Access Map

**Task:** 27  
**Steps:**
1. Set localStorage with role `surveyor`
2. Navigate to `/map/live`

**Expected:**
- Live Map page renders (surveyor is in allowedRoles for /map/live)

---

## TC-28-01 — Seed Populates All Required Collections

**Task:** 28  
**Steps:**
1. Run: `cd backend && python -m app.seed.seed_data`
2. Check in MongoDB Compass or CLI

**Expected counts:**
- `parcels`: 8
- `land_applications`: 10
- `applications`: 10
- `applicants`: 5
- `staff_members`: 4
- `certificates`: 2
- `application_documents`: 5
- `comments`: 3
- `objections`: 2
- `survey_tasks`: 3
- `survey_reports`: 2
- `notification_logs`: 4

---

## TC-30-01 — Reset Command Drops and Reseeds

**Task:** 30  
**Steps:**
1. Run: `cd backend && python -m app.seed.seed_data --reset`

**Expected:**
- Console output shows `[reset] Dropped: <collection>` for each demo collection
- Followed by seeding output and counts summary
- After reset, all collections contain fresh seed data (not cumulative)

---

## Notes

- **Task 22 note**: `$geoNear` requires a real MongoDB instance with a 2dsphere index on `parcels.geometry`. Under the in-memory test environment (mongomock), the endpoint returns an empty FeatureCollection with an `error` key — this is the correct documented fallback, not a bug.
- **Tasks 23, 24**: CSV downloads can be tested by visiting the URL directly in a browser — the browser should prompt to save/open a `.csv` file.
- **Task 25**: The management report is a JSON stub, not a PDF. PDF generation is out of scope per Task 25 specification.
- **Tasks 26, 27**: Auth is localStorage-only (demo). No backend authentication is performed. Clearing localStorage logs out the user.
