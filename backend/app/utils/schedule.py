import os
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo
from flask import current_app, has_app_context

from app.extensions import db
from app.models import (
    AttendanceRecord,
    AttendanceSession,
    Enrollment,
    FacultyAdjustment,
    TimetableEntry,
)


def get_institution_timezone() -> ZoneInfo:
    """Return the institution's configured timezone as a ZoneInfo object."""
    tz_name = "Asia/Kolkata"
    if has_app_context():
        tz_name = current_app.config.get("INSTITUTION_TIMEZONE") or tz_name
    else:
        tz_name = os.getenv("INSTITUTION_TIMEZONE", tz_name)

    try:
        return ZoneInfo(tz_name)
    except Exception:
        return ZoneInfo("Asia/Kolkata")


def get_current_institution_time() -> datetime:
    """Return the current timezone-aware datetime in the institution's timezone."""
    tz = get_institution_timezone()
    now = datetime.now(tz)
    return now


def get_timetable_window(
    session_date: date,
    start_time: time,
    end_time: time,
    tz: ZoneInfo = None,
) -> tuple[datetime, datetime]:
    """
    Construct timezone-aware start and end datetimes for a class window.
    Handles overnight classes crossing midnight by advancing end_dt to the next day.
    """
    if tz is None:
        tz = get_institution_timezone()

    start_dt = datetime.combine(session_date, start_time).replace(tzinfo=tz)
    if end_time <= start_time:
        # Class window crosses midnight into the next day
        end_dt = datetime.combine(session_date + timedelta(days=1), end_time).replace(tzinfo=tz)
    else:
        end_dt = datetime.combine(session_date, end_time).replace(tzinfo=tz)

    return start_dt, end_dt


def evaluate_timetable_window(
    session_date: date,
    start_time: time,
    end_time: time,
    current_dt: datetime = None,
    tz: ZoneInfo = None,
) -> tuple[bool, str, datetime, datetime]:
    """
    Evaluate if current_dt is within [start_dt, end_dt).
    Boundary policy:
    - start is inclusive
    - end is exclusive: start_dt <= current_dt < end_dt
    Returns (is_active, status_str, start_dt, end_dt).
    status_str in {"UPCOMING", "ACTIVE", "ENDED"}.
    """
    if tz is None:
        tz = get_institution_timezone()

    if current_dt is None:
        current_dt = get_current_institution_time()

    if current_dt.tzinfo is None:
        current_dt = current_dt.replace(tzinfo=tz)
    else:
        current_dt = current_dt.astimezone(tz)

    start_dt, end_dt = get_timetable_window(session_date, start_time, end_time, tz=tz)

    if current_dt < start_dt:
        return False, "UPCOMING", start_dt, end_dt
    elif current_dt >= end_dt:
        return False, "ENDED", start_dt, end_dt
    else:
        return True, "ACTIVE", start_dt, end_dt


def close_expired_session(session: AttendanceSession, end_time_val: time = None) -> AttendanceSession:
    """
    Applies the existing session-closing workflow to an expired session:
    - Automatically marks unrecorded active enrolled students as ABSENT (SYSTEM).
    - Sets session.status = 'CLOSED'.
    - Updates end_time.
    - Commits changes safely.
    """
    if not session or session.status != "ACTIVE":
        return session

    active_enrollments = Enrollment.query.filter_by(
        offering_id=session.offering_id,
        status="ACTIVE",
    ).all()

    existing_records = AttendanceRecord.query.filter_by(
        session_id=session.session_id,
    ).all()
    recorded_student_ids = {r.student_id for r in existing_records}

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

    if not session.end_time:
        session.end_time = end_time_val or get_current_institution_time().time()

    session.status = "CLOSED"

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return session


def reconcile_premature_session(session: AttendanceSession) -> AttendanceSession:
    """
    Safely reconciles a future / premature active session without deleting historical records.
    Sets status to 'SCHEDULED' so it does not report as active or permit early attendance.
    """
    if not session or session.status != "ACTIVE":
        return session

    session.status = "SCHEDULED"
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return session


