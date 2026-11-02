import base64
import os
import re
import time
from datetime import date, datetime, timedelta

from flask import Blueprint, jsonify, request, send_from_directory
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required
from sqlalchemy import func
from sqlalchemy.orm import joinedload
from werkzeug.utils import secure_filename

from app.extensions import bcrypt, db
from app.models import (
    AttendanceRecord,
    AttendanceSession,
    Course,
    CourseOffering,
    Department,
    Enrollment,
    Faculty,
    Student,
    TimetableEntry,
)
from app.utils.academic_year import resolve_student_academic_info
from app.utils.auth import student_or_admin_required

student_bp = Blueprint(
    "student",
    __name__,
    url_prefix="/api/student",
)

# Upload directory configuration
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads", "students")
PHOTOS_DIR = os.path.join(UPLOAD_DIR, "photos")
SIGNATURES_DIR = os.path.join(UPLOAD_DIR, "signatures")

os.makedirs(PHOTOS_DIR, exist_ok=True)
os.makedirs(SIGNATURES_DIR, exist_ok=True)

MAX_IMAGE_SIZE_BYTES = 50 * 1024  # 50 KB
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}


def is_allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[-1].lower() in ALLOWED_EXTENSIONS


def get_current_student():
    identity = get_jwt_identity()
    if not identity:
        return None
    try:
        user_id = int(identity)
    except (ValueError, TypeError):
        return None

    return Student.query.filter_by(user_id=user_id).first()


def serialize_student_profile(student):
    records = AttendanceRecord.query.filter_by(student_id=student.student_id).all()
    total_records = len(records)
    present_records = sum(1 for r in records if r.status == "PRESENT")
    attendance_rate = (
        round((present_records / total_records * 100), 1)
        if total_records > 0
        else 0.0
    )

    enrollments_count = Enrollment.query.filter_by(
        student_id=student.student_id, status="ACTIVE"
    ).count()

    acad_info = resolve_student_academic_info(student)

    return {
        "student_id": student.student_id,
        "user_id": student.user_id,
        "name": student.user.name,
        "email": student.user.email,
        "phone": student.phone or getattr(student.user, "phone", "") or "",
        "enrollment_no": student.enrollment_no,
        "semester": acad_info["semester"],
        "section": acad_info["section"],
        "academic_year": acad_info["academic_year"],
        "batch_year": acad_info["batch_year"],
        "admission_year": acad_info["admission_year"],
        "photo_url": student.photo_url or "",
        "signature_url": student.signature_url or "",
        "father_name": student.father_name or "",
        "mother_name": student.mother_name or "",
        "guardian_phone": student.guardian_phone or "",
        "blood_group": student.blood_group or "",
        "gender": student.gender or "",
        "date_of_birth": student.date_of_birth or "",
        "address": student.address or "",
        "city": student.city or "",
        "state": student.state or "",
        "pin_code": student.pin_code or "",
        "country": student.country or "India",
        "emergency_contact_name": student.emergency_contact_name or "",
        "emergency_contact_phone": student.emergency_contact_phone or "",
        "admission_date": student.admission_date or "",
        "account_status": (
            "Active" if getattr(student.user, "is_active", True) else "Inactive"
        ),
        "department": {
            "department_id": (
                student.department.department_id if student.department else None
            ),
            "department_name": (
                student.department.department_name
                if student.department
                else "Department"
            ),
            "department_code": (
                student.department.department_code if student.department else "N/A"
            ),
        },
        "batch": {
            "batch_id": student.batch.batch_id if student.batch else None,
            "batch_name": acad_info["batch_year"] or (student.batch.batch_name if student.batch else ""),
        },
        "stats": {
            "total_enrolled_courses": enrollments_count,
            "total_attendance_records": total_records,
            "present_count": present_records,
            "attendance_percentage": attendance_rate,
        },
    }


# ============================================================
# STUDENT DASHBOARD
# ============================================================

