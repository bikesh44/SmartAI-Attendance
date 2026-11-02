"""
Student Assignments & Notes Management Routes
SAMS-FR (Smart Attendance Management System)

Provides secure student endpoints for:
- Summary metrics (Total Assignments, Pending, Submitted, Notes Available)
- Enrolled classes / subjects list for dropdown filters
- Published assignments across enrolled courses
- Assignment details & attachment download
- Assignment submission (File Upload, Text, or Both) with deadline & late checks
- Student's own submission history & file download
- Published notes / study materials access & download
- Upcoming deadlines in chronological order
- Evaluated results & faculty feedback
"""

from datetime import datetime, date
import os
import re
import uuid
from typing import Optional, Tuple, List

from flask import Blueprint, jsonify, request, send_file
from flask_jwt_extended import get_jwt, get_jwt_identity, verify_jwt_in_request
from sqlalchemy.orm import joinedload
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models.assignment import CourseAssignment
from app.models.study_material import StudyMaterial
from app.models.assignment_submission import AssignmentSubmission
from app.models.course import Course
from app.models.course_offering import CourseOffering
from app.models.department import Department
from app.models.enrollment import Enrollment
from app.models.faculty import Faculty
from app.models.student import Student
from app.models.user import User
from app.utils.auth import student_required

