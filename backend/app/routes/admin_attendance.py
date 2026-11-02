import csv
from datetime import date, datetime, time, timedelta
import io
import re

from flask import Blueprint, jsonify, make_response, request
from sqlalchemy import and_, asc, case, desc, func, or_

from app.extensions import db
from app.models import (
    AttendanceRecord,
    AttendanceSession,
    Course,
    CourseOffering,
    Department,
    Faculty,
    Student,
    User,
)
from app.utils.auth import admin_required
from app.utils.academic_year import (
    canonical_academic_year,
    get_available_academic_sessions,
    get_current_academic_session,
)

admin_attendance_bp = Blueprint(
    "admin_attendance",
    __name__,
    url_prefix="/api/admin/attendance",
)


def _parse_and_validate_dates():
    from_date_raw = request.args.get("from_date")
    to_date_raw = request.args.get("to_date")
    from_d = None
    to_d = None

    if from_date_raw and from_date_raw.strip():
        try:
            from_d = date.fromisoformat(from_date_raw.strip())
        except ValueError:
            return None, None, (
                jsonify({
                    "success": False,
                    "message": "from_date must be in YYYY-MM-DD format",
                }),
                400,
            )

    if to_date_raw and to_date_raw.strip():
        try:
            to_d = date.fromisoformat(to_date_raw.strip())
        except ValueError:
            return None, None, (
                jsonify({
                    "success": False,
                    "message": "to_date must be in YYYY-MM-DD format",
                }),
                400,
            )

    if from_d and to_d and from_d > to_d:
        return None, None, (
            jsonify({
                "success": False,
                "message": "from_date cannot be later than to_date",
            }),
            400,
        )

    return from_d, to_d, None


def _build_session_filter(query, from_d=None, to_d=None):
    academic_year = request.args.get("academic_year")
    semester = request.args.get("semester")
    section = request.args.get("section")
    course_id = request.args.get("course_id")
    faculty_id = request.args.get("faculty_id")

    if academic_year and academic_year not in ["All", "all", ""]:
        canon_ay = canonical_academic_year(academic_year)
        clean_ay = academic_year.replace(" ", "")
        canon_clean = canon_ay.replace(" ", "") if canon_ay else clean_ay
        m = re.match(r"^(\d{4})-(\d{4})$", canon_ay) if canon_ay else None
        short_ay = f"{m.group(1)}-{m.group(2)[2:]}" if m else None

        filters = [
            CourseOffering.academic_year == academic_year,
            CourseOffering.academic_year == canon_ay,
            func.replace(CourseOffering.academic_year, " ", "") == clean_ay,
            func.replace(CourseOffering.academic_year, " ", "") == canon_clean,
        ]
        if short_ay:
            filters.append(CourseOffering.academic_year == short_ay)
            filters.append(func.replace(CourseOffering.academic_year, " ", "") == short_ay)

        query = query.filter(or_(*filters))

    if semester and semester not in ["All", "all", ""]:
        try:
            sem_int = int(semester)
            query = query.filter(CourseOffering.semester == sem_int)
        except ValueError:
            pass

    if section and section not in ["All", "all", ""]:
        clean_sec = section.strip()
        query = query.filter(
            or_(
                CourseOffering.section == section,
                func.trim(CourseOffering.section).ilike(clean_sec),
            )
        )

    if course_id and course_id not in ["All", "all", ""]:
        try:
            cid = int(course_id)
            query = query.filter(CourseOffering.course_id == cid)
        except ValueError:
            pass

    if faculty_id and faculty_id not in ["All", "all", ""]:
        try:
            fid = int(faculty_id)
            query = query.filter(AttendanceSession.faculty_id == fid)
        except ValueError:
            pass

    if from_d:
        query = query.filter(AttendanceSession.session_date >= from_d)

    if to_d:
        query = query.filter(AttendanceSession.session_date <= to_d)

    return query


