from datetime import datetime, date
import re
from flask import Blueprint, jsonify, request, send_file
from flask_jwt_extended import get_jwt_identity

from sqlalchemy.orm import joinedload, selectinload

from app.extensions import db, bcrypt
from app.models import (
    Faculty,
    CourseOffering,
    Enrollment,
    Student,
    User,
    Department,
    AttendanceRecord,
    AttendanceSession,
    FacultyAdjustment,
    TimetableEntry,
)
from app.utils.academic_year import (
    are_offerings_academically_compatible,
    canonical_academic_year,
    resolve_student_academic_info,
    resolve_offering_academic_year,
)
from app.utils.auth import faculty_required, faculty_or_admin_required
from app.utils.export_engine import (
    ExportRenderingError,
    ExportValidationError,
    generate_export,
)


faculty_bp = Blueprint(
    "faculty",
    __name__,
    url_prefix="/api/faculty",
)


def get_current_faculty():
    identity = get_jwt_identity()
    if not identity:
        return None
    try:
        user_id = int(identity)
    except (TypeError, ValueError):
        return None

    return Faculty.query.filter_by(user_id=user_id).first()


def serialize_faculty_profile(faculty):
    return {
        "faculty_id": faculty.faculty_id,
        "user_id": faculty.user_id,
        "name": faculty.user.name,
        "email": faculty.user.email,
        "employee_id": faculty.employee_id,
        "designation": faculty.designation,
        "phone": faculty.phone or "",
        "gender": faculty.gender or "",
        "date_of_birth": faculty.date_of_birth or "",
        "date_of_joining": faculty.date_of_joining or "",
        "employment_status": faculty.employment_status or "Permanent",
        "qualification": faculty.qualification or "",
        "specialization": faculty.specialization or "",
        "office_cabin": faculty.office_cabin or "",
        "address": faculty.address or "",
        "city": faculty.city or "",
        "state": faculty.state or "",
        "pin_code": faculty.pin_code or "",
        "country": faculty.country or "India",
        "account_status": "Active" if getattr(faculty.user, "is_active", True) else "Inactive",
        "department": {
            "department_id": faculty.department.department_id if faculty.department else None,
            "department_name": faculty.department.department_name if faculty.department else "Department",
            "department_code": faculty.department.department_code if faculty.department else "N/A",
        },
    }


@faculty_bp.get("/dashboard")
@faculty_or_admin_required
def faculty_dashboard():
    faculty = get_current_faculty()
    if not faculty:
        return jsonify({
            "success": False,
            "message": "Faculty profile not found. Please contact administration.",
        }), 404

    from app.routes.attendance import serialize_session

    offerings = (
        CourseOffering.query
        .filter_by(faculty_id=faculty.faculty_id)
        .order_by(CourseOffering.offering_id.asc())
        .all()
    )
    assigned_courses_count = len(offerings)

    # Today's classes
    local_now = datetime.now()
    today_weekday = local_now.strftime("%A")

    substitute_entry_ids = [
        adj.timetable_entry_id
        for adj in FacultyAdjustment.query.filter_by(
            substitute_faculty_id=faculty.faculty_id,
            status="APPROVED",
        ).all()
    ]

    tt_query = TimetableEntry.query.join(CourseOffering).filter(
        db.or_(
            CourseOffering.faculty_id == faculty.faculty_id,
            TimetableEntry.timetable_entry_id.in_(substitute_entry_ids),
        ) if substitute_entry_ids else (CourseOffering.faculty_id == faculty.faculty_id)
    )
    todays_entries = tt_query.filter(
        db.func.lower(TimetableEntry.day_of_week) == today_weekday.lower()
    ).order_by(TimetableEntry.start_time.asc()).all()
    todays_classes_count = len(todays_entries)

    # Active session
    active_session = (
        AttendanceSession.query
        .filter_by(faculty_id=faculty.faculty_id, status="ACTIVE")
        .order_by(AttendanceSession.session_id.desc())
        .first()
    )

    # Attendance statistics across closed sessions
    closed_sessions = (
        AttendanceSession.query
        .filter_by(faculty_id=faculty.faculty_id, status="CLOSED")
        .order_by(AttendanceSession.session_date.desc(), AttendanceSession.session_id.desc())
        .all()
    )
    closed_session_ids = [s.session_id for s in closed_sessions]
    closed_sessions_count = len(closed_session_ids)

    total_present = 0
    total_absent = 0
    if closed_session_ids:
        total_present = (
            AttendanceRecord.query
            .filter(
                AttendanceRecord.session_id.in_(closed_session_ids),
                AttendanceRecord.status.in_(["PRESENT", "LATE"]),
            )
            .count()
        )
        total_absent = (
            AttendanceRecord.query
            .filter(
                AttendanceRecord.session_id.in_(closed_session_ids),
                AttendanceRecord.status == "ABSENT",
            )
            .count()
        )

    total_possible = total_present + total_absent
    average_attendance_percentage = (
        round((total_present / total_possible) * 100, 2)
        if total_possible > 0
        else None
    )

    recent_sessions = [
        serialize_session(s)
        for s in closed_sessions[:5]
    ]

    return jsonify({
        "success": True,
        "message": "Faculty dashboard data retrieved successfully",
        "data": {
            "role": "FACULTY",
            "faculty_id": faculty.faculty_id,
            "faculty_name": faculty.user.name if faculty.user else None,
            "employee_id": faculty.employee_id,
            "assigned_courses_count": assigned_courses_count,
            "todays_classes_count": todays_classes_count,
            "active_sessions_count": 1 if active_session else 0,
            "has_active_session": bool(active_session),
            "active_session": serialize_session(active_session) if active_session else None,
            "average_attendance_percentage": average_attendance_percentage,
            "has_attendance_history": closed_sessions_count > 0,
            "attendance_overview": {
                "present": total_present,
                "absent": total_absent,
                "closed_sessions": closed_sessions_count,
                "attendance_percentage": average_attendance_percentage,
                "has_history": closed_sessions_count > 0,
            },
            "recent_sessions": recent_sessions,
        },
    }), 200


