from collections import defaultdict
from datetime import date, datetime

from flask import Blueprint, jsonify, request, send_file
from flask_jwt_extended import get_jwt_identity
from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models import (
    AttendanceRecord,
    AttendanceSession,
    CourseOffering,
    Enrollment,
    Faculty,
    Student,
)
from app.utils.academic_year import canonical_academic_year, format_batch_cohort
from app.utils.auth import faculty_required
from app.utils.export_engine import (
    ExportRenderingError,
    ExportValidationError,
    generate_export,
)

MINIMUM_ATTENDANCE_PERCENTAGE = 75.0

reports_bp = Blueprint(
    "reports",
    __name__,
    url_prefix="/api/faculty/attendance/reports",
)


def get_current_faculty():
    user_id = int(get_jwt_identity())
    return Faculty.query.filter_by(user_id=user_id).first()


def _parse_report_filters():
    """Parse and validate query parameters for date range and offering filter."""
    offering_id = request.args.get("offering_id", type=int)
    from_date_raw = request.args.get("from_date")
    to_date_raw = request.args.get("to_date")

    from_date = None
    to_date = None

    if from_date_raw:
        try:
            from_date = date.fromisoformat(from_date_raw)
        except ValueError:
            return None, None, None, (
                jsonify({
                    "success": False,
                    "message": "from_date must be in YYYY-MM-DD format",
                }),
                400,
            )

    if to_date_raw:
        try:
            to_date = date.fromisoformat(to_date_raw)
        except ValueError:
            return None, None, None, (
                jsonify({
                    "success": False,
                    "message": "to_date must be in YYYY-MM-DD format",
                }),
                400,
            )

    if from_date and to_date and from_date > to_date:
        return None, None, None, (
            jsonify({
                "success": False,
                "message": "from_date cannot be later than to_date",
            }),
            400,
        )

    return offering_id, from_date, to_date, None


def _calculate_faculty_report_data(faculty, offering_id=None, from_date=None, to_date=None):
    """Aggregate closed-session attendance records for offerings taught by faculty.

    Enforces cross-faculty isolation: only offerings where faculty_id == faculty.faculty_id
    are queried. If an unauthorized or invalid offering_id is supplied, returns a 404 error.
    """
    offering_query = CourseOffering.query.filter_by(faculty_id=faculty.faculty_id)

    if offering_id is not None:
        offering_query = offering_query.filter_by(offering_id=offering_id)

    offerings = (
        offering_query.options(joinedload(CourseOffering.course))
        .order_by(CourseOffering.offering_id.asc())
        .all()
    )

    if offering_id is not None and not offerings:
        return None, None, (
            jsonify({
                "success": False,
                "message": "Course offering not found",
            }),
            404,
        )

    report = []

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

        sessions = session_query.order_by(AttendanceSession.session_date.asc()).all()
        session_ids = [session.session_id for session in sessions]
        total_sessions = len(session_ids)

        enrollments = (
            Enrollment.query.options(
                joinedload(Enrollment.student).joinedload(Student.user)
            )
            .filter_by(
                offering_id=offering.offering_id,
                status="ACTIVE",
            )
            .order_by(Enrollment.student_id.asc())
            .all()
        )

        counts_map = defaultdict(lambda: {"PRESENT": 0, "ABSENT": 0})
        if session_ids:
            record_counts = (
                db.session.query(
                    AttendanceRecord.student_id,
                    AttendanceRecord.status,
                    db.func.count(AttendanceRecord.attendance_id),
                )
                .filter(AttendanceRecord.session_id.in_(session_ids))
                .group_by(AttendanceRecord.student_id, AttendanceRecord.status)
                .all()
            )
            for s_id, st, cnt in record_counts:
                counts_map[s_id][st] = cnt

        students = []

        for enrollment in enrollments:
            student = enrollment.student
            present_count = counts_map[student.student_id]["PRESENT"]
            absent_count = counts_map[student.student_id]["ABSENT"]

            attendance_percentage = (
                (present_count / total_sessions) * 100
                if total_sessions > 0
                else 0
            )

            students.append({
                "student_id": student.student_id,
                "enrollment_no": student.enrollment_no,
                "student_name": student.user.name if student.user else "N/A",
                "email": student.user.email if student.user else "",
                "batch_year": format_batch_cohort(
                    student.batch.batch_name if student.batch else student.academic_year
                ),
                "total_sessions": total_sessions,
                "present_sessions": present_count,
                "absent_sessions": absent_count,
                "attendance_percentage": round(attendance_percentage, 2),
                "is_low_attendance": (
                    total_sessions > 0
                    and attendance_percentage < MINIMUM_ATTENDANCE_PERCENTAGE
                ),
            })

        report.append({
            "offering_id": offering.offering_id,
            "course_id": offering.course_id,
            "course_code": offering.course.course_code if offering.course else "",
            "course_name": offering.course.course_name if offering.course else "",
            "semester": offering.semester,
            "section": offering.section,
            "academic_year": canonical_academic_year(offering.academic_year),
            "room": offering.room,
            "total_sessions": total_sessions,
            "minimum_attendance_percentage": MINIMUM_ATTENDANCE_PERCENTAGE,
            "students": students,
        })

    return offerings, report, None