# =========================================================================
# FILTER OPTIONS
# =========================================================================
@admin_attendance_bp.get("/filter-options")
@admin_required
def get_attendance_filter_options():
    # 1. Distinct academic sessions (1-year sessions)
    academic_years = get_available_academic_sessions()

    # 2. Distinct semesters from both offerings and student profiles
    off_sems = db.session.query(CourseOffering.semester).filter(CourseOffering.semester.isnot(None)).distinct().all()
    stu_sems = db.session.query(Student.semester).filter(Student.semester.isnot(None)).distinct().all()
    all_sem_set = {s[0] for s in off_sems if s[0] is not None} | {s[0] for s in stu_sems if s[0] is not None}
    semesters = sorted([int(s) for s in all_sem_set if isinstance(s, (int, str)) and str(s).isdigit()])

    # 3. Semester-to-sections mapping for dynamic contextual filtering
    sem_sec_mapping = {}
    off_sem_secs = (
        db.session.query(CourseOffering.semester, CourseOffering.section)
        .filter(CourseOffering.semester.isnot(None), CourseOffering.section.isnot(None))
        .distinct()
        .all()
    )
    for sem, sec in off_sem_secs:
        if sec and sec.strip():
            sem_sec_mapping.setdefault(str(sem), set()).add(sec.strip())

    stu_sem_secs = (
        db.session.query(Student.semester, Student.section)
        .filter(Student.semester.isnot(None), Student.section.isnot(None))
        .distinct()
        .all()
    )
    for sem, sec in stu_sem_secs:
        if sec and sec.strip():
            sem_sec_mapping.setdefault(str(sem), set()).add(sec.strip())

    semester_sections = {
        k: sorted(list(v)) for k, v in sem_sec_mapping.items()
    }

    # Distinct sections across all data
    raw_secs = set()
    for v in sem_sec_mapping.values():
        raw_secs.update(v)
    all_off_secs = db.session.query(CourseOffering.section).filter(CourseOffering.section.isnot(None)).distinct().all()
    raw_secs.update({s[0].strip() for s in all_off_secs if s[0] and s[0].strip()})
    all_stu_secs = db.session.query(Student.section).filter(Student.section.isnot(None)).distinct().all()
    raw_secs.update({s[0].strip() for s in all_stu_secs if s[0] and s[0].strip()})

    std_secs = [s for s in ["A", "B", "C", "D"] if s in raw_secs]
    other_secs = sorted([s for s in raw_secs if s not in std_secs])
    sections = std_secs + other_secs

    # Optional: if client requested filter options specifically for a semester
    req_sem = request.args.get("semester")
    if req_sem and req_sem not in ["All", "all", ""]:
        s_key = str(req_sem)
        if s_key in semester_sections:
            sem_specific_secs = set(semester_sections[s_key])
            std_s = [s for s in ["A", "B", "C", "D"] if s in sem_specific_secs]
            other_s = sorted([s for s in sem_specific_secs if s not in std_s])
            sections = std_s + other_s

    # 4. Courses
    courses_raw = (
        db.session.query(Course.course_id, Course.course_code, Course.course_name)
        .join(CourseOffering, CourseOffering.course_id == Course.course_id)
        .distinct()
        .order_by(Course.course_code.asc())
        .all()
    )
    courses = [
        {
            "course_id": c[0],
            "course_code": c[1],
            "course_name": c[2],
        }
        for c in courses_raw
    ]

    # 5. Faculty
    faculties_raw = (
        db.session.query(Faculty.faculty_id, User.name, Faculty.employee_id)
        .join(User, Faculty.user_id == User.user_id)
        .order_by(User.name.asc())
        .all()
    )
    faculty = [
        {
            "faculty_id": f[0],
            "name": f[1],
            "employee_id": f[2],
        }
        for f in faculties_raw
    ]

    # 6. Min and Max Dates from sessions
    min_date = db.session.query(func.min(AttendanceSession.session_date)).scalar()
    max_date = db.session.query(func.max(AttendanceSession.session_date)).scalar()
    today_iso = date.today().isoformat()

    return jsonify({
        "success": True,
        "academic_years": academic_years,
        "semesters": semesters,
        "sections": sections,
        "semester_sections": semester_sections,
        "courses": courses,
        "faculty": faculty,
        "date_range": {
            "from_date": min_date.isoformat() if min_date else today_iso,
            "to_date": max_date.isoformat() if max_date else today_iso,
        },
    }), 200


