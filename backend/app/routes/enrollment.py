
import re

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from app.extensions import db
from app.services.activity_service import record_activity
from app.models import Batch, Course, CourseOffering, Department, Enrollment, Student, User
from app.utils.academic_year import (
    canonical_academic_year,
    extract_cohort_start_year,
    format_batch_cohort,
    get_current_academic_session,
    is_batch_cohort,
    is_single_academic_session,
    resolve_offering_academic_year,
)
from app.utils.auth import admin_required, student_required


enrollment_bp = Blueprint(
    "enrollment",
    __name__,
    url_prefix="/api",
)


# ---------------------------------------------------------------------------
# Shared helpers for cohort-based group enrollment
# ---------------------------------------------------------------------------

def _parse_group_request(data):
    """Validate the selected department, cohort, semester, and section."""

    if not isinstance(data, dict):
        return None, "A valid JSON object is required"

    try:
        department_id = int(data.get("department_id"))
        semester = int(data.get("semester"))
    except (TypeError, ValueError):
        return None, "department_id and semester must be valid integers"

    section = data.get("section")
    session_ay = data.get("academic_session") or data.get("session_academic_year")

    if department_id < 1:
        return None, "department_id must be greater than 0"

    if semester < 1:
        return None, "semester must be greater than 0"

    if not isinstance(section, str) or not section.strip():
        return None, "A valid section is required"

    normalized_section = section.strip()

    # 1. Resolve running academic teaching session (e.g. '2026-2027')
    if session_ay and is_single_academic_session(session_ay):
        offering_session = canonical_academic_year(session_ay)
    elif data.get("academic_year") and is_single_academic_session(data.get("academic_year")):
        offering_session = canonical_academic_year(data.get("academic_year"))
    else:
        offering_session = get_current_academic_session()

    # 2. Resolve admission cohort without conflating single-year session with cohort
    raw_cohort = (
        data.get("batch_year")
        or data.get("batch_name")
        or data.get("cohort")
    )
    if not raw_cohort and data.get("academic_year") and not is_single_academic_session(data.get("academic_year")):
        raw_cohort = data.get("academic_year")

    if not raw_cohort or is_single_academic_session(raw_cohort):
        session_start = int(offering_session.split("-")[0])
        derived_start = session_start - ((semester - 1) // 2)
        cohort_start_year = str(derived_start)
        normalized_cohort = format_batch_cohort(cohort_start_year)
    else:
        normalized_cohort = format_batch_cohort(raw_cohort)
        cohort_start_year = extract_cohort_start_year(raw_cohort)

    if not cohort_start_year or not re.match(r"^\d{4}-\d{4}$", normalized_cohort):
        return None, (
            "Cohort must use the format YYYY-YYYY, "
            "for example 2026-2030"
        )

    group = {
        "department_id": department_id,
        "cohort": normalized_cohort,
        "academic_year": normalized_cohort,
        "batch_year": normalized_cohort,
        "cohort_start_year": cohort_start_year,
        "academic_session": offering_session,
        "semester": semester,
        "section": normalized_section,
    }

    return group, None


def _get_group_enrollment_context(group):
    """
    Find active students and existing offerings for the selected cohort.
    Student cohort may be stored in Batch.batch_name or legacy Student.academic_year.
    Course.batch represents the cohort start year. CourseOffering.academic_year
    represents the academic session.
    """
    cohort = group["academic_year"]
    start_year = group["cohort_start_year"]
    cohort_clean = cohort.replace(" ", "")

    students = (
        Student.query
        .join(Student.user)
        .outerjoin(Student.batch)
        .filter(
            Student.department_id == group["department_id"],
            Student.semester == group["semester"],
            Student.section == group["section"],
            db.or_(
                Batch.batch_name == cohort,
                Batch.batch_name == start_year,
                db.func.replace(Student.academic_year, " ", "") == cohort_clean,
                db.func.replace(Student.academic_year, " ", "") == f"{start_year}-{int(start_year)+4}",
            ),
            Student.user.has(is_active=True),
        )
        .order_by(Student.student_id.asc())
        .all()
    )

    offerings = (
        CourseOffering.query
        .join(CourseOffering.course)
        .filter(
            Course.department_id == group["department_id"],
            Course.semester == group["semester"],
            Course.is_active.is_(True),
            db.or_(
                Course.batch == group["cohort_start_year"],
                Course.batch.like(f"{group['cohort_start_year']}%"),
            ),
            CourseOffering.semester == group["semester"],
            CourseOffering.section == group["section"],
            CourseOffering.academic_year == group["academic_session"],
        )
        .order_by(Course.course_code.asc(), CourseOffering.offering_id.asc())
        .all()
    )

    # Identify active courses for the cohort that have no valid offering
    # for the selected semester and section.
    active_courses = (
        Course.query
        .filter(
            Course.department_id == group["department_id"],
            Course.semester == group["semester"],
            Course.is_active.is_(True),
            db.or_(
                Course.batch == group["cohort_start_year"],
                Course.batch.like(f"{group['cohort_start_year']}%"),
            ),
        )
        .order_by(Course.course_code.asc())
        .all()
    )

    offered_course_ids = {offering.course_id for offering in offerings}

    courses_without_offerings = [
        {
            "course_id": course.course_id,
            "course_code": course.course_code,
            "course_name": course.course_name,
        }
        for course in active_courses
        if course.course_id not in offered_course_ids
    ]

    return students, offerings, courses_without_offerings


def _parse_offering_ids(data, required=True):
    """Validate selected offering IDs.

    For preview requests, a missing or empty list means all matching
    offerings. For bulk enrollment, at least one offering is required.
    """
    offering_ids = data.get("offering_ids")

    # Preview mode: no selection means preview all matching offerings.
    if not required and (
        offering_ids is None or offering_ids == []
    ):
        return [], None

    # Bulk enrollment requires at least one selected offering.
    if not isinstance(offering_ids, list) or not offering_ids:
        return None, "Select at least one course offering"

    parsed_ids = []

    for value in offering_ids:
        if isinstance(value, bool):
            return None, "Every offering ID must be a positive integer"

        try:
            offering_id = int(value)
        except (TypeError, ValueError):
            return None, "Every offering ID must be a positive integer"

        if offering_id < 1:
            return None, "Every offering ID must be a positive integer"

        parsed_ids.append(offering_id)

    if len(parsed_ids) != len(set(parsed_ids)):
        return None, "Duplicate offering IDs are not allowed"

    return parsed_ids, None



def _offering_to_dict(offering):
    course = offering.course

    return {
        "offering_id": offering.offering_id,
        "course_id": course.course_id,
        "course_code": course.course_code,
        "course_name": course.course_name,
        "semester": offering.semester,
        "section": offering.section,
        "academic_year": offering.academic_year,
        "room": offering.room,
    }


def _existing_enrollment_pairs(student_ids, offering_ids):
    """Return existing (student_id, offering_id) pairs for a group."""

    if not student_ids or not offering_ids:
        return set()

    rows = db.session.execute(
        select(
            Enrollment.student_id,
            Enrollment.offering_id,
        ).where(
            Enrollment.student_id.in_(student_ids),
            Enrollment.offering_id.in_(offering_ids),
        )
    ).all()

    return {(row[0], row[1]) for row in rows}


# ---------------------------------------------------------------------------
# Admin: list existing enrollment records
# ---------------------------------------------------------------------------

@enrollment_bp.get("/admin/enrollments")
@admin_required
def get_enrollments():
    enrollments = (
        Enrollment.query
        .options(
            joinedload(Enrollment.student).joinedload(Student.user),
            joinedload(Enrollment.student).joinedload(Student.department),
            joinedload(Enrollment.student).joinedload(Student.batch),
            joinedload(Enrollment.offering).joinedload(CourseOffering.course),
        )
        .order_by(Enrollment.enrollment_id.desc())
        .all()
    )

    data = [
        {
            "enrollment_id": enrollment.enrollment_id,
            "student_id": enrollment.student_id,
            "student_name": (
                enrollment.student.user.name
                if enrollment.student and enrollment.student.user
                else None
            ),
            "enrollment_no": (
                enrollment.student.enrollment_no
                if enrollment.student
                else None
            ),
            "department_id": (
                enrollment.student.department_id
                if enrollment.student
                else None
            ),
            "department_code": (
                enrollment.student.department.department_code
                if enrollment.student and enrollment.student.department
                else None
            ),
            "department_name": (
                enrollment.student.department.department_name
                if enrollment.student and enrollment.student.department
                else None
            ),
            "batch_name": (
                enrollment.student.batch.batch_name
                if enrollment.student and enrollment.student.batch
                else (enrollment.student.academic_year if enrollment.student else None)
            ),
            "academic_year": (
                resolve_offering_academic_year(
                    enrollment.offering.academic_year,
                    enrollment.offering.semester,
                )
                if enrollment.offering
                else (enrollment.student.academic_year if enrollment.student else None)
            ),
            "semester": (
                enrollment.offering.semester
                if enrollment.offering
                else (enrollment.student.semester if enrollment.student else None)
            ),
            "section": (
                enrollment.offering.section
                if enrollment.offering
                else (enrollment.student.section if enrollment.student else None)
            ),
            "course_id": (
                enrollment.offering.course.course_id
                if enrollment.offering and enrollment.offering.course
                else None
            ),
            "course_code": (
                enrollment.offering.course.course_code
                if enrollment.offering and enrollment.offering.course
                else None
            ),
            "course_name": (
                enrollment.offering.course.course_name
                if enrollment.offering and enrollment.offering.course
                else None
            ),
            "credits": (
                enrollment.offering.course.credits
                if enrollment.offering and enrollment.offering.course
                else None
            ),
            "offering_id": enrollment.offering_id,
            "status": enrollment.status,
            "enrolled_at": (
                enrollment.enrolled_at.isoformat()
                if enrollment.enrolled_at
                else None
            ),
        }
        for enrollment in enrollments
    ]

    return jsonify({
        "success": True,
        "data": data,
    }), 200


# ---------------------------------------------------------------------------
# Admin: summary statistics and student group aggregation
# ---------------------------------------------------------------------------

@enrollment_bp.get("/admin/enrollments/summary")
@admin_required
def get_enrollments_summary():
    """Return summary statistics and student group breakdown for Course Enrollments."""
    from collections import defaultdict

    total_enrollments = Enrollment.query.count()
    active_enrollments = Enrollment.query.filter_by(status="ACTIVE").count()

    courses = Course.query.filter_by(is_active=True).all()
    offerings = (
        CourseOffering.query
        .options(joinedload(CourseOffering.course))
        .all()
    )
    students = (
        Student.query
        .join(Student.user)
        .filter(User.is_active.is_(True))
        .options(
            joinedload(Student.user),
            joinedload(Student.department),
            joinedload(Student.batch),
        )
        .all()
    )

    enrollment_pairs = (
        db.session.query(Enrollment.student_id, Enrollment.offering_id)
        .filter(Enrollment.status == "ACTIVE")
        .all()
    )
    student_enrolled_offerings = defaultdict(set)
    for s_id, o_id in enrollment_pairs:
        student_enrolled_offerings[s_id].add(o_id)

    grouped = defaultdict(list)
    for s in students:
        batch_val = s.batch.batch_name if s.batch else (s.academic_year or "")
        start_year = extract_cohort_start_year(batch_val) or (batch_val[:4] if len(batch_val) >= 4 else "2024")
        grouped[(s.department_id, start_year, s.semester, s.section)].append(s)

    group_list = []
    total_pending = 0

    for (dept_id, start_year, sem, sec), s_list in sorted(
        grouped.items(),
        key=lambda x: (x[0][0], x[0][2], x[0][3], x[0][1]),
    ):
        dept = s_list[0].department if s_list else None
        dept_code = dept.department_code if dept else "CSE"
        dept_name = dept.department_name if dept else "Computer Science Engineering"

        grp_offerings = [
            o for o in offerings
            if o.course and o.course.department_id == dept_id and o.semester == sem and o.section == sec
            and (not start_year or not o.course.batch or o.course.batch.startswith(start_year))
        ]
        grp_offering_ids = set(o.offering_id for o in grp_offerings)

        grp_courses = [
            c for c in courses
            if c.department_id == dept_id and c.semester == sem and (
                not start_year or (c.batch and c.batch.startswith(start_year))
            )
        ]

        enrolled_count = 0
        for s in s_list:
            enrolled_offs = student_enrolled_offerings.get(s.student_id, set())
            if grp_offering_ids and (enrolled_offs & grp_offering_ids):
                enrolled_count += 1

        pending_count = max(0, len(s_list) - enrolled_count)
        total_pending += pending_count

        courses_count = len(grp_courses) or len(grp_offerings)
        status = (
            "Complete"
            if (enrolled_count >= len(s_list) and len(s_list) > 0 and courses_count > 0)
            else "Incomplete"
        )

        active_offering = next(
            (
                o for o in grp_offerings
                if (o.academic_year and canonical_academic_year(o.academic_year) == get_current_academic_session())
                or o.faculty_id is not None
            ),
            grp_offerings[0] if grp_offerings else None,
        )
        raw_ay = (
            active_offering.academic_year
            if active_offering and active_offering.academic_year
            else (s_list[0].academic_year if s_list and s_list[0].academic_year else None)
        )
        if raw_ay and is_single_academic_session(raw_ay):
            ay_display = canonical_academic_year(raw_ay)
        else:
            ay_display = None

        group_list.append({
            "group_id": f"{dept_code}-{start_year}-S{sem}-{sec}",
            "department_id": dept_id,
            "department_code": dept_code,
            "department_name": dept_name,
            "batch": start_year,
            "cohort": format_batch_cohort(start_year),
            "batch_name": f"{start_year} Batch",
            "academic_year": ay_display,
            "semester": sem,
            "section": sec,
            "total_students": len(s_list),
            "enrolled_students": enrolled_count,
            "courses_count": courses_count,
            "pending_students": pending_count,
            "status": status,
        })

    return jsonify({
        "success": True,
        "data": {
            "total_enrollments": total_enrollments,
            "active_enrollments": active_enrollments,
            "pending_enrollments": total_pending or max(0, total_enrollments - active_enrollments),
            "total_groups": len(group_list),
            "groups": group_list,
        },
    }), 200


# ---------------------------------------------------------------------------
# Admin: delete an existing enrollment record
# ---------------------------------------------------------------------------

@enrollment_bp.delete("/admin/enrollments/<int:enrollment_id>")
@admin_required
def delete_enrollment(enrollment_id):
    enrollment = db.session.get(Enrollment, enrollment_id)

    if not enrollment:
        return jsonify({
            "success": False,
            "message": "Enrollment not found",
        }), 404

    try:
        db.session.delete(enrollment)
        db.session.commit()
        record_activity(
            action_type="ENROLLMENT_DELETED",
            description=f"Deleted enrollment record #{enrollment_id}",
            entity_type="Enrollment",
            entity_id=str(enrollment_id),
        )
    except Exception:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "Unable to delete the enrollment",
        }), 500

    return jsonify({
        "success": True,
        "message": "Enrollment removed successfully",
    }), 200


