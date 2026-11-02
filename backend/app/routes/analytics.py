from datetime import date

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity
from sqlalchemy import func
from app.models import (
    AttendanceRecord,
    AttendanceSession,
    CourseOffering,
    Enrollment,
    Faculty,
    Student,
    User,
)
from app.utils.auth import faculty_required
from app.utils.academic_year import canonical_academic_year

MINIMUM_ATTENDANCE_PERCENTAGE = 75.0

analytics_bp = Blueprint(
    "analytics",
    __name__,
    url_prefix="/api/faculty/attendance/analytics",
)


def get_current_faculty():
    identity = get_jwt_identity()
    if not identity:
        return None
    try:
        user_id = int(identity)
    except (TypeError, ValueError):
        return None

    return Faculty.query.filter_by(
        user_id=user_id
    ).first()


@analytics_bp.get("")
@faculty_required
def get_attendance_analytics():
    faculty = get_current_faculty()

    if not faculty:
        return jsonify({
            "success": False,
            "message": "Faculty profile not found",
        }), 404

    offering_id = request.args.get("offering_id", type=int)
    semester = request.args.get("semester", type=int)
    academic_year = request.args.get("academic_year")
    from_date_raw = request.args.get("from_date")
    to_date_raw = request.args.get("to_date")

    from_date = None
    to_date = None

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

    offering_query = CourseOffering.query.filter_by(
        faculty_id=faculty.faculty_id
    )

    if offering_id is not None:
        offering_query = offering_query.filter_by(
            offering_id=offering_id
        )

    if semester is not None:
        offering_query = offering_query.filter(CourseOffering.semester == semester)

    if academic_year and academic_year not in ["All", "all", ""]:
        offering_query = offering_query.filter(CourseOffering.academic_year == academic_year)

    offerings = (
        offering_query
        .order_by(CourseOffering.offering_id.asc())
        .all()
    )

    if offering_id is not None and not offerings:
        return jsonify({
            "success": False,
            "message": "Course offering not found",
        }), 404

    course_reports = []

    total_courses = 0
    total_sessions = 0
    total_students = 0
    total_present = 0
    total_absent = 0
    low_attendance_students = 0

    for offering in offerings:
        session_query = AttendanceSession.query.filter(
            AttendanceSession.offering_id == offering.offering_id,
            AttendanceSession.status == "CLOSED",
        )

        if from_date:
            session_query = session_query.filter(
                AttendanceSession.session_date >= from_date
            )

        if to_date:
            session_query = session_query.filter(
                AttendanceSession.session_date <= to_date
            )

        sessions = (
            session_query
            .order_by(AttendanceSession.session_date.asc())
            .all()
        )

        session_ids = [
            session.session_id
            for session in sessions
        ]

        session_count = len(session_ids)

        base_enr_q = (
            Enrollment.query
            .join(Student, Enrollment.student_id == Student.student_id)
            .join(User, Student.user_id == User.user_id)
            .filter(
                Enrollment.status == "ACTIVE",
                User.is_active.is_(True),
                User.role == "STUDENT",
            )
        )
        enrollments = (
            base_enr_q
            .filter(Enrollment.offering_id == offering.offering_id)
            .order_by(Enrollment.student_id.asc())
            .all()
        )
        if not enrollments:
            sibling_offering_ids = [
                o.offering_id for o in CourseOffering.query.filter_by(
                    course_id=offering.course_id,
                    semester=offering.semester,
                    section=offering.section,
                ).all()
            ]
            enrollments = (
                base_enr_q
                .filter(
                    Enrollment.offering_id.in_(sibling_offering_ids),
                    Student.semester == offering.semester,
                    Student.section == offering.section,
                )
                .order_by(Enrollment.student_id.asc())
                .all()
            )

        student_count = len(enrollments)

        low_attendance_count = 0

        if session_count > 0 and enrollments:
            student_ids = [
                enrollment.student_id
                for enrollment in enrollments
            ]

            present_counts = dict(
                AttendanceRecord.query.with_entities(
                    AttendanceRecord.student_id,
                    func.count(AttendanceRecord.session_id),
                )
                .filter(
                    AttendanceRecord.session_id.in_(session_ids),
                    AttendanceRecord.student_id.in_(student_ids),
                    AttendanceRecord.status == "PRESENT",
                )
                .group_by(AttendanceRecord.student_id)
                .all()
            )

            low_attendance_count = sum(
                1
                for enrollment in enrollments
                if (
                    present_counts.get(enrollment.student_id, 0)
                    / session_count
                ) * 100 < MINIMUM_ATTENDANCE_PERCENTAGE
            )

        low_attendance_students += low_attendance_count

        present_count = 0

        if session_ids and enrollments:
            student_ids = [
                enrollment.student_id
                for enrollment in enrollments
            ]

            present_count = (
                AttendanceRecord.query
                .filter(
                    AttendanceRecord.session_id.in_(session_ids),
                    AttendanceRecord.student_id.in_(student_ids),
                    AttendanceRecord.status == "PRESENT",
                )
                .count()
            )

        possible_attendance = session_count * student_count
        absent_count = possible_attendance - present_count

        attendance_percentage = (
            round((present_count / possible_attendance) * 100, 2)
            if possible_attendance > 0
            else None
        )

        total_courses += 1
        total_sessions += session_count
        total_students += student_count
        total_present += present_count
        total_absent += absent_count

        last_session_date = sessions[-1].session_date.isoformat() if sessions else None

        course_reports.append({
            "offering_id": offering.offering_id,
            "course_id": offering.course_id,
            "course_code": offering.course.course_code,
            "course_name": offering.course.course_name,
            "semester": offering.semester,
            "section": offering.section,
            "academic_year": canonical_academic_year(offering.academic_year),
            "room": offering.room,
            "total_sessions": session_count,
            "students": student_count,
            "present": present_count,
            "absent": absent_count,
            "attendance_percentage": attendance_percentage,
            "low_attendance_students": low_attendance_count,
            "has_sessions": session_count > 0,
            "last_session_date": last_session_date,
        })

    total_possible_attendance = total_present + total_absent

    overall_attendance_percentage = (
        round((total_present / total_possible_attendance) * 100, 2)
        if total_possible_attendance > 0
        else None
    )

    return jsonify({
        "success": True,
        "filters": {
            "offering_id": offering_id,
            "semester": semester,
            "academic_year": academic_year,
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
            "total_courses": total_courses,
            "total_sessions": total_sessions,
            "total_students": total_students,
            "total_present": total_present,
            "total_absent": total_absent,
            "overall_attendance_percentage": overall_attendance_percentage,
            "has_sessions": total_sessions > 0,
            "courses": course_reports,
            "minimum_attendance_percentage": (
                MINIMUM_ATTENDANCE_PERCENTAGE
            ),
            "low_attendance_students": low_attendance_students,
        },
    }), 200