# =========================================================================
# DASHBOARD / ANALYTICS
# =========================================================================
@admin_attendance_bp.get("/dashboard")
@admin_required
def get_attendance_dashboard():
    from_d, to_d, err = _parse_and_validate_dates()
    if err:
        return err

    # 1. Base query for sessions
    base_session_q = (
        db.session.query(AttendanceSession.session_id)
        .join(CourseOffering, AttendanceSession.offering_id == CourseOffering.offering_id)
        .join(Course, CourseOffering.course_id == Course.course_id)
    )
    filtered_session_q = _build_session_filter(base_session_q, from_d=from_d, to_d=to_d)
    session_rows = filtered_session_q.all()
    session_ids = [r[0] for r in session_rows]

    if not session_ids:
        return jsonify({
            "success": True,
            "kpi": {
                "total_present": 0,
                "total_absent": 0,
                "total_classes": 0,
                "attendance_rate": 0.0,
                "present_rate": 0.0,
                "absent_rate": 0.0,
                "present_trend": None,
                "absent_trend": None,
                "classes_trend": None,
                "rate_trend": None,
            },
            "trend": [],
            "by_course": [],
            "by_section": [],
        }), 200

    # 2. KPI metrics
    present_count = (
        db.session.query(func.count(AttendanceRecord.attendance_id))
        .filter(
            AttendanceRecord.session_id.in_(session_ids),
            AttendanceRecord.status.in_(["PRESENT", "LATE"]),
        )
        .scalar()
        or 0
    )
    absent_count = (
        db.session.query(func.count(AttendanceRecord.attendance_id))
        .filter(
            AttendanceRecord.session_id.in_(session_ids),
            AttendanceRecord.status == "ABSENT",
        )
        .scalar()
        or 0
    )
    total_records = present_count + absent_count
    total_classes = len(session_ids)
    overall_rate = round((present_count / total_records * 100), 1) if total_records > 0 else 0.0
    present_rate = round((present_count / total_records * 100), 1) if total_records > 0 else 0.0
    absent_rate = round((absent_count / total_records * 100), 1) if total_records > 0 else 0.0

    # 3. Attendance Trend over time
    date_stats = (
        db.session.query(
            AttendanceSession.session_date,
            func.sum(case((AttendanceRecord.status.in_(["PRESENT", "LATE"]), 1), else_=0)).label("present"),
            func.count(AttendanceRecord.attendance_id).label("total"),
        )
        .join(AttendanceRecord, AttendanceRecord.session_id == AttendanceSession.session_id)
        .filter(AttendanceSession.session_id.in_(session_ids))
        .group_by(AttendanceSession.session_date)
        .order_by(AttendanceSession.session_date.asc())
        .all()
    )

    trend = []
    # If more than 30 dates, sample approx 25 evenly spaced points to keep SVG clear
    if len(date_stats) > 30:
        step = max(1, len(date_stats) // 25)
        sampled_indices = [i * step for i in range(25)]
        if (len(date_stats) - 1) not in sampled_indices:
            sampled_indices[-1] = len(date_stats) - 1
        selected_stats = [date_stats[i] for i in sampled_indices if i < len(date_stats)]
    else:
        selected_stats = date_stats

    for row in selected_stats:
        sdate = row[0]
        p = int(row[1] or 0)
        tot = int(row[2] or 0)
        rate = round((p / tot * 100), 1) if tot > 0 else 0.0
        trend.append({
            "date": sdate.isoformat(),
            "label": sdate.strftime("%b %d"),
            "rate": rate,
            "present": p,
            "total": tot,
        })

    # 4. Attendance by Course
    course_stats = (
        db.session.query(
            Course.course_id,
            Course.course_code,
            Course.course_name,
            func.sum(case((AttendanceRecord.status.in_(["PRESENT", "LATE"]), 1), else_=0)).label("present"),
            func.count(AttendanceRecord.attendance_id).label("total"),
            func.count(func.distinct(AttendanceSession.session_id)).label("classes"),
        )
        .join(CourseOffering, CourseOffering.course_id == Course.course_id)
        .join(AttendanceSession, AttendanceSession.offering_id == CourseOffering.offering_id)
        .outerjoin(AttendanceRecord, AttendanceRecord.session_id == AttendanceSession.session_id)
        .filter(AttendanceSession.session_id.in_(session_ids))
        .group_by(Course.course_id, Course.course_code, Course.course_name)
        .order_by(desc("classes"), desc("total"))
        .all()
    )

    palette = ["#2563eb", "#0ea5e9", "#6366f1", "#f97316", "#10b981", "#64748b", "#ec4899", "#8b5cf6"]
    by_course = []
    top_courses = course_stats[:5]
    other_courses = course_stats[5:]

    for idx, row in enumerate(top_courses):
        p = int(row[3] or 0)
        tot = int(row[4] or 0)
        cls_count = int(row[5] or 0)
        rate = round((p / tot * 100), 1) if tot > 0 else 0.0
        by_course.append({
            "course_id": row[0],
            "course_code": row[1],
            "course_name": row[2],
            "rate": rate,
            "present": p,
            "total": tot,
            "classes": cls_count,
            "color": palette[idx % len(palette)],
        })

    if other_courses:
        other_p = sum(int(r[3] or 0) for r in other_courses)
        other_tot = sum(int(r[4] or 0) for r in other_courses)
        other_cls = sum(int(r[5] or 0) for r in other_courses)
        other_rate = round((other_p / other_tot * 100), 1) if other_tot > 0 else 0.0
        by_course.append({
            "course_id": 0,
            "course_code": "OTH",
            "course_name": "Others",
            "rate": other_rate,
            "present": other_p,
            "total": other_tot,
            "classes": other_cls,
            "color": palette[5],
        })

    # 5. Attendance by Section
    section_stats = (
        db.session.query(
            CourseOffering.section,
            func.sum(case((AttendanceRecord.status.in_(["PRESENT", "LATE"]), 1), else_=0)).label("present"),
            func.count(AttendanceRecord.attendance_id).label("total"),
        )
        .join(AttendanceSession, AttendanceSession.offering_id == CourseOffering.offering_id)
        .outerjoin(AttendanceRecord, AttendanceRecord.session_id == AttendanceSession.session_id)
        .filter(AttendanceSession.session_id.in_(session_ids))
        .group_by(CourseOffering.section)
        .all()
    )

    sec_palette = {
        "A": "#2563eb",
        "B": "#0ea5e9",
        "C": "#14b8a6",
        "D": "#8b5cf6",
    }
    by_section = []
    sec_dict = {row[0]: row for row in section_stats}
    sorted_sec_names = [s for s in ["A", "B", "C", "D"] if s in sec_dict]
    remaining_secs = sorted([s for s in sec_dict if s not in sorted_sec_names])
    final_secs = sorted_sec_names + remaining_secs

    for s_name in final_secs:
        row = sec_dict[s_name]
        p = int(row[1] or 0)
        tot = int(row[2] or 0)
        rate = round((p / tot * 100), 1) if tot > 0 else 0.0
        by_section.append({
            "section": s_name,
            "rate": rate,
            "present": p,
            "total": tot,
            "color": sec_palette.get(s_name, "#3b82f6"),
        })

    return jsonify({
        "success": True,
        "kpi": {
            "total_present": present_count,
            "total_absent": absent_count,
            "total_classes": total_classes,
            "attendance_rate": overall_rate,
            "present_rate": present_rate,
            "absent_rate": absent_rate,
            "present_trend": None,
            "absent_trend": None,
            "classes_trend": None,
            "rate_trend": None,
        },
        "trend": trend,
        "by_course": by_course,
        "by_section": by_section,
    }), 200


# =========================================================================
# ATTENDANCE RECORDS (PAGINATED & SEARCHABLE)
# =========================================================================
@admin_attendance_bp.get("/records")
@admin_required
def get_admin_attendance_records_list():
    from_d, to_d, err = _parse_and_validate_dates()
    if err:
        return err

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 5, type=int)
    search = request.args.get("search", "").strip()
    status_filter = request.args.get("status")

    if page < 1:
        page = 1
    if per_page < 1 or per_page > 100:
        per_page = 5

    query = (
        db.session.query(
            AttendanceRecord,
            AttendanceSession,
            CourseOffering,
            Course,
            Student,
            User,
        )
        .join(AttendanceSession, AttendanceRecord.session_id == AttendanceSession.session_id)
        .join(CourseOffering, AttendanceSession.offering_id == CourseOffering.offering_id)
        .join(Course, CourseOffering.course_id == Course.course_id)
        .join(Student, AttendanceRecord.student_id == Student.student_id)
        .join(User, Student.user_id == User.user_id)
    )

    query = _build_session_filter(query, from_d=from_d, to_d=to_d)

    if status_filter and status_filter not in ["All", "all", ""]:
        query = query.filter(AttendanceRecord.status == status_filter.upper())

    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                User.name.ilike(search_pattern),
                Student.enrollment_no.ilike(search_pattern),
                Course.course_code.ilike(search_pattern),
                Course.course_name.ilike(search_pattern),
                CourseOffering.section.ilike(search_pattern),
            )
        )

    total_records = query.count()
    total_pages = max(1, (total_records + per_page - 1) // per_page)

    records = (
        query
        .order_by(
            AttendanceSession.session_date.desc(),
            AttendanceRecord.marked_at.desc(),
            AttendanceRecord.attendance_id.desc(),
        )
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    data = []
    for rec, sess, off, crs, stu, usr in records:
        st = (rec.status or "").upper()
        if st == "PRESENT":
            status_display = "Present"
        elif st == "LATE":
            status_display = "Late"
        else:
            status_display = "Absent"
        is_attended = st in ("PRESENT", "LATE")

        marked_time_str = (
            rec.marked_at.strftime("%I:%M %p")
            if (is_attended and rec.marked_at)
            else "-"
        )
        method_str = (
            "Face Recognition"
            if rec.recognition_method == "FACE"
            else ("Manual" if is_attended else "-")
        )
        conf_str = (
            f"{rec.confidence_score:.1f}%"
            if (is_attended and rec.confidence_score is not None)
            else "-"
        )

        sem_val = off.semester if (off and off.semester is not None) else (stu.semester if stu else None)
        sec_val = off.section.strip() if (off and off.section) else (stu.section.strip() if (stu and stu.section) else None)

        if sem_val is not None and sec_val:
            sem_sec_display = f"Semester {sem_val} / Section {sec_val}"
        elif sem_val is not None:
            sem_sec_display = f"Semester {sem_val} / Section N/A"
        elif sec_val:
            sem_sec_display = f"N/A / Section {sec_val}"
        else:
            sem_sec_display = "N/A"

        data.append({
            "attendance_id": rec.attendance_id,
            "session_id": sess.session_id,
            "student_id": stu.student_id,
            "date": sess.session_date.strftime("%b %d, %Y"),
            "raw_date": sess.session_date.isoformat(),
            "student_name": usr.name,
            "roll_no": stu.enrollment_no,
            "course_code": crs.course_code,
            "course_name": crs.course_name,
            "semester": sem_val,
            "section": sec_val or "N/A",
            "semester_section": sem_sec_display,
            "status": status_display,
            "marked_at": marked_time_str,
            "method": method_str,
            "confidence_score": conf_str,
            "confidence_raw": rec.confidence_score,
        })

    return jsonify({
        "success": True,
        "page": page,
        "per_page": per_page,
        "total_records": total_records,
        "total_pages": total_pages,
        "data": data,
    }), 200


# =========================================================================
# SINGLE RECORD DETAIL FOR MODAL VIEW
# =========================================================================
@admin_attendance_bp.get("/records/<int:attendance_id>")
@admin_required
def get_single_attendance_record(attendance_id):
    item = (
        db.session.query(
            AttendanceRecord,
            AttendanceSession,
            CourseOffering,
            Course,
            Student,
            User,
        )
        .join(AttendanceSession, AttendanceRecord.session_id == AttendanceSession.session_id)
        .join(CourseOffering, AttendanceSession.offering_id == CourseOffering.offering_id)
        .join(Course, CourseOffering.course_id == Course.course_id)
        .join(Student, AttendanceRecord.student_id == Student.student_id)
        .join(User, Student.user_id == User.user_id)
        .filter(AttendanceRecord.attendance_id == attendance_id)
        .first()
    )

    if not item:
        return jsonify({
            "success": False,
            "message": "Attendance record not found",
        }), 404

    rec, sess, off, crs, stu, usr = item
    faculty_user = sess.faculty.user if (sess.faculty and sess.faculty.user) else None

    st = (rec.status or "").upper()
    status_display = "Present" if st == "PRESENT" else ("Late" if st == "LATE" else "Absent")

    sem_val = off.semester if (off and off.semester is not None) else (stu.semester if stu else None)
    sec_val = off.section.strip() if (off and off.section) else (stu.section.strip() if (stu and stu.section) else None)

    if sem_val is not None and sec_val:
        sem_sec_display = f"Semester {sem_val} / Section {sec_val}"
    elif sem_val is not None:
        sem_sec_display = f"Semester {sem_val} / Section N/A"
    elif sec_val:
        sem_sec_display = f"N/A / Section {sec_val}"
    else:
        sem_sec_display = "N/A"

    return jsonify({
        "success": True,
        "data": {
            "attendance_id": rec.attendance_id,
            "status": status_display,
            "marked_at": rec.marked_at.strftime("%I:%M:%S %p") if rec.marked_at else None,
            "confidence_score": rec.confidence_score,
            "recognition_method": rec.recognition_method,
            "semester": sem_val,
            "section": sec_val or "N/A",
            "semester_section": sem_sec_display,
            "student": {
                "student_id": stu.student_id,
                "name": usr.name,
                "email": usr.email,
                "enrollment_no": stu.enrollment_no,
                "section": sec_val or "N/A",
                "semester": sem_val if sem_val is not None else "N/A",
                "semester_section": sem_sec_display,
                "academic_year": off.academic_year if off else getattr(stu, "academic_year", "N/A"),
            },
            "session": {
                "session_id": sess.session_id,
                "date": sess.session_date.strftime("%B %d, %Y"),
                "time": f"{sess.start_time.strftime('%I:%M %p')} - {sess.end_time.strftime('%I:%M %p') if sess.end_time else 'N/A'}",
                "room": off.room or "Standard Classroom",
                "status": sess.status,
            },
            "course": {
                "course_id": crs.course_id,
                "course_code": crs.course_code,
                "course_name": crs.course_name,
            },
            "faculty": {
                "faculty_id": sess.faculty_id,
                "name": faculty_user.name if faculty_user else "Assigned Faculty",
                "employee_id": sess.faculty.employee_id if sess.faculty else None,
            },
        },
    }), 200


def _sanitize_csv_cell(val):
    if val is None:
        return ""
    s = str(val)
    if s and s[0] in ("=", "+", "-", "@", "\t", "\r"):
        return f"'{s}"
    return s


# =========================================================================
# EXPORT ATTENDANCE REPORT AS CSV
# =========================================================================
@admin_attendance_bp.get("/export")
@admin_required
def export_attendance_records():
    from_d, to_d, err = _parse_and_validate_dates()
    if err:
        return err

    search = request.args.get("search", "").strip()
    status_filter = request.args.get("status")

    query = (
        db.session.query(
            AttendanceRecord,
            AttendanceSession,
            CourseOffering,
            Course,
            Student,
            User,
        )
        .join(AttendanceSession, AttendanceRecord.session_id == AttendanceSession.session_id)
        .join(CourseOffering, AttendanceSession.offering_id == CourseOffering.offering_id)
        .join(Course, CourseOffering.course_id == Course.course_id)
        .join(Student, AttendanceRecord.student_id == Student.student_id)
        .join(User, Student.user_id == User.user_id)
    )

    query = _build_session_filter(query, from_d=from_d, to_d=to_d)

    if status_filter and status_filter not in ["All", "all", ""]:
        query = query.filter(AttendanceRecord.status == status_filter.upper())

    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                User.name.ilike(search_pattern),
                Student.enrollment_no.ilike(search_pattern),
                Course.course_code.ilike(search_pattern),
                Course.course_name.ilike(search_pattern),
                CourseOffering.section.ilike(search_pattern),
            )
        )

    records = (
        query
        .order_by(
            AttendanceSession.session_date.desc(),
            AttendanceRecord.marked_at.desc(),
            AttendanceRecord.attendance_id.desc(),
        )
        .all()
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Date",
        "Student Name",
        "Roll No.",
        "Course Code",
        "Course Name",
        "Semester / Section",
        "Status",
        "Marked At",
        "Method",
        "Confidence Score",
    ])

    for rec, sess, off, crs, stu, usr in records:
        st = (rec.status or "").upper()
        if st == "PRESENT":
            status_display = "Present"
        elif st == "LATE":
            status_display = "Late"
        else:
            status_display = "Absent"
        is_attended = st in ("PRESENT", "LATE")

        sem_val = off.semester if (off and off.semester is not None) else (stu.semester if stu else None)
        sec_val = off.section.strip() if (off and off.section) else (stu.section.strip() if (stu and stu.section) else None)

        if sem_val is not None and sec_val:
            sem_sec_display = f"Semester {sem_val} / Section {sec_val}"
        elif sem_val is not None:
            sem_sec_display = f"Semester {sem_val} / Section N/A"
        elif sec_val:
            sem_sec_display = f"N/A / Section {sec_val}"
        else:
            sem_sec_display = "N/A"

        writer.writerow([
            sess.session_date.strftime("%Y-%m-%d"),
            _sanitize_csv_cell(usr.name),
            _sanitize_csv_cell(stu.enrollment_no),
            _sanitize_csv_cell(crs.course_code),
            _sanitize_csv_cell(crs.course_name),
            sem_sec_display,
            status_display,
            rec.marked_at.strftime("%I:%M %p") if (is_attended and rec.marked_at) else "-",
            "Face Recognition" if rec.recognition_method == "FACE" else ("Manual" if is_attended else "-"),
            f"{rec.confidence_score:.1f}%" if (is_attended and rec.confidence_score is not None) else "-",
        ])


    csv_data = output.getvalue()
    response = make_response(csv_data)
    response.headers["Content-Disposition"] = "attachment; filename=attendance_report.csv"
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    return response


