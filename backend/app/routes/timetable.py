from datetime import datetime, time
import re

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity
from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models import (
    CourseOffering,
    Enrollment,
    Faculty,
    FacultyAdjustment,
    Student,
    TimetableEntry,
    User,
)
from app.utils.auth import admin_required, faculty_required, student_required
from app.utils.academic_year import are_offerings_academically_compatible, canonical_academic_year
from app.services.activity_service import record_activity

timetable_bp = Blueprint(
    "timetable",
    __name__,
    url_prefix="/api/timetable",
)


def serialize_entry(entry, adjustment_data=None):
    offering = entry.offering
    course = offering.course if offering else None
    faculty = offering.faculty if offering else None

    # If adjustment_data wasn't pre-fetched, query it on demand (for backward compatibility)
    if adjustment_data is None:
        latest_adjustment = (
            FacultyAdjustment.query.filter_by(
                timetable_entry_id=entry.timetable_entry_id,
                status="APPROVED",
            )
            .order_by(FacultyAdjustment.effective_date.desc(), FacultyAdjustment.created_at.desc())
            .first()
        )
        adjustment_data = latest_adjustment.to_dict() if latest_adjustment else None
    elif adjustment_data == {}:
        adjustment_data = None

    return {
        "timetable_entry_id": entry.timetable_entry_id,
        "day_of_week": entry.day_of_week,
        "start_time": entry.start_time.strftime("%H:%M") if entry.start_time else "",
        "end_time": entry.end_time.strftime("%H:%M") if entry.end_time else "",
        "room": entry.room or (offering.room if offering else "Not assigned"),
        "faculty_id": faculty.faculty_id if faculty else None,
        "faculty_name": (
            faculty.user.name
            if faculty and faculty.user
            else "Not assigned"
        ),
        "department_name": (
            faculty.department.department_name
            if faculty and faculty.department
            else ""
        ),
        "course_code": course.course_code if course else "",
        "course_name": course.course_name if course else "",
        "section": offering.section if offering else "",
        "semester": offering.semester if offering else None,
        "academic_year": canonical_academic_year(offering.academic_year) if offering else "",
        "offering_id": offering.offering_id if offering else None,
        "active_adjustment": adjustment_data,
        "effective_faculty_name": (
            adjustment_data["substitute_faculty_name"]
            if adjustment_data
            else (faculty.user.name if faculty and faculty.user else "Not assigned")
        ),
    }


def success_response(entries):
    adjustments_map = {}
    if entries:
        entry_ids = [e.timetable_entry_id for e in entries]
        adjustments = (
            FacultyAdjustment.query
            .filter(
                FacultyAdjustment.timetable_entry_id.in_(entry_ids),
                FacultyAdjustment.status == "APPROVED",
            )
            .options(
                joinedload(FacultyAdjustment.original_faculty).joinedload(Faculty.user),
                joinedload(FacultyAdjustment.substitute_faculty).joinedload(Faculty.user),
                joinedload(FacultyAdjustment.adjusted_by),
                joinedload(FacultyAdjustment.timetable_entry).joinedload(TimetableEntry.offering).joinedload(CourseOffering.course),
            )
            .order_by(
                FacultyAdjustment.effective_date.desc(),
                FacultyAdjustment.created_at.desc(),
            )
            .all()
        )
        for adj in adjustments:
            if adj.timetable_entry_id not in adjustments_map:
                adjustments_map[adj.timetable_entry_id] = adj.to_dict()

    return jsonify({
        "success": True,
        "count": len(entries),
        "data": [
            serialize_entry(
                entry,
                adjustment_data=adjustments_map.get(entry.timetable_entry_id, {})
            )
            for entry in entries
        ],
    }), 200


@timetable_bp.get("/admin")
@admin_required
def get_admin_timetable():
    entries = (
        TimetableEntry.query
        .join(CourseOffering)
        .options(
            joinedload(TimetableEntry.offering).joinedload(CourseOffering.course),
            joinedload(TimetableEntry.offering).joinedload(CourseOffering.faculty).joinedload(Faculty.user),
            joinedload(TimetableEntry.offering).joinedload(CourseOffering.faculty).joinedload(Faculty.department),
        )
        .order_by(
            TimetableEntry.day_of_week,
            TimetableEntry.start_time,
        )
        .all()
    )
    return success_response(entries)


