"""
Student Academic Records Blueprint.
Smart Attendance Management System (SAMS-FR)

Provides secure, authenticated endpoints for:
- Student Academic Overview (GPA, CGPA, Credits, Current Semester)
- Semester-wise Academic Results & Subject Details
- Semester Performance Progression (GPA / CGPA history for charting)
- Examination Records
- Academic Documents & Official Report Export
"""

import csv
import io
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional

from flask import Blueprint, Response, jsonify, request, send_file
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required
from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models import (
    AcademicDocument,
    AcademicResult,
    Course,
    CourseOffering,
    Department,
    Enrollment,
    Examination,
    Student,
    User,
)
from app.utils.academic_year import resolve_student_academic_info
from app.utils.auth import student_or_admin_required, admin_required
from app.utils.export_engine import (
    generate_export,
    ExportValidationError,
    ExportRenderingError,
)
from app.utils.grading_policy import (
    TOTAL_PROGRAM_CREDITS,
    calculate_cgpa,
    calculate_credits_earned,
    calculate_sgpa,
    determine_grade_and_points,
    generate_academic_insights,
)

student_academic_bp = Blueprint(
    "student_academic",
    __name__,
    url_prefix="/api/student/academic-records",
)


def get_current_student() -> Optional[Student]:
    """Derive authenticated student entity from JWT identity."""
    identity = get_jwt_identity()
    if not identity:
        return None
    try:
        user_id = int(identity)
    except (ValueError, TypeError):
        return None

    return Student.query.filter_by(user_id=user_id).first()


def format_semester_name(semester: int, academic_year: Optional[str] = None) -> str:
    """Format human-readable semester name, e.g. 'Spring Semester 2025' or 'Semester 6'."""
    season = "Spring" if semester % 2 == 0 else "Fall"
    year_part = ""
    if academic_year and "-" in academic_year:
        years = academic_year.split("-")
        year_part = f" {years[1]}" if season == "Spring" else f" {years[0]}"
    return f"{season} Semester{year_part}" if year_part else f"Semester {semester}"


# ============================================================
# 1. ACADEMIC OVERVIEW
# ============================================================

@student_academic_bp.get("/overview")
@student_or_admin_required
def get_academic_overview():
    """
    Returns high-level academic summary for the authenticated student:
    - Program, Department, Batch, Current Semester
    - Current GPA and previous semester trend
    - Cumulative CGPA
    - Credits Earned vs Total Program Credits
    - Total, Completed, and In-Progress subjects
    """
    student = get_current_student()
    if not student:
        return jsonify({
            "success": False,
            "message": "Student profile not found",
        }), 404

    acad_info = resolve_student_academic_info(student)
    dept = student.department
    dept_name = dept.department_name if dept else "Computer Science & Engineering"
    program_name = f"B.Tech {dept_name.replace('Engineering', '').strip()}"

    # Query all published results for student
    all_results = (
        AcademicResult.query
        .options(joinedload(AcademicResult.course))
        .filter_by(student_id=student.student_id, is_published=True)
        .order_by(AcademicResult.semester.asc())
        .all()
    )

    current_semester = acad_info["semester"] or student.semester or 1
    academic_year = acad_info["academic_year"] or student.academic_year or "2024-2025"

    # Identify semesters with results
    distinct_semesters = sorted(list({r.semester for r in all_results}))

    # Current GPA: calculate for the latest semester with published results, or current semester
    target_current_sem = current_semester if any(r.semester == current_semester for r in all_results) else (
        distinct_semesters[-1] if distinct_semesters else current_semester
    )
    current_sem_results = [r for r in all_results if r.semester == target_current_sem]
    current_gpa = calculate_sgpa(current_sem_results)

    # Previous GPA: calculate for target_current_sem - 1 if it exists
    prev_sem = target_current_sem - 1
    prev_sem_results = [r for r in all_results if r.semester == prev_sem]
    previous_gpa = calculate_sgpa(prev_sem_results)

    # CGPA across all published results
    cgpa = calculate_cgpa(all_results)

    # Total credits earned
    credits_earned = calculate_credits_earned(all_results)

    # Calculate subjects for the current semester:
    # Look at active enrollments for total subjects in current semester
    active_enrollments = (
        Enrollment.query
        .join(CourseOffering, Enrollment.offering_id == CourseOffering.offering_id)
        .filter(
            Enrollment.student_id == student.student_id,
            Enrollment.status == "ACTIVE",
            CourseOffering.semester == current_semester,
        )
        .all()
    )
    enrolled_count = len(active_enrollments)

    # If active enrollments exist, use that; otherwise fallback to count of courses in current semester results
    total_subjects = max(enrolled_count, len(current_sem_results))
    completed_subjects = sum(1 for r in current_sem_results if str(r.status).upper() == "PASS")
    in_progress_subjects = max(0, total_subjects - completed_subjects)

    # Available semesters for dropdown selector
    # Combine semesters with results and semesters from enrollments
    enrolled_semesters = [
        e.offering.semester for e in student.enrollments if e.offering and e.offering.semester
    ]
    all_known_sems = sorted(list(set(distinct_semesters + enrolled_semesters + [current_semester])))
    available_semesters = [
        {
            "semester": sem,
            "label": format_semester_name(sem, academic_year),
            "has_results": sem in distinct_semesters,
        }
        for sem in all_known_sems
    ]

    # Calculate GPA trend string
    trend = None
    if current_gpa is not None and previous_gpa is not None:
        diff = round(current_gpa - previous_gpa, 2)
        trend = {
            "diff": abs(diff),
            "direction": "up" if diff >= 0 else "down",
            "formatted": f"{'+' if diff >= 0 else '-'}{abs(diff):.2f}",
        }

    return jsonify({
        "success": True,
        "data": {
            "student": {
                "student_id": student.student_id,
                "name": student.user.name if student.user else "Student",
                "enrollment_no": student.enrollment_no,
                "program": program_name,
                "department": dept_name,
                "batch": acad_info["batch_year"] or (student.batch.batch_name if student.batch else "2022 - 2026"),
                "academic_year": academic_year,
                "current_semester": current_semester,
                "current_semester_label": format_semester_name(current_semester, academic_year),
            },
            "metrics": {
                "current_gpa": current_gpa,
                "previous_gpa": previous_gpa,
                "gpa_trend": trend,
                "cgpa": cgpa,
                "total_credits_earned": credits_earned,
                "total_degree_credits": TOTAL_PROGRAM_CREDITS,
                "total_subjects": total_subjects,
                "completed_subjects": completed_subjects,
                "in_progress_subjects": in_progress_subjects,
                "has_published_results": len(all_results) > 0,
            },
            "available_semesters": available_semesters,
        },
    }), 200