@student_bp.get("/dashboard")
@student_or_admin_required
def student_dashboard():
    student = get_current_student()

    if not student:
        return jsonify({
            "success": False,
            "message": "Student profile not found",
        }), 404

    trend_weeks = request.args.get("weeks", default=4, type=int)
    if trend_weeks not in (4, 8, 12):
        trend_weeks = 4

    # 1. Student identity & academic info
    dept = student.department
    dept_name = dept.department_name if dept else None
    dept_code = dept.department_code if dept else None

    acad_info = resolve_student_academic_info(student)

    student_data = {
        "student_id": student.student_id,
        "user_id": student.user_id,
        "name": student.user.name if student.user else None,
        "email": student.user.email if student.user else None,
        "enrollment_no": student.enrollment_no,
        "semester": acad_info["semester"],
        "section": acad_info["section"],
        "academic_year": acad_info["academic_year"],
        "batch_year": acad_info["batch_year"],
        "admission_year": acad_info["admission_year"],
        "department_name": dept_name,
        "department_code": dept_code,
        "photo_url": student.photo_url or "",
    }

    # 2. Student enrollments & offerings
    enrollments = (
        Enrollment.query
        .options(
            joinedload(Enrollment.offering).joinedload(CourseOffering.course),
            joinedload(Enrollment.offering).joinedload(CourseOffering.faculty).joinedload(Faculty.user),
        )
        .filter_by(student_id=student.student_id, status="ACTIVE")
        .all()
    )
    offering_ids = [e.offering_id for e in enrollments]

    # Pre-fetch all closed sessions and present records in batch
    from collections import defaultdict
    offering_sessions_map = defaultdict(list)
    all_closed_session_ids = set()

    if offering_ids:
        all_sessions = (
            AttendanceSession.query
            .filter(
                AttendanceSession.offering_id.in_(offering_ids),
                AttendanceSession.status == "CLOSED",
            )
            .all()
        )
        for s in all_sessions:
            offering_sessions_map[s.offering_id].append(s.session_id)
            all_closed_session_ids.add(s.session_id)

    student_present_session_ids = set()
    if all_closed_session_ids:
        pres_rows = (
            db.session.query(AttendanceRecord.session_id)
            .filter(
                AttendanceRecord.student_id == student.student_id,
                AttendanceRecord.session_id.in_(all_closed_session_ids),
                AttendanceRecord.status == "PRESENT",
            )
            .all()
        )
        student_present_session_ids = {r[0] for r in pres_rows}

    # 3. Course-wise attendance & metrics
    courses_data = []
    total_classes = 0
    total_present = 0
    total_absent = 0

    for enrollment in enrollments:
        offering = enrollment.offering
        if not offering:
            continue
        course = offering.course
        if not course:
            continue

        session_ids = offering_sessions_map[offering.offering_id]
        course_total_sessions = len(session_ids)

        course_present = len(set(session_ids) & student_present_session_ids)
        course_absent = max(0, course_total_sessions - course_present)
        course_pct = (
            round((course_present / course_total_sessions) * 100, 1)
            if course_total_sessions > 0
            else 0.0
        )

        total_classes += course_total_sessions
        total_present += course_present
        total_absent += course_absent

        faculty_name = None
        if offering.faculty and offering.faculty.user:
            faculty_name = offering.faculty.user.name

        courses_data.append({
            "offering_id": offering.offering_id,
            "course_id": course.course_id,
            "course_code": course.course_code,
            "course_name": course.course_name,
            "credits": course.credits,
            "section": offering.section,
            "semester": offering.semester,
            "room": offering.room or None,
            "faculty_name": faculty_name,
            "total_sessions": course_total_sessions,
            "present_sessions": course_present,
            "absent_sessions": course_absent,
            "attendance_percentage": course_pct,
        })

    courses_data.sort(key=lambda c: c["course_code"])

    overall_attendance = (
        round((total_present / total_classes) * 100, 1)
        if total_classes > 0
        else 0.0
    )

    # 4. Weekly Trend Calculation
    today = date.today()
    trend_points = []

    for i in range(trend_weeks - 1, -1, -1):
        end_d = today - timedelta(days=i * 7)
        start_d = end_d - timedelta(days=6)
        label = start_d.strftime("%b %d")

        period_records = []
        if offering_ids:
            period_records = (
                AttendanceRecord.query
                .filter_by(student_id=student.student_id)
                .join(AttendanceSession)
                .filter(
                    AttendanceSession.session_date >= start_d,
                    AttendanceSession.session_date <= end_d,
                    AttendanceSession.offering_id.in_(offering_ids),
                )
                .all()
            )

        period_total = len(period_records)
        period_present = sum(1 for r in period_records if r.status == "PRESENT")
        rate = (
            round((period_present / period_total) * 100, 1)
            if period_total > 0
            else None
        )
        trend_points.append({
            "label": label,
            "start_date": start_d.isoformat(),
            "end_date": end_d.isoformat(),
            "rate": rate,
            "total": period_total,
            "present": period_present,
        })

    trend_change = None
    attended_change = None
    missed_change = None
    if len(trend_points) >= 2:
        last_rate = trend_points[-1]["rate"]
        prev_rate = trend_points[-2]["rate"]
        if last_rate is not None and prev_rate is not None:
            trend_change = round(last_rate - prev_rate, 1)
        elif last_rate is not None:
            trend_change = round(last_rate, 1)
        else:
            trend_change = None

        last_present = trend_points[-1]["present"]
        prev_present = trend_points[-2]["present"]
        if prev_present > 0:
            attended_change = round(((last_present - prev_present) / prev_present) * 100, 1)
        elif last_present > 0:
            attended_change = 100.0
        else:
            attended_change = 0.0

        last_missed = max(0, trend_points[-1]["total"] - trend_points[-1]["present"])
        prev_missed = max(0, trend_points[-2]["total"] - trend_points[-2]["present"])
        if prev_missed > 0:
            missed_change = round(((last_missed - prev_missed) / prev_missed) * 100, 1)
        elif last_missed > 0:
            missed_change = 100.0
        else:
            missed_change = 0.0

    # 5. Today's Schedule
    today_weekday = datetime.now().strftime("%A")
    today_entries = []

    if offering_ids:
        raw_entries = (
            TimetableEntry.query
            .filter(
                TimetableEntry.offering_id.in_(offering_ids),
                func.lower(TimetableEntry.day_of_week) == today_weekday.lower(),
            )
            .order_by(TimetableEntry.start_time.asc())
            .all()
        )

        now_time = datetime.now().time()

        for entry in raw_entries:
            offering = entry.offering
            course = offering.course if offering else None

            if now_time > entry.end_time:
                class_status = "COMPLETED"
            elif entry.start_time <= now_time <= entry.end_time:
                class_status = "ONGOING"
            else:
                class_status = "UPCOMING"

            faculty_name = None
            if offering and offering.faculty and offering.faculty.user:
                faculty_name = offering.faculty.user.name

            st_str = datetime.combine(today, entry.start_time).strftime("%I:%M %p")
            et_str = datetime.combine(today, entry.end_time).strftime("%I:%M %p")

            today_entries.append({
                "timetable_entry_id": entry.timetable_entry_id,
                "offering_id": entry.offering_id,
                "start_time": st_str,
                "end_time": et_str,
                "time_slot": f"{st_str} - {et_str}",
                "course_code": course.course_code if course else None,
                "course_name": course.course_name if course else None,
                "section": offering.section if offering else None,
                "room": entry.room or (offering.room if offering else None) or None,
                "faculty_name": faculty_name,
                "status": class_status,
            })

    # 6. Recent Attendance (Latest 5 records)
    recent_records = (
        AttendanceRecord.query
        .filter_by(student_id=student.student_id)
        .join(AttendanceSession)
        .order_by(
            AttendanceSession.session_date.desc(),
            AttendanceRecord.marked_at.desc(),
        )
        .limit(5)
        .all()
    )

    recent_attendance_list = []
    for r in recent_records:
        sess = r.session
        off = sess.offering if sess else None
        c = off.course if off else None
        recent_attendance_list.append({
            "attendance_id": r.attendance_id,
            "session_id": r.session_id,
            "date": sess.session_date.strftime("%b %d, %Y") if sess and sess.session_date else None,
            "session_date": sess.session_date.isoformat() if sess and sess.session_date else None,
            "subject": c.course_name if c else None,
            "course_code": c.course_code if c else None,
            "status": r.status,
            "marked_at": r.marked_at.isoformat() if r.marked_at else None,
        })

    return jsonify({
        "success": True,
        "data": {
            "role": "STUDENT",
            "student": student_data,
            "stats": {
                "overall_attendance_percentage": overall_attendance,
                "attendance_change_percentage": trend_change,
                "classes_attended": total_present,
                "attended_change_percentage": attended_change,
                "classes_missed": total_absent,
                "missed_change_percentage": missed_change,
                "total_classes_scheduled": total_classes,
                "enrolled_courses_count": len(courses_data),
                "is_above_average": overall_attendance >= 75.0,
            },
            "attendance_trend": {
                "weeks": trend_weeks,
                "current_percentage": overall_attendance,
                "change_percentage": trend_change,
                "is_above_average": overall_attendance >= 75.0,
                "points": trend_points,
            },
            "today_schedule": {
                "day_of_week": today_weekday,
                "date_display": datetime.now().strftime("%b %d, %Y (%a)"),
                "classes": today_entries,
            },
            "courses": courses_data,
            "recent_attendance": recent_attendance_list,
        },
    }), 200