# ============================================================
# GET FACULTY PROFILE
# ============================================================

@faculty_bp.get("/profile")
@faculty_or_admin_required
def get_faculty_profile():
    faculty = get_current_faculty()

    if not faculty:
        return jsonify({
            "success": False,
            "message": "Faculty profile not found. Please contact administration.",
        }), 404

    return jsonify({
        "success": True,
        "data": serialize_faculty_profile(faculty),
    }), 200


# ============================================================
# UPDATE FACULTY PROFILE
# ============================================================

@faculty_bp.patch("/profile")
@faculty_or_admin_required
def update_faculty_profile():
    faculty = get_current_faculty()

    if not faculty:
        return jsonify({
            "success": False,
            "message": "Faculty profile not found. Please contact administration.",
        }), 404

    data = request.get_json(silent=True) or {}

    # Basic User fields
    name = data.get("name")
    email = data.get("email")

    if name is not None:
        name = str(name).strip()
        if not name:
            return jsonify({
                "success": False,
                "message": "Name cannot be empty",
            }), 400
        faculty.user.name = name

    if email is not None:
        email = str(email).strip().lower()
        if not email:
            return jsonify({
                "success": False,
                "message": "Email cannot be empty",
            }), 400

        existing_user = (
            User.query
            .filter(
                User.email == email,
                User.user_id != faculty.user_id,
            )
            .first()
        )
        if existing_user:
            return jsonify({
                "success": False,
                "message": "Email is already in use",
            }), 409

        faculty.user.email = email

    # Profile & Academic fields
    if "designation" in data and data["designation"] is not None:
        faculty.designation = str(data["designation"]).strip()

    if "phone" in data:
        faculty.phone = str(data["phone"]).strip() if data["phone"] is not None else None

    if "gender" in data:
        faculty.gender = str(data["gender"]).strip() if data["gender"] is not None else None

    if "date_of_birth" in data:
        faculty.date_of_birth = str(data["date_of_birth"]).strip() if data["date_of_birth"] is not None else None

    if "date_of_joining" in data:
        faculty.date_of_joining = str(data["date_of_joining"]).strip() if data["date_of_joining"] is not None else None

    if "employment_status" in data:
        faculty.employment_status = str(data["employment_status"]).strip() if data["employment_status"] is not None else "Permanent"

    if "qualification" in data:
        faculty.qualification = str(data["qualification"]).strip() if data["qualification"] is not None else None

    if "specialization" in data:
        faculty.specialization = str(data["specialization"]).strip() if data["specialization"] is not None else None

    if "office_cabin" in data:
        faculty.office_cabin = str(data["office_cabin"]).strip() if data["office_cabin"] is not None else None

    # Location & Contact fields
    if "address" in data:
        faculty.address = str(data["address"]).strip() if data["address"] is not None else None

    if "city" in data:
        faculty.city = str(data["city"]).strip() if data["city"] is not None else None

    if "state" in data:
        faculty.state = str(data["state"]).strip() if data["state"] is not None else None

    if "pin_code" in data:
        faculty.pin_code = str(data["pin_code"]).strip() if data["pin_code"] is not None else None

    if "country" in data:
        faculty.country = str(data["country"]).strip() if data["country"] is not None else "India"

    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Faculty profile updated successfully",
        "data": serialize_faculty_profile(faculty),
    }), 200


# ============================================================
# CHANGE FACULTY PASSWORD
# ============================================================

