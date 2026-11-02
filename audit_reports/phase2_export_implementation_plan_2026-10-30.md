# SAMS-FR — Phase 2: Multi-format Document Export Engine
## Pre-Implementation Audit & Technical Architecture Plan (REPORT ONLY)

**Date:** October 30, 2026
**Document Version:** 1.0.0
**Status:** PROPOSED & READY FOR IMPLEMENTATION APPROVAL
**Branch:** `feature/frontend-auth-portals`
**Reference Audits:**
- `audit_reports/functional_audit_2026-10-29.md`
- `audit_reports/remediation_validation_2026-10-30.md`
- `audit_reports/phase1_completion_report_2026-10-30.md`

---

## 1. Executive Summary

Phase 1 successfully resolved toolchain discoverability, Admin dashboard analytics connection, navigation links, and file-format dropzone accuracy. With the core portal layout and backend baseline stabilized, **Phase 2 addresses a systemic architectural gap: the absence of a unified, multi-format (PDF, Excel, CSV) document export engine across SAMS-FR**.

Currently, document generation is fragmented across portals:
1. **Faculty Reports (`ISSUE-EXP-01`):** Assembles CSV purely in client-side React memory; Excel and PDF buttons are hardcoded disabled.
2. **Student Academic Records (`ISSUE-EXP-02`):** Button explicitly promises a "Download Report (PDF)", but both the frontend service and Flask endpoint only generate a raw `.csv` file.
3. **Student Subject-wise Attendance (`ISSUE-EXP-03`):** Button labeled "Download Report (PDF)" initiates a `.csv` download and immediately fires `window.print()` to trigger the operating system's browser print dialog.
4. **Faculty Classes (`ISSUE-EXP-04`):** On-page advisory explicitly instructs faculty that they can download class rosters and attendance data, but zero export buttons exist in the UI or modal.

This document establishes a **Pre-Implementation Architectural Plan** for building a reusable, secure, server-side document export subsystem in Flask and React without requiring database schema changes or breaking existing integrations.

---

## 2. Current Export Architecture Overview

The existing codebase handles data exports via three disjointed, ad-hoc mechanisms:

```
[ Current Export Fragmentation ]

1. Client-Side DOM Generation (Faculty Reports, Faculty Result Template)
   React Component State (filteredStudents)
     └──> Blob(["\uFEFF", csvContent], { type: "text/csv" })
            └──> document.createElement('a').click()
            * Flaws: Bypasses backend auditing, vulnerable to client DOM manipulation, no PDF/Excel.

2. Browser System Print Workaround (Student Subject-wise Attendance)
   User Clicks "Download Report (PDF)"
     └──> GET /api/student/attendance/export (returns raw CSV)
            └──> window.URL.createObjectURL(blob)
            └──> window.print() [Browser Print Dialog]
            * Flaws: Non-standard UX, bypasses PDF formatting, produces unstyled paper printouts.

3. CSV-Only Backend Endpoints (Student Academic Records, Admin Attendance)
   Flask Route -> csv.writer(io.StringIO)
     └──> Response(mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=..."})
            * Flaws: Completely lacks PDF and Excel binary rendering; misaligned with UI button labels.
```

### Key Architectural Deficiencies Identified:
1. **Absence of a Server-Side PDF Engine:** Neither the Flask backend nor the React frontend contains a library to render binary PDF streams (`application/pdf`).
2. **Underutilized Excel Capabilities:** `openpyxl==3.1.5` is already installed in the Python environment and utilized in one-off developer scripts (`backend/export_faculty.py`), but has not been encapsulated into an application export service.
3. **No Centralized Export Subsystem:** Each Flask route implements its own CSV formatting loops, column names, and sanitization rather than utilizing a shared builder.
4. **Mismatched Content-Type Contracts:** Frontend components trigger download handlers labeled "PDF" that receive `text/csv` from the server, breaking user expectations.

---

## 3. Findings for ISSUE-EXP-01 through ISSUE-EXP-04

Each finding was verified directly against the running codebase and working tree:

| Issue ID | Portal & Page | Reported Defect | Verification Status | Source Evidence |
| :--- | :--- | :--- | :--- | :--- |
| **`ISSUE-EXP-01`** | Faculty Portal → Reports (`/faculty/reports`) | CSV generated in React memory; Excel & PDF buttons disabled `<button disabled>` | **CONFIRMED** | `frontend/src/pages/faculty/Reports.jsx` (L125-175, L1020-1048): `exportCSV` uses client Blob; Excel/PDF buttons hardcoded disabled with text *"CSV export is available. Excel and PDF export are not implemented yet."* Backend `reports_bp` has no `/export` endpoint. |
| **`ISSUE-EXP-02`** | Student Portal → Academic Report (`/student/academic-records`) | UI promises PDF; backend and frontend only produce CSV | **CONFIRMED** | `frontend/src/pages/student/AcademicReport.jsx` (L158-185, L485-502): Button says *"Download Report (PDF)"*, but calls `exportAcademicReport()`, which requests `GET /api/student/academic-records/export`. `backend/app/routes/student_academic.py` (L509-603) returns `text/csv`. |
| **`ISSUE-EXP-03`** | Student Portal → Subject-wise Attendance (`/student/reports`) | UI promises PDF; downloads CSV and triggers `window.print()` | **CONFIRMED** | `frontend/src/pages/student/Reports.jsx` (L230-265, L690-705): `handleDownloadReport` downloads CSV via `exportStudentAttendanceReport()` and calls `window.print()`. Button says *"Download Report (PDF)"*. |
| **`ISSUE-EXP-04`** | Faculty Portal → Classes (`/faculty/classes`) | Advisory promises roster and attendance download; buttons missing | **CONFIRMED** | `frontend/src/pages/faculty/Classes.jsx` (L896-898): Advisory states *"You can also download the class roster or export attendance data."* Neither class cards nor Class Details modal (L1187-1206) contains download buttons. Backend already has roster data in `GET /api/faculty/courses/<id>`. |

---

## 4. Existing Working Functionality

The codebase possesses several well-engineered foundational components that Phase 2 will directly leverage:

1. **Backend Aggregation Queries:**
   - `backend/app/routes/reports.py` (`get_attendance_report`): Accurately computes student session counts (`total_sessions`, `present_sessions`, `absent_sessions`, `attendance_percentage`, `is_low_attendance`) scoped to faculty offerings.
   - `backend/app/routes/student_academic.py` (`export_academic_report`): Efficiently queries published academic results with joins on `Course`, computing `SGPA`, `CGPA`, and `credits_earned`.
   - `backend/app/routes/student_attendance.py` (`export_student_attendance`): Successfully computes student subject-level attendance percentages and statuses (`Excellent`, `Good`, `Needs Attention`).
   - `backend/app/routes/faculty.py` (`get_faculty_course`): Resolves complete student roster information (`name`, `enrollment_no`, `email`, `department`, `batch_year`, `enrollment_status`).
2. **Formula Injection Sanitization:**
   - `backend/app/routes/admin_attendance.py` implements `_sanitize_csv_cell()` to neutralize spreadsheet formula injection vulnerabilities (`=`, `+`, `-`, `@`, `\t`, `\r`).
3. **Client-Side Blob Handling:**
   - Frontend services already use `responseType: "blob"` with Axios for raw file transfers (`attendanceService.js`, `academicService.js`, `adminService.js`).
4. **Excel Styling Reference:**
   - `backend/export_faculty.py` contains a complete openpyxl styling implementation with headers, fonts (`Font(bold=True, color="FFFFFF")`), brand colors (`fgColor="1F4E78"`), auto-width column calculation, freeze panes, and auto-filters.

---

## 5. Confirmed Defects and Missing Functionality

1. **Missing Backend PDF Generation:** Zero PDF generation libraries exist on either frontend or backend.
2. **Disabled Faculty Export Modals:** `frontend/src/pages/faculty/Reports.jsx` prevents users from selecting Excel or PDF formats.
3. **No Faculty Attendance Export Route:** Unlike Admin and Student attendance, `backend/app/routes/reports.py` has no `/export` route; faculty are forced to rely on client-side state downloads.
4. **`window.print()` Browser Trap:** `frontend/src/pages/student/Reports.jsx` opens an unexpected browser printer dialog.
5. **Missing UI Controls in Faculty Classes:** `frontend/src/pages/faculty/Classes.jsx` displays the roster table in a modal but provides no button to export it to Excel/CSV/PDF.
6. **Hardcoded `.csv` File Extensions:** Frontend handlers assume every download is a `.csv` rather than dynamically parsing the `Content-Disposition` header filename or respecting the requested format.