# ============================================================
# GET STUDENT PROFILE
# ============================================================

@student_bp.get("/profile")
@student_or_admin_required
def get_student_profile():
    student = get_current_student()

    if not student:
        return jsonify({
            "success": False,
            "message": "Student profile not found",
        }), 404

    return jsonify({
        "success": True,
        "data": serialize_student_profile(student),
    }), 200


# ============================================================
# UPDATE STUDENT PROFILE
# ============================================================

@student_bp.patch("/profile")
@student_or_admin_required
def update_student_profile():
    student = get_current_student()

    if not student:
        return jsonify({
            "success": False,
            "message": "Student profile not found",
        }), 404

    data = request.get_json(silent=True) or {}

    # Basic identity
    name = data.get("name")
    if name is not None:
        name = str(name).strip()
        if not name:
            return jsonify({
                "success": False,
                "message": "Name cannot be empty",
            }), 400
        student.user.name = name

    # Phone (sync to both student & user)
    if "phone" in data:
        phone_val = str(data["phone"]).strip() if data["phone"] is not None else None
        student.phone = phone_val
        student.user.phone = phone_val

    # Family & Guardian details
    if "father_name" in data:
        student.father_name = str(data["father_name"]).strip() if data["father_name"] is not None else None

    if "mother_name" in data:
        student.mother_name = str(data["mother_name"]).strip() if data["mother_name"] is not None else None

    if "guardian_phone" in data:
        student.guardian_phone = str(data["guardian_phone"]).strip() if data["guardian_phone"] is not None else None

    # Personal characteristics
    if "blood_group" in data:
        student.blood_group = str(data["blood_group"]).strip().upper() if data["blood_group"] is not None else None

    if "gender" in data:
        student.gender = str(data["gender"]).strip() if data["gender"] is not None else None

    if "date_of_birth" in data:
        student.date_of_birth = str(data["date_of_birth"]).strip() if data["date_of_birth"] is not None else None

    # Address & Location
    if "address" in data:
        student.address = str(data["address"]).strip() if data["address"] is not None else None

    if "city" in data:
        student.city = str(data["city"]).strip() if data["city"] is not None else None

    if "state" in data:
        student.state = str(data["state"]).strip() if data["state"] is not None else None

    if "pin_code" in data:
        student.pin_code = str(data["pin_code"]).strip() if data["pin_code"] is not None else None

    if "country" in data:
        student.country = str(data["country"]).strip() if data["country"] is not None else "India"

    # Emergency Contact
    if "emergency_contact_name" in data:
        student.emergency_contact_name = str(data["emergency_contact_name"]).strip() if data["emergency_contact_name"] is not None else None

    if "emergency_contact_phone" in data:
        student.emergency_contact_phone = str(data["emergency_contact_phone"]).strip() if data["emergency_contact_phone"] is not None else None

    # Direct photo or signature URL updates (if uploaded separately)
    if data.get("photo_url"):
        student.photo_url = str(data["photo_url"]).strip()

    if data.get("signature_url"):
        student.signature_url = str(data["signature_url"]).strip()

    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Student profile updated successfully",
        "data": serialize_student_profile(student),
    }), 200