@faculty_bp.post("/change-password")
@faculty_or_admin_required
def change_faculty_password():
    faculty = get_current_faculty()

    if not faculty:
        return jsonify({
            "success": False,
            "message": "Faculty profile not found. Please contact administration.",
        }), 404

    data = request.get_json(silent=True) or {}
    current_password = data.get("current_password")
    new_password = data.get("new_password")
    confirm_password = data.get("confirm_password")

    if not current_password or not new_password:
        return jsonify({
            "success": False,
            "message": "Current password and new password are required",
        }), 400

    if len(str(new_password)) < 6:
        return jsonify({
            "success": False,
            "message": "New password must be at least 6 characters",
        }), 400

    if confirm_password and str(new_password) != str(confirm_password):
        return jsonify({
            "success": False,
            "message": "New password and confirmation do not match",
        }), 400

    if not bcrypt.check_password_hash(faculty.user.password_hash, str(current_password)):
        return jsonify({
            "success": False,
            "message": "Current password is incorrect",
        }), 400

    faculty.user.password_hash = bcrypt.generate_password_hash(str(new_password)).decode("utf-8")
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Password changed successfully",
    }), 200

# ============================================================
# GET FACULTY CLASSES SUMMARY
# ============================================================

@faculty_bp.get("/classes/summary")
@faculty_required
def get_faculty_classes_summary():
    faculty = get_current_faculty()

    if not faculty:
        return jsonify({
            "success": False,
            "message": "Faculty profile not found. Please contact administration.",
        }), 404

    semester = request.args.get("semester", type=int)
    academic_year = request.args.get("academic_year")
    section = request.args.get("section")
    day = request.args.get("day")

    query = CourseOffering.query.filter_by(faculty_id=faculty.faculty_id)
    if semester is not None:
        query = query.filter(CourseOffering.semester == semester)
    if academic_year and academic_year not in ["All", "all", ""]:
        canon_ay = canonical_academic_year(academic_year) or academic_year
        start_year = canon_ay.split("-")[0].strip() if "-" in canon_ay else canon_ay.strip()
        query = query.filter(
            db.or_(
                CourseOffering.academic_year == academic_year,
                CourseOffering.academic_year == canon_ay,
                CourseOffering.academic_year.like(f"{start_year}%"),
            )
        )
    if section and section not in ["All", "all", "All Sections", ""]:
        query = query.filter(CourseOffering.section == section)
    if day and day not in ["All", "all", "All Days", ""]:
        day_match = (
            db.session.query(TimetableEntry.offering_id)
            .filter(db.func.lower(TimetableEntry.day_of_week) == day.strip().lower())
            .subquery()
        )
        query = query.filter(CourseOffering.offering_id.in_(day_match))

    offerings = query.all()
    offering_ids = [o.offering_id for o in offerings]
    distinct_courses_count = len(set(o.course_id for o in offerings))
    total_offerings_count = len(offerings)
    active_semesters_count = len(set(o.semester for o in offerings if o.semester is not None))

    if offering_ids:
        unique_student_ids = (
            db.session.query(Enrollment.student_id)
            .filter(
                Enrollment.offering_id.in_(offering_ids),
                Enrollment.status == "ACTIVE",
            )
            .distinct()
            .all()
        )
        unique_students_count = len(unique_student_ids)
        total_enrollments_count = (
            Enrollment.query
            .filter(
                Enrollment.offering_id.in_(offering_ids),
                Enrollment.status == "ACTIVE",
            )
            .count()
        )
    else:
        unique_students_count = 0
        total_enrollments_count = 0

    substitute_entry_ids = [
        adj.timetable_entry_id
        for adj in FacultyAdjustment.query.filter_by(
            substitute_faculty_id=faculty.faculty_id,
            status="APPROVED",
        ).all()
    ]
    tt_query = TimetableEntry.query.join(CourseOffering).filter(
        db.or_(
            CourseOffering.faculty_id == faculty.faculty_id,
            TimetableEntry.timetable_entry_id.in_(substitute_entry_ids),
        ) if substitute_entry_ids else (CourseOffering.faculty_id == faculty.faculty_id)
    )
    if semester is not None:
        tt_query = tt_query.filter(CourseOffering.semester == semester)
    if academic_year and academic_year not in ["All", "all", ""]:
        canon_ay = canonical_academic_year(academic_year) or academic_year
        start_year = canon_ay.split("-")[0].strip() if "-" in canon_ay else canon_ay.strip()
        tt_query = tt_query.filter(
            db.or_(
                CourseOffering.academic_year == academic_year,
                CourseOffering.academic_year == canon_ay,
                CourseOffering.academic_year.like(f"{start_year}%"),
            )
        )
    if section and section not in ["All", "all", "All Sections", ""]:
        tt_query = tt_query.filter(CourseOffering.section == section)
    if day and day not in ["All", "all", "All Days", ""]:
        tt_query = tt_query.filter(db.func.lower(TimetableEntry.day_of_week) == day.strip().lower())

    tt_entries_list = tt_query.all()
    weekly_timetable_slots = len(tt_entries_list)

    total_weekly_minutes = 0
    for entry in tt_entries_list:
        if entry.start_time and entry.end_time:
            sm = entry.start_time.hour * 60 + entry.start_time.minute
            em = entry.end_time.hour * 60 + entry.end_time.minute
            diff = max(0, em - sm)
            total_weekly_minutes += diff
        else:
            total_weekly_minutes += 60
    weekly_hours = round(total_weekly_minutes / 60, 1)
    if weekly_hours.is_integer():
        weekly_hours = int(weekly_hours)

    if offering_ids:
        closed_sessions = (
            AttendanceSession.query
            .filter(
                AttendanceSession.offering_id.in_(offering_ids),
                AttendanceSession.status == "CLOSED",
            )
            .all()
        )
        session_ids = [s.session_id for s in closed_sessions]
        total_closed_sessions = len(session_ids)

        if session_ids:
            total_present = (
                AttendanceRecord.query
                .filter(
                    AttendanceRecord.session_id.in_(session_ids),
                    AttendanceRecord.status == "PRESENT",
                )
                .count()
            )

            total_possible = 0
            for s in closed_sessions:
                s_students = (
                    Enrollment.query
                    .filter_by(
                        offering_id=s.offering_id,
                        status="ACTIVE",
                    )
                    .count()
                )
                total_possible += s_students

            total_absent = max(0, total_possible - total_present)
            overall_attendance_percentage = (
                round((total_present / total_possible) * 100, 2)
                if total_possible > 0
                else None
            )
        else:
            total_present = 0
            total_absent = 0
            total_possible = 0
            overall_attendance_percentage = None
    else:
        total_closed_sessions = 0
        total_present = 0
        total_absent = 0
        total_possible = 0
        overall_attendance_percentage = None

    return jsonify({
        "success": True,
        "data": {
            "assigned_courses_count": distinct_courses_count,
            "total_offerings_count": total_offerings_count,
            "enrolled_students_count": unique_students_count,
            "total_enrollments_count": total_enrollments_count,
            "weekly_timetable_slots": weekly_timetable_slots,
            "weekly_hours": weekly_hours,
            "active_semesters_count": active_semesters_count,
            "total_closed_sessions": total_closed_sessions,
            "total_present": total_present,
            "total_absent": total_absent,
            "total_eligible_opportunities": total_possible,
            "overall_attendance_percentage": overall_attendance_percentage,
        },
    }), 200


