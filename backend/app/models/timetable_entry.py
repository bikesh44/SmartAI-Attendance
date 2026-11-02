from app.extensions import db


class TimetableEntry(db.Model):
    __tablename__ = "timetable_entries"
    timetable_entry_id = db.Column(
        db.Integer,
        primary_key = True,
    )

    offering_id = db.Column(
        db.Integer,
        db.ForeignKey("course_offerings.offering_id"),
        nullable = False,
        index = True,
    )
    day_of_week = db.Column(
        db.String(9),
        nullable = False,
    )
    start_time = db.Column(
        db.Time,
        nullable = False,
    )
    end_time = db.Column(
        db.Time,
        nullable = False,
    )

    room = db.Column(
        db.String(50),
        nullable = True,
    )

    offering = db.relationship(
        "CourseOffering",
        back_populates = "timetable_entries",
    )

    def __init__(
        self,
        offering_id=None,
        day_of_week=None,
        start_time=None,
        end_time=None,
        room=None,
        **kwargs,
    ):
        super().__init__()
        self.offering_id = offering_id
        self.day_of_week = day_of_week
        self.start_time = start_time
        self.end_time = end_time
        self.room = room
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __repr__(self):
        return(
            f"<TimetableEntry {self.timetable_entry_id}:"
            f"{self.day_of_week} {self.start_time}--{self.end_time}>"
        )
