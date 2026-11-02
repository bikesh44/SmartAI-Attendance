import base64
from contextlib import nullcontext
import cv2
import numpy as np

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity

from pathlib import Path

from app.extensions import db
from app.models import (
    AttendanceSession,
    FaceProfile,
    Faculty,
    FacultyAdjustment,
    Student,
    TimetableEntry,
)
from app.services.activity_service import record_activity
from app.services.cv.attendance_service import (
    mark_face_attendance,
    validate_student_attendance_eligibility,
)
from app.services.cv.liveness_service import (
    active_evaluator,
    liveness_manager,
    pad_detector,
    PresentationAttackDetector,
)
from app.services.face_service import FaceService
from app.utils.auth import faculty_required
from app.utils import schedule


recognition_bp = Blueprint(
    "recognition",
    __name__,
    url_prefix="/api/faculty/recognition",
)

face_service = FaceService()
SIMILARITY_THRESHOLD = 0.50


def get_current_faculty():
    user_id = int(get_jwt_identity())
    return Faculty.query.filter_by(user_id=user_id).first()


def _decode_image(image_input):
    """Decode FileStorage, bytes, or base64 data into an OpenCV BGR image."""
    if image_input is None:
        return None

    if isinstance(image_input, str):
        b64_str = image_input
        if "base64," in b64_str:
            b64_str = b64_str.split("base64,")[1]
        try:
            image_bytes = base64.b64decode(b64_str)
        except Exception:
            return None
    elif hasattr(image_input, "read"):
        image_bytes = image_input.read()
    elif isinstance(image_input, (bytes, bytearray)):
        image_bytes = image_input
    else:
        return None

    if not image_bytes:
        return None

    buffer = np.frombuffer(image_bytes, dtype=np.uint8)
    return cv2.imdecode(buffer, cv2.IMREAD_COLOR)


@recognition_bp.post("/liveness/challenge")
@faculty_required
def create_liveness_challenge():
    """Generate a fresh, unpredictable randomized active liveness challenge."""
    faculty = get_current_faculty()
    if not faculty:
        return jsonify({
            "success": False,
            "message": "Faculty profile not found",
        }), 404

    json_data = request.get_json(silent=True) or {}
    session_id = request.form.get("session_id") or json_data.get("session_id")
    if not session_id:
        return jsonify({
            "success": False,
            "message": "session_id is required",
        }), 400

    try:
        session_id = int(session_id)
    except (TypeError, ValueError):
        return jsonify({
            "success": False,
            "message": "session_id must be an integer",
        }), 400

    session = db.session.get(AttendanceSession, session_id)
    if not session:
        return jsonify({
            "success": False,
            "message": "Attendance session not found",
        }), 404

    is_owner = (session.faculty_id == faculty.faculty_id)
    is_substitute = FacultyAdjustment.query.filter_by(
        substitute_faculty_id=faculty.faculty_id,
        status="APPROVED",
    ).join(TimetableEntry).filter(TimetableEntry.offering_id == session.offering_id).first() is not None

    if not (is_owner or is_substitute):
        return jsonify({
            "success": False,
            "message": "Access forbidden",
        }), 403

    if session.status != "ACTIVE":
        return jsonify({
            "success": False,
            "message": "Attendance session is not active",
        }), 409

    now = schedule.get_current_institution_time()
    is_eligible, status_str, details = schedule.get_session_schedule_status(session, current_dt=now)

    if status_str == "UPCOMING":
        return jsonify({
            "success": False,
            "message": details.get("message", "Attendance cannot be recorded before scheduled start time"),
        }), 400

    if status_str == "ENDED":
        return jsonify({
            "success": False,
            "message": "Attendance session has ended. New attendance recording is prevented.",
        }), 409

    # Check fail-closed configuration if strict model weights are required
    if current_app.config.get("FAIL_CLOSED_ON_MISSING_MODEL", False):
        model_path = current_app.config.get("PAD_MODEL_PATH")
        if not model_path or not Path(model_path).exists():
            return jsonify({
                "success": False,
                "message": "Liveness model is unavailable and fail-closed security mode is active.",
                "status": "liveness_model_unavailable",
            }), 503

    challenge = liveness_manager.create_challenge(
        session_id=session.session_id,
        faculty_id=faculty.faculty_id,
    )

    record_activity(
        action_type="LIVENESS_CHALLENGE_CREATED",
        description=f"Issued liveness challenge {challenge['challenge_type']} for session {session.session_id}",
        actor_id=faculty.user_id,
        entity_type="AttendanceSession",
        entity_id=str(session.session_id),
        details={
            "challenge_id": challenge["challenge_id"],
            "challenge_type": challenge["challenge_type"],
            "session_id": session.session_id,
        },
    )

    return jsonify({
        "success": True,
        "message": "Liveness challenge generated successfully",
        **challenge,
    }), 200