# =========================================================================
# LEGACY SESSION ENDPOINTS (Preserved for compatibility)
# =========================================================================
@admin_attendance_bp.get("/sessions")
@admin_required
def get_attendance_sessions():
    status = request.args.get("status")
    offering_id = request.args.get("offering_id", type=int)
    faculty_id = request.args.get("faculty_id", type=int)
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

    query = AttendanceSession.query

    if status:
        if status not in {"ACTIVE", "CLOSED"}:
            return jsonify({
                "success": False,
                "message": "status must be ACTIVE or CLOSED",
            }), 400
        query = query.filter(AttendanceSession.status == status)

    if offering_id is not None:
        query = query.filter(AttendanceSession.offering_id == offering_id)

    if faculty_id is not None:
        query = query.filter(AttendanceSession.faculty_id == faculty_id)

    if from_date:
        query = query.filter(AttendanceSession.session_date >= from_date)

    if to_date:
        query = query.filter(AttendanceSession.session_date <= to_date)

    sessions = (
        query
        .order_by(
            AttendanceSession.session_date.desc(),
            AttendanceSession.session_id.desc(),
        )
        .all()
    )

    data = []
    for session in sessions:
        offering = session.offering
        data.append({
            "session_id": session.session_id,
            "offering_id": session.offering_id,
            "faculty_id": session.faculty_id,
            "session_date": session.session_date.isoformat(),
            "start_time": session.start_time.isoformat(),
            "end_time": session.end_time.isoformat() if session.end_time else None,
            "status": session.status,
            "created_at": session.created_at.isoformat(),
            "course": {
                "course_id": offering.course.course_id,
                "course_code": offering.course.course_code,
                "course_name": offering.course.course_name,
            },
            "offering": {
                "academic_year": offering.academic_year,
                "semester": offering.semester,
                "section": offering.section,
                "room": offering.room,
            },
            "attendance_count": len(session.attendance_records),
        })

    return jsonify({
        "success": True,
        "count": len(data),
        "data": data,
    }), 200