---

## 6. Relevant Frontend and Backend File Paths

### Backend Files:
- `backend/app/routes/reports.py` — Faculty attendance report calculations.
- `backend/app/routes/student_academic.py` — Student academic records and grade card calculations.
- `backend/app/routes/student_attendance.py` — Student subject-wise attendance aggregation.
- `backend/app/routes/faculty.py` — Faculty course roster and details.
- `backend/app/routes/admin_attendance.py` — Admin attendance records export reference.
- `backend/export_faculty.py` — Standalone reference script for openpyxl styling.
- `backend/requirements.txt` — Python dependencies specification.

### Frontend Files:
- `frontend/src/pages/faculty/Reports.jsx` & `Reports.css` — Faculty attendance report page and export modal.
- `frontend/src/pages/student/AcademicReport.jsx` & `AcademicReport.css` — Student grade card and download quick action.
- `frontend/src/pages/student/Reports.jsx` & `Reports.css` — Student subject-wise attendance report and download action.
- `frontend/src/pages/faculty/Classes.jsx` & `Classes.css` — Faculty class management and roster modal.
- `frontend/src/services/reportService.js` — Faculty report API client.
- `frontend/src/services/academicService.js` — Student academic records API client.
- `frontend/src/services/attendanceService.js` — Student attendance API client.
- `frontend/src/services/facultyService.js` — Faculty class and roster API client.

---

## 7. Existing Dependencies and Library Selection Analysis

### 7.1. Current Python Dependencies Audit
Inspection of the virtual environment and `backend/requirements.txt`:
- `openpyxl==3.1.5` — **AVAILABLE & INSTALLED**. Full support for XLSX creation, cell styling, formulas, auto-width, and borders.
- `pandas` — **AVAILABLE & INSTALLED**.
- `Jinja2` — **AVAILABLE & INSTALLED**.
- `reportlab` — **NOT INSTALLED**.
- `weasyprint` — **NOT INSTALLED**.
- `fpdf` / `fpdf2` — **NOT INSTALLED**.

### 7.2. Why a Python PDF Library is Strictly Necessary
A PDF is a structured binary document containing cross-reference tables (`xref`), compressed font dictionaries, and vector layout commands. While CSV and HTML can be rendered with text templates, valid, printable PDF documents cannot be generated reliably without a dedicated PDF library.

### 7.3. Recommended PDF Engine: `reportlab` vs. `fpdf2`
| Criterion | `reportlab` (Recommended) | `fpdf2` (Alternative) | `weasyprint` (Rejected) |
| :--- | :--- | :--- | :--- |
| **Package Weight** | ~3.2 MB | ~250 KB | Heavy (~40 MB + GTK/Pango C-libraries) |
| **Windows Support** | Seamless (prebuilt wheels) | Seamless (pure Python) | Fragile on Windows (requires external C DLLs) |
| **Industry Adoption** | Enterprise standard (Django/Flask) | Lightweight scripting | Web-to-print |
| **Layout Capabilities** | Flowable tables, auto-wrap, multi-page headers | Manual cell coordinate positioning | CSS3 Paged Media |
| **Performance** | Extremely fast (C-accelerated or pure fallback) | Fast | Slow (full browser rendering engine) |

> [!IMPORTANT]
> **Library Recommendation:**
> 1. **Excel Generation:** Use existing, already-installed `openpyxl` (**0 new dependencies**).
> 2. **CSV Generation:** Use built-in standard library `csv` (**0 new dependencies**).
> 3. **PDF Generation:** Add `reportlab` to `backend/requirements.txt`. It is lightweight, stable, standard across academic/enterprise Python systems, and requires no external system DLLs.

*(Per instructions, no package has been installed during this planning task).*

---

## 8. Proposed Unified Export Architecture

We propose creating a modular export engine inside `backend/app/utils/export_engine/`:

```
backend/app/utils/export_engine/
├── __init__.py               # Factory and dispatcher
├── base.py                   # Common interface, sanitization, and streaming helpers
├── csv_builder.py            # RFC 4180 CSV builder with formula injection defense
├── excel_builder.py          # Openpyxl builder with branded styles, fonts, auto-width
└── pdf_builder.py            # ReportLab builder with institutional headers, tables, and footers
```

```
[ Unified Document Flow ]

Client (React UI)
  │ Request: GET /api/.../export?format={pdf|xlsx|csv}&[filters]
  ▼
Flask Route Controller (e.g., student_academic_bp.get("/export"))
  │ 1. Verify JWT & Role Permissions (@faculty_required / @student_required)
  │ 2. Enforce Data Isolation (Current User ID / Offering Ownership)
  │ 3. Fetch & Aggregate Database Records
  ▼
ExportEngine.generate(data, format, template_type)
  │
  ├── if format == 'xlsx' ──> ExcelBuilder (openpyxl) ──> io.BytesIO
  ├── if format == 'pdf'  ──> PDFBuilder (reportlab)  ──> io.BytesIO
  └── if format == 'csv'  ──> CSVBuilder (csv)        ──> io.StringIO
  ▼
Flask Response Dispatcher
  └── send_file(buffer, mimetype=..., as_attachment=True, download_name=...)
```

### Key Design Highlights:
1. **Zero Temporary Disk Files:** All generators stream directly into memory buffers (`io.BytesIO` / `io.StringIO`), avoiding file-system pollution and concurrency locks.
2. **Consistent Visual Identity:**
   - **Primary Brand Color:** Deep Navy (`#1E3A8A` / `#1F4E78`).
   - **Accent Colors:** Emerald Green (`#10B981` Pass/Present), Amber (`#F59E0B` Warning), Ruby Red (`#EF4444` Low Attendance/Fail).
   - **Font Families:** Helvetica / Arial standard fonts across PDF and Excel.
3. **Automated Header Metadata:** Every report includes:
   - Institution Name: *Smart Attendance Management System (SAMS-FR)*.
   - Document Title (e.g., *Official Academic Grade Card*, *Faculty Attendance Summary*).
   - Generated Date & Timestamp.
   - Filtering parameters applied (Semester, Academic Year, Date Range).

---

## 9. Proposed API Endpoint Table

| HTTP | URL | Role | Report Type | Formats | Required / Optional Parameters | Backend Data Source | Authorization Rule | Expected MIME Type | Suggested Filename | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **GET** | `/api/faculty/attendance/reports/export` | Faculty | Attendance Report | `xlsx`, `pdf`, `csv` | `offering_id` (opt), `from_date` (opt), `to_date` (opt), `format` (opt, default `xlsx`) | `reports.py` query logic (`CourseOffering`, `AttendanceSession`, `AttendanceRecord`) | Faculty profile exists; `offering_id` belongs to `faculty.faculty_id`. | `application/vnd.openxmlformats...`, `application/pdf`, `text/csv` | `Faculty_Attendance_<Course>_<Date>.{ext}` | **NEW** |
| **GET** | `/api/student/academic-records/export` | Student, Admin | Official Academic Grade Card | `pdf`, `xlsx`, `csv` | `semester` (opt), `format` (opt, default `pdf`) | `student_academic.py` (`AcademicResult`, `Course`) | Authenticated student owns records (`student_id == current_student.id`); only `is_published=True`. | `application/pdf`, `application/vnd.openxmlformats...`, `text/csv` | `Academic_Grade_Card_<Enrollment>_Sem<X>.{ext}` | **MODIFY** |
| **GET** | `/api/student/attendance/export` | Student | Subject-wise Attendance Report | `pdf`, `xlsx`, `csv` | `academic_year` (opt), `semester` (opt), `format` (opt, default `pdf`) | `student_attendance.py` (`Enrollment`, `AttendanceSession`, `AttendanceRecord`) | Authenticated student owns records (`student_id == current_student.id`). | `application/pdf`, `application/vnd.openxmlformats...`, `text/csv` | `Subject_Attendance_Report_<Enrollment>_{ext}` | **MODIFY** |
| **GET** | `/api/faculty/courses/<int:course_id>/roster/export` | Faculty | Class Roster | `xlsx`, `pdf`, `csv` | `offering_id` (opt), `format` (opt, default `xlsx`) | `faculty.py` (`CourseOffering`, `Enrollment`, `Student`, `User`) | Course offering assigned to authenticated faculty member (`offering.faculty_id == faculty.faculty_id`). | `application/vnd.openxmlformats...`, `application/pdf`, `text/csv` | `Class_Roster_<CourseCode>_Sec<Sec>.{ext}` | **NEW** |

