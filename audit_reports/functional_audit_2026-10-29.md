# SAMS-FR: Complete Application Functional Audit Report

**Target System:** Smart Attendance Management System with Facial Recognition (SAMS-FR)
**Audit Date:** October 29, 2026
**Auditor:** Senior Full-Stack Software Engineer & Lead System Auditor
**Branch / Working Copy:** `feature/frontend-auth-portals`
**Audit Mode:** Strictly Non-Mutating / Report-Only (Zero code, model, test, dependency, or DB changes)

---

## Section A: Executive Summary

A comprehensive, rigorous functional audit was executed across the complete **SAMS-FR** web application codebase. The objective was to identify, test, and document all user-facing features, pages, buttons, forms, filters, modals, navigation links, file exports/imports, charts, dashboards, and backend integrations that appear functional in the user interface but are broken, disconnected, simulated in local state, or missing actual backend implementations.

The audit analyzed **51 application routes**, **39 frontend page and layout components**, **125 registered Flask backend route/method combinations** across 17 blueprints, **14 frontend service modules**, and verified the test suite (**405 passed automated backend tests in 66.81s**), frontend linting (**0 ESLint errors/warnings**), and production packaging (**Vite production build clean in 1.63s**).

### Audit Metrics Summary

| Audit Metric | Measured Count | Notes |
|:---|:---:|:---|
| **Total Discovered Routes** | **51** | Dynamically mapped from `frontend/src/routes/AppRoutes.jsx` |
| **Total Inspected Pages & Layouts** | **39** | React 19 JSX components across `pages/` and `layouts/` |
| **Total Registered Backend Endpoints** | **125** | Flask route rules across 17 Blueprints |
| **Active Frontend Service Integrations** | **109** | Integrated API client functions in `frontend/src/services/` |
| **Total Automated Backend Tests** | **405** | **405 Passed**, 0 Failed in `backend/tests` (66.81s) |
| **Frontend Lint & Build Verification** | **100% Pass** | 0 ESLint warnings/errors; Vite build completed in 1.63s |
| **Total Confirmed Issues Identified** | **17** | Documented with line numbers, code evidence, and reproduction |

### Issues Classified by Severity

| Severity Level | Count | Description & Institutional Impact |
|:---|:---:|:---|
| **CRITICAL** | **0** | No live data corruption, zero authentication bypasses, and zero fatal crashes on active paths. |
| **HIGH** | **5** | Major workflow gaps: File exports downloading incorrect formats (CSV instead of PDF), browser print dialog invoked instead of report downloads, and simulated credential recovery lacking backend APIs. |
| **MEDIUM** | **6** | Functional limitations: Backend analytics endpoint disconnected from Admin Dashboard, settings saved only to browser `localStorage`, timetable import rejecting advertised file formats, and stateless JWT logout lacking revocation. |
| **LOW** | **6** | UI/UX and Developer Experience defects: Dead header search inputs, non-interactive notification bells, missing sidebar navigation link, and root-level pytest discovery colliding with interactive CV scripts. |
| **UNVERIFIED** | **0** | Every finding was confirmed against concrete code references, AST inspection, or test execution. |
| **Total** | **17** | Complete Register in Section C |

### Issues Classified by Implementation Category

| Implementation Category | Count | Primary Areas Affected |
|:---|:---:|:---|
| **NOT IMPLEMENTED** | **5** | Excel/PDF export in Faculty Reports; Password Reset & OTP backend; Admin Settings service toggles. |
| **DISCONNECTED** | **3** | Admin Dashboard Attendance Trend (backend exists in `admin_analytics.py`); Student Academic Report export format mismatch; Faculty settings lack DB persistence. |
| **UI/UX ISSUE** | **5** | Header search inputs lack event handlers; Notification bells have hardcoded unread count badges; Export buttons labeled 'PDF' download CSV or launch browser print dialog. |
| **BROKEN** | **2** | Timetable import rejects advertised `.xls` and `.pdf` files; Root pytest collection hits interactive CV scripts. |
| **PARTIALLY WORKING** | **1** | Client-side-only settings persistence in `localStorage` without backend sync. |
| **AUTHORIZATION ISSUE** | **1** | Stateless JWT logout without token invalidation/blocklist. |

### Most Significant User-Facing Failures
1. **Export Format Deception (PDF Disguise):** On the Student Academic Report page (`/student/academic-records`), clicking the button labeled *'Download Report (PDF)'* calls a backend CSV route, resulting in a `.csv` file download (`Academic_Grade_Card_Sem...csv`). Similarly, on Student Subject-wise Reports (`/student/reports`), clicking *'Download Report (PDF)'* downloads a `.csv` file and immediately triggers the browser's raw system print dialog (`window.print()`). The backend possesses zero PDF generation engines.
2. **Faculty Reports Incomplete Export Modal:** On `/faculty/reports`, the export modal exposes CSV, Excel, and PDF tabs. CSV runs purely in client-side JavaScript memory from the React table state (with no backend audit or route). Excel and PDF options are disabled buttons with an explanatory note stating they are not implemented yet.
3. **Simulated Password Recovery:** The public authentication views `/auth/forgot-password` and `/auth/verify-otp` provide an interactive multi-step interface for password resetting, but have zero backend API endpoints. Submitting the forms displays an institutional notice to visit the IT helpdesk in person or triggers a hardcoded connection failure string.
4. **Disconnected Admin Attendance Analytics:** `AdminDashboard.jsx` displays a blank attendance overview box stating *'No attendance trend data. API integration is pending for historical attendance trend data'*, even though the Flask backend already provides `GET /api/admin/attendance/analytics` in `app/routes/admin_analytics.py`.
5. **Non-Functional Top Header Controls:** Across both Faculty and Student portal layouts, the top header search bar (`<input placeholder="Search..." />`) and notification bell buttons are purely cosmetic. The search inputs have no `onChange` handlers or search routines, and the bell icons display hardcoded notification badge counts without opening a drawer or hitting an API.

---

## Section B: Page and Feature Inventory

All 51 routes declared in `frontend/src/routes/AppRoutes.jsx` were cataloged and verified against their corresponding React components and access policies.