student_assignments_bp = Blueprint(
    "student_assignments",
    __name__,
    url_prefix="/api/student/assignments",
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

def get_current_student_and_user() -> Tuple[Optional[Student], Optional[User]]:
    """Retrieves current student and user records based on JWT identity."""
    verify_jwt_in_request()
    identity = get_jwt_identity()
    try:
        user_id = int(identity) if identity is not None else None
    except (ValueError, TypeError):
        return None, None

    if not user_id:
        return None, None

    user = db.session.get(User, user_id)
    student = Student.query.filter_by(user_id=user_id).first()
    return student, user


def get_student_active_offering_ids(student_id: int) -> List[int]:
    """Returns list of offering IDs where the student has an ACTIVE enrollment."""
    enrollments = Enrollment.query.filter_by(
        student_id=student_id,
        status="ACTIVE",
    ).all()
    return [e.offering_id for e in enrollments]


def is_student_enrolled_in_offering(student_id: int, offering_id: int) -> bool:
    """Checks if student is actively enrolled in the course offering."""
    enr = Enrollment.query.filter_by(
        student_id=student_id,
        offering_id=offering_id,
        status="ACTIVE",
    ).first()
    return enr is not None


def safe_file_path(base_dir: str, file_path: str) -> Optional[str]:
    """Validates that file_path resides strictly within base_dir and exists on disk."""
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


def calculate_due_status(due_date: datetime) -> Tuple[str, str, bool]:
    """
    Returns (status_label, relative_text, is_overdue).
    """
    if not due_date:
        return "Active", "", False

    now = datetime.utcnow()
    diff = due_date - now

    if diff.total_seconds() < 0:
        return "Overdue", "Overdue", True

    days = diff.days
    hours = int(diff.seconds / 3600)

    if days == 0:
        if hours <= 1:
            return "Due soon", "Due soon", False
        return "Due today", f"{hours} hours left", False
    elif days == 1:
        return "1 day left", "1 day left", False
    elif days <= 7:
        return f"{days} days left", f"{days} days left", False
    else:
        return f"{days} days left", f"{days} days left", False


# ============================================================
# 1. SUMMARY METRICS
# ============================================================

@student_assignments_bp.route("/summary", methods=["GET"])
@student_required
def get_student_assignment_summary():
    """
    Returns 4 dynamic summary card metrics for the authenticated student:
    1. total_assignments: Published assignments across enrolled courses
    2. pending_assignments: Published assignments not submitted and due date not passed
    3. submitted_assignments: Total assignments submitted by student
    4. notes_available: Published study materials across enrolled courses
    """
    student, user = get_current_student_and_user()
    if not student:
        return jsonify({"success": False, "message": "Student profile not found"}), 404

    offering_ids = get_student_active_offering_ids(student.student_id)
    if not offering_ids:
        return jsonify({
            "success": True,
            "summary": {
                "total_assignments": 0,
                "pending_assignments": 0,
                "submitted_assignments": 0,
                "notes_available": 0,
                "enrolled_classes_count": 0,
            },
        }), 200

    now = datetime.utcnow()

    # Total published assignments
    total_assignments_query = CourseAssignment.query.filter(
        CourseAssignment.offering_id.in_(offering_ids),
        CourseAssignment.status == "PUBLISHED",
    )
    total_assignments = total_assignments_query.count()

    # Total published notes
    total_notes = StudyMaterial.query.filter(
        StudyMaterial.offering_id.in_(offering_ids),
        StudyMaterial.visibility == "PUBLISHED",
    ).count()

    # Submissions made by this student for enrolled assignments
    student_submissions = AssignmentSubmission.query.join(
        CourseAssignment,
        AssignmentSubmission.assignment_id == CourseAssignment.assignment_id,
    ).filter(
        AssignmentSubmission.student_id == student.student_id,
        CourseAssignment.offering_id.in_(offering_ids),
        CourseAssignment.status == "PUBLISHED",
    ).all()

    submitted_count = len(student_submissions)
    submitted_assignment_ids = {s.assignment_id for s in student_submissions}

    # Pending assignments: published, not submitted, and due date >= now (or late allowed)
    all_published_assignments = total_assignments_query.all()
    pending_count = 0
    for a in all_published_assignments:
        if a.assignment_id not in submitted_assignment_ids:
            # If not yet submitted and not hard-closed
            if a.due_date >= now or a.allow_late_submission:
                pending_count += 1

    return jsonify({
        "success": True,
        "summary": {
            "total_assignments": total_assignments,
            "pending_assignments": pending_count,
            "submitted_assignments": submitted_count,
            "notes_available": total_notes,
            "enrolled_classes_count": len(offering_ids),
        },
    }), 200


# ============================================================
# 2. ENROLLED CLASSES FOR DROPDOWN FILTERS
# ============================================================

@student_assignments_bp.route("/enrolled-classes", methods=["GET"])
@student_required
def get_student_enrolled_classes():
    """Returns active enrolled classes/courses for filter dropdowns."""
    student, user = get_current_student_and_user()
    if not student:
        return jsonify({"success": False, "message": "Student profile not found"}), 404

    enrollments = (
        Enrollment.query.filter_by(student_id=student.student_id, status="ACTIVE")
        .options(
            joinedload(Enrollment.offering)
            .joinedload(CourseOffering.course)
            .joinedload(Course.department),
            joinedload(Enrollment.offering)
            .joinedload(CourseOffering.faculty)
            .joinedload(Faculty.user),
        )
        .all()
    )

    classes_data = []
    for enr in enrollments:
        offering = enr.offering
        if not offering:
            continue
        course = offering.course
        faculty = offering.faculty
        faculty_name = faculty.user.name if faculty and faculty.user else "Faculty"

        classes_data.append({
            "offering_id": offering.offering_id,
            "course_id": offering.course_id,
            "course_code": course.course_code if course else "",
            "course_name": course.course_name if course else "",
            "department_name": course.department.department_name if course and course.department else "",
            "section": offering.section,
            "semester": offering.semester,
            "academic_year": offering.academic_year,
            "faculty_name": faculty_name,
            "label": f"{course.course_code if course else ''} - {course.course_name if course else ''} (Sec {offering.section})",
        })

    return jsonify({"success": True, "classes": classes_data}), 200


# ============================================================
# 3. ASSIGNMENTS LISTING & DETAIL
# ============================================================

@student_assignments_bp.route("", methods=["GET"])
@student_required
def list_student_assignments():
    """
    Lists published assignments for courses the student is actively enrolled in:
    - Filters: offering_id, status (ALL, PENDING, SUBMITTED, OVERDUE, GRADED), search
    - Returns assignments enriched with student's own submission status and progress
    """
    student, user = get_current_student_and_user()
    if not student:
        return jsonify({"success": False, "message": "Student profile not found"}), 404

    offering_ids = get_student_active_offering_ids(student.student_id)
    if not offering_ids:
        return jsonify({"success": True, "assignments": []}), 200

    query = CourseAssignment.query.filter(
        CourseAssignment.offering_id.in_(offering_ids),
        CourseAssignment.status == "PUBLISHED",
    )

    # Filter by specific course offering
    offering_filter = request.args.get("offering_id")
    if offering_filter and offering_filter != "all":
        try:
            off_id = int(offering_filter)
            query = query.filter(CourseAssignment.offering_id == off_id)
        except ValueError:
            pass

    # Search keyword
    search = request.args.get("search", "").strip()
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (CourseAssignment.title.ilike(search_pattern))
            | (CourseAssignment.description.ilike(search_pattern))
            | (CourseAssignment.assignment_type.ilike(search_pattern))
        )

    # Sort order
    assignments = (
        query.options(
            joinedload(CourseAssignment.offering)
            .joinedload(CourseOffering.course)
            .joinedload(Course.department),
            joinedload(CourseAssignment.offering)
            .joinedload(CourseOffering.faculty)
            .joinedload(Faculty.user),
        )
        .order_by(CourseAssignment.due_date.asc())
        .all()
    )

    # Query all student's submissions for these assignments
    asgn_ids = [a.assignment_id for a in assignments]
    submissions = (
        AssignmentSubmission.query.filter(
            AssignmentSubmission.assignment_id.in_(asgn_ids),
            AssignmentSubmission.student_id == student.student_id,
        ).all()
        if asgn_ids
        else []
    )
    sub_map = {s.assignment_id: s for s in submissions}

    now = datetime.utcnow()
    status_filter = (request.args.get("status") or "all").lower()

    result = []
    for a in assignments:
        offering = a.offering
        course = offering.course if offering else None
        faculty = offering.faculty if offering else None
        faculty_name = faculty.user.name if faculty and faculty.user else "Faculty"

        sub = sub_map.get(a.assignment_id)
        has_submitted = sub is not None
        time_status, time_label, is_overdue = calculate_due_status(a.due_date)

        # Class-wide stats
        enrolled_count = Enrollment.query.filter_by(
            offering_id=a.offering_id, status="ACTIVE"
        ).count()
        class_submissions_count = AssignmentSubmission.query.filter_by(
            assignment_id=a.assignment_id
        ).count()
        class_submission_rate = (
            round((class_submissions_count / enrolled_count * 100), 1)
            if enrolled_count > 0
            else 0
        )

        # Student status badge calculation
        if has_submitted:
            if sub.review_status == "REVIEWED":
                student_status = "Reviewed"
            elif sub.is_late:
                student_status = "Late Submitted"
            else:
                student_status = "Submitted"
        else:
            if is_overdue:
                if a.allow_late_submission:
                    student_status = "Overdue (Late Allowed)"
                else:
                    student_status = "Overdue"
            else:
                student_status = "Pending"

        # Apply student status filter
        if status_filter != "all":
            if status_filter == "pending" and has_submitted:
                continue
            if status_filter == "submitted" and not has_submitted:
                continue
            if status_filter == "overdue" and (not is_overdue or has_submitted):
                continue
            if status_filter == "graded" and (not sub or sub.review_status != "REVIEWED"):
                continue

        # Can submit flag
        can_submit = (
            not has_submitted
            and (not is_overdue or a.allow_late_submission)
        )

        item_data = a.to_dict()
        item_data.update({
            "course_code": course.course_code if course else "",
            "course_name": course.course_name if course else "",
            "department_name": course.department.department_name if course and course.department else "",
            "section": offering.section if offering else "",
            "semester": offering.semester if offering else None,
            "faculty_name": faculty_name,
            "student_status": student_status,
            "has_submitted": has_submitted,
            "can_submit": can_submit,
            "submission_id": sub.submission_id if sub else None,
            "marks_obtained": float(sub.marks_obtained) if (sub and sub.marks_obtained is not None) else None,
            "feedback": sub.feedback if sub else "",
            "review_status": sub.review_status if sub else "NOT_SUBMITTED",
            "submitted_at": sub.submitted_at.isoformat() if (sub and sub.submitted_at) else None,
            "is_late": sub.is_late if sub else False,
            "has_submitted_file": bool(sub.file_path) if sub else False,
            "submitted_file_name": sub.file_name if sub else None,
            "time_label": time_label,
            "is_overdue": is_overdue,
            "formatted_due_date": a.due_date.strftime("%b %d, %Y") if a.due_date else "",
            "class_submissions_count": class_submissions_count,
            "total_enrolled": enrolled_count,
            "class_submission_rate": class_submission_rate,
        })
        result.append(item_data)

    return jsonify({"success": True, "assignments": result}), 200


