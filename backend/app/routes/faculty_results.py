"""
Faculty Academic Results Management Routes
SAMS-FR (Smart Attendance Management System)

Provides backend endpoints for Faculty Result Upload:
- Assigned courses/offerings retrieval
- Assessment definitions management (Internal Tests, Midterms, Practicals, Finals)
- Live summary counters (Total Students, Draft, Submitted, Published)
- Student roster with existing scores, live grade and percentage calculation
- Draft saving and submission for administrative review
- CSV mark import and template export
"""

from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity, verify_jwt_in_request
from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models.academic_result import AcademicResult
from app.models.activity_log import ActivityLog
from app.models.assessment import Assessment
from app.models.course import Course
from app.models.course_offering import CourseOffering
from app.models.department import Department
from app.models.enrollment import Enrollment
from app.models.faculty import Faculty
from app.models.result_submission import ResultSubmission
from app.models.student import Student
from app.models.user import User
from app.utils.auth import faculty_or_admin_required, faculty_required
from app.utils.grading_policy import determine_grade_and_points as calc_grade_and_points

faculty_results_bp = Blueprint(
    "faculty_results",
    __name__,
    url_prefix="/api/faculty/results",
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_current_user_and_faculty() -> Tuple[Optional[int], Optional[Faculty], bool]:
    """Extracts current user id, faculty entity, and whether user is an admin."""
    verify_jwt_in_request()
    identity = get_jwt_identity()
    claims = get_jwt()
    is_admin = claims.get("role") == "ADMIN"

    try:
        user_id = int(identity) if identity else None
    except (TypeError, ValueError):
        user_id = None

    faculty = Faculty.query.filter_by(user_id=user_id).first() if user_id else None
    return user_id, faculty, is_admin


def determine_grade_and_points(
    marks: Optional[float], max_marks: float = 100.0
) -> Tuple[str, float, str, Optional[float]]:
    """
    Computes percentage, grade, grade points, and pass status.
    Returns (grade, grade_points, status, percentage).
    """
    if marks is None:
        return "N/A", 0.0, "PENDING", None

    max_val = float(max_marks) if max_marks and float(max_marks) > 0 else 100.0
    percentage = round((float(marks) / max_val) * 100.0, 2)
    grade, gp, status = calc_grade_and_points(marks, max_marks)
    return grade, float(gp), status, percentage


def log_faculty_activity(
    actor_id: Optional[int],
    action_type: str,
    description: str,
    entity_id: str,
    details: Optional[Dict] = None,
):
    """Logs an activity event into activity_logs table."""
    actor_name = "Faculty Member"
    actor_role = "FACULTY"
    if actor_id:
        user = db.session.get(User, actor_id)
        if user:
            actor_name = user.name
            actor_role = user.role

    log = ActivityLog(
        actor_id=actor_id,
        actor_name=actor_name,
        actor_role=actor_role,
        action_type=action_type,
        description=description,
        entity_type="FACULTY_RESULTS",
        entity_id=str(entity_id),
        status="SUCCESS",
        details=details or {},
        created_at=datetime.utcnow(),
    )
    db.session.add(log)


def ensure_default_assessments(offering_id: int, user_id: Optional[int]) -> List[Assessment]:
    """Ensures a course offering has a set of standard assessments."""
    existing = Assessment.query.filter_by(offering_id=offering_id).all()
    if existing:
        return existing

    defaults = [
        {"name": "Internal Test 1", "type": "INTERNAL", "max_marks": Decimal("30.00"), "weightage": Decimal("20.00")},
        {"name": "Internal Test 2", "type": "INTERNAL", "max_marks": Decimal("30.00"), "weightage": Decimal("20.00")},
        {"name": "Midterm Assessment", "type": "MIDTERM", "max_marks": Decimal("50.00"), "weightage": Decimal("25.00")},
        {"name": "Practical Examination", "type": "PRACTICAL", "max_marks": Decimal("50.00"), "weightage": Decimal("25.00")},
        {"name": "End-Semester Examination", "type": "FINAL", "max_marks": Decimal("100.00"), "weightage": Decimal("50.00")},
    ]

    created = []
    for d in defaults:
        asm = Assessment(
            offering_id=offering_id,
            assessment_name=d["name"],
            assessment_type=d["type"],
            max_marks=d["max_marks"],
            weightage=d["weightage"],
            created_by=user_id,
        )
        db.session.add(asm)
        created.append(asm)

    db.session.commit()
    return created


# ============================================================
# 1. RETRIEVE ASSIGNED COURSES & OFFERINGS
# ============================================================

@faculty_results_bp.get("/courses")
@faculty_or_admin_required
def get_assigned_courses():
    """
    Returns course offerings assigned to the logged-in faculty member.
    """
    user_id, faculty, is_admin = get_current_user_and_faculty()

    if not is_admin and not faculty:
        return jsonify({
            "success": False,
            "message": "Faculty profile not found. Please contact administration.",
        }), 404

    query = (
        CourseOffering.query
        .options(
            joinedload(CourseOffering.course).joinedload(Course.department),
            joinedload(CourseOffering.enrollments),
        )
    )

    if not is_admin:
        query = query.filter_by(faculty_id=faculty.faculty_id)

    offerings = (
        query
        .order_by(CourseOffering.academic_year.desc(), CourseOffering.semester.desc(), CourseOffering.offering_id.asc())
        .all()
    )

    items = []
    for off in offerings:
        course = off.course
        dept = course.department if course else None
        active_enrollments = [e for e in off.enrollments if e.status == "ACTIVE"]

        items.append({
            "offering_id": off.offering_id,
            "course_id": off.course_id,
            "course_code": course.course_code if course else "",
            "course_name": course.course_name if course else "",
            "department_code": dept.department_code if dept else "",
            "department_name": dept.department_name if dept else "",
            "academic_year": off.academic_year,
            "semester": off.semester,
            "section": off.section or "A",
            "credits": course.credits if course else 3,
            "enrolled_count": len(active_enrollments),
            "label": f"{course.course_name if course else 'Course'} ({course.course_code if course else ''})",
        })

    return jsonify({"success": True, "data": items}), 200


# ============================================================
# 2. ASSESSMENTS MANAGEMENT
# ============================================================

@faculty_results_bp.get("/assessments")
@faculty_or_admin_required
def get_assessments():
    """
    Retrieves assessments for a selected course offering.
    If none exist yet, provisions default assessment types.
    """
    offering_id = request.args.get("offering_id", type=int)
    if not offering_id:
        return jsonify({"success": False, "message": "offering_id parameter is required"}), 400

    user_id, faculty, is_admin = get_current_user_and_faculty()
    offering = db.session.get(CourseOffering, offering_id)
    if not offering:
        return jsonify({"success": False, "message": "Course offering not found"}), 404

    if not is_admin and (not faculty or offering.faculty_id != faculty.faculty_id):
        return jsonify({"success": False, "message": "Unauthorized: Not assigned to this course offering"}), 403

    assessments = ensure_default_assessments(offering_id, user_id)

    data = [
        {
            "assessment_id": a.assessment_id,
            "offering_id": a.offering_id,
            "assessment_name": a.assessment_name,
            "assessment_type": a.assessment_type,
            "max_marks": float(a.max_marks),
            "weightage": float(a.weightage) if a.weightage else 100.0,
            "assessment_date": a.assessment_date.isoformat() if a.assessment_date else None,
            "label": f"{a.assessment_name} (Max: {int(a.max_marks) if a.max_marks % 1 == 0 else float(a.max_marks)})",
        }
        for a in assessments
    ]

    return jsonify({"success": True, "data": data}), 200


@faculty_results_bp.post("/assessments")
@faculty_or_admin_required
def create_assessment():
    """
    Allows faculty to define a new assessment for their assigned course offering.
    """
    user_id, faculty, is_admin = get_current_user_and_faculty()
    payload = request.get_json(silent=True) or {}

    offering_id = payload.get("offering_id")
    name = (payload.get("assessment_name") or "").strip()
    asm_type = payload.get("assessment_type", "INTERNAL").upper()
    max_marks = payload.get("max_marks", 30.0)
    weightage = payload.get("weightage", 20.0)

    if not offering_id or not name:
        return jsonify({"success": False, "message": "Offering ID and assessment name are required"}), 400

    offering = db.session.get(CourseOffering, offering_id)
    if not offering:
        return jsonify({"success": False, "message": "Course offering not found"}), 404

    if not is_admin and (not faculty or offering.faculty_id != faculty.faculty_id):
        return jsonify({"success": False, "message": "Unauthorized: Not assigned to this course offering"}), 403

    try:
        max_marks_dec = Decimal(str(max_marks))
        weightage_dec = Decimal(str(weightage))
    except Exception:
        return jsonify({"success": False, "message": "Invalid numeric values for marks or weightage"}), 400

    existing = Assessment.query.filter_by(offering_id=offering_id, assessment_name=name).first()
    if existing:
        return jsonify({"success": False, "message": f"Assessment '{name}' already exists for this course."}), 409

    asm = Assessment(
        offering_id=offering_id,
        assessment_name=name,
        assessment_type=asm_type,
        max_marks=max_marks_dec,
        weightage=weightage_dec,
        created_by=user_id,
    )
    db.session.add(asm)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": f"Assessment '{name}' created successfully",
        "data": {
            "assessment_id": asm.assessment_id,
            "assessment_name": asm.assessment_name,
            "assessment_type": asm.assessment_type,
            "max_marks": float(asm.max_marks),
            "weightage": float(asm.weightage) if asm.weightage else None,
        },
    }), 201