# ---------------------------------------------------------------------------
# Admin: preview cohort enrollment without writing to the database
# ---------------------------------------------------------------------------

@enrollment_bp.post("/admin/enrollments/group-preview")
@admin_required
def preview_group_enrollment():
    data = request.get_json(silent=True)
    group, error = _parse_group_request(data)

    if error:
        return jsonify({
            "success": False,
            "message": error,
        }), 400

    students, available_offerings, _ = (
        _get_group_enrollment_context(group)
    )

    # Retrieve every active course for the selected department,
    # cohort, semester, and section's course group.
    active_courses = (
        Course.query
        .filter(
            Course.department_id == group["department_id"],
            Course.semester == group["semester"],
            Course.is_active.is_(True),
            db.or_(
                Course.batch == group["cohort_start_year"],
                Course.batch.like(f"{group['cohort_start_year']}%"),
            ),
        )
        .order_by(Course.course_code.asc())
        .all()
    )

    # Index matching offerings by course. Preserve multiple offerings
    # in the response so existing data isn't silently hidden.
    offerings_by_course = {}
    for offering in available_offerings:
        offerings_by_course.setdefault(
            offering.course_id, []
        ).append(offering)

    courses = []
    for course in active_courses:
        matching = offerings_by_course.get(course.course_id, [])

        courses.append({
            "course_id": course.course_id,
            "course_code": course.course_code,
            "course_name": course.course_name,
            "credits": course.credits or 3,
            "offerings": [
                _offering_to_dict(offering)
                for offering in matching
            ],
            "offering_id": (
                matching[0].offering_id if matching else None
            ),
            "has_offering": bool(matching),
            "faculty_assigned": any(
                offering.faculty_id is not None
                for offering in matching
            ),
        })

    # Keep support for older clients that pass offering_ids.
    available_by_id = {
        offering.offering_id: offering
        for offering in available_offerings
    }

    requested_ids, error = _parse_offering_ids(
        data, required=False
    )

    if error:
        return jsonify({
            "success": False,
            "message": error,
        }), 400

    if requested_ids:
        invalid_ids = [
            offering_id
            for offering_id in requested_ids
            if offering_id not in available_by_id
        ]

        if invalid_ids:
            return jsonify({
                "success": False,
                "message": (
                    "One or more selected offerings do not belong "
                    "to the selected cohort, semester, and section"
                ),
                "invalid_offering_ids": invalid_ids,
            }), 400

        selected_offerings = [
            available_by_id[offering_id]
            for offering_id in requested_ids
        ]
    else:
        selected_offerings = available_offerings

    student_ids = [
        student.student_id for student in students
    ]
    offering_ids = [
        offering.offering_id
        for offering in selected_offerings
    ]

    existing_pairs = _existing_enrollment_pairs(
        student_ids,
        offering_ids,
    )

    total_pairs = len(student_ids) * len(offering_ids)
    already_enrolled = len(existing_pairs)

    courses_without_offerings = [
        {
            "course_id": course["course_id"],
            "course_code": course["course_code"],
            "course_name": course["course_name"],
        }
        for course in courses
        if not course["has_offering"]
    ]

    students_data = [
        {
            "student_id": s.student_id,
            "user_id": s.user_id,
            "name": s.user.name if s.user else f"Student #{s.student_id}",
            "enrollment_no": s.enrollment_no,
            "email": s.user.email if s.user else "",
            "is_enrolled": any((s.student_id, oid) in existing_pairs for oid in offering_ids),
            "enrolled_offerings_count": len([oid for oid in offering_ids if (s.student_id, oid) in existing_pairs]),
            "total_offerings_count": len(offering_ids),
        }
        for s in students
    ]
    distinct_already_enrolled = len([s for s in students_data if s["is_enrolled"]])
    pending_students_count = max(0, len(students) - distinct_already_enrolled)

    return jsonify({
        "success": True,
        "message": "Enrollment preview generated successfully",
        "data": {
            **group,
            "eligible_students": len(students),
            "already_enrolled": distinct_already_enrolled,
            "pending_enrollment": pending_students_count,
            "available_courses": len(courses),
            "active_courses": len(active_courses),
            "available_offerings": len(available_offerings),
            "matched_offerings": len(selected_offerings),
            "total_matching_enrollment_pairs": total_pairs,
            "to_create": total_pairs - already_enrolled,
            "courses": courses,
            "courses_without_offerings": courses_without_offerings,
            "offerings": [
                _offering_to_dict(offering)
                for offering in selected_offerings
            ],
            "students": students_data,
        },
    }), 200