@student_assignments_bp.route("/<int:assignment_id>", methods=["GET"])
@student_required
def get_student_assignment_detail(assignment_id: int):
    """
    Retrieves complete assignment details for an enrolled course,
    including student's submission record if submitted.
    """
    student, user = get_current_student_and_user()
    if not student:
        return jsonify({"success": False, "message": "Student profile not found"}), 404

    assignment = db.session.get(CourseAssignment, assignment_id)
    if not assignment or assignment.status != "PUBLISHED":
        return jsonify({"success": False, "message": "Assignment not found or not published"}), 404

    if not is_student_enrolled_in_offering(student.student_id, assignment.offering_id):
        return jsonify({"success": False, "message": "Not authorized to access this assignment"}), 403

    offering = assignment.offering
    course = offering.course if offering else None
    faculty = offering.faculty if offering else None
    faculty_name = faculty.user.name if faculty and faculty.user else "Faculty"

    sub = AssignmentSubmission.query.filter_by(
        assignment_id=assignment.assignment_id,
        student_id=student.student_id,
    ).first()

    now = datetime.utcnow()
    time_status, time_label, is_overdue = calculate_due_status(assignment.due_date)
    has_submitted = sub is not None

    can_submit = (
        not has_submitted
        and (not is_overdue or assignment.allow_late_submission)
    )

    data = assignment.to_dict()
    data.update({
        "course_code": course.course_code if course else "",
        "course_name": course.course_name if course else "",
        "department_name": course.department.department_name if course and course.department else "",
        "section": offering.section if offering else "",
        "semester": offering.semester if offering else None,
        "faculty_name": faculty_name,
        "has_submitted": has_submitted,
        "can_submit": can_submit,
        "submission": sub.to_dict() if sub else None,
        "time_label": time_label,
        "is_overdue": is_overdue,
        "formatted_due_date": assignment.due_date.strftime("%b %d, %Y %I:%M %p") if assignment.due_date else "",
    })

    return jsonify({"success": True, "assignment": data}), 200


