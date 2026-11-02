from datetime import datetime, timezone

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload, selectinload

def format_utc_iso(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.isoformat() + "Z"
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

from app.extensions import bcrypt, db
from app.models import (
    ActivityLog,
    AttendanceRecord,
    AttendanceSession,
    Batch,
    Course,
    CourseOffering,
    Department,
    Enrollment,
    Faculty,
    FaceProfile,
    Student,
    TimetableEntry,
    User,
)
from app.services.activity_service import record_activity, serialize_activity_log
from app.services.auth_service import create_user
from app.services.face_identity_service import (
    cleanup_obsolete_face_profiles,
    detect_suspected_duplicate_students,
    reconcile_duplicate_students,
    remove_student_face_profile,
)
from app.utils.auth import admin_required
from app.utils.academic_year import (
    canonical_academic_year,
    extract_cohort_start_year,
    format_batch_cohort,
    get_available_academic_sessions,
    get_current_academic_session,
    is_batch_cohort,
    is_single_academic_session,
    resolve_offering_academic_year,
    resolve_student_academic_info,
    set_current_academic_session,
)


admin_bp = Blueprint(
    "admin",
    __name__,
    url_prefix="/api/admin",
)

# ADMIN DASHBOARD

@admin_bp.get("/dashboard")
@admin_required
def get_admin_dashboard():
    total_students = Student.query.count()
    total_faculty = Faculty.query.count()
    total_courses = Course.query.count()

    total_attendance_records = AttendanceRecord.query.count()

    present_count = AttendanceRecord.query.filter_by(
        status="PRESENT"
    ).count()

    absent_count = AttendanceRecord.query.filter_by(
        status="ABSENT"
    ).count()

    recent_logs = (
        ActivityLog.query.order_by(
            ActivityLog.created_at.desc(),
            ActivityLog.id.desc(),
        )
        .limit(10)
        .all()
    )

    return jsonify({
        "success": True,
        "data": {
            "total_students": total_students,
            "total_faculty": total_faculty,
            "total_courses": total_courses,
            "attendance_summary": {
                "present": present_count,
                "absent": absent_count,
                "total_records": total_attendance_records,
            },
            "recent_activity": [serialize_activity_log(log) for log in recent_logs],
        },
    }), 200


# RECENT ACTIVITY & AUDIT LOGS

@admin_bp.get("/activity/recent")
@admin_required
def get_recent_activity():
    try:
        limit = int(request.args.get("limit", 10))
    except (ValueError, TypeError):
        limit = 10
    limit = max(1, min(limit, 50))

    logs = (
        ActivityLog.query.order_by(
            ActivityLog.created_at.desc(),
            ActivityLog.id.desc(),
        )
        .limit(limit)
        .all()
    )

    return jsonify({
        "success": True,
        "data": [serialize_activity_log(log) for log in logs],
    }), 200


@admin_bp.get("/activity")
@admin_required
def get_activity_logs():
    try:
        page = max(1, int(request.args.get("page", 1)))
    except (ValueError, TypeError):
        page = 1

    try:
        limit = max(1, min(int(request.args.get("limit", 15)), 100))
    except (ValueError, TypeError):
        limit = 15

    query = ActivityLog.query

    action_type = request.args.get("action_type")
    if action_type:
        query = query.filter(ActivityLog.action_type == action_type.strip().upper())

    entity_type = request.args.get("entity_type")
    if entity_type:
        query = query.filter(ActivityLog.entity_type == entity_type.strip())

    total = query.count()
    logs = (
        query.order_by(
            ActivityLog.created_at.desc(),
            ActivityLog.id.desc(),
        )
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return jsonify({
        "success": True,
        "data": [serialize_activity_log(log) for log in logs],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": max(1, (total + limit - 1) // limit),
        },
    }), 200

# BATCH MANAGEMENT

@admin_bp.get("/batches")
@admin_required
def get_batches():
    batches = Batch.query.order_by(Batch.batch_name.asc()).all()

    return jsonify({
        "success": True,
        "data": [
            {
                "batch_id": batch.batch_id,
                "batch_name": format_batch_cohort(batch.batch_name),
                "raw_name": batch.batch_name,
                "is_active": batch.is_active,
            }
            for batch in batches
        ],
    }), 200


@admin_bp.post("/batches")
@admin_required
def create_batch():
    data = request.get_json(silent=True) or {}
    batch_name = str(data.get("batch_name") or "").strip()

    if not batch_name:
        return jsonify({
            "success": False,
            "message": "Batch name is required",
        }), 400

    cohort_name = format_batch_cohort(batch_name)

    if len(cohort_name) > 20:
        return jsonify({
            "success": False,
            "message": "Batch name cannot exceed 20 characters",
        }), 400

    if Batch.query.filter(
        db.or_(Batch.batch_name == cohort_name, Batch.batch_name == batch_name)
    ).first():
        return jsonify({
            "success": False,
            "message": "This batch already exists",
        }), 409

    batch = Batch(batch_name=cohort_name)

    try:
        db.session.add(batch)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "This batch already exists",
        }), 409

    return jsonify({
        "success": True,
        "message": "Batch created successfully",
        "data": {
            "batch_id": batch.batch_id,
            "batch_name": format_batch_cohort(batch.batch_name),
            "is_active": batch.is_active,
        },
    }), 201


# ACADEMIC SESSION CONFIGURATION

@admin_bp.get("/academic-session")
@admin_required
def get_academic_session_config():
    return jsonify({
        "success": True,
        "data": {
            "current_academic_year": get_current_academic_session(),
            "available_sessions": get_available_academic_sessions(),
        },
    }), 200


@admin_bp.post("/academic-session")
@admin_bp.put("/academic-session")
@admin_required
def update_academic_session_config():
    data = request.get_json(silent=True) or {}
    academic_year = data.get("academic_year")
    if not academic_year:
        return jsonify({
            "success": False,
            "message": "academic_year is required",
        }), 400

    try:
        saved_session = set_current_academic_session(academic_year)
        return jsonify({
            "success": True,
            "message": f"Institutional academic session set to {saved_session}",
            "data": {
                "current_academic_year": saved_session,
                "available_sessions": get_available_academic_sessions(),
            },
        }), 200
    except ValueError as err:
        return jsonify({
            "success": False,
            "message": str(err),
        }), 400


# ADMIN PROFILE

def serialize_admin_profile(user):
    return {
        "user_id": user.user_id,
        "name": user.name,
        "email": user.email,
        "phone": getattr(user, "phone", "") or "",
        "designation": getattr(user, "designation", "") or "System Administrator",
        "department": getattr(user, "department", "") or "Administration",
        "role": user.role,
        "is_active": getattr(user, "is_active", True),
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None,
        "last_login": format_utc_iso(getattr(user, "last_login", None)),
        "stats": {
            "total_users": User.query.count(),
            "total_students": Student.query.count(),
            "total_faculty": Faculty.query.count(),
            "total_courses": Course.query.count(),
            "total_sessions": AttendanceSession.query.count(),
        },
    }


@admin_bp.get("/profile")
@admin_required
def get_admin_profile():
    user_id = get_jwt_identity()

    user = db.session.get(User, int(user_id))

    if not user:
        return jsonify({
            "success": False,
            "message": "Admin user not found",
        }), 404

    if user.role != "ADMIN":
        return jsonify({
            "success": False,
            "message": "Access forbidden",
        }), 403

    return jsonify({
        "success": True,
        "data": serialize_admin_profile(user),
    }), 200


@admin_bp.patch("/profile")
@admin_required
def update_admin_profile():
    user_id = get_jwt_identity()

    user = db.session.get(User, int(user_id))

    if not user:
        return jsonify({
            "success": False,
            "message": "Admin user not found",
        }), 404

    if user.role != "ADMIN":
        return jsonify({
            "success": False,
            "message": "Access forbidden",
        }), 403

    data = request.get_json(silent=True) or {}

    if not data:
        return jsonify({
            "success": False,
            "message": "No fields provided for update",
        }), 400

    forbidden_fields = {"role", "user_id"}

    if forbidden_fields.intersection(data.keys()):
        return jsonify({
            "success": False,
            "message": "Role and user_id cannot be updated through admin profile",
        }), 400

    # -------------------------
    # Name
    # -------------------------

    if "name" in data and data["name"] is not None:
        name = str(data["name"]).strip()

        if not name:
            return jsonify({
                "success": False,
                "message": "Name cannot be empty",
            }), 400

        user.name = name

    # -------------------------
    # Email
    # -------------------------

    if "email" in data and data["email"] is not None:
        email = str(data["email"]).lower().strip()

        if not email:
            return jsonify({
                "success": False,
                "message": "Email cannot be empty",
            }), 400

        existing_user = User.query.filter(
            User.email == email,
            User.user_id != user.user_id,
        ).first()

        if existing_user:
            return jsonify({
                "success": False,
                "message": "Email already exists",
            }), 409

        user.email = email

    # -------------------------
    # Phone, Designation, Dept
    # -------------------------

    if "phone" in data:
        user.phone = str(data["phone"]).strip() if data["phone"] is not None else None

    if "designation" in data and data["designation"] is not None:
        user.designation = str(data["designation"]).strip()

    if "department" in data and data["department"] is not None:
        user.department = str(data["department"]).strip()

    # -------------------------
    # Password
    # -------------------------

    if "password" in data and data["password"]:
        password = str(data["password"])

        if len(password) < 8:
            return jsonify({
                "success": False,
                "message": "Password must be at least 8 characters",
            }), 400

        current_password = data.get("current_password")
        if current_password:
            if not bcrypt.check_password_hash(user.password_hash, str(current_password)):
                return jsonify({
                    "success": False,
                    "message": "Current password is incorrect",
                }), 400

        user.password_hash = bcrypt.generate_password_hash(
            password
        ).decode("utf-8")

    try:
        db.session.commit()

    except IntegrityError:
        db.session.rollback()

        return jsonify({
            "success": False,
            "message": (
                "Admin profile could not be updated "
                "because of a database constraint"
            ),
        }), 409

    except Exception:
        db.session.rollback()

        return jsonify({
            "success": False,
            "message": "Admin profile could not be updated",
        }), 500

    db.session.refresh(user)

    return jsonify({
        "success": True,
        "message": "Admin profile updated successfully",
        "data": serialize_admin_profile(user),
    }), 200


@admin_bp.post("/change-password")
@admin_required
def change_admin_password():
    user_id = get_jwt_identity()

    user = db.session.get(User, int(user_id))

    if not user:
        return jsonify({
            "success": False,
            "message": "Admin user not found",
        }), 404

    if user.role != "ADMIN":
        return jsonify({
            "success": False,
            "message": "Access forbidden",
        }), 403

    data = request.get_json(silent=True) or {}
    current_password = data.get("current_password")
    new_password = data.get("new_password")
    confirm_password = data.get("confirm_password")

    if not current_password or not new_password:
        return jsonify({
            "success": False,
            "message": "Current password and new password are required",
        }), 400

    if len(str(new_password)) < 8:
        return jsonify({
            "success": False,
            "message": "New password must be at least 8 characters",
        }), 400

    if confirm_password and str(new_password) != str(confirm_password):
        return jsonify({
            "success": False,
            "message": "New password and confirmation do not match",
        }), 400

    if not bcrypt.check_password_hash(user.password_hash, str(current_password)):
        return jsonify({
            "success": False,
            "message": "Current password is incorrect",
        }), 400

    user.password_hash = bcrypt.generate_password_hash(str(new_password)).decode("utf-8")
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Password changed successfully",
    }), 200

# ============================================================
# DEPARTMENT MANAGEMENT
# ============================================================

