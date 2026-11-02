from io import BytesIO
import unittest
from datetime import time
from openpyxl import Workbook

from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token
from sqlalchemy.pool import StaticPool

from app.extensions import db
from app.models import (
    Course,
    CourseOffering,
    Department,
    Faculty,
    TimetableEntry,
    User,
)
from app.routes.timetable_import import timetable_import_bp


def create_test_excel_bytes(sheet_name="05.10.2026 Updated Time Table", rows=None):
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_name

    # Default headers at row 3
    # DAY | P.NO. | TIMINGS | (empty) | 5CSE1 | 5CSE2
    ws.cell(row=3, column=1, value="DAY")
    ws.cell(row=3, column=2, value="P.NO.")
    ws.cell(row=3, column=3, value="TIMINGS")
    ws.cell(row=3, column=4, value="")
    ws.cell(row=3, column=5, value="5CSE1")
    ws.cell(row=3, column=6, value="5CSE2")

    if rows:
        for r_idx, row_data in enumerate(rows, start=4):
            for c_idx, val in enumerate(row_data, start=1):
                ws.cell(row=r_idx, column=c_idx, value=val)

    bio = BytesIO()
    wb.save(bio)
    bio.seek(0)
    return bio


def create_master_timetable_excel_bytes(sheet_name="Master Timetable", headers=None, rows=None, extra_sheets=None):
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_name

    col_headers = headers or [
        "Day", "Period", "Time", "Start Time", "End Time",
        "Course Code", "Course Name", "Faculty ID", "Faculty Name",
        "Semester", "Section", "Classroom / Lab", "Academic Year",
        "Break Schedule", "Assignment Status",
    ]
    for c_idx, h in enumerate(col_headers, start=1):
        ws.cell(row=1, column=c_idx, value=h)

    if rows:
        for r_idx, r_data in enumerate(rows, start=2):
            for c_idx, val in enumerate(r_data, start=1):
                ws.cell(row=r_idx, column=c_idx, value=val)

    if extra_sheets:
        for s_name in extra_sheets:
            wb.create_sheet(title=s_name)

    bio = BytesIO()
    wb.save(bio)
    bio.seek(0)
    return bio


