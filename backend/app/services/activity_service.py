import logging
from datetime import datetime, timezone
from flask import has_request_context
from flask_jwt_extended import get_jwt_identity, get_jwt

from app.extensions import db
from app.models.activity_log import ActivityLog
from app.models.user import User

logger = logging.getLogger(__name__)

SENSITIVE_KEYS = {
    "password",
    "password_hash",
    "token",
    "access_token",
    "refresh_token",
    "secret",
    "secret_key",
    "embeddings",
    "face_features",
    "embedding",
    "face_encoding",
}


def sanitize_details(details):
    """Recursively removes sensitive keys from details dictionary."""
    if not isinstance(details, dict):
        return details

    sanitized = {}
    for k, v in details.items():
        if str(k).lower() in SENSITIVE_KEYS:
            continue
        if isinstance(v, dict):
            sanitized[k] = sanitize_details(v)
        elif isinstance(v, list):
            sanitized[k] = [
                sanitize_details(item) if isinstance(item, dict) else item
                for item in v
            ]
        else:
            sanitized[k] = v
    return sanitized


def format_utc_iso(dt):
    """Serialize datetime to UTC ISO 8601 string ending with Z."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.isoformat() + "Z"
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def record_activity(
    action_type,
    description,
    actor=None,
    actor_id=None,
    actor_name=None,
    actor_role=None,
    entity_type=None,
    entity_id=None,
    status="SUCCESS",
    details=None,
    commit=True,
):
    """
    Records a system activity event in the database.
    """
    try:
        # Resolve actor if not provided
        resolved_actor_id = actor_id
        resolved_actor_name = actor_name
        resolved_actor_role = actor_role

        if actor is not None:
            resolved_actor_id = getattr(actor, "user_id", None)
            resolved_actor_name = getattr(actor, "name", None) or resolved_actor_name
            resolved_actor_role = getattr(actor, "role", None) or resolved_actor_role
        elif not resolved_actor_id and has_request_context():
            try:
                jwt_id = get_jwt_identity()
                if jwt_id is not None:
                    resolved_actor_id = int(jwt_id)
                    claims = get_jwt() or {}
                    resolved_actor_role = claims.get("role") or resolved_actor_role
            except Exception:
                pass

        if resolved_actor_id and (not resolved_actor_name or not resolved_actor_role):
            u = db.session.get(User, resolved_actor_id)
            if u:
                if not resolved_actor_name:
                    resolved_actor_name = u.name
                if not resolved_actor_role:
                    resolved_actor_role = u.role

        clean_details = sanitize_details(details) if details else None

        log_entry = ActivityLog(
            actor_id=resolved_actor_id,
            actor_name=resolved_actor_name or "System",
            actor_role=resolved_actor_role or "SYSTEM",
            action_type=str(action_type).strip().upper(),
            description=str(description).strip()[:255],
            entity_type=str(entity_type).strip() if entity_type else None,
            entity_id=str(entity_id).strip() if entity_id is not None else None,
            status=str(status).strip().upper() if status else "SUCCESS",
            details=clean_details,
            created_at=datetime.utcnow(),
        )

        db.session.add(log_entry)

        if commit:
            db.session.commit()

        return log_entry
    except Exception as exc:
        logger.error(f"Failed to record activity log: {exc}", exc_info=True)
        if commit:
            try:
                db.session.rollback()
            except Exception:
                pass
        return None


def serialize_activity_log(log):
    """Serialize an ActivityLog model instance into a standardized JSON response format."""
    if not log:
        return None

    actor_name = log.actor_name
    actor_role = log.actor_role

    if not actor_name and log.actor:
        actor_name = log.actor.name
    if not actor_role and log.actor:
        actor_role = log.actor.role

    return {
        "id": log.id,
        "action_type": log.action_type,
        "description": log.description,
        "actor": {
            "id": log.actor_id,
            "name": actor_name or "System",
            "role": actor_role or "SYSTEM",
        },
        "entity_type": log.entity_type,
        "entity_id": log.entity_id,
        "status": log.status,
        "details": log.details,
        "created_at": format_utc_iso(log.created_at),
    }