@student_assignments_bp.route("/<int:assignment_id>/download-attachment", methods=["GET"])
@student_required
def download_student_assignment_attachment(assignment_id: int):
    """Securely downloads faculty worksheet/attachment for an enrolled assignment."""
    student, user = get_current_student_and_user()
    if not student:
        return jsonify({"success": False, "message": "Student profile not found"}), 404

    assignment = db.session.get(CourseAssignment, assignment_id)
    if not assignment or assignment.status != "PUBLISHED":
        return jsonify({"success": False, "message": "Assignment not found"}), 404

    if not is_student_enrolled_in_offering(student.student_id, assignment.offering_id):
        return jsonify({"success": False, "message": "Not authorized to access this assignment"}), 403

    validated_path = safe_file_path(ASSIGNMENTS_DIR, assignment.attachment_path)
    if not validated_path:
        return jsonify({"success": False, "message": "Attachment file not found on server"}), 404

    download_name = assignment.attachment_name or os.path.basename(validated_path)
    return send_file(validated_path, as_attachment=True, download_name=download_name)


# ============================================================
# 4. SUBMIT ASSIGNMENT WORK
# ============================================================

@student_assignments_bp.route("/<int:assignment_id>/submit", methods=["POST"])
@student_required
def submit_assignment(assignment_id: int):
    """
    Submits student work for an assignment (supports File Upload, Text, or Both):
    - Verifies enrollment
    - Enforces deadline and allow_late_submission flag
    - Validates file type and size against assignment restrictions
    - Prevents duplicate submissions unless resubmission is allowed
    """
    student, user = get_current_student_and_user()
    if not student:
        return jsonify({"success": False, "message": "Student profile not found"}), 404

    assignment = db.session.get(CourseAssignment, assignment_id)
    if not assignment or assignment.status != "PUBLISHED":
        return jsonify({"success": False, "message": "Assignment not found or closed"}), 404

    if not is_student_enrolled_in_offering(student.student_id, assignment.offering_id):
        return jsonify({"success": False, "message": "Not authorized to submit to this course"}), 403

    now = datetime.utcnow()
    is_late = now > assignment.due_date

    # Enforce deadline
    if is_late and not assignment.allow_late_submission:
        return jsonify({
            "success": False,
            "message": "Submission deadline has passed and late submissions are not allowed.",
        }), 400

    # Check existing submission
    existing_sub = AssignmentSubmission.query.filter_by(
        assignment_id=assignment.assignment_id,
        student_id=student.student_id,
    ).first()

    allow_resubmit = request.form.get("resubmit", "").lower() in ("true", "1") or (
        request.is_json and request.get_json().get("resubmit") is True
    )

    if existing_sub and not allow_resubmit:
        return jsonify({
            "success": False,
            "message": "You have already submitted this assignment.",
            "submission_id": existing_sub.submission_id,
        }), 400

    # Extract input (supports multipart and json)
    if request.is_json:
        data = request.get_json() or {}
        uploaded_file = None
        submission_text = (data.get("submission_text") or "").strip()
    else:
        data = request.form.to_dict()
        uploaded_file = request.files.get("file")
        submission_text = (data.get("submission_text") or "").strip()

    sub_type = (assignment.submission_type or "FILE_UPLOAD").upper()

    # Validate based on assignment submission_type
    saved_file_path = None
    saved_file_name = None
    saved_file_size = None

    if sub_type == "FILE_UPLOAD":
        if not uploaded_file or not uploaded_file.filename:
            return jsonify({"success": False, "message": "A file is required for this submission."}), 400

    elif sub_type in ("TEXT_SUBMISSION", "TEXT"):
        if not submission_text:
            return jsonify({"success": False, "message": "Submission text is required."}), 400

    else:  # BOTH
        if not submission_text and (not uploaded_file or not uploaded_file.filename):
            return jsonify({"success": False, "message": "Please provide either text or a file upload."}), 400

    # Process file upload if provided
    if uploaded_file and uploaded_file.filename:
        original_name = secure_filename(uploaded_file.filename)
        if not original_name:
            original_name = f"submission_{uuid.uuid4().hex[:8]}"

        file_ext = original_name.rsplit(".", 1)[-1].lower() if "." in original_name else ""

        # Validate allowed file types
        if assignment.allowed_file_types:
            allowed_list = [
                ext.strip().lower().lstrip(".")
                for ext in assignment.allowed_file_types.split(",")
                if ext.strip()
            ]
            if allowed_list and file_ext not in allowed_list:
                return jsonify({
                    "success": False,
                    "message": f"Unsupported file type (.{file_ext}). Allowed formats: {', '.join(allowed_list)}",
                }), 400

        # Unique destination path
        unique_prefix = f"sub_{student.student_id}_{int(now.timestamp())}_{uuid.uuid4().hex[:6]}"
        saved_file_name = f"{unique_prefix}_{original_name}"
        full_dest = os.path.join(SUBMISSIONS_DIR, saved_file_name)
        uploaded_file.save(full_dest)

        saved_file_size = os.path.getsize(full_dest) if os.path.exists(full_dest) else 0

        # Validate max file size
        max_bytes = (assignment.maximum_file_size_mb or 10) * 1024 * 1024
        if saved_file_size > max_bytes:
            if os.path.exists(full_dest):
                os.remove(full_dest)
            return jsonify({
                "success": False,
                "message": f"File size exceeds maximum allowed limit of {assignment.maximum_file_size_mb} MB.",
            }), 400

        saved_file_path = full_dest
        saved_file_name = uploaded_file.filename

    # Save to database (Update if resubmitting, else Create)
    if existing_sub:
        # Clean up old file if replacing
        if saved_file_path and existing_sub.file_path and os.path.exists(existing_sub.file_path):
            try:
                os.remove(existing_sub.file_path)
            except OSError:
                pass

        if saved_file_path:
            existing_sub.file_path = saved_file_path
            existing_sub.file_name = saved_file_name
            existing_sub.file_size_bytes = saved_file_size

        if submission_text:
            existing_sub.submission_text = submission_text

        existing_sub.submitted_at = now
        existing_sub.is_late = is_late
        existing_sub.review_status = "PENDING"
        existing_sub.marks_obtained = None
        existing_sub.feedback = None
        submission = existing_sub
    else:
        submission = AssignmentSubmission(
            assignment_id=assignment.assignment_id,
            student_id=student.student_id,
            submission_text=submission_text,
            file_path=saved_file_path,
            file_name=saved_file_name,
            file_size_bytes=saved_file_size,
            submitted_at=now,
            is_late=is_late,
            review_status="PENDING",
        )
        db.session.add(submission)

    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Assignment submitted successfully!" if not is_late else "Assignment submitted (marked Late).",
        "submission": submission.to_dict(),
    }), 201


