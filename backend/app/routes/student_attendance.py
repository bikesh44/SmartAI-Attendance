
import re
from collections import defaultdict
from datetime import date, datetime, timedelta
from math import ceil

from flask import Blueprint, jsonify, request, send_file
from app.utils.export_engine import (
    generate_export,
    ExportValidationError,
    ExportRenderingError,
)
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
    TimetableEntry,
)
from app.utils.academic_year import (
    are_offerings_academically_compatible,
    canonical_academic_year,
    is_single_academic_session,
    resolve_offering_academic_year,
)
from app.utils.auth import student_required

student_attendance_bp = Blueprint(
    "student_attendance",
    __name__,
    url_prefix="/api/student/attendance",
)


def get_current_student():
    identity = get_jwt_identity()

    try:
        user_id = int(identity)
    except (TypeError, ValueError):
        return None

    return Student.query.filter_by(user_id=user_id).first()


def parse_date_filter(name):
    """Parse an optional YYYY-MM-DD query parameter."""
    value = request.args.get(name, "").strip()

    if not value:
        return None, None

    try:
        return date.fromisoformat(value), None
    except ValueError:
        return None, (
            jsonify({
                "success": False,
                "message": f"Invalid {name}. Use YYYY-MM-DD.",
            }),
            400,
        )


def parse_positive_int(
    name,
    default=None,
    minimum=1,
    maximum=None,
):
    """Parse an optional positive integer query parameter."""
    value = request.args.get(name)

    if value is None or value.strip() == "":
        return default, None

    try:
        number = int(value)
    except (TypeError, ValueError):
        return None, (
            jsonify({
                "success": False,
                "message": f"{name} must be an integer.",
            }),
            400,
        )

    if number < minimum or (
        maximum is not None and number > maximum
    ):
        message = f"{name} must be at least {minimum}."

        if maximum is not None:
            message = (
                f"{name} must be between {minimum} and {maximum}."
            )

        return None, (
            jsonify({
                "success": False,
                "message": message,
            }),
            400,
        )

    return number, None


def build_history_query(student_id):
    """Build a history query scoped to the authenticated student."""
    query = (
        AttendanceRecord.query
        .filter(AttendanceRecord.student_id == student_id)
        .join(AttendanceSession)
        .join(
            CourseOffering,
            AttendanceSession.offering_id
            == CourseOffering.offering_id,
        )
    )

    course_id, error = parse_positive_int("course_id")
    if error:
        return None, error

    offering_id, error = parse_positive_int("offering_id")
    if error:
        return None, error

    date_from, error = parse_date_filter("date_from")
    if error:
        return None, error

    date_to, error = parse_date_filter("date_to")
    if error:
        return None, error

    if date_from and date_to and date_from > date_to:
        return None, (
            jsonify({
                "success": False,
                "message": "date_from cannot be after date_to.",
            }),
            400,
        )

    status = request.args.get("status", "").strip().upper()

    if status and status not in {"PRESENT", "ABSENT", "LATE"}:
        return None, (
            jsonify({
                "success": False,
                "message": (
                    "Invalid status. Use PRESENT, ABSENT, or LATE."
                ),
            }),
            400,
        )

    academic_year = request.args.get("academic_year", "").strip()
    if academic_year and academic_year.lower() != "all":
        canon_ay = canonical_academic_year(academic_year)
        clean_ay = academic_year.replace(" ", "")
        query = query.filter(
            db.or_(
                CourseOffering.academic_year == academic_year,
                CourseOffering.academic_year == canon_ay,
                CourseOffering.academic_year.ilike(f"%{clean_ay}%"),
            )
        )

    semester_arg = request.args.get("semester", "").strip()
    if semester_arg and semester_arg.lower() != "all":
        sem_match = re.search(r"\d+", semester_arg)
        if sem_match:
            sem_val = int(sem_match.group(0))
            query = query.filter(CourseOffering.semester == sem_val)

    if course_id is not None:
        query = query.filter(
            CourseOffering.course_id == course_id
        )

    if offering_id is not None:
        query = query.filter(
            CourseOffering.offering_id == offering_id
        )

    if date_from:
        query = query.filter(
            AttendanceSession.session_date >= date_from
        )

    if date_to:
        query = query.filter(
            AttendanceSession.session_date <= date_to
        )

    if status:
        query = query.filter(
            AttendanceRecord.status == status
        )

    return query, None