@admin_bp.get("/departments")
@admin_required
def get_departments():
    departments = (
        Department.query
        .order_by(Department.department_id.asc())
        .all()
    )

    data = []

    for department in departments:
        faculty_count = Faculty.query.filter_by(
            department_id=department.department_id
        ).count()

        student_count = Student.query.filter_by(
            department_id=department.department_id
        ).count()

        course_count = Course.query.filter_by(
            department_id=department.department_id
        ).count()

        head_faculty = department.head_faculty

        data.append({
            "department_id": department.department_id,
            "department_name": department.department_name,
            "department_code": department.department_code,
            "head_faculty_id": department.head_faculty_id,
            "head_name": (
                head_faculty.user.name
                if head_faculty and head_faculty.user
                else None
            ),
            "head_email": (
                head_faculty.user.email
                if head_faculty and head_faculty.user
                else None
            ),
            "head_employee_id": (
                head_faculty.employee_id
                if head_faculty
                else None
            ),
            "faculty_count": faculty_count,
            "student_count": student_count,
            "course_count": course_count,
            "is_active": department.is_active,
        })

    return jsonify({
        "success": True,
        "data": data,
        "summary": {
            "total_departments": len(departments),
            "active_departments": sum(1 for d in departments if d.is_active),
            "total_faculty": Faculty.query.count(),
            "total_courses": Course.query.count(),
        },
    }), 200


@admin_bp.post("/departments")
@admin_required
def create_department():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "success": False,
            "message": "A valid JSON object is required",
        }), 400

    name = data.get("department_name")
    code = data.get("department_code")

    if not isinstance(name, str) or not name.strip():
        return jsonify({
            "success": False,
            "message": "Department name is required",
        }), 400

    if not isinstance(code, str) or not code.strip():
        return jsonify({
            "success": False,
            "message": "Department code is required",
        }), 400

    name = name.strip()
    code = code.strip().upper()

    if len(name) > 100:
        return jsonify({
            "success": False,
            "message": "Department name must not exceed 100 characters",
        }), 400

    if len(code) > 20:
        return jsonify({
            "success": False,
            "message": "Department code must not exceed 20 characters",
        }), 400

    duplicate = Department.query.filter(
        db.func.upper(Department.department_code) == code
    ).first()

    if duplicate:
        return jsonify({
            "success": False,
            "message": "Department code already exists",
        }), 409

    department = Department(
        department_name=name,
        department_code=code,
    )

    try:
        db.session.add(department)
        db.session.commit()
        record_activity(
            action_type="DEPARTMENT_CREATED",
            description=f"Created department {department.department_name} ({department.department_code})",
            entity_type="Department",
            entity_id=str(department.department_id),
            details={"name": department.department_name, "code": department.department_code},
        )
    except IntegrityError:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "Department could not be created; check for duplicate values",
        }), 409

    return jsonify({
        "success": True,
        "message": "Department created successfully",
        "data": {
            "department_id": department.department_id,
            "department_name": department.department_name,
            "department_code": department.department_code,
        },
    }), 201


@admin_bp.patch("/departments/<int:department_id>")
@admin_required
def update_department(department_id):
    department = db.session.get(Department, department_id)

    if department is None:
        return jsonify({
            "success": False,
            "message": "Department not found",
        }), 404

    data = request.get_json(silent=True)

    if not isinstance(data, dict) or not data:
        return jsonify({
            "success": False,
            "message": "Provide department_name or department_code",
        }), 400

    if "department_name" in data:
        name = data["department_name"]

        if not isinstance(name, str) or not name.strip():
            return jsonify({
                "success": False,
                "message": "Department name must not be empty",
            }), 400

        name = name.strip()

        if len(name) > 100:
            return jsonify({
                "success": False,
                "message": "Department name must not exceed 100 characters",
            }), 400

        department.department_name = name

    if "department_code" in data:
        code = data["department_code"]

        if not isinstance(code, str) or not code.strip():
            return jsonify({
                "success": False,
                "message": "Department code must not be empty",
            }), 400

        code = code.strip().upper()

        if len(code) > 20:
            return jsonify({
                "success": False,
                "message": "Department code must not exceed 20 characters",
            }), 400

        duplicate = Department.query.filter(
            db.func.upper(Department.department_code) == code,
            Department.department_id != department_id,
        ).first()

        if duplicate:
            return jsonify({
                "success": False,
                "message": "Department code already exists",
            }), 409

        department.department_code = code

    # -------------------------
    # Department status
    # -------------------------

    if "is_active" in data:
        if not isinstance(data["is_active"], bool):
            return jsonify({
                "success": False,
                "message": "is_active must be a boolean",
            }), 400

        department.is_active = data["is_active"]

    # -------------------------
    # Head of Department
    # -------------------------

    if "head_faculty_id" in data:
        value = data["head_faculty_id"]

        # null or an empty value removes the current HOD.
        if value is None or value == "":
            department.head_faculty_id = None
        else:
            try:
                head_faculty_id = int(value)
            except (TypeError, ValueError):
                return jsonify({
                    "success": False,
                    "message": "head_faculty_id must be an integer or null",
                }), 400

            head_faculty = db.session.get(
                Faculty,
                head_faculty_id,
            )

            if not head_faculty:
                return jsonify({
                    "success": False,
                    "message": "Faculty member not found",
                }), 404

            if head_faculty.department_id != department.department_id:
                return jsonify({
                    "success": False,
                    "message": (
                        "HOD must belong to the same department"
                    ),
                }), 400

            if not head_faculty.user or not head_faculty.user.is_active:
                return jsonify({
                    "success": False,
                    "message": "HOD must have an active user account",
                }), 400

            department.head_faculty_id = head_faculty.faculty_id

    try:
        db.session.commit()
        record_activity(
            action_type="DEPARTMENT_UPDATED",
            description=f"Updated department {department.department_name} ({department.department_code})",
            entity_type="Department",
            entity_id=str(department.department_id),
            details={"name": department.department_name, "code": department.department_code},
        )
    except IntegrityError:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "Department could not be updated; check for duplicate values",
        }), 409

    return jsonify({
        "success": True,
        "message": "Department updated successfully",
        "data": {
            "department_id": department.department_id,
            "department_name": department.department_name,
            "department_code": department.department_code,
            "head_faculty_id": department.head_faculty_id,
            "head_name": (
                department.head_faculty.user.name
                if department.head_faculty
                and department.head_faculty.user
                else None
            ),
            "faculty_count": Faculty.query.filter_by(
                department_id=department.department_id
            ).count(),
            "student_count": Student.query.filter_by(
                department_id=department.department_id
            ).count(),
            "is_active": department.is_active,
        },
    }), 200


@admin_bp.delete("/departments/<int:department_id>")
@admin_required
def delete_department(department_id):
    department = db.session.get(Department, department_id)

    if department is None:
        return jsonify({
            "success": False,
            "message": "Department not found",
        }), 404

    linked_counts = {
        "students": Student.query.filter_by(
            department_id=department_id
        ).count(),
        "faculty": Faculty.query.filter_by(
            department_id=department_id
        ).count(),
        "courses": Course.query.filter_by(
            department_id=department_id
        ).count(),
    }

    if any(linked_counts.values()):
        return jsonify({
            "success": False,
            "message": "Department cannot be deleted because it has linked records",
            "data": {
                "linked_counts": linked_counts,
            },
        }), 409

    dept_name = department.department_name
    dept_code = department.department_code

    try:
        db.session.delete(department)
        db.session.commit()
        record_activity(
            action_type="DEPARTMENT_DELETED",
            description=f"Deleted department {dept_name} ({dept_code})",
            entity_type="Department",
            entity_id=str(department_id),
            details={"name": dept_name, "code": dept_code},
        )
    except IntegrityError:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "Department cannot be deleted because related records exist",
        }), 409

    return jsonify({
        "success": True,
        "message": "Department deleted successfully",
    }), 200


# USER MANAGEMENT

@admin_bp.get("/users")
@admin_required
def get_users():
    users = User.query.order_by(
        User.user_id.asc()
    ).all()

    data = []
    for user in users:
        dept = user.department
        if not dept and user.student_profile and user.student_profile.department:
            dept = user.student_profile.department.name
        elif not dept and user.faculty_profile and user.faculty_profile.department:
            dept = user.faculty_profile.department.name

        ph = user.phone
        if not ph and user.student_profile and user.student_profile.phone:
            ph = user.student_profile.phone
        elif not ph and user.faculty_profile and user.faculty_profile.phone:
            ph = user.faculty_profile.phone

        data.append({
            "user_id": user.user_id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
            "department": dept or "Administration",
            "phone": ph or "—",
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
            "last_login": format_utc_iso(user.last_login),
        })

    return jsonify({
        "success": True,
        "data": data,
    }), 200


@admin_bp.post("/users")
@admin_required
def create_admin_user():
    data = request.get_json(silent=True) or {}

    name = data.get("name")
    email = data.get("email")
    password = data.get("password")
    role = data.get("role")

    if not all([name, email, password, role]):
        return jsonify({
            "success": False,
            "message": (
                "Name, email, password and role are required"
            ),
        }), 400

    role = role.upper().strip()

    if role not in {"ADMIN", "FACULTY", "STUDENT"}:
        return jsonify({
            "success": False,
            "message": "Invalid role",
        }), 400

    email = email.lower().strip()

    if User.query.filter_by(email=email).first():
        return jsonify({
            "success": False,
            "message": "Email already exists",
        }), 409

    user = create_user(
        name=name.strip(),
        email=email,
        password=password,
        role=role,
    )

    record_activity(
        action_type="USER_CREATED",
        description=f"Created user account {user.name} ({user.role})",
        entity_type="User",
        entity_id=str(user.user_id),
        details={"name": user.name, "email": user.email, "role": user.role},
    )

    return jsonify({
        "success": True,
        "message": "User created successfully",
        "data": {
            "user_id": user.user_id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
        },
    }), 201


@admin_bp.get("/users/<int:user_id>")
@admin_required
def get_user(user_id):
    user = db.session.get(User, user_id)

    if not user:
        return jsonify({
            "success": False,
            "message": "User not found",
        }), 404

    dept = user.department
    if not dept and user.student_profile and user.student_profile.department:
        dept = user.student_profile.department.name
    elif not dept and user.faculty_profile and user.faculty_profile.department:
        dept = user.faculty_profile.department.name

    ph = user.phone
    if not ph and user.student_profile and user.student_profile.phone:
        ph = user.student_profile.phone
    elif not ph and user.faculty_profile and user.faculty_profile.phone:
        ph = user.faculty_profile.phone

    return jsonify({
        "success": True,
        "data": {
            "user_id": user.user_id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
            "department": dept or "Administration",
            "phone": ph or "—",
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
            "last_login": format_utc_iso(user.last_login),
        },
    }), 200