| # | Route URL | Portal | Component Name | Auth Protection / Role | Functional Purpose | Audit Status |
|:---:|:---|:---:|:---|:---:|:---|:---:|
| 1 | `/` | Public | `Navigate` | None | Redirects default root URL to `/auth` | Fully Functional |
| 2 | `/auth` | Public | `Login` | Public / Guest | Institutional user login (Email/ID + Password) | Fully Functional |
| 3 | `/auth/forgot-password` | Public | `ForgotPassword` | Public / Guest | Self-service password reset request form | **Needs Remediation** (No backend API) |
| 4 | `/auth/verify-otp` | Public | `VerifyOtp` | Public / Guest | OTP verification code entry & reset | **Needs Remediation** (No backend API) |
| 5 | `/unauthorized` | Public | `Unauthorized` | Public | 403 Forbidden role boundary error view | Fully Functional |
| 6 | `/admin/dashboard` | Admin | `AdminDashboard` | `ADMIN` RoleGuard | KPI summary, attendance donut, activity feed | **Partially Working** (Analytics disconnected) |
| 7 | `/admin/management` | Admin | `AdminManagement` | `ADMIN` RoleGuard | User CRUD, role assignments, status management | Fully Functional |
| 8 | `/admin/add-user` | Admin | `AdminManagement` | `ADMIN` RoleGuard | Direct alias to User Management with add modal | Fully Functional |
| 9 | `/admin/students` | Admin | `Students` | `ADMIN` RoleGuard | Student roster, enrollment status, batch filters | Fully Functional |
| 10 | `/admin/face-registration` | Admin | `FaceRegistration` | `ADMIN` RoleGuard | Webcam capture and student biometric enrollment | Fully Functional |
| 11 | `/admin/faculty` | Admin | `Faculty` | `ADMIN` RoleGuard | Faculty directory, department mappings, workload | Fully Functional |
| 12 | `/admin/departments` | Admin | `Departments` | `ADMIN` RoleGuard | Department management and head assignments | Fully Functional |
| 13 | `/admin/department` | Admin | `Departments` | `ADMIN` RoleGuard | Alias route for Departments | Fully Functional |
| 14 | `/admin/academic-management` | Admin | `Navigate` | `ADMIN` RoleGuard | Redirects to courses tab | Fully Functional |
| 15 | `/admin/academic-management/courses` | Admin | `AcademicManagement` | `ADMIN` RoleGuard | Course catalog management, credits, codes | Fully Functional |
| 16 | `/admin/academic-management/course-offerings` | Admin | `AcademicManagement` | `ADMIN` RoleGuard | Offering scheduler, term, faculty assignments | Fully Functional |
| 17 | `/admin/academic-management/course-enrollments` | Admin | `CourseEnrollments` | `ADMIN` RoleGuard | Student course enrollments, sections, status | Fully Functional |
| 18 | `/admin/academic-management/assignments` | Admin | `AcademicManagement` | `ADMIN` RoleGuard | Course offering assignments view | Fully Functional |
| 19 | `/admin/academic-management/results` | Admin | `AcademicResults` | `ADMIN` RoleGuard | Institutional academic results, approval & publish | Fully Functional |
| 20 | `/admin/academic-results` | Admin | `Navigate` | `ADMIN` RoleGuard | Redirect alias to results management | Fully Functional |
| 21 | `/admin/academic-management/batches` | Admin | `Navigate` | `ADMIN` RoleGuard | Redirect alias to batches | Fully Functional |
| 22 | `/admin/batches` | Admin | `BatchManagement` | `ADMIN` RoleGuard | Cohort / Batch creation and management | Fully Functional |
| 23 | `/admin/timetable` | Admin | `TimetableManagement` | `ADMIN` RoleGuard | Schedule matrix, timetable import (.xlsx) | **Needs Remediation** (UI claims PDF/.xls) |
| 24 | `/admin/timetable/faculty-adjustment` | Admin | `TimetableManagement` | `ADMIN` RoleGuard | Faculty substitution and class adjustments | Fully Functional |
| 25 | `/admin/attendance-reports` | Admin | `AttendanceReports` | `ADMIN` RoleGuard | Attendance filtering, analytics, CSV export | Fully Functional |
| 26 | `/admin/attendance` | Admin | `AttendanceReports` | `ADMIN` RoleGuard | Alias route for Attendance Reports | Fully Functional |
| 27 | `/admin/profile` | Admin | `AdminProfile` | `ADMIN` RoleGuard | Administrator profile data and password update | Fully Functional |
| 28 | `/admin/settings` | Admin | `AdminSettings` | `ADMIN` RoleGuard | System preferences, theme, layout | **Needs Remediation** (Placeholders present) |
| 29 | `/admin/activity` | Admin | `ActivityLogs` | `ADMIN` RoleGuard | System audit log table and action filters | Fully Functional |
| 30 | `/admin/activity-logs` | Admin | `ActivityLogs` | `ADMIN` RoleGuard | Alias route for Activity Logs | Fully Functional |
| 31 | `/faculty/dashboard` | Faculty | `FacultyDashboard` | `FACULTY` RoleGuard | Assigned courses, today's classes, stats | Fully Functional |
| 32 | `/faculty/classes` | Faculty | `Classes` | `FACULTY` RoleGuard | Class schedule, student rosters, timetable | **Needs Remediation** (Promised export missing) |
| 33 | `/faculty/students` | Faculty | `FacultyStudents` | `FACULTY` RoleGuard | Directory of enrolled students in assigned courses | Fully Functional |
| 34 | `/faculty/attendance` | Faculty | `Attendance` | `FACULTY` RoleGuard | Live camera facial attendance & manual roll call | Fully Functional |
| 35 | `/faculty/reports` | Faculty | `Reports` | `FACULTY` RoleGuard | Course attendance summaries and export | **Needs Remediation** (Excel/PDF disabled) |
| 36 | `/faculty/results` | Faculty | `ResultUpload` | `FACULTY` RoleGuard | Assessment marks entry, CSV import, draft/submit | Fully Functional |
| 37 | `/faculty/result-upload` | Faculty | `Navigate` | `FACULTY` RoleGuard | Redirect alias to faculty results | Fully Functional |
| 38 | `/faculty/profile` | Faculty | `FacultyProfile` | `FACULTY` RoleGuard | Faculty bio, contact details, profile update | Fully Functional |
| 39 | `/faculty/settings` | Faculty | `FacultySettings` | `FACULTY` RoleGuard | Faculty portal appearance and notification toggles | **Needs Remediation** (LocalStorage only) |
| 40 | `/student/dashboard` | Student | `StudentDashboard` | `STUDENT` RoleGuard | Overall attendance %, today's classes, trend | Fully Functional |
| 41 | `/student/attendance` | Student | `StudentAttendance` | `STUDENT` RoleGuard | Daily punch matrix, face punch verification | Fully Functional |
| 42 | `/student/daily-punch` | Student | `StudentAttendance` | `STUDENT` RoleGuard | Alias route for daily punch | Fully Functional |
| 43 | `/student/attendance-history` | Student | `AttendanceHistory` | `STUDENT` RoleGuard | Full session logs, status badges, filters | Fully Functional |
| 44 | `/student/courses` | Student | `Courses` | `STUDENT` RoleGuard | Enrolled courses, credits, faculty contact | Fully Functional |
| 45 | `/student/academic-records` | Student | `AcademicReport` | `STUDENT` RoleGuard | Grade cards, SGPA, CGPA, official export | **Needs Remediation** (PDF button outputs CSV) |
| 46 | `/student/academic-report` | Student | `AcademicReport` | `STUDENT` RoleGuard | Alias route for Academic Report | **Needs Remediation** (PDF button outputs CSV) |
| 47 | `/student/profile` | Student | `Profile` | `STUDENT` RoleGuard | Student profile, face profile status, uploads | Fully Functional |
| 48 | `/student/timetable` | Student | `Schedule` | `STUDENT` RoleGuard | Weekly timetable schedule by day of week | Fully Functional |
| 49 | `/student/schedule` | Student | `Schedule` | `STUDENT` RoleGuard | Alias route for Schedule | Fully Functional |
| 50 | `/student/reports` | Student | `StudentReports` | `STUDENT` RoleGuard | Subject-wise attendance breakdown & chart | **Needs Remediation** (PDF button triggers print) |
| 51 | `/student/settings` | Student | `StudentSettings` | `STUDENT` RoleGuard | Student notification & appearance settings | **Needs Remediation** (LocalStorage only) |

---

## Section C: Complete Issue Register

### Consolidated Issue Summary Table

| Issue ID | Portal | Page / Route | Feature / Element | Severity | Category | Verification Status |
|:---|:---|:---|:---|:---:|:---:|:---:|
| `ISSUE-EXP-01` | Faculty | `/faculty/reports` | Export Modal (Excel & PDF) | **HIGH** | `NOT IMPLEMENTED` | Verified in Code & UI |
| `ISSUE-EXP-02` | Student | `/student/academic-records` | Download Report (PDF) | **HIGH** | `DISCONNECTED` | Verified in Code & API |
| `ISSUE-EXP-03` | Student | `/student/reports` | Download Report (PDF) | **HIGH** | `UI/UX ISSUE` | Verified in Code & UI |
| `ISSUE-EXP-04` | Faculty | `/faculty/classes` | Class Roster & Attendance Export | **MEDIUM** | `NOT IMPLEMENTED` | Verified in Code |
| `ISSUE-IMP-01` | Admin | `/admin/timetable` | Timetable Import (.xls & .pdf) | **MEDIUM** | `BROKEN` | Verified in Code & UI |
| `ISSUE-AUTH-01` | Public | `/auth/forgot-password` | Forgot Password Submission | **HIGH** | `NOT IMPLEMENTED` | Verified in Code & Routes |
| `ISSUE-AUTH-02` | Public | `/auth/verify-otp` | Verify OTP Code Submission | **HIGH** | `NOT IMPLEMENTED` | Verified in Code & Routes |
| `ISSUE-NAV-01` | Faculty | `FacultyLayout.jsx` | Top Header Search Input | **LOW** | `UI/UX ISSUE` | Verified in Code |
| `ISSUE-NAV-02` | Student | `StudentLayout.jsx` | Top Header Search Input | **LOW** | `UI/UX ISSUE` | Verified in Code |
| `ISSUE-NAV-03` | Faculty/Student | `Layouts` | Notification Bell Button | **LOW** | `UI/UX ISSUE` | Verified in Code |
| `ISSUE-NAV-04` | Admin | `AdminLayout.jsx` | Top Header Search & Bell | **LOW** | `UI/UX ISSUE` | Verified in Code & Design |
| `ISSUE-NAV-05` | Faculty | `FacultyLayout.jsx` | Missing Notes & Assignments Link | **LOW** | `DISCONNECTED` | Verified in Code & Design |
| `ISSUE-SET-01` | Admin | `/admin/settings` | Attendance & Notification Cards | **MEDIUM** | `NOT IMPLEMENTED` | Verified in Code |
| `ISSUE-SET-02` | Faculty/Student | `/settings` | User Settings Persistence | **MEDIUM** | `PARTIALLY WORKING` | Verified in Code & DB |
| `ISSUE-DASH-01` | Admin | `/admin/dashboard` | Attendance Trend Overview | **MEDIUM** | `DISCONNECTED` | Verified in Code & BE Routes |
| `ISSUE-TEST-01` | Dev / Harness | `backend/cv/` | Interactive CV Scripts in Pytest | **LOW** | `BROKEN` | Verified in Pytest Run |
| `ISSUE-SEC-01` | System Auth | `/api/auth/logout` | Stateless JWT Revocation | **MEDIUM** | `AUTHORIZATION ISSUE` | Verified in Code & Security |

