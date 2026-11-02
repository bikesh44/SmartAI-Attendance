
from app.extensions import db


class Batch(db.Model):
    __tablename__ = "batches"

    batch_id = db.Column(
        db.Integer,
        primary_key=True,
    )

    batch_name = db.Column(
        db.String(20),
        unique=True,
        nullable=False,
    )

    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
        server_default=db.true(),
    )

    def __repr__(self):
        return f"<Batch {self.batch_name}>"
