from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity

from app.extensions import db
from app.models import (
    AttendanceRecord,
    AttendanceSession,
    CourseOffering,
    Enrollment,
    Faculty,
    FacultyAdjustment,
    Student,
    TimetableEntry,
    User,
)
from app.services.activity_service import record_activity
from app.utils.auth import faculty_required, faculty_or_admin_required
from app.utils import schedule
from app.services.cv.attendance_service import validate_student_attendance_eligibility


attendance_bp = Blueprint(
    "attendance",
    __name__,
    url_prefix="/api/faculty/attendance",
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


def get_offering_active_enrollments(offering):
    """
    Returns active enrollments for active students for this course offering.
    Includes active students enrolled directly or under duplicate/legacy offering
    records matching the same course_id, semester, and section.
    """
    if not offering:
        return []

    base_q = (
        Enrollment.query
        .join(Student, Enrollment.student_id == Student.student_id)
        .join(User, Student.user_id == User.user_id)
        .filter(
            Enrollment.status == "ACTIVE",
            User.is_active.is_(True),
            User.role == "STUDENT",
        )
    )

    direct = base_q.filter(
        Enrollment.offering_id == offering.offering_id
    ).all()
    if direct:
        return direct

    # Check matching sibling offerings for same course, semester, section
    matching_offering_ids = (
        db.session.query(CourseOffering.offering_id)
        .filter(
            CourseOffering.course_id == offering.course_id,
            CourseOffering.semester == offering.semester,
            CourseOffering.section == offering.section,
        )
        .subquery()
    )

    return (
        base_q
        .filter(
            Enrollment.offering_id.in_(db.select(matching_offering_ids.c.offering_id)),
            Student.semester == offering.semester,
            Student.section == offering.section,
        )
        .all()
    )


def serialize_attendance_record(record):
    if not record:
        return None
    student = record.student
    student_name = student.user.name if (student and student.user) else f"Student #{record.student_id}"
    enrollment_no = student.enrollment_no if student else "N/A"
    return {
        "attendance_id": record.attendance_id,
        "session_id": record.session_id,
        "student_id": record.student_id,
        "student_name": student_name,
        "enrollment_no": enrollment_no,
        "status": record.status,
        "marked_at": record.marked_at.isoformat() if record.marked_at else None,
        "confidence_score": record.confidence_score,
        "recognition_method": record.recognition_method,
    }


def serialize_session(session):
    if not session:
        return None

    offering = session.offering
    course = offering.course if offering else None

    timetable_entry = schedule.get_offering_authoritative_entry(
        session.offering_id,
        session.session_date,
        target_time=session.start_time,
    )

    room = (
        (timetable_entry.room if timetable_entry and timetable_entry.room else None)
        or (offering.room if offering else None)
    )

    start_time_val = (
        session.start_time
        or (timetable_entry.start_time if timetable_entry else None)
    )
    end_time_val = (
        session.end_time
        or (timetable_entry.end_time if timetable_entry else None)
    )

    now = schedule.get_current_institution_time()
    is_eligible, status_str, _ = schedule.get_session_schedule_status(session, current_dt=now)

    return {
        "session_id": session.session_id,
        "offering_id": session.offering_id,
        "timetable_entry_id": timetable_entry.timetable_entry_id if timetable_entry else None,
        "faculty_id": session.faculty_id,
        "session_date": session.session_date.isoformat() if session.session_date else None,
        "start_time": start_time_val.isoformat() if start_time_val else None,
        "end_time": end_time_val.isoformat() if end_time_val else None,
        "status": session.status,
        "is_eligible_for_attendance": is_eligible,
        "schedule_status": status_str,
        "room": room,
        "course_code": course.course_code if course else None,
        "course_name": course.course_name if course else None,
        "section": offering.section if offering else None,
        "semester": offering.semester if offering else None,
        "academic_year": offering.academic_year if offering else None,
    }



# ============================================================
# START ATTENDANCE SESSION
# ============================================================

@attendance_bp.post("/sessions")
@faculty_required
def start_attendance_session():
    faculty = get_current_faculty()

    if not faculty:
        return jsonify({
            "success": False,
            "message": "Faculty profile not found",
        }), 404

    data = request.get_json(silent=True) or {}

    offering_id = data.get("offering_id")

    if not offering_id:
        return jsonify({
            "success": False,
            "message": "offering_id is required",
        }), 400

    offering = db.session.get(
        CourseOffering,
        offering_id,
    )

    if not offering:
        return jsonify({
            "success": False,
            "message": "Course offering not found",
        }), 404

    is_owner = (offering.faculty_id == faculty.faculty_id)
    is_substitute = FacultyAdjustment.query.filter_by(
        substitute_faculty_id=faculty.faculty_id,
        status="APPROVED",
    ).join(TimetableEntry).filter(TimetableEntry.offering_id == offering.offering_id).first() is not None

    if not (is_owner or is_substitute):
        return jsonify({
            "success": False,
            "message": "You are not authorized for this course offering",
        }), 403

    # Verify the offering has eligible active enrollments.
    active_enrollments = get_offering_active_enrollments(offering)

    if not active_enrollments:
        return jsonify({
            "success": False,
            "message": "Cannot start attendance session: No active students are enrolled in this course offering",
        }), 400

    now = schedule.get_current_institution_time()
    today_date = now.date()
    today_day = now.strftime("%A")

    # Reconcile any existing active sessions for this faculty member
    existing_active_sessions = (
        AttendanceSession.query
        .filter_by(
            faculty_id=faculty.faculty_id,
            status="ACTIVE",
        )
        .order_by(AttendanceSession.session_id.desc())
        .all()
    )

    for existing in existing_active_sessions:
        is_elig, st_str, _ = schedule.get_session_schedule_status(existing, current_dt=now)
        if st_str == "ENDED":
            schedule.close_expired_session(existing)
        elif st_str == "UPCOMING":
            schedule.reconcile_premature_session(existing)
        elif is_elig:
            return jsonify({
                "success": False,
                "message": "An active attendance session already exists",
                "data": serialize_session(existing),
            }), 409

    # Extract faculty assigned session time from the timetable
    timetable_entry_id = data.get("timetable_entry_id")
    timetable_entry = None

    if timetable_entry_id is not None:
        try:
            timetable_entry_id = int(timetable_entry_id)
        except (ValueError, TypeError):
            return jsonify({
                "success": False,
                "message": "Invalid timetable_entry_id format",
            }), 400

        timetable_entry = db.session.get(TimetableEntry, timetable_entry_id)
        if not timetable_entry:
            return jsonify({
                "success": False,
                "message": "Timetable entry not found",
            }), 404

        if timetable_entry.offering_id != offering.offering_id:
            return jsonify({
                "success": False,
                "message": "The selected timetable entry does not belong to this course offering",
            }), 400

        # Check authorization on this specific timetable entry if substitute
        if not is_owner:
            adj_sub = FacultyAdjustment.query.filter_by(
                substitute_faculty_id=faculty.faculty_id,
                timetable_entry_id=timetable_entry.timetable_entry_id,
                status="APPROVED",
            ).first()
            if not adj_sub:
                return jsonify({
                    "success": False,
                    "message": "You are not authorized for this specific timetable slot",
                }), 403

        # Verify scheduled day
        if timetable_entry.day_of_week.strip().lower() != today_day.lower():
            return jsonify({
                "success": False,
                "message": f"The selected timetable slot is scheduled for {timetable_entry.day_of_week}, not today ({today_day}).",
            }), 400
    else:
        # Resolve from assigned timetable entries for today
        today_entries = (
            TimetableEntry.query
            .filter(
                TimetableEntry.offering_id == offering.offering_id,
                db.func.lower(TimetableEntry.day_of_week) == today_day.lower(),
            )
            .order_by(TimetableEntry.start_time.asc())
            .all()
        )

        if not today_entries:
            return jsonify({
                "success": False,
                "message": f"No scheduled timetable slots found for today ({today_day}) for this course offering.",
            }), 400

        if len(today_entries) == 1:
            timetable_entry = today_entries[0]
        else:
            # Multiple slots on today. Determine if one is active right now.
            active_slots = [
                e for e in today_entries
                if schedule.evaluate_timetable_window(today_date, e.start_time, e.end_time, current_dt=now)[1] == "ACTIVE"
            ]
            if len(active_slots) == 1:
                timetable_entry = active_slots[0]
            elif len(active_slots) > 1:
                return jsonify({
                    "success": False,
                    "message": "Multiple active timetable slots exist for this course today. Please select a specific slot.",
                }), 400
            else:
                # None is active right now. Do not silently select an expired slot if an upcoming slot exists!
                upcoming_slots = [
                    e for e in today_entries
                    if schedule.evaluate_timetable_window(today_date, e.start_time, e.end_time, current_dt=now)[1] == "UPCOMING"
                ]
                if upcoming_slots:
                    timetable_entry = upcoming_slots[0]
                else:
                    # All slots today have ended. Select the most recent one to evaluate and report ended.
                    timetable_entry = today_entries[-1]

    session_start = timetable_entry.start_time
    session_end = timetable_entry.end_time


    # Validate against authoritative scheduled timetable window
    is_active, status_str, start_dt, end_dt = schedule.evaluate_timetable_window(
        today_date, session_start, session_end, current_dt=now
    )

    if status_str == "UPCOMING":
        return jsonify({
            "success": False,
            "message": f"Cannot start attendance session before the scheduled start time ({session_start.strftime('%I:%M %p')}).",
        }), 400

    if status_str == "ENDED":
        return jsonify({
            "success": False,
            "message": f"Cannot start attendance session after the scheduled class window has ended ({session_end.strftime('%I:%M %p')}).",
        }), 400

    session = AttendanceSession(
        offering_id=offering.offering_id,
        faculty_id=faculty.faculty_id,
        session_date=today_date,
        start_time=session_start,
        end_time=session_end,
        status="ACTIVE",
    )

    db.session.add(session)
    db.session.commit()

    record_activity(
        action_type="ATTENDANCE_SESSION_CREATED",
        description=f"Started attendance session for course offering {offering.offering_id}",
        actor_id=faculty.user_id if faculty else None,
        entity_type="AttendanceSession",
        entity_id=str(session.session_id),
    )

    return jsonify({
        "success": True,
        "message": "Attendance session started successfully",
        "data": serialize_session(session),
    }), 201


@attendance_bp.get("/sessions")
@faculty_required
def get_attendance_sessions():
    faculty = get_current_faculty()

    if not faculty:
        return jsonify({
            "success": False,
            "message": "Faculty profile not found",
        }), 404

    offering_id = request.args.get("offering_id", type=int)
    status_filter = request.args.get("status")
    session_date = request.args.get("date") or request.args.get("session_date")

    query = AttendanceSession.query.filter_by(faculty_id=faculty.faculty_id)

    if offering_id:
        query = query.filter(AttendanceSession.offering_id == offering_id)
    if status_filter and status_filter.upper() != "ALL":
        query = query.filter(AttendanceSession.status == status_filter.upper())
    if session_date:
        query = query.filter(AttendanceSession.session_date == session_date)

    query = query.order_by(
        AttendanceSession.session_date.desc(),
        AttendanceSession.session_id.desc(),
    )

    page = request.args.get("page", type=int)
    per_page = request.args.get("per_page", type=int)

    if page is not None and per_page is not None:
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        return jsonify({
            "success": True,
            "data": [serialize_session(s) for s in pagination.items],
            "total": pagination.total,
            "page": pagination.page,
            "per_page": pagination.per_page,
            "pages": pagination.pages,
        }), 200

    sessions = query.all()

    return jsonify({
        "success": True,
        "data": [serialize_session(session) for session in sessions],
    }), 200


# ============================================================
# GET FACULTY ATTENDANCE OVERVIEW
# ============================================================

@attendance_bp.get("/overview")
@faculty_required
def get_attendance_overview():
    faculty = get_current_faculty()

    if not faculty:
        return jsonify({
            "success": False,
            "message": "Faculty profile not found",
        }), 404

    local_now = datetime.now()
    today_date = local_now.date()

    # 1. Today's sessions count for this faculty
    today_sessions_count = (
        AttendanceSession.query
        .filter(
            AttendanceSession.faculty_id == faculty.faculty_id,
            AttendanceSession.session_date == today_date,
        )
        .count()
    )

    # 2. Active session check
    active_session = (
        AttendanceSession.query
        .filter_by(
            faculty_id=faculty.faculty_id,
            status="ACTIVE",
        )
        .order_by(AttendanceSession.session_id.desc())
        .first()
    )

    # 3. Contextual target session for attendance stats
    session_id_param = request.args.get("session_id", type=int)
    target_session = None

    if session_id_param:
        target_session = (
            AttendanceSession.query
            .filter_by(
                session_id=session_id_param,
                faculty_id=faculty.faculty_id,
            )
            .first()
        )
        if not target_session:
            return jsonify({
                "success": False,
                "message": "Session not found or not authorized for this faculty",
            }), 404
    else:
        # Default context: active session, or most recent session, or None
        target_session = (
            active_session
            or AttendanceSession.query
            .filter_by(faculty_id=faculty.faculty_id)
            .order_by(
                AttendanceSession.session_date.desc(),
                AttendanceSession.session_id.desc(),
            )
            .first()
        )

    # 4. Compute statistics for target session
    if target_session:
        active_enrollments = get_offering_active_enrollments(target_session.offering)
        enrolled_count = len(active_enrollments)

        present_count = (
            AttendanceRecord.query
            .filter(
                AttendanceRecord.session_id == target_session.session_id,
                AttendanceRecord.status.in_(["PRESENT", "LATE"]),
            )
            .count()
        )

        if target_session.status == "CLOSED":
            absent_count = (
                AttendanceRecord.query
                .filter_by(
                    session_id=target_session.session_id,
                    status="ABSENT",
                )
                .count()
            )
        else:
            absent_count = max(0, enrolled_count - present_count)

        total_recorded = (
            AttendanceRecord.query
            .filter_by(session_id=target_session.session_id)
            .count()
        )

        attendance_rate = (
            round((present_count / enrolled_count) * 100, 1)
            if enrolled_count > 0
            else None
        )
    else:
        enrolled_count = 0
        present_count = 0
        absent_count = 0
        total_recorded = 0
        attendance_rate = None

    return jsonify({
        "success": True,
        "data": {
            "today_sessions": today_sessions_count,
            "active_sessions": 1 if active_session else 0,
            "has_active_session": bool(active_session),
            "active_session": serialize_session(active_session) if active_session else None,
            "selected_session": serialize_session(target_session) if target_session else None,
            "students_present": present_count,
            "students_absent": absent_count,
            "total_enrolled": enrolled_count,
            "total_recorded": total_recorded,
            "attendance_rate": attendance_rate,
        },
    }), 200


# ============================================================
# GET ACTIVE ATTENDANCE SESSION
# ============================================================

@attendance_bp.get("/sessions/active")
@faculty_required
def get_active_attendance_session():
    faculty = get_current_faculty()

    if not faculty:
        return jsonify({
            "success": False,
            "message": "Faculty profile not found",
        }), 404

    offering_id = request.args.get("offering_id", type=int)
    now = schedule.get_current_institution_time()

    query = AttendanceSession.query.filter_by(
        faculty_id=faculty.faculty_id,
        status="ACTIVE",
    )
    if offering_id:
        query = query.filter(AttendanceSession.offering_id == offering_id)

    sessions = (
        query
        .order_by(
            AttendanceSession.session_id.desc()
        )
        .all()
    )

    active_eligible_session = None

    for s in sessions:
        if not s.offering:
            continue
        is_eligible, status_str, _ = schedule.get_session_schedule_status(s, current_dt=now)
        if status_str == "ENDED":
            schedule.close_expired_session(s)
        elif status_str == "UPCOMING":
            schedule.reconcile_premature_session(s)
        elif is_eligible and not active_eligible_session:
            active_eligible_session = s


    if not active_eligible_session:
        return jsonify({
            "success": True,
            "message": "No active attendance session",
            "data": None,
        }), 200

    return jsonify({
        "success": True,
        "data": serialize_session(active_eligible_session),
    }), 200


# ============================================================
# CLOSE ATTENDANCE SESSION
# ============================================================

@attendance_bp.post("/sessions/<int:session_id>/close")
@faculty_required
def close_attendance_session(session_id):
    faculty = get_current_faculty()

    if not faculty:
        return jsonify({
            "success": False,
            "message": "Faculty profile not found",
        }), 404

    session = db.session.get(
        AttendanceSession,
        session_id,
    )

    if not session:
        return jsonify({
            "success": False,
            "message": "Attendance session not found",
        }), 404

    if session.faculty_id != faculty.faculty_id:
        return jsonify({
            "success": False,
            "message": "You are not authorized for this session",
        }), 403

    if session.status != "ACTIVE":
        return jsonify({
            "success": False,
            "message": "Attendance session is already closed",
        }), 409

    # Find all actively enrolled students for this course offering.
    active_enrollments = get_offering_active_enrollments(session.offering)

    # Find students whose attendance has already been recorded.
    existing_records = AttendanceRecord.query.filter_by(
        session_id=session.session_id,
    ).all()

    recorded_student_ids = {
        record.student_id for record in existing_records
    }

    local_now = datetime.now()

    # Automatically mark students without an attendance record as ABSENT.
    for enrollment in active_enrollments:
        if enrollment.student_id not in recorded_student_ids:
            absent_record = AttendanceRecord(
                session_id=session.session_id,
                student_id=enrollment.student_id,
                status="ABSENT",
                marked_at=datetime.now(timezone.utc).replace(tzinfo=None),
                recognition_method="SYSTEM",
            )
            db.session.add(absent_record)

    # Close the session and save all absence records together.
    if not session.end_time:
        session.end_time = local_now.time()
    session.status = "CLOSED"

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return jsonify({
        "success": True,
        "message": "Attendance session closed successfully",
        "data": serialize_session(session),
    }), 200


# ============================================================
# MARK ATTENDANCE RECORD / MANUAL CORRECTION
# ============================================================

@attendance_bp.post("/sessions/<int:session_id>/records")
@faculty_or_admin_required
def mark_attendance(session_id):
    claims = get_jwt()
    user_role = claims.get("role")

    if user_role == "FACULTY":
        return jsonify({
            "success": False,
            "message": "Manual attendance marking by faculty is disabled. Attendance must be recorded via face recognition.",
        }), 403

    session = db.session.get(
        AttendanceSession,
        session_id,
    )

    if not session:
        return jsonify({
            "success": False,
            "message": "Attendance session not found",
        }), 404

    data = request.get_json(silent=True) or {}

    student_id = data.get("student_id")
    status_val = str(data.get("status", "PRESENT")).upper().strip()
    confidence_score = data.get("confidence_score")
    recognition_method = str(data.get("recognition_method", "MANUAL")).upper().strip()
    allow_update = data.get("allow_update", True)

    if not student_id:
        return jsonify({
            "success": False,
            "message": "student_id is required",
        }), 400

    if status_val not in {"PRESENT", "ABSENT", "LATE"}:
        return jsonify({
            "success": False,
            "message": "Invalid status. Must be PRESENT, ABSENT, or LATE",
        }), 400

    if recognition_method not in {"FACE", "MANUAL", "SYSTEM"}:
        return jsonify({
            "success": False,
            "message": "Invalid recognition_method",
        }), 400

    now = schedule.get_current_institution_time()
    is_eligible, status_str, details = schedule.get_session_schedule_status(session, current_dt=now)

    if status_str == "UPCOMING":
        return jsonify({
            "success": False,
            "message": details.get("message", "Attendance cannot be recorded before scheduled start time"),
        }), 400

    # Face capture requires active session within valid class window; manual correction is permitted on active or closed sessions
    if recognition_method == "FACE":
        if session.status != "ACTIVE":
            return jsonify({
                "success": False,
                "message": "Attendance session is not active",
            }), 409
        if status_str == "ENDED":
            schedule.close_expired_session(session)
            return jsonify({
                "success": False,
                "message": "Attendance session has ended",
            }), 409

    is_eligible, message, student = validate_student_attendance_eligibility(
        session=session,
        student_id=student_id,
        faculty_id=None,
        check_window=(recognition_method == "FACE"),
    )
    if not is_eligible:
        if "not found" in message.lower():
            return jsonify({
                "success": False,
                "message": message,
            }), 404
        return jsonify({
            "success": False,
            "message": message,
        }), 403


    existing_record = AttendanceRecord.query.filter_by(
        session_id=session_id,
        student_id=student_id,
    ).first()

    if existing_record:
        if not allow_update:
            return jsonify({
                "success": False,
                "message": "Attendance already marked for this student",
            }), 409

        existing_record.status = status_val
        existing_record.recognition_method = recognition_method
        existing_record.marked_at = datetime.now(timezone.utc).replace(tzinfo=None)
        if confidence_score is not None:
            try:
                existing_record.confidence_score = float(confidence_score)
            except (TypeError, ValueError):
                pass
        db.session.commit()
        return jsonify({
            "success": True,
            "message": "Attendance record updated successfully",
            "data": serialize_attendance_record(existing_record),
        }), 200

    if confidence_score is not None:
        try:
            confidence_score = float(confidence_score)
        except (TypeError, ValueError):
            return jsonify({
                "success": False,
                "message": "confidence_score must be a number",
            }), 400

        if not 0.0 <= confidence_score <= 1.0:
            return jsonify({
                "success": False,
                "message": "confidence_score must be between 0 and 1",
            }), 400

    record = AttendanceRecord(
        session_id=session_id,
        student_id=student_id,
        status=status_val,
        marked_at=datetime.now(timezone.utc).replace(tzinfo=None),
        confidence_score=confidence_score,
        recognition_method=recognition_method,
    )

    db.session.add(record)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Attendance marked successfully",
        "data": serialize_attendance_record(record),
    }), 201