# ============================================================
# UPLOAD PASSPORT-SIZE PHOTO (< 50 KB STRICT)
# ============================================================

@student_bp.post("/upload-photo")
@student_or_admin_required
def upload_student_photo():
    student = get_current_student()

    if not student:
        return jsonify({
            "success": False,
            "message": "Student profile not found",
        }), 404

    file_bytes = None
    ext = "jpg"

    # Option A: Multipart/form-data upload
    if "file" in request.files or "photo" in request.files:
        uploaded_file = request.files.get("file") or request.files.get("photo")
        if not uploaded_file or not uploaded_file.filename:
            return jsonify({
                "success": False,
                "message": "No file was selected for upload",
            }), 400

        filename = secure_filename(uploaded_file.filename)
        if not is_allowed_file(filename):
            return jsonify({
                "success": False,
                "message": f"Unsupported file type. Allowed formats: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
            }), 400

        ext = filename.rsplit(".", 1)[-1].lower()
        file_bytes = uploaded_file.read()

    # Option B: Base64 JSON data_url
    else:
        json_data = request.get_json(silent=True) or {}
        data_url = json_data.get("image") or json_data.get("data_url") or json_data.get("photo")
        if data_url and isinstance(data_url, str) and "base64," in data_url:
            header, encoded = data_url.split("base64,", 1)
            try:
                file_bytes = base64.b64decode(encoded)
                if "png" in header:
                    ext = "png"
                elif "webp" in header:
                    ext = "webp"
                else:
                    ext = "jpg"
            except (ValueError, KeyError, IndexError, TypeError):
                return jsonify({
                    "success": False,
                    "message": "Invalid base64 image data",
                }), 400
        else:
            return jsonify({
                "success": False,
                "message": "Upload a photo file or base64 image data",
            }), 400

    # STRICT SIZE VALIDATION (< 50 KB)
    if len(file_bytes) > MAX_IMAGE_SIZE_BYTES:
        size_kb = len(file_bytes) / 1024
        return jsonify({
            "success": False,
            "message": f"Passport-size photo must be strictly less than 50 KB. (Selected file: {size_kb:.1f} KB)",
        }), 400

    old_photo_url = student.photo_url

    # Save to disk
    save_filename = f"student_photo_{student.student_id}_{int(time.time() * 1000)}.{ext}"
    filepath = os.path.join(PHOTOS_DIR, save_filename)

    with open(filepath, "wb") as f:
        f.write(file_bytes)

    # Update database
    photo_url = f"/api/student/uploads/photos/{save_filename}"
    student.photo_url = photo_url
    db.session.commit()

    # Safely clean up previous photo file from disk if it exists and differs from new file
    if old_photo_url and old_photo_url.startswith("/api/student/uploads/photos/"):
        old_filename = os.path.basename(old_photo_url)
        old_filepath = os.path.join(PHOTOS_DIR, old_filename)
        if os.path.exists(old_filepath) and os.path.abspath(old_filepath) != os.path.abspath(filepath):
            try:
                os.remove(old_filepath)
            except OSError:
                pass

    return jsonify({
        "success": True,
        "message": "Passport-size photo uploaded successfully",
        "photo_url": photo_url,
        "file_size_kb": round(len(file_bytes) / 1024, 2),
    }), 200


# ============================================================
# UPLOAD SIGNATURE (< 50 KB STRICT)
# ============================================================