# ---------------------------------------------------------------------------
# Admin: enroll the selected group in selected offerings atomically
# ---------------------------------------------------------------------------

@enrollment_bp.post("/admin/enrollments/group-bulk")
@admin_required
def bulk_enroll_group():
    data = request.get_json(silent=True)
    group, error = _parse_group_request(data)

    if error:
        return jsonify({
            "success": False,
            "message": error,
        }), 400

    students, _, _ = _get_group_enrollment_context(group)

    # Only active courses belonging to the selected cohort and group.
    courses = (
        Course.query
        .filter(
            Course.department_id == group["department_id"],
            Course.semester == group["semester"],
            Course.is_active.is_(True),
            db.or_(
                Course.batch == group["cohort_start_year"],
                Course.batch.like(f"{group['cohort_start_year']}%"),
            ),
        )
        .order_by(Course.course_code.asc())
        .all()
    )

    # Optional course_ids filter from Step 2
    selected_course_ids = data.get("course_ids")
    if selected_course_ids and isinstance(selected_course_ids, list):
        try:
            cid_set = {int(cid) for cid in selected_course_ids}
            courses = [c for c in courses if c.course_id in cid_set]
        except (TypeError, ValueError):
            pass

    if not courses:
        return jsonify({
            "success": False,
            "message": "No active courses were found for this group.",
        }), 400

    # Optional student_ids filter from Step 3
    selected_student_ids = data.get("student_ids")
    if selected_student_ids and isinstance(selected_student_ids, list):
        try:
            sid_set = {int(sid) for sid in selected_student_ids}
            students = [s for s in students if s.student_id in sid_set]
        except (TypeError, ValueError):
            pass

    if not students:
        return jsonify({
            "success": False,
            "message": "No eligible active students were found.",
            "data": {
                **group,
                "eligible_students": 0,
                "matched_offerings": 0,
                "created_offerings": 0,
                "created": 0,
                "already_enrolled": 0,
            },
        }), 200

    student_ids = [student.student_id for student in students]
    created_offerings = []
    matched_offerings = []

    # New offerings use the academic session convention.
    session = canonical_academic_year(group.get("academic_session") or get_current_academic_session())

    try:
        for course in courses:
            existing = (
                CourseOffering.query
                .filter(
                    CourseOffering.course_id == course.course_id,
                    CourseOffering.academic_year == session,
                    CourseOffering.semester == group["semester"],
                    CourseOffering.section == group["section"],
                )
                .order_by(CourseOffering.offering_id.asc())
                .first()
            )

            if existing:
                # Reuse the existing offering without changing its
                # academic session, room, or faculty assignment.
                offering = existing
            else:
                offering = CourseOffering(
                    course_id=course.course_id,
                    faculty_id=None,
                    academic_year=session,
                    semester=group["semester"],
                    section=group["section"],
                    room=None,
                )
                db.session.add(offering)
                db.session.flush()
                created_offerings.append(offering)

            matched_offerings.append(offering)

        # Optional offering_ids filter
        selected_offering_ids = data.get("offering_ids")
        if selected_offering_ids and isinstance(selected_offering_ids, list):
            try:
                oid_set = {int(oid) for oid in selected_offering_ids}
                matched_offerings = [o for o in matched_offerings if o.offering_id in oid_set]
            except (TypeError, ValueError):
                pass

        offering_ids = [
            offering.offering_id for offering in matched_offerings
        ]

        existing_pairs = _existing_enrollment_pairs(
            student_ids,
            offering_ids,
        )

        rows = [
            {
                "student_id": student_id,
                "offering_id": offering_id,
                "status": "ACTIVE",
            }
            for student_id in student_ids
            for offering_id in offering_ids
            if (student_id, offering_id) not in existing_pairs
        ]

        if rows:
            db.session.execute(db.insert(Enrollment), rows)

        db.session.commit()

        record_activity(
            action_type="ENROLLMENT_BULK_CREATED",
            description=f"Bulk enrolled {len(rows)} students into {len(offering_ids)} course offerings",
            entity_type="Enrollment",
            details={"created": len(rows), "offerings": len(offering_ids)},
        )

    except IntegrityError:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": (
                "A database conflict occurred. "
                "The bulk enrollment transaction was rolled back."
            ),
        }), 409

    except Exception:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": (
                "Bulk enrollment failed. "
                "The transaction was rolled back."
            ),
        }), 500

    return jsonify({
        "success": True,
        "message": "Group bulk enrollment completed successfully.",
        "data": {
            **group,
            "eligible_students": len(student_ids),
            "matched_offerings": len(matched_offerings),
            "created_offerings": len(created_offerings),
            "created": len(rows),
            "already_enrolled": len(existing_pairs),
            "offering_ids": offering_ids,
        },
    }), 201 if rows or created_offerings else 200