@timetable_bp.get("/faculty")
@faculty_required
def get_faculty_timetable():
    user_id = int(get_jwt_identity())
    faculty = Faculty.query.filter_by(user_id=user_id).first()

    if not faculty:
        return jsonify({
            "success": False,
            "message": "Faculty profile not found",
        }), 404

    offering_id = request.args.get("offering_id", type=int)

    substitute_entry_ids = [
        adj.timetable_entry_id
        for adj in FacultyAdjustment.query.filter_by(
            substitute_faculty_id=faculty.faculty_id,
            status="APPROVED",
        ).all()
    ]

    query = (
        TimetableEntry.query
        .join(CourseOffering)
        .options(
            joinedload(TimetableEntry.offering).joinedload(CourseOffering.course),
            joinedload(TimetableEntry.offering).joinedload(CourseOffering.faculty).joinedload(Faculty.user),
            joinedload(TimetableEntry.offering).joinedload(CourseOffering.faculty).joinedload(Faculty.department),
        )
        .filter(
            db.or_(
                CourseOffering.faculty_id == faculty.faculty_id,
                TimetableEntry.timetable_entry_id.in_(substitute_entry_ids),
            ) if substitute_entry_ids else (CourseOffering.faculty_id == faculty.faculty_id)
        )
    )

    if offering_id is not None:
        query = query.filter(TimetableEntry.offering_id == offering_id)

    day_filter = request.args.get("day") or request.args.get("day_of_week")
    if day_filter and day_filter.strip().lower() not in ["all", "all days", ""]:
        query = query.filter(
            db.func.lower(TimetableEntry.day_of_week) == day_filter.strip().lower()
        )

    entries = (
        query
        .order_by(
            TimetableEntry.day_of_week,
            TimetableEntry.start_time,
        )
        .all()
    )
    return success_response(entries)


@timetable_bp.get("/student")
@student_required
def get_student_timetable():
    user_id = int(get_jwt_identity())
    student = Student.query.filter_by(user_id=user_id).first()
    if not student:
        return jsonify({
            "success": False,
            "message": "Student profile not found",
        }), 404

    enrollments = (
        Enrollment.query
        .options(joinedload(Enrollment.offering))
        .filter_by(
            student_id=student.student_id,
            status="ACTIVE",
        )
        .all()
    )
    if not enrollments:
        return success_response([])

    enrolled_offering_ids = [e.offering_id for e in enrollments if e.offering_id]

    direct_tts = (
        TimetableEntry.query
        .filter(TimetableEntry.offering_id.in_(enrolled_offering_ids))
        .all()
    )
    direct_covered_offering_ids = {tt.offering_id for tt in direct_tts}

    all_target_offering_ids = set(enrolled_offering_ids)

    for enr in enrollments:
        off = enr.offering
        if not off or off.offering_id in direct_covered_offering_ids:
            continue
        candidate_siblings = (
            CourseOffering.query
            .filter(
                CourseOffering.course_id == off.course_id,
                CourseOffering.semester == off.semester,
                CourseOffering.section == off.section,
                CourseOffering.offering_id != off.offering_id,
            )
            .all()
        )
        for sib in candidate_siblings:
            if are_offerings_academically_compatible(
                sib.academic_year, sib.semester,
                off.academic_year, off.semester,
            ):
                all_target_offering_ids.add(sib.offering_id)

    entries = (
        TimetableEntry.query
        .options(
            joinedload(TimetableEntry.offering).joinedload(CourseOffering.course),
            joinedload(TimetableEntry.offering).joinedload(CourseOffering.faculty).joinedload(Faculty.user),
            joinedload(TimetableEntry.offering).joinedload(CourseOffering.faculty).joinedload(Faculty.department),
        )
        .filter(TimetableEntry.offering_id.in_(all_target_offering_ids))
        .order_by(
            TimetableEntry.day_of_week,
            TimetableEntry.start_time,
        )
        .all()
    )

    seen = set()
    deduped_entries = []
    for entry in entries:
        off = entry.offering
        course_id = off.course_id if off else None
        section = (off.section or "").strip().upper() if off else ""
        room = (entry.room or "").strip().upper()
        faculty_id = off.faculty_id if off else None
        day = (entry.day_of_week or "").strip().capitalize()
        start = entry.start_time.strftime("%H:%M:%S") if entry.start_time else ""
        end = entry.end_time.strftime("%H:%M:%S") if entry.end_time else ""

        # Logical slot identity: course, section, day, start, end, room, and faculty
        # Distinct rooms or distinct faculty at the same time represent distinct legitimate sessions
        slot_key = (course_id, section, day, start, end, room, faculty_id)
        if slot_key not in seen:
            seen.add(slot_key)
            deduped_entries.append(entry)

    return success_response(deduped_entries)


