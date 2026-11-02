"""
Admin and Faculty Academic Results Management Blueprint.
Smart Attendance & Academic Management System (SAMS-FR)

Provides comprehensive full-stack REST APIs for:
- Assessment Definition & Academic Configuration
- Faculty Result Entry & Draft / Final Submission Workflow
- Administrator Review, Approval, and Return-for-Correction
- Result Publication to Student Portal
- Audit Logging & Post-Publication Result Corrections
"""

from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required
from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models import (
    AcademicResult,
    ActivityLog,
    Assessment,
    Course,
    CourseOffering,
    Department,
    Enrollment,
    Examination,
    Faculty,
    ResultCorrection,
    ResultSubmission,
    Student,
    User,
)
from app.utils.auth import admin_required, faculty_or_admin_required
from app.utils.grading_policy import (
    determine_grade_and_points,
)

admin_academic_results_bp = Blueprint(
    "admin_academic_results",
    __name__,
    url_prefix="/api/admin/academic-results",
)


def get_current_user_id() -> Optional[int]:
    """Derive user_id from verified JWT identity."""
    identity = get_jwt_identity()
    if not identity:
        return None
    try:
        return int(identity)
    except (ValueError, TypeError):
        return None


def log_academic_activity(
    actor_id: Optional[int],
    action_type: str,
    description: str,
    entity_id: str,
    details: Optional[Dict] = None,
):
    """Log an activity event to activity_logs table."""
    actor_name = "System"
    actor_role = "ADMIN"
    if actor_id:
        user = User.query.get(actor_id)
        if user:
            actor_name = user.name
            actor_role = user.role

    log = ActivityLog(
        actor_id=actor_id,
        actor_name=actor_name,
        actor_role=actor_role,
        action_type=action_type,
        description=description,
        entity_type="ACADEMIC_RESULTS",
        entity_id=str(entity_id),
        status="SUCCESS",
        details=details or {},
        created_at=datetime.utcnow(),
    )
    db.session.add(log)


# ============================================================
# 1. ACADEMIC CONFIGURATION & FILTER OPTIONS
# ============================================================

@admin_academic_results_bp.get("/filters")
@faculty_or_admin_required
def get_filter_options():
    """
    Returns dynamic filter options populated from real database records:
    - Academic Years
    - Semesters
    - Departments
    - Courses
    - Faculty
    - Result Statuses
    """
    # Academic years from offerings
    years_query = (
        db.session.query(CourseOffering.academic_year)
        .distinct()
        .filter(CourseOffering.academic_year.isnot(None))
        .order_by(CourseOffering.academic_year.desc())
        .all()
    )
    academic_years = [y[0] for y in years_query if y[0]]
    if not academic_years:
        academic_years = ["2026-2027", "2024-2025"]

    # Semesters from offerings or courses
    semesters_query = (
        db.session.query(CourseOffering.semester)
        .distinct()
        .filter(CourseOffering.semester.isnot(None))
        .order_by(CourseOffering.semester.asc())
        .all()
    )
    semesters = [s[0] for s in semesters_query if s[0]]
    if not semesters:
        semesters = [1, 2, 3, 4, 5, 6, 7, 8]

    # Active departments
    depts = (
        Department.query
        .filter_by(is_active=True)
        .order_by(Department.department_name.asc())
        .all()
    )
    departments = [
        {
            "department_id": d.department_id,
            "department_name": d.department_name,
            "department_code": d.department_code,
        }
        for d in depts
    ]

    # Courses
    courses = (
        Course.query
        .order_by(Course.course_code.asc())
        .all()
    )
    courses_data = [
        {
            "course_id": c.course_id,
            "course_code": c.course_code,
            "course_name": c.course_name,
            "department_id": c.department_id,
            "semester": c.semester,
            "credits": c.credits,
        }
        for c in courses
    ]

    # Faculty members
    faculty_members = (
        Faculty.query
        .join(User, Faculty.user_id == User.user_id)
        .order_by(User.name.asc())
        .all()
    )
    faculty_data = [
        {
            "faculty_id": f.faculty_id,
            "name": f.user.name if f.user else "Faculty",
            "department_id": f.department_id,
        }
        for f in faculty_members
    ]

    statuses = [
        {"value": "all", "label": "All Statuses"},
        {"value": "SUBMITTED", "label": "Submitted for Review"},
        {"value": "APPROVED", "label": "Approved"},
        {"value": "PUBLISHED", "label": "Published"},
        {"value": "RETURNED", "label": "Returned for Correction"},
        {"value": "DRAFT", "label": "Draft"},
    ]

    return jsonify({
        "success": True,
        "data": {
            "academic_years": academic_years,
            "semesters": semesters,
            "departments": departments,
            "courses": courses_data,
            "faculty": faculty_data,
            "statuses": statuses,
        },
    }), 200


