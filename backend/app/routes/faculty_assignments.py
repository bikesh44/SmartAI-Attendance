"""
Faculty Assignment & Notes Management Routes
SAMS-FR (Smart Attendance Management System)

Provides complete backend endpoints for:
- Summary metrics (Total Assignments, Total Notes, Total Submissions, Pending Review)
- Course offerings taught by authenticated faculty
- Assignment CRUD (Create, Read, Update, Delete, Toggle Status)
- Assignment attachment upload & download
- Study materials / Notes CRUD (Upload, List, Edit, Delete, Download)
- Submissions review, grading & evaluation
- Submissions file download
- Class overview & Recent uploads
"""

from datetime import datetime, date
import os
import re
import uuid
from typing import Optional, Tuple

from flask import Blueprint, jsonify, request, send_file
from flask_jwt_extended import get_jwt, get_jwt_identity, verify_jwt_in_request
from sqlalchemy.orm import joinedload
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models.assignment import CourseAssignment, Assignment
from app.models.study_material import StudyMaterial, Note
from app.models.assignment_submission import AssignmentSubmission
from app.models.course import Course
from app.models.course_offering import CourseOffering
from app.models.department import Department
from app.models.enrollment import Enrollment
from app.models.faculty import Faculty
from app.models.student import Student
from app.models.user import User
from app.utils.auth import faculty_or_admin_required, faculty_required

faculty_assignments_bp = Blueprint(
    "faculty_assignments",
    __name__,
    url_prefix="/api/faculty/assignments",
)

# Upload directory configuration
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
UPLOAD_BASE_DIR = os.path.join(BACKEND_DIR, "uploads")
ASSIGNMENTS_DIR = os.path.join(UPLOAD_BASE_DIR, "assignments")
MATERIALS_DIR = os.path.join(UPLOAD_BASE_DIR, "materials")
SUBMISSIONS_DIR = os.path.join(UPLOAD_BASE_DIR, "submissions")

for folder in (ASSIGNMENTS_DIR, MATERIALS_DIR, SUBMISSIONS_DIR):
    os.makedirs(folder, exist_ok=True)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_current_faculty_and_user() -> Tuple[Optional[Faculty], Optional[User], bool]:
    """Retrieves current faculty record, user record, and admin status from JWT."""
    verify_jwt_in_request()
    claims = get_jwt()
    is_admin = claims.get("role") == "ADMIN"
    user_id = get_jwt_identity()

    try:
        user_id_int = int(user_id) if user_id is not None else None
    except (TypeError, ValueError):
        user_id_int = None

    if not user_id_int:
        return None, None, False

    user = db.session.get(User, user_id_int)
    faculty = Faculty.query.filter_by(user_id=user_id_int).first()

    return faculty, user, is_admin


def get_faculty_offering_ids(faculty_id: int) -> list:
    """Returns list of offering IDs taught by this faculty."""
    offerings = CourseOffering.query.filter_by(faculty_id=faculty_id).all()
    return [o.offering_id for o in offerings]


def is_faculty_authorized_for_offering(faculty_id: int, offering_id: int, is_admin: bool = False) -> bool:
    """Checks if faculty owns this course offering (or if caller is admin)."""
    if is_admin:
        return True
    offering = CourseOffering.query.filter_by(offering_id=offering_id, faculty_id=faculty_id).first()
    return offering is not None


def safe_file_path(base_dir: str, file_path: str) -> Optional[str]:
    """Validates that file_path resides strictly within base_dir and exists."""
    if not file_path:
        return None
    full_path = os.path.abspath(file_path)
    base_path = os.path.abspath(base_dir)
    try:
        common = os.path.commonpath([base_path, full_path])
        if common != base_path:
            return None
    except ValueError:
        return None
    if not os.path.isfile(full_path):
        return None
    return full_path