# ============================================================
# UPDATE / CORRECT ATTENDANCE RECORD (PATCH)
# ============================================================

@attendance_bp.patch("/sessions/<int:session_id>/records/<int:student_id>")
@faculty_or_admin_required
def update_attendance_record(session_id, student_id):
    claims = get_jwt()
    user_role = claims.get("role")

    if user_role == "FACULTY":
        return jsonify({
            "success": False,
            "message": "Manual attendance marking by faculty is disabled. Attendance must be recorded via face recognition.",
        }), 403

    session = db.session.get(AttendanceSession, session_id)
    if not session:
        return jsonify({
            "success": False,
            "message": "Attendance session not found",
        }), 404

    is_eligible, message, student = validate_student_attendance_eligibility(
        session=session,
        student_id=student_id,
        faculty_id=None,
        check_window=False,
    )
    if not is_eligible:
        if "not found" in message.lower():
            return jsonify({
                "success": False,
                "message": message,
            }), 404
        return jsonify({
            "success": False,
            "message": message,
        }), 403

    data = request.get_json(silent=True) or {}
    status_val = str(data.get("status", "PRESENT")).upper().strip()
    if status_val not in {"PRESENT", "ABSENT", "LATE"}:
        return jsonify({
            "success": False,
            "message": "Invalid status. Must be PRESENT, ABSENT, or LATE",
        }), 400

    recognition_method = str(data.get("recognition_method", "MANUAL")).upper().strip()
    if recognition_method not in {"FACE", "MANUAL", "SYSTEM"}:
        recognition_method = "MANUAL"

    record = AttendanceRecord.query.filter_by(
        session_id=session_id,
        student_id=student_id,
    ).first()

    if not record:
        record = AttendanceRecord(
            session_id=session_id,
            student_id=student_id,
            status=status_val,
            marked_at=datetime.now(timezone.utc).replace(tzinfo=None),
            confidence_score=None,
            recognition_method=recognition_method,
        )
        db.session.add(record)
    else:
        record.status = status_val
        record.recognition_method = recognition_method
        record.marked_at = datetime.now(timezone.utc).replace(tzinfo=None)

    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Attendance record updated successfully",
        "data": serialize_attendance_record(record),
    }), 200


# ============================================================
# GET SESSION ATTENDANCE RECORDS
# ============================================================

@attendance_bp.get("/sessions/<int:session_id>/records")
@faculty_required
def get_session_attendance(session_id):
    faculty = get_current_faculty()

    if not faculty:
        return jsonify({
            "success": False,
            "message": "Faculty profile not found",
        }), 404

    session = db.session.get(
        AttendanceSession,
        session_id,
    )

    if not session:
        return jsonify({
            "success": False,
            "message": "Attendance session not found",
        }), 404

    if session.faculty_id != faculty.faculty_id:
        return jsonify({
            "success": False,
            "message": "You are not authorized for this session",
        }), 403

    records = (
        AttendanceRecord.query
        .filter_by(session_id=session_id)
        .order_by(AttendanceRecord.marked_at.asc())
        .all()
    )

    data = [serialize_attendance_record(record) for record in records]

    return jsonify({
        "success": True,
        "data": data,
    }), 200