# SAMS-FR — Focused Authorization, Biometric API & Audit Evidence Review

**Document Location:** `backend/docs/focused_authorization_biometric_security_review.md`
**Review Date:** October 27, 2026
**Auditor Mode:** Independent Defensive Security & Authorization Review
**Git Branch:** `feature/frontend-auth-portals`
**Runtime:** Python 3.10.11 / Flask 3.1.3 / MySQL 8.0 (`sams_db` @ `localhost:3306`) / React 19.2.8 / Vite 8.2.0

---

## 1. Executive Review & Disproven Assumptions from Initial Audit

An independent, code-level verification of `backend/docs/api_integration_health_security_audit.md` and `backend/docs/complete_backend_api_inventory.md` was conducted. The previous audit report was evaluated against actual source code, route decorators, authentication helpers, and database models.

### Key Corrections to Previous Audit Claims

1. **DISPROVEN: Token Revocation / `TokenBlacklist` Model**
   - *Previous Audit Claim:* Stated that a `TokenBlacklist` model enforces logout revocation.
   - *Independent Code Finding:* **No `TokenBlacklist` model exists in the codebase.** Neither `backend/app/models/` nor `backend/app/routes/auth.py` contains token blocklist logic or `@jwt.token_in_blocklist_loader`. Logout simply executes `unset_jwt_cookies(response)`, clearing client-side cookies. If an issued JWT string is saved, it remains cryptographically valid on the backend until expiry (3 hours for admin, 7 days for others).
   - *Classification:* **Confirmed Architectural Vulnerability (SEC-05 - Medium).**

2. **DISPROVEN: Backend Password Reset & OTP Rate Limiting**
   - *Previous Audit Claim:* Stated that `auth.py` implemented a 6-digit cryptographic OTP password reset flow with rate limiting.
   - *Independent Code Finding:* **No password-reset or OTP verification endpoints exist in `backend/app/routes/auth.py` or anywhere in the backend.** Frontend components `frontend/src/pages/auth/ForgotPassword.jsx` (lines 72-75) and `frontend/src/pages/auth/VerifyOtp.jsx` (lines 109-121) explicitly contain comments: *"Backend password-reset API is not implemented yet. This is temporary frontend behavior."*
   - *Classification:* **Corrected Audit Finding / Unimplemented Feature (SEC-06 - Info).**

3. **CORRECTED: Mislabeled Route Roles in Inventory**
   - *Previous Inventory Labeling:* Mislabeled `/api/face/enroll`, `/api/face/<id>`, `/api/face/status/<id>` as `Public`, and `/api/faculty/change-password` as `ADMIN`.
   - *Root Cause:* The automated inspection script in `scratch/inventory_backend_routes.py` failed to unwrap parameterized decorators `@role_required(...)` and substring-matched `"admin"` inside `@faculty_or_admin_required`.
   - *Actual Implementation:* All face endpoints are protected by JWT and role requirements (`@role_required("ADMIN", "STUDENT")`, `@role_required("ADMIN")`, `@role_required("ADMIN", "FACULTY", "STUDENT")`).

4. **CONFIRMED & FIXED: Broken Object Level Authorization (BOLA/IDOR) on Face Status**
   - *Vulnerability:* While `POST /api/face/enroll` enforced that callers with role `STUDENT` could only enroll their own face, `GET /api/face/status/<student_id>` failed to enforce identity ownership for students. Student A could query Student B's face registration status and model version.
   - *Remediation:* Fixed in `backend/app/routes/face.py` and validated with dedicated regression tests.

---

## 2. Phase 1 — Public & Protected Face APIs Inspection

All facial recognition and biometric endpoints across `face_bp`, `face_profile_bp`, `admin_bp`, and `recognition_bp` were inspected:

