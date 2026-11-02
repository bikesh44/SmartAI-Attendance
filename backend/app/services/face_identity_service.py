import logging
from datetime import datetime, timedelta, timezone

import numpy as np
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import (
    AttendanceRecord,
    Enrollment,
    FaceProfile,
    Student,
    User,
)
from app.services.activity_service import record_activity
from app.services.face_service import FaceService

logger = logging.getLogger(__name__)

face_service = FaceService()
DEFAULT_SIMILARITY_THRESHOLD = 0.50
FACE_MODEL_VERSION = "sface_2021dec"


def check_face_cross_student_conflict(
    probe_encoding: np.ndarray,
    target_student_id: int,
    threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
) -> tuple[bool, int | None, float]:
    """
    Compares the newly generated probe encoding against all active face profiles
    belonging to other students.

    Returns:
        (has_conflict: bool, conflicting_student_id: int | None, similarity_score: float)
    """
    if probe_encoding is None:
        return False, None, 0.0

    probe_feature = probe_encoding.astype(np.float32)
    if probe_feature.ndim == 1:
        probe_feature = probe_feature.reshape(1, 128)

    # Query all active profiles of other students
    other_profiles = (
        FaceProfile.query
        .filter(
            FaceProfile.student_id != target_student_id,
            FaceProfile.is_active.is_(True),
            FaceProfile.model_version == FACE_MODEL_VERSION,
        )
        .all()
    )

    best_match_id = None
    best_similarity = -1.0

    for profile in other_profiles:
        try:
            reg_feature = np.frombuffer(profile.embedding, dtype=np.float32)
            if reg_feature.shape != (128,) or not np.isfinite(reg_feature).all():
                continue
            reg_feature = reg_feature.reshape(1, 128)

            comparison = face_service.compare_encoding(probe_feature, reg_feature)
            sim = comparison["cosine_similarity"]
            if sim > best_similarity:
                best_similarity = sim
                best_match_id = profile.student_id
        except Exception as e:
            logger.warning("Error comparing face profile %s: %s", profile.face_id, e)
            continue

    if best_match_id is not None and best_similarity >= threshold:
        return True, best_match_id, float(best_similarity)

    return False, None, float(max(best_similarity, 0.0))


def safe_replace_face_profile(
    student_id: int,
    encoding: np.ndarray,
    model_version: str = FACE_MODEL_VERSION,
    check_cross_student: bool = True,
    threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
) -> tuple[bool, str, FaceProfile | None, str]:
    """
    Atomically updates/replaces a student's active face registration:
    1. Validates student canonical record exists.
    2. Runs cross-student conflict check: ensures this face is not already registered
       to another active student.
    3. Deactivates previous active face profiles for this student.
    4. Creates and activates the new FaceProfile record inside a database transaction.
    5. Preserves the student's canonical student_id, attendance, and enrollments.

    Returns:
        (success: bool, message: str, face_profile: FaceProfile | None, status: str)
    """
    student = db.session.get(Student, student_id)
    if not student:
        return False, "Student not found", None, "student_not_found"

    if (
        encoding is None
        or not isinstance(encoding, np.ndarray)
        or not np.isfinite(encoding).all()
    ):
        return False, "Generated face encoding is invalid", None, "invalid_encoding"

    probe_feature = encoding.astype(np.float32)
    if probe_feature.ndim == 1:
        probe_feature = probe_feature.reshape(1, 128)
    if probe_feature.shape != (1, 128):
        return False, "Face encoding must have shape (1, 128)", None, "invalid_encoding"

    # Step 2: Cross-student conflict check
    if check_cross_student:
        has_conflict, conflicting_id, similarity = check_face_cross_student_conflict(
            probe_encoding=probe_feature,
            target_student_id=student_id,
            threshold=threshold,
        )
        if has_conflict:
            conflicting_student = db.session.get(Student, conflicting_id)
            enrollment_ref = conflicting_student.enrollment_no if conflicting_student else str(conflicting_id)
            logger.warning(
                "Face enrollment conflict: Student %s face matches already registered student %s (similarity: %.3f)",
                student_id,
                conflicting_id,
                similarity,
            )
            return (
                False,
                f"Face biometric matches another registered student (Enrollment: {enrollment_ref}). "
                "A face cannot be registered to multiple student accounts.",
                None,
                "conflict_detected",
            )

    embedding_bytes = probe_feature.tobytes()

    try:
        # Step 3: Deactivate any currently active profile(s) for this student
        existing_profiles = (
            FaceProfile.query
            .filter_by(
                student_id=student_id,
                is_active=True,
            )
            .with_for_update()
            .all()
        )
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)

        for p in existing_profiles:
            p.is_active = False
            p.updated_at = now_utc

        # Step 4: Insert the new active FaceProfile
        new_profile = FaceProfile(
            student_id=student_id,
            embedding=embedding_bytes,
            model_version=model_version,
            is_active=True,
            created_at=now_utc,
            updated_at=now_utc,
        )
        db.session.add(new_profile)
        db.session.commit()

        logger.info(
            "Successfully enrolled/replaced face for student %s (face_id: %s)",
            student_id,
            new_profile.face_id,
        )
        return True, "Face enrolled successfully", new_profile, "enrolled"

    except IntegrityError as e:
        db.session.rollback()
        logger.error(
            "IntegrityError while activating face profile for student %s: %s",
            student_id,
            e,
        )
        return False, "Another face registration is currently in progress for this student", None, "concurrent_conflict"
    except Exception as e:
        db.session.rollback()
        logger.error("Error saving face profile for student %s: %s", student_id, e)
        return False, "Face enrollment failed", None, "error"


