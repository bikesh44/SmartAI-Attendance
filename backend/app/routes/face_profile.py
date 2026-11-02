from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity

from app.extensions import db
from app.models import FaceProfile, Student
from app.utils.auth import admin_required, student_required
from app.services.cv.face_service import serialize_embedding

face_profile_bp = Blueprint(
    "face_profile",
    __name__,
    url_prefix="/api",
)


def get_current_student():
    user_id = int(get_jwt_identity())

    return Student.query.filter_by(
        user_id=user_id
    ).first()


@face_profile_bp.post("/student/face-profile")
@student_required
def create_face_profile():
    student = get_current_student()

    if not student:
        return jsonify({
            "success": False,
            "message": "Student profile not found",
        }), 404

    data = request.get_json(silent=True) or {}

    embedding = data.get("embedding")
    model_version = data.get("model_version")

    # Validate embedding presence
    if embedding is None:
        return jsonify({
            "success": False,
            "message": "embedding is required",
        }), 400

    # Validate model version presence
    if model_version is None:
        return jsonify({
            "success": False,
            "message": "model_version is required",
        }), 400

    # Validate embedding type
    if not isinstance(embedding, list):
        return jsonify({
            "success": False,
            "message": "embedding must be a list",
        }), 400

    # Validate embedding dimension
    if len(embedding) != 512:
        return jsonify({
            "success": False,
            "message": "embedding must contain exactly 512 values",
        }), 400

    # Validate model version type
    if not isinstance(model_version, str):
        return jsonify({
            "success": False,
            "message": "model_version must be a string",
        }), 400

    model_version = model_version.strip()

    # Validate model version content
    if not model_version:
        return jsonify({
            "success": False,
            "message": "model_version cannot be empty",
        }), 400

    # Validate database column limit
    if len(model_version) > 50:
        return jsonify({
            "success": False,
            "message": "model_version must not exceed 50 characters",
        }), 400

    # Serialize and validate embedding values
    try:
        embedding_bytes = serialize_embedding(embedding)
    except (TypeError, ValueError):
        return jsonify({
            "success": False,
            "message": "embedding must contain numeric values",
        }), 400

    # Deactivate existing active profile(s) atomically and create new active profile
    existing_profiles = FaceProfile.query.filter_by(
        student_id=student.student_id,
        is_active=True,
    ).all()

    for p in existing_profiles:
        p.is_active = False

    face_profile = FaceProfile(
        student_id=student.student_id,
        embedding=embedding_bytes,
        model_version=model_version,
        is_active=True,
    )

    db.session.add(face_profile)
    db.session.commit()

    is_update = len(existing_profiles) > 0
    return jsonify({
        "success": True,
        "message": "Face profile updated successfully" if is_update else "Face profile created successfully",
        "data": {
            "face_id": face_profile.face_id,
            "student_id": face_profile.student_id,
            "model_version": face_profile.model_version,
            "is_active": face_profile.is_active,
        },
    }), 200 if is_update else 201


@face_profile_bp.get("/student/face-profile")
@student_required
def get_my_face_profile():
    student = get_current_student()

    if not student:
        return jsonify({
            "success": False,
            "message": "Student profile not found",
        }), 404

    profile = FaceProfile.query.filter_by(
        student_id=student.student_id,
        is_active=True,
    ).first()

    if not profile:
        return jsonify({
            "success": False,
            "message": "Face profile not found",
        }), 404

    return jsonify({
        "success": True,
        "data": {
            "face_id": profile.face_id,
            "student_id": profile.student_id,
            "model_version": profile.model_version,
            "created_at": profile.created_at.isoformat(),
            "updated_at": profile.updated_at.isoformat(),
            "is_active": profile.is_active,
        },
    }), 200


@face_profile_bp.delete("/student/face-profile")
@student_required
def deactivate_my_face_profile():
    student = get_current_student()

    if not student:
        return jsonify({
            "success": False,
            "message": "Student profile not found",
        }), 404

    profile = FaceProfile.query.filter_by(
        student_id=student.student_id,
        is_active=True,
    ).first()

    if not profile:
        return jsonify({
            "success": False,
            "message": "Face profile not found",
        }), 404

    profile.is_active = False

    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Face profile deactivated successfully",
    }), 200


@face_profile_bp.get("/admin/face-profiles")
@admin_required
def get_face_profiles():
    profiles = (
        FaceProfile.query
        .order_by(FaceProfile.face_id.asc())
        .all()
    )

    data = [
        {
            "face_id": profile.face_id,
            "student_id": profile.student_id,
            "model_version": profile.model_version,
            "created_at": profile.created_at.isoformat(),
            "updated_at": profile.updated_at.isoformat(),
            "is_active": profile.is_active,
        }
        for profile in profiles
    ]

    return jsonify({
        "success": True,
        "data": data,
    }), 200