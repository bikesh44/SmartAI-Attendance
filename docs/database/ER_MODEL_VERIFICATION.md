# ER Model Verification

## Purpose

Verification of the approved ER model against the existing
ER-to-backend model-to-database mapping.

## Entity Mapping

The existing mapping contains the following approved entities:

- ADMIN -> admin.py -> admins
- DEPARTMENT -> department.py -> departments
- PROGRAM -> program.py -> programs
- FACULTY -> faculty.py -> faculties
- SECTION -> section.py -> sections
- SEMESTER -> semester.py -> semesters
- STUDENT -> student.py -> students
- FACE_DATA -> face_data.py -> face_data
- SUBJECT -> subject.py -> subjects
- FACULTY_ASSIGNMENT -> faculty_assignment.py -> faculty_assignments
- ATTENDANCE_SESSION -> attendance_session.py -> attendance_sessions
- ATTENDANCE -> attendance.py -> attendance

## Relationship Verification

The approved ER diagram shows the following key relationships:

- DEPARTMENT -> PROGRAM
- DEPARTMENT -> FACULTY
- PROGRAM -> SEMESTER
- SEMESTER -> SUBJECT
- SECTION -> STUDENT
- STUDENT -> FACE_DATA
- FACULTY -> FACULTY_ASSIGNMENT
- SECTION -> FACULTY_ASSIGNMENT
- SUBJECT -> FACULTY_ASSIGNMENT
- FACULTY_ASSIGNMENT -> ATTENDANCE_SESSION
- ATTENDANCE_SESSION -> ATTENDANCE
- STUDENT -> ATTENDANCE

## Verification Result

Entity-to-model-to-table mapping is consistent with the approved
ER model.

The backend implementation must preserve the approved entities,
foreign-key relationships, and database structure.

No new entities or relationships should be introduced without
team approval.