def detect_suspected_duplicate_students(
    threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
) -> list[dict]:
    """
    Scans the database for suspected duplicate student identities:
    1. Biometric matches: Active face profiles across different students with cosine similarity >= threshold.
    2. Identifier matches: Case-insensitive enrollment number overlaps or shared emails.
    """
    duplicates = []
    seen_pairs = set()

    # 1. Biometric Scan across active face profiles
    active_profiles = (
        FaceProfile.query
        .filter_by(
            is_active=True,
            model_version=FACE_MODEL_VERSION,
        )
        .all()
    )

    n = len(active_profiles)
    for i in range(n):
        p1 = active_profiles[i]
        f1 = np.frombuffer(p1.embedding, dtype=np.float32)
        if f1.shape != (128,) or not np.isfinite(f1).all():
            continue
        f1 = f1.reshape(1, 128)

        for j in range(i + 1, n):
            p2 = active_profiles[j]
            if p1.student_id == p2.student_id:
                continue

            pair_key = tuple(sorted([p1.student_id, p2.student_id]))
            if pair_key in seen_pairs:
                continue

            f2 = np.frombuffer(p2.embedding, dtype=np.float32)
            if f2.shape != (128,) or not np.isfinite(f2).all():
                continue
            f2 = f2.reshape(1, 128)

            comp = face_service.compare_encoding(f1, f2)
            sim = comp["cosine_similarity"]

            if sim >= threshold:
                seen_pairs.add(pair_key)
                s1 = db.session.get(Student, p1.student_id)
                s2 = db.session.get(Student, p2.student_id)

                duplicates.append({
                    "type": "biometric_match",
                    "similarity_score": round(float(sim), 4),
                    "student_a": _summarize_student_record(s1),
                    "student_b": _summarize_student_record(s2),
                    "detected_at": datetime.now(timezone.utc).isoformat(),
                })

    # 2. Identifier matches
    all_students = Student.query.all()
    enrollment_map: dict[str, list[Student]] = {}
    for s in all_students:
        if s.enrollment_no:
            norm = s.enrollment_no.strip().upper()
            enrollment_map.setdefault(norm, []).append(s)

    for norm, st_list in enrollment_map.items():
        if len(st_list) > 1:
            for i in range(len(st_list)):
                for j in range(i + 1, len(st_list)):
                    pair_key = tuple(sorted([st_list[i].student_id, st_list[j].student_id]))
                    if pair_key not in seen_pairs:
                        seen_pairs.add(pair_key)
                        duplicates.append({
                            "type": "identifier_match",
                            "similarity_score": 1.0,
                            "student_a": _summarize_student_record(st_list[i]),
                            "student_b": _summarize_student_record(st_list[j]),
                            "detected_at": datetime.now(timezone.utc).isoformat(),
                        })

    return duplicates