# ============================================================
# 2. METRICS OVERVIEW CARDS
# ============================================================

@admin_academic_results_bp.get("/overview")
@admin_required
def get_results_overview():
    """
    Returns exact counts from the database for the 4 summary cards:
    - Pending Reviews (SUBMITTED)
    - Submitted Results (SUBMITTED, APPROVED, PUBLISHED)
    - Published Results (PUBLISHED)
    - Returned for Correction (RETURNED)
    Plus overall statistics (pass rate, average marks).
    """
    pending_reviews = ResultSubmission.query.filter_by(status="SUBMITTED").count()
    submitted_results = ResultSubmission.query.filter(ResultSubmission.status.in_(["SUBMITTED", "APPROVED", "PUBLISHED"])).count()
    published_results = ResultSubmission.query.filter_by(status="PUBLISHED").count()
    returned_corrections = ResultSubmission.query.filter_by(status="RETURNED").count()
    draft_results = ResultSubmission.query.filter_by(status="DRAFT").count()

    total_submissions = ResultSubmission.query.count()

    # Calculate average pass rate and overall score from published/submitted records
    stats_query = (
        db.session.query(
            func.sum(ResultSubmission.total_students),
            func.sum(ResultSubmission.passed_students),
            func.avg(ResultSubmission.average_marks),
        )
        .filter(ResultSubmission.status.in_(["SUBMITTED", "APPROVED", "PUBLISHED"]))
        .first()
    )

    total_std = stats_query[0] or 0
    passed_std = stats_query[1] or 0
    avg_marks = float(stats_query[2] or 0.0)

    pass_rate = round((passed_std / total_std * 100), 1) if total_std > 0 else 0.0

    return jsonify({
        "success": True,
        "data": {
            "cards": {
                "pending_reviews": pending_reviews,
                "submitted_results": submitted_results,
                "published_results": published_results,
                "returned_corrections": returned_corrections,
                "draft_results": draft_results,
            },
            "stats": {
                "total_submissions": total_submissions,
                "total_students_evaluated": total_std,
                "passed_students": passed_std,
                "overall_pass_rate": pass_rate,
                "average_marks": round(avg_marks, 2),
            },
        },
    }), 200


# ============================================================
# 3. SUBMISSIONS LIST WITH FILTERING & PAGINATION
# ============================================================