@admin_bp.patch("/users/<int:user_id>")
@admin_required
def update_user(user_id):
    user = db.session.get(User, user_id)

    if not user:
        return jsonify({
            "success": False,
            "message": "User not found",
        }), 404

    data = request.get_json(silent=True) or {}

    # Validate the requested active status before changing the user.
    if "is_active" in data and not isinstance(data["is_active"], bool):
        return jsonify({
            "success": False,
            "message": "is_active must be a boolean",
        }), 400

    # Validate the requested role before applying changes.
    requested_role = data.get("role", user.role)
    if not isinstance(requested_role, str):
        return jsonify({
            "success": False,
            "message": "Invalid role",
        }), 400

    final_role = requested_role.upper().strip()
    if final_role not in {"ADMIN", "FACULTY", "STUDENT"}:
        return jsonify({
            "success": False,
            "message": "Invalid role",
        }), 400

    final_is_active = data.get("is_active", user.is_active)

    # Prevent changing or disabling the current administrator account.
    current_user_id = get_jwt_identity()
    if str(current_user_id) == str(user.user_id):
        if final_role != "ADMIN" or final_is_active is not True:
            return jsonify({
                "success": False,
                "message": (
                    "You cannot deactivate your current account "
                    "or change your own administrator role."
                ),
            }), 409

    # Never leave the system without an active administrator.
    if user.role == "ADMIN" and user.is_active:
        removing_active_admin = (
            final_role != "ADMIN" or final_is_active is not True
        )
        if removing_active_admin:
            active_admin_count = User.query.filter_by(
                role="ADMIN",
                is_active=True,
            ).count()

            if active_admin_count <= 1:
                return jsonify({
                    "success": False,
                    "message": (
                        "The last active administrator cannot be "
                        "deactivated or changed to another role."
                    ),
                }), 409

    # Apply the validated active status only after the safeguards.
    if "is_active" in data:
        user.is_active = final_is_active


    if "name" in data:
        name = str(data["name"]).strip()

        if not name:
            return jsonify({
                "success": False,
                "message": "Name cannot be empty",
            }), 400

        user.name = name

    if "email" in data:
        email = str(data["email"]).lower().strip()

        if not email:
            return jsonify({
                "success": False,
                "message": "Email cannot be empty",
            }), 400

        existing_user = User.query.filter(
            User.email == email,
            User.user_id != user_id,
        ).first()

        if existing_user:
            return jsonify({
                "success": False,
                "message": "Email already exists",
            }), 409

        user.email = email

    if "role" in data:
        role = str(data["role"]).upper().strip()

        if role not in {"ADMIN", "FACULTY", "STUDENT"}:
            return jsonify({
                "success": False,
                "message": "Invalid role",
            }), 400

        user.role = role

    if "password" in data:
        password = str(data["password"])

        if len(password) < 8:
            return jsonify({
                "success": False,
                "message": "Password must be at least 8 characters",
            }), 400

        user.password_hash = bcrypt.generate_password_hash(
            password
        ).decode("utf-8")

    try:
        db.session.commit()
        record_activity(
            action_type="USER_UPDATED",
            description=f"Updated user account {user.name} ({user.role})",
            entity_type="User",
            entity_id=str(user.user_id),
            details={"name": user.name, "email": user.email, "role": user.role},
        )
    except IntegrityError:
        db.session.rollback()

        return jsonify({
            "success": False,
            "message": "User could not be updated because of a database constraint",
        }), 409

    except Exception:
        db.session.rollback()

        return jsonify({
            "success": False,
            "message": "User could not be updated",
        }), 500

    return jsonify({
        "success": True,
        "message": "User updated successfully",
        "data": {
            "user_id": user.user_id,
            "name": user.name,
            "email": user.email,
            "is_active": user.is_active,
        },
    }), 200


@admin_bp.delete("/users/<int:user_id>")
@admin_required
def delete_user(user_id):
    user = db.session.get(User, user_id)

    if not user:
        return jsonify({
            "success": False,
            "message": "User not found",
        }), 404

    # Prevent administrators from deleting their own account.
    current_user_id = get_jwt_identity()

    if str(current_user_id) == str(user.user_id):
        return jsonify({
            "success": False,
            "message": "You cannot delete your current account.",
        }), 409

    try:
        # Preserve at least one active administrator.
        if user.role == "ADMIN" and user.is_active:
            active_admin_count = User.query.filter_by(
                role="ADMIN",
                is_active=True,
            ).count()

            if active_admin_count <= 1:
                return jsonify({
                    "success": False,
                    "message": (
                        "The last active administrator cannot be deleted."
                    ),
                }), 409

        student = Student.query.filter_by(
            user_id=user.user_id
        ).first()

        faculty = Faculty.query.filter_by(
            user_id=user.user_id
        ).first()

        has_history = False

        if student:
            has_history = (
                AttendanceRecord.query.filter_by(
                    student_id=student.student_id
                ).first() is not None
                or Enrollment.query.filter_by(
                    student_id=student.student_id
                ).first() is not None
            )

        if faculty:
            has_history = has_history or (
                CourseOffering.query.filter_by(
                    faculty_id=faculty.faculty_id
                ).first() is not None
                or AttendanceSession.query.filter_by(
                    faculty_id=faculty.faculty_id
                ).first() is not None
            )

        if has_history:
            user.is_active = False
            db.session.commit()
            record_activity(
                action_type="USER_DEACTIVATED",
                description=f"Deactivated user account {user.name} ({user.role})",
                entity_type="User",
                entity_id=str(user.user_id),
            )

            return jsonify({
                "success": True,
                "action": "deactivated",
                "message": (
                    "User deactivated because related academic or "
                    "attendance records must be preserved."
                ),
                "data": {
                    "user_id": user.user_id,
                    "is_active": False,
                },
            }), 200

        # No protected history exists. Remove the empty profile first.
        deleted_name = user.name
        deleted_role = user.role
        if student:
            db.session.delete(student)

        if faculty:
            db.session.delete(faculty)

        db.session.delete(user)
        db.session.commit()
        record_activity(
            action_type="USER_DELETED",
            description=f"Deleted user account {deleted_name} ({deleted_role})",
            entity_type="User",
            entity_id=str(user_id),
        )

        return jsonify({
            "success": True,
            "action": "deleted",
            "message": "User deleted successfully.",
            "data": {
                "user_id": user_id,
            },
        }), 200

    except IntegrityError:
        db.session.rollback()

        return jsonify({
            "success": False,
            "message": (
                "User could not be permanently deleted because "
                "related records still exist. No records were deleted."
            ),
        }), 409

    except Exception:
        db.session.rollback()

        return jsonify({
            "success": False,
            "message": "User could not be deleted.",
        }), 500

@admin_bp.patch("/users/<int:user_id>/reactivate")
@admin_required
def reactivate_user(user_id):
    """Reactivate an existing inactive user account."""
    user = db.session.get(User, user_id)

    if not user:
        return jsonify({
            "success": False,
            "message": "User not found",
        }), 404

    if user.is_active:
        return jsonify({
            "success": True,
            "action": "already_active",
            "message": "User account is already active.",
            "data": {
                "user_id": user.user_id,
                "is_active": True,
            },
        }), 200

    try:
        user.is_active = True
        db.session.commit()
        record_activity(
            action_type="USER_REACTIVATED",
            description=f"Reactivated user account {user.name} ({user.role})",
            entity_type="User",
            entity_id=str(user.user_id),
        )

        return jsonify({
            "success": True,
            "action": "reactivated",
            "message": (
                "User account reactivated successfully. "
                "Existing academic and attendance history "
                "has been preserved."
            ),
            "data": {
                "user_id": user.user_id,
                "is_active": True,
            },
        }), 200

    except IntegrityError:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": (
                "The account could not be reactivated "
                "because of a database constraint."
            ),
        }), 409

    except Exception:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "Unable to reactivate the user account.",
        }), 500

def get_student_attendance_summary(student_id):
    active_enrollments = Enrollment.query.filter_by(
        student_id=student_id,
        status="ACTIVE",
    ).all()

    offering_ids = [
        enrollment.offering_id
        for enrollment in active_enrollments
    ]

    closed_sessions = []

    if offering_ids:
        closed_sessions = AttendanceSession.query.filter(
            AttendanceSession.offering_id.in_(offering_ids),
            AttendanceSession.status == "CLOSED",
        ).all()

    session_ids = [
        session.session_id
        for session in closed_sessions
    ]

    total_sessions = len(session_ids)
    present_sessions = 0

    if session_ids:
        present_sessions = AttendanceRecord.query.filter(
            AttendanceRecord.student_id == student_id,
            AttendanceRecord.session_id.in_(session_ids),
            AttendanceRecord.status == "PRESENT",
        ).count()

    absent_sessions = total_sessions - present_sessions

    attendance_percentage = (
        (present_sessions / total_sessions) * 100
        if total_sessions > 0
        else 0.0
    )

    return {
        "total_sessions": total_sessions,
        "present_sessions": present_sessions,
        "absent_sessions": absent_sessions,
        "attendance_percentage": round(
            attendance_percentage, 2
        ),
    }
# ============================================================
# STUDENT MANAGEMENT
# ============================================================

def batch_get_student_attendance_summaries(student_ids):
    if not student_ids:
        return {}

    enrollments = (
        db.session.query(Enrollment.student_id, Enrollment.offering_id)
        .filter(
            Enrollment.student_id.in_(student_ids),
            Enrollment.status == "ACTIVE",
        )
        .all()
    )

    from collections import defaultdict
    student_offerings = defaultdict(set)
    all_offering_ids = set()
    for s_id, off_id in enrollments:
        student_offerings[s_id].add(off_id)
        all_offering_ids.add(off_id)

    if not all_offering_ids:
        return {
            s_id: {
                "total_sessions": 0,
                "present_sessions": 0,
                "absent_sessions": 0,
                "attendance_percentage": 0.0,
            }
            for s_id in student_ids
        }

    closed_sessions = (
        db.session.query(AttendanceSession.session_id, AttendanceSession.offering_id)
        .filter(
            AttendanceSession.offering_id.in_(all_offering_ids),
            AttendanceSession.status == "CLOSED",
        )
        .all()
    )

    offering_sessions = defaultdict(set)
    all_closed_session_ids = set()
    for sess_id, off_id in closed_sessions:
        offering_sessions[off_id].add(sess_id)
        all_closed_session_ids.add(sess_id)

    student_sessions = {}
    for s_id in student_ids:
        s_sess = set()
        for off_id in student_offerings.get(s_id, ()):
            s_sess.update(offering_sessions.get(off_id, ()))
        student_sessions[s_id] = s_sess

    student_present_counts = defaultdict(int)
    if all_closed_session_ids:
        present_records = (
            db.session.query(AttendanceRecord.student_id, AttendanceRecord.session_id)
            .filter(
                AttendanceRecord.student_id.in_(student_ids),
                AttendanceRecord.session_id.in_(all_closed_session_ids),
                AttendanceRecord.status == "PRESENT",
            )
            .all()
        )
        for s_id, sess_id in present_records:
            if sess_id in student_sessions.get(s_id, set()):
                student_present_counts[s_id] += 1

    summaries = {}
    for s_id in student_ids:
        sess_ids = student_sessions.get(s_id, set())
        total = len(sess_ids)
        present = student_present_counts.get(s_id, 0)
        absent = total - present
        pct = round((present / total) * 100, 2) if total > 0 else 0.0
        summaries[s_id] = {
            "total_sessions": total,
            "present_sessions": present,
            "absent_sessions": absent,
            "attendance_percentage": pct,
        }

    return summaries


