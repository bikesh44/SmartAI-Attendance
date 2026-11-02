# SAMS-FR — Authoritative Backend API Endpoint Inventory

**Generated:** October 27, 2026
**Total Registered Endpoints:** 125

This document provides an exhaustive, authoritative inventory of all 125 registered route/method combinations across all 17 Flask application blueprints.

## Blueprint: `admin` (51 endpoints)

| HTTP Method | Route URL | Handler Function | Role / Auth | Source Location |
|:---:|:---|:---|:---:|:---|
| `GET` | `/api/admin/academic-session` | `get_academic_session_config` | `ADMIN` | `app\routes\admin.py:251` |
| `POST` | `/api/admin/academic-session` | `update_academic_session_config` | `ADMIN` | `app\routes\admin.py:263` |
| `PUT` | `/api/admin/academic-session` | `update_academic_session_config` | `ADMIN` | `app\routes\admin.py:263` |
| `GET` | `/api/admin/academic/summary` | `get_academic_summary` | `ADMIN` | `app\routes\admin.py:2588` |
| `GET` | `/api/admin/activity` | `get_activity_logs` | `ADMIN` | `app\routes\admin.py:132` |
| `GET` | `/api/admin/activity/recent` | `get_recent_activity` | `ADMIN` | `app\routes\admin.py:108` |
| `GET` | `/api/admin/batches` | `get_batches` | `ADMIN` | `app\routes\admin.py:179` |
| `POST` | `/api/admin/batches` | `create_batch` | `ADMIN` | `app\routes\admin.py:198` |
| `POST` | `/api/admin/change-password` | `change_admin_password` | `ADMIN` | `app\routes\admin.py:487` |
| `GET` | `/api/admin/course-offerings` | `get_course_offerings` | `ADMIN` | `app\routes\admin.py:3052` |
| `POST` | `/api/admin/course-offerings` | `create_course_offering` | `ADMIN` | `app\routes\admin.py:3139` |
| `DELETE` | `/api/admin/course-offerings/<int:offering_id>` | `delete_course_offering` | `ADMIN` | `app\routes\admin.py:3379` |
| `PATCH` | `/api/admin/course-offerings/<int:offering_id>` | `update_course_offering` | `ADMIN` | `app\routes\admin.py:3249` |
| `PUT` | `/api/admin/course-offerings/<int:offering_id>` | `update_course_offering` | `ADMIN` | `app\routes\admin.py:3249` |
| `GET` | `/api/admin/courses` | `get_courses` | `ADMIN` | `app\routes\admin.py:2610` |
| `POST` | `/api/admin/courses` | `create_course` | `ADMIN` | `app\routes\admin.py:2668` |
| `DELETE` | `/api/admin/courses/<int:course_id>` | `delete_course` | `ADMIN` | `app\routes\admin.py:2997` |
| `GET` | `/api/admin/courses/<int:course_id>` | `get_course` | `ADMIN` | `app\routes\admin.py:2640` |
| `PATCH` | `/api/admin/courses/<int:course_id>` | `update_course` | `ADMIN` | `app\routes\admin.py:2818` |
| `GET` | `/api/admin/dashboard` | `get_admin_dashboard` | `ADMIN` | `app\routes\admin.py:64` |
| `GET` | `/api/admin/departments` | `get_departments` | `ADMIN` | `app\routes\admin.py:547` |
| `POST` | `/api/admin/departments` | `create_department` | `ADMIN` | `app\routes\admin.py:611` |
| `DELETE` | `/api/admin/departments/<int:department_id>` | `delete_department` | `ADMIN` | `app\routes\admin.py:863` |
| `PATCH` | `/api/admin/departments/<int:department_id>` | `update_department` | `ADMIN` | `app\routes\admin.py:695` |
| `POST` | `/api/admin/face-profiles/cleanup-obsolete` | `cleanup_obsolete_profiles_route` | `ADMIN` | `app\routes\admin.py:2492` |
| `GET` | `/api/admin/faculty` | `get_faculty` | `ADMIN` | `app\routes\admin.py:3538` |
| `POST` | `/api/admin/faculty` | `create_faculty` | `ADMIN` | `app\routes\admin.py:3718` |
| `DELETE` | `/api/admin/faculty/<int:faculty_id>` | `delete_faculty` | `ADMIN` | `app\routes\admin.py:4087` |
| `GET` | `/api/admin/faculty/<int:faculty_id>` | `get_faculty_by_id` | `ADMIN` | `app\routes\admin.py:3598` |
| `PATCH` | `/api/admin/faculty/<int:faculty_id>` | `update_faculty` | `ADMIN` | `app\routes\admin.py:3911` |
| `GET` | `/api/admin/faculty/filter-options` | `get_faculty_filter_options` | `ADMIN` | `app\routes\admin.py:3494` |
| `GET` | `/api/admin/faculty/summary` | `get_faculty_summary` | `ADMIN` | `app\routes\admin.py:3435` |
| `GET` | `/api/admin/profile` | `get_admin_profile` | `ADMIN` | `app\routes\admin.py:317` |
| `PATCH` | `/api/admin/profile` | `update_admin_profile` | `ADMIN` | `app\routes\admin.py:342` |
| `GET` | `/api/admin/students` | `get_students` | `ADMIN` | `app\routes\admin.py:1734` |
| `POST` | `/api/admin/students` | `create_student` | `ADMIN` | `app\routes\admin.py:1831` |
| `DELETE` | `/api/admin/students/<int:student_id>` | `delete_student` | `ADMIN` | `app\routes\admin.py:2347` |
| `GET` | `/api/admin/students/<int:student_id>` | `get_student` | `ADMIN` | `app\routes\admin.py:1808` |
| `PATCH` | `/api/admin/students/<int:student_id>` | `update_student` | `ADMIN` | `app\routes\admin.py:2100` |
| `DELETE` | `/api/admin/students/<int:student_id>/face` | `remove_student_face_registration` | `ADMIN` | `app\routes\admin.py:2535` |
| `DELETE` | `/api/admin/students/<int:student_id>/face-profile` | `remove_student_face_registration` | `ADMIN` | `app\routes\admin.py:2535` |
| `GET` | `/api/admin/students/duplicates` | `get_suspected_duplicate_students` | `ADMIN` | `app\routes\admin.py:2422` |
| `GET` | `/api/admin/students/filter-options` | `get_students_filter_options` | `ADMIN` | `app\routes\admin.py:1684` |
| `POST` | `/api/admin/students/reconcile-duplicates` | `reconcile_duplicate_students_route` | `ADMIN` | `app\routes\admin.py:2439` |
| `GET` | `/api/admin/students/summary` | `get_students_summary` | `ADMIN` | `app\routes\admin.py:1635` |
| `GET` | `/api/admin/users` | `get_users` | `ADMIN` | `app\routes\admin.py:923` |
| `POST` | `/api/admin/users` | `create_admin_user` | `ADMIN` | `app\routes\admin.py:963` |
| `DELETE` | `/api/admin/users/<int:user_id>` | `delete_user` | `ADMIN` | `app\routes\admin.py:1233` |
| `GET` | `/api/admin/users/<int:user_id>` | `get_user` | `ADMIN` | `app\routes\admin.py:1025` |
| `PATCH` | `/api/admin/users/<int:user_id>` | `update_user` | `ADMIN` | `app\routes\admin.py:1065` |
| `PATCH` | `/api/admin/users/<int:user_id>/reactivate` | `reactivate_user` | `ADMIN` | `app\routes\admin.py:1368` |

