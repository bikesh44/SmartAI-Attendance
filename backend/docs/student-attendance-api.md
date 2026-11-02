# Student Attendance API Documentation



## 1. Authentication



All endpoints require a valid JWT access token belonging to a user with the `STUDENT` role.



Header:



`Authorization: Bearer <access_token>`



The API resolves the student profile from the authenticated user's ID. A student cannot retrieve another student's attendance by supplying a different student ID.



## 2. Attendance History



**Endpoint:** `GET /api/student/attendance/`



Returns attendance records belonging to the authenticated student, ordered by session date and attendance record time.



### Query parameters



| Parameter | Type | Description |

|---|---|---|

| `course_id` | Integer | Filter by course |

| `offering_id` | Integer | Filter by course offering |

| `date_from` | YYYY-MM-DD | Include sessions on or after this date |

| `date_to` | YYYY-MM-DD | Include sessions on or before this date |

| `status` | String | `PRESENT`, `ABSENT`, or `LATE` |

| `page` | Integer | Page number; defaults to 1 |

| `per_page` | Integer | Records per page; defaults to 20; maximum 100 |



### Example request



`GET /api/student/attendance/?page=1&per_page=20&status=PRESENT`



### Example successful response



```json

{

  "success": true,

  "page": 1,

  "per_page": 20,

  "total_records": 1,

  "total_pages": 1,

  "data": \[

    {

      "attendance_id": 12,

      "session_id": 7,

      "course_id": 3,

      "offering_id": 5,

      "course_code": "CSE301",

      "course_name": "Database Systems",

      "section": "A",

      "session_date": "2026-10-07",

      "status": "PRESENT",

      "marked_at": "2026-10-07T09:15:00",

      "recognition_method": "FACE"

    }

  ]

}

```



Example IDs and timestamps are illustrative.



## 3. Attendance Report



**Endpoint:** `GET /api/student/attendance/report`



Uses the same filters, pagination, authentication, and response structure as the attendance history endpoint.



Example:



`GET /api/student/attendance/report?date_from=2026-10-01&date_to=2026-10-31&page=1&per_page=20`



## 4. Attendance Summary



**Endpoint:** `GET /api/student/attendance/summary`



Returns attendance statistics for the authenticated student's active course enrollments.



The summary counts closed attendance sessions. A closed session without a corresponding student attendance record is counted as absent. Active sessions are excluded.



### Example successful response



```json

{

  "success": true,

  "overall": {

    "total_sessions": 10,

    "present_sessions": 8,

    "absent_sessions": 2,

    "attendance_percentage": 80.0

  },

  "data": \[

    {

      "offering_id": 5,

      "course_code": "CSE301",

      "course_name": "Database Systems",

      "semester": 6,

      "section": "A",

      "total_sessions": 10,

      "present_sessions": 8,

      "absent_sessions": 2,

      "attendance_percentage": 80.0

    }

  ]

}

```



Example values are illustrative. With no closed sessions, the percentage is `0`.



## 5. Error responses



Invalid query parameters return HTTP `400`.



Example:



```json

{

  "success": false,

  "message": "Invalid date_from. Use YYYY-MM-DD."

}

```



A missing student profile returns HTTP `404`.



Missing or invalid authentication and incorrect roles are handled by the application's JWT and role-protection mechanisms.



## 6. Verification



The student attendance summary/history test module and attendance session closure test module pass. The complete backend test suite has also passed in the current development environment.



Re-run the tests after future changes:



`python -m unittest discover -s tests`