# ============================================================
# 3. LIVE SUMMARY COUNTERS FOR DASHBOARD CARDS
# ============================================================

@faculty_results_bp.get("/summary")
@faculty_or_admin_required
def get_results_summary():
    """
    Returns real database metrics for the 4 summary cards:
    - total_students: Enrolled students in selected offering
    - draft: Results saved but not submitted
    - submitted: Results waiting for administrative review
    - published: Results approved and published to student portal
    """
    offering_id = request.args.get("offering_id", type=int)
    assessment_id = request.args.get("assessment_id", type=int)

    user_id, faculty, is_admin = get_current_user_and_faculty()

    if not offering_id:
        # Default global summary across all offerings taught by this faculty
        offerings_query = CourseOffering.query
        if not is_admin and faculty:
            offerings_query = offerings_query.filter_by(faculty_id=faculty.faculty_id)

        offerings = offerings_query.all()
        off_ids = [o.offering_id for o in offerings]

        if not off_ids:
            return jsonify({
                "success": True,
                "data": {
                    "total_students": 0,
                    "draft": 0,
                    "submitted": 0,
                    "published": 0,
                    "submission_status": "NOT_STARTED",
                },
            }), 200

        total_enrolled = Enrollment.query.filter(
            Enrollment.offering_id.in_(off_ids),
            Enrollment.status == "ACTIVE",
        ).count()

        submissions = ResultSubmission.query.filter(ResultSubmission.offering_id.in_(off_ids)).all()
        draft_count = sum(s.total_students for s in submissions if s.status == "DRAFT")
        submitted_count = sum(s.total_students for s in submissions if s.status in ("SUBMITTED", "APPROVED"))
        published_count = sum(s.total_students for s in submissions if s.status == "PUBLISHED")

        return jsonify({
            "success": True,
            "data": {
                "total_students": total_enrolled,
                "draft": draft_count,
                "submitted": submitted_count,
                "published": published_count,
                "submission_status": "DRAFT" if draft_count > 0 else "NOT_STARTED",
            },
        }), 200

    # Specific offering summary
    offering = db.session.get(CourseOffering, offering_id)
    if not offering:
        return jsonify({"success": False, "message": "Course offering not found"}), 404

    if not is_admin and (not faculty or offering.faculty_id != faculty.faculty_id):
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    total_students = Enrollment.query.filter_by(offering_id=offering_id, status="ACTIVE").count()

    # Submission query
    sub_query = ResultSubmission.query.filter_by(offering_id=offering_id)
    if assessment_id:
        sub_query = sub_query.filter_by(assessment_id=assessment_id)
    submission = sub_query.first()

    # Count individual AcademicResults linked to this offering & assessment
    res_query = AcademicResult.query.filter_by(offering_id=offering_id)
    if assessment_id:
        res_query = res_query.filter_by(assessment_id=assessment_id)
    elif submission:
        res_query = res_query.filter_by(submission_id=submission.submission_id)

    results = res_query.all()
    evaluated_count = len([r for r in results if r.marks_obtained is not None])

    sub_status = submission.status if submission else "NOT_STARTED"
    draft_val = evaluated_count if sub_status == "DRAFT" else (0 if sub_status in ("SUBMITTED", "PUBLISHED") else evaluated_count)
    submitted_val = evaluated_count if sub_status in ("SUBMITTED", "APPROVED") else 0
    published_val = evaluated_count if sub_status == "PUBLISHED" else 0

    return jsonify({
        "success": True,
        "data": {
            "total_students": total_students,
            "draft": draft_val,
            "submitted": submitted_val,
            "published": published_val,
            "submission_status": sub_status,
            "submission_id": submission.submission_id if submission else None,
            "review_remarks": submission.review_remarks if submission and sub_status == "RETURNED" else None,
            "submitted_at": submission.submitted_at.isoformat() if submission and submission.submitted_at else None,
            "published_at": submission.published_at.isoformat() if submission and submission.published_at else None,
        },
    }), 200