## Blueprint: `admin_analytics` (1 endpoints)

| HTTP Method | Route URL | Handler Function | Role / Auth | Source Location |
|:---:|:---|:---|:---:|:---|
| `GET` | `/api/admin/attendance/analytics` | `get_admin_attendance_analytics` | `ADMIN` | `app\routes\admin_analytics.py:23` |

## Blueprint: `admin_attendance` (8 endpoints)

| HTTP Method | Route URL | Handler Function | Role / Auth | Source Location |
|:---:|:---|:---|:---:|:---|
| `GET` | `/api/admin/attendance/dashboard` | `get_attendance_dashboard` | `ADMIN` | `app\routes\admin_attendance.py:261` |
| `GET` | `/api/admin/attendance/export` | `export_attendance_records` | `ADMIN` | `app\routes\admin_attendance.py:706` |
| `GET` | `/api/admin/attendance/filter-options` | `get_attendance_filter_options` | `ADMIN` | `app\routes\admin_attendance.py:144` |
| `GET` | `/api/admin/attendance/records` | `get_admin_attendance_records_list` | `ADMIN` | `app\routes\admin_attendance.py:479` |
| `GET` | `/api/admin/attendance/records/<int:attendance_id>` | `get_single_attendance_record` | `ADMIN` | `app\routes\admin_attendance.py:616` |
| `GET` | `/api/admin/attendance/sessions` | `get_attendance_sessions` | `ADMIN` | `app\routes\admin_attendance.py:819` |
| `GET` | `/api/admin/attendance/sessions/<int:session_id>` | `get_attendance_session` | `ADMIN` | `app\routes\admin_attendance.py:919` |
| `GET` | `/api/admin/attendance/sessions/<int:session_id>/records` | `get_attendance_records` | `ADMIN` | `app\routes\admin_attendance.py:957` |