@student_bp.post("/upload-signature")
@student_or_admin_required
def upload_student_signature():
    student = get_current_student()

    if not student:
        return jsonify({
            "success": False,
            "message": "Student profile not found",
        }), 404

    file_bytes = None
    ext = "png"

    # Option A: Multipart/form-data upload
    if "file" in request.files or "signature" in request.files:
        uploaded_file = request.files.get("file") or request.files.get("signature")
        if not uploaded_file or not uploaded_file.filename:
            return jsonify({
                "success": False,
                "message": "No signature file was selected for upload",
            }), 400

        filename = secure_filename(uploaded_file.filename)
        if not is_allowed_file(filename):
            return jsonify({
                "success": False,
                "message": f"Unsupported file type. Allowed formats: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
            }), 400

        ext = filename.rsplit(".", 1)[-1].lower()
        file_bytes = uploaded_file.read()

    # Option B: Base64 JSON data_url
    else:
        json_data = request.get_json(silent=True) or {}
        data_url = json_data.get("signature") or json_data.get("data_url") or json_data.get("image")
        if data_url and isinstance(data_url, str) and "base64," in data_url:
            header, encoded = data_url.split("base64,", 1)
            try:
                file_bytes = base64.b64decode(encoded)
                if "png" in header:
                    ext = "png"
                elif "webp" in header:
                    ext = "webp"
                else:
                    ext = "jpg"
            except (ValueError, KeyError, IndexError, TypeError):
                return jsonify({
                    "success": False,
                    "message": "Invalid base64 signature data",
                }), 400
        else:
            return jsonify({
                "success": False,
                "message": "Upload a signature file or base64 signature data",
            }), 400

    # STRICT SIZE VALIDATION (< 50 KB)
    if len(file_bytes) > MAX_IMAGE_SIZE_BYTES:
        size_kb = len(file_bytes) / 1024
        return jsonify({
            "success": False,
            "message": f"Signature must be strictly less than 50 KB. (Selected file: {size_kb:.1f} KB)",
        }), 400

    # Save to disk
    save_filename = f"student_sig_{student.student_id}_{int(time.time())}.{ext}"
    filepath = os.path.join(SIGNATURES_DIR, save_filename)

    with open(filepath, "wb") as f:
        f.write(file_bytes)

    # Update database
    signature_url = f"/api/student/uploads/signatures/{save_filename}"
    student.signature_url = signature_url
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Signature uploaded successfully",
        "signature_url": signature_url,
        "file_size_kb": round(len(file_bytes) / 1024, 2),
    }), 200


# ============================================================
# SERVE STUDENT UPLOADS
# ============================================================

@student_bp.get("/uploads/<folder>/<filename>")
@jwt_required()
def serve_student_upload(folder, filename):
    if folder not in ("photos", "signatures"):
        return jsonify({
            "success": False,
            "message": "Invalid upload category",
        }), 404

    # Strict path traversal checks: reject traversal tokens or slashes
    if ".." in filename or "/" in filename or "\\" in filename or "\0" in filename:
        return jsonify({
            "success": False,
            "message": "Invalid filename",
        }), 400

    safe_filename = secure_filename(filename)
    if not safe_filename or safe_filename != filename:
        return jsonify({
            "success": False,
            "message": "Invalid filename",
        }), 400

    # Extract target student ID from strict filename pattern
    if folder == "photos":
        match = re.match(r"^student_photo_(\d+)_(\d+)\.(?:jpg|jpeg|png|webp)$", safe_filename, re.IGNORECASE)
    else:
        match = re.match(r"^student_sig_(\d+)_(\d+)\.(?:jpg|jpeg|png|webp)$", safe_filename, re.IGNORECASE)

    if not match:
        return jsonify({
            "success": False,
            "message": "File not found",
        }), 404

    target_student_id = int(match.group(1))

    # Evaluate caller authorization
    claims = get_jwt()
    user_role = (claims.get("role") or "").strip().upper()
    identity = get_jwt_identity()

    authorized = False
    if user_role == "ADMIN":
        # Admin can access all student uploads
        authorized = True
    elif folder == "photos" and user_role == "FACULTY":
        # Faculty can view student profile photos for attendance and academic rosters
        authorized = True
    elif user_role == "STUDENT":
        # Students can only access their own photo and signature
        try:
            user_id = int(identity)
        except (ValueError, TypeError):
            user_id = None

        if user_id:
            current_student = Student.query.filter_by(user_id=user_id).first()
            if current_student and current_student.student_id == target_student_id:
                authorized = True

    if not authorized:
        return jsonify({
            "success": False,
            "message": "Access forbidden",
        }), 403

    target_dir = PHOTOS_DIR if folder == "photos" else SIGNATURES_DIR
    target_path = os.path.realpath(os.path.join(target_dir, safe_filename))
    base_canonical = os.path.realpath(target_dir)

    # Symlink escape / jail check
    if not target_path.startswith(base_canonical + os.path.sep) and target_path != base_canonical:
        return jsonify({
            "success": False,
            "message": "Access denied",
        }), 400

    if not os.path.isfile(target_path):
        return jsonify({
            "success": False,
            "message": "File not found",
        }), 404

    return send_from_directory(target_dir, safe_filename)


# ============================================================
# CHANGE STUDENT PASSWORD
# ============================================================