---

## 10. Security and Data Integrity Analysis

### 10.1. Role-Based Access Control & Strict Data Isolation
- **Faculty Isolation:** A faculty member can only export reports and rosters for course offerings they teach. Passing an arbitrary `offering_id` parameter belonging to another faculty member will return `HTTP 403 Forbidden` or `HTTP 404 Not Found`.
- **Student Isolation:** Students cannot supply arbitrary `student_id` query parameters. The student ID is strictly extracted from the validated JWT token (`get_jwt_identity()`).
- **Unpublished Result Protection:** In `student_academic.py`, query filters strictly enforce `is_published == True`. Draft, under-review, or returned grades are completely inaccessible in export documents.

### 10.2. Exclusion of Sensitive Attributes
Export files will strictly exclude:
- User passwords, password hashes, or salt values.
- JWT tokens, session IDs, or refresh cookies.
- Biometric facial embeddings, feature vectors, or raw face image arrays.
- Internal database primary keys where not relevant to academic credentials.

### 10.3. Formula Injection (CSV / Excel Injection) Defense
When exporting to CSV or Excel, user-supplied text (such as student names, course titles, or remarks) starting with dangerous spreadsheet formula characters (`=`, `+`, `-`, `@`, `\t`, `\r`) will be safely escaped using leading single quotes or whitespace padding via `_sanitize_csv_cell()`.

### 10.4. Audit Logging Integration
Where institutional audit logging exists (`backend/app/models/activity_log.py` / `log_activity`), export operations will record:
- `actor_id`: User executing download.
- `action`: `REPORT_EXPORTED`.
- `details`: Format, report type, filter parameters, and timestamp.

---

## 11. Frontend Implementation Plan

### 11.1. Faculty Reports (`frontend/src/pages/faculty/Reports.jsx`)
- **Current State:** Export modal shows disabled Excel and PDF buttons; CSV export generated in browser memory.
- **Required Changes:**
  1. Update `reportService.js` with `exportFacultyAttendanceReport(params = {})` accepting `format`, `offering_id`, `from_date`, `to_date` with `responseType: "blob"`.
  2. Enable all three format buttons: `Excel (.xlsx)`, `PDF (.pdf)`, `CSV (.csv)`.
  3. Replace the client-side `exportCSV()` function with an unified `handleExport(format)` calling `reportService`.
  4. Display active download spinners on the selected button (`exportingFormat === "pdf"`).
  5. Remove the disclaimer text: *"CSV export is available. Excel and PDF export are not implemented yet."*
  6. Automatically trigger browser file download with the server-supplied filename.

### 11.2. Student Academic Report (`frontend/src/pages/student/AcademicReport.jsx`)
- **Current State:** Quick Action button says *"Download Report (PDF)"*, but only downloads `.csv`.
- **Required Changes:**
  1. Update `academicService.exportAcademicReport` to pass `format: "pdf"` by default.
  2. In `handleExport`: Check `response.data.type` or file headers; save as `.pdf` with `application/pdf` Blob.
  3. Optional: Add a split-button or format selector dropdown allowing students to choose between Official PDF Grade Card or Excel/CSV format.
  4. Display clear loading state: *"Generating Official PDF..."*.

### 11.3. Student Subject-wise Report (`frontend/src/pages/student/Reports.jsx`)
- **Current State:** Downloads CSV and executes `window.print()`.
- **Required Changes:**
  1. Remove `window.print()` entirely.
  2. Update `exportStudentAttendanceReport` call to pass `format: "pdf"`.
  3. Save received binary stream as `.pdf` with MIME `application/pdf`.
  4. Display success feedback toast upon completion.