# ============================================================
# 2. SEMESTER RESULTS & SUBJECT DETAILS
# ============================================================

@student_academic_bp.get("/results")
@student_or_admin_required
def get_semester_results():
    """
    Returns subject-wise marks, grades, grade points, credits, and SGPA
    for a specific semester (only published records).
    """
    student = get_current_student()
    if not student:
        return jsonify({
            "success": False,
            "message": "Student profile not found",
        }), 404

    semester_param = request.args.get("semester", type=int)

    # Find available published results
    query = (
        AcademicResult.query
        .options(joinedload(AcademicResult.course))
        .filter_by(student_id=student.student_id, is_published=True)
    )

    all_published = query.all()

    if not all_published:
        # Clean empty state when no results exist in DB
        return jsonify({
            "success": True,
            "data": {
                "semester": semester_param or student.semester,
                "semester_label": format_semester_name(semester_param or student.semester, student.academic_year),
                "sgpa": None,
                "cgpa": None,
                "total_credits": 0,
                "credits_earned": 0,
                "results": [],
                "subject_performance": [],
                "insights": [
                    "No published examination records are available yet for this semester.",
                    "Official grade sheets are released after examination cell verification.",
                ],
                "summary": {
                    "total": 0,
                    "passed": 0,
                    "failed": 0,
                },
            },
        }), 200

    distinct_semesters = sorted(list({r.semester for r in all_published}))

    # Default to requested semester, or student's current semester, or latest semester with results
    target_semester = semester_param
    if target_semester is None:
        target_semester = student.semester if student.semester in distinct_semesters else distinct_semesters[-1]

    sem_results = [r for r in all_published if r.semester == target_semester]

    # Calculate metrics for the target semester
    sgpa = calculate_sgpa(sem_results)
    cgpa = calculate_cgpa(all_published)
    total_credits = sum(r.credits for r in sem_results)
    credits_earned = calculate_credits_earned(sem_results)

    # Format table records
    formatted_results = []
    subject_performance = []

    for idx, r in enumerate(sem_results, 1):
        course = r.course
        code = course.course_code if course else f"SUB{idx}"
        name = course.course_name if course else f"Subject {idx}"
        marks = float(r.marks_obtained) if r.marks_obtained is not None else None
        max_marks = float(r.max_marks or 100.0)
        percentage = round((marks / max_marks * 100), 1) if marks is not None and max_marks > 0 else 0.0

        formatted_results.append({
            "index": idx,
            "result_id": r.result_id,
            "subject_code": code,
            "subject_name": name,
            "credits": r.credits,
            "marks": marks,
            "max_marks": max_marks,
            "grade": r.grade,
            "grade_points": float(r.grade_points),
            "status": "Pass" if str(r.status).upper() == "PASS" else "Fail",
            "remarks": r.remarks or "-",
        })

        if marks is not None:
            subject_performance.append({
                "subject_code": code,
                "subject_name": name,
                "percentage": percentage,
                "marks": marks,
                "max_marks": max_marks,
                "grade": r.grade,
            })

    insights = generate_academic_insights(sgpa, cgpa, sem_results)

    passed_count = sum(1 for r in sem_results if str(r.status).upper() == "PASS")
    failed_count = len(sem_results) - passed_count

    return jsonify({
        "success": True,
        "data": {
            "semester": target_semester,
            "semester_label": format_semester_name(target_semester, student.academic_year),
            "sgpa": sgpa,
            "cgpa": cgpa,
            "total_credits": total_credits,
            "credits_earned": credits_earned,
            "results": formatted_results,
            "subject_performance": subject_performance,
            "insights": insights,
            "summary": {
                "total": len(sem_results),
                "passed": passed_count,
                "failed": failed_count,
            },
        },
    }), 200


