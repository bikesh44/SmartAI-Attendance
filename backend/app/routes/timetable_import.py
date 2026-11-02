
import re
from datetime import datetime, time
from io import BytesIO

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity
from openpyxl import load_workbook

from app.extensions import db
from app.services.activity_service import record_activity
from app.models import (
    Course,
    CourseOffering,
    Faculty,
    FacultyAdjustment,
    Student,
    TimetableEntry,
    User,
)
from app.utils.auth import admin_required
from app.utils.academic_year import (
    canonical_academic_year,
    get_available_academic_sessions,
    get_current_academic_session,
    is_batch_cohort,
    is_single_academic_session,
)

timetable_import_bp = Blueprint(
    "timetable_import",
    __name__,
    url_prefix="/api/timetable/import",
)

SHEET_NAME = "05.10.2026 Updated Time Table"
MAX_FILE_SIZE = 10 * 1024 * 1024

# Time range pattern supporting:
# "09:30 AM - 10:30 AM", "9:30am - 10:30am", "09:30-10:30", "9:30 to 10:30", en-dash and em-dash
TIME_PATTERN_12H = re.compile(
    r"^\s*(\d{1,2}:\d{2}\s*[ap]m)\s*(?:-|–|—|to)\s*(\d{1,2}:\d{2}\s*[ap]m)\s*$",
    re.IGNORECASE,
)
TIME_PATTERN_24H = re.compile(
    r"^\s*(\d{1,2}:\d{2})\s*(?:-|–|—|to)\s*(\d{1,2}:\d{2})\s*$",
    re.IGNORECASE,
)

COURSE_CODE_PATTERN = re.compile(
    r"\b([A-Z]{2,6}[-\s]?\d{3,4}[A-Z]?)\b",
    re.IGNORECASE,
)
ROOM_PATTERN = re.compile(
    r"\b(?:Room|Rm|Lab|Hall)[-\s]*([A-Za-z0-9\-]+)|\b([RL][-\s]*\d{2,4})\b|(?:,\s*|\s+)(\d{3,4}[A-Za-z]?)$",
    re.IGNORECASE,
)
FACULTY_TITLE_PATTERN = re.compile(
    r"\b(?:Dr\.|Mr\.|Ms\.|Mrs\.|Prof\.)\s+([A-Za-z]+(?:\s+[A-Za-z]+)*)",
    re.IGNORECASE,
)

DAY_NORMALIZATION = {
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
    "THRUSDAY": "Thursday",
    "FRI": "Friday",
    "FRIDAY": "Friday",
    "SAT": "Saturday",
    "SATURDAY": "Saturday",
    "SUN": "Sunday",
    "SUNDAY": "Sunday",
}


def clean(value):
    if value is None:
        return ""
    return str(value).strip()


def canonical_academic_year(val):
    if not val:
        return ""
    s = str(val).strip()
    s = re.sub(r"\s*-\s*", "-", s)
    m = re.match(r"^(\d{4})-(\d{2})$", s)
    if m:
        century = m.group(1)[:2]
        return f"{m.group(1)}-{century}{m.group(2)}"
    return s


def normalize_day(value):
    cleaned = clean(value).upper()
    return DAY_NORMALIZATION.get(cleaned, cleaned.capitalize() if cleaned else "")


def normalize_time_str(val):
    if not val:
        return None
    if isinstance(val, time):
        return val.strftime("%H:%M")
    if isinstance(val, datetime):
        return val.time().strftime("%H:%M")
    s = str(val).strip()
    m12 = re.match(r"^(\d{1,2}):(\d{2})\s*([ap]m)$", s, re.IGNORECASE)
    if m12:
        hr = int(m12.group(1))
        mn = int(m12.group(2))
        ampm = m12.group(3).lower()
        if ampm == "pm" and hr < 12:
            hr += 12
        elif ampm == "am" and hr == 12:
            hr = 0
        return f"{hr:02d}:{mn:02d}"
    m24 = re.match(r"^(\d{1,2}):(\d{2})$", s)
    if m24:
        return f"{int(m24.group(1)):02d}:{int(m24.group(2)):02d}"
    return None


def parse_time_range(value):
    val_clean = clean(value)
    if not val_clean:
        return None, None

    match_12 = TIME_PATTERN_12H.match(val_clean)
    if match_12:
        try:
            start = datetime.strptime(
                match_12.group(1).replace(" ", "").lower(),
                "%I:%M%p",
            ).strftime("%H:%M")
            end = datetime.strptime(
                match_12.group(2).replace(" ", "").lower(),
                "%I:%M%p",
            ).strftime("%H:%M")
            return start, end
        except ValueError:
            pass

    match_24 = TIME_PATTERN_24H.match(val_clean)
    if match_24:
        try:
            start_parts = [int(p) for p in match_24.group(1).split(":")]
            end_parts = [int(p) for p in match_24.group(2).split(":")]
            start = f"{start_parts[0]:02d}:{start_parts[1]:02d}"
            end = f"{end_parts[0]:02d}:{end_parts[1]:02d}"
            return start, end
        except (ValueError, IndexError):
            pass

    return None, None


