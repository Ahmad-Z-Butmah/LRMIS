# Student 3 — Frontend Test Cases

**Module:** Surveyor / Registrar Assignment & Analytics Dashboard  
**Frontend URL:** http://localhost:5173  
**Backend URL:** http://127.0.0.1:8001

---

## Prerequisites

1. MongoDB running (`docker start lrmis-mongo`)
2. Backend running: `cd backend && python -m uvicorn app.main:app --reload --port 8001`
3. Seed data loaded: `python -m app.seed.seed_data`
4. Frontend running: `cd frontend && npm run dev`

---

## TC-01 — Analytics Dashboard Loads Without Errors

**Path:** `/staff/analytics`  
**Steps:**
1. Navigate to `/staff/analytics`
2. Wait for loading spinner to disappear

**Expected:**
- Page renders all sections: KPI cards, charts, Surveyor Workload, Registrar Analytics, Delayed Applications
- No red error banners
- KPI cards display numeric values (not `—` dashes)

---

## TC-02 — KPI Cards Show Correct Fields

**Path:** `/staff/analytics`  
**Steps:**
1. Load the dashboard
2. Inspect the KPI card row

**Expected:**
- Cards present: Total Applications, Pending, Survey Required, Active Survey Tasks, Approved, Rejected, Certs Issued, Active Surveyors
- All values are non-negative integers
- No `undefined` or `NaN` displayed

---

## TC-03 — Processing Time Chart Uses Correct Keys

**Path:** `/staff/analytics`  
**Steps:**
1. Scroll to "Average Processing Time by Application Type (days)" section
2. Observe bar chart labels and values

**Expected:**
- Bars labelled with application type names (e.g., "first registration", "ownership transfer")
- Values shown are processing days (float), not `0` for all entries if seed data exists
- No bar labelled "stage" or "average days" (old field names)

---

## TC-04 — Delayed Applications Section Appears

**Path:** `/staff/analytics`  
**Steps:**
1. Scroll to "Delayed Applications (> 7 days pending)" section

**Expected:**
- Section renders without error
- If no applications are delayed: shows "No applications delayed beyond 7 days."
- If delayed apps exist: table with columns Application ID, Status, Type, Zone, Parcel, Submitted, Delayed (days)
- Rows with ≥ 30 delayed days show red row highlight; 7–29 days show warning highlight

---

## TC-05 — Delayed Applications Status Badges

**Path:** `/staff/analytics`  
**Steps:**
1. Observe the Status column in the Delayed Applications table (if data present)

**Expected:**
- Each row shows a coloured `StatusBadge` component (not plain text)
- Status values match known workflow states (submitted, pre_checked, survey_required, etc.)
- Closed, rejected, and certificate_issued applications do NOT appear (excluded at API level)

---

## TC-06 — Surveyor Workload Table Renders

**Path:** `/staff/analytics`  
**Steps:**
1. Scroll to "Surveyor Workload" section

**Expected:**
- Table shows: Surveyor, Active, Completed, Max, Workload bar, Avg Days, Reports
- Workload bar fills proportionally to workload_percentage
- Rows with ≥ 90% workload show red tint; 70–89% show amber tint

---

## TC-07 — Registrar Analytics Shows Proxy Note

**Path:** `/staff/analytics`  
**Steps:**
1. Scroll to "Registrar Analytics" section

**Expected:**
- If registrars exist: table shows Registrar, Assigned (proxy), Completed, Approved, Rejected, Avg Review (days)
- Blue note: "Assigned reviews count is a global proxy — no per-registrar assignment field in schema."
- Average review time shows `—` when 0

---

## TC-08 — Applications By Status Bar Chart

**Path:** `/staff/analytics`  
**Steps:**
1. Scroll to "Applications by Status" section

**Expected:**
- Horizontal bar chart with status labels (underscores replaced by spaces)
- Bars coloured by status: red for rejected/under_objection, green for approved, amber for survey_required/missing_documents, purple for legal_review
- Sorted by count descending

---

## TC-09 — Under Objection Callout Conditional Render

**Path:** `/staff/analytics`  
**Steps:**
1. Observe the area just below the KPI cards
2. Test with and without applications in `under_objection` status

**Expected:**
- If count > 0: callout banner shows "X Application(s) under objection" with links to Registrar Review and Application Details
- If count = 0: callout banner is NOT rendered

---

## TC-10 — Navigation Buttons Work

**Path:** `/staff/analytics`  
**Steps:**
1. Click "Surveyor Tasks" button in the page header
2. Navigate back
3. Click "Live Map" button in the page header

**Expected:**
- "Surveyor Tasks" navigates to `/surveyor/tasks`
- "Live Map" navigates to `/map/live`
- Both navigate without page reload errors

---

## Notes

- All API calls use `Promise.allSettled` — a single endpoint failure shows a section-level error banner without blocking the rest of the dashboard
- The Delayed Applications section fetches `GET /analytics/delayed-applications?days=7`
- Processing Time chart keys: `labelKey="application_type"`, `valueKey="average_processing_days"` (updated from old `stage`/`average_days` shape)
- Zone chart source is shown as a note: geofeed when available, parcel_ref fallback with warning otherwise