# ============================================================
# 4. ROSTER AND MARKS FOR ENTRY TABLE
# ============================================================

@faculty_results_bp.get("/students")
@faculty_or_admin_required
def get_students_for_entry():
    """
    Returns the enrolled students for the chosen course offering and assessment,
    including current marks, percentage, grade, status (Complete/Pending), and remarks.
    """
    offering_id = request.args.get("offering_id", type=int)
    assessment_id = request.args.get("assessment_id", type=int)

    if not offering_id:
        return jsonify({"success": False, "message": "offering_id parameter is required"}), 400

    user_id, faculty, is_admin = get_current_user_and_faculty()
    offering = (
        CourseOffering.query
        .options(
            joinedload(CourseOffering.course).joinedload(Course.department),
        )
        .filter_by(offering_id=offering_id)
        .first()
    )
    if not offering:
        return jsonify({"success": False, "message": "Course offering not found"}), 404

    if not is_admin and (not faculty or offering.faculty_id != faculty.faculty_id):
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    # Resolve assessment
    if not assessment_id:
        assessments = ensure_default_assessments(offering_id, user_id)
        assessment = assessments[0] if assessments else None
    else:
        assessment = db.session.get(Assessment, assessment_id)

    max_marks = float(assessment.max_marks) if assessment else 30.0

    # Retrieve active enrollments sorted by Roll No
    enrollments = (
        Enrollment.query
        .join(Student, Enrollment.student_id == Student.student_id)
        .join(User, Student.user_id == User.user_id)
        .options(
            joinedload(Enrollment.student).joinedload(Student.user),
        )
        .filter(
            Enrollment.offering_id == offering_id,
            Enrollment.status == "ACTIVE",
        )
        .order_by(Student.enrollment_no.asc())
        .all()
    )

    # Submission and results lookup
    sub_query = ResultSubmission.query.filter_by(offering_id=offering_id)
    if assessment:
        sub_query = sub_query.filter_by(assessment_id=assessment.assessment_id)
    submission = sub_query.first()

    results_map = {}
    if assessment:
        res_list = AcademicResult.query.filter_by(
            offering_id=offering_id,
            assessment_id=assessment.assessment_id,
        ).all()
        results_map = {r.student_id: r for r in res_list}
    elif submission:
        res_list = AcademicResult.query.filter_by(
            submission_id=submission.submission_id,
        ).all()
        results_map = {r.student_id: r for r in res_list}

    student_records = []
    complete_count = 0
    marks_sum = 0.0

    for idx, enr in enumerate(enrollments, 1):
        stu = enr.student
        user = stu.user if stu else None
        res = results_map.get(enr.student_id)

        raw_marks = float(res.marks_obtained) if res and res.marks_obtained is not None else None
        grade, gp, status_flag, percentage = determine_grade_and_points(raw_marks, max_marks)

        is_complete = raw_marks is not None
        if is_complete:
            complete_count += 1
            marks_sum += raw_marks

        student_records.append({
            "index": idx,
            "student_id": enr.student_id,
            "roll_no": stu.enrollment_no if stu else f"STU{enr.student_id:04d}",
            "student_name": user.name if user else "Student",
            "max_marks": max_marks,
            "marks_obtained": raw_marks,
            "percentage": percentage,
            "grade": grade if is_complete else "-",
            "grade_points": gp if is_complete else None,
            "status": "Complete" if is_complete else "Pending",
            "remarks": res.remarks if res and res.remarks else ("No marks entered" if not is_complete else "-"),
            "result_id": res.result_id if res else None,
        })

    course = offering.course
    avg_marks = round(marks_sum / complete_count, 2) if complete_count > 0 else 0.0

    return jsonify({
        "success": True,
        "data": {
            "course": {
                "offering_id": offering.offering_id,
                "course_id": offering.course_id,
                "course_code": course.course_code if course else "",
                "course_name": course.course_name if course else "",
                "academic_year": offering.academic_year,
                "semester": offering.semester,
                "section": offering.section or "A",
            },
            "assessment": {
                "assessment_id": assessment.assessment_id if assessment else None,
                "assessment_name": assessment.assessment_name if assessment else "Internal Test 1",
                "assessment_type": assessment.assessment_type if assessment else "INTERNAL",
                "max_marks": max_marks,
            },
            "submission": {
                "submission_id": submission.submission_id if submission else None,
                "status": submission.status if submission else "NOT_STARTED",
                "review_remarks": submission.review_remarks if submission and submission.status == "RETURNED" else None,
                "submitted_at": submission.submitted_at.isoformat() if submission and submission.submitted_at else None,
            },
            "stats": {
                "total_enrolled": len(enrollments),
                "complete_count": complete_count,
                "pending_count": len(enrollments) - complete_count,
                "average_marks": avg_marks,
            },
            "students": student_records,
        },
    }), 200