def _serialize_student(student, include_details=False, attendance_summary=None):
    is_active = getattr(student.user, "is_active", True)
    has_face = any(fp.is_active for fp in student.face_profiles) if student.face_profiles else False

    if attendance_summary is None:
        attendance_summary = get_student_attendance_summary(student.student_id)

    acad_info = resolve_student_academic_info(student)

    data = {
        "student_id": student.student_id,
        "user_id": student.user_id,
        "name": student.user.name,
        "email": student.user.email,
        "enrollment_no": student.enrollment_no,
        "roll_no": getattr(student, "roll_no", None) or student.enrollment_no,
        "semester": acad_info["semester"],
        "section": acad_info["section"],
        "academic_year": acad_info["academic_year"],
        "batch_year": acad_info["batch_year"],
        "batch_name": acad_info["batch_name"],
        "admission_year": acad_info["admission_year"],
        "batch_id": student.batch_id,
        "department_id": student.department.department_id if student.department else None,
        "department_name": student.department.department_name if student.department else "",
        "department_code": student.department.department_code if student.department else "",
        "is_active": is_active,
        "status": "Active" if is_active else "Inactive",
        "face_registered": has_face,
        "face_status": "Registered" if has_face else "Not Registered",
        "photo_url": student.photo_url,
        "phone": student.phone or "",
        "guardian_phone": student.guardian_phone or "",
        "date_of_birth": student.date_of_birth or "",
        "gender": student.gender or "",
        "address": student.address or "",
        "city": student.city or "",
        "state": student.state or "",
        "pin_code": student.pin_code or "",
        "country": student.country or "India",
        "father_name": student.father_name or "",
        "mother_name": student.mother_name or "",
        "blood_group": student.blood_group or "",
        "admission_date": student.admission_date or "",
        "attendance_summary": attendance_summary,
    }

    if include_details and student.enrollments:
        data["enrollments"] = [
            {
                "enrollment_id": enr.enrollment_id,
                "offering_id": enr.offering_id,
                "course_code": enr.offering.course.course_code if enr.offering and enr.offering.course else "",
                "course_name": enr.offering.course.course_name if enr.offering and enr.offering.course else "",
                "semester": enr.offering.semester if enr.offering else None,
                "section": enr.offering.section if enr.offering else "",
                "status": enr.status,
            }
            for enr in student.enrollments
        ]

    return data


@admin_bp.get("/students/summary")
@admin_required
def get_students_summary():
    total_students = Student.query.count()
    active_students = Student.query.join(Student.user).filter(User.is_active.is_(True)).count()
    inactive_students = total_students - active_students
    face_registered = (
        db.session.query(FaceProfile.student_id)
        .filter(FaceProfile.is_active.is_(True))
        .distinct()
        .count()
    )
    face_registered_percentage = (
        round((face_registered / total_students) * 100, 1)
        if total_students > 0
        else 0.0
    )

    distinct_semesters = [
        s[0]
        for s in db.session.query(Student.semester)
        .filter(Student.semester.isnot(None))
        .distinct()
        .order_by(Student.semester.asc())
        .all()
    ]
    distinct_sections = [
        s[0]
        for s in db.session.query(Student.section)
        .filter(Student.section.isnot(None), Student.section != "")
        .distinct()
        .order_by(Student.section.asc())
        .all()
    ]

    return jsonify({
        "success": True,
        "data": {
            "total_students": total_students,
            "active_students": active_students,
            "inactive_students": inactive_students,
            "face_registered": face_registered,
            "face_registered_percentage": face_registered_percentage,
            "semesters": distinct_semesters,
            "sections": distinct_sections,
        },
    }), 200


@admin_bp.get("/students/filter-options")
@admin_required
def get_students_filter_options():
    semesters = [
        s[0]
        for s in db.session.query(Student.semester)
        .filter(Student.semester.isnot(None))
        .distinct()
        .order_by(Student.semester.asc())
        .all()
    ]
    sections = [
        s[0]
        for s in db.session.query(Student.section)
        .filter(Student.section.isnot(None), Student.section != "")
        .distinct()
        .order_by(Student.section.asc())
        .all()
    ]
    departments = [
        {
            "department_id": d.department_id,
            "department_name": d.department_name,
            "department_code": d.department_code,
        }
        for d in Department.query.order_by(Department.department_name.asc()).all()
    ]
    batches = [
        {
            "batch_id": b.batch_id,
            "batch_name": format_batch_cohort(b.batch_name),
            "is_active": b.is_active,
        }
        for b in Batch.query.order_by(Batch.batch_name.asc()).all()
    ]
    academic_years = get_available_academic_sessions()

    return jsonify({
        "success": True,
        "data": {
            "semesters": semesters,
            "sections": sections,
            "departments": departments,
            "batches": batches,
            "academic_years": academic_years,
            "current_academic_year": get_current_academic_session(),
        },
    }), 200


@admin_bp.get("/students")
@admin_required
def get_students():
    query = (
        Student.query
        .join(Student.user)
        .join(Student.department)
        .options(
            joinedload(Student.user),
            joinedload(Student.department),
            joinedload(Student.batch),
            selectinload(Student.face_profiles),
        )
    )

    department_id = request.args.get("department_id", type=int)
    semester = request.args.get("semester", type=int)
    section = request.args.get("section")
    status = request.args.get("status")
    search = request.args.get("search", "").strip()
    batch_id = request.args.get("batch_id", type=int)
    academic_year = request.args.get("academic_year")

    if department_id:
        query = query.filter(Student.department_id == department_id)
    if semester:
        query = query.filter(Student.semester == semester)
    if section and section not in ["All", "all", "All Sections", ""]:
        query = query.filter(Student.section == section)
    if batch_id:
        query = query.filter(Student.batch_id == batch_id)
    if academic_year and academic_year not in ["All", "all", ""]:
        canon_ay = canonical_academic_year(academic_year)
        query = query.filter(
            db.or_(
                Student.academic_year == canon_ay,
                Student.enrollments.any(
                    Enrollment.offering.has(CourseOffering.academic_year == canon_ay)
                ),
            )
        )
    if status in ["ACTIVE", "Active"]:
        query = query.filter(User.is_active.is_(True))
    elif status in ["INACTIVE", "Inactive"]:
        query = query.filter(User.is_active.is_(False))

    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            db.or_(
                User.name.ilike(search_pattern),
                User.email.ilike(search_pattern),
                Student.enrollment_no.ilike(search_pattern),
            )
        )

    students = query.order_by(Student.student_id.asc()).all()
    student_ids = [student.student_id for student in students]
    summaries = batch_get_student_attendance_summaries(student_ids)

    data = [
        _serialize_student(
            student,
            attendance_summary=summaries.get(student.student_id),
        )
        for student in students
    ]

    return jsonify({
        "success": True,
        "data": data,
    }), 200


@admin_bp.get("/students/<int:student_id>")
@admin_required
def get_student(student_id):
    student = (
        Student.query
        .join(Student.user)
        .join(Student.department)
        .filter(Student.student_id == student_id)
        .first()
    )

    if not student:
        return jsonify({
            "success": False,
            "message": "Student not found",
        }), 404

    return jsonify({
        "success": True,
        "data": _serialize_student(student, include_details=True),
    }), 200


@admin_bp.post("/students")
@admin_required
def create_student():
    data = request.get_json(silent=True) or {}

    user_id = data.get("user_id")
    enrollment_no = str(
        data.get("enrollment_no", "")
    ).strip()
    section = str(
        data.get("section", "")
    ).strip()
    academic_year = str(
        data.get("academic_year", "")
    ).strip()

    semester = data.get("semester")
    department_id = data.get("department_id")
    batch_id = data.get("batch_id")

    # -------------------------
    # Required fields
    # -------------------------

    if (
        user_id is None
        or not enrollment_no
        or not section
        or not academic_year
        or semester is None
        or department_id is None
    ):
        return jsonify({
            "success": False,
            "message": (
                "user_id, enrollment_no, semester, section, "
                "academic_year and department_id are required"
            ),
        }), 400

    # -------------------------
    # User ID validation
    # -------------------------

    try:
        user_id = int(user_id)

    except (TypeError, ValueError):
        return jsonify({
            "success": False,
            "message": "User ID must be an integer",
        }), 400

    # -------------------------
    # Semester validation
    # -------------------------

    try:
        semester = int(semester)

    except (TypeError, ValueError):
        return jsonify({
            "success": False,
            "message": "Semester must be an integer",
        }), 400

    if semester < 1:
        return jsonify({
            "success": False,
            "message": "Semester must be greater than 0",
        }), 400

    if semester > 8:
        return jsonify({
            "success": False,
            "message": "Semester must be between 1 and 8",
        }), 400

    if len(section) > 20:
        return jsonify({
            "success": False,
            "message": "Section must not exceed 20 characters",
        }), 400

    # -------------------------
    # Department ID validation
    # -------------------------

    try:
        department_id = int(department_id)

    except (TypeError, ValueError):
        return jsonify({
            "success": False,
            "message": "Department ID must be an integer",
        }), 400

    # -------------------------
    # Existing User validation
    # -------------------------

    user = db.session.get(User, user_id)

    if not user:
        return jsonify({
            "success": False,
            "message": "User not found",
        }), 404

    if user.role != "STUDENT":
        return jsonify({
            "success": False,
            "message": "User role must be STUDENT",
        }), 400

    # -------------------------
    # Existing Student profile
    # -------------------------

    existing_student_profile = Student.query.filter_by(
        user_id=user_id
    ).first()

    if existing_student_profile:
        return jsonify({
            "success": False,
            "message": "Student profile already exists for this user",
        }), 409

    # -------------------------
    # Duplicate enrollment
    # -------------------------

    existing_student = Student.query.filter(
        func.lower(Student.enrollment_no) == enrollment_no.lower()
    ).first()

    if existing_student:
        return jsonify({
            "success": False,
            "message": "Enrollment number already exists",
        }), 409

    # -------------------------
    # Department
    # -------------------------

    department = db.session.get(
        Department,
        department_id,
    )

     # -------------------------
    # Optional Batch validation
    # -------------------------

    batch = None

    if batch_id not in (None, ""):
        try:
            batch_id = int(batch_id)
        except (TypeError, ValueError):
            return jsonify({
                "success": False,
                "message": "Batch ID must be an integer",
            }), 400

        batch = db.session.get(Batch, batch_id)

        if not batch:
            return jsonify({
                "success": False,
                "message": "Batch not found",
            }), 404

        if not batch.is_active:
            return jsonify({
                "success": False,
                "message": "Selected batch is inactive",
            }), 400
    elif data.get("batch_year") or data.get("batch_name"):
        b_name = str(data.get("batch_year") or data.get("batch_name")).strip()
        c_name = format_batch_cohort(b_name)
        batch = Batch.query.filter(
            db.or_(Batch.batch_name == c_name, Batch.batch_name == b_name)
        ).first()
        if not batch:
            batch = Batch(batch_name=c_name)
            db.session.add(batch)
            db.session.flush()

    if not department:
        return jsonify({
            "success": False,
            "message": "Department not found",
        }), 404

    # -------------------------
    # Create Student profile
    # -------------------------

    canonical_ay = canonical_academic_year(academic_year) if academic_year else get_current_academic_session()

    student = Student(
        user_id=user.user_id,
        department_id=department.department_id,
        batch_id=batch.batch_id if batch else None,
        enrollment_no=enrollment_no,
        semester=semester,
        section=section,
        academic_year=canonical_ay,
    )

    try:
        db.session.add(student)
        db.session.commit()
        record_activity(
            action_type="STUDENT_CREATED",
            description=f"Created student profile for {user.name} ({student.enrollment_no})",
            entity_type="Student",
            entity_id=str(student.student_id),
            details={"name": user.name, "enrollment_no": student.enrollment_no},
        )
    except IntegrityError:
        db.session.rollback()

        return jsonify({
            "success": False,
            "message": (
                "Student could not be created because "
                "of a duplicate or database constraint"
            ),
        }), 409

    except Exception:
        db.session.rollback()

        return jsonify({
            "success": False,
            "message": "Student could not be created",
        }), 500

    db.session.refresh(student)
    academic_info = resolve_student_academic_info(student)

    return jsonify({
        "success": True,
        "message": "Student profile created successfully",
        "data": {
            "student_id": student.student_id,
            "user_id": user.user_id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "enrollment_no": student.enrollment_no,
            "semester": academic_info["semester"],
            "section": academic_info["section"],
            "academic_year": academic_info["academic_year"],
            "batch_year": academic_info["batch_year"],
            "batch_name": academic_info["batch_name"],
            "batch_id": student.batch_id,
            "admission_year": academic_info["admission_year"],
            "department_id": department.department_id,
            "department_name": department.department_name,
            "department_code": department.department_code,
        },
    }), 201