# ============================================================
# 3. ACADEMIC PERFORMANCE PROGRESSION (GPA / CGPA CHART)
# ============================================================

@student_academic_bp.get("/performance-history")
@student_or_admin_required
def get_performance_history():
    """
    Returns semester-by-semester progression of GPA and CGPA for charting.
    Only considers semesters with published results.
    """
    student = get_current_student()
    if not student:
        return jsonify({
            "success": False,
            "message": "Student profile not found",
        }), 404

    all_published = (
        AcademicResult.query
        .filter_by(student_id=student.student_id, is_published=True)
        .order_by(AcademicResult.semester.asc())
        .all()
    )

    if not all_published:
        return jsonify({
            "success": True,
            "data": [],
        }), 200

    # Group by semester
    from collections import defaultdict
    results_by_semester = defaultdict(list)
    for r in all_published:
        results_by_semester[r.semester].append(r)

    history = []
    accumulated_results = []

    for sem in sorted(results_by_semester.keys()):
        sem_records = results_by_semester[sem]
        accumulated_results.extend(sem_records)

        sem_gpa = calculate_sgpa(sem_records)
        progressive_cgpa = calculate_cgpa(accumulated_results)
        credits_earned = calculate_credits_earned(sem_records)

        history.append({
            "semester": sem,
            "semester_name": f"Sem {sem}",
            "full_name": format_semester_name(sem, student.academic_year),
            "gpa": sem_gpa,
            "cgpa": progressive_cgpa,
            "credits_earned": credits_earned,
            "total_courses": len(sem_records),
        })

    return jsonify({
        "success": True,
        "data": history,
    }), 200


# ============================================================
# 4. EXAMINATION RECORDS
# ============================================================

@student_academic_bp.get("/examinations")
@student_or_admin_required
def get_examination_records():
    """
    Returns published examinations and assessment schedules for the student.
    """
    student = get_current_student()
    if not student:
        return jsonify({
            "success": False,
            "message": "Student profile not found",
        }), 404

    # Fetch examinations for student's academic year or completed results
    exams = (
        Examination.query
        .filter_by(is_published=True)
        .order_by(Examination.semester.desc(), Examination.created_at.desc())
        .all()
    )

    exam_list = []
    for ex in exams:
        # Count student results in this exam
        results_count = AcademicResult.query.filter_by(
            student_id=student.student_id,
            exam_id=ex.exam_id,
            is_published=True,
        ).count()

        exam_list.append({
            "exam_id": ex.exam_id,
            "exam_name": ex.exam_name,
            "exam_type": ex.exam_type,
            "academic_year": ex.academic_year,
            "semester": ex.semester,
            "semester_label": format_semester_name(ex.semester, ex.academic_year),
            "start_date": ex.start_date.isoformat() if ex.start_date else None,
            "end_date": ex.end_date.isoformat() if ex.end_date else None,
            "published_at": ex.published_at.isoformat() if ex.published_at else None,
            "student_results_count": results_count,
            "status": "Published",
        })

    return jsonify({
        "success": True,
        "data": exam_list,
    }), 200