def parse_date_string(date_val) -> Optional[datetime]:
    """Parses various date and datetime formats."""
    if not date_val:
        return None
    if isinstance(date_val, datetime):
        return date_val
    if isinstance(date_val, date):
        return datetime.combine(date_val, datetime.min.time())

    date_str = str(date_val).strip()
    # Try ISO formats
    for fmt in (
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            pass

    # Try fromisoformat (handles subseconds / timezone if standard)
    try:
        clean_str = re.sub(r"Z$", "", date_str)
        return datetime.fromisoformat(clean_str)
    except Exception:
        return None


def calculate_due_status(due_date: datetime) -> Tuple[str, str]:
    """
    Returns (status_badge, relative_text).
    status_badge: 'Active' | 'Upcoming' | 'Overdue' | 'Due Today'
    """
    if not due_date:
        return "Active", ""

    now = datetime.utcnow()
    diff = due_date - now

    if diff.total_seconds() < 0:
        return "Overdue", "Overdue"

    days = diff.days
    hours = int(diff.seconds / 3600)

    if days == 0:
        if hours <= 1:
            return "Active", "Due soon"
        return "Active", f"{hours} hours left"
    elif days == 1:
        return "Active", "1 day left"
    elif days <= 7:
        return "Active", f"{days} days left"
    else:
        return "Upcoming", f"{days} days left"


# ============================================================
# 1. SUMMARY METRICS
# ============================================================

@faculty_assignments_bp.route("/summary", methods=["GET"])
@faculty_required
def get_assignment_summary():
    """Returns 4 summary card statistics for the logged-in faculty."""
    faculty, user, is_admin = get_current_faculty_and_user()
    if not faculty and not is_admin:
        return jsonify({"success": False, "message": "Faculty profile not found"}), 404

    offering_ids = get_faculty_offering_ids(faculty.faculty_id) if faculty else []

    if not offering_ids:
        return jsonify({
            "success": True,
            "summary": {
                "total_assignments": 0,
                "total_notes": 0,
                "total_submissions": 0,
                "pending_review": 0,
                "classes_count": 0,
            },
        }), 200

    total_assignments = CourseAssignment.query.filter(CourseAssignment.offering_id.in_(offering_ids)).count()
    total_notes = StudyMaterial.query.filter(StudyMaterial.offering_id.in_(offering_ids)).count()

    # Total submissions received for faculty's assignments
    total_submissions = (
        AssignmentSubmission.query.join(CourseAssignment, AssignmentSubmission.assignment_id == CourseAssignment.assignment_id)
        .filter(CourseAssignment.offering_id.in_(offering_ids))
        .count()
    )

    pending_review = (
        AssignmentSubmission.query.join(CourseAssignment, AssignmentSubmission.assignment_id == CourseAssignment.assignment_id)
        .filter(
            CourseAssignment.offering_id.in_(offering_ids),
            AssignmentSubmission.review_status == "PENDING",
        )
        .count()
    )

    return jsonify({
        "success": True,
        "summary": {
            "total_assignments": total_assignments,
            "total_notes": total_notes,
            "total_submissions": total_submissions,
            "pending_review": pending_review,
            "classes_count": len(offering_ids),
        },
    }), 200


# ============================================================
# 2. COURSE OFFERINGS / CLASSES FOR DROPDOWNS
# ============================================================

@faculty_assignments_bp.route("/classes", methods=["GET"])
@faculty_required
def get_faculty_classes():
    """Returns course offerings taught by the logged-in faculty."""
    faculty, user, is_admin = get_current_faculty_and_user()
    if not faculty and not is_admin:
        return jsonify({"success": False, "message": "Faculty profile not found"}), 404

    offerings = (
        CourseOffering.query.filter_by(faculty_id=faculty.faculty_id)
        .options(joinedload(CourseOffering.course).joinedload(Course.department))
        .order_by(CourseOffering.academic_year.desc(), CourseOffering.semester.asc())
        .all()
    )

    classes_data = []
    for offering in offerings:
        course = offering.course
        enrolled_count = Enrollment.query.filter_by(
            offering_id=offering.offering_id,
            status="ACTIVE",
        ).count()

        classes_data.append({
            "offering_id": offering.offering_id,
            "course_id": offering.course_id,
            "course_code": course.course_code if course else "",
            "course_name": course.course_name if course else "",
            "department_name": course.department.department_name if course and course.department else "",
            "section": offering.section,
            "semester": offering.semester,
            "academic_year": offering.academic_year,
            "room": offering.room or "",
            "total_enrolled": enrolled_count,
            "display_name": f"{course.course_code if course else ''} - {course.course_name if course else ''} (Sec {offering.section})",
        })

    return jsonify({
        "success": True,
        "classes": classes_data,
    }), 200


# ============================================================
# 3. ASSIGNMENTS CRUD
# ============================================================

@faculty_assignments_bp.route("", methods=["GET"])
@faculty_required
def list_assignments():
    """
    List assignments for this faculty with optional filtering:
    - offering_id: filter by specific class
    - status: filter by status (ACTIVE, UPCOMING, CLOSED, DRAFT)
    - search: search keyword in title or description
    """
    faculty, user, is_admin = get_current_faculty_and_user()
    if not faculty and not is_admin:
        return jsonify({"success": False, "message": "Faculty profile not found"}), 404

    offering_ids = get_faculty_offering_ids(faculty.faculty_id)
    if not offering_ids:
        return jsonify({"success": True, "assignments": []}), 200

    query = CourseAssignment.query.filter(CourseAssignment.offering_id.in_(offering_ids))

    # Offering filter
    offering_filter = request.args.get("offering_id")
    if offering_filter and offering_filter != "all":
        try:
            off_id = int(offering_filter)
            query = query.filter(CourseAssignment.offering_id == off_id)
        except ValueError:
            pass

    # Status filter
    status_filter = request.args.get("status")
    now = datetime.utcnow()
    if status_filter and status_filter.upper() != "ALL":
        status_val = status_filter.upper()
        if status_val == "DRAFT":
            query = query.filter(CourseAssignment.status == "DRAFT")
        elif status_val == "CLOSED":
            query = query.filter(
                (CourseAssignment.status == "CLOSED") | (CourseAssignment.due_date < now)
            )
        elif status_val == "ACTIVE":
            query = query.filter(
                CourseAssignment.status == "PUBLISHED",
                CourseAssignment.due_date >= now,
            )
        elif status_val == "UPCOMING":
            # Due in more than 7 days
            query = query.filter(
                CourseAssignment.status == "PUBLISHED",
                CourseAssignment.due_date > now,
            )
        else:
            query = query.filter(CourseAssignment.status == status_val)

    # Search filter
    search = request.args.get("search", "").strip()
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (CourseAssignment.title.ilike(search_pattern))
            | (CourseAssignment.description.ilike(search_pattern))
            | (CourseAssignment.assignment_type.ilike(search_pattern))
        )

    # Order by due_date ascending, then created_at desc
    assignments = (
        query.options(joinedload(CourseAssignment.offering).joinedload(CourseOffering.course))
        .order_by(CourseAssignment.due_date.asc())
        .all()
    )

    result = []
    for item in assignments:
        offering = item.offering
        course = offering.course if offering else None

        enrolled_count = Enrollment.query.filter_by(
            offering_id=item.offering_id,
            status="ACTIVE",
        ).count()

        submissions_count = AssignmentSubmission.query.filter_by(
            assignment_id=item.assignment_id,
        ).count()

        reviewed_count = AssignmentSubmission.query.filter_by(
            assignment_id=item.assignment_id,
            review_status="REVIEWED",
        ).count()

        rate = round((submissions_count / enrolled_count * 100), 1) if enrolled_count > 0 else 0
        computed_status, time_label = calculate_due_status(item.due_date)

        # Respect draft and closed overrides
        effective_status = computed_status
        if item.status == "DRAFT":
            effective_status = "Draft"
        elif item.status == "CLOSED":
            effective_status = "Closed"

        data = item.to_dict()
        data.update({
            "course_code": course.course_code if course else "",
            "course_name": course.course_name if course else "",
            "section": offering.section if offering else "",
            "semester": offering.semester if offering else None,
            "total_enrolled": enrolled_count,
            "submissions_count": submissions_count,
            "reviewed_count": reviewed_count,
            "pending_count": max(0, submissions_count - reviewed_count),
            "submission_rate": rate,
            "effective_status": effective_status,
            "time_label": time_label,
            "formatted_due_date": item.due_date.strftime("%b %d, %Y") if item.due_date else "",
        })
        result.append(data)

    return jsonify({"success": True, "assignments": result}), 200