# =========================================================
# FACULTY ADJUSTMENT ENDPOINTS
# =========================================================

@timetable_bp.get("/adjustments")
@admin_required
def get_faculty_adjustments():
    """
    Returns faculty adjustments audit history.
    """
    entry_id = request.args.get("timetable_entry_id", type=int)
    status = request.args.get("status")

    query = FacultyAdjustment.query

    if entry_id:
        query = query.filter_by(timetable_entry_id=entry_id)
    if status:
        query = query.filter_by(status=status.upper())

    adjustments = query.order_by(FacultyAdjustment.created_at.desc()).all()

    return jsonify({
        "success": True,
        "count": len(adjustments),
        "data": [adj.to_dict() for adj in adjustments],
    }), 200


@timetable_bp.post("/adjustments")
@admin_required
def create_faculty_adjustment():
    """
    Creates an emergency faculty adjustment for a specific timetable class
    without destroying the original course offering or timetable assignment.
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"success": False, "message": "JSON payload required."}), 400

    timetable_entry_id = data.get("timetable_entry_id")
    substitute_faculty_id = data.get("substitute_faculty_id")
    effective_date_str = data.get("effective_date")
    reason = str(data.get("reason") or "").strip()
    request_approval = bool(data.get("request_approval", False))

    if not timetable_entry_id:
        return jsonify({"success": False, "message": "A specific timetable class must be selected."}), 400

    entry = db.session.get(TimetableEntry, timetable_entry_id)
    if not entry:
        return jsonify({"success": False, "message": "Selected timetable entry not found."}), 404

    offering = entry.offering
    if not offering:
        return jsonify({"success": False, "message": "Course offering for entry not found."}), 404

    original_faculty_id = offering.faculty_id
    if not original_faculty_id:
        return jsonify({
            "success": False,
            "message": "The selected class does not have an original faculty assigned to replace.",
        }), 400

    if not substitute_faculty_id:
        return jsonify({"success": False, "message": "Please choose a valid substitute faculty member."}), 400

    if int(substitute_faculty_id) == int(original_faculty_id):
        return jsonify({
            "success": False,
            "message": "The substitute faculty must be different from the currently assigned faculty.",
        }), 400

    substitute_faculty = db.session.get(Faculty, substitute_faculty_id)
    if not substitute_faculty:
        return jsonify({"success": False, "message": "Substitute faculty record not found."}), 404

    if not reason:
        return jsonify({"success": False, "message": "Reason for faculty adjustment is required."}), 400

    if not effective_date_str:
        return jsonify({"success": False, "message": "Effective date is required."}), 400

    try:
        effective_date = datetime.strptime(effective_date_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"success": False, "message": "Invalid date format. Use YYYY-MM-DD."}), 400

    # Conflict check 1: Substitute faculty's regular timetable overlap
    substitute_entries = (
        TimetableEntry.query
        .join(CourseOffering)
        .filter(
            CourseOffering.faculty_id == substitute_faculty_id,
            TimetableEntry.day_of_week == entry.day_of_week,
            TimetableEntry.timetable_entry_id != entry.timetable_entry_id,
        )
        .all()
    )
    for se in substitute_entries:
        if max(entry.start_time, se.start_time) < min(entry.end_time, se.end_time):
            course_label = se.offering.course.course_code if se.offering and se.offering.course else "another class"
            return jsonify({
                "success": False,
                "message": (
                    f"Substitute faculty {substitute_faculty.user.name} already has a scheduled class "
                    f"({course_label}) on {entry.day_of_week} ({se.start_time.strftime('%H:%M')}–{se.end_time.strftime('%H:%M')})."
                ),
            }), 409

    # Conflict check 2: Substitute faculty's other active adjustments on the same date and overlapping time
    other_adjustments = (
        FacultyAdjustment.query
        .filter(
            FacultyAdjustment.substitute_faculty_id == substitute_faculty_id,
            FacultyAdjustment.effective_date == effective_date,
            FacultyAdjustment.status == "APPROVED",
            FacultyAdjustment.timetable_entry_id != entry.timetable_entry_id,
        )
        .all()
    )
    for adj in other_adjustments:
        other_entry = adj.timetable_entry
        if other_entry and other_entry.day_of_week == entry.day_of_week:
            if max(entry.start_time, other_entry.start_time) < min(entry.end_time, other_entry.end_time):
                return jsonify({
                    "success": False,
                    "message": (
                        f"Substitute faculty {substitute_faculty.user.name} is already substituting for another class "
                        f"on {effective_date_str} at this time ({other_entry.start_time.strftime('%H:%M')}–{other_entry.end_time.strftime('%H:%M')})."
                    ),
                }), 409

    admin_user_id = int(get_jwt_identity())
    adjustment_status = "PENDING" if request_approval else "APPROVED"

    adjustment = FacultyAdjustment(
        timetable_entry_id=entry.timetable_entry_id,
        original_faculty_id=original_faculty_id,
        substitute_faculty_id=substitute_faculty_id,
        adjusted_by_user_id=admin_user_id,
        effective_date=effective_date,
        reason=reason,
        status=adjustment_status,
        created_at=datetime.utcnow(),
    )

    db.session.add(adjustment)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": (
            f"Faculty adjustment successfully recorded for {substitute_faculty.user.name}. "
            f"Original assignment preserved in audit log."
        ),
        "data": adjustment.to_dict(),
    }), 201


@timetable_bp.post("/adjustments/<int:adjustment_id>/cancel")
@admin_required
def cancel_faculty_adjustment(adjustment_id):
    """
    Cancels an active or pending faculty adjustment.
    """
    adjustment = db.session.get(FacultyAdjustment, adjustment_id)
    if not adjustment:
        return jsonify({"success": False, "message": "Adjustment record not found."}), 404

    adjustment.status = "CANCELLED"
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Faculty adjustment has been cancelled. Timetable reverted to original assignment.",
        "data": adjustment.to_dict(),
    }), 200


@timetable_bp.route("/<int:entry_id>", methods=["PUT", "PATCH"])
@admin_required
def update_timetable_entry(entry_id):
    """
    Updates an existing timetable entry directly (day of week, start time, end time, room).
    Validates time formats, ensures end_time > start_time, checks for faculty/room conflicts,
    and updates transactionally without creating duplicate entries.
    """
    entry = db.session.get(TimetableEntry, entry_id)
    if not entry:
        return jsonify({
            "success": False,
            "message": f"Timetable entry with ID {entry_id} not found.",
            "field": "timetable_entry_id",
        }), 404

    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return jsonify({
            "success": False,
            "message": "Valid JSON body is required.",
        }), 400

    # Validate offering if provided
    if "offering_id" in data and data["offering_id"] is not None:
        try:
            req_offering_id = int(data["offering_id"])
            if req_offering_id != entry.offering_id:
                return jsonify({
                    "success": False,
                    "message": "Timetable entry does not belong to the expected course offering.",
                    "field": "offering_id",
                }), 400
        except (ValueError, TypeError):
            return jsonify({
                "success": False,
                "message": "Invalid offering_id provided.",
                "field": "offering_id",
            }), 400

    # Day of week normalization & validation
    day_mapping = {
        "MON": "Monday",
        "MONDAY": "Monday",
        "TUE": "Tuesday",
        "TUES": "Tuesday",
        "TUESDAY": "Tuesday",
        "WED": "Wednesday",
        "WEDNESDAY": "Wednesday",
        "THU": "Thursday",
        "THUR": "Thursday",
        "THURS": "Thursday",
        "THURSDAY": "Thursday",
        "FRI": "Friday",
        "FRIDAY": "Friday",
        "SAT": "Saturday",
        "SATURDAY": "Saturday",
        "SUN": "Sunday",
        "SUNDAY": "Sunday",
    }

    target_day = entry.day_of_week
    if "day_of_week" in data and data["day_of_week"] is not None:
        cleaned_day = str(data["day_of_week"]).strip().upper()
        if cleaned_day not in day_mapping:
            return jsonify({
                "success": False,
                "message": "Invalid day of week. Allowed values: Monday through Sunday.",
                "field": "day_of_week",
            }), 400
        target_day = day_mapping[cleaned_day]

    # Time validation
    time_re = re.compile(r"^([01]?\d|2[0-3]):([0-5]\d)(?::[0-5]\d)?$")

    start_time_val = data.get("start_time")
    if start_time_val is None:
        start_t = entry.start_time
    else:
        s_str = str(start_time_val).strip()
        m_start = time_re.match(s_str)
        if not m_start:
            return jsonify({
                "success": False,
                "message": "Invalid start time format. Use HH:MM in 24-hour format.",
                "field": "start_time",
            }), 400
        start_t = time(int(m_start.group(1)), int(m_start.group(2)))

    end_time_val = data.get("end_time")
    if end_time_val is None:
        end_t = entry.end_time
    else:
        e_str = str(end_time_val).strip()
        m_end = time_re.match(e_str)
        if not m_end:
            return jsonify({
                "success": False,
                "message": "Invalid end time format. Use HH:MM in 24-hour format.",
                "field": "end_time",
            }), 400
        end_t = time(int(m_end.group(1)), int(m_end.group(2)))

    if start_t >= end_t:
        return jsonify({
            "success": False,
            "message": "End time must be later than start time.",
            "field": "end_time",
        }), 400

    # Room validation
    if "room" in data:
        raw_room = data.get("room")
        if raw_room is None:
            target_room = None
        else:
            target_room = str(raw_room).strip()
            if len(target_room) > 50:
                return jsonify({
                    "success": False,
                    "message": "Room name cannot exceed 50 characters.",
                    "field": "room",
                }), 400
            if target_room in ["", "Not assigned", "None", "null"]:
                target_room = None
    else:
        target_room = entry.room

    # Conflict Check 1: Faculty overlap
    offering = entry.offering
    faculty_id = offering.faculty_id if offering else None
    if faculty_id:
        # Check standard timetable entries for the same faculty on target_day
        fac_entries = (
            TimetableEntry.query
            .join(CourseOffering)
            .filter(
                CourseOffering.faculty_id == faculty_id,
                db.func.lower(TimetableEntry.day_of_week) == target_day.lower(),
                TimetableEntry.timetable_entry_id != entry.timetable_entry_id,
            )
            .all()
        )
        for te in fac_entries:
            if max(start_t, te.start_time) < min(end_t, te.end_time):
                c_code = te.offering.course.course_code if te.offering and te.offering.course else "another class"
                fac_name = te.offering.faculty.user.name if te.offering and te.offering.faculty and te.offering.faculty.user else "Faculty"
                return jsonify({
                    "success": False,
                    "message": (
                        f"Faculty {fac_name} already has a scheduled class ({c_code}) "
                        f"on {target_day} ({te.start_time.strftime('%H:%M')}–{te.end_time.strftime('%H:%M')})."
                    ),
                    "field": "start_time",
                }), 409

        # Check substitute adjustments where this faculty is substituting for another class
        sub_adjs = (
            FacultyAdjustment.query
            .filter(
                FacultyAdjustment.substitute_faculty_id == faculty_id,
                FacultyAdjustment.status == "APPROVED",
                FacultyAdjustment.timetable_entry_id != entry.timetable_entry_id,
            )
            .all()
        )
        for adj in sub_adjs:
            te = adj.timetable_entry
            if te and te.day_of_week.lower() == target_day.lower():
                if max(start_t, te.start_time) < min(end_t, te.end_time):
                    fac_name = offering.faculty.user.name if offering and offering.faculty and offering.faculty.user else "Faculty"
                    return jsonify({
                        "success": False,
                        "message": (
                            f"Faculty {fac_name} is already substituting for another class "
                            f"on {target_day} ({te.start_time.strftime('%H:%M')}–{te.end_time.strftime('%H:%M')})."
                        ),
                        "field": "start_time",
                    }), 409

    # Conflict Check 2: Room overlap
    if target_room:
        room_entries = (
            TimetableEntry.query
            .join(CourseOffering)
            .filter(
                db.func.lower(TimetableEntry.day_of_week) == target_day.lower(),
                TimetableEntry.timetable_entry_id != entry.timetable_entry_id,
                db.or_(
                    db.func.lower(TimetableEntry.room) == target_room.lower(),
                    db.and_(
                        TimetableEntry.room.is_(None),
                        db.func.lower(CourseOffering.room) == target_room.lower(),
                    ),
                ),
            )
            .all()
        )
        for te in room_entries:
            te_ay = canonical_academic_year(te.offering.academic_year) if te.offering else ""
            entry_ay = canonical_academic_year(entry.offering.academic_year) if entry.offering else ""
            if not te_ay or not entry_ay or te_ay == entry_ay:
                if max(start_t, te.start_time) < min(end_t, te.end_time):
                    c_code = te.offering.course.course_code if te.offering and te.offering.course else "another class"
                    return jsonify({
                        "success": False,
                        "message": (
                            f"Room {target_room} is already booked on {target_day} "
                            f"({te.start_time.strftime('%H:%M')}–{te.end_time.strftime('%H:%M')}) for {c_code}."
                        ),
                        "field": "room",
                    }), 409

    # Conflict Check 3: Section overlap
    if offering and offering.section:
        sec_entries = (
            TimetableEntry.query
            .join(CourseOffering)
            .filter(
                CourseOffering.semester == offering.semester,
                CourseOffering.section == offering.section,
                db.func.lower(TimetableEntry.day_of_week) == target_day.lower(),
                TimetableEntry.timetable_entry_id != entry.timetable_entry_id,
            )
            .all()
        )
        for te in sec_entries:
            te_ay = canonical_academic_year(te.offering.academic_year) if te.offering else ""
            entry_ay = canonical_academic_year(entry.offering.academic_year) if entry.offering else ""
            if not te_ay or not entry_ay or te_ay == entry_ay:
                if max(start_t, te.start_time) < min(end_t, te.end_time):
                    c_code = te.offering.course.course_code if te.offering and te.offering.course else "another class"
                    return jsonify({
                        "success": False,
                        "message": (
                            f"Section {offering.section} (Sem {offering.semester}) already has a scheduled class ({c_code}) "
                            f"on {target_day} ({te.start_time.strftime('%H:%M')}–{te.end_time.strftime('%H:%M')})."
                        ),
                        "field": "start_time",
                    }), 409

    # Transactional update
    entry.day_of_week = target_day
    entry.start_time = start_t
    entry.end_time = end_t
    entry.room = target_room

    db.session.commit()

    admin_user_id = int(get_jwt_identity())
    admin_user = db.session.get(User, admin_user_id)
    admin_name = admin_user.name if admin_user else f"Admin {admin_user_id}"

    record_activity(
        action_type="TIMETABLE_ENTRY_UPDATED",
        description=(
            f"Updated timetable entry #{entry.timetable_entry_id}: "
            f"{entry.day_of_week} {entry.start_time.strftime('%H:%M')}–{entry.end_time.strftime('%H:%M')}, "
            f"Room: {entry.room or 'Not assigned'}"
        ),
        actor_id=admin_user_id,
        actor_name=admin_name,
        entity_type="TimetableEntry",
        entity_id=entry.timetable_entry_id,
        details={
            "timetable_entry_id": entry.timetable_entry_id,
            "day_of_week": entry.day_of_week,
            "start_time": entry.start_time.strftime("%H:%M"),
            "end_time": entry.end_time.strftime("%H:%M"),
            "room": entry.room,
        },
    )

    return jsonify({
        "success": True,
        "message": "Timetable entry updated successfully.",
        "data": serialize_entry(entry),
    }), 200