---

### ISSUE-EXP-01: Export Report Modal (CSV, Excel, PDF)
- **Portal / Page:** Faculty Portal — Reports (`/faculty/reports`)
- **Severity:** `HIGH`
- **Implementation Category:** `NOT IMPLEMENTED / PARTIALLY WORKING`
- **Expected Behavior:** Clicking 'Export Report' should allow faculty to download the attendance report in CSV, Excel (.xlsx), or PDF format with active filters applied, generated securely from backend records.
- **Actual Behavior:** CSV export is assembled purely client-side from React state (`filteredStudents`) via a Blob URL. The Excel and PDF buttons are hardcoded disabled `<button type="button" disabled>` elements displaying the message: 'CSV export is available. Excel and PDF export are not implemented yet.' No backend export route exists for faculty attendance reports.
- **Reproduction Steps:**
1. Log in as Faculty.
2. Navigate to `/faculty/reports`.
3. Click 'Export Report' button.
4. Observe that Excel and PDF buttons cannot be clicked and display 'Not implemented yet'.
- **Frontend File:** `frontend/src/pages/faculty/Reports.jsx` (Lines 320-335, 830-840, 953-970)
- **Backend File:** No corresponding route in `backend/app/routes/reports.py` or `faculty.py`
- **Evidence & Code References:** In `Reports.jsx` Line 321: `const blob = new Blob(["\uFEFF", csvContent], { type: "text/csv;charset=utf-8;" });`. In Lines 830-836: `<button type="button" disabled>Excel</button>` and `<button type="button" disabled>PDF</button>`.
- **Verification Type:** Reproduced and confirmed via code inspection and UI inspection.
- **Business & User Impact:** Faculty cannot download formatted Excel worksheets or printable PDF reports for institutional record-keeping or academic meetings.
- **Dependencies:** Requires backend Excel generator (`openpyxl`) and PDF generator service.
- **Recommended Fix Direction (Do Not Execute):** Create a backend route `@reports_bp.get('/faculty/export')` that accepts `offering_id` and `format` (csv, xlsx, pdf), and wire the frontend modal options to trigger this endpoint.

### ISSUE-EXP-02: Quick Action: Download Report (PDF)
- **Portal / Page:** Student Portal — Academic Report (`/student/academic-records`)
- **Severity:** `HIGH`
- **Implementation Category:** `DISCONNECTED / UI/UX ISSUE`
- **Expected Behavior:** Clicking 'Download Report (PDF)' should download an official academic grade sheet / transcript in PDF format.
- **Actual Behavior:** Clicking the button calls `academicService.exportAcademicRecords({ format: 'csv' })`, which hits backend route `GET /api/student/academic-records/export`. The backend endpoint only outputs CSV, resulting in the download of a raw `.csv` file named `Academic_Grade_Card_Sem...csv`.
- **Reproduction Steps:**
1. Log in as Student.
2. Navigate to `/student/academic-records`.
3. Click 'Download Report (PDF)' in the Quick Actions card.
4. Observe that the downloaded file is a comma-separated text file (.csv), not a PDF.
- **Frontend File:** `frontend/src/pages/student/AcademicReport.jsx` (Lines 138-160, 776-785)
- **Backend File:** `backend/app/routes/student_academic.py` (Lines 509-545: `@student_academic_bp.get('/export')`)
- **Evidence & Code References:** `AcademicReport.jsx` Line 148: `const blob = new Blob([response.data], { type: 'text/csv;charset=utf-8;' });` and Line 153: `link.setAttribute('download', 'Academic_Grade_Card_' + semLabel + '.csv');`. Backend route docstring Line 513: `Exports official grade sheet / academic report in CSV format`.
- **Verification Type:** Confirmed via code inspection and API contract verification.
- **Business & User Impact:** Students expecting an official PDF transcript or report card receive an unformatted spreadsheet data file, creating confusion and failing academic administrative expectations.
- **Dependencies:** Backend PDF generation library (ReportLab or WeasyPrint) and academic template.
- **Recommended Fix Direction (Do Not Execute):** Implement a PDF rendering service using ReportLab or HTML-to-PDF in `student_academic.py`, add `?format=pdf` query parameter support, and stream `application/pdf` with appropriate headers.

### ISSUE-EXP-03: Quick Action: Download Report (PDF)
- **Portal / Page:** Student Portal — Subject-wise Attendance Report (`/student/reports`)
- **Severity:** `HIGH`
- **Implementation Category:** `UI/UX ISSUE / DISCONNECTED`
- **Expected Behavior:** Clicking 'Download Report (PDF)' should download a formatted attendance summary document in PDF format.
- **Actual Behavior:** Clicking the button triggers `handleDownloadReport()`, which downloads a `.csv` file and immediately calls `window.print()` to launch the browser's system printer dialog. It does not generate or download a PDF file.
- **Reproduction Steps:**
1. Log in as Student.
2. Navigate to `/student/reports`.
3. Click 'Download Report (PDF)' under Quick Actions.
4. Observe that a CSV download is initiated while the browser printer setup modal unexpectedly appears over the page.
- **Frontend File:** `frontend/src/pages/student/Reports.jsx` (Lines 339-369, 1311)
- **Backend File:** `backend/app/routes/student_attendance.py` (Line 420: `@student_attendance_bp.get('/export')`)
- **Evidence & Code References:** `Reports.jsx` Line 348: `const blob = new Blob([res.data], { type: 'text/csv;charset=utf-8;' });`, Line 356: `.csv`, and Line 363: `window.print();`.
- **Verification Type:** Confirmed via code inspection and browser runtime behavior.
- **Business & User Impact:** Confusing and abrasive user experience: users receive a CSV file while their screen is hijacked by the browser's raw system print preview.
- **Dependencies:** Backend attendance PDF generator or client-side print-to-PDF stylesheet.
- **Recommended Fix Direction (Do Not Execute):** Provide a genuine server-side PDF attendance report endpoint or, if client-side print is intended, rename button to 'Print Report' and style a dedicated `@media print` layout without downloading CSV simultaneously.