@student_bp.post("/change-password")
@student_or_admin_required
def change_student_password():
    student = get_current_student()

    if not student:
        return jsonify({
            "success": False,
            "message": "Student profile not found",
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
            "message": "New password and confirm password do not match",
        }), 400

    if not bcrypt.check_password_hash(student.user.password_hash, str(current_password)):
        return jsonify({
            "success": False,
            "message": "Current password is incorrect",
        }), 400

    student.user.password_hash = bcrypt.generate_password_hash(str(new_password)).decode("utf-8")
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Password changed successfully",
    }), 200


# ============================================================
# STUDENT COURSES
# ============================================================

DAY_ORDER = {
    "monday": 1,
    "tuesday": 2,
    "wednesday": 3,
    "thursday": 4,
    "friday": 5,
    "saturday": 6,
    "sunday": 7,
}

DAY_ABBR = {
    "monday": "Mon",
    "tuesday": "Tue",
    "wednesday": "Wed",
    "thursday": "Thu",
    "friday": "Fri",
    "saturday": "Sat",
    "sunday": "Sun",
}


def format_timetable_schedules(timetable_entries):
    if not timetable_entries:
        return "Schedule not assigned", []

    sorted_entries = sorted(
        timetable_entries,
        key=lambda e: (
            DAY_ORDER.get((e.day_of_week or "").strip().lower(), 99),
            e.start_time or datetime.min.time(),
        ),
    )

    schedules_list = []
    from collections import OrderedDict
    slot_days = OrderedDict()

    for entry in sorted_entries:
        day_clean = (entry.day_of_week or "").strip().capitalize()
        day_key = day_clean.lower()
        abbr = DAY_ABBR.get(day_key, day_clean[:3])

        st_str = (
            datetime.combine(date.today(), entry.start_time).strftime("%I:%M %p")
            if entry.start_time
            else ""
        )
        et_str = (
            datetime.combine(date.today(), entry.end_time).strftime("%I:%M %p")
            if entry.end_time
            else ""
        )
        time_slot = f"{st_str} - {et_str}" if st_str and et_str else ""

        schedules_list.append({
            "timetable_entry_id": entry.timetable_entry_id,
            "day_of_week": day_clean,
            "day_abbr": abbr,
            "start_time": st_str,
            "end_time": et_str,
            "time_slot": time_slot,
            "room": entry.room or None,
        })

        if time_slot:
            if time_slot not in slot_days:
                slot_days[time_slot] = []
            if abbr not in slot_days[time_slot]:
                slot_days[time_slot].append(abbr)

    if not slot_days:
        return "Schedule not assigned", schedules_list

    parts = []
    for slot, days in slot_days.items():
        parts.append(f"{', '.join(days)} {slot}")

    if len(parts) > 2:
        all_days = list(OrderedDict.fromkeys([s["day_abbr"] for s in schedules_list]))
        summary = f"{', '.join(all_days)} (Multiple slots)"
    else:
        summary = "; ".join(parts)

    return summary, schedules_list


# ============================================================
# STUDENT COURSES
# ============================================================

