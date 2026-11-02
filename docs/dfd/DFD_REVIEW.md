# DFD Level 1 Review

## Processes

1.0 Authentication
2.0 User & Academic Management
3.0 Face Recognition & Attendance
4.0 Attendance Management
5.0 Report Generation

## External Users

- Administrator
- Faculty Member
- Student

## Data Stores

- D1 — Student Database
- D2 — Faculty Database
- D3 — Subject Database
- D4 — Face Data
- D5 — Attendance Database
- D6 — Department/Program/Section DB

## Required Flow Review

| Flow | Status | Observation |
|---|---|---|
| Authentication | Present | Explicitly represented by 1.0 Authentication |
| Student Registration | Partially represented | Student Database and User & Academic Management are present |
| Face Registration | Not explicitly represented | Face Data store exists, but no explicit Face Registration process is shown |
| Face Recognition | Present | Explicitly represented by 3.0 Face Recognition & Attendance |
| Attendance | Present | Attendance is represented by processes 3.0 and 4.0 |
| Reports | Present | Explicitly represented by 5.0 Report Generation |

## Review Conclusion

The DFD contains the main authentication, academic management,
face recognition, attendance, and reporting components.

Student Registration and Face Registration are not explicitly named
as separate processes in the provided DFD. This is recorded as a
review observation and is not changed during the foundation phase.