@admin_academic_results_bp.get("/submissions")
@admin_required
def get_submissions_list():
    """
    Returns paginated list of result submissions filtered by:
    academic_year, semester, department_id, course_id, faculty_id, status.
    """
    page = request.args.get("page", default=1, type=int)
    limit = request.args.get("limit", default=10, type=int)
    if page < 1:
        page = 1
    if limit < 1 or limit > 100:
        limit = 10

    academic_year = request.args.get("academic_year")
    semester = request.args.get("semester", type=int)
    department_id = request.args.get("department_id", type=int)
    course_id = request.args.get("course_id", type=int)
    faculty_id = request.args.get("faculty_id", type=int)
    status = request.args.get("status")

    query = (
        ResultSubmission.query
        .join(Assessment, ResultSubmission.assessment_id == Assessment.assessment_id)
        .join(CourseOffering, ResultSubmission.offering_id == CourseOffering.offering_id)
        .join(Course, CourseOffering.course_id == Course.course_id)
        .join(Department, Course.department_id == Department.department_id)
        .join(Faculty, ResultSubmission.faculty_id == Faculty.faculty_id)
        .join(User, Faculty.user_id == User.user_id)
        .options(
            joinedload(ResultSubmission.assessment),
            joinedload(ResultSubmission.offering).joinedload(CourseOffering.course).joinedload(Course.department),
            joinedload(ResultSubmission.faculty).joinedload(Faculty.user),
        )
    )

    if academic_year and academic_year != "all":
        query = query.filter(ResultSubmission.academic_year == academic_year)
    if semester and semester > 0:
        query = query.filter(ResultSubmission.semester == semester)
    if department_id and department_id > 0:
        query = query.filter(Course.department_id == department_id)
    if course_id and course_id > 0:
        query = query.filter(CourseOffering.course_id == course_id)
    if faculty_id and faculty_id > 0:
        query = query.filter(ResultSubmission.faculty_id == faculty_id)
    if status and status != "all":
        query = query.filter(ResultSubmission.status == status.upper())

    total_count = query.count()
    submissions = (
        query
        .order_by(ResultSubmission.created_at.desc(), ResultSubmission.submission_id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    items = []
    for s in submissions:
        course = s.offering.course if s.offering else None
        dept = course.department if course else None
        faculty_user = s.faculty.user if s.faculty else None

        items.append({
            "submission_id": s.submission_id,
            "assessment_id": s.assessment_id,
            "offering_id": s.offering_id,
            "course_id": course.course_id if course else None,
            "course_code": course.course_code if course else "N/A",
            "course_name": course.course_name if course else "N/A",
            "department_id": dept.department_id if dept else None,
            "department_name": dept.department_name if dept else "N/A",
            "department_code": dept.department_code if dept else "N/A",
            "faculty_id": s.faculty_id,
            "faculty_name": faculty_user.name if faculty_user else "Faculty",
            "assessment_name": s.assessment.assessment_name if s.assessment else "Assessment",
            "assessment_type": s.assessment.assessment_type if s.assessment else "FINAL",
            "max_marks": float(s.assessment.max_marks or 100.0) if s.assessment else 100.0,
            "academic_year": s.academic_year,
            "semester": s.semester,
            "section": s.offering.section if s.offering else "A",
            "student_count": s.total_students,
            "passed_count": s.passed_students,
            "failed_count": s.failed_students,
            "average_marks": float(s.average_marks) if s.average_marks is not None else None,
            "status": s.status,
            "submitted_at": s.submitted_at.isoformat() if s.submitted_at else None,
            "reviewed_at": s.reviewed_at.isoformat() if s.reviewed_at else None,
            "published_at": s.published_at.isoformat() if s.published_at else None,
            "review_remarks": s.review_remarks,
        })

    total_pages = (total_count + limit - 1) // limit if limit > 0 else 1

    return jsonify({
        "success": True,
        "data": {
            "submissions": items,
            "pagination": {
                "page": page,
                "limit": limit,
                "total_count": total_count,
                "total_pages": total_pages,
            },
        },
    }), 200


# ============================================================
# 4. SUBMISSION DETAILS FOR ADMINISTRATIVE REVIEW
# ============================================================

@admin_academic_results_bp.get("/submissions/<int:submission_id>")
@admin_required
def get_submission_details(submission_id: int):
    """
    Returns complete details of a submission, enrolled students, their scores,
    grade distribution, and any missing marks warnings.
    """
    submission = (
        ResultSubmission.query
        .options(
            joinedload(ResultSubmission.assessment),
            joinedload(ResultSubmission.offering).joinedload(CourseOffering.course).joinedload(Course.department),
            joinedload(ResultSubmission.faculty).joinedload(Faculty.user),
        )
        .get(submission_id)
    )

    if not submission:
        return jsonify({
            "success": False,
            "message": f"Result submission #{submission_id} not found",
        }), 404

    offering = submission.offering
    course = offering.course if offering else None
    dept = course.department if course else None
    assessment = submission.assessment

    # 1. Fetch all active enrollments for this offering
    enrollments = (
        Enrollment.query
        .join(Student, Enrollment.student_id == Student.student_id)
        .join(User, Student.user_id == User.user_id)
        .filter(
            Enrollment.offering_id == submission.offering_id,
            Enrollment.status == "ACTIVE",
        )
        .order_by(Student.enrollment_no.asc())
        .all()
    )

    # 2. Fetch existing results for this submission
    results = (
        AcademicResult.query
        .filter_by(submission_id=submission.submission_id)
        .all()
    )
    results_map = {r.student_id: r for r in results}

    student_records = []
    missing_count = 0
    max_marks = float(assessment.max_marks or 100.0) if assessment else 100.0

    for idx, enr in enumerate(enrollments, 1):
        stu = enr.student
        user = stu.user if stu else None
        res = results_map.get(enr.student_id)

        marks = float(res.marks_obtained) if res and res.marks_obtained is not None else None
        is_missing = marks is None
        if is_missing:
            missing_count += 1

        student_records.append({
            "index": idx,
            "student_id": stu.student_id if stu else enr.student_id,
            "enrollment_no": stu.enrollment_no if stu else "N/A",
            "student_name": user.name if user else "Student",
            "result_id": res.result_id if res else None,
            "marks_obtained": marks,
            "max_marks": max_marks,
            "grade": res.grade if res else "N/A",
            "grade_points": float(res.grade_points) if res else 0.0,
            "status": res.status if res else ("Pending" if is_missing else "Pass"),
            "is_missing": is_missing,
            "remarks": res.remarks if res else None,
        })

    # Grade distribution breakdown
    grade_distribution = {}
    for sr in student_records:
        g = sr["grade"]
        if g != "N/A":
            grade_distribution[g] = grade_distribution.get(g, 0) + 1

    return jsonify({
        "success": True,
        "data": {
            "submission_id": submission.submission_id,
            "status": submission.status,
            "academic_year": submission.academic_year,
            "semester": submission.semester,
            "section": offering.section if offering else "A",
            "review_remarks": submission.review_remarks,
            "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else None,
            "reviewed_at": submission.reviewed_at.isoformat() if submission.reviewed_at else None,
            "published_at": submission.published_at.isoformat() if submission.published_at else None,
            "course": {
                "course_id": course.course_id if course else None,
                "course_code": course.course_code if course else "N/A",
                "course_name": course.course_name if course else "N/A",
                "credits": course.credits if course else 3,
                "department_name": dept.department_name if dept else "N/A",
            },
            "faculty": {
                "faculty_id": submission.faculty_id,
                "name": submission.faculty.user.name if submission.faculty and submission.faculty.user else "Faculty",
            },
            "assessment": {
                "assessment_id": assessment.assessment_id if assessment else None,
                "assessment_name": assessment.assessment_name if assessment else "Final Examination",
                "assessment_type": assessment.assessment_type if assessment else "FINAL",
                "max_marks": max_marks,
            },
            "summary": {
                "total_enrolled": len(enrollments),
                "evaluated_count": len(student_records) - missing_count,
                "missing_count": missing_count,
                "passed_count": submission.passed_students,
                "failed_count": submission.failed_students,
                "average_marks": float(submission.average_marks) if submission.average_marks is not None else None,
                "grade_distribution": grade_distribution,
            },
            "students": student_records,
        },
    }), 200


# ============================================================
# 5. APPROVAL & RETURN WORKFLOW
# ============================================================

@admin_academic_results_bp.post("/submissions/<int:submission_id>/approve")
@admin_required
def approve_submission(submission_id: int):
    """
    Approves a submitted result set.
    Transitions status from SUBMITTED to APPROVED.
    """
    user_id = get_current_user_id()
    submission = ResultSubmission.query.get(submission_id)

    if not submission:
        return jsonify({"success": False, "message": "Submission not found"}), 404

    if submission.status not in ("SUBMITTED", "RETURNED"):
        return jsonify({
            "success": False,
            "message": f"Cannot approve submission in '{submission.status}' state. Only 'SUBMITTED' or 'RETURNED' results can be approved.",
        }), 400

    payload = request.get_json() or {}
    approval_note = payload.get("remarks", "Approved by administration")

    submission.status = "APPROVED"
    submission.reviewed_by_user_id = user_id
    submission.reviewed_at = datetime.utcnow()
    submission.review_remarks = approval_note

    log_academic_activity(
        actor_id=user_id,
        action_type="RESULT_APPROVED",
        description=f"Approved results for submission #{submission.submission_id} ({submission.offering.course.course_code if submission.offering and submission.offering.course else 'Course'})",
        entity_id=str(submission.submission_id),
        details={"status": "APPROVED", "remarks": approval_note},
    )

    db.session.commit()

    return jsonify({
        "success": True,
        "message": f"Submission #{submission_id} has been approved successfully",
        "data": {
            "submission_id": submission.submission_id,
            "status": submission.status,
            "reviewed_at": submission.reviewed_at.isoformat(),
        },
    }), 200


@admin_academic_results_bp.post("/submissions/<int:submission_id>/return")
@admin_required
def return_submission(submission_id: int):
    """
    Returns an incomplete or invalid submission to faculty for correction.
    Requires an explanation reason.
    Transitions status from SUBMITTED to RETURNED.
    """
    user_id = get_current_user_id()
    submission = ResultSubmission.query.get(submission_id)

    if not submission:
        return jsonify({"success": False, "message": "Submission not found"}), 404

    if submission.status != "SUBMITTED":
        return jsonify({
            "success": False,
            "message": f"Cannot return submission in '{submission.status}' state. Only 'SUBMITTED' results can be returned.",
        }), 400

    payload = request.get_json() or {}
    reason = payload.get("reason", "").strip()

    if not reason:
        return jsonify({
            "success": False,
            "message": "A detailed reason is required to return a submission for correction.",
        }), 400

    submission.status = "RETURNED"
    submission.reviewed_by_user_id = user_id
    submission.reviewed_at = datetime.utcnow()
    submission.review_remarks = reason

    log_academic_activity(
        actor_id=user_id,
        action_type="RESULT_RETURNED",
        description=f"Returned submission #{submission.submission_id} for correction. Reason: {reason}",
        entity_id=str(submission.submission_id),
        details={"status": "RETURNED", "reason": reason},
    )

    db.session.commit()

    return jsonify({
        "success": True,
        "message": f"Submission #{submission_id} has been returned to faculty for correction.",
        "data": {
            "submission_id": submission.submission_id,
            "status": submission.status,
            "review_remarks": submission.review_remarks,
        },
    }), 200


# ============================================================
# 6. PUBLICATION WORKFLOW
# ============================================================

@admin_academic_results_bp.post("/submissions/<int:submission_id>/publish")
@admin_required
def publish_submission(submission_id: int):
    """
    Publishes approved academic results to the Student Portal.
    Transitions status from APPROVED to PUBLISHED.
    Sets is_published = True and published_at on all child AcademicResult rows.
    """
    user_id = get_current_user_id()
    submission = ResultSubmission.query.get(submission_id)

    if not submission:
        return jsonify({"success": False, "message": "Submission not found"}), 404

    if submission.status != "APPROVED":
        return jsonify({
            "success": False,
            "message": f"Cannot publish submission in '{submission.status}' state. Results must be 'APPROVED' before publication.",
        }), 400

    now = datetime.utcnow()
    submission.status = "PUBLISHED"
    submission.published_by_user_id = user_id
    submission.published_at = now

    # Flip publication flag for all student results in this submission
    results = AcademicResult.query.filter_by(submission_id=submission.submission_id).all()
    published_count = 0
    for r in results:
        r.is_published = True
        r.published_at = now
        published_count += 1

    log_academic_activity(
        actor_id=user_id,
        action_type="RESULT_PUBLISHED",
        description=f"Published {published_count} results for submission #{submission.submission_id} to student portal.",
        entity_id=str(submission.submission_id),
        details={"status": "PUBLISHED", "published_results_count": published_count},
    )

    db.session.commit()

    return jsonify({
        "success": True,
        "message": f"Successfully published {published_count} results to Student Portal",
        "data": {
            "submission_id": submission.submission_id,
            "status": submission.status,
            "published_at": submission.published_at.isoformat(),
            "published_count": published_count,
        },
    }), 200


# ============================================================
# 7. POST-PUBLICATION RESULT CORRECTION WORKFLOW
# ============================================================

@admin_academic_results_bp.post("/corrections")
@admin_required
def record_result_correction():
    """
    Authorized correction of a student's marks/grade.
    Preserves audit history in result_corrections table.
    Accepts: { result_id: int, new_marks: float, reason: str }
    """
    user_id = get_current_user_id()
    payload = request.get_json() or {}

    result_id = payload.get("result_id")
    new_marks = payload.get("new_marks")
    reason = payload.get("reason", "").strip()

    if not result_id or new_marks is None or not reason:
        return jsonify({
            "success": False,
            "message": "result_id, new_marks, and a mandatory reason are required.",
        }), 400

    try:
        new_marks = float(new_marks)
        if new_marks < 0 or new_marks > 100:
            return jsonify({"success": False, "message": "new_marks must be between 0 and 100"}), 400
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "new_marks must be a valid number"}), 400

    result = AcademicResult.query.get(result_id)
    if not result:
        return jsonify({"success": False, "message": f"Result #{result_id} not found"}), 404

    # Save previous values
    prev_marks = result.marks_obtained
    prev_grade = result.grade
    prev_gp = result.grade_points

    # Calculate new grade & points
    new_grade, new_gp, status = determine_grade_and_points(
        marks=new_marks,
        max_marks=float(result.max_marks or 100.0),
    )

    # Insert audit entry into result_corrections
    correction = ResultCorrection(
        result_id=result.result_id,
        student_id=result.student_id,
        course_id=result.course_id,
        submission_id=result.submission_id,
        previous_marks=prev_marks,
        new_marks=Decimal(str(new_marks)),
        previous_grade=prev_grade,
        new_grade=new_grade,
        previous_grade_points=prev_gp,
        new_grade_points=new_gp,
        reason=reason,
        corrected_by_user_id=user_id,
        created_at=datetime.utcnow(),
    )
    db.session.add(correction)

    # Update result
    result.marks_obtained = Decimal(str(new_marks))
    result.grade = new_grade
    result.grade_points = new_gp
    result.status = status
    result.updated_at = datetime.utcnow()

    # Recalculate submission metrics if associated
    if result.submission:
        sub = result.submission
        sub_results = AcademicResult.query.filter_by(submission_id=sub.submission_id).all()
        if sub_results:
            sub.passed_students = sum(1 for r in sub_results if str(r.status).upper() == "PASS")
            sub.failed_students = len(sub_results) - sub.passed_students
            valid_marks = [float(r.marks_obtained) for r in sub_results if r.marks_obtained is not None]
            if valid_marks:
                sub.average_marks = Decimal(str(round(sum(valid_marks) / len(valid_marks), 2)))

    log_academic_activity(
        actor_id=user_id,
        action_type="RESULT_CORRECTED",
        description=f"Corrected marks for student #{result.student.enrollment_no if result.student else result.student_id} in {result.course.course_code if result.course else 'Course'}: {prev_marks} -> {new_marks}. Reason: {reason}",
        entity_id=str(result.result_id),
        details={
            "result_id": result.result_id,
            "previous_marks": float(prev_marks) if prev_marks else None,
            "new_marks": new_marks,
            "reason": reason,
        },
    )

    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Result correction recorded successfully",
        "data": {
            "result_id": result.result_id,
            "marks_obtained": float(result.marks_obtained),
            "grade": result.grade,
            "grade_points": float(result.grade_points),
            "status": result.status,
        },
    }), 200