| Endpoint | HTTP Method | Route Decorator | Server Role Check | Student Identity Derivation | Cross-Student Access Control | Replay & Liveness Protection |
|:---|:---:|:---|:---:|:---|:---|:---:|
| `/api/face/enroll` | `POST` | `@role_required("ADMIN", "STUDENT")` | Yes | If `STUDENT`, verified via `Student.user_id == get_jwt_identity()` | **Strict:** Student cannot enroll another student (HTTP 403). `check_face_cross_student_conflict()` prevents duplicate face theft. | High quality / single face checked |
| `/api/face/status/<id>` | `GET` | `@role_required("ADMIN", "FACULTY", "STUDENT")` | Yes | If `STUDENT`, verified via `current_student.student_id == student_id` | **Strict (Remediated):** Student A receives HTTP 403 if querying Student B. | Read-only status |
| `/api/face/<id>` & `/api/face/student/<id>` | `DELETE` | `@role_required("ADMIN")` | Yes | N/A (Admin only) | **Strict:** Students & Faculty receive HTTP 403. Admin can safely deactivate or remove. | Audit logged via `record_activity` |
| `/api/student/face-profile` | `GET` | `@student_required` | Yes | Derived strictly from JWT `get_current_student()` | **Strict:** Always queries caller's profile. No ID parameter accepted. | N/A |
| `/api/student/face-profile` | `POST` | `@student_required` | Yes | Derived strictly from JWT `get_current_student()` | **Strict:** Always associates new profile with authenticated caller. | Requires 512-dim embedding |
| `/api/student/face-profile` | `DELETE` | `@student_required` | Yes | Derived strictly from JWT `get_current_student()` | **Strict:** Deactivates only authenticated caller's profile. | Sets `is_active=False` |
| `/api/admin/face-profiles` | `GET` | `@admin_required` | Yes | Admin only | **Strict:** Faculty and students receive HTTP 403. | Embeddings not returned in response |
| `/api/admin/students/<id>/face` | `DELETE` | `@admin_required` | Yes | Admin only | **Strict:** Faculty and students receive HTTP 403. | Controlled administrative removal |
| `/api/faculty/recognition/liveness/challenge` | `POST` | `@faculty_required` | Yes | Derived from JWT `get_current_faculty()` | **Strict:** Bound to `session_id` and `faculty_id`. Caller must own or be substitute for session. | Cryptographic nonce + 35s TTL |
| `/api/faculty/recognition/liveness/verify` | `POST` | `@faculty_required` | Yes | Derived from JWT `get_current_faculty()` | **Strict:** Checks `challenge["session_id"] == session.session_id` & `challenge["faculty_id"] == faculty.faculty_id`. | Multi-cue PAD + motion + frontality |
| `/api/faculty/recognition/attendance` | `POST` | `@faculty_required` | Yes | Verified via token `student_id` | **Strict:** Bound to `session_id`, `faculty_id`, `student_id`. | Single-use token consumed atomically under lock |

---

## 3. Phase 2 — Portal Authorization & Cross-Resource Verification

### Portal Role Boundaries
- **Admin Portal (`/api/admin/*`):** Protected by `@admin_required`. Attempts by faculty or students consistently return HTTP 403 Forbidden.
- **Faculty Portal (`/api/faculty/*`):** Protected by `@faculty_required` or `@faculty_or_admin_required`.
  - `/api/faculty/dashboard` & `/api/faculty/profile`: Scoped strictly to `get_current_faculty()` (authenticated user).
  - `/api/faculty/courses`: Filters by `CourseOffering.faculty_id == faculty.faculty_id`. Cross-faculty viewing is blocked.
  - `/api/faculty/attendance/sessions`: Checks `offering.faculty_id == faculty.faculty_id` or approved substitute adjustment in `FacultyAdjustment`. Cross-faculty session start is blocked (HTTP 403).
  - `/api/faculty/attendance/sessions/<id>/close`: Verifies `session.faculty_id == faculty.faculty_id`. Cross-faculty closing is blocked (HTTP 403).
  - `/api/faculty/attendance/sessions/<id>/records`: Verifies `session.faculty_id == faculty.faculty_id`. Cross-faculty record reading is blocked (HTTP 403).