## Blueprint: `analytics` (1 endpoints)

| HTTP Method | Route URL | Handler Function | Role / Auth | Source Location |
|:---:|:---|:---|:---:|:---|
| `GET` | `/api/faculty/attendance/analytics` | `get_attendance_analytics` | `FACULTY` | `app\routes\analytics.py:41` |

## Blueprint: `attendance` (8 endpoints)

| HTTP Method | Route URL | Handler Function | Role / Auth | Source Location |
|:---:|:---|:---|:---:|:---|
| `GET` | `/api/faculty/attendance/overview` | `get_attendance_overview` | `FACULTY` | `app\routes\attendance.py:441` |
| `GET` | `/api/faculty/attendance/sessions` | `get_attendance_sessions` | `FACULTY` | `app\routes\attendance.py:386` |
| `POST` | `/api/faculty/attendance/sessions` | `start_attendance_session` | `FACULTY` | `app\routes\attendance.py:167` |
| `POST` | `/api/faculty/attendance/sessions/<int:session_id>/close` | `close_attendance_session` | `FACULTY` | `app\routes\attendance.py:632` |
| `GET` | `/api/faculty/attendance/sessions/<int:session_id>/records` | `get_session_attendance` | `FACULTY` | `app\routes\attendance.py:950` |
| `POST` | `/api/faculty/attendance/sessions/<int:session_id>/records` | `mark_attendance` | `ADMIN` | `app\routes\attendance.py:714` |
| `PATCH` | `/api/faculty/attendance/sessions/<int:session_id>/records/<int:student_id>` | `update_attendance_record` | `ADMIN` | `app\routes\attendance.py:869` |
| `GET` | `/api/faculty/attendance/sessions/active` | `get_active_attendance_session` | `FACULTY` | `app\routes\attendance.py:572` |

## Blueprint: `auth` (5 endpoints)

| HTTP Method | Route URL | Handler Function | Role / Auth | Source Location |
|:---:|:---|:---|:---:|:---|
| `GET` | `/api/auth/admin-test` | `admin_test` | `ADMIN` | `app\routes\auth.py:123` |
| `POST` | `/api/auth/login` | `login` | `Public` | `app\routes\auth.py:25` |
| `POST` | `/api/auth/logout` | `logout` | `Public` | `app\routes\auth.py:85` |
| `GET` | `/api/auth/me` | `me` | `Authenticated` | `app\routes\auth.py:99` |
| `GET` | `/api/auth/protected-test` | `protected_test` | `Authenticated` | `app\routes\auth.py:132` |

## Blueprint: `enrollment` (5 endpoints)

| HTTP Method | Route URL | Handler Function | Role / Auth | Source Location |
|:---:|:---|:---|:---:|:---|
| `GET` | `/api/admin/enrollments` | `get_enrollments` | `ADMIN` | `app\routes\enrollment.py:269` |
| `DELETE` | `/api/admin/enrollments/<int:enrollment_id>` | `delete_enrollment` | `ADMIN` | `app\routes\enrollment.py:512` |
| `POST` | `/api/admin/enrollments/group-bulk` | `bulk_enroll_group` | `ADMIN` | `app\routes\enrollment.py:725` |
| `POST` | `/api/admin/enrollments/group-preview` | `preview_group_enrollment` | `ADMIN` | `app\routes\enrollment.py:549` |
| `GET` | `/api/admin/enrollments/summary` | `get_enrollments_summary` | `ADMIN` | `app\routes\enrollment.py:377` |