# ============================================================
# 8. AUDIT HISTORY TIMELINE
# ============================================================

@admin_academic_results_bp.get("/audit-history")
@admin_required
def get_audit_history():
    """
    Returns structured audit history timeline of result submissions,
    approvals, returns, publications, and mark corrections.
    """
    limit = request.args.get("limit", default=25, type=int)

    # Fetch logs from activity_logs for academic results
    logs = (
        ActivityLog.query
        .filter(ActivityLog.entity_type == "ACADEMIC_RESULTS")
        .order_by(ActivityLog.created_at.desc(), ActivityLog.id.desc())
        .limit(limit)
        .all()
    )

    # Fetch corrections
    corrections = (
        ResultCorrection.query
        .options(
            joinedload(ResultCorrection.student).joinedload(Student.user),
            joinedload(ResultCorrection.course),
            joinedload(ResultCorrection.corrected_by),
        )
        .order_by(ResultCorrection.created_at.desc())
        .limit(limit)
        .all()
    )

    events = []

    for l in logs:
        events.append({
            "id": f"log-{l.id}",
            "type": l.action_type,
            "actor_name": l.actor_name or "System",
            "actor_role": l.actor_role or "ADMIN",
            "description": l.description,
            "timestamp": l.created_at.isoformat(),
            "details": l.details or {},
        })

    for c in corrections:
        stu_name = c.student.user.name if c.student and c.student.user else f"Student {c.student_id}"
        course_name = c.course.course_code if c.course else "Course"
        admin_name = c.corrected_by.name if c.corrected_by else "Admin"

        events.append({
            "id": f"cor-{c.correction_id}",
            "type": "RESULT_CORRECTED",
            "actor_name": admin_name,
            "actor_role": "ADMIN",
            "description": f"Grade Correction for {stu_name} ({course_name}): {c.previous_marks} -> {c.new_marks}. Reason: {c.reason}",
            "timestamp": c.created_at.isoformat(),
            "details": {
                "previous_marks": float(c.previous_marks) if c.previous_marks else None,
                "new_marks": float(c.new_marks) if c.new_marks else None,
                "previous_grade": c.previous_grade,
                "new_grade": c.new_grade,
                "reason": c.reason,
            },
        })

    # Sort combined events by timestamp descending
    events.sort(key=lambda x: x["timestamp"], reverse=True)
    events = events[:limit]

    return jsonify({
        "success": True,
        "data": events,
    }), 200