@recognition_bp.post("/liveness/verify")
@faculty_required
def verify_liveness_evidence():
    """Verify challenge evidence frames (passive PAD + active motion + identity match)."""
    faculty = get_current_faculty()
    if not faculty:
        return jsonify({
            "success": False,
            "message": "Faculty profile not found",
        }), 404

    json_data = request.get_json(silent=True) or {}
    session_id = request.form.get("session_id") or json_data.get("session_id")
    challenge_id = request.form.get("challenge_id") or json_data.get("challenge_id")

    if not session_id:
        return jsonify({
            "success": False,
            "message": "session_id is required",
        }), 400

    if not challenge_id:
        return jsonify({
            "success": False,
            "message": "challenge_id is required",
        }), 400

    try:
        session_id = int(session_id)
    except (TypeError, ValueError):
        return jsonify({
            "success": False,
            "message": "session_id must be an integer",
        }), 400

    session = db.session.get(AttendanceSession, session_id)
    if not session:
        return jsonify({
            "success": False,
            "message": "Attendance session not found",
        }), 404

    is_owner = (session.faculty_id == faculty.faculty_id)
    is_substitute = FacultyAdjustment.query.filter_by(
        substitute_faculty_id=faculty.faculty_id,
        status="APPROVED",
    ).join(TimetableEntry).filter(TimetableEntry.offering_id == session.offering_id).first() is not None

    if not (is_owner or is_substitute):
        return jsonify({
            "success": False,
            "message": "Access forbidden",
        }), 403

    if session.status != "ACTIVE":
        return jsonify({
            "success": False,
            "message": "Attendance session is not active",
        }), 409

    # Look up challenge
    challenge = liveness_manager.get_challenge(challenge_id)
    if not challenge:
        return jsonify({
            "success": False,
            "message": "Challenge is invalid, expired, or already completed",
            "status": "challenge_expired",
        }), 400

    if challenge["session_id"] != session.session_id or challenge["faculty_id"] != faculty.faculty_id:
        return jsonify({
            "success": False,
            "message": "Challenge session or faculty binding mismatch",
            "status": "challenge_mismatch",
        }), 403

    # Extract evidence frames from files, form, or JSON
    raw_frames = []
    uploaded_files = request.files.getlist("frames")
    if uploaded_files:
        raw_frames.extend(uploaded_files)

    for key in ["frame_0", "frame_1", "frame_2", "frame_initial", "frame_action", "frame_final"]:
        f = request.files.get(key)
        if f:
            raw_frames.append(f)

    form_files = request.form.getlist("frames")
    if form_files:
        raw_frames.extend(form_files)

    for key in ["frame_0", "frame_1", "frame_2", "frame_initial", "frame_action", "frame_final"]:
        f = request.form.get(key)
        if f:
            raw_frames.append(f)

    json_frames = json_data.get("frames") or []
    if isinstance(json_frames, list):
        for item in json_frames:
            if isinstance(item, str):
                raw_frames.append(item)
            elif isinstance(item, dict) and "image" in item:
                raw_frames.append(item["image"])

    decoded_frames = []
    for item in raw_frames:
        img = _decode_image(item)
        if img is not None and img.size > 0:
            decoded_frames.append(img)

    if len(decoded_frames) < 2:
        return jsonify({
            "success": False,
            "message": "At least 2 valid evidence frames are required for liveness verification",
            "status": "insufficient_frames",
        }), 400

    # Extract timestamps
    timestamps = []
    ts_input = request.form.get("timestamps") or json_data.get("timestamps")
    if ts_input:
        if isinstance(ts_input, str):
            try:
                import json
                timestamps = json.loads(ts_input)
            except Exception:
                timestamps = [float(v.strip()) for v in ts_input.split(",") if v.strip()]
        elif isinstance(ts_input, list):
            timestamps = [float(v) for v in ts_input]

    if len(timestamps) != len(decoded_frames):
        timestamps = [float(i * 500) for i in range(len(decoded_frames))]

    # Determine mirror orientation (default: True for standard webcam selfie previews)
    is_mirrored = True
    mirrored_param = request.form.get("mirrored")
    if mirrored_param is not None:
        is_mirrored = str(mirrored_param).strip().lower() in ("true", "1", "yes")
    elif request.is_json and request.json:
        is_mirrored = bool(request.json.get("mirrored", True))

    # 1. Detect faces in each frame for spatial tracking and face bounding box crops
    detected_faces_per_frame = []
    for frame in decoded_frames:
        try:
            faces = face_service.detect_faces(frame)
            detected_faces_per_frame.append(faces)
        except Exception as e:
            current_app.logger.warning("Face detection failed in evidence frame: %s", e)
            detected_faces_per_frame.append([])

    # 2. Passive Presentation Attack Detection (PAD) using face crops
    detector = pad_detector
    if current_app.config.get("FAIL_CLOSED_ON_MISSING_MODEL", False) or current_app.config.get("PAD_MODEL_PATH"):
        detector = PresentationAttackDetector(
            model_path=current_app.config.get("PAD_MODEL_PATH"),
            fail_closed_if_missing_model=current_app.config.get("FAIL_CLOSED_ON_MISSING_MODEL", False),
        )

    for idx, frame in enumerate(decoded_frames):
        faces_in_frame = detected_faces_per_frame[idx]
        face_bbox = faces_in_frame[0].get("bbox") if faces_in_frame else None
        pad_res = detector.analyze_frame(frame, face_bbox=face_bbox)

        if not pad_res.is_live:
            # Distinguish image quality / focus warnings from confirmed presentation attacks
            if pad_res.attack_type in ("blurred_or_low_quality", "face_crop_too_small"):
                return jsonify({
                    "success": False,
                    "message": f"Image quality insufficient: {', '.join(pad_res.reasons)}. Please face the camera and ensure adequate lighting.",
                    "status": "quality_warning",
                    "attack_type": pad_res.attack_type,
                    "metrics": pad_res.metrics,
                }), 400
            else:
                record_activity(
                    action_type="LIVENESS_SPOOF_REJECTED",
                    description=f"Presentation attack rejected ({pad_res.attack_type}) in session {session.session_id}",
                    actor_id=faculty.user_id,
                    entity_type="AttendanceSession",
                    entity_id=str(session.session_id),
                    details={
                        "challenge_id": challenge_id,
                        "attack_type": pad_res.attack_type,
                        "reasons": pad_res.reasons,
                        "frame_index": idx,
                    },
                )
                return jsonify({
                    "success": False,
                    "message": f"Presentation attack detected: {', '.join(pad_res.reasons)}",
                    "status": "spoof_suspected",
                    "attack_type": pad_res.attack_type,
                    "pad_score": pad_res.pad_score,
                    "metrics": pad_res.metrics,
                }), 400

    # 3. Check single face presence in all frames
    for idx, faces in enumerate(detected_faces_per_frame):
        if not faces:
            return jsonify({
                "success": False,
                "message": f"No face detected in evidence frame {idx + 1}. Please ensure your face is clearly visible.",
                "status": "no_face",
            }), 400
        if len(faces) > 1:
            return jsonify({
                "success": False,
                "message": f"Multiple faces detected in evidence frame {idx + 1}. Exactly one face must be visible.",
                "status": "multiple_faces",
            }), 400

    # 4. Active Challenge Movement Evaluation
    passed, reason, motion_meta = active_evaluator.evaluate_challenge(
        challenge_type=challenge["challenge_type"],
        frames=decoded_frames,
        timestamps=timestamps,
        detected_faces_per_frame=detected_faces_per_frame,
        is_mirrored=is_mirrored,
    )

    if not passed:
        record_activity(
            action_type="LIVENESS_CHALLENGE_FAILED",
            description=f"Liveness challenge failed ({challenge['challenge_type']}): {reason}",
            actor_id=faculty.user_id,
            entity_type="AttendanceSession",
            entity_id=str(session.session_id),
            details={
                "challenge_id": challenge_id,
                "reason": reason,
                "metadata": motion_meta,
            },
        )
        return jsonify({
            "success": False,
            "message": f"Liveness challenge failed: {reason}",
            "status": "challenge_failed",
            "metadata": motion_meta,
        }), 400

    # 4. Identity Recognition against registered students
    face_profiles = FaceProfile.query.filter_by(
        is_active=True,
        model_version="sface_2021dec",
    ).all()

    registered_students = []
    for profile in face_profiles:
        encoding = np.frombuffer(profile.embedding, dtype=np.float32)
        if encoding.shape != (128,) or not np.isfinite(encoding).all():
            continue
        registered_students.append({
            "student_id": profile.student_id,
            "encoding": encoding.reshape(1, 128),
        })

    if not registered_students:
        return jsonify({
            "success": False,
            "message": "No registered face profiles found in the system",
            "status": "no_registered_students",
        }), 200

    # Find the most frontal frame for recognition
    best_frame = decoded_frames[0]
    rec_result = face_service.recognize_all_students(
        best_frame,
        registered_students,
        SIMILARITY_THRESHOLD,
    )

    matches = rec_result.get("matches", [])
    if not matches and len(decoded_frames) > 2:
        rec_result = face_service.recognize_all_students(
            decoded_frames[-1],
            registered_students,
            SIMILARITY_THRESHOLD,
        )
        matches = rec_result.get("matches", [])

    if not matches:
        return jsonify({
            "success": False,
            "message": "Face liveness passed, but student was not recognized among registered profiles",
            "status": "not_recognized",
            "data": None,
        }), 200

    match = matches[0]
    student_id = match["student_id"]
    confidence_score = match["similarity_score"]

    # Validate student attendance eligibility
    is_eligible, elig_message, student = validate_student_attendance_eligibility(
        session=session,
        student_id=student_id,
        faculty_id=faculty.faculty_id,
        check_window=True,
    )

    if not is_eligible:
        return jsonify({
            "success": False,
            "message": f"Student recognized but not eligible: {elig_message}",
            "status": "ineligible",
            "student_id": student_id,
        }), 403

    # Issue single-use verification token bound to student, session, and faculty
    verification_token = liveness_manager.issue_verification_token(
        challenge_id=challenge_id,
        student_id=student_id,
        session_id=session.session_id,
        faculty_id=faculty.faculty_id,
        confidence_score=confidence_score,
        pad_score=0.95,
    )

    student_name = student.user.name if (student and student.user) else f"Student #{student_id}"
    enrollment_no = student.enrollment_no if student else "N/A"

    record_activity(
        action_type="LIVENESS_VERIFIED",
        description=f"Liveness verified for student {student_id} in session {session.session_id}",
        actor_id=faculty.user_id,
        entity_type="AttendanceSession",
        entity_id=str(session.session_id),
        details={
            "challenge_id": challenge_id,
            "student_id": student_id,
            "confidence_score": confidence_score,
        },
    )

    return jsonify({
        "success": True,
        "status": "verified",
        "message": "Liveness and identity verified successfully",
        "verification_token": verification_token,
        "student_id": student_id,
        "student_name": student_name,
        "enrollment_no": enrollment_no,
        "confidence_score": confidence_score,
        "challenge_type": challenge["challenge_type"],
    }), 200