HEADER_ALIASES = {
    "day": ["DAY", "DAYS", "DAY OF WEEK", "DAY_OF_WEEK", "WEEKDAY"],
    "period": ["PERIOD", "P.NO.", "P.NO", "PERIOD NO", "P. NO.", "PERIOD NUMBER", "SLOT"],
    "time": ["TIME", "TIMING", "TIMINGS", "TIME SLOT", "TIME RANGE", "SCHEDULE"],
    "start_time": ["START TIME", "START_TIME", "START", "FROM"],
    "end_time": ["END TIME", "END_TIME", "END", "TO", "UNTIL"],
    "course_code": ["COURSE CODE", "COURSE_CODE", "SUBJECT CODE", "SUB CODE", "CODE"],
    "course_name": ["COURSE NAME", "COURSE_NAME", "SUBJECT NAME", "SUB NAME", "COURSE", "SUBJECT", "TITLE"],
    "faculty_id": ["FACULTY ID", "FACULTY_ID", "TEACHER ID", "EMP ID", "EMPLOYEE ID", "FACULTY CODE"],
    "faculty_name": ["FACULTY NAME", "FACULTY_NAME", "TEACHER NAME", "FACULTY", "INSTRUCTOR", "TEACHER", "PROFESSOR"],
    "semester": ["SEMESTER", "SEM"],
    "section": ["SECTION", "SEC", "CLASS GROUP", "GROUP"],
    "classroom": ["CLASSROOM / LAB", "CLASSROOM/LAB", "CLASSROOM", "ROOM NO", "ROOM_NO", "ROOM", "LAB", "VENUE", "LOCATION"],
    "academic_year": ["ACADEMIC YEAR", "ACADEMIC_YEAR", "AY", "YEAR"],
    "break_schedule": ["BREAK SCHEDULE", "BREAK_SCHEDULE", "BREAK TIME", "BREAK"],
    "assignment_status": ["ASSIGNMENT STATUS", "STATUS"],
}


def map_headers(header_row):
    """
    Maps column indices to known timetable fields using a two-pass alias resolver.
    Pass 1 matches exact names to prevent substring collisions (e.g. COURSE CODE vs COURSE NAME).
    Pass 2 matches substrings for unmapped columns.
    """
    col_map = {}
    cleaned_headers = [
        re.sub(r"[\s_]+", " ", str(h).strip()).upper() if h is not None else ""
        for h in header_row
    ]

    # Pass 1: Exact alias matches
    for idx, h_clean in enumerate(cleaned_headers):
        if not h_clean:
            continue
        for field, aliases in HEADER_ALIASES.items():
            if field in col_map:
                continue
            if any(h_clean == alias for alias in aliases):
                col_map[field] = idx
                break

    # Pass 2: Substring matches for remaining fields
    for idx, h_clean in enumerate(cleaned_headers):
        if not h_clean:
            continue
        for field, aliases in HEADER_ALIASES.items():
            if field in col_map:
                continue
            if any(alias in h_clean for alias in aliases if len(alias) > 3):
                col_map[field] = idx
                break

    return col_map


def string_to_time(val):
    if isinstance(val, time):
        return val
    parts = str(val).split(":")
    return time(int(parts[0]), int(parts[1]))


def time_ranges_overlap(start1, end1, start2, end2):
    s1, e1 = string_to_time(start1), string_to_time(end1)
    s2, e2 = string_to_time(start2), string_to_time(end2)
    return max(s1, s2) < min(e1, e2)


def get_workbook_sheet(workbook, requested_sheet=None):
    if requested_sheet and requested_sheet in workbook.sheetnames:
        return workbook[requested_sheet], requested_sheet

    # Priority 1: Exact or case-insensitive "Master Timetable"
    for name in workbook.sheetnames:
        if name.strip().lower() == "master timetable":
            return workbook[name], name

    # Priority 2: Configured legacy SHEET_NAME
    if SHEET_NAME in workbook.sheetnames:
        return workbook[SHEET_NAME], SHEET_NAME

    # Priority 3: Look for any sheet containing 'timetable' or 'time table'
    for name in workbook.sheetnames:
        if "timetable" in name.lower() or "time table" in name.lower():
            return workbook[name], name

    # Fallback to the first sheet
    if workbook.sheetnames:
        return workbook[workbook.sheetnames[0]], workbook.sheetnames[0]

    return None, None


def find_timetable_header_row(all_rows, max_search_rows=15):
    """
    Inspects sheet rows to determine the header row index, column mapping,
    and whether the sheet is a row-based table or a grid/matrix table.
    """
    for r_idx, row in enumerate(all_rows[:max_search_rows]):
        if not any(row):
            continue
        col_map = map_headers(row)

        has_course = "course_code" in col_map or "course_name" in col_map
        has_faculty = "faculty_name" in col_map or "faculty_id" in col_map
        has_time = "time" in col_map or ("start_time" in col_map and "end_time" in col_map)
        has_day = "day" in col_map
        has_period = "period" in col_map

        # Row-based table detection: has explicit course/faculty columns and day/period/time
        if (has_course or has_faculty) and (has_time or has_day or has_period):
            return r_idx, col_map, True

        # Grid-based table detection: starts with DAY and has period/timings columns
        row_vals = [
            clean(val).upper()
            for val in row[:10]
            if val is not None
        ]
        if row_vals and row_vals[0] == "DAY":
            has_p = any(p in row_vals for p in ["P.NO.", "P.NO", "PERIOD", "PERIOD NO", "P. NO."])
            has_t = any("TIMING" in v or "TIME" in v for v in row_vals)
            if has_p or has_t:
                return r_idx, col_map, False

    # Fallback default: row index 0, not row-based
    return 0, {}, False