# ============================================================
# 5. SAVE DRAFT MARKS & SUBMIT RESULTS FOR REVIEW
# ============================================================

def process_save_or_submit(action: str):
    """Internal handler for saving drafts or submitting marks."""
    user_id, faculty, is_admin = get_current_user_and_faculty()
    payload = request.get_json(silent=True) or {}

    offering_id = payload.get("offering_id")
    assessment_id = payload.get("assessment_id")
    scores = payload.get("scores", [])

    if not offering_id:
        return jsonify({"success": False, "message": "offering_id is required"}), 400

    offering = db.session.get(CourseOffering, offering_id)
    if not offering:
        return jsonify({"success": False, "message": "Course offering not found"}), 404

    if not is_admin and (not faculty or offering.faculty_id != faculty.faculty_id):
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    # Find or create Assessment
    if assessment_id:
        assessment = db.session.get(Assessment, assessment_id)
    else:
        assessments = ensure_default_assessments(offering_id, user_id)
        assessment = assessments[0] if assessments else None

    if not assessment:
        return jsonify({"success": False, "message": "No valid assessment configured"}), 400

    max_marks = float(assessment.max_marks)
    target_status = "SUBMITTED" if action == "SUBMIT" else "DRAFT"

    # Find or create ResultSubmission
    submission = ResultSubmission.query.filter_by(
        offering_id=offering_id,
        assessment_id=assessment.assessment_id,
    ).first()

    effective_faculty_id = offering.faculty_id or (faculty.faculty_id if faculty else 1)

    if not submission:
        submission = ResultSubmission(
            assessment_id=assessment.assessment_id,
            offering_id=offering_id,
            faculty_id=effective_faculty_id,
            academic_year=offering.academic_year,
            semester=offering.semester,
            status=target_status,
            submitted_by_user_id=user_id,
            submitted_at=datetime.utcnow() if target_status == "SUBMITTED" else None,
        )
        db.session.add(submission)
        db.session.flush()
    else:
        if submission.status == "PUBLISHED" and not is_admin:
            return jsonify({
                "success": False,
                "message": "Results are already published to students and cannot be modified without administrative clearance.",
            }), 400

        submission.status = target_status
        if target_status == "SUBMITTED":
            submission.submitted_at = datetime.utcnow()
            submission.submitted_by_user_id = user_id

    # Verify student membership and upsert AcademicResult
    total_count = len(scores)
    passed_count = 0
    marks_sum = 0.0
    valid_count = 0

    course = offering.course
    credits = course.credits if course else 3

    for item in scores:
        student_id = item.get("student_id")
        raw_marks = item.get("marks_obtained")
        remarks = item.get("remarks")

        if raw_marks is not None and str(raw_marks).strip() != "":
            try:
                marks_val = float(raw_marks)
                if marks_val < 0 or marks_val > max_marks:
                    return jsonify({
                        "success": False,
                        "message": f"Mark {marks_val} is out of permitted range (0 to {max_marks}).",
                    }), 400
                marks_sum += marks_val
                valid_count += 1
            except (ValueError, TypeError):
                return jsonify({"success": False, "message": f"Invalid mark value for student #{student_id}"}), 400
        else:
            marks_val = None

        # When submitting, all students must have marks
        if target_status == "SUBMITTED" and marks_val is None:
            return jsonify({
                "success": False,
                "message": "All students must have valid marks entered before final submission.",
            }), 400

        grade, gp, status_flag, _ = determine_grade_and_points(marks_val, max_marks)
        if status_flag == "PASS":
            passed_count += 1

        # Check existing result
        res = AcademicResult.query.filter_by(
            student_id=student_id,
            offering_id=offering_id,
            assessment_id=assessment.assessment_id,
        ).first()

        if res:
            res.submission_id = submission.submission_id
            res.marks_obtained = Decimal(str(marks_val)) if marks_val is not None else None
            res.max_marks = Decimal(str(max_marks))
            res.grade = grade
            res.grade_points = gp
            res.status = status_flag
            res.remarks = remarks
            res.is_published = False  # Faculty submissions are never auto-published!
            res.updated_at = datetime.utcnow()
        else:
            new_res = AcademicResult(
                student_id=student_id,
                course_id=offering.course_id,
                offering_id=offering.offering_id,
                assessment_id=assessment.assessment_id,
                submission_id=submission.submission_id,
                academic_year=offering.academic_year,
                semester=offering.semester,
                credits=credits,
                marks_obtained=Decimal(str(marks_val)) if marks_val is not None else None,
                max_marks=Decimal(str(max_marks)),
                grade=grade,
                grade_points=gp,
                status=status_flag,
                is_published=False,
                remarks=remarks,
            )
            db.session.add(new_res)

    submission.total_students = total_count
    submission.passed_students = passed_count
    submission.failed_students = max(0, total_count - passed_count)
    submission.average_marks = Decimal(str(round(marks_sum / valid_count, 2))) if valid_count > 0 else Decimal("0.00")

    action_label = "RESULT_SUBMITTED" if target_status == "SUBMITTED" else "RESULT_DRAFT_SAVED"
    log_faculty_activity(
        actor_id=user_id,
        action_type=action_label,
        description=f"{'Submitted results for admin review' if target_status == 'SUBMITTED' else 'Saved marks draft'} for {course.course_code if course else 'Course'} ({valid_count}/{total_count} marks recorded).",
        entity_id=str(submission.submission_id),
        details={"status": target_status, "assessment": assessment.assessment_name},
    )

    db.session.commit()

    msg = (
        "Results successfully submitted for administrative review."
        if target_status == "SUBMITTED"
        else "Draft marks successfully saved."
    )

    return jsonify({
        "success": True,
        "message": msg,
        "data": {
            "submission_id": submission.submission_id,
            "status": submission.status,
            "total_students": submission.total_students,
            "passed_students": submission.passed_students,
            "average_marks": float(submission.average_marks),
        },
    }), 200