class TestTimetableImportWorkflow(unittest.TestCase):
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
            # Seed Faculty User
            fac_user = User(
                user_id=2,
                name="Dr. Neera Batra",
                email="neera@test.edu",
                password_hash="test",
                role="FACULTY",
            )
            fac_user_2 = User(
                user_id=3,
                name="Dr. Monika",
                email="monika@test.edu",
                password_hash="test",
                role="FACULTY",
            )
            student_user = User(
                user_id=4,
                name="Student User",
                email="student@test.edu",
                password_hash="test",
                role="STUDENT",
            )

            dept = Department(
                department_id=1,
                department_name="Computer Science & Engineering",
                department_code="CSE",
            )

            db.session.add_all([admin_user, fac_user, fac_user_2, student_user, dept])
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

            c1 = Course(
                course_id=1,
                department_id=1,
                course_code="BCSE-513",
                course_name="Cloud Computing",
                semester=5,
                credits=4,
            )
            c2 = Course(
                course_id=2,
                department_id=1,
                course_code="BCSE-513L",
                course_name="Cloud Computing Lab",
                semester=5,
                credits=2,
            )
            c3 = Course(
                course_id=3,
                department_id=1,
                course_code="BHUM-004",
                course_name="Economics for Engineers",
                semester=5,
                credits=3,
            )

            db.session.add_all([fac1, fac2, c1, c2, c3])
            db.session.commit()

            with self.app.test_request_context():
                self.admin_token = create_access_token(
                    identity=str(admin_user.user_id),
                    additional_claims={"role": "ADMIN"},
                )
                self.student_token = create_access_token(
                    identity=str(student_user.user_id),
                    additional_claims={"role": "STUDENT"},
                )

        self.admin_headers = {"Authorization": f"Bearer {self.admin_token}"}
        self.student_headers = {"Authorization": f"Bearer {self.student_token}"}

    def test_academic_years_endpoint(self):
        res = self.client.get(
            "/api/timetable/import/academic-years",
            headers=self.admin_headers,
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertTrue(len(data["academic_years"]) > 0)
        self.assertIn("default", data)

    def test_unauthorized_access_rejected(self):
        res = self.client.get(
            "/api/timetable/import/academic-years",
            headers=self.student_headers,
        )
        self.assertEqual(res.status_code, 403)

        res_anon = self.client.get("/api/timetable/import/academic-years")
        self.assertEqual(res_anon.status_code, 401)

    def test_preview_backward_compatibility(self):
        excel_bytes = create_test_excel_bytes(
            rows=[
                ["Monday", "1", "09:30 AM - 10:30 AM", "", "BCSE-513 / Dr. Neera Batra / Room-302", "BHUM-004"],
            ]
        )
        res = self.client.post(
            "/api/timetable/import/preview",
            headers=self.admin_headers,
            data={"file": (excel_bytes, "timetable.xlsx")},
            content_type="multipart/form-data",
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["entry_count"], 2)
        self.assertEqual(data["entries"][0]["day_of_week"], "Monday")
        self.assertEqual(data["entries"][0]["start_time"], "09:30")
        self.assertEqual(data["entries"][0]["end_time"], "10:30")

    def test_preview_malformed_file(self):
        res = self.client.post(
            "/api/timetable/import/preview",
            headers=self.admin_headers,
            data={"file": (BytesIO(b"not a real excel file"), "bad.xlsx")},
            content_type="multipart/form-data",
        )
        self.assertEqual(res.status_code, 400)
        self.assertFalse(res.get_json()["success"])

    def test_analyze_entity_matching_and_conflict_detection(self):
        excel_bytes = create_test_excel_bytes(
            rows=[
                # Row 1: Valid BCSE-513 with Dr. Neera Batra in Room-302
                ["Monday", "1", "09:30 AM - 10:30 AM", "", "BCSE-513 / Dr. Neera Batra / Room-302", ""],
                # Row 2: Valid BHUM-004 Economics for Engineers in Room-105
                ["Monday", "2", "10:30 AM - 11:30 AM", "", "BHUM-004 / Dr. Monika / Room-105", ""],
                # Row 3: Conflict - scheduling Dr. Neera Batra simultaneously in 5CSE2 at 09:30
                ["Monday", "1", "09:30 AM - 10:30 AM", "", "", "BCSE-513L / Dr. Neera Batra / Lab-1"],
            ]
        )

        res = self.client.post(
            "/api/timetable/import/analyze",
            headers=self.admin_headers,
            data={
                "file": (excel_bytes, "timetable.xlsx"),
                "academic_year": "2026-27",
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["total_rows"], 3)

        entries = data["entries"]
        # Entry 0: matched
        self.assertEqual(entries[0]["course_code"], "BCSE-513")
        self.assertEqual(entries[0]["faculty_name"], "Dr. Neera Batra")
        self.assertEqual(entries[0]["room"], "Room-302")

        # Entry 1: matched
        self.assertEqual(entries[1]["course_code"], "BHUM-004")
        self.assertEqual(entries[1]["faculty_name"], "Dr. Monika")

        # Entry 2: conflict due to double-booked faculty in the same batch
        self.assertEqual(entries[2]["status"], "conflict")
        self.assertTrue(any("scheduled for multiple classes" in c for c in entries[2]["conflicts"]))

    def test_commit_transaction_and_idempotency(self):
        # 1. Commit two valid entries
        payload = {
            "academic_year": "2026-27",
            "import_mode": "add_missing",
            "entries": [
                {
                    "course_id": 1,
                    "faculty_id": 1,
                    "section": "5CSE1",
                    "semester": 5,
                    "day_of_week": "Monday",
                    "start_time": "09:30",
                    "end_time": "10:30",
                    "room": "Room-302",
                },
                {
                    "course_id": 3,
                    "faculty_id": 2,
                    "section": "5CSE1",
                    "semester": 5,
                    "day_of_week": "Tuesday",
                    "start_time": "10:30",
                    "end_time": "11:30",
                    "room": "Room-105",
                },
            ],
        }

        res = self.client.post(
            "/api/timetable/import/commit",
            headers=self.admin_headers,
            json=payload,
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["created_entries"], 2)
        self.assertEqual(data["data"]["created_offerings"], 2)

        # Verify DB entries
        with self.app.app_context():
            entries_count = TimetableEntry.query.count()
            self.assertEqual(entries_count, 2)
            offerings_count = CourseOffering.query.filter_by(academic_year="2026-27").count()
            self.assertEqual(offerings_count, 2)

        # 2. Re-import identical entries in 'add_missing' mode -> Should skip duplicates safely
        res_repeat = self.client.post(
            "/api/timetable/import/commit",
            headers=self.admin_headers,
            json=payload,
        )
        self.assertEqual(res_repeat.status_code, 200)
        repeat_data = res_repeat.get_json()
        self.assertEqual(repeat_data["data"]["created_entries"], 0)
        self.assertEqual(repeat_data["data"]["skipped_entries"], 2)

        # Verify no duplicate entries were created in DB
        with self.app.app_context():
            self.assertEqual(TimetableEntry.query.count(), 2)

    def test_commit_transaction_rollback_on_failure(self):
        # Entry with invalid course_id will be rejected
        payload = {
            "academic_year": "2026-27",
            "import_mode": "add_missing",
            "entries": [
                {
                    "course_id": 99999,  # Does not exist
                    "faculty_id": 1,
                    "section": "5CSE1",
                    "semester": 5,
                    "day_of_week": "Wednesday",
                    "start_time": "09:30",
                    "end_time": "10:30",
                    "room": "Room-999",
                }
            ],
        }

        res = self.client.post(
            "/api/timetable/import/commit",
            headers=self.admin_headers,
            json=payload,
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["data"]["created_entries"], 0)
        self.assertEqual(len(data["data"]["errors"]), 1)

        # Verify DB is clean
        with self.app.app_context():
            self.assertEqual(TimetableEntry.query.count(), 0)

    def test_master_timetable_sheet_discovery_prefers_master_timetable(self):
        bio = create_master_timetable_excel_bytes(
            sheet_name="Master Timetable",
            extra_sheets=["Read Me", "Sem 1-A", "Sem 1-B"],
        )
        res = self.client.post(
            "/api/timetable/import/sheets",
            headers=self.admin_headers,
            data={"file": (bio, "test_schedule.xlsx")},
            content_type="multipart/form-data",
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertIn("Master Timetable", data["sheets"])
        self.assertEqual(data["recommended"], "Master Timetable")

    def test_master_timetable_row_based_parsing_and_normalization(self):
        rows = [
            [
                "Monday", "P1", "08:40 AM - 09:40 AM", "08:40 AM", "09:40 AM",
                "BCSE-513", "Cloud Computing", 1, "Dr. Neera Batra",
                5, "A", "Room-302", "2026-2027", "", "Assigned",
            ],
            [
                "Tuesday", "P2", "09:40 AM - 10:40 AM", "09:40 AM", "10:40 AM",
                "BHUM-004", "Economics for Engineers", 2, "Dr. Monika",
                5, "A", "Room-105", "2026-2027", "", "Assigned",
            ],
        ]
        bio = create_master_timetable_excel_bytes(rows=rows)
        res = self.client.post(
            "/api/timetable/import/analyze",
            headers=self.admin_headers,
            data={
                "file": (bio, "master_timetable.xlsx"),
                "academic_year": "2026-2027",
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["total_rows"], 2)
        self.assertEqual(data["source_sheet"], "Master Timetable")

        entry1 = data["entries"][0]
        self.assertEqual(entry1["day_of_week"], "Monday")
        self.assertEqual(entry1["start_time"], "08:40")
        self.assertEqual(entry1["end_time"], "09:40")
        self.assertEqual(entry1["period"], "P1")
        self.assertEqual(entry1["course_code"], "BCSE-513")
        self.assertEqual(entry1["course_id"], 1)
        self.assertEqual(entry1["faculty_id"], 1)
        self.assertEqual(entry1["faculty_name"], "Dr. Neera Batra")
        self.assertEqual(entry1["semester"], 5)
        self.assertEqual(entry1["section"], "A")
        self.assertEqual(entry1["class_group"], "Sem 5-A")
        self.assertEqual(entry1["room"], "Room-302")
        self.assertIn(entry1["status"], {"matched", "warning"})
        self.assertEqual(entry1["offering_action"], "create")

        entry2 = data["entries"][1]
        self.assertEqual(entry2["day_of_week"], "Tuesday")
        self.assertEqual(entry2["course_code"], "BHUM-004")
        self.assertEqual(entry2["faculty_id"], 2)
        self.assertEqual(entry2["room"], "Room-105")

    def test_master_timetable_skips_blank_rows_and_break_schedules(self):
        rows = [
            [
                "Monday", "P1", "08:40 AM - 09:40 AM", "08:40 AM", "09:40 AM",
                "BCSE-513", "Cloud Computing", 1, "Dr. Neera Batra",
                5, "A", "Room-302", "2026-2027", "", "Assigned",
            ],
            [
                "Monday", "Break", "10:40 AM - 11:00 AM", "10:40 AM", "11:00 AM",
                "", "", "", "", 5, "A", "", "2026-2027", "Morning Break", "Break",
            ],
            ["", "", "", "", "", "", "", "", "", "", "", "", "", "", ""],
            [None, None, None, None, None, None, None, None, None, None, None, None, None, None, None],
            [
                "Monday", "P3", "11:00 AM - 12:00 PM", "11:00 AM", "12:00 PM",
                "BHUM-004", "Economics for Engineers", 2, "Dr. Monika",
                5, "A", "Room-105", "2026-2027", "", "Assigned",
            ],
        ]
        bio = create_master_timetable_excel_bytes(rows=rows)
        res = self.client.post(
            "/api/timetable/import/analyze",
            headers=self.admin_headers,
            data={
                "file": (bio, "master_timetable.xlsx"),
                "academic_year": "2026-2027",
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        # Exactly 2 teaching periods parsed; break and blank rows skipped
        self.assertEqual(data["total_rows"], 2)

    def test_master_timetable_unmatched_entities_and_academic_year_warning(self):
        rows = [
            [
                "Wednesday", "P1", "08:40 AM - 09:40 AM", "08:40 AM", "09:40 AM",
                "UNKNOWN-999", "Unknown Subject", 9999, "Unknown Faculty",
                5, "A", "Room-999", "2024-2025", "", "Assigned",
            ],
        ]
        bio = create_master_timetable_excel_bytes(rows=rows)
        res = self.client.post(
            "/api/timetable/import/analyze",
            headers=self.admin_headers,
            data={
                "file": (bio, "master_timetable.xlsx"),
                "academic_year": "2026-2027",
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["total_rows"], 1)

        entry = data["entries"][0]
        self.assertEqual(entry["status"], "unmatched")
        self.assertIsNone(entry["course_id"])
        self.assertIsNone(entry["faculty_id"])

        # Check academic year discrepancy warning is present
        has_ay_warning = any("differs from selected" in w for w in entry["warnings"])
        self.assertTrue(has_ay_warning)

    def test_master_timetable_database_remains_clean_before_commit(self):
        rows = [
            [
                "Thursday", "P1", "08:40 AM - 09:40 AM", "08:40 AM", "09:40 AM",
                "BCSE-513", "Cloud Computing", 1, "Dr. Neera Batra",
                5, "A", "Room-302", "2026-2027", "", "Assigned",
            ],
        ]
        bio = create_master_timetable_excel_bytes(rows=rows)
        res = self.client.post(
            "/api/timetable/import/analyze",
            headers=self.admin_headers,
            data={
                "file": (bio, "master_timetable.xlsx"),
                "academic_year": "2026-2027",
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(res.status_code, 200)

        # Database must not contain any new entries or offerings prior to commit
        with self.app.app_context():
            self.assertEqual(TimetableEntry.query.count(), 0)
            self.assertEqual(CourseOffering.query.count(), 0)

    def test_master_timetable_real_workbook_if_available(self):
        import os
        real_path = r"C:\Users\pandi\Downloads\CSE_Weekly_Timetable_Semesters_1_3_5_7.xlsx"
        if not os.path.exists(real_path):
            self.skipTest(f"Real workbook not found at {real_path}")

        with open(real_path, "rb") as f:
            file_bytes = f.read()

        bio = BytesIO(file_bytes)
        res = self.client.post(
            "/api/timetable/import/analyze",
            headers=self.admin_headers,
            data={
                "file": (bio, "CSE_Weekly_Timetable_Semesters_1_3_5_7.xlsx"),
                "academic_year": "2026-2027",
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["source_sheet"], "Master Timetable")
        self.assertEqual(data["total_rows"], 240)
        self.assertEqual(len(data["entries"]), 240)

        # Confirm DB is still completely untouched
        with self.app.app_context():
            self.assertEqual(TimetableEntry.query.count(), 0)