@admin_bp.patch("/students/<int:student_id>")
@admin_required
def update_student(student_id):
    student = (
        Student.query
        .join(Student.user)
        .filter(Student.student_id == student_id)
        .first()
    )

    if not student:
        return jsonify({
            "success": False,
            "message": "Student not found",
        }), 404

    data = request.get_json(silent=True) or {}

    if not data:
        return jsonify({
            "success": False,
            "message": "No fields provided for update",
        }), 400

    # -------------------------
    # User fields are forbidden
    # -------------------------

    forbidden_fields = {
        "name",
        "email",
        "password",
        "role",
        "user_id",
    }

    supplied_forbidden_fields = (
        forbidden_fields.intersection(data.keys())
    )

    if supplied_forbidden_fields:
        return jsonify({
            "success": False,
            "message": (
                "User fields cannot be updated through the "
                "student profile API. Use /api/admin/users/<user_id>"
            ),
            "fields": sorted(supplied_forbidden_fields),
        }), 400

    # -------------------------
    # Enrollment number
    # -------------------------

    if "enrollment_no" in data:
        enrollment_no = str(
            data["enrollment_no"]
        ).strip()

        if not enrollment_no:
            return jsonify({
                "success": False,
                "message": "Enrollment number cannot be empty",
            }), 400

        existing_student = Student.query.filter(
            Student.enrollment_no == enrollment_no,
            Student.student_id != student_id,
        ).first()

        if existing_student:
            return jsonify({
                "success": False,
                "message": "Enrollment number already exists",
            }), 409

        student.enrollment_no = enrollment_no

    # -------------------------
    # Semester
    # -------------------------

    if "semester" in data:
        try:
            semester = int(data["semester"])

        except (TypeError, ValueError):
            return jsonify({
                "success": False,
                "message": "Semester must be an integer",
            }), 400

        if semester < 1:
            return jsonify({
                "success": False,
                "message": "Semester must be greater than 0",
            }), 400

        student.semester = semester

    # -------------------------
    # Section
    # -------------------------

    if "section" in data:
        section = str(
            data["section"]
        ).strip()

        if not section:
            return jsonify({
                "success": False,
                "message": "Section cannot be empty",
            }), 400

        student.section = section

    # -------------------------
    # Academic year
    # -------------------------

    if "academic_year" in data:
        academic_year = str(
            data["academic_year"]
        ).strip()

        if not academic_year:
            return jsonify({
                "success": False,
                "message": "Academic year cannot be empty",
            }), 400

        student.academic_year = canonical_academic_year(academic_year)

    # -------------------------
    # Batch
    # -------------------------

    if "batch_id" in data:
        raw_b_id = data.get("batch_id")
        if raw_b_id in (None, ""):
            student.batch_id = None
        else:
            try:
                b_id = int(raw_b_id)
                batch_obj = db.session.get(Batch, b_id)
                if not batch_obj:
                    return jsonify({
                        "success": False,
                        "message": "Batch not found",
                    }), 404
                student.batch_id = b_id
            except (TypeError, ValueError):
                return jsonify({
                    "success": False,
                    "message": "Batch ID must be an integer",
                }), 400
    elif "batch_year" in data or "batch_name" in data:
        raw_b_name = str(data.get("batch_year") or data.get("batch_name") or "").strip()
        if raw_b_name:
            cohort_name = format_batch_cohort(raw_b_name)
            batch_obj = Batch.query.filter(
                db.or_(Batch.batch_name == cohort_name, Batch.batch_name == raw_b_name)
            ).first()
            if not batch_obj:
                batch_obj = Batch(batch_name=cohort_name)
                db.session.add(batch_obj)
                db.session.flush()
            student.batch_id = batch_obj.batch_id

    # -------------------------
    # Department
    # -------------------------

    if "department_id" in data:
        try:
            department_id = int(
                data["department_id"]
            )

        except (TypeError, ValueError):
            return jsonify({
                "success": False,
                "message": "Department ID must be an integer",
            }), 400

        department = db.session.get(
            Department,
            department_id,
        )

        if not department:
            return jsonify({
                "success": False,
                "message": "Department not found",
            }), 404

        student.department_id = department.department_id

    try:
        db.session.commit()

    except IntegrityError:
        db.session.rollback()

        return jsonify({
            "success": False,
            "message": (
                "Student could not be updated because "
                "of a duplicate or database constraint"
            ),
        }), 409

    except Exception:
        db.session.rollback()

        return jsonify({
            "success": False,
            "message": "Student could not be updated",
        }), 500

    db.session.refresh(student)
    academic_info = resolve_student_academic_info(student)

    return jsonify({
        "success": True,
        "message": "Student updated successfully",
        "data": {
            "student_id": student.student_id,
            "user_id": student.user_id,
            "name": student.user.name,
            "email": student.user.email,
            "enrollment_no": student.enrollment_no,
            "semester": academic_info["semester"],
            "section": academic_info["section"],
            "academic_year": academic_info["academic_year"],
            "batch_year": academic_info["batch_year"],
            "batch_name": academic_info["batch_name"],
            "batch_id": student.batch_id,
            "admission_year": academic_info["admission_year"],
            "department_id": student.department.department_id if student.department else None,
            "department_name": student.department.department_name if student.department else "",
            "department_code": student.department.department_code if student.department else "",
        },
    }), 200


@admin_bp.delete("/students/<int:student_id>")
@admin_required
def delete_student(student_id):
    student = Student.query.filter_by(
        student_id=student_id
    ).first()

    if not student:
        return jsonify({
            "success": False,
            "message": "Student not found",
        }), 404

    # Preserve attendance history.
    attendance_count = AttendanceRecord.query.filter_by(
        student_id=student.student_id
    ).count()

    if attendance_count > 0:
        return jsonify({
            "success": False,
            "message": (
                "Student cannot be deleted because attendance "
                "records exist. Deactivate the student account "
                "to preserve academic history."
            ),
        }), 409

    # Preserve course enrollment history.
    enrollment_count = Enrollment.query.filter_by(
        student_id=student.student_id
    ).count()

    if enrollment_count > 0:
        return jsonify({
            "success": False,
            "message": (
                "Student cannot be deleted because course "
                "enrollment records exist. Deactivate the "
                "student account to preserve academic history."
            ),
        }), 409

    try:
        # Only delete the profile when no attendance or
        # enrollment history exists. The linked User remains.
        db.session.delete(student)
        db.session.commit()

    except IntegrityError:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": (
                "Student could not be deleted because related "
                "records exist."
            ),
        }), 409

    except Exception:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "Student could not be deleted.",
        }), 500

    return jsonify({
        "success": True,
        "message": "Student profile deleted successfully.",
        "data": {
            "student_id": student_id,
        },
    }), 200


@admin_bp.get("/students/duplicates")
@admin_required
def get_suspected_duplicate_students():
    """
    Scans the database and returns a report of suspected duplicate student records
    and cross-student biometric collisions.
    """
    threshold = request.args.get("threshold", default=0.50, type=float)
    duplicates = detect_suspected_duplicate_students(threshold=threshold)
    return jsonify({
        "success": True,
        "count": len(duplicates),
        "threshold": threshold,
        "data": duplicates,
    }), 200


@admin_bp.post("/students/reconcile-duplicates")
@admin_required
def reconcile_duplicate_students_route():
    """
    Explicit, authorized administrative reconciliation:
    Merges related enrollments and attendance records from duplicate to canonical,
    invalidates duplicate's active face mappings, and deactivates duplicate user account.
    """
    data = request.get_json(silent=True) or {}
    canonical_id = data.get("canonical_student_id")
    duplicate_id = data.get("duplicate_student_id")
    action = data.get("action", "merge_and_deactivate")
    reason = data.get("reason", "Admin manual reconciliation")

    if not canonical_id or not duplicate_id:
        return jsonify({
            "success": False,
            "message": "canonical_student_id and duplicate_student_id are required",
        }), 400

    try:
        canonical_id = int(canonical_id)
        duplicate_id = int(duplicate_id)
    except (ValueError, TypeError):
        return jsonify({
            "success": False,
            "message": "Student IDs must be integers",
        }), 400

    admin_user_id = int(get_jwt_identity())

    try:
        result = reconcile_duplicate_students(
            canonical_student_id=canonical_id,
            duplicate_student_id=duplicate_id,
            admin_user_id=admin_user_id,
            action=action,
            reason=reason,
        )
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({
            "success": False,
            "message": str(e),
        }), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": f"Reconciliation failed: {str(e)}",
        }), 500


@admin_bp.post("/face-profiles/cleanup-obsolete")
@admin_required
def cleanup_obsolete_profiles_route():
    """
    Safely deletes obsolete (inactive) face profiles according to retention policy.
    Active face profiles are NEVER deleted.
    """
    data = request.get_json(silent=True) or {}
    student_id = data.get("student_id")
    retention_days = data.get("retention_days", 0)

    try:
        if student_id is not None:
            student_id = int(student_id)
        retention_days = int(retention_days)
    except (ValueError, TypeError):
        return jsonify({
            "success": False,
            "message": "student_id and retention_days must be integers",
        }), 400

    try:
        purged = cleanup_obsolete_face_profiles(
            student_id=student_id,
            retention_days=retention_days,
        )
        return jsonify({
            "success": True,
            "message": f"Successfully purged {purged} obsolete face profile(s)",
            "purged_count": purged,
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": f"Cleanup failed: {str(e)}",
        }), 500


# ============================================================
# REMOVE STUDENT FACE BIOMETRIC REGISTRATION
# ============================================================

@admin_bp.delete("/students/<int:student_id>/face")
@admin_bp.delete("/students/<int:student_id>/face-profile")
@admin_required
def remove_student_face_registration(student_id):
    """
    Administrator-controlled removal / deactivation of a student's active face biometric.
    Allows re-registration while maintaining student academic data and attendance history.
    """
    admin_user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    reason = data.get("reason") or request.args.get("reason")
    face_id = data.get("face_id") or request.args.get("face_id", type=int)
    permanent = data.get("permanent") if "permanent" in data else request.args.get("permanent", type=bool, default=False)

    success, message, result_data, status = remove_student_face_profile(
        student_id=student_id,
        admin_user_id=admin_user_id,
        face_id=face_id,
        reason=reason,
        permanent=permanent,
    )

    if not success:
        if status in ("student_not_found", "face_profile_not_found", "not_registered"):
            return jsonify({
                "success": False,
                "message": message,
                "status": status,
                "data": result_data,
            }), 404
        elif status in ("profile_student_mismatch", "invalid_face_id"):
            return jsonify({
                "success": False,
                "message": message,
                "status": status,
            }), 400
        return jsonify({
            "success": False,
            "message": message,
            "status": status,
        }), 500

    return jsonify({
        "success": True,
        "message": message,
        "data": result_data,
    }), 200


# ============================================================
# ACADEMIC MANAGEMENT SUMMARY
# ============================================================

@admin_bp.get("/academic/summary")
@admin_required
def get_academic_summary():
    total_courses = Course.query.count()
    active_courses = Course.query.filter_by(is_active=True).count()
    course_offerings = CourseOffering.query.count()
    enrollments = Enrollment.query.filter_by(status="ACTIVE").count()

    return jsonify({
        "success": True,
        "data": {
            "total_courses": total_courses,
            "active_courses": active_courses,
            "course_offerings": course_offerings,
            "enrollments": enrollments,
        },
    }), 200


# COURSE MANAGEMENT


