import unittest
from datetime import date, time

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


class TestFacultyAdjustmentWorkflow(unittest.TestCase):
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
                name="Dr. Anita Desai",
                email="anita@test.edu",
                password_hash="test",
                role="FACULTY",
            )
            fac_user_3 = User(
                user_id=4,
                name="Prof. Neha Gupta",
                email="neha@test.edu",
                password_hash="test",
                role="FACULTY",
            )

            dept = Department(
                department_id=1,
                department_name="Computer Science & Engineering",
                department_code="CSE",
            )

            db.session.add_all([admin_user, fac_user_1, fac_user_2, fac_user_3, dept])
            db.session.commit()

            fac1 = Faculty(
                faculty_id=1,
                user_id=2,
                department_id=1,
                employee_id="EMP001",
                designation="Professor",
            )
            fac2 = Faculty(
                faculty_id=2,
                user_id=3,
                department_id=1,
                employee_id="EMP002",
                designation="Associate Professor",
            )
            fac3 = Faculty(
                faculty_id=3,
                user_id=4,
                department_id=1,
                employee_id="EMP003",
                designation="Assistant Professor",
            )

            c1 = Course(
                course_id=1,
                department_id=1,
                course_code="CS101",
                course_name="Data Structures",
                semester=3,
                credits=4,
            )
            c2 = Course(
                course_id=2,
                department_id=1,
                course_code="CS102",
                course_name="DBMS",
                semester=3,
                credits=4,
            )

            db.session.add_all([fac1, fac2, fac3, c1, c2])
            db.session.commit()

            # Offering 1 for fac1
            off1 = CourseOffering(
                offering_id=1,
                course_id=1,
                faculty_id=1,
                academic_year="2026-27",
                semester=3,
                section="A",
                room="R101",
            )
            # Offering 2 for fac2
            off2 = CourseOffering(
                offering_id=2,
                course_id=2,
                faculty_id=2,
                academic_year="2026-27",
                semester=3,
                section="B",
                room="R102",
            )
            db.session.add_all([off1, off2])
            db.session.commit()

            # Timetable entry 1: Mon 08:00 - 09:00 for fac1
            te1 = TimetableEntry(
                timetable_entry_id=1,
                offering_id=1,
                day_of_week="Monday",
                start_time=time(8, 0),
                end_time=time(9, 0),
                room="R101",
            )
            # Timetable entry 2: Mon 08:00 - 09:00 for fac2 (busy at same time!)
            te2 = TimetableEntry(
                timetable_entry_id=2,
                offering_id=2,
                day_of_week="Monday",
                start_time=time(8, 0),
                end_time=time(9, 0),
                room="R102",
            )
            db.session.add_all([te1, te2])
            db.session.commit()

        with self.app.app_context():
            self.admin_token = create_access_token(identity="1", additional_claims={"role": "ADMIN"})
            self.headers = {"Authorization": f"Bearer {self.admin_token}"}

    def test_create_faculty_adjustment_success(self):
        # fac3 is free on Monday 08:00-09:00 -> replace fac1 on te1
        payload = {
            "timetable_entry_id": 1,
            "substitute_faculty_id": 3,
            "effective_date": "2026-10-20",
            "reason": "Faculty attending research conference",
            "request_approval": False,
        }
        res = self.client.post("/api/timetable/adjustments", json=payload, headers=self.headers)
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["original_faculty_id"], 1)
        self.assertEqual(data["data"]["substitute_faculty_id"], 3)
        self.assertEqual(data["data"]["status"], "APPROVED")

        # Check that original CourseOffering faculty was NOT overwritten
        with self.app.app_context():
            entry = db.session.get(TimetableEntry, 1)
            self.assertEqual(entry.offering.faculty_id, 1)
            # Check admin timetable serializer reflects active adjustment
            serialized = self.client.get("/api/timetable/admin", headers=self.headers).get_json()
            entry_match = [e for e in serialized["data"] if e["timetable_entry_id"] == 1][0]
            self.assertEqual(entry_match["faculty_name"], "Dr. Rajesh Kumar")
            self.assertEqual(entry_match["effective_faculty_name"], "Prof. Neha Gupta")
            self.assertIsNotNone(entry_match["active_adjustment"])

    def test_self_substitution_rejected(self):
        # Try replacing fac1 with fac1
        payload = {
            "timetable_entry_id": 1,
            "substitute_faculty_id": 1,
            "effective_date": "2026-10-20",
            "reason": "Invalid substitution",
        }
        res = self.client.post("/api/timetable/adjustments", json=payload, headers=self.headers)
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertFalse(data["success"])
        self.assertIn("different", data["message"].lower())

    def test_substitute_conflict_detected(self):
        # fac2 is busy on Monday 08:00-09:00 -> conflict!
        payload = {
            "timetable_entry_id": 1,
            "substitute_faculty_id": 2,
            "effective_date": "2026-10-20",
            "reason": "Faculty unwell",
        }
        res = self.client.post("/api/timetable/adjustments", json=payload, headers=self.headers)
        self.assertEqual(res.status_code, 409)
        data = res.get_json()
        self.assertFalse(data["success"])
        self.assertIn("already", data["message"].lower())

    def test_cancel_adjustment(self):
        # Create adjustment
        payload = {
            "timetable_entry_id": 1,
            "substitute_faculty_id": 3,
            "effective_date": "2026-10-20",
            "reason": "Temporary leave",
        }
        res = self.client.post("/api/timetable/adjustments", json=payload, headers=self.headers)
        self.assertEqual(res.status_code, 201)
        adj_id = res.get_json()["data"]["adjustment_id"]

        # Cancel it
        cancel_res = self.client.post(f"/api/timetable/adjustments/{adj_id}/cancel", headers=self.headers)
        self.assertEqual(cancel_res.status_code, 200)
        self.assertEqual(cancel_res.get_json()["data"]["status"], "CANCELLED")