# ============================================================
# GET FACULTY COURSES
# ============================================================

@faculty_bp.get("/courses")
@faculty_required
def get_faculty_courses():
    faculty = get_current_faculty()

    if not faculty:
        return jsonify({
            "success": False,
            "message": "Faculty profile not found. Please contact administration.",
        }), 404

    semester = request.args.get("semester", type=int)
    academic_year = request.args.get("academic_year")
    section = request.args.get("section")
    day = request.args.get("day")

    query = (
        CourseOffering.query
        .filter_by(faculty_id=faculty.faculty_id)
    )

    if semester is not None:
        query = query.filter(CourseOffering.semester == semester)
    if academic_year and academic_year not in ["All", "all", ""]:
        canon_ay = canonical_academic_year(academic_year) or academic_year
        start_year = canon_ay.split("-")[0].strip() if "-" in canon_ay else canon_ay.strip()
        query = query.filter(
            db.or_(
                CourseOffering.academic_year == academic_year,
                CourseOffering.academic_year == canon_ay,
                CourseOffering.academic_year.like(f"{start_year}%"),
            )
        )
    if section and section not in ["All", "all", "All Sections", ""]:
        query = query.filter(CourseOffering.section == section)
    if day and day not in ["All", "all", "All Days", ""]:
        day_match = (
            db.session.query(TimetableEntry.offering_id)
            .filter(db.func.lower(TimetableEntry.day_of_week) == day.strip().lower())
            .subquery()
        )
        query = query.filter(CourseOffering.offering_id.in_(day_match))

    offerings = (
        query
        .options(
            joinedload(CourseOffering.course),
            selectinload(CourseOffering.timetable_entries),
        )
        .order_by(CourseOffering.offering_id.asc())
        .all()
    )

    offering_ids = [o.offering_id for o in offerings]
    active_student_counts = {}
    if offering_ids:
        active_counts = (
            db.session.query(
                Enrollment.offering_id,
                db.func.count(Enrollment.enrollment_id),
            )
            .join(Student, Enrollment.student_id == Student.student_id)
            .join(User, Student.user_id == User.user_id)
            .filter(
                Enrollment.offering_id.in_(offering_ids),
                Enrollment.status == "ACTIVE",
                User.is_active.is_(True),
            )
            .group_by(Enrollment.offering_id)
            .all()
        )
        active_student_counts = dict(active_counts)

    data = []

    short_day_map = {
        "Monday": "Mon",
        "Tuesday": "Tue",
        "Wednesday": "Wed",
        "Thursday": "Thu",
        "Friday": "Fri",
        "Saturday": "Sat",
        "Sunday": "Sun",
    }

    for offering in offerings:
        active_student_count = active_student_counts.get(offering.offering_id, 0)
        if active_student_count == 0:
            sibling_ids = [
                o.offering_id for o in CourseOffering.query.filter_by(
                    course_id=offering.course_id,
                    semester=offering.semester,
                    section=offering.section,
                ).all()
                if o.offering_id != offering.offering_id
            ]
            if sibling_ids:
                active_student_count = (
                    db.session.query(Enrollment.enrollment_id)
                    .join(Student, Enrollment.student_id == Student.student_id)
                    .join(User, Student.user_id == User.user_id)
                    .filter(
                        Enrollment.offering_id.in_(sibling_ids),
                        Enrollment.status == "ACTIVE",
                        User.is_active.is_(True),
                        Student.semester == offering.semester,
                        Student.section == offering.section,
                    )
                    .count()
                )
        tt_entries = sorted(
            offering.timetable_entries,
            key=lambda e: (e.day_of_week or "", e.start_time or "")
        )

        room = offering.room
        if not room and tt_entries:
            for entry in tt_entries:
                if entry.room:
                    room = entry.room
                    break

        days_list = [short_day_map.get(e.day_of_week, e.day_of_week[:3] if e.day_of_week else "") for e in tt_entries if e.day_of_week]
        unique_days = list(dict.fromkeys([d for d in days_list if d]))
        days_display = ", ".join(unique_days) if unique_days else "Not scheduled"

        time_display = "—"
        if tt_entries:
            first_tt = tt_entries[0]
            if first_tt.start_time and first_tt.end_time:
                st_str = first_tt.start_time.strftime("%I:%M %p")
                et_str = first_tt.end_time.strftime("%I:%M %p")
                time_display = f"{st_str} - {et_str}"

        serialized_tt = [
            {
                "timetable_entry_id": e.timetable_entry_id,
                "day_of_week": e.day_of_week,
                "start_time": e.start_time.strftime("%H:%M") if e.start_time else "",
                "end_time": e.end_time.strftime("%H:%M") if e.end_time else "",
                "room": e.room,
            }
            for e in tt_entries
        ]

        data.append({
            "offering_id": offering.offering_id,
            "course_id": offering.course_id,
            "course_code": offering.course.course_code,
            "course_name": offering.course.course_name,
            "credits": offering.course.credits,
            "semester": offering.semester,
            "section": offering.section,
            "batch": offering.course.batch if offering.course and offering.course.batch else "",
            "academic_year": resolve_offering_academic_year(offering.academic_year, offering.semester),
            "room": room,
            "student_count": active_student_count,
            "days_display": days_display,
            "time_display": time_display,
            "timetable_entries": serialized_tt,
        })

    return jsonify({
        "success": True,
        "data": data,
    }), 200