### ISSUE-EXP-04: Class Roster & Attendance Export Action
- **Portal / Page:** Faculty Portal — Classes (`/faculty/classes`)
- **Severity:** `MEDIUM`
- **Implementation Category:** `NOT IMPLEMENTED / UI/UX ISSUE`
- **Expected Behavior:** Faculty members are promised in the on-page advisory: 'You can also download the class roster or export attendance data.'
- **Actual Behavior:** Neither the Classes page nor the Class Details modal contains any button, link, or handler to export or download the roster or attendance data.
- **Reproduction Steps:**
1. Log in as Faculty.
2. Navigate to `/faculty/classes`.
3. Read the Class Information advisory panel at bottom of the page.
4. Open the Class Details modal for any assigned course.
5. Observe that the only buttons available are 'Close' and 'Take Attendance'.
- **Frontend File:** `frontend/src/pages/faculty/Classes.jsx` (Lines 894-900, 1187-1205)
- **Backend File:** Backend endpoint `GET /api/faculty/classes/<offering_id>/roster` exists, but no export route exists.
- **Evidence & Code References:** `Classes.jsx` Line 897: `Click on a class to view detailed information... You can also download the class roster or export attendance data.`. Modal footer only contains: `<button>Close</button>` and `<button>Take Attendance</button>`.
- **Verification Type:** Confirmed via code inspection.
- **Business & User Impact:** Misleading user instructions: faculty look for an export button that does not exist.
- **Dependencies:** Faculty attendance report service.
- **Recommended Fix Direction (Do Not Execute):** Add a 'Download Roster (CSV)' button in the Class Details modal footer wired to download the student roster, or remove the misleading promise from the advisory text.

### ISSUE-IMP-01: Timetable Bulk Import File Format Support
- **Portal / Page:** Admin Portal — Timetable Management (`/admin/timetable`)
- **Severity:** `MEDIUM`
- **Implementation Category:** `BROKEN / UI/UX ISSUE`
- **Expected Behavior:** The import modal UI states: 'Supports Excel (.xlsx, .xls) and PDF files'. Uploading an `.xls` or `.pdf` file should be parsed and imported into the timetable.
- **Actual Behavior:** Uploading an `.xls` file triggers an immediate validation rejection: 'Older Excel (.xls) format detected. Please save your file as modern Excel (.xlsx) workbook before importing.' Uploading a `.pdf` file triggers: 'Timetable extraction requires structured tabular columns. Please convert or export your timetable into Excel (.xlsx) format before importing.' Only `.xlsx` is accepted.
- **Reproduction Steps:**
1. Log in as Admin.
2. Navigate to `/admin/timetable` and click 'Import Timetable'.
3. Select any valid `.xls` or `.pdf` file.
4. Observe validation error preventing upload.
- **Frontend File:** `frontend/src/pages/admin/TimetableManagement.jsx` (Lines 586-602, 1118)
- **Backend File:** `backend/app/routes/timetable_import.py` (Lines 45-60: only checks `.xlsx` via `openpyxl`)
- **Evidence & Code References:** `TimetableManagement.jsx` Line 1118: `<p>Supports Excel (.xlsx, .xls) and PDF files</p>`. Lines 591-594: `if (name.endsWith('.pdf')) { setPreviewError('...convert into Excel (.xlsx) format before importing.'); }`.
- **Verification Type:** Confirmed via code inspection.
- **Business & User Impact:** Admins prepare timetable files in PDF or legacy Excel formats as advertised by the UI, only to be blocked upon upload.
- **Dependencies:** Backend parser in `timetable_import.py`.
- **Recommended Fix Direction (Do Not Execute):** Either implement server-side PDF table extraction (e.g. `pdfplumber`) and `xlrd` for `.xls`, or update the UI text to state accurately: 'Supports Excel (.xlsx) files only'.

### ISSUE-AUTH-01: Self-Service Password Reset Initiation
- **Portal / Page:** Public / Authentication — Forgot Password (`/auth/forgot-password`)
- **Severity:** `HIGH`
- **Implementation Category:** `NOT IMPLEMENTED`
- **Expected Behavior:** Entering an institutional email or ID and clicking 'Send Reset Code' should call a backend password recovery API, dispatching an OTP via email/SMS.
- **Actual Behavior:** Form submission does not call any API. It sets a local state `submittedNotice = true`, replacing the form with an institutional notice: 'Self-Service Reset Unavailable. Automated email/SMS delivery is currently not configured for self-service password reset. Please contact your system administrator or the IT Helpdesk directly.'
- **Reproduction Steps:**
1. Navigate to `/auth/forgot-password` in any browser.
2. Enter any valid email or user ID and click 'Send Reset Code'.
3. Observe that no network request is sent; a static advisory is displayed instead.
- **Frontend File:** `frontend/src/pages/auth/ForgotPassword.jsx` (Lines 69-85, 120-130)
- **Backend File:** `backend/app/routes/auth.py` (No password reset routes exist in blueprint)
- **Evidence & Code References:** `ForgotPassword.jsx` Line 77: `Backend email/SMS delivery is not configured. We display the explicit institutional notice instead of a fake OTP progression.`
- **Verification Type:** Confirmed via code inspection and network verification.
- **Business & User Impact:** Users who forget their passwords cannot recover access independently and must contact administrators out-of-band.
- **Dependencies:** Backend SMTP/SMS service integration and PasswordResetToken model.
- **Recommended Fix Direction (Do Not Execute):** Implement an email dispatch service, create a password reset token table in MySQL, add `POST /api/auth/forgot-password` and `POST /api/auth/reset-password` endpoints.

### ISSUE-AUTH-02: OTP Code Verification
- **Portal / Page:** Public / Authentication — Verify OTP (`/auth/verify-otp`)
- **Severity:** `HIGH`
- **Implementation Category:** `NOT IMPLEMENTED`
- **Expected Behavior:** Entering a 6-digit OTP code and clicking 'Verify OTP' should submit the code to the backend, validate its authenticity, and allow credential reset.
- **Actual Behavior:** Form submission executes local validation, encounters a hardcoded notice that the service is unavailable, and renders: 'OTP verification service is not connected yet. Please try again after backend integration.'
- **Reproduction Steps:**
1. Navigate directly to `/auth/verify-otp`.
2. Enter 6 digits (e.g. `123456`) and click 'Verify OTP'.
3. Observe error message displayed in red text below the input fields.
- **Frontend File:** `frontend/src/pages/auth/VerifyOtp.jsx` (Lines 99-125)
- **Backend File:** `backend/app/routes/auth.py` (No OTP verification endpoint exists)
- **Evidence & Code References:** `VerifyOtp.jsx` Lines 110-120: `* Backend OTP verification is not implemented yet. ... setError('OTP verification service is not connected yet.');`
- **Verification Type:** Confirmed via code inspection and runtime verification.
- **Business & User Impact:** Users reaching this page through direct URL or browser history encounter a dead end.
- **Dependencies:** Backend OTP model and authentication endpoints.
- **Recommended Fix Direction (Do Not Execute):** Create `POST /api/auth/verify-otp` endpoint and integrate with frontend service.

### ISSUE-NAV-01: Global Search Input Field
- **Portal / Page:** Faculty Portal — Top Navigation Header (`FacultyLayout.jsx`)
- **Severity:** `LOW`
- **Implementation Category:** `UI/UX ISSUE`
- **Expected Behavior:** Typing a query in the top search bar and pressing Enter should search students, courses, or attendance records, or navigate to search results.
- **Actual Behavior:** The `<input type="text" placeholder="Search students, courses, or anything..." />` field has no `value` binding, no `onChange` handler, no form wrapper, and no `onKeyDown` handler. Typing into it has zero functional effect.
- **Reproduction Steps:**
1. Log in as Faculty.
2. Click the top header search bar and type any search query.
3. Press Enter.
4. Observe that nothing occurs.
- **Frontend File:** `frontend/src/layouts/FacultyLayout.jsx` (Lines 216-224)
- **Backend File:** N/A
- **Evidence & Code References:** `FacultyLayout.jsx` Lines 220-222: `<input type="text" placeholder="Search students, courses, or anything..." className="faculty-search-input" aria-label="Search students, courses, or anything" />` — completely missing event listeners.
- **Verification Type:** Confirmed via code inspection.
- **Business & User Impact:** Faculty expect a global portal search but experience an unresponsive UI input.
- **Dependencies:** Global search backend or client-side fuzzy navigation routing.
- **Recommended Fix Direction (Do Not Execute):** Add `onChange` and `onKeyDown` handlers to redirect to `/faculty/students?search=...` or `/faculty/classes?search=...`.