def serialize_record(record):
    """Serialize an attendance record for the student API."""
    session = record.session
    offering = session.offering
    course = offering.course

    st = session.start_time
    et = session.end_time

    start_time_str = st.strftime("%I:%M %p") if st else None
    end_time_str = et.strftime("%I:%M %p") if et else None
    session_timing = (
        f"{start_time_str} - {end_time_str}"
        if (start_time_str and end_time_str)
        else start_time_str
    )
    session_name = "Morning" if (st and st.hour < 12) else "Afternoon"

    att_time_str = (
        record.marked_at.strftime("%I:%M %p")
        if (record.marked_at and record.status != "ABSENT")
        else None
    )

    faculty_name = None
    if offering.faculty and offering.faculty.user:
        faculty_name = offering.faculty.user.name

    return {
        "attendance_id": record.attendance_id,
        "session_id": record.session_id,
        "course_id": offering.course_id,
        "offering_id": offering.offering_id,
        "course_code": course.course_code,
        "course_name": course.course_name,
        "section": offering.section,
        "session_date": session.session_date.isoformat(),
        "status": record.status,
        "marked_at": (
            record.marked_at.isoformat()
            if record.marked_at
            else None
        ),
        "attendance_time": att_time_str,
        "start_time": start_time_str,
        "end_time": end_time_str,
        "session_timing": session_timing,
        "session_name": session_name,
        "session": session_name,
        "academic_year": offering.academic_year,
        "semester": offering.semester,
        "room": offering.room or "TBD",
        "faculty_name": faculty_name,
        "remarks": None,
        "recognition_method": record.recognition_method,
        "confidence_score": record.confidence_score,
    }