@faculty_assignments_bp.route("", methods=["POST"])
@faculty_required
def create_assignment():
    """Creates a new assignment with optional attachment file upload."""
    faculty, user, is_admin = get_current_faculty_and_user()
    if not faculty and not is_admin:
        return jsonify({"success": False, "message": "Faculty profile not found"}), 404

    # Extract parameters (supports multipart/form-data and json)
    if request.is_json:
        data = request.get_json() or {}
        uploaded_file = None
    else:
        data = request.form.to_dict()
        uploaded_file = request.files.get("file") or request.files.get("attachment")

    offering_id_raw = data.get("offering_id")
    title = (data.get("title") or "").strip()
    due_date_raw = data.get("due_date")

    if not offering_id_raw:
        return jsonify({"success": False, "message": "Class (course offering) is required"}), 400
    if not title:
        return jsonify({"success": False, "message": "Assignment title is required"}), 400
    if not due_date_raw:
        return jsonify({"success": False, "message": "Due date is required"}), 400

    try:
        offering_id = int(offering_id_raw)
    except ValueError:
        return jsonify({"success": False, "message": "Invalid offering ID"}), 400

    if not is_faculty_authorized_for_offering(faculty.faculty_id, offering_id, is_admin):
        return jsonify({"success": False, "message": "Not authorized for this course offering"}), 403

    parsed_due_date = parse_date_string(due_date_raw)
    if not parsed_due_date:
        return jsonify({"success": False, "message": "Invalid due date format"}), 400

    description = (data.get("description") or "").strip()
    assignment_type = data.get("assignment_type") or "File Upload"
    submission_type = data.get("submission_type") or "FILE_UPLOAD"
    allowed_file_types = data.get("allowed_file_types") or "pdf,doc,docx,zip"
    allow_late_submission = str(data.get("allow_late_submission", "")).lower() in ("true", "1", "yes")
    status = data.get("status") or "PUBLISHED"

    try:
        maximum_marks = float(data.get("maximum_marks") or 100.0)
    except (ValueError, TypeError):
        maximum_marks = 100.0

    try:
        maximum_file_size_mb = int(data.get("maximum_file_size_mb") or 10)
    except (ValueError, TypeError):
        maximum_file_size_mb = 10

    attachment_path = None
    attachment_name = None

    if uploaded_file and uploaded_file.filename:
        original_name = secure_filename(uploaded_file.filename)
        if not original_name:
            original_name = f"attachment_{uuid.uuid4().hex[:8]}"
        attachment_name = uploaded_file.filename
        unique_prefix = f"asgn_{int(datetime.utcnow().timestamp())}_{uuid.uuid4().hex[:6]}"
        saved_filename = f"{unique_prefix}_{original_name}"
        full_dest = os.path.join(ASSIGNMENTS_DIR, saved_filename)
        uploaded_file.save(full_dest)
        attachment_path = full_dest

    assignment = CourseAssignment(
        offering_id=offering_id,
        faculty_id=faculty.faculty_id,
        title=title,
        description=description,
        assignment_type=assignment_type,
        attachment_path=attachment_path,
        attachment_name=attachment_name,
        maximum_marks=maximum_marks,
        submission_type=submission_type,
        allowed_file_types=allowed_file_types,
        maximum_file_size_mb=maximum_file_size_mb,
        due_date=parsed_due_date,
        allow_late_submission=allow_late_submission,
        status=status,
    )

    db.session.add(assignment)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Assignment created successfully",
        "assignment": assignment.to_dict(),
    }), 201