@student_bp.get("/courses")
@student_or_admin_required
def get_student_courses():
    student = get_current_student()

    if not student:
        return jsonify({
            "success": False,
            "message": "Student profile not found",
        }), 404

    # Validate query parameters
    semester_arg = request.args.get("semester")
    dept_id_arg = request.args.get("department_id")
    search_arg = (request.args.get("search") or request.args.get("q") or "").strip().lower()

    filter_semester = None
    if semester_arg is not None and semester_arg.strip() != "" and semester_arg.strip().lower() != "all":
        try:
            filter_semester = int(semester_arg)
        except (ValueError, TypeError):
            return jsonify({
                "success": False,
                "message": "Invalid semester parameter. Must be an integer.",
            }), 400

    filter_dept_id = None
    if dept_id_arg is not None and dept_id_arg.strip() != "" and dept_id_arg.strip().lower() != "all":
        try:
            filter_dept_id = int(dept_id_arg)
        except (ValueError, TypeError):
            return jsonify({
                "success": False,
                "message": "Invalid department_id parameter. Must be an integer.",
            }), 400

    enrollments = (
        Enrollment.query
        .options(
            joinedload(Enrollment.offering).joinedload(CourseOffering.course).joinedload(Course.department),
            joinedload(Enrollment.offering).joinedload(CourseOffering.faculty).joinedload(Faculty.user),
            joinedload(Enrollment.offering).joinedload(CourseOffering.timetable_entries),
        )
        .filter_by(
            student_id=student.student_id,
            status="ACTIVE",
        )
        .all()
    )

    offering_ids = [e.offering_id for e in enrollments if e.offering_id]

    # Pre-fetch closed sessions and student's present records in batch
    from collections import defaultdict
    offering_sessions_map = defaultdict(set)
    all_closed_session_ids = set()

    if offering_ids:
        closed_sessions = (
            AttendanceSession.query
            .filter(
                AttendanceSession.offering_id.in_(offering_ids),
                AttendanceSession.status == "CLOSED",
            )
            .all()
        )
        for s in closed_sessions:
            offering_sessions_map[s.offering_id].add(s.session_id)
            all_closed_session_ids.add(s.session_id)

    student_present_session_ids = set()
    if all_closed_session_ids:
        pres_rows = (
            db.session.query(AttendanceRecord.session_id)
            .filter(
                AttendanceRecord.student_id == student.student_id,
                AttendanceRecord.session_id.in_(all_closed_session_ids),
                AttendanceRecord.status == "PRESENT",
            )
            .all()
        )
        student_present_session_ids = {r[0] for r in pres_rows}

    # Upcoming classes calculation for next 7 calendar days
    today = date.today()
    now_time = datetime.now().time()
    upcoming_classes_count = 0

    for day_offset in range(7):
        target_date = today + timedelta(days=day_offset)
        target_day_name = target_date.strftime("%A").lower()

        for enr in enrollments:
            off = enr.offering
            if not off:
                continue
            for tt in off.timetable_entries:
                if (tt.day_of_week or "").strip().lower() == target_day_name:
                    if day_offset == 0:
                        if tt.start_time > now_time:
                            upcoming_classes_count += 1
                    else:
                        upcoming_classes_count += 1

    # Today's schedule entries
    today_weekday = datetime.now().strftime("%A").lower()
    today_schedule_entries = []

    for enr in enrollments:
        off = enr.offering
        if not off:
            continue
        c = off.course
        for tt in off.timetable_entries:
            if (tt.day_of_week or "").strip().lower() == today_weekday:
                if now_time > tt.end_time:
                    slot_status = "COMPLETED"
                elif tt.start_time <= now_time <= tt.end_time:
                    slot_status = "ONGOING"
                else:
                    slot_status = "UPCOMING"

                st_str = datetime.combine(today, tt.start_time).strftime("%I:%M %p")
                et_str = datetime.combine(today, tt.end_time).strftime("%I:%M %p")

                today_schedule_entries.append({
                    "timetable_entry_id": tt.timetable_entry_id,
                    "offering_id": off.offering_id,
                    "course_code": c.course_code if c else "",
                    "course_name": c.course_name if c else "",
                    "time_slot": f"{st_str} - {et_str}",
                    "start_time": st_str,
                    "end_time": et_str,
                    "raw_start_time": str(tt.start_time),
                    "room": tt.room or off.room or "TBD",
                    "status": slot_status,
                })

    today_schedule_entries.sort(key=lambda x: x["raw_start_time"])

    # Build course records and distinct department/semester filters
    all_courses_data = []
    seen_departments = {}
    seen_semesters = set()

    total_sessions_all = 0
    total_present_all = 0

    for enrollment in enrollments:
        offering = enrollment.offering
        course = offering.course if offering else None
        if not course:
            continue

        dept = course.department
        if dept and dept.department_id not in seen_departments:
            seen_departments[dept.department_id] = {
                "department_id": dept.department_id,
                "department_name": dept.department_name,
                "department_code": dept.department_code,
            }

        if offering.semester is not None:
            seen_semesters.add(offering.semester)

        session_ids = offering_sessions_map[offering.offering_id]
        course_total_sessions = len(session_ids)
        course_present = len(session_ids & student_present_session_ids)
        course_absent = max(0, course_total_sessions - course_present)

        total_sessions_all += course_total_sessions
        total_present_all += course_present

        course_pct = (
            round((course_present / course_total_sessions) * 100, 1)
            if course_total_sessions > 0
            else None
        )

        sched_summary, sched_list = format_timetable_schedules(offering.timetable_entries)

        faculty_payload = None
        if offering.faculty:
            fac_user = offering.faculty.user
            faculty_payload = {
                "faculty_id": offering.faculty.faculty_id,
                "name": fac_user.name if fac_user else None,
                "employee_id": offering.faculty.employee_id,
                "designation": offering.faculty.designation,
                "email": fac_user.email if fac_user else None,
            }

        all_courses_data.append({
            "enrollment_id": enrollment.enrollment_id,
            "offering_id": offering.offering_id,
            "course_id": course.course_id,
            "course_code": course.course_code,
            "course_name": course.course_name,
            "credits": course.credits,
            "semester": offering.semester,
            "section": offering.section,
            "academic_year": offering.academic_year,
            "room": offering.room or (sched_list[0]["room"] if sched_list else None) or "TBD",
            "department": (
                {
                    "department_id": dept.department_id,
                    "department_name": dept.department_name,
                    "department_code": dept.department_code,
                }
                if dept
                else None
            ),
            "faculty": faculty_payload,
            "schedule_summary": sched_summary,
            "schedules": sched_list,
            "attendance": {
                "total_sessions": course_total_sessions,
                "present_sessions": course_present,
                "absent_sessions": course_absent,
                "attendance_percentage": course_pct,
            },
        })

    all_courses_data.sort(key=lambda c: c["course_code"])

    overall_attendance = (
        round((total_present_all / total_sessions_all) * 100, 1)
        if total_sessions_all > 0
        else None
    )

    stats_payload = {
        "total_courses": len(all_courses_data),
        "upcoming_classes_7_days": upcoming_classes_count,
        "completed_classes_semester": len(all_closed_session_ids),
        "overall_attendance_rate": overall_attendance,
        "has_attendance_data": total_sessions_all > 0,
    }

    # Apply filters if provided
    filtered_courses = all_courses_data
    if filter_semester is not None:
        filtered_courses = [c for c in filtered_courses if c["semester"] == filter_semester]
    if filter_dept_id is not None:
        filtered_courses = [
            c for c in filtered_courses
            if c["department"] and c["department"]["department_id"] == filter_dept_id
        ]
    if search_arg:
        filtered_courses = [
            c for c in filtered_courses
            if search_arg in (c["course_code"] or "").lower()
            or search_arg in (c["course_name"] or "").lower()
            or (c["faculty"] and search_arg in (c["faculty"]["name"] or "").lower())
            or (c["department"] and search_arg in (c["department"]["department_name"] or "").lower())
        ]

    departments_list = sorted(list(seen_departments.values()), key=lambda d: d["department_name"])
    semesters_list = sorted(list(seen_semesters))

    return jsonify({
        "success": True,
        "data": filtered_courses,
        "stats": stats_payload,
        "today_schedule": today_schedule_entries,
        "departments": departments_list,
        "semesters": semesters_list,
    }), 200