# ============================================================
# 9. ASSESSMENT CONFIGURATION MANAGEMENT
# ============================================================

@admin_academic_results_bp.post("/assessments")
@admin_required
def create_assessment():
    """
    Creates a new assessment definition for a course offering.
    """
    user_id = get_current_user_id()
    payload = request.get_json() or {}

    offering_id = payload.get("offering_id")
    assessment_name = payload.get("assessment_name", "").strip()
    assessment_type = payload.get("assessment_type", "FINAL").upper()
    max_marks = payload.get("max_marks", 100.0)
    weightage = payload.get("weightage", 100.0)
    exam_id = payload.get("exam_id")
    date_str = payload.get("assessment_date")

    if not offering_id or not assessment_name:
        return jsonify({
            "success": False,
            "message": "offering_id and assessment_name are required",
        }), 400

    offering = CourseOffering.query.get(offering_id)
    if not offering:
        return jsonify({"success": False, "message": "Course offering not found"}), 404

    # Check duplicate
    existing = Assessment.query.filter_by(
        offering_id=offering_id,
        assessment_name=assessment_name,
    ).first()
    if existing:
        return jsonify({
            "success": False,
            "message": f"Assessment '{assessment_name}' already exists for this course offering",
        }), 409

    assessment_date = None
    if date_str:
        try:
            assessment_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            pass

    assessment = Assessment(
        offering_id=offering_id,
        exam_id=exam_id,
        assessment_name=assessment_name,
        assessment_type=assessment_type,
        max_marks=Decimal(str(max_marks)),
        weightage=Decimal(str(weightage)),
        assessment_date=assessment_date,
        created_by=user_id,
    )
    db.session.add(assessment)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Assessment created successfully",
        "data": {
            "assessment_id": assessment.assessment_id,
            "assessment_name": assessment.assessment_name,
            "max_marks": float(assessment.max_marks),
        },
    }), 201