@admin_bp.get("/courses")
@admin_required
def get_courses():
    courses = Course.query.order_by(
        Course.course_id.asc()
    ).all()

    data = [
        {
            "course_id": course.course_id,
            "course_code": course.course_code,
            "course_name": course.course_name,
            "department_id": course.department.department_id,
            "department_name": course.department.department_name,
            "department_code": course.department.department_code,
            "semester": course.semester,
            "credits": course.credits,
            "academic_year": resolve_offering_academic_year(course.batch, course.semester) if course.batch else "",
            "batch": course.batch,
            "is_active": course.is_active,
        }
        for course in courses
    ]

    return jsonify({
        "success": True,
        "data": data,
    }), 200


@admin_bp.get("/courses/<int:course_id>")
@admin_required
def get_course(course_id):
    course = db.session.get(Course, course_id)

    if not course:
        return jsonify({
            "success": False,
            "message": "Course not found",
        }), 404

    return jsonify({
        "success": True,
        "data": {
            "course_id": course.course_id,
            "course_code": course.course_code,
            "course_name": course.course_name,
            "department_id": course.department.department_id,
            "department_name": course.department.department_name,
            "department_code": course.department.department_code,
            "semester": course.semester,
            "credits": course.credits,
            "academic_year": resolve_offering_academic_year(course.batch, course.semester) if course.batch else "",
            "batch": course.batch,
        },
    }), 200


@admin_bp.post("/courses")
@admin_required
def create_course():
    data = request.get_json(silent=True) or {}

    course_code = str(data.get("course_code") or "").strip()
    course_name = str(data.get("course_name") or "").strip()
    department_id = data.get("department_id")
    semester = data.get("semester")
    credits = data.get("credits")
    raw_batch = str(data.get("batch") if ("batch" in data and data.get("batch")) else (data.get("academic_year") or "")).strip()
    if is_single_academic_session(raw_batch):
        batch = canonical_academic_year(raw_batch)
    else:
        batch = raw_batch

    if (
        not course_code
        or not course_name
        or not batch
        or department_id is None
        or semester is None
        or credits is None
    ):
        return jsonify({
            "success": False,
            "message": (
                "course_code, course_name, batch, department_id, "
                "semester and credits are required"
            ),
        }), 400

    try:
        department_id = int(department_id)
        semester = int(semester)
        credits = int(credits)
    except (TypeError, ValueError):
        return jsonify({
            "success": False,
            "message": (
                "department_id, semester and credits "
                "must be integers"
            ),
        }), 400

    if department_id < 1:
        return jsonify({
            "success": False,
            "message": "Department ID must be greater than 0",
        }), 400

    if semester < 1:
        return jsonify({
            "success": False,
            "message": "Semester must be greater than 0",
        }), 400

    if credits < 1:
        return jsonify({
            "success": False,
            "message": "Credits must be greater than 0",
        }), 400

    if len(course_code) > 30:
        return jsonify({
            "success": False,
            "message": "Course code cannot exceed 30 characters",
        }), 400

    if len(course_name) > 150:
        return jsonify({
            "success": False,
            "message": "Course name cannot exceed 150 characters",
        }), 400

    if len(batch) > 20:
        return jsonify({
            "success": False,
            "message": "Batch cannot exceed 20 characters",
        }), 400

    department = db.session.get(Department, department_id)

    if not department:
        return jsonify({
            "success": False,
            "message": "Department not found",
        }), 404

    existing_course = Course.query.filter_by(
        course_code=course_code
    ).first()

    if existing_course:
        return jsonify({
            "success": False,
            "message": "Course code already exists",
        }), 409

    course = Course(
        course_code=course_code,
        course_name=course_name,
        department_id=department_id,
        semester=semester,
        credits=credits,
        batch=batch,
    )

    try:
        db.session.add(course)
        db.session.commit()
        db.session.refresh(course)
        record_activity(
            action_type="COURSE_CREATED",
            description=f"Created course {course.course_name} ({course.course_code})",
            entity_type="Course",
            entity_id=str(course.course_id),
            details={"name": course.course_name, "code": course.course_code},
        )
    except IntegrityError:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "Course could not be created due to a conflict",
        }), 409

    except Exception:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "Course could not be created",
        }), 500

    return jsonify({
        "success": True,
        "message": "Course created successfully",
        "data": {
            "course_id": course.course_id,
            "course_code": course.course_code,
            "course_name": course.course_name,
            "department_id": course.department.department_id,
            "department_name": course.department.department_name,
            "department_code": course.department.department_code,
            "semester": course.semester,
            "credits": course.credits,
            "is_active": course.is_active,
        },
    }), 201


@admin_bp.patch("/courses/<int:course_id>")
@admin_required
def update_course(course_id):
    course = db.session.get(Course, course_id)

    if not course:
        return jsonify({
            "success": False,
            "message": "Course not found",
        }), 404

    data = request.get_json(silent=True) or {}

    allowed_fields = {
        "course_code",
        "course_name",
        "department_id",
        "semester",
        "credits",
        "is_active",
        "batch",
        "academic_year",
    }

    if not data or not set(data.keys()).issubset(allowed_fields):
        return jsonify({
            "success": False,
            "message": "Provide valid course fields to update",
        }), 400

    if "course_code" in data:
        course_code = str(data.get("course_code") or "").strip()

        if not course_code:
            return jsonify({
                "success": False,
                "message": "Course code cannot be empty",
            }), 400

        if len(course_code) > 30:
            return jsonify({
                "success": False,
                "message": "Course code cannot exceed 30 characters",
            }), 400

        duplicate = Course.query.filter(
            Course.course_code == course_code,
            Course.course_id != course_id,
        ).first()

        if duplicate:
            return jsonify({
                "success": False,
                "message": "Course code already exists",
            }), 409

        course.course_code = course_code

    if "course_name" in data:
        course_name = str(data.get("course_name") or "").strip()

        if not course_name:
            return jsonify({
                "success": False,
                "message": "Course name cannot be empty",
            }), 400

        if len(course_name) > 150:
            return jsonify({
                "success": False,
                "message": "Course name cannot exceed 150 characters",
            }), 400

        course.course_name = course_name

    if "batch" in data or "academic_year" in data:
        raw_val = data.get("batch") if ("batch" in data and data.get("batch")) else data.get("academic_year")
        batch = str(raw_val or "").strip()

        if not batch:
            return jsonify({
                "success": False,
                "message": "Batch cannot be empty",
            }), 400

        if len(batch) > 20:
            return jsonify({
                "success": False,
                "message": "Batch cannot exceed 20 characters",
            }), 400

        course.batch = batch

    if "department_id" in data:
        try:
            department_id = int(data["department_id"])
        except (TypeError, ValueError):
            return jsonify({
                "success": False,
                "message": "Department ID must be an integer",
            }), 400

        if department_id < 1:
            return jsonify({
                "success": False,
                "message": "Department ID must be greater than 0",
            }), 400

        department = db.session.get(Department, department_id)

        if not department:
            return jsonify({
                "success": False,
                "message": "Department not found",
            }), 404

        course.department_id = department_id

    for field in ("semester", "credits"):
        if field in data:
            try:
                value = int(data[field])
            except (TypeError, ValueError):
                return jsonify({
                    "success": False,
                    "message": f"{field} must be an integer",
                }), 400

            if value < 1:
                return jsonify({
                    "success": False,
                    "message": f"{field} must be greater than 0",
                }), 400

            setattr(course, field, value)
    if "is_active" in data:
        if not isinstance(data["is_active"], bool):
            return jsonify({
                "success": False,
                "message": "is_active must be true or false",
            }), 400

        course.is_active = data["is_active"]

    try:
        db.session.commit()
        db.session.refresh(course)

    except IntegrityError:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "Course could not be updated due to a conflict",
        }), 409

    except Exception:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "Course could not be updated",
        }), 500

    return jsonify({
        "success": True,
        "message": "Course updated successfully",
        "data": {
            "course_id": course.course_id,
            "course_code": course.course_code,
            "course_name": course.course_name,
            "department_id": course.department.department_id,
            "department_name": course.department.department_name,
            "department_code": course.department.department_code,
            "semester": course.semester,
            "credits": course.credits,
            "is_active": course.is_active,
        },
    }), 200


@admin_bp.delete("/courses/<int:course_id>")
@admin_required
def delete_course(course_id):
    course = db.session.get(Course, course_id)

    if not course:
        return jsonify({
            "success": False,
            "message": "Course not found",
        }), 404

    offering_count = CourseOffering.query.filter_by(
        course_id=course_id
    ).count()

    if offering_count > 0:
        return jsonify({
            "success": False,
            "message": (
                "Course cannot be deleted because "
                "course offerings exist"
            ),
        }), 409

    try:
        db.session.delete(course)
        db.session.commit()

    except IntegrityError:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": (
                "Course cannot be deleted because "
                "related records exist"
            ),
        }), 409

    except Exception:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "Course could not be deleted",
        }), 500

    return jsonify({
        "success": True,
        "message": "Course deleted successfully",
    }), 200


# ============================================================
# COURSE OFFERING MANAGEMENT
# ============================================================

@admin_bp.get("/course-offerings")
@admin_required
def get_course_offerings():
    offerings = (
        CourseOffering.query
        .options(
            joinedload(CourseOffering.course),
            joinedload(CourseOffering.faculty).joinedload(Faculty.user),
        )
        .order_by(CourseOffering.offering_id.asc())
        .all()
    )

    enrollment_counts = dict(
        db.session.query(
            Enrollment.offering_id,
            db.func.count(Enrollment.enrollment_id)
        ).group_by(Enrollment.offering_id).all()
    )

    session_counts = dict(
        db.session.query(
            AttendanceSession.offering_id,
            db.func.count(AttendanceSession.session_id)
        ).group_by(AttendanceSession.offering_id).all()
    )

    enrollment_batches = dict(
        db.session.query(
            Enrollment.offering_id,
            Batch.batch_name
        )
        .join(Student, Enrollment.student_id == Student.student_id)
        .join(Batch, Student.batch_id == Batch.batch_id)
        .distinct()
        .all()
    )

    data = []
    for offering in offerings:
        if offering.faculty_id:
            if offering.faculty and offering.faculty.user and offering.faculty.user.name:
                faculty_name = offering.faculty.user.name
            else:
                current_app.logger.warning(
                    f"CourseOffering {offering.offering_id} references faculty_id {offering.faculty_id} "
                    f"but faculty or user profile is missing or inconsistent."
                )
                faculty_name = f"Faculty #{offering.faculty_id}"
        else:
            faculty_name = "Unassigned"

        batch_val = (
            (offering.course.batch if offering.course and offering.course.batch else None)
            or enrollment_batches.get(offering.offering_id)
            or ""
        )

        data.append({
            "offering_id": offering.offering_id,
            "course_id": offering.course_id,
            "course_code": offering.course.course_code if offering.course else "",
            "course_name": offering.course.course_name if offering.course else "",
            "faculty_id": offering.faculty_id,
            "faculty_name": faculty_name,
            "batch": batch_val,
            "academic_year": resolve_offering_academic_year(
                offering.academic_year,
                offering.semester,
                batch=batch_val,
            ),
            "raw_academic_year": offering.academic_year,
            "semester": offering.semester,
            "section": offering.section,
            "room": offering.room,
            "enrollment_count": enrollment_counts.get(offering.offering_id, 0),
            "attendance_session_count": session_counts.get(
                offering.offering_id, 0
            ),
        })

    return jsonify({
        "success": True,
        "data": data,
    }), 200