# ============================================================
# 5. ACADEMIC DOCUMENTS
# ============================================================

@student_academic_bp.get("/documents")
@student_or_admin_required
def get_academic_documents():
    """
    Returns available verifiable documents (Grade Cards, Transcripts).
    """
    student = get_current_student()
    if not student:
        return jsonify({
            "success": False,
            "message": "Student profile not found",
        }), 404

    docs = (
        AcademicDocument.query
        .filter_by(student_id=student.student_id)
        .order_by(AcademicDocument.issued_at.desc())
        .all()
    )

    doc_list = [
        {
            "document_id": d.document_id,
            "title": d.title,
            "document_type": d.document_type,
            "academic_year": d.academic_year,
            "semester": d.semester,
            "semester_label": format_semester_name(d.semester, d.academic_year) if d.semester else None,
            "file_size_bytes": d.file_size_bytes,
            "is_verified": d.is_verified,
            "issued_at": d.issued_at.strftime("%b %d, %Y") if d.issued_at else None,
        }
        for d in docs
    ]

    return jsonify({
        "success": True,
        "data": doc_list,
    }), 200


# ============================================================
# 6. EXPORT OFFICIAL REPORT
# ============================================================

@student_academic_bp.get("/export")
@student_or_admin_required
def export_academic_report():
    """
    Exports official grade sheet / academic report in PDF (default), Excel (.xlsx),
    or CSV format using authentic published academic records.
    """
    student = get_current_student()
    if not student:
        return jsonify({
            "success": False,
            "message": "Student profile not found",
        }), 404

    semester_param = request.args.get("semester", type=int)
    format_param = request.args.get("format", "pdf").strip().lower()

    if format_param not in ("pdf", "csv", "xlsx", "excel"):
        return jsonify({
            "success": False,
            "message": f"Unsupported export format '{format_param}'. Must be 'pdf', 'csv', or 'xlsx'.",
        }), 400

    query = (
        AcademicResult.query
        .options(joinedload(AcademicResult.course))
        .filter_by(student_id=student.student_id, is_published=True)
    )
    if semester_param is not None:
        query = query.filter_by(semester=semester_param)

    results = query.order_by(AcademicResult.semester.asc(), AcademicResult.course_id.asc()).all()

    if not results:
        return jsonify({
            "success": False,
            "message": "No published records found to export",
        }), 404

    sgpa = calculate_sgpa(results)
    all_published = AcademicResult.query.filter_by(student_id=student.student_id, is_published=True).all()
    cgpa = calculate_cgpa(all_published)
    credits_earned = calculate_credits_earned(results)

    sgpa_str = f"{float(sgpa):.2f}" if sgpa is not None else "N/A"
    cgpa_str = f"{float(cgpa):.2f}" if cgpa is not None else "N/A"

    # Metadata key-value block
    metadata = {
        "Student Name": student.user.name if student.user and student.user.name else "Student",
        "Enrollment No": student.enrollment_no or "N/A",
        "Department": student.department.department_name if student.department else "N/A",
        "Academic Year": student.academic_year or "N/A",
        "Semester": f"Semester {semester_param}" if semester_param else "All Semesters",
    }
    if student.section:
        metadata["Section"] = student.section

    # Summary metrics block
    summary = {
        "Semester GPA (SGPA)": sgpa_str,
        "Cumulative GPA (CGPA)": cgpa_str,
        "Credits Earned": str(credits_earned),
        "Total Courses": len(results),
    }

    # Table columns
    headers = [
        "S.No.",
        "Course Code",
        "Course Name",
        "Credits",
        "Marks",
        "Max Marks",
        "Grade",
        "Points",
        "Status",
        "Remarks",
    ]

    rows = []
    for idx, r in enumerate(results, 1):
        c = r.course
        code = c.course_code if c and c.course_code else f"CRS-{r.course_id}"
        name = c.course_name if c and c.course_name else "Course"
        cr = r.credits if r.credits is not None else (c.credits if c and c.credits is not None else 0)
        marks = f"{float(r.marks_obtained):.1f}" if r.marks_obtained is not None else "N/A"
        max_m = f"{float(r.max_marks):.1f}" if r.max_marks is not None else "100.0"
        grade = r.grade or "N/A"
        gp = f"{float(r.grade_points):.2f}" if r.grade_points is not None else "0.00"
        status = r.status or "PASS"
        remarks = r.remarks or "-"
        rows.append([idx, code, name, cr, marks, max_m, grade, gp, status, remarks])

    sem_slug = f"Sem{semester_param}" if semester_param else "All"
    date_str = datetime.now().strftime("%Y%m%d")
    base_filename = f"Academic_Grade_Card_{student.enrollment_no}_{sem_slug}_{date_str}"

    subtitle_text = f"Official Academic Grade Card — {student.enrollment_no}"
    if semester_param:
        subtitle_text += f" (Semester {semester_param})"

    try:
        stream, mimetype, filename = generate_export(
            format_type=format_param,
            headers=headers,
            rows=rows,
            title="OFFICIAL STUDENT ACADEMIC GRADE CARD",
            subtitle=subtitle_text,
            metadata=metadata,
            summary=summary,
            base_filename=base_filename,
            sheet_name="Grade Card",
            orientation="landscape",
        )
    except ExportValidationError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400
    except ExportRenderingError as exc:
        return jsonify({"success": False, "message": f"Rendering error: {str(exc)}"}), 500

    return send_file(
        stream,
        mimetype=mimetype,
        as_attachment=True,
        download_name=filename,
    )