@faculty_assignments_bp.route("/<int:assignment_id>", methods=["GET"])
@faculty_required
def get_assignment_detail(assignment_id: int):
    """Retrieves full details of a single assignment."""
    faculty, user, is_admin = get_current_faculty_and_user()
    assignment = db.session.get(CourseAssignment, assignment_id)
    if not assignment:
        return jsonify({"success": False, "message": "Assignment not found"}), 404

    if not is_faculty_authorized_for_offering(faculty.faculty_id, assignment.offering_id, is_admin):
        return jsonify({"success": False, "message": "Not authorized to view this assignment"}), 403

    offering = assignment.offering
    course = offering.course if offering else None
    enrolled_count = Enrollment.query.filter_by(offering_id=assignment.offering_id, status="ACTIVE").count()
    submissions_count = AssignmentSubmission.query.filter_by(assignment_id=assignment.assignment_id).count()
    reviewed_count = AssignmentSubmission.query.filter_by(assignment_id=assignment.assignment_id, review_status="REVIEWED").count()

    computed_status, time_label = calculate_due_status(assignment.due_date)

    data = assignment.to_dict()
    data.update({
        "course_code": course.course_code if course else "",
        "course_name": course.course_name if course else "",
        "section": offering.section if offering else "",
        "semester": offering.semester if offering else None,
        "total_enrolled": enrolled_count,
        "submissions_count": submissions_count,
        "reviewed_count": reviewed_count,
        "pending_count": max(0, submissions_count - reviewed_count),
        "submission_rate": round((submissions_count / enrolled_count * 100), 1) if enrolled_count > 0 else 0,
        "effective_status": computed_status if assignment.status == "PUBLISHED" else assignment.status.capitalize(),
        "time_label": time_label,
        "formatted_due_date": assignment.due_date.strftime("%b %d, %Y %I:%M %p") if assignment.due_date else "",
    })

    return jsonify({"success": True, "assignment": data}), 200


@faculty_assignments_bp.route("/<int:assignment_id>", methods=["PUT", "PATCH"])
@faculty_required
def update_assignment(assignment_id: int):
    """Updates assignment details and optionally replaces attachment."""
    faculty, user, is_admin = get_current_faculty_and_user()
    assignment = db.session.get(CourseAssignment, assignment_id)
    if not assignment:
        return jsonify({"success": False, "message": "Assignment not found"}), 404

    if not is_faculty_authorized_for_offering(faculty.faculty_id, assignment.offering_id, is_admin):
        return jsonify({"success": False, "message": "Not authorized to modify this assignment"}), 403

    if request.is_json:
        data = request.get_json() or {}
        uploaded_file = None
    else:
        data = request.form.to_dict()
        uploaded_file = request.files.get("file") or request.files.get("attachment")

    if "title" in data and data["title"].strip():
        assignment.title = data["title"].strip()
    if "description" in data:
        assignment.description = data["description"].strip()
    if "assignment_type" in data:
        assignment.assignment_type = data["assignment_type"]
    if "submission_type" in data:
        assignment.submission_type = data["submission_type"]
    if "allowed_file_types" in data:
        assignment.allowed_file_types = data["allowed_file_types"]
    if "status" in data:
        assignment.status = data["status"]

    if "maximum_marks" in data:
        try:
            assignment.maximum_marks = float(data["maximum_marks"])
        except (ValueError, TypeError):
            pass

    if "maximum_file_size_mb" in data:
        try:
            assignment.maximum_file_size_mb = int(data["maximum_file_size_mb"])
        except (ValueError, TypeError):
            pass

    if "allow_late_submission" in data:
        assignment.allow_late_submission = str(data["allow_late_submission"]).lower() in ("true", "1", "yes")

    if "due_date" in data and data["due_date"]:
        parsed_due = parse_date_string(data["due_date"])
        if parsed_due:
            assignment.due_date = parsed_due

    # Optional file attachment replacement
    if uploaded_file and uploaded_file.filename:
        # Remove old attachment if exists
        if assignment.attachment_path and os.path.exists(assignment.attachment_path):
            try:
                os.remove(assignment.attachment_path)
            except OSError:
                pass

        original_name = secure_filename(uploaded_file.filename) or f"attachment_{uuid.uuid4().hex[:8]}"
        saved_filename = f"asgn_{int(datetime.utcnow().timestamp())}_{uuid.uuid4().hex[:6]}_{original_name}"
        full_dest = os.path.join(ASSIGNMENTS_DIR, saved_filename)
        uploaded_file.save(full_dest)
        assignment.attachment_path = full_dest
        assignment.attachment_name = uploaded_file.filename

    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Assignment updated successfully",
        "assignment": assignment.to_dict(),
    }), 200