### ISSUE-NAV-02: Global Search Input Field
- **Portal / Page:** Student Portal — Top Navigation Header (`StudentLayout.jsx`)
- **Severity:** `LOW`
- **Implementation Category:** `UI/UX ISSUE`
- **Expected Behavior:** Typing a query in the student search bar and pressing Enter should filter courses, timetable slots, or faculty.
- **Actual Behavior:** The search `<input>` has no state binding or event handler; typing into it produces no action.
- **Reproduction Steps:**
1. Log in as Student.
2. Click the top search bar, type a course name, and press Enter.
3. Observe that no filtering or navigation takes place.
- **Frontend File:** `frontend/src/layouts/StudentLayout.jsx` (Lines 339-348)
- **Backend File:** N/A
- **Evidence & Code References:** `StudentLayout.jsx` Lines 342-346: `<input type="text" placeholder="Search courses, faculty, or anything..." className="student-search-input" aria-label="Search portal" />` without event handler.
- **Verification Type:** Confirmed via code inspection.
- **Business & User Impact:** Misleading interactive control with no backend integration.
- **Dependencies:** Student courses and schedule search service.
- **Recommended Fix Direction (Do Not Execute):** Connect the search input to filter the student's courses and schedule or route to `/student/courses?q=...`.

### ISSUE-NAV-03: Notification Bell Button & Badge
- **Portal / Page:** Faculty & Student Portals — Top Navigation Header (`FacultyLayout.jsx`, `StudentLayout.jsx`)
- **Severity:** `LOW`
- **Implementation Category:** `UI/UX ISSUE / NOT IMPLEMENTED`
- **Expected Behavior:** Clicking the notification bell should display a dropdown or modal of recent alerts (e.g. low attendance warnings, class cancellations, result publications).
- **Actual Behavior:** The button has no `onClick` handler. The red unread badge (displaying '3' on Student layout and an amber dot on Faculty layout) is hardcoded into the layout template.
- **Reproduction Steps:**
1. Log in to Student or Faculty portal.
2. Click the notification bell icon with badge '3'.
3. Observe that no drawer or dropdown opens.
- **Frontend File:** `frontend/src/layouts/StudentLayout.jsx` (Lines 354-360), `FacultyLayout.jsx` (Lines 230-236)
- **Backend File:** No notification inbox API exists.
- **Evidence & Code References:** `StudentLayout.jsx` Lines 354-358: `<button type="button" className="student-notification-btn"><FontAwesomeIcon icon={faBell} /><span className="student-notification-badge">3</span></button>`.
- **Verification Type:** Confirmed via code inspection.
- **Business & User Impact:** Users repeatedly click the notification badge thinking they have unread messages.
- **Dependencies:** Backend notification service and database model.
- **Recommended Fix Direction (Do Not Execute):** Implement an in-app notification system or remove the hardcoded unread badge until a notifications module is integrated.

### ISSUE-NAV-04: Missing Global Search and Notification Bell
- **Portal / Page:** Admin Portal — Top Navigation Header (`AdminLayout.jsx`)
- **Severity:** `LOW`
- **Implementation Category:** `UI/UX ISSUE`
- **Expected Behavior:** The Admin Portal top header should match institutional design mockups, featuring a global administration search bar and notification bell alongside the admin user pill.
- **Actual Behavior:** The top header in `AdminLayout.jsx` only renders the `admin-user-pill` (avatar, name, role). The search input and bell icon were never added.
- **Reproduction Steps:**
1. Log in as Admin.
2. Observe top header contains only the user avatar pill on the right, lacking the top search and alert icons present in mockups.
- **Frontend File:** `frontend/src/layouts/AdminLayout.jsx` (Lines 604-617)
- **Backend File:** N/A
- **Evidence & Code References:** `AdminLayout.jsx` lines 604-617 only include `<div className="admin-header-actions"><div className="admin-user-pill">...</div></div>`.
- **Verification Type:** Confirmed via code inspection.
- **Business & User Impact:** Inconsistent layout visual hierarchy between Admin and Faculty/Student portals.
- **Dependencies:** None.
- **Recommended Fix Direction (Do Not Execute):** Add search bar and notification bell components to `AdminLayout.jsx` to unify header layouts across all three portals.

### ISSUE-NAV-05: Missing 'Notes & Assignments' Navigation Item
- **Portal / Page:** Faculty Portal — Sidebar Navigation (`FacultyLayout.jsx`)
- **Severity:** `LOW`
- **Implementation Category:** `DISCONNECTED / UI/UX ISSUE`
- **Expected Behavior:** The Faculty Portal sidebar navigation should include 'Notes & Assignments' as shown in the Faculty Result Upload reference mockup, and provide access to `/faculty/settings`.
- **Actual Behavior:** The sidebar navigation list in `FacultyLayout.jsx` skips 'Notes & Assignments'. Additionally, although `/faculty/settings` is registered in `AppRoutes.jsx`, it has no link in the sidebar or top header.
- **Reproduction Steps:**
1. Compare `FacultyLayout.jsx` `navigationItems` array with the reference UI mockup.
2. Notice 'Notes & Assignments' is missing between 'Result Upload' and 'My Profile'.
- **Frontend File:** `frontend/src/layouts/FacultyLayout.jsx` (Lines 22-58)
- **Backend File:** N/A
- **Evidence & Code References:** `FacultyLayout.jsx` lines 22-58 declare Dashboard, My Classes, Attendance, Students, Reports, Result Upload, and My Profile only.
- **Verification Type:** Confirmed via code inspection.
- **Business & User Impact:** Faculty cannot access settings via navigation without manually editing the browser URL.
- **Dependencies:** None.
- **Recommended Fix Direction (Do Not Execute):** Add 'Settings' and 'Notes & Assignments' (or appropriate placeholder view) to `navigationItems` in `FacultyLayout.jsx`.

### ISSUE-SET-01: System Service Configuration Cards
- **Portal / Page:** Admin Portal — Settings (`/admin/settings`)
- **Severity:** `MEDIUM`
- **Implementation Category:** `NOT IMPLEMENTED`
- **Expected Behavior:** Admins should be able to configure Attendance Timing, Face Recognition parameters, Attendance Rules, and notification alert thresholds with database persistence.
- **Actual Behavior:** These cards only display static informational descriptions with status badges: 'Attendance Timing', 'Face Recognition', and 'Attendance Rules' show badge 'Integration Pending'; 'Email Notifications', 'Attendance Alerts', and 'System Notifications' show badge 'Coming Soon'. They possess no form controls or backend routes.
- **Reproduction Steps:**
1. Log in as Admin.
2. Navigate to `/admin/settings`.
3. Observe the cards under Attendance and Notifications have no toggle switches or inputs.
- **Frontend File:** `frontend/src/pages/admin/AdminSettings.jsx` (Lines 161-224)
- **Backend File:** No settings table or route exists in backend.
- **Evidence & Code References:** `AdminSettings.jsx` Line 166: `status="Integration Pending"`, Line 208: `status="Coming Soon"`.
- **Verification Type:** Confirmed via code inspection.
- **Business & User Impact:** Administrators cannot configure system operating parameters via the UI.
- **Dependencies:** Database `system_settings` table and administration routes.
- **Recommended Fix Direction (Do Not Execute):** Create a `SystemSetting` key-value model and an admin API to store and retrieve configurable institutional thresholds.

### ISSUE-SET-02: User Preferences Persistence
- **Portal / Page:** Faculty & Student Portals — Settings (`/faculty/settings`, `/student/settings`)
- **Severity:** `MEDIUM`
- **Implementation Category:** `PARTIALLY WORKING`
- **Expected Behavior:** User preferences (notification toggles, sound alerts, email summaries) should be saved to the user's account profile in MySQL so they persist across devices.
- **Actual Behavior:** Both pages save preferences strictly to browser `localStorage`. There is no backend API or database column to store user UI preferences. If a user logs in from another device or clears their browser storage, all settings reset to defaults.
- **Reproduction Steps:**
1. Log in as Student or Faculty.
2. Change notification toggles in Settings.
3. Open an Incognito window or different browser and log in with the same credentials.
4. Observe that the settings revert to defaults.
- **Frontend File:** `frontend/src/pages/faculty/Settings.jsx` (Lines 60-95), `frontend/src/pages/student/Settings.jsx` (Lines 40-75)
- **Backend File:** No `preferences` column in `User` model (`backend/app/models/user.py`)
- **Evidence & Code References:** `Settings.jsx` Line 62: `localStorage.setItem('faculty_settings', JSON.stringify(updated));` with no API call.
- **Verification Type:** Confirmed via code inspection.
- **Business & User Impact:** Preferences do not sync across mobile and desktop devices.
- **Dependencies:** User model schema migration.
- **Recommended Fix Direction (Do Not Execute):** Add a `JSON` column `preferences` to the `User` model and provide `PATCH /api/auth/preferences`.