- **Student Portal (`/api/student/*`):** Protected by `@student_required` or `@student_or_admin_required`.
  - `/api/student/dashboard`: Scoped strictly to `get_current_student()`.
  - `/api/student/attendance/`: Scoped strictly to `student.student_id`. No query parameter can alter student identity.
  - `/api/student/attendance/summary`: Scoped strictly to caller's active enrollments.
- **Timetable Routes (`/api/timetable/*`):**
  - `/api/timetable/faculty`: `@faculty_required`. Filters by `offering.faculty_id == faculty.faculty_id` plus approved substitute adjustments.
  - `/api/timetable/student`: `@student_required`. Filters by active enrollments of caller.

### Intentional Administrative Behavior: Manual Attendance Override
- In `backend/app/routes/attendance.py`, `POST /sessions/<id>/records` and `PATCH /sessions/<id>/records/<student_id>` are decorated with `@faculty_or_admin_required`, but contain explicit code:
  ```python
  if user_role == "FACULTY":
      return jsonify({
          "success": False,
          "message": "Manual attendance marking by faculty is disabled. Attendance must be recorded via face recognition.",
      }), 403
  ```
- **Conclusion:** These endpoints are intentionally restricted to `ADMIN` only. The design choice mandates face recognition for faculty workflows while reserving manual overrides for administrators.

---

## 4. Phase 3 & 4 — Test Execution Evidence & Coverage Matrix

### Automated Test Suites Executed

1. **Focused Authorization & Biometric Regression Suite (`tests/test_focused_authorization_biometrics.py`):**
   - `test_missing_and_malformed_jwt`: PASSED
   - `test_expired_jwt`: PASSED
   - `test_role_boundaries_admin_faculty_student`: PASSED
   - `test_cross_student_face_profile_isolation`: PASSED
   - `test_cross_student_attendance_isolation`: PASSED
   - `test_cross_faculty_attendance_isolation`: PASSED
   - `test_biometric_deletion_authorization`: PASSED
   - `test_liveness_challenge_lifecycle_binding_and_replay`: PASSED
   - `test_faculty_manual_attendance_disabled`: PASSED
   - `test_logout_unsets_cookies`: PASSED
   - `test_invalid_identifiers_and_malformed_payloads`: PASSED
   - **Result: 11 passed out of 11 in 8.16s.**

2. **Comprehensive API & Security Test Suite (`tests/test_api_endpoints_comprehensive.py`):**
   - **Result: 22 passed out of 22 in 16.25s.**

3. **Complete Backend Regression Suite (`tests/`):**
   - **Command:** `python -m pytest tests/`
   - **Result: 335 passed out of 335 in 47.31s (100% pass rate across all 34 test modules).**

4. **Biometric Anti-Spoofing & Liveness Benchmark (`evaluate_liveness.py`):**
   - Passive PAD trials (80): 80/80 passed (0% APCER, 0% BPCER).
   - Active Challenge trials (40): 40/40 passed.
   - Overall Accuracy: 100.0%.

5. **Frontend Quality & Build Verification:**
   - `npm run lint`: 0 errors, 0 warnings.
   - `npm run build`: 86 assets compiled cleanly in 2.38s.

---

## 5. Phase 5 — Other Security Controls Review