### 11.4. Faculty Classes (`frontend/src/pages/faculty/Classes.jsx`)
- **Current State:** On-page advisory promises download capability, but no buttons exist.
- **Required Changes:**
  1. Add an **"Export Roster"** action button in the Class Details modal header right next to the "Enrolled Students" title.
  2. Add a dropdown menu allowing faculty to choose `Excel (.xlsx)`, `PDF (.pdf)`, or `CSV (.csv)`.
  3. Connect to `facultyService.exportCourseRoster(courseId, { format, offering_id })`.
  4. Provide responsive styling matching existing modal secondary buttons.

---

## 12. Backend Implementation Plan

### 12.1. Shared Utilities Structure (`backend/app/utils/export_engine/`)
1. **`excel_builder.py`:**
   - Class `ExcelReportBuilder`:
     - `add_header(title, subtitle, metadata_dict)`
     - `add_table(headers, rows, column_widths=None, alignments=None, status_column_idx=None)`
     - `get_bytes()`: Returns `BytesIO` buffer ready for `send_file`.
2. **`pdf_builder.py`:**
   - Class `PDFReportBuilder`:
     - Built using `reportlab.platypus` (`SimpleDocTemplate`, `Table`, `Paragraph`, `Spacer`).
     - Applies SAMS-FR branded color palette (`#1E3A8A`, `#3B82F6`, `#F3F4F6`).
     - Header block with institution name, title, generation timestamp.
     - Formatted table with auto-wrap cells and clean borders.
     - Footer with page numbering and computer-generated disclaimer.
3. **`csv_builder.py`:**
   - Class `CSVReportBuilder`:
     - Formula sanitization for all strings.
     - Outputs UTF-8 encoded `StringIO` buffer.

### 12.2. Route Controller Enhancements
1. **`backend/app/routes/reports.py`:**
   - Register route `@reports_bp.get("/export")`.
   - Reuses core query from `get_attendance_report()`.
   - Dispatches data to `ExcelReportBuilder`, `PDFReportBuilder`, or `CSVReportBuilder` based on `request.args.get("format", "xlsx")`.
2. **`backend/app/routes/student_academic.py`:**
   - Update `@student_academic_bp.get("/export")`.
   - Read `format = request.args.get("format", "pdf")`.
   - If `pdf`: Render formatted Academic Transcript using `PDFReportBuilder`.
   - If `xlsx`: Render formatted grade sheet using `ExcelReportBuilder`.
   - If `csv`: Retain existing CSV output with formula protection.
3. **`backend/app/routes/student_attendance.py`:**
   - Update `@student_attendance_bp.get("/export")`.
   - Read `format = request.args.get("format", "pdf")`.
   - Render student subject-wise summary with attendance percentages.
4. **`backend/app/routes/faculty.py`:**
   - Add `@faculty_bp.get("/courses/<int:course_id>/roster/export")`.
   - Enforce faculty ownership.
   - Output enrolled students table with `Roll No`, `Student Name`, `Department`, `Batch`, and `Status`.

---

## 13. Database Impact Assessment

- **Database Schemas:** **ZERO CHANGES**.
- **Database Migrations:** **ZERO MIGRATIONS REQUIRED**.
- **Existing Records:** All exports rely strictly on existing `Student`, `Faculty`, `Course`, `CourseOffering`, `Enrollment`, `AttendanceSession`, `AttendanceRecord`, and `AcademicResult` tables.
- **Performance Impact:**
  - Database queries reuse existing indexes (`offering_id`, `session_date`, `student_id`, `is_published`).
  - Read-only operations with no table locking or write transactions.

---

## 14. Testing Strategy

### 14.1. Automated Backend Test Plan (`backend/tests/`)
1. **Excel Generation Tests:**
   - Verify `openpyxl` returns valid `.xlsx` magic bytes (`PK\x03\x04`).
   - Verify Content-Type `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`.
   - Verify table column headers and row counts match database records.
2. **PDF Generation Tests:**
   - Verify `reportlab` returns valid PDF magic bytes (`%PDF-1.`).
   - Verify Content-Type `application/pdf`.
   - Verify document contains student/faculty names and course titles.
3. **CSV Generation Tests:**
   - Verify CSV header structure and data rows.
   - Verify formula injection characters (`=1+1`) are escaped.