# ============================================================
# GET FACULTY COURSE DETAILS
# ============================================================

@faculty_bp.get("/courses/<int:course_id>")
@faculty_required
def get_faculty_course(course_id):
    faculty = get_current_faculty()

    if not faculty:
        return jsonify({
            "success": False,
            "message": "Faculty profile not found. Please contact administration.",
        }), 404

    offerings = (
        CourseOffering.query
        .filter_by(
            faculty_id=faculty.faculty_id,
            course_id=course_id,
        )
        .order_by(CourseOffering.offering_id.asc())
        .all()
    )

    if not offerings:
        return jsonify({
            "success": False,
            "message": "Course not found for this faculty",
        }), 404

    course = offerings[0].course
    offering_data = []

    for offering in offerings:
        active_enrollments = (
            Enrollment.query
            .filter_by(
                offering_id=offering.offering_id,
                status="ACTIVE",
            )
            .order_by(Enrollment.student_id.asc())
            .all()
        )

        students = []

        for enrollment in active_enrollments:
            student = enrollment.student
            acad_info = resolve_student_academic_info(student)

            students.append({
                "student_id": student.student_id,
                "enrollment_no": student.enrollment_no,
                "name": student.user.name,
                "email": student.user.email,
                "semester": acad_info["semester"],
                "section": acad_info["section"],
                "academic_year": canonical_academic_year(offering.academic_year),
                "batch_year": acad_info["batch_year"],
                "admission_year": acad_info["admission_year"],
                "enrollment_status": enrollment.status,
            })

        room = offering.room
        if not room:
            tt_entry = (
                TimetableEntry.query
                .filter_by(offering_id=offering.offering_id)
                .filter(TimetableEntry.room.isnot(None))
                .first()
            )
            if tt_entry:
                room = tt_entry.room

        offering_data.append({
            "offering_id": offering.offering_id,
            "semester": offering.semester,
            "section": offering.section,
            "academic_year": resolve_offering_academic_year(offering.academic_year, offering.semester),
            "room": room,
            "student_count": len(students),
            "students": students,
        })

    return jsonify({
        "success": True,
        "data": {
            "course_id": course.course_id,
            "course_code": course.course_code,
            "course_name": course.course_name,
            "credits": course.credits,
            "offerings": offering_data,
        },
    }), 200


# ============================================================
# GET FACULTY STUDENTS
# ============================================================

