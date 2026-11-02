import re
from datetime import datetime

from app.extensions import db
from app.models.course_offering import CourseOffering
from app.models.system_setting import SystemSetting


def canonical_academic_year(val):
    """
    Normalizes academic year format to YYYY-YYYY.
    E.g.: '2024 - 2025' -> '2024-2025', '2025-26' -> '2025-2026'.
    """
    if not val:
        return ""
    s = str(val).strip()
    s = re.sub(r"\s*-\s*", "-", s)
    m = re.match(r"^(\d{4})-(\d{2})$", s)
    if m:
        century = m.group(1)[:2]
        return f"{m.group(1)}-{century}{m.group(2)}"
    return s


def is_single_academic_session(val):
    """
    Checks if a string represents a 1-year academic session (e.g. 2024-2025).
    """
    c = canonical_academic_year(val)
    m = re.match(r"^(\d{4})-(\d{4})$", c)
    if m:
        start_y, end_y = int(m.group(1)), int(m.group(2))
        return end_y - start_y == 1
    return False


def is_batch_cohort(val):
    """
    Checks if a string represents a multi-year degree cohort (e.g. 2024-2028 or 2024).
    """
    if not val:
        return False
    s = str(val).strip()
    c = canonical_academic_year(s)
    m = re.match(r"^(\d{4})-(\d{4})$", c)
    if m:
        return int(m.group(2)) - int(m.group(1)) > 1
    m4 = re.match(r"^\d{4}$", s)
    return bool(m4)


def resolve_offering_academic_year(val, semester=None, batch=None):
    """
    Resolves any course offering academic_year value into a canonical 1-year
    teaching academic session (e.g. '2025-2026').
    If a legacy multi-year cohort range (e.g. '2026-2030' or '2026-2032') or a single
    batch year (e.g. '2026') was stored, normalizes it using progression semester:
      offset = (semester - 1) // 2
      teaching_session = f"{start_year + offset}-{start_year + offset + 1}"
    If a 1-year session was mistakenly stamped with the cohort admission year (e.g. '2024-2025'
    for Semester 5 of Batch 2024), advances it according to progression offset.
    """
    if not val and not batch:
        return get_current_academic_session()

    sem_num = 1
    if semester is not None:
        try:
            sem_num = max(1, int(semester))
        except (ValueError, TypeError):
            sem_num = 1
    year_offset = (sem_num - 1) // 2

    batch_start = None
    if batch:
        b_str = extract_cohort_start_year(str(batch))
        if b_str and b_str.isdigit() and len(b_str) == 4:
            batch_start = int(b_str)

    if not val:
        if batch_start:
            teaching_start = batch_start + year_offset
            return f"{teaching_start}-{teaching_start + 1}"
        return get_current_academic_session()

    s = str(val).strip()
    canon = canonical_academic_year(s)

    val_start_str = extract_cohort_start_year(s)
    val_start = int(val_start_str) if val_start_str and val_start_str.isdigit() and len(val_start_str) == 4 else None

    # If canon is a single 1-year academic session:
    if is_single_academic_session(canon):
        if batch_start and val_start and val_start < (batch_start + year_offset):
            teaching_start = batch_start + year_offset
            return f"{teaching_start}-{teaching_start + 1}"
        return canon

    # Otherwise multi-year cohort range (e.g. '2026 -2032') or single year:
    effective_start = val_start or batch_start
    if effective_start:
        teaching_start = effective_start + year_offset
        return f"{teaching_start}-{teaching_start + 1}"

    return canon


def are_offerings_academically_compatible(ay1, sem1, ay2, sem2) -> bool:
    """
    Determines whether two course offerings belong to the same academic teaching session.
    - Normalizes and compares 1-year sessions (e.g. '2026-2027' and '2026 - 2027').
    - Disallows cross-session matching between distinct academic years (e.g. '2024-2025' and '2026-2027').
    - If both offerings have valid academic sessions, they must be canonically identical.
    - If either is unassigned (None or empty), they are treated as compatible (no conflict).
    """
    if not ay1 or not ay2:
        return True

    canon1 = canonical_academic_year(ay1)
    canon2 = canonical_academic_year(ay2)

    if is_single_academic_session(canon1) and is_single_academic_session(canon2):
        return canon1 == canon2

    res1 = resolve_offering_academic_year(ay1, sem1)
    res2 = resolve_offering_academic_year(ay2, sem2)
    return res1 == res2


def format_batch_cohort(val, duration_years=4):
    """
    Standardizes a batch cohort to YYYY-YYYY format (e.g. '2024-2028').
    Accepts '2024', '2024-2028', '2024 -2028'.
    """
    if not val:
        return ""
    s = str(val).strip()
    s = re.sub(r"\s*-\s*", "-", s)
    m = re.match(r"^(\d{4})-(\d{4})$", s)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    m4 = re.match(r"^(\d{4})$", s)
    if m4:
        start_year = int(m4.group(1))
        return f"{start_year}-{start_year + duration_years}"
    return s


