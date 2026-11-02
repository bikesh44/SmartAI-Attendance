from flask import Blueprint, jsonify, current_app
from sqlalchemy import text

health_bp = Blueprint("health", __name__)


@health_bp.get("/api/health")
def health():
    return jsonify({"status": "ok"}), 200


@health_bp.get("/api/db-health")
def db_health():
    from app.extensions import db

    try:
        db.session.execute(text("SELECT 1"))
        return jsonify({"database": "ok"}), 200
    except Exception as e:
        current_app.logger.error("Database health check failed: %s", e)
        return jsonify({
            "database": "error",
            "message": "Database connection failed"
        }), 500