@faculty_bp.get("/students")
@faculty_required
def get_faculty_students():
    faculty = get_current_faculty()

    if not faculty:
        return jsonify({
            "success": False,
            "message": "Faculty profile not found. Please contact administration.",
        }), 404

    offering_id_filter = request.args.get("offering_id", type=int)

    if offering_id_filter:
        offering = db.session.get(CourseOffering, offering_id_filter)
        if not offering:
            return jsonify({
                "success": False,
                "message": "Course offering not found",
            }), 404

        if offering.faculty_id != faculty.faculty_id:
            return jsonify({
                "success": False,
                "message": "You are not authorized for this course offering",
            }), 403

        target_offerings = [offering]
    else:
        target_offerings = (
            CourseOffering.query
            .filter_by(faculty_id=faculty.faculty_id)
            .order_by(CourseOffering.offering_id.asc())
            .all()
        )

    students = {}

    for offering in target_offerings:
        # 1. Direct active enrollments on this faculty offering
        direct_enrollments = (
            Enrollment.query
            .options(
                joinedload(Enrollment.student).joinedload(Student.user),
                joinedload(Enrollment.student).joinedload(Student.department),
                joinedload(Enrollment.student).selectinload(Student.face_profiles),
            )
            .join(Student, Enrollment.student_id == Student.student_id)
            .join(User, Student.user_id == User.user_id)
            .filter(
                Enrollment.offering_id == offering.offering_id,
                Enrollment.status == "ACTIVE",
                User.is_active.is_(True),
            )
            .all()
        )

        enrollments_to_process = direct_enrollments

        # 2. Sibling fallback: if no direct enrollments, check equivalent sibling offerings
        if not direct_enrollments:
            sibling_candidates = (
                CourseOffering.query
                .filter(
                    CourseOffering.course_id == offering.course_id,
                    CourseOffering.semester == offering.semester,
                    CourseOffering.section == offering.section,
                    CourseOffering.offering_id != offering.offering_id,
                    db.or_(
                        CourseOffering.faculty_id.is_(None),
                        CourseOffering.faculty_id == faculty.faculty_id,
                    ),
                )
                .all()
            )
            sibling_offerings = [
                s for s in sibling_candidates
                if are_offerings_academically_compatible(
                    s.academic_year, s.semester,
                    offering.academic_year, offering.semester,
                )
            ]
            sibling_ids = [s.offering_id for s in sibling_offerings]
            if sibling_ids:
                enrollments_to_process = (
                    Enrollment.query
                    .options(
                        joinedload(Enrollment.student).joinedload(Student.user),
                        joinedload(Enrollment.student).joinedload(Student.department),
                        joinedload(Enrollment.student).selectinload(Student.face_profiles),
                    )
                    .join(Student, Enrollment.student_id == Student.student_id)
                    .join(User, Student.user_id == User.user_id)
                    .filter(
                        Enrollment.offering_id.in_(sibling_ids),
                        Enrollment.status == "ACTIVE",
                        User.is_active.is_(True),
                        Student.semester == offering.semester,
                        Student.section == offering.section,
                    )
                    .all()
                )

        for enrollment in enrollments_to_process:
            student = enrollment.student
            has_face = any(fp.is_active for fp in student.face_profiles)
            real_enrollment_id = enrollment.offering_id
            faculty_teaching_id = offering.offering_id

            if student.student_id in students:
                curr_ids = students[student.student_id]["offering_ids"]
                if real_enrollment_id not in curr_ids:
                    curr_ids.append(real_enrollment_id)
                if faculty_teaching_id not in curr_ids:
                    curr_ids.append(faculty_teaching_id)
                continue

            acad_info = resolve_student_academic_info(student)

            offering_ids_list = [real_enrollment_id]
            if faculty_teaching_id != real_enrollment_id:
                offering_ids_list.append(faculty_teaching_id)

            students[student.student_id] = {
                "student_id": student.student_id,
                "user_id": student.user_id,
                "name": student.user.name,
                "email": student.user.email,
                "enrollment_no": student.enrollment_no,
                "semester": acad_info["semester"],
                "section": acad_info["section"],
                "academic_year": acad_info["academic_year"],
                "batch_year": acad_info["batch_year"],
                "admission_year": acad_info["admission_year"],
                "offering_id": real_enrollment_id,
                "offering_ids": offering_ids_list,
                "teaching_offering_id": faculty_teaching_id,
                "has_face_profile": has_face,
                "face_registered": has_face,
                "department": {
                    "department_id": student.department.department_id,
                    "department_name": student.department.department_name,
                    "department_code": student.department.department_code,
                },
            }

    return jsonify({
        "success": True,
        "data": list(students.values()),
    }), 200


# ============================================================
# GET CLASS ROSTER (JSON)
# ============================================================