# ============================================================
# 10. FACULTY RESULT ENTRY WORKFLOW (PHASE 6 INTEGRATION)
# ============================================================

@admin_academic_results_bp.get("/faculty/my-offerings")
@faculty_or_admin_required
def get_faculty_offerings():
    """
    Returns course offerings assigned to the authenticated faculty.
    """
    user_id = get_current_user_id()
    faculty = Faculty.query.filter_by(user_id=user_id).first()

    claims = get_jwt()
    is_admin = claims.get("role") == "ADMIN"

    query = (
        CourseOffering.query
        .options(
            joinedload(CourseOffering.course),
            joinedload(CourseOffering.faculty).joinedload(Faculty.user),
        )
    )

    if not is_admin:
        if not faculty:
            return jsonify({"success": False, "message": "Faculty record not found"}), 404
        query = query.filter_by(faculty_id=faculty.faculty_id)

    offerings = query.order_by(CourseOffering.academic_year.desc(), CourseOffering.semester.desc()).all()

    items = []
    for o in offerings:
        items.append({
            "offering_id": o.offering_id,
            "course_code": o.course.course_code if o.course else "",
            "course_name": o.course.course_name if o.course else "",
            "credits": o.course.credits if o.course else 3,
            "academic_year": o.academic_year,
            "semester": o.semester,
            "section": o.section,
            "enrolled_count": len(o.enrollments),
            "faculty_name": o.faculty.user.name if o.faculty and o.faculty.user else "Faculty",
        })

    return jsonify({"success": True, "data": items}), 200