def get_offering_authoritative_entry(
    offering_id: int,
    target_date: date = None,
    timetable_entry_id: int = None,
    target_time: time = None,
) -> TimetableEntry | None:
    """
    Finds the authoritative TimetableEntry for a course offering on target_date.
    Uses timetable_entry_id if provided, exact start_time if provided,
    or active/upcoming schedule status if multiple entries exist on the target day.
    """
    if timetable_entry_id:
        te = db.session.get(TimetableEntry, timetable_entry_id)
        if te and te.offering_id == offering_id:
            return te

    if target_date is None:
        target_date = get_current_institution_time().date()

    day_name = target_date.strftime("%A")

    day_entries = (
        TimetableEntry.query
        .filter(
            TimetableEntry.offering_id == offering_id,
            db.func.lower(TimetableEntry.day_of_week) == day_name.lower(),
        )
        .order_by(TimetableEntry.start_time.asc())
        .all()
    )

    if day_entries:
        # 1. If target_time is given, check for exact start_time match
        if target_time:
            exact_match = [e for e in day_entries if e.start_time == target_time]
            if exact_match:
                return exact_match[0]
            # Check if target_time falls within slot window [start_time, end_time)
            window_match = [e for e in day_entries if e.start_time <= target_time < e.end_time]
            if window_match:
                return window_match[0]

        # 2. If exactly one slot exists on this day, return it
        if len(day_entries) == 1:
            return day_entries[0]

        # 3. If multiple slots exist on this day, check if one is currently ACTIVE
        now = get_current_institution_time()
        active_entries = [
            e for e in day_entries
            if evaluate_timetable_window(target_date, e.start_time, e.end_time, current_dt=now)[1] == "ACTIVE"
        ]
        if len(active_entries) == 1:
            return active_entries[0]

        # 4. If none is active, check if one is UPCOMING
        upcoming_entries = [
            e for e in day_entries
            if evaluate_timetable_window(target_date, e.start_time, e.end_time, current_dt=now)[1] == "UPCOMING"
        ]
        if upcoming_entries:
            return upcoming_entries[0]

        # 5. Otherwise return the latest ended slot
        return day_entries[-1]

    # Fallback to any offering entry in database
    return (
        TimetableEntry.query
        .filter_by(offering_id=offering_id)
        .order_by(TimetableEntry.timetable_entry_id.asc())
        .first()
    )


def get_session_schedule_status(
    session: AttendanceSession,
    current_dt: datetime = None,
) -> tuple[bool, str, dict]:
    """
    Evaluates the scheduled timetable window for a session.
    Returns:
    (is_eligible_for_attendance: bool, status_str: str, details: dict)
    status_str in {"UPCOMING", "ACTIVE", "ENDED", "CLOSED"}.
    """
    if not session:
        return False, "NONE", {"message": "No session provided"}

    if session.status == "CLOSED":
        return False, "CLOSED", {"message": "Attendance session is closed"}

    if current_dt is None:
        current_dt = get_current_institution_time()

    session_date = session.session_date or current_dt.date()

    # Look up authoritative timetable entry for this offering on session_date
    te = get_offering_authoritative_entry(
        session.offering_id,
        session_date,
        target_time=session.start_time,
    )

    if te:
        start_time = te.start_time
        end_time = te.end_time
    else:
        start_time = session.start_time
        end_time = session.end_time

    if not start_time:
        start_time = time(9, 0)
    if not end_time:
        end_time = (datetime.combine(session_date, start_time) + timedelta(hours=1)).time()

    is_active, status_str, start_dt, end_dt = evaluate_timetable_window(
        session_date, start_time, end_time, current_dt=current_dt
    )

    details = {
        "session_id": session.session_id,
        "offering_id": session.offering_id,
        "start_time": start_time.strftime("%H:%M"),
        "end_time": end_time.strftime("%H:%M"),
        "start_dt": start_dt,
        "end_dt": end_dt,
        "status": status_str,
    }

    if status_str == "UPCOMING":
        details["message"] = (
            f"Class is scheduled for {start_time.strftime('%I:%M %p')}. "
            f"Attendance cannot be started or recorded before the scheduled start time."
        )
    elif status_str == "ENDED":
        details["message"] = (
            f"Class scheduled window ended at {end_time.strftime('%I:%M %p')}. "
            f"New attendance recording is prevented."
        )
    else:
        details["message"] = "Attendance session is currently active within scheduled class hours."

    return is_active, status_str, details
