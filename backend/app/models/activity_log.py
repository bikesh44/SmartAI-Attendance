from datetime import datetime
from app.extensions import db


class ActivityLog(db.Model):
    __tablename__ = "activity_logs"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    actor_id = db.Column(
        db.Integer,
        db.ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    actor_name = db.Column(db.String(100), nullable=True)
    actor_role = db.Column(db.String(20), nullable=True)
    action_type = db.Column(db.String(50), nullable=False, index=True)
    description = db.Column(db.String(255), nullable=False)
    entity_type = db.Column(db.String(50), nullable=True, index=True)
    entity_id = db.Column(db.String(50), nullable=True)
    status = db.Column(db.String(20), nullable=False, default="SUCCESS")
    details = db.Column(db.JSON, nullable=True)

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True,
    )

    actor = db.relationship("User", foreign_keys=[actor_id], lazy="joined")

    def __repr__(self):
        return f"<ActivityLog {self.id}: {self.action_type}>"