@faculty_assignments_bp.route("/<int:assignment_id>", methods=["DELETE"])
@faculty_required
def delete_assignment(assignment_id: int):
    """Deletes an assignment along with attachments and submissions."""
    faculty, user, is_admin = get_current_faculty_and_user()
    assignment = db.session.get(CourseAssignment, assignment_id)
    if not assignment:
        return jsonify({"success": False, "message": "Assignment not found"}), 404

    if not is_faculty_authorized_for_offering(faculty.faculty_id, assignment.offering_id, is_admin):
        return jsonify({"success": False, "message": "Not authorized to delete this assignment"}), 403

    # Clean up attachment file
    if assignment.attachment_path and os.path.exists(assignment.attachment_path):
        try:
            os.remove(assignment.attachment_path)
        except OSError:
            pass

    # Clean up submission files
    submissions = AssignmentSubmission.query.filter_by(assignment_id=assignment.assignment_id).all()
    for sub in submissions:
        if sub.file_path and os.path.exists(sub.file_path):
            try:
                os.remove(sub.file_path)
            except OSError:
                pass

    db.session.delete(assignment)
    db.session.commit()

    return jsonify({"success": True, "message": "Assignment deleted successfully"}), 200


@faculty_assignments_bp.route("/<int:assignment_id>/status", methods=["PATCH"])
@faculty_required
def toggle_assignment_status(assignment_id: int):
    """Toggles assignment status (e.g. PUBLISHED, CLOSED, DRAFT)."""
    faculty, user, is_admin = get_current_faculty_and_user()
    assignment = db.session.get(CourseAssignment, assignment_id)
    if not assignment:
        return jsonify({"success": False, "message": "Assignment not found"}), 404

    if not is_faculty_authorized_for_offering(faculty.faculty_id, assignment.offering_id, is_admin):
        return jsonify({"success": False, "message": "Not authorized"}), 403

    data = request.get_json() or {}
    new_status = data.get("status")
    if not new_status or new_status not in ("PUBLISHED", "CLOSED", "DRAFT"):
        return jsonify({"success": False, "message": "Invalid status value"}), 400

    assignment.status = new_status
    db.session.commit()

    return jsonify({
        "success": True,
        "message": f"Status updated to {new_status}",
        "status": assignment.status,
    }), 200


@faculty_assignments_bp.route("/<int:assignment_id>/download", methods=["GET"])
@faculty_required
def download_assignment_attachment(assignment_id: int):
    """Securely downloads the assignment attachment file."""
    faculty, user, is_admin = get_current_faculty_and_user()
    assignment = db.session.get(CourseAssignment, assignment_id)
    if not assignment:
        return jsonify({"success": False, "message": "Assignment not found"}), 404

    if not is_faculty_authorized_for_offering(faculty.faculty_id, assignment.offering_id, is_admin):
        return jsonify({"success": False, "message": "Not authorized"}), 403

    validated_path = safe_file_path(ASSIGNMENTS_DIR, assignment.attachment_path)
    if not validated_path:
        return jsonify({"success": False, "message": "Attachment file not found on server"}), 404

    download_name = assignment.attachment_name or os.path.basename(validated_path)
    return send_file(validated_path, as_attachment=True, download_name=download_name)


# ============================================================
# 4. SUBMISSIONS & EVALUATION
# ============================================================

@faculty_assignments_bp.route("/<int:assignment_id>/submissions", methods=["GET"])
@faculty_required
def get_assignment_submissions(assignment_id: int):
    """
    Returns full student submission status roster for an assignment:
    - Lists all actively enrolled students in the offering
    - Shows submission details if submitted, or 'Not Submitted'
    """
    faculty, user, is_admin = get_current_faculty_and_user()
    assignment = db.session.get(CourseAssignment, assignment_id)
    if not assignment:
        return jsonify({"success": False, "message": "Assignment not found"}), 404

    if not is_faculty_authorized_for_offering(faculty.faculty_id, assignment.offering_id, is_admin):
        return jsonify({"success": False, "message": "Not authorized"}), 403

    # Fetch active enrollments
    enrollments = (
        Enrollment.query.filter_by(offering_id=assignment.offering_id, status="ACTIVE")
        .options(joinedload(Enrollment.student).joinedload(Student.user))
        .all()
    )

    # Fetch submissions map
    submissions = AssignmentSubmission.query.filter_by(assignment_id=assignment.assignment_id).all()
    sub_map = {s.student_id: s for s in submissions}

    roster = []
    for enr in enrollments:
        student = enr.student
        if not student:
            continue
        user_info = student.user
        sub = sub_map.get(student.student_id)

        student_name = user_info.name if user_info else f"Student #{student.student_id}"
        email = user_info.email if user_info else ""

        entry = {
            "student_id": student.student_id,
            "roll_number": student.enrollment_no,
            "name": student_name,
            "email": email,
            "submission_id": sub.submission_id if sub else None,
            "submitted": bool(sub),
            "submitted_at": sub.submitted_at.isoformat() if sub else None,
            "is_late": sub.is_late if sub else False,
            "has_file": bool(sub.file_path) if sub else False,
            "file_name": sub.file_name if sub else None,
            "file_size_bytes": sub.file_size_bytes if sub else None,
            "submission_text": sub.submission_text if sub else "",
            "marks_obtained": float(sub.marks_obtained) if (sub and sub.marks_obtained is not None) else None,
            "maximum_marks": float(assignment.maximum_marks),
            "feedback": sub.feedback if sub else "",
            "review_status": sub.review_status if sub else "NOT_SUBMITTED",
            "reviewed_at": sub.reviewed_at.isoformat() if (sub and sub.reviewed_at) else None,
        }
        roster.append(entry)

    # Sort roster by roll number
    roster.sort(key=lambda x: x["roll_number"] or "")

    return jsonify({
        "success": True,
        "assignment": assignment.to_dict(),
        "total_enrolled": len(enrollments),
        "total_submitted": len(submissions),
        "total_reviewed": sum(1 for s in submissions if s.review_status == "REVIEWED"),
        "submissions": roster,
    }), 200