## Blueprint: `face` (4 endpoints)

| HTTP Method | Route URL | Handler Function | Role / Auth | Source Location |
|:---:|:---|:---|:---:|:---|
| `DELETE` | `/api/face/<int:student_id>` | `remove_student_face_biometric` | `ADMIN` | `app\routes\face.py:225` |
| `POST` | `/api/face/enroll` | `enroll_face` | `ADMIN, STUDENT` | `app\routes\face.py:64` |
| `GET` | `/api/face/status/<int:student_id>` | `face_registration_status` | `ADMIN, FACULTY, STUDENT` | `app\routes\face.py:186` |
| `DELETE` | `/api/face/student/<int:student_id>` | `remove_student_face_biometric` | `ADMIN` | `app\routes\face.py:225` |

## Blueprint: `face_profile` (4 endpoints)

| HTTP Method | Route URL | Handler Function | Role / Auth | Source Location |
|:---:|:---|:---|:---:|:---|
| `GET` | `/api/admin/face-profiles` | `get_face_profiles` | `ADMIN` | `app\routes\face_profile.py:199` |
| `DELETE` | `/api/student/face-profile` | `deactivate_my_face_profile` | `STUDENT` | `app\routes\face_profile.py:167` |
| `GET` | `/api/student/face-profile` | `get_my_face_profile` | `STUDENT` | `app\routes\face_profile.py:132` |
| `POST` | `/api/student/face-profile` | `create_face_profile` | `STUDENT` | `app\routes\face_profile.py:24` |

## Blueprint: `faculty` (8 endpoints)

| HTTP Method | Route URL | Handler Function | Role / Auth | Source Location |
|:---:|:---|:---|:---:|:---|
| `POST` | `/api/faculty/change-password` | `change_faculty_password` | `ADMIN` | `app\routes\faculty.py:330` |
| `GET` | `/api/faculty/classes/summary` | `get_faculty_classes_summary` | `FACULTY` | `app\routes\faculty.py:382` |
| `GET` | `/api/faculty/courses` | `get_faculty_courses` | `FACULTY` | `app\routes\faculty.py:571` |
| `GET` | `/api/faculty/courses/<int:course_id>` | `get_faculty_course` | `FACULTY` | `app\routes\faculty.py:743` |
| `GET` | `/api/faculty/dashboard` | `faculty_dashboard` | `ADMIN` | `app\routes\faculty.py:78` |
| `GET` | `/api/faculty/profile` | `get_faculty_profile` | `ADMIN` | `app\routes\faculty.py:202` |
| `PATCH` | `/api/faculty/profile` | `update_faculty_profile` | `ADMIN` | `app\routes\faculty.py:223` |
| `GET` | `/api/faculty/students` | `get_faculty_students` | `FACULTY` | `app\routes\faculty.py:840` |

## Blueprint: `health` (2 endpoints)

| HTTP Method | Route URL | Handler Function | Role / Auth | Source Location |
|:---:|:---|:---|:---:|:---|
| `GET` | `/api/db-health` | `db_health` | `Public` | `app\routes\__init__.py:12` |
| `GET` | `/api/health` | `health` | `Public` | `app\routes\__init__.py:7` |

## Blueprint: `recognition` (3 endpoints)

| HTTP Method | Route URL | Handler Function | Role / Auth | Source Location |
|:---:|:---|:---|:---:|:---|
| `POST` | `/api/faculty/recognition/attendance` | `process_recognition_attendance` | `FACULTY` | `app\routes\recognition.py:528` |
| `POST` | `/api/faculty/recognition/liveness/challenge` | `create_liveness_challenge` | `FACULTY` | `app\routes\recognition.py:78` |
| `POST` | `/api/faculty/recognition/liveness/verify` | `verify_liveness_evidence` | `FACULTY` | `app\routes\recognition.py:180` |

## Blueprint: `reports` (1 endpoints)