4. **Security & Authorization Tests:**
   - Test student cannot download another student's academic record or attendance report (IDOR check).
   - Test faculty cannot export rosters for course offerings assigned to another faculty member.
   - Test unauthenticated requests return `HTTP 401 Unauthorized`.
   - Test unpublished grades are omitted from student grade card exports.

### 14.2. Frontend Integration & Manual Test Checklist
1. **Faculty Reports:**
   - Click "Export Report" -> Modal opens with active CSV, Excel, and PDF buttons.
   - Clicking Excel downloads `Faculty_Attendance_Report_*.xlsx`.
   - Clicking PDF downloads `Faculty_Attendance_Report_*.pdf`.
   - Clicking CSV downloads server-generated `Faculty_Attendance_Report_*.csv`.
2. **Student Academic Records:**
   - Click "Download Report (PDF)" -> Real `.pdf` file is downloaded.
   - PDF opens cleanly in PDF readers with institutional banner, GPA cards, and subject grades table.
3. **Student Subject-wise Report:**
   - Click "Download Report (PDF)" -> Real `.pdf` file is downloaded.
   - Verify no browser `window.print()` dialog appears.
4. **Faculty Classes:**
   - Open Class Details modal -> "Export Roster" button is visible and active.
   - Downloads enrolled student list in Excel/PDF/CSV.

### 14.3. Full Regression Suite
- Run root `pytest -q` to ensure all 405 existing tests pass without regressions.
- Run `npm --prefix frontend run lint` to guarantee clean ESLint status.
- Run `npm --prefix frontend run build` to confirm production client bundling.

---

## 15. Staged Implementation Roadmap

We recommend dividing the Phase 2 implementation into 6 focused stages:

```
┌─────────────────────────────────────────────────────────────┐
│ Phase 2A: Shared Export Engine Utilities                    │
│ • openpyxl Excel builder, reportlab PDF builder, CSV builder│
└──────────────────────────────┬──────────────────────────────┘
                               │
       ┌───────────────────────┴───────────────────────┐
       ▼                                               ▼
┌──────────────────────────────┐ ┌──────────────────────────────┐
│ Phase 2B: Faculty Reports    │ │ Phase 2C: Student Academic   │
│ • GET /reports/export        │ │ • GET /academic-records/     │
│ • Enable modal Excel/PDF     │ │   export (PDF correction)    │
└──────────────┬───────────────┘ └──────────────┬───────────────┘
               │                                │
               ▼                                ▼
┌──────────────────────────────┐ ┌──────────────────────────────┐
│ Phase 2D: Student Subject-   │ │ Phase 2E: Faculty Classes    │
│ wise Attendance              │ │ • GET /courses/:id/roster/   │
│ • GET /attendance/export(PDF)│ │   export                     │
│ • Remove window.print()      │ │ • Roster export UI button    │
└──────────────┬───────────────┘ └──────────────┬───────────────┘
               │                                │
               └───────────────┬────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ Phase 2F: Comprehensive Testing & Verification              │
│ • Automated test suite, linting, build, and completion doc  │
└─────────────────────────────────────────────────────────────┘
```

### Detailed Breakdown:
- **Phase 2A — Core Export Engine Utilities:**
  - Add `reportlab` dependency to `backend/requirements.txt`.
  - Create `backend/app/utils/export_engine/` (`excel_builder.py`, `pdf_builder.py`, `csv_builder.py`).
  - Unit tests for builders.
- **Phase 2B — Faculty Reports Export (`ISSUE-EXP-01`):**
  - Implement `GET /api/faculty/attendance/reports/export`.
  - Update `reportService.js` and `frontend/src/pages/faculty/Reports.jsx`.
- **Phase 2C — Student Academic Records PDF (`ISSUE-EXP-02`):**
  - Update `GET /api/student/academic-records/export` to support `format=pdf`.
  - Update `AcademicReport.jsx` to receive and download real PDF transcripts.
- **Phase 2D — Student Subject-wise Report PDF (`ISSUE-EXP-03`):**
  - Update `GET /api/student/attendance/export` to support `format=pdf`.
  - Update `Reports.jsx` to download real PDF and eliminate `window.print()`.
- **Phase 2E — Faculty Classes Roster Export (`ISSUE-EXP-04`):**
  - Implement `GET /api/faculty/courses/<course_id>/roster/export`.
  - Update `Classes.jsx` modal with "Export Roster" control.