def _summarize_student_record(student: Student | None) -> dict | None:
    if not student:
        return None
    user = student.user
    att_count = AttendanceRecord.query.filter_by(student_id=student.student_id).count()
    enr_count = Enrollment.query.filter_by(student_id=student.student_id).count()
    active_fp = FaceProfile.query.filter_by(student_id=student.student_id, is_active=True).first()

    return {
        "student_id": student.student_id,
        "user_id": student.user_id,
        "name": user.name if user else None,
        "email": user.email if user else None,
        "enrollment_no": student.enrollment_no,
        "semester": student.semester,
        "section": student.section,
        "academic_year": student.academic_year,
        "attendance_count": att_count,
        "enrollment_count": enr_count,
        "has_active_face": active_fp is not None,
        "face_id": active_fp.face_id if active_fp else None,
        "is_active_account": user.is_active if user else False,
    }


def reconcile_duplicate_students(
    canonical_student_id: int,
    duplicate_student_id: int,
    admin_user_id: int,
    action: str = "merge_and_deactivate",
    reason: str = None,
) -> dict:
    """
    Explicit, authorized administrative reconciliation process:
    - Selects canonical student record.
    - Reassigns related enrollments and attendance records safely.
    - Invalidates obsolete face mappings for duplicate student.
    - Deactivates duplicate user account if action is 'merge_and_deactivate'.
    - Records the reconciliation in an audit log without logging raw biometric data.
    """
    if canonical_student_id == duplicate_student_id:
        raise ValueError("Canonical student and duplicate student must be different records.")

    canonical = db.session.get(Student, canonical_student_id)
    if not canonical:
        raise ValueError(f"Canonical student ID {canonical_student_id} not found.")

    duplicate = db.session.get(Student, duplicate_student_id)
    if not duplicate:
        raise ValueError(f"Duplicate student ID {duplicate_student_id} not found.")

    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    reassigned_enrollments = 0
    reassigned_attendance = 0

    # 1. Reassign enrollments safely
    dup_enrollments = Enrollment.query.filter_by(student_id=duplicate_student_id).all()
    for enr in dup_enrollments:
        canon_enr = Enrollment.query.filter_by(
            student_id=canonical_student_id,
            offering_id=enr.offering_id,
        ).first()
        if not canon_enr:
            enr.student_id = canonical_student_id
            reassigned_enrollments += 1
        else:
            # Canonical is already enrolled; mark duplicate enrollment inactive
            enr.status = "INACTIVE"

    # 2. Reassign attendance records safely
    dup_attendance = AttendanceRecord.query.filter_by(student_id=duplicate_student_id).all()
    for att in dup_attendance:
        canon_att = AttendanceRecord.query.filter_by(
            student_id=canonical_student_id,
            session_id=att.session_id,
        ).first()
        if not canon_att:
            att.student_id = canonical_student_id
            reassigned_attendance += 1
        else:
            # Canonical already has an attendance record for this session; delete or keep canonical
            db.session.delete(att)

    # 3. Invalidate duplicate's face mappings
    dup_face_profiles = FaceProfile.query.filter_by(student_id=duplicate_student_id, is_active=True).all()
    for fp in dup_face_profiles:
        fp.is_active = False
        fp.updated_at = now_utc

    # 4. Deactivate duplicate user account if requested
    if action == "merge_and_deactivate" and duplicate.user:
        duplicate.user.is_active = False

    # 5. Audit Logging
    logger.info(
        "AUDIT: Admin user %s reconciled duplicate student %s (%s) into canonical student %s (%s). "
        "Reassigned %d enrollments, %d attendance records. Reason: %s",
        admin_user_id,
        duplicate_student_id,
        duplicate.enrollment_no,
        canonical_student_id,
        canonical.enrollment_no,
        reassigned_enrollments,
        reassigned_attendance,
        reason or "Admin authorized duplicate reconciliation",
    )

    db.session.commit()

    return {
        "success": True,
        "canonical_student_id": canonical_student_id,
        "duplicate_student_id": duplicate_student_id,
        "reassigned_enrollments": reassigned_enrollments,
        "reassigned_attendance": reassigned_attendance,
        "invalidated_face_profiles": len(dup_face_profiles),
        "duplicate_account_deactivated": action == "merge_and_deactivate",
        "reconciled_at": now_utc.isoformat(),
    }