def extract_cell_components(raw_cell, courses, faculty_members):
    """
    Extracts course, faculty, and room from raw timetable cell text.
    Uses database-backed entity dictionaries with longest-match priority,
    falling back to regex heuristics.
    """
    text = clean(raw_cell)
    if not text or text.upper() in {"LUNCH BREAK", "BREAK", "RECESS", "FREE", "LIBRARY", "SPORTS"}:
        return None

    extracted_room = None
    extracted_course = None
    extracted_faculty = None
    matched_course_candidates = []
    matched_faculty_candidates = []

    # 1. Extract Room
    room_match = ROOM_PATTERN.search(text)
    if room_match:
        extracted_room = room_match.group(0).strip(" ,")

    # 2. Match Course
    # Sort courses by code length descending to ensure BCSE-513L matches before BCSE-513
    courses_by_code_len = sorted(courses, key=lambda c: len(c.course_code), reverse=True)
    for c in courses_by_code_len:
        # Check boundary-aware or delimiter-aware match for code
        code_pattern = re.compile(
            r"(?<![A-Za-z0-9])" + re.escape(c.course_code) + r"(?![A-Za-z0-9])",
            re.IGNORECASE,
        )
        if code_pattern.search(text):
            matched_course_candidates.append(c)

    if not matched_course_candidates:
        # Match by normalized code without dash/space
        text_normalized = re.sub(r"[\s\-_]", "", text).lower()
        for c in courses_by_code_len:
            c_norm = re.sub(r"[\s\-_]", "", c.course_code).lower()
            if c_norm in text_normalized:
                matched_course_candidates.append(c)

    if not matched_course_candidates:
        # Match by course name
        courses_by_name_len = sorted(courses, key=lambda c: len(c.course_name), reverse=True)
        for c in courses_by_name_len:
            if len(c.course_name) >= 4 and c.course_name.lower() in text.lower():
                matched_course_candidates.append(c)

    # If code still not found, check regex heuristic
    if not matched_course_candidates:
        code_match = COURSE_CODE_PATTERN.search(text)
        if code_match and code_match.group(0).upper() not in {"ROOM", "TIME"}:
            raw_code_candidate = code_match.group(0).strip()
            # check if any course matches this candidate
            for c in courses:
                if c.course_code.upper() == raw_code_candidate.upper():
                    matched_course_candidates.append(c)

    if len(matched_course_candidates) == 1:
        extracted_course = matched_course_candidates[0]
    elif len(matched_course_candidates) > 1:
        # Check if one is an exact match for course_code
        exact = [c for c in matched_course_candidates if c.course_code.lower() == text.strip().lower()]
        if len(exact) == 1:
            extracted_course = exact[0]
            matched_course_candidates = [exact[0]]

    # 3. Match Faculty
    # Match by employee_id or user.name
    faculty_by_len = sorted(faculty_members, key=lambda f: len(f.user.name), reverse=True)
    for f in faculty_by_len:
        if f.employee_id.lower() in text.lower():
            matched_faculty_candidates.append(f)
            continue
        # Check name
        f_name = f.user.name.strip()
        f_name_clean = re.sub(r"^(?:Dr\.|Mr\.|Ms\.|Mrs\.|Prof\.)\s*", "", f_name, flags=re.IGNORECASE).strip()
        if f_name.lower() in text.lower() or (len(f_name_clean) >= 4 and f_name_clean.lower() in text.lower()):
            matched_faculty_candidates.append(f)

    if len(matched_faculty_candidates) == 1:
        extracted_faculty = matched_faculty_candidates[0]
    elif len(matched_faculty_candidates) > 1:
        # Check if one candidate is an exact full name match (e.g. Dr. Arpneek Kaur vs Dr. Arpneek)
        exact_full = [
            f for f in matched_faculty_candidates
            if f.user.name.strip().lower() in text.lower()
        ]
        if len(exact_full) == 1:
            matched_faculty_candidates = exact_full
            extracted_faculty = exact_full[0]

    return {
        "raw_cell": text,
        "course": extracted_course,
        "course_candidates": matched_course_candidates,
        "faculty": extracted_faculty,
        "faculty_candidates": matched_faculty_candidates,
        "room": extracted_room,
    }


def parse_row_based_sheet(all_rows, col_map, sheet_name, header_row_idx):
    """
    Parses a row-based timetable sheet where each row specifies Day, Period, Time,
    Course, Faculty, Semester, Section, Classroom, and Academic Year.
    """
    entries = []
    errors = []
    current_day = ""
    period_rows = 0

    for row_idx, row in enumerate(all_rows[header_row_idx + 1:], start=header_row_idx + 2):
        if not any(row):
            continue

        day_raw = clean(row[col_map["day"]]) if "day" in col_map and col_map["day"] < len(row) else ""
        if day_raw:
            norm_day = normalize_day(day_raw)
            if norm_day:
                current_day = norm_day

        period_val = clean(row[col_map["period"]]) if "period" in col_map and col_map["period"] < len(row) else ""
        if period_val.lower() in {"break", "lunch", "recess", "free", "library", "sports"}:
            continue

        # Extract Time
        start_time = None
        end_time = None
        if "start_time" in col_map and "end_time" in col_map:
            st_raw = row[col_map["start_time"]] if col_map["start_time"] < len(row) else None
            et_raw = row[col_map["end_time"]] if col_map["end_time"] < len(row) else None
            start_time = normalize_time_str(st_raw)
            end_time = normalize_time_str(et_raw)

        if (not start_time or not end_time) and "time" in col_map:
            time_raw = row[col_map["time"]] if col_map["time"] < len(row) else None
            start_time, end_time = parse_time_range(time_raw)

        if not current_day:
            errors.append({
                "row": row_idx,
                "message": "No day could be determined for this period.",
            })
            continue

        if not start_time or not end_time:
            errors.append({
                "row": row_idx,
                "message": "Invalid or unsupported time format.",
                "value": f"{row[col_map.get('time', 0)] if 'time' in col_map else ''}",
            })
            continue

        if start_time >= end_time:
            errors.append({
                "row": row_idx,
                "message": "Period start time must precede end time.",
                "value": f"{start_time} - {end_time}",
            })
            continue

        course_code = clean(row[col_map["course_code"]]) if "course_code" in col_map and col_map["course_code"] < len(row) else ""
        course_name = clean(row[col_map["course_name"]]) if "course_name" in col_map and col_map["course_name"] < len(row) else ""
        faculty_id = row[col_map["faculty_id"]] if "faculty_id" in col_map and col_map["faculty_id"] < len(row) else None
        faculty_name = clean(row[col_map["faculty_name"]]) if "faculty_name" in col_map and col_map["faculty_name"] < len(row) else ""
        semester_raw = row[col_map["semester"]] if "semester" in col_map and col_map["semester"] < len(row) else None
        section_raw = clean(row[col_map["section"]]) if "section" in col_map and col_map["section"] < len(row) else "A"
        room = clean(row[col_map["classroom"]]) if "classroom" in col_map and col_map["classroom"] < len(row) else ""
        ay = clean(row[col_map["academic_year"]]) if "academic_year" in col_map and col_map["academic_year"] < len(row) else ""

        # Normalize semester
        semester = None
        if semester_raw is not None:
            m = re.search(r"\d+", str(semester_raw))
            if m:
                semester = int(m.group(0))

        # Derive class group
        if semester and section_raw:
            class_group = f"Sem {semester}-{section_raw}"
        else:
            class_group = section_raw or "General"

        period_rows += 1
        raw_cell_summary = f"{course_code} {course_name} {faculty_name} {room}".strip()

        entries.append({
            "source_row": row_idx,
            "day_of_week": current_day,
            "period": period_val or f"P{period_rows}",
            "start_time": start_time,
            "end_time": end_time,
            "class_group": class_group,
            "semester": semester,
            "section": section_raw,
            "course_code": course_code,
            "course_name": course_name,
            "faculty_id": faculty_id,
            "faculty_name": faculty_name,
            "room": room,
            "academic_year": ay,
            "raw_cell": raw_cell_summary,
            "source_sheet": sheet_name,
            "is_row_based": True,
        })

    return entries, period_rows, errors