# ============================================================
# 5. MY SUBMISSIONS TAB
# ============================================================

@student_assignments_bp.route("/submissions", methods=["GET"])
@student_required
def get_student_submissions_history():
    """Returns the authenticated student's own submission history."""
    student, user = get_current_student_and_user()
    if not student:
        return jsonify({"success": False, "message": "Student profile not found"}), 404

    query = (
        AssignmentSubmission.query.filter_by(student_id=student.student_id)
        .options(
            joinedload(AssignmentSubmission.assignment)
            .joinedload(CourseAssignment.offering)
            .joinedload(CourseOffering.course),
            joinedload(AssignmentSubmission.assignment)
            .joinedload(CourseAssignment.offering)
            .joinedload(CourseOffering.faculty)
            .joinedload(Faculty.user),
        )
        .order_by(AssignmentSubmission.submitted_at.desc())
    )

    submissions = query.all()
    results = []

    for sub in submissions:
        assignment = sub.assignment
        offering = assignment.offering if assignment else None
        course = offering.course if offering else None
        faculty = offering.faculty if offering else None
        faculty_name = faculty.user.name if faculty and faculty.user else "Faculty"

        data = sub.to_dict()
        data.update({
            "assignment_title": assignment.title if assignment else "Assignment",
            "assignment_type": assignment.assignment_type if assignment else "",
            "maximum_marks": float(assignment.maximum_marks) if assignment else 100.0,
            "course_code": course.course_code if course else "",
            "course_name": course.course_name if course else "",
            "section": offering.section if offering else "",
            "faculty_name": faculty_name,
            "due_date": assignment.due_date.isoformat() if assignment and assignment.due_date else None,
            "formatted_submitted_date": sub.submitted_at.strftime("%b %d, %Y %I:%M %p") if sub.submitted_at else "",
        })
        results.append(data)

    return jsonify({"success": True, "submissions": results}), 200