# ============================================================
# 7. AUTHORIZED RESULT ENTRY (ADMIN / FACULTY)
# ============================================================

@student_academic_bp.post("/admin/entry")
@admin_required
def record_academic_results():
    """
    Authorized endpoint for Admin / Exam Cell to record and publish student results.
    Accepts:
    {
      "exam_id": optional int,
      "results": [
        {
          "student_id": int,
          "course_id": int,
          "offering_id": optional int,
          "academic_year": str,
          "semester": int,
          "credits": int,
          "marks_obtained": float,
          "max_marks": optional float (100.0),
          "grade": optional str,
          "grade_points": optional float,
          "status": optional str,
          "is_published": bool,
          "remarks": optional str
        }
      ]
    }
    """
    payload = request.get_json() or {}
    results_data = payload.get("results", [])

    if not isinstance(results_data, list) or not results_data:
        return jsonify({
            "success": False,
            "message": "results array is required",
        }), 400

    exam_id = payload.get("exam_id")
    recorded = []

    for item in results_data:
        student_id = item.get("student_id")
        course_id = item.get("course_id")
        academic_year = item.get("academic_year")
        semester = item.get("semester")

        if not all([student_id, course_id, academic_year, semester]):
            continue

        student = Student.query.get(student_id)
        course = Course.query.get(course_id)
        if not student or not course:
            continue

        credits = item.get("credits", course.credits or 3)
        marks = item.get("marks_obtained")
        max_marks = item.get("max_marks", 100.0)

        # Calculate or use explicit grade & points
        explicit_grade = item.get("grade")
        explicit_gp = item.get("grade_points")
        grade, gp, status = determine_grade_and_points(
            marks=marks,
            max_marks=max_marks,
            explicit_grade=explicit_grade,
            explicit_grade_points=explicit_gp,
        )

        is_published = bool(item.get("is_published", True))
        published_at = datetime.utcnow() if is_published else None

        # Check existing result
        existing = AcademicResult.query.filter_by(
            student_id=student_id,
            course_id=course_id,
            academic_year=academic_year,
            semester=semester,
        ).first()

        if existing:
            existing.exam_id = exam_id or existing.exam_id
            existing.offering_id = item.get("offering_id", existing.offering_id)
            existing.credits = credits
            existing.marks_obtained = marks
            existing.max_marks = max_marks
            existing.grade = grade
            existing.grade_points = gp
            existing.status = item.get("status", status)
            existing.is_published = is_published
            existing.published_at = published_at or existing.published_at
            existing.remarks = item.get("remarks", existing.remarks)
            recorded.append(existing)
        else:
            new_res = AcademicResult(
                student_id=student_id,
                course_id=course_id,
                offering_id=item.get("offering_id"),
                exam_id=exam_id,
                academic_year=academic_year,
                semester=semester,
                credits=credits,
                marks_obtained=marks,
                max_marks=max_marks,
                grade=grade,
                grade_points=gp,
                status=item.get("status", status),
                is_published=is_published,
                published_at=published_at,
                remarks=item.get("remarks"),
            )
            db.session.add(new_res)
            recorded.append(new_res)

    db.session.commit()

    return jsonify({
        "success": True,
        "message": f"Successfully recorded {len(recorded)} academic result entries",
        "count": len(recorded),
    }), 201