def parse_grid_based_sheet(all_rows, col_map, sheet_name, header_row_idx):
    """
    Parses a grid/matrix timetable sheet where columns specify sections or class groups
    and each cell contains combined freeform text.
    """
    if header_row_idx >= len(all_rows):
        return None, 0, ["Header row index out of bounds."]

    headers = [clean(v) for v in all_rows[header_row_idx]]
    if not headers or headers[0].upper() != "DAY" or len(headers) < 4:
        return None, 0, ["The worksheet headers do not match the expected timetable format."]

    period_col = col_map.get("period", 1)
    timings_col = col_map.get("time", 2)
    group_start_col = max(period_col, timings_col) + 1

    groups = [
        {"column": index, "group": header}
        for index, header in enumerate(headers)
        if index >= group_start_col and header and "LUNCH" not in header.upper()
    ]

    entries = []
    errors = []
    current_day = ""
    period_rows = 0

    for row_number, row in enumerate(all_rows[header_row_idx + 1:], start=header_row_idx + 2):
        if not any(row):
            continue

        day_raw = clean(row[0]) if len(row) > 0 else ""
        period_val = clean(row[period_col]) if len(row) > period_col else ""
        time_val = clean(row[timings_col]) if len(row) > timings_col else ""

        if day_raw:
            norm = normalize_day(day_raw)
            if norm:
                current_day = norm

        if not period_val and not time_val:
            continue

        period_rows += 1
        start_time, end_time = parse_time_range(time_val)

        if not current_day:
            errors.append({
                "row": row_number,
                "message": "No day could be determined for this period.",
            })
            continue

        if not start_time or not end_time:
            errors.append({
                "row": row_number,
                "message": "Invalid or unsupported time range format.",
                "value": time_val,
            })
            continue

        if start_time >= end_time:
            errors.append({
                "row": row_number,
                "message": "The period end time must be after its start time.",
                "value": time_val,
            })
            continue

        for group_info in groups:
            c_idx = group_info["column"]
            cell_val = clean(row[c_idx]) if c_idx < len(row) else ""
            if not cell_val or cell_val.upper() in {"LUNCH BREAK", "BREAK", "RECESS", "FREE", "LIBRARY", "SPORTS"}:
                continue

            entries.append({
                "source_row": row_number,
                "day_of_week": current_day,
                "period": period_val or f"P{period_rows}",
                "start_time": start_time,
                "end_time": end_time,
                "class_group": group_info["group"],
                "raw_cell": cell_val,
                "source_sheet": sheet_name,
                "is_row_based": False,
            })

    return entries, period_rows, errors


def parse_workbook_sheet(sheet, sheet_name, header_row=None):
    """
    Universal workbook sheet parser supporting both:
    1. Row-based tables (Master Timetable layout with columns for course, faculty, etc.)
    2. Grid/matrix tables (columns for groups with multi-line cell content).
    """
    all_rows = list(sheet.iter_rows(values_only=True))
    if not all_rows:
        return [], 0, ["Worksheet is empty."]

    header_idx, col_map, is_row_based = find_timetable_header_row(all_rows)

    if is_row_based:
        return parse_row_based_sheet(all_rows, col_map, sheet_name, header_idx)
    else:
        if header_row is not None and header_row > 0:
            header_idx = header_row - 1
            col_map = map_headers(all_rows[header_idx]) if header_idx < len(all_rows) else {}
        return parse_grid_based_sheet(all_rows, col_map, sheet_name, header_idx)


@timetable_import_bp.get("/academic-years")
@admin_required
def get_available_academic_years():
    """
    Returns available academic years from course_offerings, system setting, and institutional calendar.
    Normalizes formatting and avoids cohort spans (e.g. 2026-2030).
    """
    all_years = get_available_academic_sessions()
    default_year = get_current_academic_session()

    return jsonify({
        "success": True,
        "academic_years": all_years,
        "default": default_year,
    }), 200


@timetable_import_bp.post("/sheets")
@admin_required
def get_workbook_sheets():
    """
    Returns the sheet names of an uploaded Excel file to allow admin sheet selection.
    """
    uploaded = request.files.get("file")
    if not uploaded or not uploaded.filename:
        return jsonify({"success": False, "message": "No file uploaded."}), 400

    if not uploaded.filename.lower().endswith(".xlsx"):
        return jsonify({"success": False, "message": "Only .xlsx files are supported."}), 400

    file_bytes = uploaded.read(MAX_FILE_SIZE + 1)
    if len(file_bytes) > MAX_FILE_SIZE:
        return jsonify({"success": False, "message": "The workbook must be 10MB or smaller."}), 413

    try:
        workbook = load_workbook(BytesIO(file_bytes), read_only=True, data_only=True)
        sheets = workbook.sheetnames
        _, recommended = get_workbook_sheet(workbook)
        workbook.close()
        return jsonify({
            "success": True,
            "sheets": sheets,
            "recommended": recommended,
        }), 200
    except Exception as exc:
        return jsonify({
            "success": False,
            "message": "Could not read sheets from this workbook.",
            "error": str(exc),
        }), 400