@student_attendance_bp.get("/")
@student_attendance_bp.get("/report")
@student_required
def get_my_attendance():
    """Return filtered and paginated attendance history."""
    student = get_current_student()

    if not student:
        return jsonify({
            "success": False,
            "message": "Student profile not found",
        }), 404

    page, error = parse_positive_int("page", default=1)
    if error:
        return error

    per_page, error = parse_positive_int(
        "per_page",
        default=20,
        maximum=100,
    )
    if error:
        return error

    query, error = build_history_query(student.student_id)
    if error:
        return error

    total_records = query.count()
    total_pages = (
        ceil(total_records / per_page)
        if total_records
        else 0
    )

    records = (
        query
        .options(
            joinedload(AttendanceRecord.session)
            .joinedload(AttendanceSession.offering)
            .joinedload(CourseOffering.course),
            joinedload(AttendanceRecord.session)
            .joinedload(AttendanceSession.offering)
            .joinedload(CourseOffering.faculty)
            .joinedload(Faculty.user),
        )
        .order_by(
            AttendanceSession.session_date.desc(),
            AttendanceRecord.marked_at.desc(),
            AttendanceRecord.attendance_id.desc(),
        )
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    return jsonify({
        "success": True,
        "page": page,
        "per_page": per_page,
        "total_records": total_records,
        "total_pages": total_pages,
        "data": [
            serialize_record(record)
            for record in records
        ],
    }), 200


@student_attendance_bp.get("/summary")
@student_required
def get_attendance_summary():
    """Return attendance totals for the student's active enrollments with optional filters."""
    student = get_current_student()

    if not student:
        return jsonify({
            "success": False,
            "message": "Student profile not found",
        }), 404

    # Optional filter params
    course_id, error = parse_positive_int("course_id")
    if error:
        return error

    offering_id, error = parse_positive_int("offering_id")
    if error:
        return error

    date_from, error = parse_date_filter("date_from")
    if error:
        return error

    date_to, error = parse_date_filter("date_to")
    if error:
        return error

    if date_from and date_to and date_from > date_to:
        return jsonify({
            "success": False,
            "message": "date_from cannot be after date_to.",
        }), 400

    academic_year = request.args.get("academic_year", "").strip()
    semester_arg = request.args.get("semester", "").strip()

    all_enrollments = (
        Enrollment.query
        .options(
            joinedload(Enrollment.offering)
            .joinedload(CourseOffering.course),
            joinedload(Enrollment.offering)
            .joinedload(CourseOffering.faculty)
            .joinedload(Faculty.user),
        )
        .filter_by(
            student_id=student.student_id,
            status="ACTIVE",
        )
        .all()
    )

    # Collect available filter options from student's profile & enrollments
    seen_years = set()
    seen_semesters = set()
    seen_courses = {}

    if student.academic_year:
        seen_years.add(canonical_academic_year(student.academic_year))
    if student.semester:
        seen_semesters.add(student.semester)

    for enr in all_enrollments:
        off = enr.offering
        if not off:
            continue
        c = off.course
        if c and c.course_id not in seen_courses:
            seen_courses[c.course_id] = {
                "course_id": c.course_id,
                "course_code": c.course_code,
                "course_name": c.course_name,
            }
        if off.academic_year:
            seen_years.add(canonical_academic_year(off.academic_year))
        if off.semester is not None:
            seen_semesters.add(off.semester)

    filter_options = {
        "academic_years": sorted([y for y in seen_years if y]),
        "semesters": sorted(seen_semesters),
        "courses": sorted(seen_courses.values(), key=lambda x: x["course_code"]),
    }

    # Apply filters to enrollments
    enrollments = all_enrollments
    if course_id is not None:
        enrollments = [e for e in enrollments if e.offering and e.offering.course_id == course_id]
    if offering_id is not None:
        enrollments = [e for e in enrollments if e.offering_id == offering_id]
    if academic_year and academic_year.lower() != "all":
        canon_ay = canonical_academic_year(academic_year)
        clean_ay = academic_year.replace(" ", "")
        enrollments = [
            e for e in enrollments
            if e.offering and (
                e.offering.academic_year == academic_year
                or canonical_academic_year(e.offering.academic_year) == canon_ay
                or clean_ay in (e.offering.academic_year or "").replace(" ", "")
            )
        ]
    if semester_arg and semester_arg.lower() != "all":
        sem_match = re.search(r"\d+", semester_arg)
        if sem_match:
            target_sem = int(sem_match.group(0))
            enrollments = [e for e in enrollments if e.offering and e.offering.semester == target_sem]

    offering_sessions_map = defaultdict(set)
    all_closed_session_ids = set()

    for enrollment in enrollments:
        offering = enrollment.offering
        if not offering:
            continue

        # Direct sessions for this offering
        direct_query = AttendanceSession.query.filter(
            AttendanceSession.offering_id == offering.offering_id,
            AttendanceSession.status == "CLOSED",
        )
        if date_from:
            direct_query = direct_query.filter(AttendanceSession.session_date >= date_from)
        if date_to:
            direct_query = direct_query.filter(AttendanceSession.session_date <= date_to)

        direct_sessions = direct_query.all()
        for s in direct_sessions:
            offering_sessions_map[offering.offering_id].add(s.session_id)
            all_closed_session_ids.add(s.session_id)

        # Sibling sessions for equivalent course, semester, section offerings
        candidate_siblings = (
            CourseOffering.query
            .filter(
                CourseOffering.course_id == offering.course_id,
                CourseOffering.semester == offering.semester,
                CourseOffering.section == offering.section,
                CourseOffering.offering_id != offering.offering_id,
            )
            .all()
        )
        sibling_offerings = [
            s for s in candidate_siblings
            if are_offerings_academically_compatible(
                s.academic_year, s.semester,
                offering.academic_year, offering.semester,
            )
        ]
        sibling_ids = [s.offering_id for s in sibling_offerings]
        if sibling_ids:
            sib_query = AttendanceSession.query.filter(
                AttendanceSession.offering_id.in_(sibling_ids),
                AttendanceSession.status == "CLOSED",
            )
            if date_from:
                sib_query = sib_query.filter(AttendanceSession.session_date >= date_from)
            if date_to:
                sib_query = sib_query.filter(AttendanceSession.session_date <= date_to)

            sibling_sessions = sib_query.all()
            for s in sibling_sessions:
                offering_sessions_map[offering.offering_id].add(s.session_id)
                all_closed_session_ids.add(s.session_id)

    student_records_map = {}
    if all_closed_session_ids:
        rec_rows = (
            AttendanceRecord.query
            .filter(
                AttendanceRecord.student_id == student.student_id,
                AttendanceRecord.session_id.in_(all_closed_session_ids),
            )
            .all()
        )
        for r in rec_rows:
            student_records_map[r.session_id] = r.status

    data = []
    overall_total = 0
    overall_present = 0
    overall_late = 0

    for enrollment in enrollments:
        offering = enrollment.offering
        if not offering:
            continue

        course = offering.course
        if not course:
            continue

        session_ids = offering_sessions_map[offering.offering_id]
        total_sessions = len(session_ids)
        present_count = sum(1 for sid in session_ids if student_records_map.get(sid) == "PRESENT")
        late_count = sum(1 for sid in session_ids if student_records_map.get(sid) == "LATE")
        absent_count = max(0, total_sessions - present_count - late_count)

        percentage = (
            (present_count / total_sessions) * 100
            if total_sessions
            else 0
        )

        overall_total += total_sessions
        overall_present += present_count
        overall_late += late_count

        ay_raw = offering.academic_year
        if ay_raw and is_single_academic_session(ay_raw):
            ay_val = canonical_academic_year(ay_raw)
        else:
            ay_val = resolve_offering_academic_year(ay_raw, offering.semester)

        faculty_name = (
            offering.faculty.user.name
            if (offering.faculty and offering.faculty.user)
            else None
        )

        data.append({
            "offering_id": offering.offering_id,
            "course_id": course.course_id,
            "course_code": course.course_code,
            "course_name": course.course_name,
            "credits": course.credits,
            "faculty_name": faculty_name,
            "room": offering.room or "TBD",
            "semester": offering.semester,
            "section": offering.section,
            "academic_year": ay_val,
            "total_sessions": total_sessions,
            "eligible_sessions": total_sessions,
            "present_sessions": present_count,
            "absent_sessions": absent_count,
            "late_sessions": late_count,
            "has_eligible_sessions": total_sessions > 0,
            "attendance_percentage": round(percentage, 2) if total_sessions > 0 else 0,
            "display_percentage": f"{round(percentage, 1)}%" if total_sessions > 0 else "N/A",
        })

    overall_absent = max(0, overall_total - overall_present - overall_late)
    overall_percentage = (
        (overall_present / overall_total) * 100
        if overall_total
        else 0
    )

    return jsonify({
        "success": True,
        "overall": {
            "total_sessions": overall_total,
            "eligible_sessions": overall_total,
            "present_sessions": overall_present,
            "absent_sessions": overall_absent,
            "late_sessions": overall_late,
            "present_days": overall_present,
            "absent_days": overall_absent,
            "late_days": overall_late,
            "total_days": overall_total,
            "has_eligible_sessions": overall_total > 0,
            "attendance_percentage": round(overall_percentage, 1) if overall_total > 0 else 0,
            "display_percentage": f"{round(overall_percentage, 1)}%" if overall_total > 0 else "N/A",
        },
        "data": data,
        "filter_options": filter_options,
    }), 200


@student_attendance_bp.get("/<int:attendance_id>")
@student_required
def get_attendance_record_detail(attendance_id):
    """Return full details for a single attendance record owned by the student."""
    student = get_current_student()

    if not student:
        return jsonify({
            "success": False,
            "message": "Student profile not found",
        }), 404

    record = (
        AttendanceRecord.query
        .options(
            joinedload(AttendanceRecord.session)
            .joinedload(AttendanceSession.offering)
            .joinedload(CourseOffering.course),
            joinedload(AttendanceRecord.session)
            .joinedload(AttendanceSession.offering)
            .joinedload(CourseOffering.faculty)
            .joinedload(Faculty.user),
        )
        .filter_by(
            attendance_id=attendance_id,
            student_id=student.student_id,
        )
        .first()
    )

    if not record:
        return jsonify({
            "success": False,
            "message": "Attendance record not found",
        }), 404

    return jsonify({
        "success": True,
        "data": serialize_record(record),
    }), 200


@student_attendance_bp.get("/export")
@student_required
def export_student_attendance():
    """Export the authenticated student's subject-wise attendance report as PDF (default), XLSX, or CSV."""
    student = get_current_student()
    if not student:
        return jsonify({
            "success": False,
            "message": "Student profile not found",
        }), 404

    format_param = request.args.get("format", "pdf").strip().lower()
    if format_param not in ("pdf", "csv", "xlsx", "excel"):
        return jsonify({
            "success": False,
            "message": f"Unsupported export format '{format_param}'. Must be 'pdf', 'csv', or 'xlsx'.",
        }), 400

    summary_resp, status_code = get_attendance_summary()
    if status_code != 200:
        return summary_resp, status_code

    summary_json = summary_resp.get_json()
    if not summary_json.get("success"):
        return jsonify({
            "success": False,
            "message": "Failed to compute report data",
        }), 500

    courses_data = summary_json.get("data", [])
    overall = summary_json.get("overall", {})

    student_name = student.user.name if student.user and student.user.name else "Student"
    dept_name = student.department.department_name if student.department else "N/A"
    ay_filter = request.args.get("academic_year", "").strip() or student.academic_year or "N/A"
    sem_arg = request.args.get("semester", "").strip()
    sem_filter = sem_arg if sem_arg and sem_arg.lower() != "all" else (f"Semester {student.semester}" if student.semester else "All Semesters")
    date_from_str = request.args.get("date_from", "").strip()
    date_to_str = request.args.get("date_to", "").strip()

    metadata = {
        "Student Name": student_name,
        "Enrollment No": student.enrollment_no or "N/A",
        "Department": dept_name,
        "Academic Year": ay_filter,
        "Semester": sem_filter,
    }
    if date_from_str or date_to_str:
        date_range_label = f"{date_from_str or 'Beginning'} to {date_to_str or 'Today'}"
        metadata["Date Range"] = date_range_label

    total_sessions = overall.get("total_sessions", 0)
    present_sessions = overall.get("present_sessions", 0)
    absent_sessions = overall.get("absent_sessions", 0)
    late_sessions = overall.get("late_sessions", 0)
    attendance_pct = overall.get("attendance_percentage", 0)

    summary_block = {
        "Overall Attendance": f"{attendance_pct}%" if total_sessions > 0 else "N/A",
        "Classes Attended": f"{present_sessions} / {total_sessions}",
        "Classes Missed": str(absent_sessions),
        "Late Sessions": str(late_sessions),
        "Total Subjects": len(courses_data),
    }

    headers = [
        "S.No.",
        "Course Code",
        "Subject Name",
        "Credits",
        "Faculty In-Charge",
        "Semester",
        "Section",
        "Conducted",
        "Attended",
        "Missed",
        "Late",
        "Attendance %",
        "Status",
    ]

    rows = []
    for idx, c in enumerate(courses_data, start=1):
        tot = int(c.get("total_sessions", 0))
        pres = int(c.get("present_sessions", 0))
        absent = int(c.get("absent_sessions", 0))
        late = int(c.get("late_sessions", 0))
        pct = float(c.get("attendance_percentage", 0)) if tot > 0 else 0.0
        if tot == 0:
            status_label = "No Sessions"
        elif pct >= 90.0:
            status_label = "Excellent"
        elif pct >= 75.0:
            status_label = "Good"
        else:
            status_label = "Needs Attention"

        pct_str = f"{pct:.1f}%" if tot > 0 else "N/A"

        rows.append([
            idx,
            c.get("course_code") or "N/A",
            c.get("course_name") or "Subject",
            str(c.get("credits") or "-"),
            c.get("faculty_name") or "Assigned Faculty",
            f"Sem {c.get('semester')}" if c.get("semester") else "-",
            c.get("section") or "-",
            str(tot),
            str(pres),
            str(absent),
            str(late),
            pct_str,
            status_label,
        ])

    base_filename = f"Subject_Attendance_Report_{student.enrollment_no}"

    try:
        stream, mimetype, filename = generate_export(
            format_type=format_param,
            headers=headers,
            rows=rows,
            title="STUDENT SUBJECT-WISE ATTENDANCE REPORT",
            subtitle=f"Official Attendance Summary — {student_name} ({student.enrollment_no})",
            metadata=metadata,
            summary=summary_block,
            base_filename=base_filename,
            sheet_name="Subject Attendance",
            orientation="landscape",
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


@student_attendance_bp.get("/daily-punch")
@student_attendance_bp.get("/matrix")
@student_required
def get_daily_punch():
    """Return weekly subject attendance matrix, daily punch summary cards, and day schedule."""
    student = get_current_student()
    if not student:
        return jsonify({
            "success": False,
            "message": "Student profile not found",
        }), 404

    # 1. Parse target date and week range
    date_str = request.args.get("date", "").strip()
    if date_str:
        try:
            target_date = date.fromisoformat(date_str)
        except ValueError:
            return jsonify({
                "success": False,
                "message": "Invalid date. Use YYYY-MM-DD.",
            }), 400
    else:
        target_date = date.today()

    start_date_str = request.args.get("start_date", "").strip()
    end_date_str = request.args.get("end_date", "").strip()

    if start_date_str and end_date_str:
        try:
            week_start = date.fromisoformat(start_date_str)
            week_end = date.fromisoformat(end_date_str)
        except ValueError:
            return jsonify({
                "success": False,
                "message": "Invalid start_date or end_date. Use YYYY-MM-DD.",
            }), 400
        if week_start > week_end:
            return jsonify({
                "success": False,
                "message": "start_date cannot be after end_date.",
            }), 400
    else:
        # Default to Monday through Friday of the week containing target_date
        week_start = target_date - timedelta(days=target_date.weekday())
        week_end = week_start + timedelta(days=4)

    # Generate 5 standard weekdays (Mon - Fri)
    week_days = []
    curr = week_start
    while curr <= week_end:
        week_days.append({
            "date": curr.isoformat(),
            "day_name": curr.strftime("%A"),
            "short_day": curr.strftime("%a"),
            "short_date": curr.strftime("%b %d"),
            "label": curr.strftime("%a %b %d"),
            "is_today": (curr == date.today()),
            "is_selected": (curr == target_date),
        })
        curr += timedelta(days=1)

    # 2. Query Student's Active Enrollments & Offerings
    enrollments = (
        Enrollment.query
        .options(
            joinedload(Enrollment.offering).joinedload(CourseOffering.course),
            joinedload(Enrollment.offering).joinedload(CourseOffering.faculty).joinedload(Faculty.user),
        )
        .filter_by(student_id=student.student_id, status="ACTIVE")
        .all()
    )

    offering_sessions_map = defaultdict(set)
    all_closed_session_ids = set()
    offering_to_compatible_ids = defaultdict(set)
    all_target_offering_ids = set()

    for enrollment in enrollments:
        off = enrollment.offering
        if not off:
            continue
        offering_to_compatible_ids[off.offering_id].add(off.offering_id)
        all_target_offering_ids.add(off.offering_id)

        # Sibling offerings with compatible academic term
        candidates = (
            CourseOffering.query
            .filter(
                CourseOffering.course_id == off.course_id,
                CourseOffering.semester == off.semester,
                CourseOffering.section == off.section,
                CourseOffering.offering_id != off.offering_id,
            )
            .all()
        )
        for sib in candidates:
            if are_offerings_academically_compatible(
                sib.academic_year, sib.semester,
                off.academic_year, off.semester,
            ):
                offering_to_compatible_ids[off.offering_id].add(sib.offering_id)
                all_target_offering_ids.add(sib.offering_id)

    # 3. Overall Semester Summary Calculation
    if all_target_offering_ids:
        all_closed_sessions = (
            AttendanceSession.query
            .filter(
                AttendanceSession.offering_id.in_(all_target_offering_ids),
                AttendanceSession.status == "CLOSED",
            )
            .all()
        )
        for s in all_closed_sessions:
            for direct_id, comp_set in offering_to_compatible_ids.items():
                if s.offering_id in comp_set:
                    offering_sessions_map[direct_id].add(s.session_id)
            all_closed_session_ids.add(s.session_id)

    student_records_map = {}
    if all_closed_session_ids:
        rec_rows = (
            AttendanceRecord.query
            .filter(
                AttendanceRecord.student_id == student.student_id,
                AttendanceRecord.session_id.in_(all_closed_session_ids),
            )
            .all()
        )
        for r in rec_rows:
            student_records_map[r.session_id] = r.status

    overall_total = 0
    overall_present = 0
    overall_late = 0

    for enr in enrollments:
        off = enr.offering
        if not off:
            continue
        s_ids = offering_sessions_map[off.offering_id]
        total_s = len(s_ids)
        present_s = sum(1 for sid in s_ids if student_records_map.get(sid) in ("PRESENT", "LATE"))
        late_s = sum(1 for sid in s_ids if student_records_map.get(sid) == "LATE")

        overall_total += total_s
        overall_present += present_s
        overall_late += late_s

    overall_absent = max(0, overall_total - overall_present)
    overall_percentage = (
        round((overall_present / overall_total) * 100, 1)
        if overall_total > 0
        else 0.0
    )
    present_percentage = (
        round((overall_present / overall_total) * 100, 1)
        if overall_total > 0
        else 0.0
    )
    absent_percentage = (
        round((overall_absent / overall_total) * 100, 1)
        if overall_total > 0
        else 0.0
    )
    late_percentage = (
        round((overall_late / overall_total) * 100, 1)
        if overall_total > 0
        else 0.0
    )

    # 4. Fetch Timetable Entries for target offerings
    timetable_entries = []
    if all_target_offering_ids:
        timetable_entries = (
            TimetableEntry.query
            .options(
                joinedload(TimetableEntry.offering).joinedload(CourseOffering.course),
                joinedload(TimetableEntry.offering).joinedload(CourseOffering.faculty).joinedload(Faculty.user),
            )
            .filter(TimetableEntry.offering_id.in_(all_target_offering_ids))
            .all()
        )

    # Group timetable entries by (offering_id, day_of_week.lower())
    timetable_by_offering_day = defaultdict(list)
    for entry in timetable_entries:
        day_key = entry.day_of_week.strip().lower()
        for direct_id, comp_set in offering_to_compatible_ids.items():
            if entry.offering_id in comp_set:
                timetable_by_offering_day[(direct_id, day_key)].append(entry)

    # 5. Fetch Attendance Sessions for the requested week (and target date)
    date_min = min(week_start, target_date)
    date_max = max(week_end, target_date)

    range_sessions = []
    if all_target_offering_ids:
        range_sessions = (
            AttendanceSession.query
            .options(
                joinedload(AttendanceSession.offering).joinedload(CourseOffering.course),
                joinedload(AttendanceSession.faculty).joinedload(Faculty.user),
            )
            .filter(
                AttendanceSession.offering_id.in_(all_target_offering_ids),
                AttendanceSession.session_date >= date_min,
                AttendanceSession.session_date <= date_max,
            )
            .all()
        )

    sessions_by_offering_date = defaultdict(list)
    range_session_ids = set()
    for s in range_sessions:
        range_session_ids.add(s.session_id)
        for direct_id, comp_set in offering_to_compatible_ids.items():
            if s.offering_id in comp_set:
                sessions_by_offering_date[(direct_id, s.session_date.isoformat())].append(s)

    range_records_map = {}
    if range_session_ids:
        range_records = (
            AttendanceRecord.query
            .filter(
                AttendanceRecord.student_id == student.student_id,
                AttendanceRecord.session_id.in_(range_session_ids),
            )
            .all()
        )
        for r in range_records:
            range_records_map[r.session_id] = r

    # 6. Build the Weekly Subject Attendance Matrix
    matrix_data = []
    today = date.today()

    for enrollment in enrollments:
        off = enrollment.offering
        if not off or not off.course:
            continue
        course = off.course

        faculty_name = None
        if off.faculty and off.faculty.user:
            faculty_name = off.faculty.user.name

        week_attendance = {}

        for w_day in week_days:
            d_iso = w_day["date"]
            d_obj = date.fromisoformat(d_iso)
            day_name_lower = w_day["day_name"].lower()

            tt_slots = timetable_by_offering_day.get((off.offering_id, day_name_lower), [])
            is_scheduled = len(tt_slots) > 0

            sess_list = sessions_by_offering_date.get((off.offering_id, d_iso), [])

            cell_sessions = []
            has_present = False
            has_late = False
            has_absent = False
            has_active = False

            for s in sess_list:
                rec = range_records_map.get(s.session_id)
                if s.status == "CLOSED":
                    rec_status = rec.status if rec else "ABSENT"
                elif s.status == "ACTIVE":
                    rec_status = rec.status if rec else "PENDING"
                    has_active = True
                else:
                    rec_status = rec.status if rec else "PENDING"

                if rec_status == "PRESENT":
                    has_present = True
                elif rec_status == "LATE":
                    has_late = True
                elif rec_status == "ABSENT":
                    has_absent = True

                cell_sessions.append({
                    "session_id": s.session_id,
                    "session_date": s.session_date.isoformat(),
                    "status": rec_status,
                    "session_status": s.status,
                    "start_time": s.start_time.strftime("%I:%M %p") if s.start_time else None,
                    "end_time": s.end_time.strftime("%I:%M %p") if s.end_time else None,
                    "marked_at": rec.marked_at.isoformat() if rec and rec.marked_at else None,
                })

            if len(sess_list) > 0:
                if has_present:
                    cell_status = "PRESENT"
                elif has_late:
                    cell_status = "LATE"
                elif has_absent and not has_active:
                    cell_status = "ABSENT"
                elif has_active:
                    cell_status = "PENDING"
                else:
                    cell_status = "ABSENT"
            else:
                if is_scheduled:
                    if d_obj < today:
                        cell_status = "UNRECORDED"
                    elif d_obj == today:
                        cell_status = "PENDING"
                    else:
                        cell_status = "UPCOMING"
                else:
                    cell_status = "NO_CLASS"

            week_attendance[d_iso] = {
                "date": d_iso,
                "scheduled": is_scheduled,
                "status": cell_status,
                "total_sessions": len(cell_sessions),
                "sessions": cell_sessions,
            }

        matrix_data.append({
            "offering_id": off.offering_id,
            "course_id": course.course_id,
            "course_code": course.course_code,
            "course_name": course.course_name,
            "semester": off.semester,
            "section": off.section,
            "room": off.room or "TBD",
            "faculty_name": faculty_name or "Faculty Assigned",
            "week_attendance": week_attendance,
        })

    matrix_data.sort(key=lambda x: x["course_code"])

    # 7. Today's / Selected Date Metrics & Schedule
    target_date_iso = target_date.isoformat()
    target_day_name_lower = target_date.strftime("%A").lower()

    target_tt_entries = []
    seen_entries = set()
    for enr in enrollments:
        off = enr.offering
        if not off:
            continue
        entries = timetable_by_offering_day.get((off.offering_id, target_day_name_lower), [])
        for entry in entries:
            slot_key = (entry.offering_id, entry.start_time, entry.end_time)
            if slot_key not in seen_entries:
                seen_entries.add(slot_key)
                target_tt_entries.append(entry)

    target_tt_entries.sort(key=lambda e: e.start_time)

    today_schedule = []
    now_time = datetime.now().time() if target_date == today else None

    target_sessions = [s for s in range_sessions if s.session_date == target_date]
    target_sessions_by_offering = defaultdict(list)
    for s in target_sessions:
        for direct_id, comp_set in offering_to_compatible_ids.items():
            if s.offering_id in comp_set:
                target_sessions_by_offering[direct_id].append(s)

    for entry in target_tt_entries:
        off = entry.offering
        course = off.course if off else None
        c_code = course.course_code if course else "CLASS"
        c_name = course.course_name if course else "Scheduled Class"
        f_name = off.faculty.user.name if (off and off.faculty and off.faculty.user) else None

        st_str = datetime.combine(target_date, entry.start_time).strftime("%I:%M %p")
        et_str = datetime.combine(target_date, entry.end_time).strftime("%I:%M %p")

        matching_sessions = target_sessions_by_offering.get(off.offering_id if off else 0, [])
        att_status = "Upcoming"

        if matching_sessions:
            sess = matching_sessions[0]
            rec = range_records_map.get(sess.session_id)
            if sess.status == "CLOSED":
                if rec and rec.status == "PRESENT":
                    att_status = "Present"
                elif rec and rec.status == "LATE":
                    att_status = "Late"
                else:
                    att_status = "Absent"
            elif sess.status == "ACTIVE":
                if rec and rec.status == "PRESENT":
                    att_status = "Present"
                else:
                    att_status = "In Progress"
        else:
            if target_date < today:
                att_status = "Unrecorded"
            elif target_date == today:
                if now_time and now_time > entry.end_time:
                    att_status = "Unrecorded"
                elif now_time and entry.start_time <= now_time <= entry.end_time:
                    att_status = "In Progress"
                else:
                    att_status = "Upcoming"
            else:
                att_status = "Upcoming"

        today_schedule.append({
            "timetable_entry_id": entry.timetable_entry_id,
            "offering_id": entry.offering_id,
            "course_code": c_code,
            "course_name": c_name,
            "start_time": st_str,
            "end_time": et_str,
            "time_slot": f"{st_str} - {et_str}",
            "room": entry.room or (off.room if off else "TBD") or "TBD",
            "faculty_name": f_name or "Faculty Assigned",
            "attendance_status": att_status,
        })

    total_classes_today = len(today_schedule)
    present_today = sum(1 for item in today_schedule if item["attendance_status"] in ("Present", "Late"))
    absent_today = sum(1 for item in today_schedule if item["attendance_status"] == "Absent")

    # If sessions were held on target date without timetable entries, account for them
    for s in target_sessions:
        rec = range_records_map.get(s.session_id)
        if s.status == "CLOSED":
            if rec and rec.status in ("PRESENT", "LATE") and present_today == 0 and total_classes_today == 0:
                present_today += 1
            elif (not rec or rec.status == "ABSENT") and absent_today == 0 and total_classes_today == 0:
                absent_today += 1

    summary_cards = {
        "selected_date": target_date_iso,
        "selected_date_display": target_date.strftime("%b %d, %Y (%A)"),
        "is_today": (target_date == today),
        "present_today": present_today,
        "absent_today": absent_today,
        "total_classes_today": total_classes_today,
        "attendance_rate": overall_percentage,
    }

    week_info = {
        "start_date": week_start.isoformat(),
        "end_date": week_end.isoformat(),
        "selected_date": target_date_iso,
        "date_range_display": f"{week_start.strftime('%b %d')} – {week_end.strftime('%b %d, %Y')}",
        "days": week_days,
    }

    overall_summary = {
        "attendance_rate": overall_percentage,
        "present_percentage": present_percentage,
        "absent_percentage": absent_percentage,
        "late_percentage": late_percentage,
        "total_sessions": overall_total,
        "present_sessions": overall_present,
        "absent_sessions": overall_absent,
        "late_sessions": overall_late,
    }

    return jsonify({
        "success": True,
        "week_info": week_info,
        "summary_cards": summary_cards,
        "matrix": matrix_data,
        "today_schedule": today_schedule,
        "overall_summary": overall_summary,
    }), 200