@faculty_bp.get("/classes/<int:offering_id>/roster")
@faculty_bp.get("/courses/offerings/<int:offering_id>/roster")
@faculty_required
def get_class_roster(offering_id):
    """Retrieve enrolled student roster details for an assigned offering."""
    faculty = get_current_faculty()
    if not faculty:
        return jsonify({
            "success": False,
            "message": "Faculty profile not found. Please contact administration.",
        }), 404

    offering = CourseOffering.query.filter_by(
        offering_id=offering_id,
        faculty_id=faculty.faculty_id,
    ).first()

    if not offering:
        return jsonify({
            "success": False,
            "message": "Class offering not found or unauthorized",
        }), 404

    # 1. Direct active enrollments
    direct_enrollments = (
        Enrollment.query
        .options(
            joinedload(Enrollment.student).joinedload(Student.user),
            joinedload(Enrollment.student).joinedload(Student.department),
        )
        .join(Student, Enrollment.student_id == Student.student_id)
        .join(User, Student.user_id == User.user_id)
        .filter(
            Enrollment.offering_id == offering.offering_id,
            Enrollment.status == "ACTIVE",
            db.or_(User.is_active.is_(True), User.is_active.is_(None)),
        )
        .order_by(Student.enrollment_no.asc(), User.name.asc())
        .all()
    )

    enrollments_to_process = direct_enrollments

    # 2. Sibling fallback
    if not direct_enrollments:
        sibling_candidates = (
            CourseOffering.query
            .filter(
                CourseOffering.course_id == offering.course_id,
                CourseOffering.semester == offering.semester,
                CourseOffering.section == offering.section,
                CourseOffering.offering_id != offering.offering_id,
                db.or_(
                    CourseOffering.faculty_id.is_(None),
                    CourseOffering.faculty_id == faculty.faculty_id,
                ),
            )
            .all()
        )
        sibling_offerings = [
            s for s in sibling_candidates
            if are_offerings_academically_compatible(
                s.academic_year, s.semester,
                offering.academic_year, offering.semester,
            )
        ]
        sibling_ids = [s.offering_id for s in sibling_offerings]
        if sibling_ids:
            enrollments_to_process = (
                Enrollment.query
                .options(
                    joinedload(Enrollment.student).joinedload(Student.user),
                    joinedload(Enrollment.student).joinedload(Student.department),
                )
                .join(Student, Enrollment.student_id == Student.student_id)
                .join(User, Student.user_id == User.user_id)
                .filter(
                    Enrollment.offering_id.in_(sibling_ids),
                    Enrollment.status == "ACTIVE",
                    db.or_(User.is_active.is_(True), User.is_active.is_(None)),
                    Student.semester == offering.semester,
                    Student.section == offering.section,
                )
                .order_by(Student.enrollment_no.asc(), User.name.asc())
                .all()
            )

    students = []
    for enr in enrollments_to_process:
        student = enr.student
        dept_name = student.department.department_name if student.department else "—"
        acad_info = resolve_student_academic_info(student)
        students.append({
            "student_id": student.student_id,
            "enrollment_no": student.enrollment_no,
            "name": student.user.name if student.user else "",
            "email": student.user.email if student.user else "",
            "department": dept_name,
            "semester": acad_info.get("semester") or offering.semester,
            "section": acad_info.get("section") or offering.section,
            "academic_year": acad_info.get("academic_year") or resolve_offering_academic_year(offering.academic_year, offering.semester),
            "status": enr.status,
        })

    course = offering.course
    return jsonify({
        "success": True,
        "data": {
            "offering_id": offering.offering_id,
            "course_id": offering.course_id,
            "course_code": course.course_code if course else "",
            "course_name": course.course_name if course else "",
            "semester": offering.semester,
            "section": offering.section,
            "academic_year": resolve_offering_academic_year(offering.academic_year, offering.semester),
            "total_students": len(students),
            "students": students,
        },
    }), 200


# ============================================================
# EXPORT CLASS ROSTER
# ============================================================

