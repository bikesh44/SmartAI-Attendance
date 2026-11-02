import base64
import cv2
import numpy as np

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity

from app.extensions import db
from app.models import FaceProfile, Student
from app.services.face_identity_service import (
    remove_student_face_profile,
    safe_replace_face_profile,
)
from app.services.face_service import FaceService
from app.utils.auth import role_required


face_bp = Blueprint(
    "face",
    __name__,
    url_prefix="/api/face",
)


face_service = FaceService()

FACE_MODEL_VERSION = "sface_2021dec"


def _decode_image(image_input):
    """Decode an uploaded image (FileStorage, bytes, or base64 string) into an OpenCV BGR image."""
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

    buffer = np.frombuffer(
        image_bytes,
        dtype=np.uint8,
    )

    return cv2.imdecode(
        buffer,
        cv2.IMREAD_COLOR,
    )


@face_bp.post("/enroll")
@role_required("ADMIN", "STUDENT")
def enroll_face():
    """Enroll or replace a student's face profile."""
    json_data = request.get_json(silent=True) or {}

    student_id = request.form.get("student_id") or json_data.get("student_id")

    if not student_id:
        return jsonify({
            "success": False,
            "message": "student_id is required",
        }), 400

    try:
        student_id = int(student_id)
    except (TypeError, ValueError):
        return jsonify({
            "success": False,
            "message": "student_id must be an integer",
        }), 400

    # Authorization check for student role
    claims = get_jwt()
    user_role = claims.get("role")
    user_id = int(get_jwt_identity())
    if user_role == "STUDENT":
        current_student = Student.query.filter_by(user_id=user_id).first()
        if not current_student or current_student.student_id != student_id:
            return jsonify({
                "success": False,
                "message": "You can only enroll your own face",
            }), 403

    student = db.session.get(Student, student_id)

    if not student:
        return jsonify({
            "success": False,
            "message": "Student not found",
        }), 404

    image_input = (
        request.files.get("image")
        or request.form.get("image")
        or json_data.get("image")
    )

    if image_input is None:
        return jsonify({
            "success": False,
            "message": "image is required",
        }), 400

    image = _decode_image(image_input)
    if image is not None:
        print(
            "[FACE DEBUG]",
            "shape:", image.shape,
            "dtype:", image.dtype,
            "min:", int(image.min()),
            "max:", int(image.max()),
        )
    else:
        print("[FACE DEBUG] Image decoding failed")

    if image is None:
        return jsonify({
            "success": False,
            "message": "Invalid image",
        }), 400

    result = face_service.enroll_student(image)

    if result["status"] != "enrolled":
        status_messages = {
            "invalid_image": "Invalid image",
            "no_face": "No face detected",
            "multiple_faces": (
                "Multiple faces detected; exactly one face is required"
            ),
            "encoding_failed": "Face encoding failed",
            "invalid_encoding": "Generated face encoding is invalid",
        }

        return jsonify({
            "success": False,
            "message": status_messages.get(
                result["status"],
                "Face enrollment failed",
            ),
            "status": result["status"],
        }), 400

    encoding = result["encoding"]

    success, message, face_profile, status = safe_replace_face_profile(
        student_id=student_id,
        encoding=encoding,
        model_version=FACE_MODEL_VERSION,
        check_cross_student=True,
    )

    if not success:
        status_code = 409 if status in ("conflict_detected", "concurrent_conflict") else 400
        return jsonify({
            "success": False,
            "message": message,
            "status": status,
        }), status_code

    return jsonify({
        "success": True,
        "message": message,
        "data": {
            "student_id": student.student_id,
            "face_id": face_profile.face_id,
            "model_version": face_profile.model_version,
            "status": "enrolled",
        },
    }), 201

@face_bp.get("/status/<int:student_id>")
@role_required("ADMIN", "FACULTY", "STUDENT")
def face_registration_status(student_id):
    """Return the active face registration status for a student."""
    claims = get_jwt()
    user_role = claims.get("role")
    if user_role == "STUDENT":
        user_id = int(get_jwt_identity())
        current_student = Student.query.filter_by(user_id=user_id).first()
        if not current_student or current_student.student_id != student_id:
            return jsonify({
                "success": False,
                "message": "You can only view your own face registration status",
            }), 403

    student = db.session.get(Student, student_id)

    if not student:
        return jsonify({
            "success": False,
            "message": "Student not found",
        }), 404

    face_profile = FaceProfile.query.filter_by(
        student_id=student_id,
        is_active=True,
    ).first()

    if face_profile:
        return jsonify({
            "success": True,
            "data": {
                "student_id": student.student_id,
                "registered": True,
                "status": "registered",
                "model_version": face_profile.model_version,
            },
        }), 200

    return jsonify({
        "success": True,
        "data": {
            "student_id": student.student_id,
            "registered": False,
            "status": "not_registered",
            "model_version": None,
        },
    }), 200


@face_bp.delete("/student/<int:student_id>")
@face_bp.delete("/<int:student_id>")
@role_required("ADMIN")
def remove_student_face_biometric(student_id):
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