| Control | Status | Evidence | Code Location |
|:---|:---:|:---|:---|
| **Password Hashing** | Enabled | Bcrypt with 12 salt rounds | `backend/app/services/auth_service.py:12` |
| **JWT Storage & Transmission** | Enabled | HTTPOnly, SameSite=Lax cookies | `backend/app/config.py:19-22`, `auth.py:82` |
| **JWT Signing Secret** | Enabled | Loaded from environment variable `JWT_SECRET_KEY` | `backend/app/config.py:23` |
| **Token Expiration** | Enabled | 3 hours for ADMIN; 7 days for FACULTY/STUDENT | `backend/app/routes/auth.py:63`, `config.py:24` |
| **Token Server Revocation** | Missing | No blacklist model or blocklist callback | Documented as SEC-05 |
| **Password Reset / OTP** | Not Implemented | Frontend stubs exist; backend route not created | Documented as SEC-06 |
| **CORS Origins** | Enabled | Configured via `CORS_ORIGINS` with `supports_credentials=True` | `backend/app/__init__.py:49` |
| **Upload Security** | Partial | Extension check (`ALLOWED_EXTENSIONS`), 50 KB max, `secure_filename`. Unauthenticated static serve. | `backend/app/routes/student.py:40, 767` |
| **SQL Injection** | Defended | 100% SQLAlchemy ORM / bound parameters | Entire codebase |
| **CSV Formula Injection** | Defended | `_sanitize_csv_cell()` prepends `'` to formula triggers | `backend/app/routes/admin_attendance.py:703` |
| **Security Headers** | Defended | `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` | `backend/app/__init__.py:56` |
| **Biometric Privacy** | Defended | Binary BLOB storage, never exposed in JSON API responses | `FaceProfile.embedding` |

---

## 6. Phase 6 — Confirmed Findings & Safe Remediation Log

| Finding ID | Severity | Description & Evidence | Remediation Action | Status |
|:---:|:---:|:---|:---|:---:|
| **SEC-01** | Medium | **CWE-209:** Internal database exception string returned in `/api/db-health`. | Logged error server-side; returned generic message. | **Fixed & Tested** |
| **SEC-02** | Low | **CWE-693:** Missing defensive security headers (`X-Frame-Options`, `X-Content-Type-Options`). | Added `@app.after_request` handler in `create_app()`. | **Fixed & Tested** |
| **SEC-03** | Low | **CWE-1236:** CSV formula injection in attendance report export. | Added `_sanitize_csv_cell()` neutralizing `=`, `+`, `-`, `@`. | **Fixed & Tested** |
| **SEC-04** | Medium | **CWE-284/CWE-639:** BOLA on `GET /api/face/status/<student_id>`. Student A could inspect Student B's registration status. | Added student identity ownership check `current_student.student_id == student_id`. | **Fixed & Tested** |
| **SEC-05** | Medium | **CWE-613:** Stateless JWT logout (no database blocklist). Token remains valid if captured. | Documented architectural constraint; recommended Redis token blocklist. | **Documented** |
| **SEC-06** | Info | **CWE-1059:** Previous audit claimed OTP password reset existed; backend is unimplemented. | Documented actual implementation state. | **Documented** |
| **SEC-07** | Low | **CWE-200:** Unauthenticated student photo/signature static serving on `/api/student/uploads/...`. | Protected by random filename & `secure_filename`; auth decorator recommended for production. | **Documented** |
| **SEC-08** | Low | **CWE-614:** `JWT_COOKIE_SECURE = False` in dev configuration. | Must be set to `True` when served over HTTPS. | **Documented** |
| **SEC-09** | Info | **CWE-1104:** High severity npm audit advisories for `axios` and `vite`. | Browser React SPA mitigates Node adapter risks; scheduled for package maintenance. | **Documented** |

---

## 7. Final Git Working-Tree Verification

```text
On branch feature/frontend-auth-portals
Your branch is up to date with 'origin/feature/frontend-auth-portals'.

Changes not staged for commit:
  (use "git add <file>..." to update what will be committed)
  (use "git restore <file>..." to discard changes in working directory)
	modified:   backend/app/__init__.py
	modified:   backend/app/routes/__init__.py
	modified:   backend/app/routes/admin_attendance.py
	modified:   backend/app/routes/face.py
	modified:   backend/docs/complete_backend_api_inventory.md

Untracked files:
  (use "git add <file>..." to include in what will be committed)
	backend/docs/api_integration_health_security_audit.md
	backend/docs/focused_authorization_biometric_security_review.md
	backend/tests/test_api_endpoints_comprehensive.py
	backend/tests/test_focused_authorization_biometrics.py
```

*Zero destructive Git operations were executed. No changes were staged, committed, stashed, or pushed. All existing workspace files and user modifications are strictly preserved.*