@faculty_bp.get("/classes/<int:offering_id>/roster/export")
@faculty_bp.get("/courses/offerings/<int:offering_id>/roster/export")
@faculty_required
def export_class_roster(offering_id):
    """Export the student roster for an assigned course offering in CSV, Excel, or PDF."""
    faculty = get_current_faculty()
    if not faculty:
        return jsonify({
            "success": False,
            "message": "Faculty profile not found. Please contact administration.",
        }), 404

    offering = CourseOffering.query.filter_by(
        offering_id=offering_id,
        faculty_id=faculty.faculty_id,
    ).first()

    if not offering:
        return jsonify({
            "success": False,
            "message": "Class offering not found or unauthorized",
        }), 404

    format_param = (request.args.get("format") or "xlsx").strip().lower()
    if format_param == "excel":
        format_param = "xlsx"

    if format_param not in ("xlsx", "pdf", "csv"):
        return jsonify({
            "success": False,
            "message": f"Unsupported export format '{format_param}'. Supported formats: xlsx, pdf, csv.",
        }), 400

    # 1. Direct active enrollments
    direct_enrollments = (
        Enrollment.query
        .options(
            joinedload(Enrollment.student).joinedload(Student.user),
            joinedload(Enrollment.student).joinedload(Student.department),
        )
        .join(Student, Enrollment.student_id == Student.student_id)
        .join(User, Student.user_id == User.user_id)
        .filter(
            Enrollment.offering_id == offering.offering_id,
            Enrollment.status == "ACTIVE",
            db.or_(User.is_active.is_(True), User.is_active.is_(None)),
        )
        .order_by(Student.enrollment_no.asc(), User.name.asc())
        .all()
    )

    enrollments_to_process = direct_enrollments

    # 2. Sibling fallback
    if not direct_enrollments:
        sibling_candidates = (
            CourseOffering.query
            .filter(
                CourseOffering.course_id == offering.course_id,
                CourseOffering.semester == offering.semester,
                CourseOffering.section == offering.section,
                CourseOffering.offering_id != offering.offering_id,
                db.or_(
                    CourseOffering.faculty_id.is_(None),
                    CourseOffering.faculty_id == faculty.faculty_id,
                ),
            )
            .all()
        )
        sibling_offerings = [
            s for s in sibling_candidates
            if are_offerings_academically_compatible(
                s.academic_year, s.semester,
                offering.academic_year, offering.semester,
            )
        ]
        sibling_ids = [s.offering_id for s in sibling_offerings]
        if sibling_ids:
            enrollments_to_process = (
                Enrollment.query
                .options(
                    joinedload(Enrollment.student).joinedload(Student.user),
                    joinedload(Enrollment.student).joinedload(Student.department),
                )
                .join(Student, Enrollment.student_id == Student.student_id)
                .join(User, Student.user_id == User.user_id)
                .filter(
                    Enrollment.offering_id.in_(sibling_ids),
                    Enrollment.status == "ACTIVE",
                    db.or_(User.is_active.is_(True), User.is_active.is_(None)),
                    Student.semester == offering.semester,
                    Student.section == offering.section,
                )
                .order_by(Student.enrollment_no.asc(), User.name.asc())
                .all()
            )

    headers = [
        "S.No.",
        "Enrollment No",
        "Student Name",
        "Department",
        "Semester",
        "Section",
        "Academic Year",
        "Enrollment Status",
    ]

    rows = []
    for idx, enr in enumerate(enrollments_to_process, start=1):
        student = enr.student
        dept_name = "—"
        if student.department:
            dept_name = student.department.department_name or student.department.department_code or "—"
        acad_info = resolve_student_academic_info(student)
        sem_val = acad_info.get("semester") or student.semester or offering.semester or "—"
        sec_val = acad_info.get("section") or student.section or offering.section or "—"
        acad_year_val = (
            acad_info.get("academic_year")
            or resolve_offering_academic_year(offering.academic_year, offering.semester)
            or "—"
        )
        student_name = student.user.name if (student.user and student.user.name) else "—"

        rows.append([
            idx,
            student.enrollment_no or "—",
            student_name,
            dept_name,
            sem_val,
            sec_val,
            acad_year_val,
            enr.status or "ACTIVE",
        ])

    course = offering.course
    faculty_name = faculty.user.name if (faculty.user and faculty.user.name) else "Faculty"
    course_code = course.course_code if course else "COURSE"
    course_name = course.course_name if course else "Course"
    course_display = f"{course_code} - {course_name}"
    sec_sem_display = f"Semester {offering.semester} | Section {offering.section}"
    offering_acad_year = resolve_offering_academic_year(offering.academic_year, offering.semester)

    dept_display = "—"
    if course and course.department:
        dept_display = course.department.department_name
    elif faculty.department:
        dept_display = faculty.department.department_name

    metadata = {
        "Faculty": faculty_name,
        "Department": dept_display,
        "Course": course_display,
        "Semester / Section": sec_sem_display,
        "Academic Year": offering_acad_year,
        "Total Enrolled": len(rows),
        "Generated On": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

    summary = {
        "Total Enrolled Students": len(rows),
        "Active Students": sum(1 for e in enrollments_to_process if (e.status or "").upper() == "ACTIVE"),
        "Course Credits": str(course.credits) if (course and course.credits is not None) else "—",
    }

    code_slug = re.sub(r"[^a-zA-Z0-9_-]", "_", course_code)
    sec_slug = re.sub(r"[^a-zA-Z0-9_-]", "_", offering.section) if offering.section else "Sec"
    today_str = datetime.now().strftime("%Y%m%d")
    base_filename = f"Class_Roster_{code_slug}_{sec_slug}_{today_str}"

    try:
        stream, mimetype, filename = generate_export(
            format_type=format_param,
            headers=headers,
            rows=rows,
            title="CLASS ROSTER REPORT",
            subtitle=f"{course_display} ({sec_sem_display})",
            metadata=metadata,
            summary=summary,
            base_filename=base_filename,
            sheet_name="Class Roster",
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