@timetable_import_bp.post("/preview")
@admin_required
def preview_timetable_import():
    """
    Backward-compatible preview endpoint that returns extracted raw timetable rows.
    """
    uploaded = request.files.get("file")
    if not uploaded or not uploaded.filename:
        return jsonify({
            "success": False,
            "message": "Upload an Excel workbook using the 'file' field",
        }), 400
    if not uploaded.filename.lower().endswith(".xlsx"):
        return jsonify({
            "success": False,
            "message": "Only .xlsx files are supported.",
        }), 400
    file_bytes = uploaded.read(MAX_FILE_SIZE + 1)
    if len(file_bytes) > MAX_FILE_SIZE:
        return jsonify({
            "success": False,
            "message": "The workbook must be 10MB or smaller.",
        }), 413
    try:
        workbook = load_workbook(BytesIO(file_bytes), data_only=True)
    except Exception as exc:
        return jsonify({
            "success": False,
            "message": "The uploaded file is not a readable Excel workbook.",
            "error_type": type(exc).__name__,
        }), 400

    try:
        requested_sheet = request.form.get("sheet_name")
        sheet, sheet_name = get_workbook_sheet(workbook, requested_sheet)

        if not sheet:
            return jsonify({
                "success": False,
                "message": f"Required worksheet not found: {SHEET_NAME}",
                "available_sheets": workbook.sheetnames,
            }), 422

        entries, period_rows, errors = parse_workbook_sheet(sheet, sheet_name)

        if entries is None:
            return jsonify({
                "success": False,
                "message": "The worksheet headers do not match the expected timetable format.",
                "available_sheets": workbook.sheetnames,
            }), 422

        return jsonify({
            "success": True,
            "message": "Preview generated. No timetable records were saved.",
            "source_sheet": sheet_name,
            "available_sheets": workbook.sheetnames,
            "period_rows_examined": period_rows,
            "entry_count": len(entries),
            "error_count": len(errors),
            "entries": entries,
            "errors": errors,
            "warnings": [
                "Course, faculty and room details remain in raw_cell until their parsing and database matching rules are verified.",
                "Merged-class assignments must be reviewed before confirming an import.",
            ],
        }), 200
    finally:
        workbook.close()


