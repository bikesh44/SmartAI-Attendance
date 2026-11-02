from datetime import date

from flask import Blueprint, jsonify, request

from app.models import (
    AttendanceRecord,
    AttendanceSession,
    CourseOffering,
    Enrollment,
    Faculty,
)
from app.utils.auth import admin_required
from app.utils.academic_year import canonical_academic_year


admin_analytics_bp = Blueprint(
    "admin_analytics",
    __name__,
    url_prefix="/api/admin/attendance",
)


@admin_analytics_bp.get("/analytics")
@admin_required
def get_admin_attendance_analytics():
    faculty_id = request.args.get("faculty_id", type=int)
    offering_id = request.args.get("offering_id", type=int)
    from_date_raw = request.args.get("from_date")
    to_date_raw = request.args.get("to_date")

    from_date = None
    to_date = None

    # ---------------------------------------------------------
    # Date validation
    # ---------------------------------------------------------

    if from_date_raw:
        try:
            from_date = date.fromisoformat(from_date_raw)
        except ValueError:
            return jsonify({
                "success": False,
                "message": "from_date must be in YYYY-MM-DD format",
            }), 400

    if to_date_raw:
        try:
            to_date = date.fromisoformat(to_date_raw)
        except ValueError:
            return jsonify({
                "success": False,
                "message": "to_date must be in YYYY-MM-DD format",
            }), 400

    if from_date and to_date and from_date > to_date:
        return jsonify({
            "success": False,
            "message": "from_date cannot be later than to_date",
        }), 400

    # ---------------------------------------------------------
    # Offering validation
    # ---------------------------------------------------------

    if offering_id is not None:
        offering = CourseOffering.query.filter_by(
            offering_id=offering_id
        ).first()

        if not offering:
            return jsonify({
                "success": False,
                "message": "Course offering not found",
            }), 404

    # ---------------------------------------------------------
    # Faculty validation
    # ---------------------------------------------------------

    if faculty_id is not None:
        faculty = Faculty.query.filter_by(
            faculty_id=faculty_id
        ).first()

        if not faculty:
            return jsonify({
                "success": False,
                "message": "Faculty not found",
            }), 404

    # ---------------------------------------------------------
    # Attendance sessions
    # ---------------------------------------------------------

    session_query = AttendanceSession.query.filter(
        AttendanceSession.status == "CLOSED"
    )

    if faculty_id is not None:
        session_query = session_query.filter(
            AttendanceSession.faculty_id == faculty_id
        )

    if offering_id is not None:
        session_query = session_query.filter(
            AttendanceSession.offering_id == offering_id
        )

    if from_date:
        session_query = session_query.filter(
            AttendanceSession.session_date >= from_date
        )

    if to_date:
        session_query = session_query.filter(
            AttendanceSession.session_date <= to_date
        )

    sessions = session_query.all()

    session_ids = [session.session_id for session in sessions]

    # ---------------------------------------------------------
    # Per-course analytics
    # ---------------------------------------------------------

    course_data = []

    total_sessions = 0
    total_students = 0
    total_present = 0
    total_absent = 0

    offerings = {}

    for session in sessions:
        offering = session.offering

        if offering.offering_id not in offerings:
            offerings[offering.offering_id] = {
                "offering": offering,
                "sessions": [],
            }

        offerings[offering.offering_id]["sessions"].append(session)

    for offering_id_key, offering_info in offerings.items():
        offering = offering_info["offering"]
        offering_sessions = offering_info["sessions"]

        active_enrollments = Enrollment.query.filter_by(
            offering_id=offering_id_key,
            status="ACTIVE",
        ).all()

        student_ids = {
            enrollment.student_id
            for enrollment in active_enrollments
        }

        session_count = len(offering_sessions)
        student_count = len(student_ids)

        possible_attendance = session_count * student_count

        present_count = 0

        if session_ids and student_ids:
            present_count = (
                AttendanceRecord.query
                .filter(
                    AttendanceRecord.session_id.in_(
                        [session.session_id for session in offering_sessions]
                    ),
                    AttendanceRecord.student_id.in_(student_ids),
                    AttendanceRecord.status == "PRESENT",
                )
                .count()
            )

        absent_count = possible_attendance - present_count

        percentage = (
            (present_count / possible_attendance) * 100
            if possible_attendance
            else 0.0
        )

        faculty = offering.faculty

        course_data.append({
            "offering_id": offering.offering_id,
            "course": {
                "course_id": offering.course.course_id,
                "course_code": offering.course.course_code,
                "course_name": offering.course.course_name,
            },
            "faculty": (
                {
                    "faculty_id": faculty.faculty_id,
                    "name": (
                        faculty.user.name
                        if faculty.user
                        else None
                    ),
                    "employee_id": faculty.employee_id,
                }
                if faculty
                else None
            ),
            "academic_year": canonical_academic_year(offering.academic_year),
            "semester": offering.semester,
            "section": offering.section,
            "room": offering.room,
            "total_sessions": session_count,
            "total_students": student_count,
            "total_present": present_count,
            "total_absent": absent_count,
            "attendance_percentage": round(percentage, 2),
        })

        total_sessions += session_count
        total_students += student_count
        total_present += present_count
        total_absent += absent_count

    possible_total = total_present + total_absent

    overall_percentage = (
        (total_present / possible_total) * 100
        if possible_total
        else 0.0
    )

    return jsonify({
        "success": True,
        "filters": {
            "faculty_id": faculty_id,
            "offering_id": offering_id,
            "from_date": (
                from_date.isoformat()
                if from_date
                else None
            ),
            "to_date": (
                to_date.isoformat()
                if to_date
                else None
            ),
        },
        "data": {
            "total_sessions": total_sessions,
            "total_students": total_students,
            "total_present": total_present,
            "total_absent": total_absent,
            "overall_percentage": round(
                overall_percentage,
                2,
            ),
            "courses": course_data,
        },
    }), 200