@admin_bp.post("/course-offerings")
@admin_required
def create_course_offering():
    data = request.get_json(silent=True) or {}

    try:
        course_id = int(data.get("course_id"))
        semester = int(data.get("semester"))
    except (TypeError, ValueError):
        return jsonify({
            "success": False,
            "message": "Valid course_id and semester are required",
        }), 400

    raw_faculty_id = data.get("faculty_id")

    if raw_faculty_id is None or str(raw_faculty_id).strip() == "":
        faculty_id = None
        faculty = None
    else:
        try:
            faculty_id = int(raw_faculty_id)
        except (TypeError, ValueError):
            return jsonify({
                "success": False,
                "message": "Invalid faculty_id",
            }), 400

        faculty = db.session.get(Faculty, faculty_id)

        if not faculty:
            return jsonify({
                "success": False,
                "message": "Faculty not found",
            }), 404

    academic_year = str(
        data.get("academic_year") or ""
    ).strip()

    if not academic_year:
        academic_year = get_current_academic_session()
    else:
        academic_year = canonical_academic_year(academic_year)

    if not is_single_academic_session(academic_year):
        return jsonify({
            "success": False,
            "message": "Academic year for course offerings must represent a 1-year academic session (e.g. '2025-2026'), not a cohort range.",
        }), 400

    section = str(data.get("section") or "").strip()
    room = str(data.get("room") or "").strip() or None

    if not academic_year or not section or semester < 1:
        return jsonify({
            "success": False,
            "message": (
                "Academic year, section and a valid semester are required"
            ),
        }), 400

    course = db.session.get(Course, course_id)

    if not course:
        return jsonify({
            "success": False,
            "message": "Course not found",
        }), 404


    if "batch" in data and course:
        raw_b = str(data.get("batch") or "").strip()
        if raw_b and (not course.batch or course.batch != raw_b):
            course.batch = raw_b

    offering = CourseOffering(
        course_id=course_id,
        faculty_id=faculty_id,
        academic_year=academic_year,
        semester=semester,
        section=section,
        room=room,
    )

    try:
        db.session.add(offering)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "Course offering could not be created due to a data conflict",
        }), 409
    except Exception:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "Course offering could not be created",
        }), 500

    return jsonify({
        "success": True,
        "message": "Course offering created successfully",
        "data": {
            "offering_id": offering.offering_id,
        },
    }), 201


@admin_bp.route("/course-offerings/<int:offering_id>", methods=["PATCH", "PUT"])
@admin_required
def update_course_offering(offering_id):
    offering = db.session.get(CourseOffering, offering_id)

    if not offering:
        return jsonify({
            "success": False,
            "message": "Course offering not found",
        }), 404

    data = request.get_json(silent=True) or {}

    if not data:
        return jsonify({
            "success": False,
            "message": "No fields provided for update",
        }), 400

    if "course_id" in data:
        try:
            course_id = int(data["course_id"])
        except (TypeError, ValueError):
            return jsonify({
                "success": False,
                "message": "Invalid course_id",
            }), 400

        if not db.session.get(Course, course_id):
            return jsonify({
                "success": False,
                "message": "Course not found",
            }), 404

        offering.course_id = course_id

    if "faculty_id" in data:
        raw_faculty_id = data["faculty_id"]

        # Allow the offering to have no assigned faculty.
        if raw_faculty_id is None or str(raw_faculty_id).strip() == "":
            offering.faculty_id = None
        else:
            try:
                faculty_id = int(raw_faculty_id)
            except (TypeError, ValueError):
                return jsonify({
                    "success": False,
                    "message": "Invalid faculty_id",
                }), 400

            if not db.session.get(Faculty, faculty_id):
                return jsonify({
                    "success": False,
                    "message": "Faculty not found",
                }), 404

            offering.faculty_id = faculty_id


    if "semester" in data:
        try:
            semester = int(data["semester"])
        except (TypeError, ValueError):
            return jsonify({
                "success": False,
                "message": "Invalid semester",
            }), 400

        if semester < 1:
            return jsonify({
                "success": False,
                "message": "Semester must be at least 1",
            }), 400

        offering.semester = semester

    if "academic_year" in data:
        academic_year = str(data["academic_year"] or "").strip()
        if not academic_year:
            return jsonify({
                "success": False,
                "message": "Academic year cannot be empty",
            }), 400
        canon_ay = canonical_academic_year(academic_year)
        if not is_single_academic_session(canon_ay):
            return jsonify({
                "success": False,
                "message": "Academic year for course offerings must represent a 1-year academic session (e.g. '2025-2026'), not a cohort range.",
            }), 400
        offering.academic_year = canon_ay

    if "section" in data:
        section = str(data["section"] or "").strip()
        if not section:
            return jsonify({
                "success": False,
                "message": "Section cannot be empty",
            }), 400
        offering.section = section

    if "room" in data:
        offering.room = str(data["room"] or "").strip() or None

    if "batch" in data and offering.course:
        raw_b = str(data.get("batch") or "").strip()
        if raw_b:
            offering.course.batch = raw_b

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "Course offering could not be updated due to a data conflict",
        }), 409
    except Exception:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "Course offering could not be updated",
        }), 500

    return jsonify({
        "success": True,
        "message": "Course offering updated successfully",
    }), 200


@admin_bp.delete("/course-offerings/<int:offering_id>")
@admin_required
def delete_course_offering(offering_id):
    offering = db.session.get(CourseOffering, offering_id)

    if not offering:
        return jsonify({
            "success": False,
            "message": "Course offering not found",
        }), 404

    enrollment_count = Enrollment.query.filter_by(
        offering_id=offering_id
    ).count()

    attendance_session_count = AttendanceSession.query.filter_by(
        offering_id=offering_id
    ).count()

    if enrollment_count or attendance_session_count:
        return jsonify({
            "success": False,
            "message": (
                "Course offering cannot be deleted because it has "
                "enrollments or attendance sessions"
            ),
        }), 409

    try:
        db.session.delete(offering)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": (
                "Course offering cannot be deleted because related records exist"
            ),
        }), 409
    except Exception:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "Course offering could not be deleted",
        }), 500

    return jsonify({
        "success": True,
        "message": "Course offering deleted successfully",
    }), 200


# ============================================================
# FACULTY MANAGEMENT
# ============================================================

@admin_bp.get("/faculty/summary")
@admin_required
def get_faculty_summary():
    total_faculty = Faculty.query.count()
    active_faculty = (
        Faculty.query
        .join(Faculty.user)
        .filter(User.is_active.is_(True))
        .count()
    )
    inactive_faculty = (
        Faculty.query
        .join(Faculty.user)
        .filter(User.is_active.is_(False))
        .count()
    )

    total_departments = Department.query.count()

    # Total classes: course offerings assigned to faculty
    total_classes = CourseOffering.query.filter(
        CourseOffering.faculty_id.isnot(None)
    ).count()

    distinct_courses = (
        db.session.query(CourseOffering.course_id)
        .filter(CourseOffering.faculty_id.isnot(None))
        .distinct()
        .count()
    )

    # Active semesters with assigned faculty offerings
    semester_rows = (
        db.session.query(CourseOffering.semester)
        .filter(
            CourseOffering.faculty_id.isnot(None),
            CourseOffering.semester.isnot(None),
        )
        .distinct()
        .order_by(CourseOffering.semester.asc())
        .all()
    )
    active_semesters = [r[0] for r in semester_rows if r[0] is not None]

    return jsonify({
        "success": True,
        "data": {
            "total_faculty": total_faculty,
            "active_faculty": active_faculty,
            "inactive_faculty": inactive_faculty,
            "total_departments": total_departments,
            "total_classes": total_classes,
            "distinct_courses": distinct_courses,
            "active_semesters": active_semesters,
            "semester_display": ", ".join(str(s) for s in active_semesters) if active_semesters else "N/A",
        },
    }), 200


@admin_bp.get("/faculty/filter-options")
@admin_required
def get_faculty_filter_options():
    departments = Department.query.order_by(
        Department.department_name.asc()
    ).all()
    dept_data = [
        {
            "department_id": d.department_id,
            "department_name": d.department_name,
            "department_code": d.department_code,
        }
        for d in departments
    ]

    semester_rows = (
        db.session.query(CourseOffering.semester)
        .filter(CourseOffering.semester.isnot(None))
        .distinct()
        .order_by(CourseOffering.semester.asc())
        .all()
    )
    semesters = [r[0] for r in semester_rows if r[0] is not None]

    courses = Course.query.order_by(Course.course_code.asc()).all()
    course_data = [
        {
            "course_id": c.course_id,
            "course_code": c.course_code,
            "course_name": c.course_name,
        }
        for c in courses
    ]

    return jsonify({
        "success": True,
        "data": {
            "departments": dept_data,
            "semesters": semesters,
            "courses": course_data,
        },
    }), 200


@admin_bp.get("/faculty")
@admin_required
def get_faculty():
    faculty_members = (
        Faculty.query
        .options(
            joinedload(Faculty.user),
            joinedload(Faculty.department),
            selectinload(Faculty.course_offerings).joinedload(CourseOffering.course),
        )
        .order_by(Faculty.faculty_id.asc())
        .all()
    )

    data = []
    for faculty in faculty_members:
        assigned_courses = sorted(list({
            off.course.course_code
            for off in faculty.course_offerings
            if off.course and off.course.course_code
        }))
        assigned_course_names = sorted(list({
            off.course.course_name
            for off in faculty.course_offerings
            if off.course and off.course.course_name
        }))
        semesters = sorted(list({
            off.semester
            for off in faculty.course_offerings
            if off.semester is not None
        }))

        data.append({
            "faculty_id": faculty.faculty_id,
            "user_id": faculty.user_id,
            "name": faculty.user.name if faculty.user else "N/A",
            "email": faculty.user.email if faculty.user else "N/A",
            "phone": faculty.phone or "",
            "employee_id": faculty.employee_id,
            "designation": faculty.designation,
            "department_id": faculty.department.department_id if faculty.department else None,
            "department_name": faculty.department.department_name if faculty.department else "N/A",
            "department_code": faculty.department.department_code if faculty.department else "N/A",
            "date_of_joining": faculty.date_of_joining or "",
            "qualification": faculty.qualification or "",
            "specialization": faculty.specialization or "",
            "office_cabin": faculty.office_cabin or "",
            "is_active": faculty.user.is_active if faculty.user else False,
            "assigned_courses": assigned_courses,
            "assigned_course_names": assigned_course_names,
            "assigned_classes_count": len(faculty.course_offerings),
            "semesters": semesters,
        })

    return jsonify({
        "success": True,
        "data": data,
    }), 200