# ============================================================
# STUDENT COURSE DETAIL
# ============================================================

@student_bp.get("/courses/<int:offering_id>")
@student_or_admin_required
def get_student_course_detail(offering_id):
    student = get_current_student()

    if not student:
        return jsonify({
            "success": False,
            "message": "Student profile not found",
        }), 404

    claims = get_jwt()
    user_role = (claims.get("role") or "").strip().upper()

    enrollment = (
        Enrollment.query
        .options(
            joinedload(Enrollment.offering).joinedload(CourseOffering.course).joinedload(Course.department),
            joinedload(Enrollment.offering).joinedload(CourseOffering.faculty).joinedload(Faculty.user),
            joinedload(Enrollment.offering).joinedload(CourseOffering.timetable_entries),
        )
        .filter_by(
            student_id=student.student_id,
            offering_id=offering_id,
            status="ACTIVE",
        )
        .first()
    )

    if not enrollment:
        offering_exists = CourseOffering.query.filter_by(offering_id=offering_id).first()
        if not offering_exists:
            return jsonify({
                "success": False,
                "message": "Course offering not found",
            }), 404

        if user_role != "ADMIN":
            return jsonify({
                "success": False,
                "message": "You are not enrolled in this course offering",
            }), 403

        offering = offering_exists
    else:
        offering = enrollment.offering

    course = offering.course if offering else None
    if not course:
        return jsonify({
            "success": False,
            "message": "Course not found for offering",
        }), 404

    # Attendance for this offering
    closed_sessions = (
        AttendanceSession.query
        .filter_by(offering_id=offering.offering_id, status="CLOSED")
        .all()
    )
    closed_session_ids = [s.session_id for s in closed_sessions]
    present_records_count = 0
    if closed_session_ids:
        present_records_count = (
            AttendanceRecord.query
            .filter(
                AttendanceRecord.student_id == student.student_id,
                AttendanceRecord.session_id.in_(closed_session_ids),
                AttendanceRecord.status == "PRESENT",
            )
            .count()
        )

    total_sessions = len(closed_session_ids)
    absent_count = max(0, total_sessions - present_records_count)
    attendance_pct = (
        round((present_records_count / total_sessions) * 100, 1)
        if total_sessions > 0
        else None
    )

    sched_summary, sched_list = format_timetable_schedules(offering.timetable_entries)

    faculty_payload = None
    if offering.faculty:
        fac_user = offering.faculty.user
        faculty_payload = {
            "faculty_id": offering.faculty.faculty_id,
            "name": fac_user.name if fac_user else None,
            "employee_id": offering.faculty.employee_id,
            "designation": offering.faculty.designation,
            "email": fac_user.email if fac_user else None,
            "phone": offering.faculty.phone or (fac_user.phone if fac_user else None),
        }

    dept = course.department

    return jsonify({
        "success": True,
        "data": {
            "enrollment_id": enrollment.enrollment_id if enrollment else None,
            "offering_id": offering.offering_id,
            "course_id": course.course_id,
            "course_code": course.course_code,
            "course_name": course.course_name,
            "credits": course.credits,
            "semester": offering.semester,
            "section": offering.section,
            "academic_year": offering.academic_year,
            "room": offering.room or (sched_list[0]["room"] if sched_list else None) or "TBD",
            "department": (
                {
                    "department_id": dept.department_id,
                    "department_name": dept.department_name,
                    "department_code": dept.department_code,
                }
                if dept
                else None
            ),
            "faculty": faculty_payload,
            "schedule_summary": sched_summary,
            "schedules": sched_list,
            "attendance": {
                "total_sessions": total_sessions,
                "present_sessions": present_records_count,
                "absent_sessions": absent_count,
                "attendance_percentage": attendance_pct,
            },
        },
    }), 200