| HTTP Method | Route URL | Handler Function | Role / Auth | Source Location |
|:---:|:---|:---|:---:|:---|
| `GET` | `/api/faculty/attendance/reports` | `get_attendance_report` | `FACULTY` | `app\routes\reports.py:33` |

## Blueprint: `student` (8 endpoints)

| HTTP Method | Route URL | Handler Function | Role / Auth | Source Location |
|:---:|:---|:---|:---:|:---|
| `POST` | `/api/student/change-password` | `change_student_password` | `ADMIN` | `app\routes\student.py:785` |
| `GET` | `/api/student/courses` | `get_student_courses` | `ADMIN` | `app\routes\student.py:838` |
| `GET` | `/api/student/dashboard` | `student_dashboard` | `ADMIN` | `app\routes\student.py:137` |
| `GET` | `/api/student/profile` | `get_student_profile` | `ADMIN` | `app\routes\student.py:461` |
| `PATCH` | `/api/student/profile` | `update_student_profile` | `ADMIN` | `app\routes\student.py:482` |
| `POST` | `/api/student/upload-photo` | `upload_student_photo` | `ADMIN` | `app\routes\student.py:575` |
| `POST` | `/api/student/upload-signature` | `upload_student_signature` | `ADMIN` | `app\routes\student.py:677` |
| `GET` | `/api/student/uploads/<folder>/<filename>` | `serve_student_upload` | `Public` | `app\routes\student.py:767` |

## Blueprint: `student_attendance` (3 endpoints)

| HTTP Method | Route URL | Handler Function | Role / Auth | Source Location |
|:---:|:---|:---|:---:|:---|
| `GET` | `/api/student/attendance/` | `get_my_attendance` | `STUDENT` | `app\routes\student_attendance.py:212` |
| `GET` | `/api/student/attendance/report` | `get_my_attendance` | `STUDENT` | `app\routes\student_attendance.py:212` |
| `GET` | `/api/student/attendance/summary` | `get_attendance_summary` | `STUDENT` | `app\routes\student_attendance.py:278` |

## Blueprint: `timetable` (8 endpoints)

| HTTP Method | Route URL | Handler Function | Role / Auth | Source Location |
|:---:|:---|:---|:---:|:---|
| `PATCH` | `/api/timetable/<int:entry_id>` | `update_timetable_entry` | `ADMIN` | `app\routes\timetable.py:469` |
| `PUT` | `/api/timetable/<int:entry_id>` | `update_timetable_entry` | `ADMIN` | `app\routes\timetable.py:469` |
| `GET` | `/api/timetable/adjustments` | `get_faculty_adjustments` | `ADMIN` | `app\routes\timetable.py:293` |
| `POST` | `/api/timetable/adjustments` | `create_faculty_adjustment` | `ADMIN` | `app\routes\timetable.py:318` |
| `POST` | `/api/timetable/adjustments/<int:adjustment_id>/cancel` | `cancel_faculty_adjustment` | `ADMIN` | `app\routes\timetable.py:449` |
| `GET` | `/api/timetable/admin` | `get_admin_timetable` | `ADMIN` | `app\routes\timetable.py:119` |
| `GET` | `/api/timetable/faculty` | `get_faculty_timetable` | `FACULTY` | `app\routes\timetable.py:139` |
| `GET` | `/api/timetable/student` | `get_student_timetable` | `STUDENT` | `app\routes\timetable.py:197` |

## Blueprint: `timetable_import` (5 endpoints)

| HTTP Method | Route URL | Handler Function | Role / Auth | Source Location |
|:---:|:---|:---|:---:|:---|
| `GET` | `/api/timetable/import/academic-years` | `get_available_academic_years` | `ADMIN` | `app\routes\timetable_import.py:617` |
| `POST` | `/api/timetable/import/analyze` | `analyze_timetable_import` | `ADMIN` | `app\routes\timetable_import.py:740` |
| `POST` | `/api/timetable/import/commit` | `commit_timetable_import` | `ADMIN` | `app\routes\timetable_import.py:1158` |
| `POST` | `/api/timetable/import/preview` | `preview_timetable_import` | `ADMIN` | `app\routes\timetable_import.py:669` |
| `POST` | `/api/timetable/import/sheets` | `get_workbook_sheets` | `ADMIN` | `app\routes\timetable_import.py:634` |