@faculty_assignments_bp.route("/submissions/<int:submission_id>/evaluate", methods=["POST"])
@faculty_required
def evaluate_submission(submission_id: int):
    """Assigns marks and feedback to a student submission."""
    faculty, user, is_admin = get_current_faculty_and_user()
    submission = db.session.get(AssignmentSubmission, submission_id)
    if not submission:
        return jsonify({"success": False, "message": "Submission not found"}), 404

    assignment = submission.assignment
    if not assignment or not is_faculty_authorized_for_offering(faculty.faculty_id, assignment.offering_id, is_admin):
        return jsonify({"success": False, "message": "Not authorized to evaluate this submission"}), 403

    data = request.get_json() or {}
    marks_raw = data.get("marks_obtained")
    feedback = (data.get("feedback") or "").strip()

    if marks_raw is None:
        return jsonify({"success": False, "message": "Marks obtained is required"}), 400

    try:
        marks = float(marks_raw)
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Invalid marks value"}), 400

    max_marks = float(assignment.maximum_marks)
    if marks < 0 or marks > max_marks:
        return jsonify({
            "success": False,
            "message": f"Marks must be between 0 and maximum marks ({max_marks})",
        }), 400

    submission.marks_obtained = marks
    submission.feedback = feedback
    submission.review_status = "REVIEWED"
    submission.reviewed_at = datetime.utcnow()
    submission.reviewed_by = user.user_id if user else None

    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Submission evaluated successfully",
        "submission": submission.to_dict(),
    }), 200


@faculty_assignments_bp.route("/submissions/<int:submission_id>/download", methods=["GET"])
@faculty_required
def download_submission_file(submission_id: int):
    """Securely downloads a student's submitted file."""
    faculty, user, is_admin = get_current_faculty_and_user()
    submission = db.session.get(AssignmentSubmission, submission_id)
    if not submission:
        return jsonify({"success": False, "message": "Submission not found"}), 404

    assignment = submission.assignment
    if not assignment or not is_faculty_authorized_for_offering(faculty.faculty_id, assignment.offering_id, is_admin):
        return jsonify({"success": False, "message": "Not authorized"}), 403

    validated_path = safe_file_path(SUBMISSIONS_DIR, submission.file_path)
    if not validated_path:
        return jsonify({"success": False, "message": "Submission file not found on server"}), 404

    download_name = submission.file_name or os.path.basename(validated_path)
    return send_file(validated_path, as_attachment=True, download_name=download_name)


# ============================================================
# 5. STUDY MATERIALS / NOTES CRUD
# ============================================================

@faculty_assignments_bp.route("/notes", methods=["GET"])
@faculty_required
def list_notes():
    """Lists study materials / notes for this faculty with filtering."""
    faculty, user, is_admin = get_current_faculty_and_user()
    if not faculty and not is_admin:
        return jsonify({"success": False, "message": "Faculty profile not found"}), 404

    offering_ids = get_faculty_offering_ids(faculty.faculty_id)
    if not offering_ids:
        return jsonify({"success": True, "notes": []}), 200

    query = StudyMaterial.query.filter(StudyMaterial.offering_id.in_(offering_ids))

    offering_filter = request.args.get("offering_id")
    if offering_filter and offering_filter != "all":
        try:
            off_id = int(offering_filter)
            query = query.filter(StudyMaterial.offering_id == off_id)
        except ValueError:
            pass

    category_filter = request.args.get("category")
    if category_filter and category_filter.upper() != "ALL":
        query = query.filter(StudyMaterial.category == category_filter.upper())

    search = request.args.get("search", "").strip()
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (StudyMaterial.title.ilike(search_pattern))
            | (StudyMaterial.description.ilike(search_pattern))
            | (StudyMaterial.file_name.ilike(search_pattern))
        )

    notes = (
        query.options(joinedload(StudyMaterial.offering).joinedload(CourseOffering.course))
        .order_by(StudyMaterial.created_at.desc())
        .all()
    )

    result = []
    for item in notes:
        offering = item.offering
        course = offering.course if offering else None
        data = item.to_dict()
        data.update({
            "course_code": course.course_code if course else "",
            "course_name": course.course_name if course else "",
            "section": offering.section if offering else "",
            "formatted_date": item.created_at.strftime("%b %d, %Y") if item.created_at else "",
        })
        result.append(data)

    return jsonify({"success": True, "notes": result}), 200