@student_assignments_bp.route("/submissions/<int:submission_id>/download", methods=["GET"])
@student_required
def download_student_own_submission_file(submission_id: int):
    """Securely downloads the student's own submitted file. Verifies ownership."""
    student, user = get_current_student_and_user()
    if not student:
        return jsonify({"success": False, "message": "Student profile not found"}), 404

    submission = db.session.get(AssignmentSubmission, submission_id)
    if not submission or submission.student_id != student.student_id:
        return jsonify({"success": False, "message": "Submission not found or unauthorized"}), 404

    validated_path = safe_file_path(SUBMISSIONS_DIR, submission.file_path)
    if not validated_path:
        return jsonify({"success": False, "message": "Submission file not found on server"}), 404

    download_name = submission.file_name or os.path.basename(validated_path)
    return send_file(validated_path, as_attachment=True, download_name=download_name)


# ============================================================
# 6. NOTES & STUDY MATERIALS TAB
# ============================================================

@student_assignments_bp.route("/notes", methods=["GET"])
@student_required
def list_student_notes():
    """
    Lists published study materials for courses the student is actively enrolled in.
    Supports filtering by offering_id, category, and search query.
    """
    student, user = get_current_student_and_user()
    if not student:
        return jsonify({"success": False, "message": "Student profile not found"}), 404

    offering_ids = get_student_active_offering_ids(student.student_id)
    if not offering_ids:
        return jsonify({"success": True, "notes": []}), 200

    query = StudyMaterial.query.filter(
        StudyMaterial.offering_id.in_(offering_ids),
        StudyMaterial.visibility == "PUBLISHED",
    )

    # Class filter
    offering_filter = request.args.get("offering_id")
    if offering_filter and offering_filter != "all":
        try:
            off_id = int(offering_filter)
            query = query.filter(StudyMaterial.offering_id == off_id)
        except ValueError:
            pass

    # Category filter
    category_filter = request.args.get("category")
    if category_filter and category_filter.upper() != "ALL":
        query = query.filter(StudyMaterial.category == category_filter.upper())

    # Search keyword
    search = request.args.get("search", "").strip()
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (StudyMaterial.title.ilike(search_pattern))
            | (StudyMaterial.description.ilike(search_pattern))
            | (StudyMaterial.file_name.ilike(search_pattern))
        )

    notes = (
        query.options(
            joinedload(StudyMaterial.offering)
            .joinedload(CourseOffering.course),
            joinedload(StudyMaterial.offering)
            .joinedload(CourseOffering.faculty)
            .joinedload(Faculty.user),
        )
        .order_by(StudyMaterial.created_at.desc())
        .all()
    )

    results = []
    for item in notes:
        offering = item.offering
        course = offering.course if offering else None
        faculty = offering.faculty if offering else None
        faculty_name = faculty.user.name if faculty and faculty.user else "Faculty"

        data = item.to_dict()
        data.update({
            "course_code": course.course_code if course else "",
            "course_name": course.course_name if course else "",
            "section": offering.section if offering else "",
            "faculty_name": faculty_name,
            "formatted_date": item.created_at.strftime("%b %d, %Y") if item.created_at else "",
        })
        results.append(data)

    return jsonify({"success": True, "notes": results}), 200