@admin_academic_results_bp.get("/faculty/offerings/<int:offering_id>/students")
@faculty_or_admin_required
def get_offering_students_for_entry(offering_id: int):
    """
    Returns enrolled students and any existing draft/submitted scores
    for faculty mark entry.
    """
    user_id = get_current_user_id()
    claims = get_jwt()
    is_admin = claims.get("role") == "ADMIN"

    offering = CourseOffering.query.get(offering_id)
    if not offering:
        return jsonify({"success": False, "message": "Course offering not found"}), 404

    if not is_admin:
        faculty = Faculty.query.filter_by(user_id=user_id).first()
        if not faculty or offering.faculty_id != faculty.faculty_id:
            return jsonify({"success": False, "message": "You are not assigned to this course offering"}), 403

    # Enrollments
    enrollments = (
        Enrollment.query
        .join(Student, Enrollment.student_id == Student.student_id)
        .join(User, Student.user_id == User.user_id)
        .filter(
            Enrollment.offering_id == offering_id,
            Enrollment.status == "ACTIVE",
        )
        .order_by(Student.enrollment_no.asc())
        .all()
    )

    # Check for existing submission
    submission = ResultSubmission.query.filter_by(offering_id=offering_id).first()
    results_map = {}
    if submission:
        results = AcademicResult.query.filter_by(submission_id=submission.submission_id).all()
        results_map = {r.student_id: r for r in results}

    student_list = []
    for enr in enrollments:
        stu = enr.student
        res = results_map.get(enr.student_id)
        student_list.append({
            "student_id": stu.student_id if stu else enr.student_id,
            "enrollment_no": stu.enrollment_no if stu else "N/A",
            "name": stu.user.name if stu and stu.user else "Student",
            "marks_obtained": float(res.marks_obtained) if res and res.marks_obtained is not None else None,
            "grade": res.grade if res else None,
            "grade_points": float(res.grade_points) if res else None,
            "remarks": res.remarks if res else None,
        })

    return jsonify({
        "success": True,
        "data": {
            "offering_id": offering.offering_id,
            "course_code": offering.course.course_code if offering.course else "",
            "course_name": offering.course.course_name if offering.course else "",
            "academic_year": offering.academic_year,
            "semester": offering.semester,
            "section": offering.section,
            "submission_status": submission.status if submission else "DRAFT",
            "submission_id": submission.submission_id if submission else None,
            "students": student_list,
        },
    }), 200