@faculty_assignments_bp.route("/notes", methods=["POST"])
@faculty_required
def upload_note():
    """Uploads a study material / lecture note document."""
    faculty, user, is_admin = get_current_faculty_and_user()
    if not faculty and not is_admin:
        return jsonify({"success": False, "message": "Faculty profile not found"}), 404

    data = request.form.to_dict()
    uploaded_file = request.files.get("file")

    offering_id_raw = data.get("offering_id")
    title = (data.get("title") or "").strip()

    if not offering_id_raw:
        return jsonify({"success": False, "message": "Course offering is required"}), 400
    if not title:
        return jsonify({"success": False, "message": "Note title is required"}), 400
    if not uploaded_file or not uploaded_file.filename:
        return jsonify({"success": False, "message": "File is required"}), 400

    try:
        offering_id = int(offering_id_raw)
    except ValueError:
        return jsonify({"success": False, "message": "Invalid offering ID"}), 400

    if not is_faculty_authorized_for_offering(faculty.faculty_id, offering_id, is_admin):
        return jsonify({"success": False, "message": "Not authorized for this course offering"}), 403

    description = (data.get("description") or "").strip()
    category = data.get("category") or "LECTURE_NOTES"
    visibility = data.get("visibility") or "PUBLISHED"

    # Save file
    original_name = secure_filename(uploaded_file.filename) or f"note_{uuid.uuid4().hex[:8]}"
    file_ext = original_name.rsplit(".", 1)[-1].lower() if "." in original_name else "bin"
    saved_filename = f"note_{int(datetime.utcnow().timestamp())}_{uuid.uuid4().hex[:6]}_{original_name}"
    full_dest = os.path.join(MATERIALS_DIR, saved_filename)
    uploaded_file.save(full_dest)

    file_size = os.path.getsize(full_dest) if os.path.exists(full_dest) else 0

    note = StudyMaterial(
        offering_id=offering_id,
        faculty_id=faculty.faculty_id,
        title=title,
        description=description,
        category=category,
        file_path=full_dest,
        file_name=uploaded_file.filename,
        file_type=file_ext,
        file_size_bytes=file_size,
        visibility=visibility,
    )

    db.session.add(note)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Study material uploaded successfully",
        "note": note.to_dict(),
    }), 201


@faculty_assignments_bp.route("/notes/<int:material_id>", methods=["PUT", "PATCH"])
@faculty_required
def update_note(material_id: int):
    """Updates study material metadata."""
    faculty, user, is_admin = get_current_faculty_and_user()
    note = db.session.get(StudyMaterial, material_id)
    if not note:
        return jsonify({"success": False, "message": "Note not found"}), 404

    if not is_faculty_authorized_for_offering(faculty.faculty_id, note.offering_id, is_admin):
        return jsonify({"success": False, "message": "Not authorized"}), 403

    data = request.form.to_dict() if request.form else (request.get_json() or {})

    if "title" in data and data["title"].strip():
        note.title = data["title"].strip()
    if "description" in data:
        note.description = data["description"].strip()
    if "category" in data:
        note.category = data["category"]
    if "visibility" in data:
        note.visibility = data["visibility"]

    # Optional file replacement
    uploaded_file = request.files.get("file") if request.files else None
    if uploaded_file and uploaded_file.filename:
        if note.file_path and os.path.exists(note.file_path):
            try:
                os.remove(note.file_path)
            except OSError:
                pass
        original_name = secure_filename(uploaded_file.filename) or f"note_{uuid.uuid4().hex[:8]}"
        file_ext = original_name.rsplit(".", 1)[-1].lower() if "." in original_name else "bin"
        saved_filename = f"note_{int(datetime.utcnow().timestamp())}_{uuid.uuid4().hex[:6]}_{original_name}"
        full_dest = os.path.join(MATERIALS_DIR, saved_filename)
        uploaded_file.save(full_dest)

        note.file_path = full_dest
        note.file_name = uploaded_file.filename
        note.file_type = file_ext
        note.file_size_bytes = os.path.getsize(full_dest)

    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Note updated successfully",
        "note": note.to_dict(),
    }), 200


@faculty_assignments_bp.route("/notes/<int:material_id>", methods=["DELETE"])
@faculty_required
def delete_note(material_id: int):
    """Deletes study material and associated file."""
    faculty, user, is_admin = get_current_faculty_and_user()
    note = db.session.get(StudyMaterial, material_id)
    if not note:
        return jsonify({"success": False, "message": "Note not found"}), 404

    if not is_faculty_authorized_for_offering(faculty.faculty_id, note.offering_id, is_admin):
        return jsonify({"success": False, "message": "Not authorized"}), 403

    if note.file_path and os.path.exists(note.file_path):
        try:
            os.remove(note.file_path)
        except OSError:
            pass

    db.session.delete(note)
    db.session.commit()

    return jsonify({"success": True, "message": "Study material deleted successfully"}), 200