@admin_bp.get("/faculty/<int:faculty_id>")
@admin_required
def get_faculty_by_id(faculty_id):
    faculty = (
        Faculty.query
        .options(
            joinedload(Faculty.user),
            joinedload(Faculty.department),
            selectinload(Faculty.course_offerings).joinedload(CourseOffering.course),
            selectinload(Faculty.course_offerings).selectinload(CourseOffering.enrollments),
            selectinload(Faculty.course_offerings).selectinload(CourseOffering.timetable_entries),
        )
        .filter(Faculty.faculty_id == faculty_id)
        .first()
    )

    if not faculty:
        return jsonify({
            "success": False,
            "message": "Faculty not found",
        }), 404

    classes_list = []
    schedule_list = []

    for off in faculty.course_offerings:
        c_code = off.course.course_code if off.course else "N/A"
        c_name = off.course.course_name if off.course else "Unknown Course"
        classes_list.append({
            "offering_id": off.offering_id,
            "course_id": off.course_id,
            "course_code": c_code,
            "course_name": c_name,
            "semester": off.semester,
            "section": off.section,
            "academic_year": off.academic_year,
            "room": off.room or "TBD",
            "enrolled_students": len(off.enrollments),
        })

        for tt in off.timetable_entries:
            start_str = (
                tt.start_time.strftime("%H:%M")
                if hasattr(tt.start_time, "strftime")
                else str(tt.start_time)
            )
            end_str = (
                tt.end_time.strftime("%H:%M")
                if hasattr(tt.end_time, "strftime")
                else str(tt.end_time)
            )
            schedule_list.append({
                "timetable_entry_id": tt.timetable_entry_id,
                "offering_id": off.offering_id,
                "course_code": c_code,
                "course_name": c_name,
                "semester": off.semester,
                "section": off.section,
                "day_of_week": tt.day_of_week,
                "start_time": start_str,
                "end_time": end_str,
                "room": tt.room or off.room or "TBD",
            })

    day_order = {
        "Monday": 1,
        "Tuesday": 2,
        "Wednesday": 3,
        "Thursday": 4,
        "Friday": 5,
        "Saturday": 6,
        "Sunday": 7,
    }
    schedule_list.sort(
        key=lambda x: (day_order.get(x["day_of_week"], 99), x["start_time"])
    )

    assigned_courses = sorted(list({
        off.course.course_code
        for off in faculty.course_offerings
        if off.course and off.course.course_code
    }))
    semesters = sorted(list({
        off.semester
        for off in faculty.course_offerings
        if off.semester is not None
    }))

    return jsonify({
        "success": True,
        "data": {
            "faculty_id": faculty.faculty_id,
            "user_id": faculty.user_id,
            "name": faculty.user.name if faculty.user else "N/A",
            "email": faculty.user.email if faculty.user else "N/A",
            "phone": faculty.phone or "",
            "employee_id": faculty.employee_id,
            "designation": faculty.designation,
            "department_id": faculty.department.department_id if faculty.department else None,
            "department_name": faculty.department.department_name if faculty.department else "N/A",
            "department_code": faculty.department.department_code if faculty.department else "N/A",
            "date_of_joining": faculty.date_of_joining or "",
            "qualification": faculty.qualification or "",
            "specialization": faculty.specialization or "",
            "office_cabin": faculty.office_cabin or "",
            "address": faculty.address or "",
            "city": faculty.city or "",
            "state": faculty.state or "",
            "pin_code": faculty.pin_code or "",
            "country": faculty.country or "India",
            "is_active": faculty.user.is_active if faculty.user else False,
            "assigned_courses": assigned_courses,
            "assigned_classes_count": len(faculty.course_offerings),
            "semesters": semesters,
            "classes": classes_list,
            "schedule": schedule_list,
        },
    }), 200


@admin_bp.post("/faculty")
@admin_required
def create_faculty():
    data = request.get_json(silent=True) or {}

    user_id = data.get("user_id")
    employee_id = str(
        data.get("employee_id", "")
    ).strip()
    designation = str(
        data.get("designation", "")
    ).strip()
    department_id = data.get("department_id")

    # -------------------------
    # Required fields
    # -------------------------

    if (
        user_id is None
        or not employee_id
        or not designation
        or department_id is None
    ):
        return jsonify({
            "success": False,
            "message": (
                "user_id, employee_id, designation and "
                "department_id are required"
            ),
        }), 400

    # -------------------------
    # User ID validation
    # -------------------------

    try:
        user_id = int(user_id)

    except (TypeError, ValueError):
        return jsonify({
            "success": False,
            "message": "User ID must be an integer",
        }), 400

    # -------------------------
    # Department ID validation
    # -------------------------

    try:
        department_id = int(department_id)

    except (TypeError, ValueError):
        return jsonify({
            "success": False,
            "message": "Department ID must be an integer",
        }), 400

    # -------------------------
    # Existing User validation
    # -------------------------

    user = db.session.get(
        User,
        user_id,
    )

    if not user:
        return jsonify({
            "success": False,
            "message": "User not found",
        }), 404

    if user.role != "FACULTY":
        return jsonify({
            "success": False,
            "message": "User role must be FACULTY",
        }), 400

    # -------------------------
    # Existing Faculty profile
    # -------------------------

    existing_faculty_profile = Faculty.query.filter_by(
        user_id=user_id
    ).first()

    if existing_faculty_profile:
        return jsonify({
            "success": False,
            "message": "Faculty profile already exists for this user",
        }), 409

    # -------------------------
    # Duplicate employee ID
    # -------------------------

    existing_faculty = Faculty.query.filter_by(
        employee_id=employee_id
    ).first()

    if existing_faculty:
        return jsonify({
            "success": False,
            "message": "Employee ID already exists",
        }), 409

    # -------------------------
    # Department
    # -------------------------

    department = db.session.get(
        Department,
        department_id,
    )

    if not department:
        return jsonify({
            "success": False,
            "message": "Department not found",
        }), 404

    # -------------------------
    # Create Faculty profile
    # -------------------------

    phone = str(data.get("phone", "")).strip() or None
    date_of_joining = str(data.get("date_of_joining", "")).strip() or None
    qualification = str(data.get("qualification", "")).strip() or None
    specialization = str(data.get("specialization", "")).strip() or None
    office_cabin = str(data.get("office_cabin", "")).strip() or None

    faculty = Faculty(
        user_id=user.user_id,
        department_id=department.department_id,
        employee_id=employee_id,
        designation=designation,
        phone=phone,
        date_of_joining=date_of_joining,
        qualification=qualification,
        specialization=specialization,
        office_cabin=office_cabin,
    )

    try:
        db.session.add(faculty)
        db.session.commit()
        record_activity(
            action_type="FACULTY_CREATED",
            description=f"Created faculty profile for {user.name} ({faculty.employee_id})",
            entity_type="Faculty",
            entity_id=str(faculty.faculty_id),
            details={"name": user.name, "employee_id": faculty.employee_id},
        )
    except IntegrityError:
        db.session.rollback()

        return jsonify({
            "success": False,
            "message": (
                "Faculty could not be created because "
                "of a duplicate or database constraint"
            ),
        }), 409

    except Exception:
        db.session.rollback()

        return jsonify({
            "success": False,
            "message": "Faculty could not be created",
        }), 500

    db.session.refresh(faculty)

    return jsonify({
        "success": True,
        "message": "Faculty profile created successfully",
        "data": {
            "faculty_id": faculty.faculty_id,
            "user_id": user.user_id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "employee_id": faculty.employee_id,
            "designation": faculty.designation,
            "department_id": department.department_id,
            "department_name": department.department_name,
            "department_code": department.department_code,
        },
    }), 201


@admin_bp.patch("/faculty/<int:faculty_id>")
@admin_required
def update_faculty(faculty_id):
    faculty = (
        Faculty.query
        .join(Faculty.user)
        .filter(Faculty.faculty_id == faculty_id)
        .first()
    )

    if not faculty:
        return jsonify({
            "success": False,
            "message": "Faculty not found",
        }), 404

    data = request.get_json(silent=True) or {}

    if not data:
        return jsonify({
            "success": False,
            "message": "No fields provided for update",
        }), 400

    # -------------------------
    # User fields are forbidden
    # -------------------------

    forbidden_fields = {
        "name",
        "email",
        "password",
        "role",
        "user_id",
    }

    supplied_forbidden_fields = (
        forbidden_fields.intersection(data.keys())
    )

    if supplied_forbidden_fields:
        return jsonify({
            "success": False,
            "message": (
                "User fields cannot be updated through the "
                "faculty profile API. Use /api/admin/users/<user_id>"
            ),
            "fields": sorted(supplied_forbidden_fields),
        }), 400

    # -------------------------
    # Employee ID
    # -------------------------

    if "employee_id" in data:
        employee_id = str(
            data["employee_id"]
        ).strip()

        if not employee_id:
            return jsonify({
                "success": False,
                "message": "Employee ID cannot be empty",
            }), 400

        existing_faculty = Faculty.query.filter(
            Faculty.employee_id == employee_id,
            Faculty.faculty_id != faculty_id,
        ).first()

        if existing_faculty:
            return jsonify({
                "success": False,
                "message": "Employee ID already exists",
            }), 409

        faculty.employee_id = employee_id

    # -------------------------
    # Designation
    # -------------------------

    if "designation" in data:
        designation = str(
            data["designation"]
        ).strip()

        if not designation:
            return jsonify({
                "success": False,
                "message": "Designation cannot be empty",
            }), 400

        faculty.designation = designation

    # -------------------------
    # Department
    # -------------------------

    if "department_id" in data:
        try:
            department_id = int(
                data["department_id"]
            )

        except (TypeError, ValueError):
            return jsonify({
                "success": False,
                "message": "Department ID must be an integer",
            }), 400

        department = db.session.get(
            Department,
            department_id,
        )

        if not department:
            return jsonify({
                "success": False,
                "message": "Department not found",
            }), 404

        faculty.department_id = department.department_id

    if "phone" in data:
        faculty.phone = str(data["phone"]).strip() or None
    if "date_of_joining" in data:
        faculty.date_of_joining = str(data["date_of_joining"]).strip() or None
    if "qualification" in data:
        faculty.qualification = str(data["qualification"]).strip() or None
    if "specialization" in data:
        faculty.specialization = str(data["specialization"]).strip() or None
    if "office_cabin" in data:
        faculty.office_cabin = str(data["office_cabin"]).strip() or None

    try:
        db.session.commit()

    except IntegrityError:
        db.session.rollback()

        return jsonify({
            "success": False,
            "message": (
                "Faculty could not be updated because "
                "of a duplicate or database constraint"
            ),
        }), 409

    except Exception:
        db.session.rollback()

        return jsonify({
            "success": False,
            "message": "Faculty could not be updated",
        }), 500

    db.session.refresh(faculty)

    return jsonify({
        "success": True,
        "message": "Faculty updated successfully",
        "data": {
            "faculty_id": faculty.faculty_id,
            "user_id": faculty.user_id,
            "name": faculty.user.name,
            "email": faculty.user.email,
            "employee_id": faculty.employee_id,
            "designation": faculty.designation,
            "department_id": faculty.department.department_id,
            "department_name": faculty.department.department_name,
            "department_code": faculty.department.department_code,
        },
    }), 200


@admin_bp.delete("/faculty/<int:faculty_id>")
@admin_required
def delete_faculty(faculty_id):
    faculty = Faculty.query.filter_by(
        faculty_id=faculty_id
    ).first()

    if not faculty:
        return jsonify({
            "success": False,
            "message": "Faculty not found",
        }), 404

    # -------------------------
    # Course offering safety
    # -------------------------

    course_offering_count = CourseOffering.query.filter_by(
        faculty_id=faculty.faculty_id
    ).count()

    if course_offering_count > 0:
        return jsonify({
            "success": False,
            "message": (
                "Faculty cannot be deleted because "
                "course offerings exist"
            ),
        }), 409

    # -------------------------
    # Attendance session safety
    # -------------------------

    attendance_session_count = AttendanceSession.query.filter_by(
        faculty_id=faculty.faculty_id
    ).count()

    if attendance_session_count > 0:
        return jsonify({
            "success": False,
            "message": (
                "Faculty cannot be deleted because "
                "attendance sessions exist"
            ),
        }), 409

    # -------------------------
    # Linked User safety
    # -------------------------

    user = faculty.user

    if user and user.student_profile:
        return jsonify({
            "success": False,
            "message": (
                "Faculty cannot be deleted because "
                "the linked user has a student profile"
            ),
        }), 409

    try:
        # Delete ONLY the Faculty profile.
        # The linked User account remains.
        db.session.delete(faculty)
        db.session.commit()

    except IntegrityError:
        db.session.rollback()

        return jsonify({
            "success": False,
            "message": (
                "Faculty could not be deleted because "
                "related records exist"
            ),
        }), 409

    except Exception:
        db.session.rollback()

        return jsonify({
            "success": False,
            "message": "Faculty could not be deleted",
        }), 500

    return jsonify({
        "success": True,
        "message": "Faculty profile deleted successfully",
        "data": {
            "faculty_id": faculty_id,
        },
    }), 200