@reports_bp.get("")
@faculty_required
def get_attendance_report():
    """Retrieve JSON attendance report summary for courses assigned to faculty."""
    faculty = get_current_faculty()
    if not faculty:
        return jsonify({
            "success": False,
            "message": "Faculty profile not found",
        }), 404

    offering_id, from_date, to_date, err = _parse_report_filters()
    if err:
        return err

    offerings, report, err = _calculate_faculty_report_data(
        faculty, offering_id=offering_id, from_date=from_date, to_date=to_date
    )
    if err:
        return err

    return jsonify({
        "success": True,
        "filters": {
            "offering_id": offering_id,
            "from_date": from_date.isoformat() if from_date else None,
            "to_date": to_date.isoformat() if to_date else None,
        },
        "data": report,
    }), 200


@reports_bp.get("/export")
@faculty_required
def export_attendance_report():
    """Export attendance report for courses assigned to faculty in CSV, Excel, or PDF.

    Enforces strict backend faculty authorization, filter preservation,
    and memory-efficient streaming via the shared export engine.
    """
    faculty = get_current_faculty()
    if not faculty:
        return jsonify({
            "success": False,
            "message": "Faculty profile not found",
        }), 404

    # Format parameter validation
    format_param = request.args.get("format", "xlsx").strip().lower()
    if format_param not in ("csv", "xlsx", "excel", "pdf"):
        return jsonify({
            "success": False,
            "message": f"Unsupported export format '{format_param}'. Supported: 'csv', 'xlsx', 'pdf'.",
        }), 400

    offering_id, from_date, to_date, err = _parse_report_filters()
    if err:
        return err

    offerings, report_data, err = _calculate_faculty_report_data(
        faculty, offering_id=offering_id, from_date=from_date, to_date=to_date
    )
    if err:
        return err

    # Additional user display filters
    status_filter = request.args.get("status", "All").strip()
    search_filter = request.args.get("search", "").strip().lower()

    headers = [
        "S.No.",
        "Student ID",
        "Student Name",
        "Course & Section",
        "Total Classes",
        "Attended",
        "Absent",
        "Attendance %",
        "Status",
    ]

    rows = []
    idx = 1
    total_students = 0
    total_present_sum = 0
    total_sessions_sum = 0
    low_attendance_count = 0

    for item in report_data:
        class_label = f"{item['course_code']} - {item['section']}"
        for stu in item.get("students", []):
            # Apply search filter
            if search_filter:
                s_name = (stu.get("student_name") or "").lower()
                s_id = (stu.get("enrollment_no") or "").lower()
                s_email = (stu.get("email") or "").lower()
                if (
                    search_filter not in s_name
                    and search_filter not in s_id
                    and search_filter not in s_email
                ):
                    continue

            # Apply status filter
            is_low = stu.get("is_low_attendance", False)
            pres_count = stu.get("present_sessions", 0)
            abs_count = stu.get("absent_sessions", 0)

            if status_filter == "Present" and pres_count == 0:
                continue
            if status_filter == "Absent" and abs_count == 0:
                continue
            if status_filter in ("Low", "LOW", "Needs Attention") and not is_low:
                continue
            if status_filter in ("Good", "GOOD") and is_low:
                continue

            pct = stu.get("attendance_percentage", 0.0)
            status_label = "Needs Attention" if is_low else "Good"

            rows.append([
                idx,
                stu.get("enrollment_no") or "N/A",
                stu.get("student_name") or "N/A",
                class_label,
                stu.get("total_sessions", 0),
                pres_count,
                abs_count,
                f"{pct:.1f}%",
                status_label,
            ])
            idx += 1
            total_students += 1
            total_present_sum += pres_count
            total_sessions_sum += stu.get("total_sessions", 0)
            if is_low:
                low_attendance_count += 1

    # Metadata & summary
    faculty_user = getattr(faculty, "user", None)
    fac_name = faculty_user.name if faculty_user else "Faculty"
    dept = getattr(faculty, "department", None)
    dept_name = dept.department_name if dept else "N/A"

    class_str = (
        f"{offerings[0].course.course_code} - {offerings[0].section}"
        if (offering_id and len(offerings) == 1 and offerings[0].course)
        else "All Assigned Classes"
    )

    date_str = (
        f"{from_date.isoformat()} to {to_date.isoformat()}"
        if (from_date and to_date)
        else (
            f"From {from_date.isoformat()}"
            if from_date
            else (f"Up to {to_date.isoformat()}" if to_date else "All Recorded Sessions")
        )
    )

    metadata = {
        "Faculty": fac_name,
        "Department": dept_name,
        "Class": class_str,
        "Date Range": date_str,
    }

    avg_pct = (
        round((total_present_sum / total_sessions_sum) * 100, 1)
        if total_sessions_sum > 0
        else 0.0
    )
    summary = {
        "Total Students": total_students,
        "Low Attendance (<75%)": low_attendance_count,
        "Average Attendance": f"{avg_pct}%",
    }

    class_slug = (
        f"{offerings[0].course.course_code}_{offerings[0].section}"
        if (offering_id and len(offerings) == 1 and offerings[0].course)
        else "All_Classes"
    )
    today_str = datetime.now().strftime("%Y%m%d")
    base_filename = f"Faculty_Attendance_Report_{class_slug}_{today_str}"

    try:
        stream, mimetype, filename = generate_export(
            format_type=format_param,
            headers=headers,
            rows=rows,
            title="FACULTY ATTENDANCE REPORT",
            subtitle=class_str,
            metadata=metadata,
            summary=summary,
            base_filename=base_filename,
            sheet_name="Attendance Report",
            orientation="landscape" if len(headers) > 7 else "portrait",
        )
    except ExportValidationError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400
    except ExportRenderingError as exc:
        return jsonify({"success": False, "message": f"Rendering error: {str(exc)}"}), 500

    return send_file(
        stream,
        mimetype=mimetype,
        as_attachment=True,
        download_name=filename,
    )