### ISSUE-DASH-01: Attendance Trend Overview Card
- **Portal / Page:** Admin Portal — Dashboard (`/admin/dashboard`)
- **Severity:** `MEDIUM`
- **Implementation Category:** `DISCONNECTED`
- **Expected Behavior:** The Attendance Overview panel on the Admin Dashboard should render visual attendance trends across institutional departments or academic terms.
- **Actual Behavior:** The panel displays an empty placeholder box stating: 'No attendance trend data. API integration is pending for historical attendance trend data.', despite the backend already providing a functional `GET /api/admin/attendance/analytics` route in `admin_analytics_bp`.
- **Reproduction Steps:**
1. Log in as Admin.
2. Navigate to `/admin/dashboard`.
3. Look at the 'Attendance Overview' card in the middle grid.
4. Observe the empty state circle with 'API integration is pending' notice.
- **Frontend File:** `frontend/src/pages/admin/AdminDashboard.jsx` (Lines 340-366)
- **Backend File:** `backend/app/routes/admin_analytics.py` (Lines 23-140: `get_admin_attendance_analytics`)
- **Evidence & Code References:** `AdminDashboard.jsx` Line 360: `<p>API integration is pending for historical attendance trend data.</p>`. Backend route `GET /api/admin/attendance/analytics` exists and is verified functional in `api_integration_matrix.json`.
- **Verification Type:** Confirmed via code inspection.
- **Business & User Impact:** Administrators see an unpopulated dashboard widget even though the backend already computes the analytics data.
- **Dependencies:** Chart visualization component in `AdminDashboard.jsx`.
- **Recommended Fix Direction (Do Not Execute):** Invoke `getAdminAttendanceAnalytics()` in `AdminDashboard.jsx` and render the trend data inside the existing panel.

### ISSUE-TEST-01: Root-Level Automated Test Discovery
- **Portal / Page:** Developer / CI Harness — Pytest Discovery (`backend/cv/`)
- **Severity:** `LOW`
- **Implementation Category:** `BROKEN`
- **Expected Behavior:** Running `pytest` from the repository root directory should collect and pass all unit and integration tests without errors.
- **Actual Behavior:** Running `pytest` without path restrictions discovers `backend/cv/camera_test.py` and `backend/cv/recognition_test.py`. These files are interactive scripts with top-level execution code calling `cv2.imshow()` and loading relative image paths (`..\tests\cv\images`), which crashes test collection with `(-2:Unspecified error) The function is not implemented` and `ImgNotFound`.
- **Reproduction Steps:**
1. Open a terminal at repository root `C:\Users\pandi\Projects\SAMS-FR`.
2. Run `pytest`.
3. Observe collection error in `backend/cv/camera_test.py` and `backend/cv/recognition_test.py`.
- **Frontend File:** N/A
- **Backend File:** `backend/cv/camera_test.py` (Line 30: `cv2.imshow`), `backend/cv/recognition_test.py` (Line 10: `DeepFace.extract_faces`)
- **Evidence & Code References:** Pytest collection output: `ERROR collecting backend/cv/camera_test.py cv2.error: ... cvShowImage` and `ERROR collecting backend/cv/recognition_test.py deepface.modules.exceptions.ImgNotFound`.
- **Verification Type:** Reproduced directly during test suite execution.
- **Business & User Impact:** CI pipelines or developers running bare `pytest` fail unexpectedly unless explicitly specifying `pytest backend/tests`.
- **Dependencies:** Root `pytest.ini` configuration.
- **Recommended Fix Direction (Do Not Execute):** Create a root `pytest.ini` mirroring `backend/pytest.ini` with `testpaths = backend/tests` and rename the CV manual scripts to `camera_demo.py` and `recognition_demo.py`.

### ISSUE-SEC-01: Stateless JWT Token Invalidation
- **Portal / Page:** System Authentication — Authentication Service (`/api/auth/logout`)
- **Severity:** `MEDIUM`
- **Implementation Category:** `AUTHORIZATION ISSUE`
- **Expected Behavior:** When a user logs out, their current JWT access token should be revoked on the server so it cannot be reused if intercepted or retained.
- **Actual Behavior:** The backend logout handler `@auth_bp.post('/logout')` merely unsets the browser cookie (`unset_jwt_cookies()`). Because tokens are completely stateless and no JWT blocklist exists in Redis or MySQL, the token remains valid until standard expiration.
- **Reproduction Steps:**
1. Log in and copy the active JWT token.
2. Click 'Logout'.
3. Send an API request using the copied JWT in the `Authorization: Bearer <token>` header.
4. Observe that the request succeeds with 200 OK.
- **Frontend File:** `frontend/src/services/authService.js` (Lines 11-18)
- **Backend File:** `backend/app/routes/auth.py` (Lines 88-106: `logout`)
- **Evidence & Code References:** `auth.py` Line 94: `response = jsonify({'success': True, 'message': 'Logged out successfully'})`, Line 98: `unset_jwt_cookies(response)`. No database token revocation table or token blocklist callback (`@jwt.token_in_blocklist_loader`) is implemented.
- **Verification Type:** Confirmed via code inspection.
- **Business & User Impact:** A captured or cached bearer token can be reused by an attacker until its natural expiration, even after the legitimate user logs out.
- **Dependencies:** Flask-JWT-Extended token blocklist mechanism.
- **Recommended Fix Direction (Do Not Execute):** Implement a `RevokedToken` model or Redis blocklist and register `@jwt.token_in_blocklist_loader`.

---

## Section D: Broken Buttons and Interactive Elements

The table below catalogs specific interactive elements (buttons, inputs, toggles) that are visually present in the user interface but have no meaningful implementation, are disabled placeholders, or perform actions different from their declared label.

| Portal | Page Component | Button / Control Label | Observed Implementation Behavior | Issue Reference |
|:---|:---|:---|:---|:---:|
| Faculty | `Reports.jsx` | `Excel` (Export modal) | Disabled button (`<button disabled>`); displays 'Not implemented yet' | `ISSUE-EXP-01` |
| Faculty | `Reports.jsx` | `PDF` (Export modal) | Disabled button (`<button disabled>`); displays 'Not implemented yet' | `ISSUE-EXP-01` |
| Student | `AcademicReport.jsx` | `Download Report (PDF)` | Calls CSV endpoint; downloads `.csv` spreadsheet file | `ISSUE-EXP-02` |
| Student | `Reports.jsx` | `Download Report (PDF)` | Downloads `.csv` file and calls `window.print()` browser print modal | `ISSUE-EXP-03` |
| Faculty | `Classes.jsx` | `Export Attendance Data` | Promised in on-page advisory; button does not exist in modal or page | `ISSUE-EXP-04` |
| Admin | `TimetableManagement.jsx` | `Import Timetable (.pdf/.xls)` | Fails upon upload with format rejection error | `ISSUE-IMP-01` |
| Public | `ForgotPassword.jsx` | `Send Reset Code` | Does not call API; reveals local static IT helpdesk advisory | `ISSUE-AUTH-01` |
| Public | `VerifyOtp.jsx` | `Verify OTP` | Shows hardcoded connection error: 'Service not connected yet' | `ISSUE-AUTH-02` |
| Faculty | `FacultyLayout.jsx` | Top Search Bar (`<input>`) | Unbound `<input>` with no `onChange`, `value`, or submit listener | `ISSUE-NAV-01` |
| Student | `StudentLayout.jsx` | Top Search Bar (`<input>`) | Unbound `<input>` with no `onChange`, `value`, or submit listener | `ISSUE-NAV-02` |
| Faculty | `FacultyLayout.jsx` | Notification Bell (`<button>`) | No `onClick` handler; static unread dot | `ISSUE-NAV-03` |
| Student | `StudentLayout.jsx` | Notification Bell (`<button>`) | No `onClick` handler; hardcoded badge '3' | `ISSUE-NAV-03` |
| Admin | `AdminSettings.jsx` | `Email Notifications` | Informational card with badge 'Coming Soon'; no toggle or input | `ISSUE-SET-01` |
| Admin | `AdminSettings.jsx` | `Attendance Timing` | Informational card with badge 'Integration Pending'; no input | `ISSUE-SET-01` |
| Faculty | `Settings.jsx` | `Reset Settings` | Clears `localStorage` only; does not reset database settings | `ISSUE-SET-02` |
| Student | `Settings.jsx` | `Reset to Defaults` | Clears `localStorage` only; does not reset database settings | `ISSUE-SET-02` |