@student_assignments_bp.route("/notes/<int:material_id>/download", methods=["GET"])
@student_required
def download_student_note(material_id: int):
    """Securely downloads a study material document for an enrolled course."""
    student, user = get_current_student_and_user()
    if not student:
        return jsonify({"success": False, "message": "Student profile not found"}), 404

    note = db.session.get(StudyMaterial, material_id)
    if not note or note.visibility != "PUBLISHED":
        return jsonify({"success": False, "message": "Study material not found"}), 404

    if not is_student_enrolled_in_offering(student.student_id, note.offering_id):
        return jsonify({"success": False, "message": "Not authorized to access this document"}), 403

    validated_path = safe_file_path(MATERIALS_DIR, note.file_path)
    if not validated_path:
        return jsonify({"success": False, "message": "File not found on server"}), 404

    download_name = note.file_name or os.path.basename(validated_path)
    return send_file(validated_path, as_attachment=True, download_name=download_name)


# ============================================================
# 7. UPCOMING DEADLINES TAB
# ============================================================

@student_assignments_bp.route("/deadlines", methods=["GET"])
@student_required
def get_student_upcoming_deadlines():
    """
    Returns published assignments in chronological order of due date.
    Highlights remaining time and submission status.
    """
    student, user = get_current_student_and_user()
    if not student:
        return jsonify({"success": False, "message": "Student profile not found"}), 404

    offering_ids = get_student_active_offering_ids(student.student_id)
    if not offering_ids:
        return jsonify({"success": True, "deadlines": []}), 200

    assignments = (
        CourseAssignment.query.filter(
            CourseAssignment.offering_id.in_(offering_ids),
            CourseAssignment.status == "PUBLISHED",
        )
        .options(
            joinedload(CourseAssignment.offering)
            .joinedload(CourseOffering.course),
            joinedload(CourseAssignment.offering)
            .joinedload(CourseOffering.faculty)
            .joinedload(Faculty.user),
        )
        .order_by(CourseAssignment.due_date.asc())
        .all()
    )

    asgn_ids = [a.assignment_id for a in assignments]
    submissions = (
        AssignmentSubmission.query.filter(
            AssignmentSubmission.assignment_id.in_(asgn_ids),
            AssignmentSubmission.student_id == student.student_id,
        ).all()
        if asgn_ids
        else []
    )
    sub_map = {s.assignment_id: s for s in submissions}

    deadlines = []
    for a in assignments:
        offering = a.offering
        course = offering.course if offering else None
        faculty = offering.faculty if offering else None
        faculty_name = faculty.user.name if faculty and faculty.user else "Faculty"

        sub = sub_map.get(a.assignment_id)
        has_submitted = sub is not None
        time_status, time_label, is_overdue = calculate_due_status(a.due_date)

        can_submit = (
            not has_submitted
            and (not is_overdue or a.allow_late_submission)
        )

        deadlines.append({
            "assignment_id": a.assignment_id,
            "title": a.title,
            "course_code": course.course_code if course else "",
            "course_name": course.course_name if course else "",
            "faculty_name": faculty_name,
            "due_date": a.due_date.isoformat() if a.due_date else None,
            "formatted_due_date": a.due_date.strftime("%b %d, %Y %I:%M %p") if a.due_date else "",
            "time_label": time_label,
            "is_overdue": is_overdue,
            "has_submitted": has_submitted,
            "can_submit": can_submit,
            "submission_status": "Submitted" if has_submitted else ("Overdue" if is_overdue else "Pending"),
            "maximum_marks": float(a.maximum_marks),
        })

    return jsonify({"success": True, "deadlines": deadlines}), 200