@faculty_results_bp.post("/save-draft")
@faculty_or_admin_required
def save_draft():
    """Saves marks as draft without forwarding for approval."""
    return process_save_or_submit(action="DRAFT")


@faculty_results_bp.post("/submit")
@faculty_or_admin_required
def submit_results():
    """Validates marks and submits result set to administrator for review."""
    return process_save_or_submit(action="SUBMIT")


# ============================================================
# 6. CSV IMPORT VALIDATION
# ============================================================

@faculty_results_bp.post("/import")
@faculty_or_admin_required
def import_marks_csv():
    """
    Accepts parsed CSV rows, validates Roll Numbers against active enrollments,
    and checks mark boundaries.
    """
    user_id, faculty, is_admin = get_current_user_and_faculty()
    payload = request.get_json(silent=True) or {}

    offering_id = payload.get("offering_id")
    assessment_id = payload.get("assessment_id")
    rows = payload.get("rows", [])

    if not offering_id:
        return jsonify({"success": False, "message": "offering_id is required"}), 400

    offering = db.session.get(CourseOffering, offering_id)
    if not offering:
        return jsonify({"success": False, "message": "Course offering not found"}), 404

    if not is_admin and (not faculty or offering.faculty_id != faculty.faculty_id):
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    assessment = db.session.get(Assessment, assessment_id) if assessment_id else None
    max_marks = float(assessment.max_marks) if assessment else 30.0

    enrollments = (
        Enrollment.query
        .join(Student, Enrollment.student_id == Student.student_id)
        .options(joinedload(Enrollment.student))
        .filter(Enrollment.offering_id == offering_id, Enrollment.status == "ACTIVE")
        .all()
    )

    roster_map = {e.student.enrollment_no.strip().upper(): e.student for e in enrollments if e.student}

    valid_rows = []
    errors = []

    for idx, r in enumerate(rows, 1):
        raw_roll = str(r.get("roll_no") or r.get("Roll No") or "").strip().upper()
        raw_marks = r.get("marks_obtained") or r.get("Marks") or r.get("Marks Obtained")
        remarks = str(r.get("remarks") or r.get("Remarks") or "-").strip()

        if not raw_roll:
            errors.append(f"Row {idx}: Missing roll number.")
            continue

        student = roster_map.get(raw_roll)
        if not student:
            errors.append(f"Row {idx}: Student roll '{raw_roll}' is not enrolled in this course.")
            continue

        try:
            marks_num = float(raw_marks)
            if marks_num < 0 or marks_num > max_marks:
                errors.append(f"Row {idx} ({raw_roll}): Mark {marks_num} out of range (0 - {max_marks}).")
                continue
        except (ValueError, TypeError):
            errors.append(f"Row {idx} ({raw_roll}): Invalid numeric mark '{raw_marks}'.")
            continue

        valid_rows.append({
            "student_id": student.student_id,
            "roll_no": student.enrollment_no,
            "marks_obtained": marks_num,
            "remarks": remarks,
        })

    return jsonify({
        "success": True,
        "message": f"Successfully parsed {len(valid_rows)} valid rows with {len(errors)} errors.",
        "data": {
            "valid_records": valid_rows,
            "errors": errors,
            "total_parsed": len(rows),
        },
    }), 200