def extract_cohort_start_year(val):
    """
    Extracts the 4-digit admission or start year from a batch or date string.
    E.g. '2024-2028' -> '2024', '2024' -> '2024', '2024-08-15' -> '2024'.
    """
    if not val:
        return ""
    s = str(val).strip()
    m = re.match(r"^(\d{4})", s)
    if m:
        return m.group(1)
    return ""


def get_system_setting(key, default=None):
    """Retrieve a persisted system setting."""
    try:
        row = SystemSetting.query.filter_by(setting_key=key).first()
        if row and row.setting_value:
            return row.setting_value.strip()
    except Exception:
        # Table might not exist yet or connection issue
        pass
    return default


def set_system_setting(key, value):
    """Persist or update a system setting."""
    row = SystemSetting.query.filter_by(setting_key=key).first()
    if row:
        row.setting_value = str(value).strip()
    else:
        row = SystemSetting(setting_key=key, setting_value=str(value).strip())
        db.session.add(row)
    db.session.commit()
    return row.setting_value


def get_current_academic_session():
    """
    Returns the authoritative institutional current academic session (e.g. '2026-2027').
    Prioritizes:
    1. Administrator-controlled setting in system_settings ('current_academic_year').
    2. Latest active 1-year academic session from course offerings.
    3. Calendar calculation ({year}-{year+1} if month >= 6 else {year-1}-{year}).
    """
    persisted = get_system_setting("current_academic_year")
    if persisted and is_single_academic_session(persisted):
        return canonical_academic_year(persisted)

    # Check database offerings for valid 1-year sessions
    try:
        raw_years = [
            r[0] for r in db.session.query(CourseOffering.academic_year).distinct().all() if r[0]
        ]
        valid_sessions = sorted(
            [canonical_academic_year(y) for y in raw_years if is_single_academic_session(y)],
            reverse=True,
        )
        if valid_sessions:
            return valid_sessions[0]
    except Exception:
        pass

    now = datetime.now()
    cur_y = now.year
    # In academic calendars, session starts mid-year (June/July)
    if now.month >= 6:
        return f"{cur_y}-{cur_y + 1}"
    return f"{cur_y - 1}-{cur_y}"


def set_current_academic_session(session_str):
    """
    Administrator updates the institution's current academic session.
    Validates that it is a 1-year academic session (e.g. '2026-2027').
    """
    canonical = canonical_academic_year(session_str)
    if not is_single_academic_session(canonical):
        raise ValueError(
            f"Invalid academic session '{session_str}'. Must be a 1-year session in format YYYY-YYYY, e.g. '2026-2027'."
        )
    return set_system_setting("current_academic_year", canonical)


def get_available_academic_sessions():
    """
    Returns list of distinct 1-year academic sessions from offerings, system setting, and adjacent years.
    """
    sessions = set()
    current_session = get_current_academic_session()
    sessions.add(current_session)

    try:
        raw_years = [
            r[0] for r in db.session.query(CourseOffering.academic_year).distinct().all() if r[0]
        ]
        for y in raw_years:
            if is_single_academic_session(y):
                sessions.add(canonical_academic_year(y))
    except Exception:
        pass

    # Add surrounding sessions for admin selector
    cur_start = int(current_session.split("-")[0])
    for offset in range(-3, 3):
        start_y = cur_start + offset
        sessions.add(f"{start_y}-{start_y + 1}")

    return sorted(list(sessions), reverse=True)


def resolve_student_academic_info(student):
    """
    Authoritative helper to resolve:
    - batch_year: Degree cohort range (e.g. '2024-2028')
    - admission_year: 4-digit admission year (e.g. '2024')
    - academic_year: Student's current academic session (e.g. '2026-2027')
    - semester: Current progression semester (e.g. 5)
    - section: Section (e.g. 'A')
    """
    batch_raw = student.batch.batch_name if student.batch else None
    if not batch_raw and is_batch_cohort(student.academic_year):
        batch_raw = student.academic_year

    batch_year = format_batch_cohort(batch_raw) if batch_raw else ""
    admission_year = extract_cohort_start_year(batch_raw or student.admission_date or "")

    # Determine student's active academic session
    session = None
    if student.enrollments:
        enrolled_sessions = [
            canonical_academic_year(e.offering.academic_year)
            for e in student.enrollments
            if e.offering and is_single_academic_session(e.offering.academic_year)
        ]
        if enrolled_sessions:
            session = sorted(enrolled_sessions, reverse=True)[0]

    if not session:
        if is_single_academic_session(student.academic_year):
            session = canonical_academic_year(student.academic_year)
        else:
            session = get_current_academic_session()

    return {
        "batch_year": batch_year,
        "batch_name": batch_year,
        "admission_year": admission_year,
        "academic_year": session,
        "semester": student.semester,
        "section": student.section,
    }