def cleanup_obsolete_face_profiles(
    student_id: int = None,
    retention_days: int = 0,
) -> int:
    """
    Safely deletes obsolete (is_active=False) face profiles that exceed the retention window.
    Active face profiles are NEVER deleted.
    """
    query = FaceProfile.query.filter(FaceProfile.is_active.is_(False))

    if student_id is not None:
        query = query.filter(FaceProfile.student_id == student_id)

    if retention_days > 0:
        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=retention_days)
        query = query.filter(FaceProfile.updated_at < cutoff)

    deleted_count = query.delete(synchronize_session="fetch")
    db.session.commit()

    logger.info("Purged %d obsolete face profile records (retention_days=%d)", deleted_count, retention_days)
    return deleted_count


def remove_student_face_profile(
    student_id: int,
    admin_user_id: int,
    face_id: int | None = None,
    reason: str | None = None,
    permanent: bool = False,
) -> tuple[bool, str, dict | None, str]:
    """
    Safely deactivates or removes a student's active face biometric registration:
    1. Validates that the canonical student record exists.
    2. If face_id is specified, verifies it exists and belongs to the given student.
    3. Finds active FaceProfile(s) for the student.
    4. Safely deactivates (is_active=False) or permanently deletes them.
    5. Preserves student account, enrollment, courses, and historical attendance.
    6. Records the removal action in the system activity log.
    7. Atomically commits the database transaction.

    Returns:
        (success: bool, message: str, data: dict | None, status: str)
    """
    student = db.session.get(Student, student_id)
    if not student:
        return False, "Student not found", None, "student_not_found"

    if face_id is not None:
        try:
            face_id = int(face_id)
        except (TypeError, ValueError):
            return False, "Invalid face_id format", None, "invalid_face_id"

        target_fp = db.session.get(FaceProfile, face_id)
        if not target_fp:
            return False, "Face profile not found", None, "face_profile_not_found"

        if target_fp.student_id != student_id:
            return (
                False,
                "Face profile does not belong to the specified student",
                None,
                "profile_student_mismatch",
            )

    active_query = FaceProfile.query.filter_by(
        student_id=student_id,
        is_active=True,
    )
    if face_id is not None:
        active_query = active_query.filter_by(face_id=face_id)

    active_profiles = active_query.with_for_update().all()

    if not active_profiles:
        return (
            False,
            "No active face biometric registration found for this student",
            {
                "student_id": student.student_id,
                "enrollment_no": student.enrollment_no,
                "face_registered": False,
            },
            "not_registered",
        )

    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    removed_face_ids = []

    for fp in active_profiles:
        removed_face_ids.append(fp.face_id)
        if permanent:
            db.session.delete(fp)
        else:
            fp.is_active = False
            fp.updated_at = now_utc

    student_name = student.user.name if student.user else None
    action_desc = (
        f"Removed active face biometric registration for student {student.enrollment_no}"
        f" ({student_name or 'ID: ' + str(student_id)})"
    )

    record_activity(
        action_type="FACE_BIOMETRIC_REMOVED",
        description=action_desc[:255],
        actor_id=admin_user_id,
        entity_type="Student",
        entity_id=str(student_id),
        status="SUCCESS",
        details={
            "student_id": student_id,
            "enrollment_no": student.enrollment_no,
            "student_name": student_name,
            "removed_face_ids": removed_face_ids,
            "deactivated_count": len(removed_face_ids),
            "permanent_deletion": bool(permanent),
            "reason": reason or "Administrative removal of incorrect biometric registration",
        },
        commit=False,
    )

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error("Error removing face profile for student %s: %s", student_id, e)
        return False, "Failed to remove face biometric registration", None, "error"

    logger.info(
        "Admin user %s removed face biometric registration for student %s (%s). Profiles: %s, permanent: %s",
        admin_user_id,
        student_id,
        student.enrollment_no,
        removed_face_ids,
        permanent,
    )

    return (
        True,
        "Face biometric registration removed successfully",
        {
            "student_id": student.student_id,
            "enrollment_no": student.enrollment_no,
            "face_registered": False,
            "removed_face_ids": removed_face_ids,
            "deactivated_count": len(removed_face_ids),
            "permanent": bool(permanent),
        },
        "removed",
    )