@admin_academic_results_bp.post("/faculty/offerings/<int:offering_id>/submit")
@faculty_or_admin_required
def submit_marks_by_faculty(offering_id: int):
    """
    Allows faculty (or admin on behalf) to save draft marks or submit for approval.
    Enforces course ownership!
    Accepts:
    {
      "action": "DRAFT" | "SUBMIT",
      "assessment_name": optional str,
      "max_marks": optional float (100.0),
      "scores": [
        { "student_id": int, "marks_obtained": float, "remarks": optional str }
      ]
    }
    """
    user_id = get_current_user_id()
    claims = get_jwt()
    is_admin = claims.get("role") == "ADMIN"

    offering = CourseOffering.query.get(offering_id)
    if not offering:
        return jsonify({"success": False, "message": "Course offering not found"}), 404

    faculty = Faculty.query.filter_by(user_id=user_id).first()
    if not is_admin:
        if not faculty or offering.faculty_id != faculty.faculty_id:
            return jsonify({"success": False, "message": "You are not authorized to submit results for this course"}), 403

    payload = request.get_json() or {}
    action = payload.get("action", "DRAFT").upper()
    target_status = "SUBMITTED" if action == "SUBMIT" else "DRAFT"
    assessment_name = payload.get("assessment_name", "End-Semester Examination").strip()
    max_marks = float(payload.get("max_marks", 100.0))
    scores = payload.get("scores", [])

    if not scores:
        return jsonify({"success": False, "message": "No student scores provided"}), 400

    # Ensure assessment entity exists
    assessment = Assessment.query.filter_by(
        offering_id=offering_id,
        assessment_name=assessment_name,
    ).first()
    if not assessment:
        assessment = Assessment(
            offering_id=offering_id,
            assessment_name=assessment_name,
            assessment_type="FINAL",
            max_marks=Decimal(str(max_marks)),
            created_by=user_id,
        )
        db.session.add(assessment)
        db.session.flush()

    # Find or create submission
    sub = ResultSubmission.query.filter_by(
        assessment_id=assessment.assessment_id,
        offering_id=offering_id,
    ).first()

    effective_faculty_id = offering.faculty_id or (faculty.faculty_id if faculty else 1)

    if not sub:
        sub = ResultSubmission(
            assessment_id=assessment.assessment_id,
            offering_id=offering_id,
            faculty_id=effective_faculty_id,
            academic_year=offering.academic_year,
            semester=offering.semester,
            status=target_status,
            submitted_by_user_id=user_id,
            submitted_at=datetime.utcnow() if target_status == "SUBMITTED" else None,
        )
        db.session.add(sub)
        db.session.flush()
    else:
        if sub.status == "PUBLISHED" and not is_admin:
            return jsonify({"success": False, "message": "Published results cannot be modified by faculty. Contact administration."}), 400
        sub.status = target_status
        if target_status == "SUBMITTED":
            sub.submitted_at = datetime.utcnow()
            sub.submitted_by_user_id = user_id

    # Record / update individual student results
    total_count = len(scores)
    passed_count = 0
    marks_sum = 0.0
    valid_marks_count = 0

    course = offering.course
    credits = course.credits if course else 3

    for item in scores:
        student_id = item.get("student_id")
        raw_marks = item.get("marks_obtained")
        remarks = item.get("remarks")

        if raw_marks is not None:
            try:
                marks_val = float(raw_marks)
                marks_sum += marks_val
                valid_marks_count += 1
            except (ValueError, TypeError):
                marks_val = None
        else:
            marks_val = None

        grade, gp, status = determine_grade_and_points(marks=marks_val, max_marks=max_marks)
        if status == "PASS":
            passed_count += 1

        existing_res = AcademicResult.query.filter_by(
            student_id=student_id,
            course_id=offering.course_id,
            academic_year=offering.academic_year,
            semester=offering.semester,
        ).first()

        is_pub = False  # Faculty submissions are never auto-published to students!

        if existing_res:
            existing_res.submission_id = sub.submission_id
            existing_res.assessment_id = assessment.assessment_id
            existing_res.marks_obtained = Decimal(str(marks_val)) if marks_val is not None else None
            existing_res.max_marks = Decimal(str(max_marks))
            existing_res.grade = grade
            existing_res.grade_points = gp
            existing_res.status = status
            existing_res.remarks = remarks
            existing_res.is_published = is_pub
            existing_res.updated_at = datetime.utcnow()
        else:
            new_res = AcademicResult(
                student_id=student_id,
                course_id=offering.course_id,
                offering_id=offering.offering_id,
                assessment_id=assessment.assessment_id,
                submission_id=sub.submission_id,
                academic_year=offering.academic_year,
                semester=offering.semester,
                credits=credits,
                marks_obtained=Decimal(str(marks_val)) if marks_val is not None else None,
                max_marks=Decimal(str(max_marks)),
                grade=grade,
                grade_points=gp,
                status=status,
                is_published=is_pub,
                remarks=remarks,
            )
            db.session.add(new_res)

    # Update submission aggregate stats
    sub.total_students = total_count
    sub.passed_students = passed_count
    sub.failed_students = max(0, total_count - passed_count)
    sub.average_marks = Decimal(str(round(marks_sum / valid_marks_count, 2))) if valid_marks_count > 0 else Decimal("0.00")

    action_label = "RESULT_SUBMITTED" if target_status == "SUBMITTED" else "RESULT_DRAFT_SAVED"
    log_academic_activity(
        actor_id=user_id,
        action_type=action_label,
        description=f"{'Submitted' if target_status == 'SUBMITTED' else 'Saved draft'} marks for {course.course_code if course else 'Course'} ({total_count} students evaluated).",
        entity_id=str(sub.submission_id),
        details={"status": target_status, "total_students": total_count},
    )

    db.session.commit()

    return jsonify({
        "success": True,
        "message": f"Results successfully {'submitted for review' if target_status == 'SUBMITTED' else 'saved as draft'}",
        "data": {
            "submission_id": sub.submission_id,
            "status": sub.status,
            "total_students": sub.total_students,
            "passed_students": sub.passed_students,
            "average_marks": float(sub.average_marks),
        },
    }), 200
