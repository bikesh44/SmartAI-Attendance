# ER → Backend Model → Database Table Mapping

| ER Entity | Backend Model | Database Table |
|-----------|---------------|----------------|
| ADMIN     | admin.py      | admins         |
| DEPARTMENT| department.py | departments |
| PROGRAM | program.py | programs |
| FACULTY | faculty.py | faculties |
| SECTION | section.py | sections |
| SEMESTER | semester.py | semesters |
| STUDENT | student.py | students |
| FACE_DATA | face_data.py | face_data |
| SUBJECT | subject.py | subjects |
| FACULTY_ASSIGNMENT | faculty_assignment.py | faculty_assignments |
| ATTENDANCE_SESSION | attendance_session.py | attendance_sessions |
| ATTENDANCE | attendance.py | attendance |

## Database

Database: MySQL 8.0.45

Database name: sams_fr

Status: Local database created and connectivity verified.

## Important

The backend models and database tables must follow the approved ER diagram.
No new entities or relationships should be introduced without team approval.