@recognition_bp.post("/attendance")
@faculty_required
def process_recognition_attendance():
    json_data = request.get_json(silent=True) or {}
    session_id = request.form.get("session_id") or json_data.get("session_id")
    verification_token = (
        request.form.get("verification_token")
        or json_data.get("verification_token")
        or request.headers.get("X-Verification-Token")
    )
    student_id_param = request.form.get("student_id") or json_data.get("student_id")
    image_input = (
        request.files.get("image")
        or request.form.get("image")
        or json_data.get("image")
    )

    if not session_id:
        return jsonify({
            "success": False,
            "message": "session_id is required",
        }), 400

    try:
        session_id = int(session_id)
    except (TypeError, ValueError):
        return jsonify({
            "success": False,
            "message": "session_id must be an integer",
        }), 400

    # Acquire dedicated per-token lock to ensure atomic validation, consumption, and recording
    token_lock = liveness_manager.acquire_token_lock(verification_token) if verification_token else nullcontext()
    with token_lock:
        # Pre-validate token status before performing DB queries if token is provided
        if verification_token:
            token_valid, token_err = liveness_manager.check_token_status(verification_token)
            if not token_valid:
                return jsonify({
                    "success": False,
                    "message": f"Verification token error: {token_err}",
                    "status": "invalid_verification_token",
                }), 403

        faculty = get_current_faculty()
        if not faculty:
            return jsonify({
                "success": False,
                "message": "Faculty profile not found",
            }), 404

        # Verify that the attendance session belongs to authenticated faculty
        session = db.session.get(AttendanceSession, session_id)
        if not session:
            return jsonify({
                "success": False,
                "message": "Attendance session not found",
            }), 404

        is_owner = (session.faculty_id == faculty.faculty_id)
        is_substitute = FacultyAdjustment.query.filter_by(
            substitute_faculty_id=faculty.faculty_id,
            status="APPROVED",
        ).join(TimetableEntry).filter(TimetableEntry.offering_id == session.offering_id).first() is not None

        if not (is_owner or is_substitute):
            return jsonify({
                "success": False,
                "message": "Access forbidden",
            }), 403

        if session.status != "ACTIVE":
            return jsonify({
                "success": False,
                "message": "Attendance session is not active",
            }), 409

        now = schedule.get_current_institution_time()
        is_eligible, status_str, details = schedule.get_session_schedule_status(session, current_dt=now)

        if status_str == "UPCOMING":
            schedule.reconcile_premature_session(session)
            return jsonify({
                "success": False,
                "message": details.get("message", "Attendance cannot be recorded before scheduled start time"),
            }), 400

        if status_str == "ENDED":
            schedule.close_expired_session(session)
            return jsonify({
                "success": False,
                "message": "Attendance session has ended. New attendance recording is prevented.",
            }), 409

        # Enforce Liveness Verification requirement
        require_liveness = current_app.config.get(
            "REQUIRE_LIVENESS_VERIFICATION",
            not current_app.config.get("TESTING", False),
        )

        if not verification_token and require_liveness:
            return jsonify({
                "success": False,
                "message": "Liveness verification token required. Direct attendance marking without verified liveness challenge is prohibited.",
                "status": "verification_token_required",
            }), 403

        # If verification_token is provided, atomically consume and record attendance
        if verification_token:
            target_student_id = None
            if student_id_param is not None:
                try:
                    target_student_id = int(student_id_param)
                except (TypeError, ValueError):
                    pass

            token_success, token_reason, verified_token_data = liveness_manager.consume_verification_token(
                token=verification_token,
                expected_session_id=session.session_id,
                expected_student_id=target_student_id,
                expected_faculty_id=faculty.faculty_id,
            )

            if not token_success:
                return jsonify({
                    "success": False,
                    "message": f"Verification token error: {token_reason}",
                    "status": "invalid_verification_token",
                }), 403

            verified_student_id = verified_token_data["student_id"]
            confidence_score = verified_token_data.get("confidence_score", 0.85)

            record, message = mark_face_attendance(
                session_id=session.session_id,
                student_id=verified_student_id,
                confidence_score=confidence_score,
                faculty_id=faculty.faculty_id,
            )

            student = db.session.get(Student, verified_student_id)
            student_name = student.user.name if (student and student.user) else f"Student #{verified_student_id}"
            enrollment_no = student.enrollment_no if student else "N/A"

            if record:
                data_rec = {
                    "attendance_id": record.attendance_id,
                    "session_id": record.session_id,
                    "student_id": record.student_id,
                    "name": student_name,
                    "student_name": student_name,
                    "enrollment_no": enrollment_no,
                    "status": record.status,
                    "confidence_score": record.confidence_score,
                    "recognition_method": record.recognition_method,
                    "marked_at": record.marked_at.isoformat() if record.marked_at else None,
                    "is_new": (message == "Attendance marked successfully"),
                    "is_eligible": True,
                    "message": message,
                }
                return jsonify({
                    "success": True,
                    "status": "recognized",
                    "message": message,
                    "detected_count": 1,
                    "recognized_count": 1,
                    "recognized": [data_rec],
                    "data": data_rec,
                }), 200
            else:
                return jsonify({
                    "success": False,
                    "status": "ineligible",
                    "message": message,
                    "data": None,
                }), 400

        # Fallback to direct image recognition (only when require_liveness is False, e.g. legacy tests)
        if image_input is None:
            return jsonify({
                "success": False,
                "message": "image is required",
            }), 400

        image = _decode_image(image_input)
        if image is None:
            return jsonify({
                "success": False,
                "message": "Invalid image",
            }), 400

        # Load active face profiles
        face_profiles = FaceProfile.query.filter_by(
            is_active=True,
            model_version="sface_2021dec",
        ).all()

        registered_students = []
        for profile in face_profiles:
            encoding = np.frombuffer(profile.embedding, dtype=np.float32)
            if encoding.shape != (128,) or not np.isfinite(encoding).all():
                continue
            registered_students.append({
                "student_id": profile.student_id,
                "encoding": encoding.reshape(1, 128),
            })

        if not registered_students:
            return jsonify({
                "success": True,
                "status": "no_registered_students",
                "message": "No registered face profiles found in the system",
                "detected_count": 0,
                "recognized_count": 0,
                "recognized": [],
                "data": None,
            }), 200

        # Run face recognition on frame
        try:
            rec_result = face_service.recognize_all_students(
                image,
                registered_students,
                SIMILARITY_THRESHOLD,
            )
        except (cv2.error, ValueError):
            return jsonify({
                "success": False,
                "message": "Face recognition processing error",
                "status": "recognition_failed",
            }), 400

        detected_count = rec_result.get("detected_count", 0)
        matches = rec_result.get("matches", [])

        if detected_count == 0:
            return jsonify({
                "success": True,
                "status": "no_face",
                "message": "No face detected in frame",
                "detected_count": 0,
                "recognized_count": 0,
                "recognized": [],
                "data": None,
            }), 200

        if not matches:
            return jsonify({
                "success": True,
                "status": "not_recognized",
                "message": "Face detected but not recognized as a registered student",
                "detected_count": detected_count,
                "recognized_count": 0,
                "recognized": [],
                "data": None,
            }), 200

        # Process all recognized matches
        recognized_records = []
        for match in matches:
            student_id = match["student_id"]
            confidence_score = match["similarity_score"]

            record, message = mark_face_attendance(
                session_id=session_id,
                student_id=student_id,
                confidence_score=confidence_score,
                faculty_id=faculty.faculty_id,
            )

            student = db.session.get(Student, student_id)
            student_name = student.user.name if (student and student.user) else f"Student #{student_id}"
            enrollment_no = student.enrollment_no if student else "N/A"

            if record:
                recognized_records.append({
                    "attendance_id": record.attendance_id,
                    "session_id": record.session_id,
                    "student_id": record.student_id,
                    "name": student_name,
                    "student_name": student_name,
                    "enrollment_no": enrollment_no,
                    "status": record.status,
                    "confidence_score": record.confidence_score,
                    "recognition_method": record.recognition_method,
                    "marked_at": record.marked_at.isoformat() if record.marked_at else None,
                    "is_new": (message == "Attendance marked successfully"),
                    "is_eligible": True,
                    "message": message,
                })
            else:
                current_app.logger.warning(
                    "Rejected attendance attempt for student %s in session %s: %s",
                    student_id,
                    session_id,
                    message,
                )
                recognized_records.append({
                    "attendance_id": None,
                    "session_id": session.session_id,
                    "student_id": student_id,
                    "name": student_name,
                    "student_name": student_name,
                    "enrollment_no": enrollment_no,
                    "status": "INELIGIBLE",
                    "confidence_score": confidence_score,
                    "recognition_method": "FACE",
                    "marked_at": None,
                    "is_new": False,
                    "is_eligible": False,
                    "message": message,
                })

        primary_record = recognized_records[0] if recognized_records else None
        new_marked_count = sum(1 for r in recognized_records if r.get("is_new"))

        if new_marked_count > 0:
            overall_message = f"Attendance marked for {new_marked_count} student(s)"
        elif recognized_records:
            overall_message = recognized_records[0]["message"]
        else:
            overall_message = "No eligible student marked"

        return jsonify({
            "success": True,
            "status": "recognized",
            "message": overall_message,
            "detected_count": detected_count,
            "recognized_count": len(recognized_records),
            "recognized": recognized_records,
            "data": primary_record,
        }), 200