# ============================================================
# 8. RESULTS & FEEDBACK TAB
# ============================================================

@student_assignments_bp.route("/results", methods=["GET"])
@student_required
def get_student_evaluated_results():
    """
    Returns evaluated assignment submissions with marks obtained, percentage,
    evaluation date, and faculty feedback.
    """
    student, user = get_current_student_and_user()
    if not student:
        return jsonify({"success": False, "message": "Student profile not found"}), 404

    evaluated_subs = (
        AssignmentSubmission.query.filter_by(
            student_id=student.student_id,
            review_status="REVIEWED",
        )
        .options(
            joinedload(AssignmentSubmission.assignment)
            .joinedload(CourseAssignment.offering)
            .joinedload(CourseOffering.course),
            joinedload(AssignmentSubmission.assignment)
            .joinedload(CourseAssignment.offering)
            .joinedload(CourseOffering.faculty)
            .joinedload(Faculty.user),
        )
        .order_by(AssignmentSubmission.reviewed_at.desc())
        .all()
    )

    results = []
    for sub in evaluated_subs:
        assignment = sub.assignment
        offering = assignment.offering if assignment else None
        course = offering.course if offering else None
        faculty = offering.faculty if offering else None
        faculty_name = faculty.user.name if faculty and faculty.user else "Faculty"

        max_marks = float(assignment.maximum_marks) if assignment else 100.0
        marks_obtained = float(sub.marks_obtained) if sub.marks_obtained is not None else 0.0
        percentage = round((marks_obtained / max_marks * 100), 1) if max_marks > 0 else 0.0

        results.append({
            "submission_id": sub.submission_id,
            "assignment_id": sub.assignment_id,
            "assignment_title": assignment.title if assignment else "Assignment",
            "course_code": course.course_code if course else "",
            "course_name": course.course_name if course else "",
            "faculty_name": faculty_name,
            "maximum_marks": max_marks,
            "marks_obtained": marks_obtained,
            "percentage": percentage,
            "feedback": sub.feedback or "No feedback provided",
            "reviewed_at": sub.reviewed_at.isoformat() if sub.reviewed_at else None,
            "formatted_reviewed_date": sub.reviewed_at.strftime("%b %d, %Y") if sub.reviewed_at else "",
            "is_late": sub.is_late,
            "submitted_at": sub.submitted_at.isoformat() if sub.submitted_at else None,
            "has_file": bool(sub.file_path),
            "file_name": sub.file_name,
        })

    return jsonify({"success": True, "results": results}), 200