@timetable_import_bp.post("/analyze")
@admin_required
def analyze_timetable_import():
    """
    Performs complete parsing, entity matching against MySQL database,
    and conflict & duplicate detection.
    """
    uploaded = request.files.get("file")
    if not uploaded or not uploaded.filename:
        return jsonify({"success": False, "message": "Upload a timetable workbook using the 'file' field."}), 400

    filename_lower = uploaded.filename.lower()
    if not filename_lower.endswith(".xlsx"):
        if filename_lower.endswith(".xls"):
            return jsonify({
                "success": False,
                "message": "Older Excel (.xls) format detected. Please save your file as modern Excel (.xlsx) workbook before importing.",
            }), 400
        elif filename_lower.endswith(".pdf"):
            return jsonify({
                "success": False,
                "message": "Direct PDF extraction requires structured tabular text. Please export or convert your timetable PDF into Excel (.xlsx) format for accurate period and entity mapping.",
            }), 400
        return jsonify({"success": False, "message": "Unsupported file format. Please upload an Excel (.xlsx) workbook."}), 400

    academic_year = clean(request.form.get("academic_year"))
    if not academic_year:
        return jsonify({"success": False, "message": "Academic year is required."}), 400

    requested_sheet = clean(request.form.get("sheet_name"))

    file_bytes = uploaded.read(MAX_FILE_SIZE + 1)
    if len(file_bytes) == 0:
        return jsonify({"success": False, "message": "The uploaded file is empty. Please select a valid timetable file."}), 400
    if len(file_bytes) > MAX_FILE_SIZE:
        return jsonify({"success": False, "message": "The workbook must be 10MB or smaller."}), 413

    try:
        workbook = load_workbook(BytesIO(file_bytes), data_only=True)
    except Exception as exc:
        return jsonify({
            "success": False,
            "message": "The uploaded file is not a valid or readable Excel workbook. It may be corrupt or encrypted.",
            "error_type": type(exc).__name__,
        }), 400

    try:
        sheet, sheet_name = get_workbook_sheet(workbook, requested_sheet)
        if not sheet:
            return jsonify({
                "success": False,
                "message": "No valid timetable worksheet found in workbook.",
                "available_sheets": workbook.sheetnames,
            }), 422

        raw_entries, _period_rows, parse_errors = parse_workbook_sheet(sheet, sheet_name)
        if raw_entries is None:
            return jsonify({
                "success": False,
                "message": "The worksheet headers do not match the expected timetable format.",
                "available_sheets": workbook.sheetnames,
            }), 422
        if len(raw_entries) == 0:
            diag_message = f"No valid timetable entries could be extracted from sheet '{sheet_name}'."
            if parse_errors:
                diag_message += f" ({'; '.join(str(e.get('message', e)) for e in parse_errors[:2])})"
            return jsonify({
                "success": False,
                "message": diag_message,
                "source_sheet": sheet_name,
                "available_sheets": workbook.sheetnames,
                "parse_errors": parse_errors,
            }), 422
    finally:
        workbook.close()

    # Pre-fetch existing database entities for high-performance matching
    courses = Course.query.all()
    courses_by_code = {c.course_code.upper(): c for c in courses}
    courses_by_name = {c.course_name.lower(): c for c in courses}

    faculty_members = Faculty.query.join(User).all()
    faculty_by_id = {f.faculty_id: f for f in faculty_members}
    faculty_by_emp = {f.employee_id.upper(): f for f in faculty_members}
    faculty_by_full_name = {f.user.name.strip().lower(): f for f in faculty_members}
    faculty_by_clean_name = {
        re.sub(r"^(?:Dr\.|Mr\.|Ms\.|Mrs\.|Prof\.)\s*", "", f.user.name, flags=re.I).strip().lower(): f
        for f in faculty_members
    }

    canonical_selected_ay = canonical_academic_year(academic_year)
    all_offerings = CourseOffering.query.all()
    offering_map = {
        (o.course_id, o.semester, o.section, canonical_academic_year(o.academic_year)): o
        for o in all_offerings
    }

    all_db_entries = TimetableEntry.query.join(CourseOffering).all()
    db_entries_by_ay = {}
    for te in all_db_entries:
        ay_canon = canonical_academic_year(te.offering.academic_year)
        db_entries_by_ay.setdefault(ay_canon, []).append(te)

    analyzed_rows = []
    status_counts = {
        "valid": 0,
        "matched": 0,
        "warning": 0,
        "ambiguous": 0,
        "unmatched": 0,
        "conflict": 0,
        "duplicate": 0,
    }

    # Tracking intra-batch scheduling to detect overlaps within the uploaded workbook itself
    batch_faculty_schedule = []
    batch_room_schedule = []
    batch_section_schedule = []

    for idx, raw_item in enumerate(raw_entries):
        is_row_based = raw_item.get("is_row_based", False)

        if is_row_based:
            # Row-based resolution: values are extracted from distinct columns
            c_code = raw_item.get("course_code", "").upper()
            c_name = raw_item.get("course_name", "").lower()
            matched_course = courses_by_code.get(c_code) or courses_by_name.get(c_name)
            course_candidates = [matched_course] if matched_course else []

            f_id = raw_item.get("faculty_id")
            f_name = raw_item.get("faculty_name", "")
            matched_faculty = None
            if f_id is not None:
                try:
                    matched_faculty = faculty_by_id.get(int(f_id))
                except (ValueError, TypeError):
                    matched_faculty = faculty_by_emp.get(str(f_id).upper())
            if not matched_faculty and f_name:
                f_name_lower = f_name.strip().lower()
                f_clean = re.sub(r"^(?:Dr\.|Mr\.|Ms\.|Mrs\.|Prof\.)\s*", "", f_name, flags=re.I).strip().lower()
                matched_faculty = faculty_by_full_name.get(f_name_lower) or faculty_by_clean_name.get(f_clean)
            faculty_candidates = [matched_faculty] if matched_faculty else []

            detected_room = raw_item.get("room") or None
            class_group = raw_item.get("class_group") or "General"
            day_of_week = raw_item["day_of_week"]
            start_time = raw_item["start_time"]
            end_time = raw_item["end_time"]
            semester = raw_item.get("semester") or (matched_course.semester if matched_course else 1)
            section = raw_item.get("section") or "A"
            row_ay = raw_item.get("academic_year") or academic_year
        else:
            # Grid-based resolution: parse freeform cell text
            cell_components = extract_cell_components(
                raw_item["raw_cell"],
                courses,
                faculty_members,
            )
            matched_course = cell_components["course"] if cell_components else None
            course_candidates = cell_components["course_candidates"] if cell_components else []
            matched_faculty = cell_components["faculty"] if cell_components else None
            faculty_candidates = cell_components["faculty_candidates"] if cell_components else []
            detected_room = cell_components["room"] if cell_components else None

            class_group = raw_item["class_group"]
            day_of_week = raw_item["day_of_week"]
            start_time = raw_item["start_time"]
            end_time = raw_item["end_time"]
            semester = matched_course.semester if matched_course else None
            section = class_group
            row_ay = academic_year

        status = "matched"
        warnings = []
        conflicts = []
        offering_id = None
        offering_action = "reuse"

        # Academic Year check: report discrepancies between workbook row and selected academic year
        eff_ay_canon = canonical_academic_year(row_ay) if row_ay else canonical_selected_ay
        if row_ay and academic_year:
            canon_row_ay = canonical_academic_year(row_ay)
            canon_sel_ay = canonical_academic_year(academic_year)
            if canon_row_ay and canon_sel_ay and canon_row_ay != canon_sel_ay:
                warnings.append(
                    f"Workbook academic year ({row_ay}) differs from selected ({academic_year})."
                )

        # Check Course Resolution
        if not matched_course:
            if course_candidates:
                status = "ambiguous"
                warnings.append(f"Found {len(course_candidates)} potential course matches.")
            else:
                status = "unmatched"
                warnings.append("Could not identify course from cell text.")
        else:
            # Check Course Offering
            lookup_key = (matched_course.course_id, semester, section, eff_ay_canon)
            existing_off = offering_map.get(lookup_key)
            if not existing_off and eff_ay_canon != canonical_selected_ay:
                existing_off = offering_map.get((matched_course.course_id, semester, section, canonical_selected_ay))
            if existing_off:
                offering_id = existing_off.offering_id
                offering_action = "reuse"
                if not matched_faculty and existing_off.faculty:
                    matched_faculty = existing_off.faculty
            else:
                offering_action = "create"
                warnings.append(f"Will create a new course offering for this section ({row_ay or academic_year}).")

        # Check Faculty Resolution
        if not matched_faculty and faculty_candidates:
            if status != "unmatched":
                status = "ambiguous"
            warnings.append(f"Multiple faculty candidates matched: {', '.join(f.user.name for f in faculty_candidates)}.")
        elif not matched_faculty:
            warnings.append("No faculty member identified.")

        if not detected_room:
            warnings.append("No classroom or laboratory specified.")

        # Determine target existing entries for this academic year
        target_existing_entries = db_entries_by_ay.get(eff_ay_canon, [])
        if not target_existing_entries and eff_ay_canon != canonical_selected_ay:
            target_existing_entries = db_entries_by_ay.get(canonical_selected_ay, [])

        # Duplicate Check: Check against DB entries
        is_duplicate = False
        if offering_id:
            for te in target_existing_entries:
                if (
                    te.offering_id == offering_id
                    and te.day_of_week.lower() == day_of_week.lower()
                    and te.start_time.strftime("%H:%M") == start_time
                    and te.end_time.strftime("%H:%M") == end_time
                ):
                    is_duplicate = True
                    status = "duplicate"
                    warnings.append("Identical timetable entry already exists in the database.")
                    adj = FacultyAdjustment.query.filter_by(
                        timetable_entry_id=te.timetable_entry_id,
                        status="APPROVED",
                    ).first()
                    if adj:
                        warnings.append(
                            f"Entry has an active approved faculty adjustment to {adj.substitute_faculty.user.name}. It will be preserved."
                        )
                    break

        # Conflict Check 1: Faculty overlap against DB and intra-batch
        fac_id = matched_faculty.faculty_id if matched_faculty else None
        if fac_id and not is_duplicate:
            # DB check
            for te in target_existing_entries:
                if (
                    te.offering.faculty_id == fac_id
                    and te.day_of_week.lower() == day_of_week.lower()
                    and time_ranges_overlap(start_time, end_time, te.start_time.strftime("%H:%M"), te.end_time.strftime("%H:%M"))
                ):
                    status = "conflict"
                    conflicts.append(
                        f"Faculty {matched_faculty.user.name} already has {te.offering.course.course_code} on {day_of_week} ({te.start_time.strftime('%H:%M')}–{te.end_time.strftime('%H:%M')})."
                    )

            # Intra-batch check
            for item in batch_faculty_schedule:
                if (
                    item["faculty_id"] == fac_id
                    and item["day_of_week"].lower() == day_of_week.lower()
                    and time_ranges_overlap(start_time, end_time, item["start_time"], item["end_time"])
                ):
                    status = "conflict"
                    conflicts.append(
                        f"Faculty {matched_faculty.user.name} is scheduled for multiple classes at the same time in this workbook."
                    )

        # Conflict Check 2: Room overlap against DB and intra-batch
        if detected_room and not is_duplicate:
            for te in target_existing_entries:
                te_room = te.room or te.offering.room
                if (
                    te_room
                    and te_room.lower() == detected_room.lower()
                    and te.day_of_week.lower() == day_of_week.lower()
                    and time_ranges_overlap(start_time, end_time, te.start_time.strftime("%H:%M"), te.end_time.strftime("%H:%M"))
                ):
                    status = "conflict"
                    conflicts.append(
                        f"Room {detected_room} is already booked on {day_of_week} ({te.start_time.strftime('%H:%M')}–{te.end_time.strftime('%H:%M')})."
                    )

            for item in batch_room_schedule:
                if (
                    item["room"].lower() == detected_room.lower()
                    and item["day_of_week"].lower() == day_of_week.lower()
                    and time_ranges_overlap(start_time, end_time, item["start_time"], item["end_time"])
                ):
                    status = "conflict"
                    conflicts.append(
                        f"Room {detected_room} is assigned to multiple classes at the same time in this workbook."
                    )

        # Conflict Check 3: Section/Group overlap
        if not is_duplicate:
            for item in batch_section_schedule:
                if (
                    item["class_group"].lower() == class_group.lower()
                    and item["day_of_week"].lower() == day_of_week.lower()
                    and time_ranges_overlap(start_time, end_time, item["start_time"], item["end_time"])
                ):
                    status = "conflict"
                    conflicts.append(
                        f"Class group {class_group} has multiple classes scheduled at the same time in this workbook."
                    )

        # Register in batch schedule
        if fac_id:
            batch_faculty_schedule.append({
                "faculty_id": fac_id,
                "day_of_week": day_of_week,
                "start_time": start_time,
                "end_time": end_time,
            })
        if detected_room:
            batch_room_schedule.append({
                "room": detected_room,
                "day_of_week": day_of_week,
                "start_time": start_time,
                "end_time": end_time,
            })
        batch_section_schedule.append({
            "class_group": class_group,
            "section": section,
            "semester": semester,
            "day_of_week": day_of_week,
            "start_time": start_time,
            "end_time": end_time,
        })

        if status == "matched" and warnings:
            status = "warning"

        if status in {"matched", "warning"}:
            status_counts["valid"] += 1
        status_counts[status] += 1

        analyzed_rows.append({
            "index": idx,
            "source_row": raw_item["source_row"],
            "day_of_week": day_of_week,
            "period": raw_item["period"],
            "start_time": start_time,
            "end_time": end_time,
            "class_group": class_group,
            "raw_cell": raw_item["raw_cell"],
            "course_id": matched_course.course_id if matched_course else None,
            "course_code": matched_course.course_code if matched_course else "",
            "course_name": matched_course.course_name if matched_course else "",
            "semester": semester,
            "section": section,
            "academic_year": row_ay or academic_year,
            "faculty_id": matched_faculty.faculty_id if matched_faculty else None,
            "faculty_name": matched_faculty.user.name if matched_faculty else "",
            "room": detected_room or "",
            "status": status,
            "offering_id": offering_id,
            "offering_action": offering_action,
            "warnings": warnings,
            "conflicts": conflicts,
            "course_candidates": [
                {
                    "course_id": c.course_id,
                    "course_code": c.course_code,
                    "course_name": c.course_name,
                    "semester": c.semester,
                }
                for c in course_candidates
            ],
            "faculty_candidates": [
                {
                    "faculty_id": f.faculty_id,
                    "name": f.user.name,
                    "employee_id": f.employee_id,
                }
                for f in faculty_candidates
            ],
        })

    return jsonify({
        "success": True,
        "academic_year": academic_year,
        "source_sheet": sheet_name,
        "available_sheets": [sheet_name],
        "total_rows": len(analyzed_rows),
        "counts": status_counts,
        "entries": analyzed_rows,
        "parse_errors": parse_errors,
        "available_courses": [
            {
                "course_id": c.course_id,
                "course_code": c.course_code,
                "course_name": c.course_name,
                "semester": c.semester,
            }
            for c in courses
        ],
        "available_faculty": [
            {
                "faculty_id": f.faculty_id,
                "name": f.user.name,
                "employee_id": f.employee_id,
            }
            for f in faculty_members
        ],
    }), 200