@admin_attendance_bp.get("/sessions/<int:session_id>")
@admin_required
def get_attendance_session(session_id):
    session = db.session.get(AttendanceSession, session_id)
    if not session:
        return jsonify({
            "success": False,
            "message": "Attendance session not found",
        }), 404

    offering = session.offering
    return jsonify({
        "success": True,
        "data": {
            "session_id": session.session_id,
            "offering_id": session.offering_id,
            "faculty_id": session.faculty_id,
            "session_date": session.session_date.isoformat(),
            "start_time": session.start_time.isoformat(),
            "end_time": session.end_time.isoformat() if session.end_time else None,
            "status": session.status,
            "created_at": session.created_at.isoformat(),
            "course": {
                "course_id": offering.course.course_id,
                "course_code": offering.course.course_code,
                "course_name": offering.course.course_name,
            },
            "offering": {
                "academic_year": offering.academic_year,
                "semester": offering.semester,
                "section": offering.section,
                "room": offering.room,
            },
            "attendance_count": len(session.attendance_records),
        },
    }), 200


@admin_attendance_bp.get("/sessions/<int:session_id>/records")
@admin_required
def get_attendance_records(session_id):
    session = db.session.get(AttendanceSession, session_id)
    if not session:
        return jsonify({
            "success": False,
            "message": "Attendance session not found",
        }), 404

    records = (
        AttendanceRecord.query
        .filter_by(session_id=session_id)
        .order_by(AttendanceRecord.marked_at.asc())
        .all()
    )

    data = []
    for record in records:
        student = record.student
        data.append({
            "attendance_id": record.attendance_id,
            "student_id": record.student_id,
            "student": {
                "student_id": student.student_id,
                "name": student.user.name,
                "enrollment_no": student.enrollment_no,
            },
            "status": record.status,
            "marked_at": record.marked_at.isoformat(),
            "confidence_score": record.confidence_score,
            "recognition_method": record.recognition_method,
        })

    return jsonify({
        "success": True,
        "session_id": session_id,
        "count": len(data),
        "data": data,
    }), 200