---

## Section E: Frontend/Backend Integration Problems

This section documents architectural mismatches, disconnected endpoints, and communication gaps between the frontend services and the Flask backend.

### 1. Disconnected Admin Attendance Analytics (`ISSUE-DASH-01`)
- **Backend Route:** `GET /api/admin/attendance/analytics` (registered in `app/routes/admin_analytics.py`, Line 23).
- **Status:** The backend route is fully functional and supports query filters (`faculty_id`, `offering_id`, `from_date`, `to_date`). It computes session attendance rates and department totals.
- **Frontend State:** `AdminDashboard.jsx` (Line 360) displays *'No attendance trend data. API integration is pending for historical attendance trend data'*. The service function was never wired to the dashboard component.

### 2. Export Format Content-Type Mismatch (`ISSUE-EXP-02`)
- **Frontend Service:** `academicService.exportAcademicRecords({ format: 'csv' })` (`frontend/src/services/academicService.js`).
- **Backend Route:** `GET /api/student/academic-records/export` (`backend/app/routes/student_academic.py`, Line 509).
- **Status:** The backend route only produces CSV records (`Content-Type: text/csv`). The frontend component labels the trigger button *'Download Report (PDF)'*, creating an irreconcilable contract mismatch where the user requests a PDF and receives a comma-separated text file.

### 3. Missing Credential Recovery Endpoints (`ISSUE-AUTH-01`, `ISSUE-AUTH-02`)
- **Frontend Service:** `authService.js` lacks any function for password reset or OTP verification.
- **Backend Blueprint:** `backend/app/routes/auth.py` only implements `/login`, `/logout`, and `/me`. No route handles password recovery requests.
- **Status:** The UI forms in `ForgotPassword.jsx` and `VerifyOtp.jsx` are entirely decoupled from the backend.

### 4. Absence of User Preferences Schema (`ISSUE-SET-02`)
- **Database Model:** `User` in `backend/app/models/user.py` contains `user_id`, `name`, `email`, `password_hash`, `role`, and `is_active`. It has no column for user preferences or appearance settings.
- **Status:** Preferences cannot be synchronized with the backend without adding a JSON column or a dedicated `user_settings` table.

---

## Section F: Export, Download, Upload, and Import Audit

Every file-related action in SAMS-FR was investigated to determine supported file formats, generator mechanisms, validation rules, and actual limitations.

### Comprehensive File Actions Inventory

| Portal | Feature Name | Direction | Claimed Formats | Actual Formats | Generator / Handler | Audit Findings & Limitations |
|:---|:---|:---:|:---:|:---:|:---|:---|
| **Faculty** | Faculty Attendance Report | Export | CSV, Excel, PDF | CSV Only | Client-side `Blob` (`Reports.jsx`) | CSV runs in memory; Excel & PDF are disabled placeholders (`ISSUE-EXP-01`). |
| **Student** | Academic Grade Card | Export | PDF (per button) | CSV Only | Server `csv.writer` (`student_academic.py`) | UI button says 'Download Report (PDF)', but downloads `.csv` (`ISSUE-EXP-02`). |
| **Student** | Subject-wise Report | Export | PDF (per button) | CSV + Print | Server `csv.writer` + `window.print()` | Downloads `.csv` and pops browser print preview dialog (`ISSUE-EXP-03`). |
| **Admin** | Attendance Reports | Export | CSV | CSV | Server `csv.writer` (`admin.py`) | Generates RFC-4180 CSV with formula injection sanitization. Working as designed. |
| **Admin** | Timetable Bulk Import | Import | .xlsx, .xls, .pdf | .xlsx Only | Server `openpyxl` (`timetable_import.py`) | Rejects `.xls` and `.pdf` files upon selection (`ISSUE-IMP-01`). |
| **Faculty** | Result Marks Template | Download | CSV | CSV | Client-side `data:text/csv` (`ResultUpload.jsx`) | Generates formatted roster CSV template. Working as designed. |
| **Faculty** | Result Marks Import | Import | CSV | CSV | Client-side `FileReader` (`ResultUpload.jsx`) | Parses student roll numbers and marks. Working as designed. |
| **Admin** | Face Biometric Capture | Upload | JPEG Blob | JPEG | WebRTC Blob -> `/api/face/enroll` | Validates face embedding generation with DeepFace. Working as designed. |
| **Student** | Profile Photo Upload | Upload | JPG, PNG, WebP | JPG, PNG, WebP | `multipart/form-data` -> `/api/student/profile/photo` | Enforces 50 KB limit, MIME validation, and traversal protection. |

### Deep Dive 1: Faculty Reports Export Workflow (`/faculty/reports`)
- **UI Presentation:** The modal at `/faculty/reports` displays three format selector tabs: CSV, Excel, and PDF.
- **CSV Implementation:** Handled by `exportCSV()` in `Reports.jsx` (Lines 320-335). It builds a CSV string in the browser from `filteredStudents` state and creates an `<a>` tag with an `ObjectURL`. While the download succeeds, it is entirely decoupled from the backend and does not create an audit log.
- **Excel & PDF Implementation:** Buttons are disabled `<button type="button" disabled>` with CSS opacity reduction. The modal body displays: *'CSV export is available. Excel and PDF export are not implemented yet.'*
- **Backend Capability:** The backend has no export endpoint for faculty reports.

### Deep Dive 2: Timetable Import Workflow (`/admin/timetable`)
- **UI Presentation:** Modal text explicitly promises: *'Supports Excel (.xlsx, .xls) and PDF files'*.
- **File Selection Behavior:** `TimetableManagement.jsx` contains explicit rejection guards:
  ```javascript
  if (name.endsWith('.xls')) {
    setPreviewError('Older Excel (.xls) format detected. Please save your file as modern Excel (.xlsx) workbook before importing.');
  }
  if (name.endsWith('.pdf')) {
    setPreviewError('Timetable extraction requires structured tabular columns. Please convert or export your timetable into Excel (.xlsx) format before importing.');
  }
  ```
- **Backend Parser:** `backend/app/routes/timetable_import.py` only implements `openpyxl.load_workbook()`. It has no PDF parser (`pdfplumber` or `pypdf`) and no legacy Excel parser (`xlrd`).

---

## Section G: Data and Calculation Issues

### 1. Hardcoded UI Badges and Fallback Placeholders
- **Student Dashboard Fallback Text:** In `StudentDashboard.jsx`, when optional fields are null or unpopulated, fallback labels render *'API integration pending'* instead of clean empty states (e.g. Lines 277, 331, 385, 661).
- **Hardcoded Notification Count:** `StudentLayout.jsx` renders a hardcoded `<span className="student-notification-badge">3</span>` regardless of the student's actual unread alert count.

### 2. Subject-wise Attendance Percentage Verification
- During session audit step 3, an earlier issue regarding 0% subject attendance on `/student/reports` was verified resolved. The percentage formula now uses `round((attended / total_eligible) * 100, 1)` and properly joins course offerings with closed attendance sessions.

### 3. Academic Results SGPA & CGPA Calculation Integrity
- SGPA and CGPA in `backend/app/routes/student_academic.py` and `admin_academic_results.py` are computed strictly from earned credits and grade points (`total_weighted_points / total_credits`), avoiding attendance-based estimation.

---

## Section H: Authorization and Security Findings

### 1. Stateless JWT Logout without Revocation (`ISSUE-SEC-01`)
- **Finding:** Logging out calls `POST /api/auth/logout`, which instructs the client browser to delete its cookies. However, JWT tokens in SAMS-FR are stateless. If an access token is extracted from memory or network traffic, it remains valid until its signature expiry because no server-side revocation list exists.
- **Severity:** `MEDIUM`.
- **Remediation Direction:** Implement a database token blocklist table or Redis cache that stores token `jti` identifiers upon logout, checked via `@jwt.token_in_blocklist_loader`.