@timetable_import_bp.post("/commit")
@admin_required
def commit_timetable_import():
    """
    Persists valid and admin-resolved timetable entries and course offerings
    within an atomic SQLAlchemy transaction.
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"success": False, "message": "JSON payload required."}), 400

    academic_year = clean(data.get("academic_year"))
    if not academic_year:
        return jsonify({"success": False, "message": "Academic year is required."}), 400

    import_mode = clean(data.get("import_mode")) or "add_missing"
    entries_to_import = data.get("entries") or []

    if not isinstance(entries_to_import, list) or not entries_to_import:
        return jsonify({"success": False, "message": "No entries provided to import."}), 400

    admin_user_id = int(get_jwt_identity())
    admin_user = db.session.get(User, admin_user_id)
    admin_name = admin_user.name if admin_user else f"User {admin_user_id}"

    created_offerings_count = 0
    created_entries_count = 0
    updated_entries_count = 0
    skipped_entries_count = 0
    errors = []

    # Cache courses and faculty
    courses_cache = {c.course_id: c for c in Course.query.all()}
    faculty_cache = {f.faculty_id: f for f in Faculty.query.all()}

    # Begin atomic transaction
    try:
        # Step 1: Pre-load offerings
        canonical_target_ay = canonical_academic_year(academic_year)
        existing_offerings = CourseOffering.query.all()
        offering_lookup = {
            (o.course_id, o.semester, o.section, canonical_academic_year(o.academic_year)): o
            for o in existing_offerings
        }

        # Step 2: In replace_scope mode, remove existing timetable entries for the affected offerings
        if import_mode == "replace_scope":
            target_course_ids = {
                e.get("course_id") for e in entries_to_import if e.get("course_id")
            }
            scoped_offerings = [
                o for o in existing_offerings
                if o.course_id in target_course_ids
                and canonical_academic_year(o.academic_year) == canonical_target_ay
            ]
            for off in scoped_offerings:
                for te_item in off.timetable_entries:
                    has_adj = FacultyAdjustment.query.filter_by(
                        timetable_entry_id=te_item.timetable_entry_id,
                        status="APPROVED",
                    ).first()
                    if not has_adj:
                        db.session.delete(te_item)

        # Step 3: Process entries
        for row_idx, item in enumerate(entries_to_import):
            course_id = item.get("course_id")
            if not course_id or course_id not in courses_cache:
                errors.append(f"Row {row_idx + 1}: Valid course is required.")
                continue

            course = courses_cache[course_id]
            faculty_id = item.get("faculty_id") or None
            if faculty_id and faculty_id not in faculty_cache:
                faculty_id = None

            semester = item.get("semester") or course.semester or 1
            section = clean(item.get("section") or item.get("class_group") or "A")
            room = clean(item.get("room")) or None
            day_of_week = normalize_day(item.get("day_of_week"))
            start_time_str = clean(item.get("start_time"))
            end_time_str = clean(item.get("end_time"))

            if not day_of_week or not start_time_str or not end_time_str:
                errors.append(f"Row {row_idx + 1}: Day of week, start time, and end time are required.")
                continue

            start_t = string_to_time(start_time_str)
            end_t = string_to_time(end_time_str)

            if start_t >= end_t:
                errors.append(f"Row {row_idx + 1}: Start time must precede end time.")
                continue

            row_ay = clean(item.get("academic_year"))
            raw_ay = row_ay or academic_year
            canon_entry_ay = canonical_academic_year(raw_ay)

            # Resolve or create CourseOffering
            offering_key = (course_id, semester, section, canon_entry_ay)
            offering = offering_lookup.get(offering_key)
            if not offering and canon_entry_ay != canonical_target_ay:
                offering = offering_lookup.get((course_id, semester, section, canonical_target_ay))

            if not offering:
                offering = CourseOffering(
                    course_id=course_id,
                    faculty_id=faculty_id,
                    academic_year=raw_ay,
                    semester=semester,
                    section=section,
                    room=room,
                )
                db.session.add(offering)
                db.session.flush()  # assign offering_id
                offering_lookup[offering_key] = offering
                created_offerings_count += 1
            else:
                # Update faculty or room on offering when provided
                if faculty_id:
                    offering.faculty_id = faculty_id
                if room:
                    offering.room = room

            # Resolve or create TimetableEntry
            existing_entry = TimetableEntry.query.filter_by(
                offering_id=offering.offering_id,
                day_of_week=day_of_week,
                start_time=start_t,
                end_time=end_t,
            ).first()

            if existing_entry:
                if import_mode == "update_matched":
                    if room:
                        existing_entry.room = room
                    updated_entries_count += 1
                else:
                    skipped_entries_count += 1
                continue

            # Create new entry
            new_entry = TimetableEntry(
                offering_id=offering.offering_id,
                day_of_week=day_of_week,
                start_time=start_t,
                end_time=end_t,
                room=room or offering.room,
            )
            db.session.add(new_entry)
            created_entries_count += 1

        db.session.commit()

        record_activity(
            action_type="TIMETABLE_IMPORTED",
            description=f"Imported timetable for {academic_year} ({created_entries_count} created, {updated_entries_count} updated)",
            actor_id=admin_user_id,
            actor_name=admin_name,
            entity_type="Timetable",
            details={
                "academic_year": academic_year,
                "created_entries": created_entries_count,
                "updated_entries": updated_entries_count,
            },
        )

        current_app.logger.info(
            f"Timetable import completed by {admin_name} (ID: {admin_user_id}) for {academic_year}: "
            f"{created_entries_count} created, {updated_entries_count} updated, "
            f"{skipped_entries_count} skipped, {created_offerings_count} offerings created."
        )

        return jsonify({
            "success": True,
            "message": (
                f"Timetable imported successfully for {academic_year}. "
                f"{created_entries_count} entries created, {updated_entries_count} updated, "
                f"{skipped_entries_count} skipped."
            ),
            "data": {
                "academic_year": academic_year,
                "import_mode": import_mode,
                "created_entries": created_entries_count,
                "updated_entries": updated_entries_count,
                "skipped_entries": skipped_entries_count,
                "created_offerings": created_offerings_count,
                "errors": errors,
            },
        }), 200

    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception(f"Timetable import failed for {academic_year}: {exc}")
        return jsonify({
            "success": False,
            "message": "The timetable import could not be completed. All changes have been rolled back.",
            "error": str(exc),
        }), 500
