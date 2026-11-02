import unittest
from datetime import time
from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token
from sqlalchemy.pool import StaticPool

from app.extensions import db
from app.models import (
    Course,
    CourseOffering,
    Department,
    Faculty,
    FacultyAdjustment,
    TimetableEntry,
    User,
)
from app.routes.timetable import timetable_bp
from app.routes.timetable_import import timetable_import_bp


class TestTimetableEntryEdit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = Flask(__name__)
        cls.app.config.update(
            TESTING=True,
            SECRET_KEY="test-secret-key-123",
            JWT_SECRET_KEY="test-jwt-secret-key-32-bytes-long",
            SQLALCHEMY_DATABASE_URI="sqlite://",
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
            SQLALCHEMY_ENGINE_OPTIONS={
                "poolclass": StaticPool,
                "connect_args": {"check_same_thread": False},
            },
            JWT_TOKEN_LOCATION=["headers"],
        )

        db.init_app(cls.app)
        JWTManager(cls.app)
        cls.app.register_blueprint(timetable_bp)
        cls.app.register_blueprint(timetable_import_bp)

        with cls.app.app_context():
            db.create_all()

    @classmethod
    def tearDownClass(cls):
        with cls.app.app_context():
            db.session.remove()
            db.drop_all()

    def setUp(self):
        self.client = self.app.test_client()

        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.create_all()

            # Seed Admin User
            admin_user = User(
                user_id=1,
                name="System Administrator",
                email="admin@test.edu",
                password_hash="test",
                role="ADMIN",
            )
            # Seed Faculty Users
            fac_user_1 = User(
                user_id=2,
                name="Dr. Rajesh Kumar",
                email="rajesh@test.edu",
                password_hash="test",
                role="FACULTY",
            )
            fac_user_2 = User(
                user_id=3,
                name="Prof. Sunita Sharma",
                email="sunita@test.edu",
                password_hash="test",
                role="FACULTY",
            )
            # Seed Student User
            student_user = User(
                user_id=4,
                name="Aman Gupta",
                email="aman@test.edu",
                password_hash="test",
                role="STUDENT",
            )

            dept = Department(department_id=1, department_name="Computer Science", department_code="CSE")
            db.session.add_all([admin_user, fac_user_1, fac_user_2, student_user, dept])
            db.session.flush()

            faculty_1 = Faculty(faculty_id=1, user_id=2, department_id=1, employee_id="EMP001", designation="Professor")
            faculty_2 = Faculty(faculty_id=2, user_id=3, department_id=1, employee_id="EMP002", designation="Associate Professor")
            db.session.add_all([faculty_1, faculty_2])
            db.session.flush()

            course_1 = Course(course_id=1, course_code="BCSE-001", course_name="Computational & Problem Solving", semester=1, department_id=1, credits=4)
            course_2 = Course(course_id=2, course_code="BCSE-002", course_name="Data Structures", semester=1, department_id=1, credits=4)
            db.session.add_all([course_1, course_2])
            db.session.flush()

            offering_1 = CourseOffering(
                offering_id=1,
                course_id=1,
                faculty_id=1,
                academic_year="2026-2027",
                semester=1,
                section="A",
                room="CSE-1A-01",
            )
            offering_2 = CourseOffering(
                offering_id=2,
                course_id=2,
                faculty_id=2,
                academic_year="2026-2027",
                semester=1,
                section="B",
                room="CSE-1A-02",
            )
            db.session.add_all([offering_1, offering_2])
            db.session.flush()

            # Entry 1: Monday, 14:40 - 15:40, CSE-1A-01
            entry_1 = TimetableEntry(
                timetable_entry_id=1,
                offering_id=1,
                day_of_week="Monday",
                start_time=time(14, 40),
                end_time=time(15, 40),
                room="CSE-1A-01",
            )
            # Entry 2: Monday, 15:40 - 16:40, CSE-1A-02 (Course 2, Faculty 2)
            entry_2 = TimetableEntry(
                timetable_entry_id=2,
                offering_id=2,
                day_of_week="Monday",
                start_time=time(15, 40),
                end_time=time(16, 40),
                room="CSE-1A-02",
            )
            # Entry 3: Tuesday, 10:00 - 11:00, Room 203 (Course 1, Faculty 1)
            entry_3 = TimetableEntry(
                timetable_entry_id=3,
                offering_id=1,
                day_of_week="Tuesday",
                start_time=time(10, 0),
                end_time=time(11, 0),
                room="Room 203",
            )
            db.session.add_all([entry_1, entry_2, entry_3])
            db.session.commit()

        with self.app.app_context():
            self.admin_token = create_access_token(identity="1", additional_claims={"role": "ADMIN"})
            self.student_token = create_access_token(identity="4", additional_claims={"role": "STUDENT"})
            self.faculty_token = create_access_token(identity="2", additional_claims={"role": "FACULTY"})
            self.faculty_2_token = create_access_token(identity="3", additional_claims={"role": "FACULTY"})

    def test_update_time_and_room_success(self):
        """Admin successfully updates start time, end time, and room for an existing timetable entry."""
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        payload = {
            "day_of_week": "Monday",
            "start_time": "15:40",
            "end_time": "16:40",
            "room": "Room 204",
        }
        res = self.client.put("/api/timetable/1", json=payload, headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["start_time"], "15:40")
        self.assertEqual(data["data"]["end_time"], "16:40")
        self.assertEqual(data["data"]["room"], "Room 204")
        self.assertEqual(data["data"]["day_of_week"], "Monday")
        # Ensure other fields are preserved
        self.assertEqual(data["data"]["course_code"], "BCSE-001")
        self.assertEqual(data["data"]["faculty_name"], "Dr. Rajesh Kumar")
        self.assertEqual(data["data"]["section"], "A")

        # Verify in DB
        with self.app.app_context():
            entry = db.session.get(TimetableEntry, 1)
            self.assertEqual(entry.start_time, time(15, 40))
            self.assertEqual(entry.end_time, time(16, 40))
            self.assertEqual(entry.room, "Room 204")
            # Verify no duplicate was created
            count = TimetableEntry.query.count()
            self.assertEqual(count, 3)

    def test_update_day_of_week_success(self):
        """Admin can change the day of week for an existing timetable entry."""
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        payload = {
            "day_of_week": "Wednesday",
            "start_time": "14:40",
            "end_time": "15:40",
            "room": "CSE-1A-01",
        }
        res = self.client.put("/api/timetable/1", json=payload, headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["data"]["day_of_week"], "Wednesday")

        with self.app.app_context():
            entry = db.session.get(TimetableEntry, 1)
            self.assertEqual(entry.day_of_week, "Wednesday")

    def test_reject_invalid_time_format(self):
        """Reject invalid time format like '25:00' or 'invalid'."""
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        payload = {
            "start_time": "invalid",
            "end_time": "15:40",
        }
        res = self.client.put("/api/timetable/1", json=payload, headers=headers)
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertFalse(data["success"])
        self.assertEqual(data["field"], "start_time")

    def test_reject_end_time_not_later_than_start_time(self):
        """Reject end time that is equal to or earlier than start time."""
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        # Equal times
        res1 = self.client.put("/api/timetable/1", json={"start_time": "14:00", "end_time": "14:00"}, headers=headers)
        self.assertEqual(res1.status_code, 400)
        self.assertEqual(res1.get_json()["field"], "end_time")

        # End before start
        res2 = self.client.put("/api/timetable/1", json={"start_time": "16:00", "end_time": "15:00"}, headers=headers)
        self.assertEqual(res2.status_code, 400)
        self.assertEqual(res2.get_json()["field"], "end_time")

    def test_reject_unauthorized_access(self):
        """Reject requests without token or from non-admin roles."""
        # No token
        res_no_auth = self.client.put("/api/timetable/1", json={"start_time": "10:00", "end_time": "11:00"})
        self.assertIn(res_no_auth.status_code, [401, 403])

        # Student token
        headers_student = {"Authorization": f"Bearer {self.student_token}"}
        res_student = self.client.put("/api/timetable/1", json={"start_time": "10:00", "end_time": "11:00"}, headers=headers_student)
        self.assertEqual(res_student.status_code, 403)

        # Faculty token
        headers_faculty = {"Authorization": f"Bearer {self.faculty_token}"}
        res_fac = self.client.put("/api/timetable/1", json={"start_time": "10:00", "end_time": "11:00"}, headers=headers_faculty)
        self.assertEqual(res_fac.status_code, 403)

    def test_reject_room_conflict(self):
        """Reject schedule change when room is already booked by another entry."""
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        # Entry 2 is on Monday 15:40-16:40 in CSE-1A-02.
        # Try moving Entry 1 (Monday 14:40-15:40) to Monday 15:40-16:40 in CSE-1A-02.
        payload = {
            "day_of_week": "Monday",
            "start_time": "15:40",
            "end_time": "16:40",
            "room": "CSE-1A-02",
        }
        res = self.client.put("/api/timetable/1", json=payload, headers=headers)
        self.assertEqual(res.status_code, 409)
        data = res.get_json()
        self.assertFalse(data["success"])
        self.assertIn("Room CSE-1A-02 is already booked", data["message"])
        self.assertEqual(data["field"], "room")

    def test_reject_faculty_conflict(self):
        """Reject schedule change when assigned faculty is already teaching another class."""
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        # Faculty 1 (Dr. Rajesh Kumar) teaches Entry 3 on Tuesday 10:00-11:00.
        # Try moving Entry 1 (Faculty 1) to Tuesday 10:00-11:00 in another room.
        payload = {
            "day_of_week": "Tuesday",
            "start_time": "10:00",
            "end_time": "11:00",
            "room": "Room 501",
        }
        res = self.client.put("/api/timetable/1", json=payload, headers=headers)
        self.assertEqual(res.status_code, 409)
        data = res.get_json()
        self.assertFalse(data["success"])
        self.assertIn("Dr. Rajesh Kumar already has a scheduled class", data["message"])

    def test_reject_nonexistent_entry(self):
        """Returns 404 if timetable entry does not exist."""
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        res = self.client.put("/api/timetable/9999", json={"start_time": "10:00", "end_time": "11:00"}, headers=headers)
        self.assertEqual(res.status_code, 404)

    def test_commit_import_with_edited_extracted_values(self):
        """Verify that when extracted entries have edited time and room values, commit uses the edited values."""
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        payload = {
            "academic_year": "2026-2027",
            "import_mode": "add_missing",
            "entries": [
                {
                    "course_id": 1,
                    "faculty_id": 1,
                    "semester": 1,
                    "section": "C",
                    "room": "New-Lab-01",  # edited room
                    "day_of_week": "Friday",  # edited day
                    "start_time": "09:00",  # edited start time
                    "end_time": "10:30",  # edited end time
                }
            ],
        }
        res = self.client.post("/api/timetable/import/commit", json=payload, headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])

        with self.app.app_context():
            new_entry = (
                TimetableEntry.query
                .filter_by(day_of_week="Friday", room="New-Lab-01")
                .first()
            )
            self.assertIsNotNone(new_entry)
            self.assertEqual(new_entry.start_time, time(9, 0))
            self.assertEqual(new_entry.end_time, time(10, 30))
            self.assertEqual(new_entry.room, "New-Lab-01")

    def test_admin_edit_persists_and_faculty_api_returns_updated_values(self):
        """
        Verify:
        1. Admin edits timetable entry (Entry 1 -> Sunday 22:16-22:40, Room CSE-1A-01).
        2. Database contains updated values.
        3. Assigned faculty API (/api/timetable/faculty) returns the updated entry.
        4. Day filter ?day=Sunday returns the updated entry.
        5. Day filter ?day=Monday or ?day=Saturday correctly excludes the updated entry.
        """
        admin_headers = {"Authorization": f"Bearer {self.admin_token}"}
        payload = {
            "day_of_week": "Sunday",
            "start_time": "22:16",
            "end_time": "22:40",
            "room": "CSE-1A-01",
        }
        res_edit = self.client.put("/api/timetable/1", json=payload, headers=admin_headers)
        self.assertEqual(res_edit.status_code, 200)
        data = res_edit.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["day_of_week"], "Sunday")
        self.assertEqual(data["data"]["start_time"], "22:16")
        self.assertEqual(data["data"]["end_time"], "22:40")
        self.assertEqual(data["data"]["room"], "CSE-1A-01")

        # 2. Database verification
        with self.app.app_context():
            db_entry = db.session.get(TimetableEntry, 1)
            self.assertIsNotNone(db_entry)
            self.assertEqual(db_entry.day_of_week, "Sunday")
            self.assertEqual(db_entry.start_time, time(22, 16))
            self.assertEqual(db_entry.end_time, time(22, 40))
            self.assertEqual(db_entry.room, "CSE-1A-01")

        # 3. Assigned faculty API returns updated values
        fac_headers = {"Authorization": f"Bearer {self.faculty_token}"}
        res_fac_all = self.client.get("/api/timetable/faculty", headers=fac_headers)
        self.assertEqual(res_fac_all.status_code, 200)
        fac_entries = res_fac_all.get_json()["data"]
        entry_1 = next((e for e in fac_entries if e["timetable_entry_id"] == 1), None)
        self.assertIsNotNone(entry_1)
        self.assertEqual(entry_1["day_of_week"], "Sunday")
        self.assertEqual(entry_1["start_time"], "22:16")
        self.assertEqual(entry_1["end_time"], "22:40")
        self.assertEqual(entry_1["room"], "CSE-1A-01")

        # 4. Day filter ?day=Sunday returns the updated entry
        res_fac_sun = self.client.get("/api/timetable/faculty?day=Sunday", headers=fac_headers)
        self.assertEqual(res_fac_sun.status_code, 200)
        sun_entries = res_fac_sun.get_json()["data"]
        self.assertEqual(len(sun_entries), 1)
        self.assertEqual(sun_entries[0]["timetable_entry_id"], 1)
        self.assertEqual(sun_entries[0]["room"], "CSE-1A-01")

        # 5. Day filter ?day=Monday does NOT return entry 1 anymore
        res_fac_mon = self.client.get("/api/timetable/faculty?day=Monday", headers=fac_headers)
        self.assertEqual(res_fac_mon.status_code, 200)
        mon_entries = res_fac_mon.get_json()["data"]
        self.assertFalse(any(e["timetable_entry_id"] == 1 for e in mon_entries))

        # 6. Day filter for Saturday has 0 classes for Faculty 1
        res_fac_sat = self.client.get("/api/timetable/faculty?day=Saturday", headers=fac_headers)
        self.assertEqual(res_fac_sat.status_code, 200)
        self.assertEqual(len(res_fac_sat.get_json()["data"]), 0)

    def test_unrelated_faculty_does_not_receive_unauthorized_timetable(self):
        """
        Verify that unrelated faculty member does not receive unauthorized timetable entries.
        """
        fac_2_headers = {"Authorization": f"Bearer {self.faculty_2_token}"}
        res = self.client.get("/api/timetable/faculty", headers=fac_2_headers)
        self.assertEqual(res.status_code, 200)
        entries = res.get_json()["data"]
        # Faculty 2 is only assigned offering 2 (Entry 2)
        entry_ids = [e["timetable_entry_id"] for e in entries]
        self.assertIn(2, entry_ids)
        self.assertNotIn(1, entry_ids)
        self.assertNotIn(3, entry_ids)


if __name__ == "__main__":
    unittest.main()