@faculty_assignments_bp.route("/notes/<int:material_id>/download", methods=["GET"])
@faculty_required
def download_note(material_id: int):
    """Securely downloads study material file."""
    faculty, user, is_admin = get_current_faculty_and_user()
    note = db.session.get(StudyMaterial, material_id)
    if not note:
        return jsonify({"success": False, "message": "Note not found"}), 404

    if not is_faculty_authorized_for_offering(faculty.faculty_id, note.offering_id, is_admin):
        return jsonify({"success": False, "message": "Not authorized"}), 403

    validated_path = safe_file_path(MATERIALS_DIR, note.file_path)
    if not validated_path:
        return jsonify({"success": False, "message": "File not found on server"}), 404

    download_name = note.file_name or os.path.basename(validated_path)
    return send_file(validated_path, as_attachment=True, download_name=download_name)


# ============================================================
# 6. CLASS OVERVIEW & RECENT UPLOADS
# ============================================================

@faculty_assignments_bp.route("/class-overview", methods=["GET"])
@faculty_required
def get_class_overview():
    """Returns class-wise summary cards with counts and submission statistics."""
    faculty, user, is_admin = get_current_faculty_and_user()
    if not faculty and not is_admin:
        return jsonify({"success": False, "message": "Faculty profile not found"}), 404

    offerings = (
        CourseOffering.query.filter_by(faculty_id=faculty.faculty_id)
        .options(joinedload(CourseOffering.course).joinedload(Course.department))
        .all()
    )

    overview = []
    for offering in offerings:
        course = offering.course
        enrolled_count = Enrollment.query.filter_by(offering_id=offering.offering_id, status="ACTIVE").count()
        assignments_count = CourseAssignment.query.filter_by(offering_id=offering.offering_id).count()
        notes_count = StudyMaterial.query.filter_by(offering_id=offering.offering_id).count()

        submissions_count = (
            AssignmentSubmission.query.join(CourseAssignment)
            .filter(CourseAssignment.offering_id == offering.offering_id)
            .count()
        )

        expected_submissions = enrolled_count * assignments_count
        rate = round((submissions_count / expected_submissions * 100), 1) if expected_submissions > 0 else 0

        overview.append({
            "offering_id": offering.offering_id,
            "course_id": offering.course_id,
            "course_code": course.course_code if course else "",
            "course_name": course.course_name if course else "",
            "department_name": course.department.department_name if course and course.department else "",
            "section": offering.section,
            "semester": offering.semester,
            "academic_year": offering.academic_year,
            "total_enrolled": enrolled_count,
            "assignments_count": assignments_count,
            "notes_count": notes_count,
            "submissions_count": submissions_count,
            "expected_submissions": expected_submissions,
            "completion_rate": rate,
        })

    return jsonify({"success": True, "classes": overview}), 200


@faculty_assignments_bp.route("/recent-uploads", methods=["GET"])
@faculty_required
def get_recent_uploads():
    """Returns combined recent uploads of assignments and notes for the sidebar card."""
    faculty, user, is_admin = get_current_faculty_and_user()
    if not faculty and not is_admin:
        return jsonify({"success": False, "message": "Faculty profile not found"}), 404

    offering_ids = get_faculty_offering_ids(faculty.faculty_id)
    if not offering_ids:
        return jsonify({"success": True, "recent_uploads": []}), 200

    assignments = (
        CourseAssignment.query.filter(CourseAssignment.offering_id.in_(offering_ids))
        .options(joinedload(CourseAssignment.offering).joinedload(CourseOffering.course))
        .order_by(CourseAssignment.created_at.desc())
        .limit(5)
        .all()
    )

    notes = (
        StudyMaterial.query.filter(StudyMaterial.offering_id.in_(offering_ids))
        .options(joinedload(StudyMaterial.offering).joinedload(CourseOffering.course))
        .order_by(StudyMaterial.created_at.desc())
        .limit(5)
        .all()
    )

    recent = []
    for a in assignments:
        course = a.offering.course if a.offering else None
        enrolled = Enrollment.query.filter_by(offering_id=a.offering_id, status="ACTIVE").count()
        recent.append({
            "id": a.assignment_id,
            "type": "ASSIGNMENT",
            "title": a.title,
            "course_code": course.course_code if course else "",
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "date_label": a.created_at.strftime("%b %d, %Y") if a.created_at else "",
            "file_type": "pdf" if (a.attachment_name and a.attachment_name.endswith(".pdf")) else "assignment",
            "extra_info": f"{enrolled} students",
        })

    for n in notes:
        course = n.offering.course if n.offering else None
        recent.append({
            "id": n.material_id,
            "type": "NOTE",
            "title": n.title,
            "course_code": course.course_code if course else "",
            "created_at": n.created_at.isoformat() if n.created_at else None,
            "date_label": n.created_at.strftime("%b %d, %Y") if n.created_at else "",
            "file_type": n.file_type or "pdf",
            "extra_info": n.formatted_file_size(),
        })

    recent.sort(key=lambda x: x["created_at"] or "", reverse=True)

    return jsonify({"success": True, "recent_uploads": recent[:6]}), 200