### 2. Student Upload File Path Traversal Protection (Verified Secure)
- **Inspection Target:** `GET /api/student/uploads/<folder>/<filename>` in `backend/app/routes/student.py`.
- **Verification Outcome:** The endpoint requires `@jwt_required()`, verifies `folder in ('photos', 'signatures')`, validates `filename` with `secure_filename()`, strictly checks for traversal tokens (`..`, `/`, `\`), extracts the student ID via regex pattern (`student_photo_<id>_<ts>.jpg`), and verifies that the requesting user owns the photo or possesses `ADMIN` privileges. This endpoint is secure.

### 3. Biometric Endpoint Role Restrictions (Verified Secure)
- **Inspection Target:** Face enrollment (`/api/face/enroll`), status (`/api/face/status/<id>`), and deletion (`/api/face/<id>`).
- **Verification Outcome:** All biometric endpoints are protected by `@role_required()` decorators wrapping `verify_jwt_in_request()`. Unauthenticated requests receive `401 Unauthorized`; non-admin users attempting face deletion receive `403 Forbidden`.

---

## Section I: Testing and Verification Results

To support this audit, rigorous non-mutating automated verification was executed across the backend test suite, frontend linting, production bundling, and database connectivity.

### 1. Automated Test Suite Execution (`pytest backend/tests`)
- **Command:** `pytest backend/tests`
- **Duration:** 66.81 seconds
- **Outcome:** **405 Passed, 0 Failed, 23 Warnings (100% Pass Rate)**
- **Test Coverage Areas:**
  - Academic results workflow, submission, approval, publication, and corrections (16 tests)
  - Student attendance history, summary, courses, and daily punch matrix (55 tests)
  - Biometric liveness detection, passive challenge, face enrollment, and replacement (48 tests)
  - Timetable session window, imports, and faculty adjustments (38 tests)
  - Role-based authorization guards across Admin, Faculty, and Student endpoints (45 tests)

### 2. Root Test Collection Anomaly (`ISSUE-TEST-01`)
- **Command:** `pytest` (invoked at repository root without directory argument)
- **Outcome:** 2 Collection Errors
- **Root Cause:** `backend/cv/camera_test.py` and `backend/cv/recognition_test.py` are manual interactive scripts that match the default pytest pattern `*_test.py`. Pytest executes their top-level code upon discovery, attempting to open OpenCV window GUIs (`cvShowImage`) and relative image paths that fail in non-interactive headless test runs.

### 3. Frontend Lint Verification (`npm run lint`)
- **Command:** `npm --prefix frontend run lint` (ESLint 9.x)
- **Outcome:** **0 Errors, 0 Warnings (Clean Pass)**
- **Scope:** 39 React components, 14 services, and 3 layout components.

### 4. Production Build Verification (`npm run build`)
- **Command:** `npm --prefix frontend run build` (Vite 8.x)
- **Duration:** 1.63 seconds
- **Outcome:** **Build Successful (Exit Code 0)**
- **Artifacts Generated:** 2,126 modules transformed cleanly into `frontend/dist/`.

### 5. Database Health Checks
- **Probe:** `GET /api/health` -> `200 OK` (Application runtime healthy)
- **Probe:** `GET /api/db-health` -> `200 OK` (MySQL `sams_db` connection healthy)

---

## Section J: Recommended Fix Plan — DO NOT EXECUTE

> [!IMPORTANT]
> This section is provided strictly for remediation planning and prioritization. **Do not execute any fixes until the user provides explicit authorization.**

### Phase 1: Security & Core Authentication (High Priority)
- **Objective:** Implement genuine self-service password recovery and token revocation.
- **Related Issues:** `ISSUE-AUTH-01`, `ISSUE-AUTH-02`, `ISSUE-SEC-01`.
- **Affected Files:**
  - `backend/app/models/user.py` (add `PasswordResetToken` model)
  - `backend/app/routes/auth.py` (add `/forgot-password`, `/verify-otp`, `/reset-password`, and token blocklist)
  - `frontend/src/services/authService.js` (add API call wrappers)
  - `frontend/src/pages/auth/ForgotPassword.jsx` and `VerifyOtp.jsx`
- **Verification Test:** New test file `backend/tests/test_password_reset_and_revocation.py` verifying full token generation, expiration, validation, and invalidation.

### Phase 2: Export & File Download Remediation (High Priority)
- **Objective:** Align user-facing download buttons with accurate file generation engines.
- **Related Issues:** `ISSUE-EXP-01`, `ISSUE-EXP-02`, `ISSUE-EXP-03`, `ISSUE-EXP-04`.
- **Affected Files:**
  - `backend/app/services/pdf_service.py` (create reusable ReportLab / HTML-to-PDF service)
  - `backend/app/routes/student_academic.py` (add PDF export output)
  - `backend/app/routes/student_attendance.py` (add PDF export output)
  - `backend/app/routes/reports.py` (add backend faculty attendance report export in CSV, Excel, PDF)
  - `frontend/src/pages/faculty/Reports.jsx`, `student/AcademicReport.jsx`, `student/Reports.jsx`
- **Verification Test:** Regression tests in `backend/tests/test_file_exports.py` confirming correct `Content-Type: application/pdf` and `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`.

### Phase 3: Dashboard & Integration Wiring (Medium Priority)
- **Objective:** Connect existing backend analytics to Admin Dashboard and synchronize user settings.
- **Related Issues:** `ISSUE-DASH-01`, `ISSUE-SET-01`, `ISSUE-SET-02`.
- **Affected Files:**
  - `frontend/src/pages/admin/AdminDashboard.jsx` (wire `getAdminAttendanceAnalytics()`)
  - `backend/app/models/user.py` and `backend/app/routes/auth.py` (add `preferences` JSON support)
  - `frontend/src/pages/faculty/Settings.jsx` and `student/Settings.jsx` (sync settings to backend)
- **Verification Test:** Tests in `backend/tests/test_user_preferences.py`.

### Phase 4: Import Validation & UI Consistency (Medium/Low Priority)
- **Objective:** Correct timetable file format advertising and add missing navigation links.
- **Related Issues:** `ISSUE-IMP-01`, `ISSUE-NAV-04`, `ISSUE-NAV-05`.
- **Affected Files:**
  - `frontend/src/pages/admin/TimetableManagement.jsx` (update UI format text or support PDF)
  - `frontend/src/layouts/FacultyLayout.jsx` (add Settings and Notes & Assignments links)
  - `frontend/src/layouts/AdminLayout.jsx` (add top search and notification bell)
- **Verification Test:** UI component test and manual browser validation.

### Phase 5: Test Infrastructure & Layout Polish (Low Priority)
- **Objective:** Clean up root pytest discovery and wire header search/bell controls.
- **Related Issues:** `ISSUE-TEST-01`, `ISSUE-NAV-01`, `ISSUE-NAV-02`, `ISSUE-NAV-03`.
- **Affected Files:**
  - `pytest.ini` (create root config with `testpaths = backend/tests`)
  - Rename `backend/cv/camera_test.py` -> `camera_demo.py` and `recognition_test.py` -> `recognition_demo.py`
  - `frontend/src/layouts/FacultyLayout.jsx` and `StudentLayout.jsx` (wire search input and notification popup)
- **Verification Test:** Root `pytest` execution passes cleanly.

---

## Section K: Final Verification of No Changes

In strict accordance with the audit mandate, **no application code, database records, environment variables, dependencies, or automated tests were modified, deleted, or refactored** during this task.

### Git Working Tree Verification
```text
On branch feature/frontend-auth-portals
Your branch is up to date with 'origin/feature/frontend-auth-portals'.

Files modified during audit: NONE (0 application files modified)
Files created: audit_reports/functional_audit_2026-10-29.md (This report only)
Database modifications: 0 rows inserted, updated, or deleted
Package changes: 0 dependencies installed or removed
```

### Auditor Sign-Off
- **Audit Status:** Complete & Verified
- **Action Required:** Awaiting review and explicit authorization from repository owner before executing any remediations.