- **Phase 2F — Full Regression & Final Report:**
  - Automated integration tests in `backend/tests/test_document_exports.py`.
  - Pytest verification, ESLint check, Vite build check.
  - Final Phase 2 completion report.

---

## 16. Risks and Dependencies

| Risk / Dependency | Impact | Probability | Mitigation Strategy |
| :--- | :--- | :--- | :--- |
| **New Dependency (`reportlab`)** | Backend deployment requires `pip install reportlab`. | Low | `reportlab` is pure Python or prebuilt binary wheel with no external GTK/system C-libraries. Safe on all Windows/Linux environments. |
| **Memory Consumption on Large Exports** | Large attendance tables could consume excessive RAM. | Low | Streaming via `BytesIO`; standard semester rosters (< 500 students) consume < 5 MB RAM during document generation. |
| **Axios Blob Caching** | Cached API wrapper in `frontend/src/services/api.js` could serialize Blob responses to JSON `{}`. | Medium | Use `Cache-Control: no-cache` headers on all binary export requests to completely bypass client cache. |
| **Browser Pop-up Blockers** | Some browsers block multiple programmatic download clicks. | Low | Trigger download directly within user gesture handler using standard `<a download="...">` technique. |

---

## 17. Acceptance Criteria for Phase 2 Completion

1. **`ISSUE-EXP-01` Acceptance:**
   - Faculty can export attendance reports in `.xlsx`, `.pdf`, and `.csv`.
   - Disabled buttons and "not implemented" notices are completely removed.
   - Filter criteria (date range, offering) are strictly respected in downloaded files.
2. **`ISSUE-EXP-02` Acceptance:**
   - Clicking "Download Report (PDF)" on `/student/academic-records` delivers a valid `application/pdf` file.
   - Grade Card PDF features institutional branding, student enrollment details, SGPA, CGPA, and grade table.
   - No `.csv` file is received when clicking the PDF button.
3. **`ISSUE-EXP-03` Acceptance:**
   - Clicking "Download Report (PDF)" on `/student/reports` delivers a valid `application/pdf` file.
   - Browser `window.print()` dialog is completely removed.
   - Attendance percentage and session breakdown are formatted accurately.
4. **`ISSUE-EXP-04` Acceptance:**
   - Class Details modal on `/faculty/classes` contains an active "Export Roster" button.
   - Faculty can download the enrolled student roster in Excel, PDF, or CSV.
5. **Quality & Regression Criteria:**
   - `pytest` passes all 405 existing backend tests plus new export tests with 0 failures.
   - `npm run lint` passes with 0 errors and 0 warnings.
   - `npm run build` succeeds cleanly.
   - Zero database migrations or schema alterations.

---

## 18. Git Working-Tree Preservation Summary

Before and during this planning inspection:
- `git status --short`: Verified all pre-existing user modifications and untracked files are untouched.
- `git branch --show-current`: Confirmed active branch is `feature/frontend-auth-portals`.
- `git diff --stat`: Confirmed no changes to application code, routes, or tests occurred during this audit.
- No files were staged or committed.

---

## 19. Summary & Recommendation

| Issue ID | Feature | Current Flaw | Planned Solution | Complexity |
| :--- | :--- | :--- | :--- | :--- |
| **`ISSUE-EXP-01`** | Faculty Reports | In-memory CSV; Excel/PDF disabled | New `/reports/export` endpoint + openpyxl/reportlab | **Medium** |
| **`ISSUE-EXP-02`** | Student Academic Records | Advertises PDF, returns CSV | Backend PDF generation + frontend Blob handling | **Medium** |
| **`ISSUE-EXP-03`** | Student Subject-wise Report | Advertises PDF, calls `window.print()` | Backend PDF generation; eliminate `window.print()` | **Medium** |
| **`ISSUE-EXP-04`** | Faculty Classes | Advisory promises roster export; no button | New `/courses/<id>/roster/export` + modal export UI | **Low-Medium** |

**Implementation Recommendation:**
Phase 2 is thoroughly planned, risks are mitigated, and existing working trees are preserved. Implementation can proceed immediately upon user approval.
