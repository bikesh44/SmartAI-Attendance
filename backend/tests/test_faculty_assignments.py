"""
Unit & Integration Tests for Faculty Assignment & Notes Module
SAMS-FR (Smart Attendance Management System)
"""

import io
import os
import unittest
from datetime import datetime, timedelta
from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token
from sqlalchemy.pool import StaticPool

from app.extensions import db
from app.models import (
    AssignmentSubmission,
    Course,
    CourseAssignment,
    CourseOffering,
    Department,
    Enrollment,
    Faculty,
    Student,
    StudyMaterial,
    User,
)
from app.routes.faculty_assignments import faculty_assignments_bp


class TestFacultyAssignments(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = Flask(__name__)
        cls.app.config.update(
            TESTING=True,
            SECRET_KEY="test-faculty-assignments-secret",
            JWT_SECRET_KEY="test-jwt-faculty-assignments-key-32-bytes",
            SQLALCHEMY_DATABASE_URI="sqlite://",
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
            SQLALCHEMY_ENGINE_OPTIONS={
                "poolclass": StaticPool,
                "connect_args": {"check_same_thread": False},
            },
            JWT_TOKEN_LOCATION=["headers"],
        )

        db.init_app(cls.app)
        cls.jwt = JWTManager(cls.app)
        cls.app.register_blueprint(faculty_assignments_bp)

        with cls.app.app_context():
            db.create_all()

    def setUp(self):
        self.client = self.app.test_client()

        with self.app.app_context():
            # Clean up tables
            AssignmentSubmission.query.delete()
            StudyMaterial.query.delete()
            CourseAssignment.query.delete()
            Enrollment.query.delete()
            CourseOffering.query.delete()
            Course.query.delete()
            Student.query.delete()
            Faculty.query.delete()
            Department.query.delete()
            User.query.delete()
            db.session.commit()

            # Create test Department
            dept = Department(
                department_name="Computer Science & Engineering",
                department_code="CSE",
            )
            db.session.add(dept)
            db.session.flush()

            # Create Faculty User 1
            user_faculty_1 = User(
                name="Alan Turing",
                email="faculty1@sams.edu",
                password_hash="test-hash",
                role="FACULTY",
            )
            db.session.add(user_faculty_1)
            db.session.flush()

            faculty_1 = Faculty(
                user_id=user_faculty_1.user_id,
                department_id=dept.department_id,
                employee_id="FAC001",
                designation="Professor",
            )
            db.session.add(faculty_1)

            # Create Faculty User 2 (for authorization tests)
            user_faculty_2 = User(
                name="Ada Lovelace",
                email="faculty2@sams.edu",
                password_hash="test-hash",
                role="FACULTY",
            )
            db.session.add(user_faculty_2)
            db.session.flush()

            faculty_2 = Faculty(
                user_id=user_faculty_2.user_id,
                department_id=dept.department_id,
                employee_id="FAC002",
                designation="Associate Professor",
            )
            db.session.add(faculty_2)

            # Create Student Users
            user_student_1 = User(
                name="Grace Hopper",
                email="student1@sams.edu",
                password_hash="test-hash",
                role="STUDENT",
            )
            user_student_2 = User(
                name="Linus Torvalds",
                email="student2@sams.edu",
                password_hash="test-hash",
                role="STUDENT",
            )
            db.session.add_all([user_student_1, user_student_2])
            db.session.flush()

            student_1 = Student(
                user_id=user_student_1.user_id,
                department_id=dept.department_id,
                enrollment_no="ENR2026001",
                semester=3,
                section="A",
                academic_year="2026-2027",
            )
            student_2 = Student(
                user_id=user_student_2.user_id,
                department_id=dept.department_id,
                enrollment_no="ENR2026002",
                semester=3,
                section="A",
                academic_year="2026-2027",
            )
            db.session.add_all([student_1, student_2])

            # Create Courses
            course_cs101 = Course(
                department_id=dept.department_id,
                course_code="CS101",
                course_name="Data Structures",
                semester=3,
                credits=4,
            )
            course_cs102 = Course(
                department_id=dept.department_id,
                course_code="CS102",
                course_name="Algorithms",
                semester=3,
                credits=4,
            )
            db.session.add_all([course_cs101, course_cs102])
            db.session.flush()

            # Create Offerings: Offering 1 taught by Faculty 1; Offering 2 taught by Faculty 2
            offering_1 = CourseOffering(
                course_id=course_cs101.course_id,
                faculty_id=faculty_1.faculty_id,
                academic_year="2026-2027",
                semester=3,
                section="A",
                room="Room 101",
            )
            offering_2 = CourseOffering(
                course_id=course_cs102.course_id,
                faculty_id=faculty_2.faculty_id,
                academic_year="2026-2027",
                semester=3,
                section="B",
                room="Room 102",
            )
            db.session.add_all([offering_1, offering_2])
            db.session.flush()

            # Enroll students in Offering 1
            enr_1 = Enrollment(
                student_id=student_1.student_id,
                offering_id=offering_1.offering_id,
                status="ACTIVE",
            )
            enr_2 = Enrollment(
                student_id=student_2.student_id,
                offering_id=offering_1.offering_id,
                status="ACTIVE",
            )
            db.session.add_all([enr_1, enr_2])
            db.session.commit()

            # Save scalar IDs for detached tests
            self.faculty_1_id = faculty_1.faculty_id
            self.faculty_2_id = faculty_2.faculty_id
            self.user_faculty_1_id = user_faculty_1.user_id
            self.user_faculty_2_id = user_faculty_2.user_id
            self.student_1_id = student_1.student_id
            self.student_2_id = student_2.student_id
            self.offering_1_id = offering_1.offering_id
            self.offering_2_id = offering_2.offering_id

            # Generate JWT headers for Faculty 1 and Faculty 2
            with self.app.test_request_context():
                token_1 = create_access_token(
                    identity=str(self.user_faculty_1_id),
                    additional_claims={"role": "FACULTY"},
                )
                self.headers_faculty_1 = {"Authorization": f"Bearer {token_1}"}

                token_2 = create_access_token(
                    identity=str(self.user_faculty_2_id),
                    additional_claims={"role": "FACULTY"},
                )
                self.headers_faculty_2 = {"Authorization": f"Bearer {token_2}"}

    def test_get_classes(self):
        """Test retrieving course offerings taught by faculty."""
        resp = self.client.get("/api/faculty/assignments/classes", headers=self.headers_faculty_1)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(len(data["classes"]), 1)
        self.assertEqual(data["classes"][0]["course_code"], "CS101")
        self.assertEqual(data["classes"][0]["total_enrolled"], 2)

    def test_create_and_list_assignment(self):
        """Test creating an assignment and listing it."""
        due = (datetime.utcnow() + timedelta(days=5)).isoformat()
        payload = {
            "offering_id": self.offering_1_id,
            "title": "Data Structures Assignment 1",
            "description": "Implement a binary search tree",
            "assignment_type": "File Upload",
            "maximum_marks": 100,
            "due_date": due,
            "status": "PUBLISHED",
        }
        create_resp = self.client.post(
            "/api/faculty/assignments",
            headers=self.headers_faculty_1,
            json=payload,
        )
        self.assertEqual(create_resp.status_code, 201)
        res_data = create_resp.get_json()
        self.assertTrue(res_data["success"])
        asgn_id = res_data["assignment"]["assignment_id"]

        # List assignments
        list_resp = self.client.get("/api/faculty/assignments", headers=self.headers_faculty_1)
        self.assertEqual(list_resp.status_code, 200)
        list_data = list_resp.get_json()
        self.assertTrue(list_data["success"])
        self.assertEqual(len(list_data["assignments"]), 1)
        self.assertEqual(list_data["assignments"][0]["title"], "Data Structures Assignment 1")
        self.assertEqual(list_data["assignments"][0]["total_enrolled"], 2)
        self.assertEqual(list_data["assignments"][0]["submissions_count"], 0)

        # Detail view
        detail_resp = self.client.get(f"/api/faculty/assignments/{asgn_id}", headers=self.headers_faculty_1)
        self.assertEqual(detail_resp.status_code, 200)
        self.assertEqual(detail_resp.get_json()["assignment"]["title"], "Data Structures Assignment 1")

    def test_assignment_file_upload(self):
        """Test creating an assignment with file attachment."""
        due = (datetime.utcnow() + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
        data = {
            "offering_id": str(self.offering_1_id),
            "title": "Assignment with Worksheet",
            "description": "See attached worksheet PDF",
            "due_date": due,
            "file": (io.BytesIO(b"%PDF-1.4 dummy pdf content"), "worksheet.pdf"),
        }
        resp = self.client.post(
            "/api/faculty/assignments",
            headers=self.headers_faculty_1,
            data=data,
            content_type="multipart/form-data",
        )
        self.assertEqual(resp.status_code, 201)
        asgn_id = resp.get_json()["assignment"]["assignment_id"]

        # Download attachment
        dl_resp = self.client.get(f"/api/faculty/assignments/{asgn_id}/download", headers=self.headers_faculty_1)
        self.assertEqual(dl_resp.status_code, 200)
        self.assertEqual(dl_resp.data, b"%PDF-1.4 dummy pdf content")

    def test_update_and_status_toggle(self):
        """Test updating assignment fields and toggling status."""
        asgn = CourseAssignment(
            offering_id=self.offering_1_id,
            faculty_id=self.faculty_1_id,
            title="Initial Title",
            maximum_marks=50,
            due_date=datetime.utcnow() + timedelta(days=3),
            status="PUBLISHED",
        )
        with self.app.app_context():
            db.session.add(asgn)
            db.session.commit()
            asgn_id = asgn.assignment_id

        # Update assignment
        up_resp = self.client.put(
            f"/api/faculty/assignments/{asgn_id}",
            headers=self.headers_faculty_1,
            json={"title": "Updated Title", "maximum_marks": 75},
        )
        self.assertEqual(up_resp.status_code, 200)

        # Status toggle
        st_resp = self.client.patch(
            f"/api/faculty/assignments/{asgn_id}/status",
            headers=self.headers_faculty_1,
            json={"status": "CLOSED"},
        )
        self.assertEqual(st_resp.status_code, 200)
        self.assertEqual(st_resp.get_json()["status"], "CLOSED")

    def test_delete_assignment(self):
        """Test deleting an assignment."""
        asgn = CourseAssignment(
            offering_id=self.offering_1_id,
            faculty_id=self.faculty_1_id,
            title="To Delete",
            due_date=datetime.utcnow() + timedelta(days=1),
        )
        with self.app.app_context():
            db.session.add(asgn)
            db.session.commit()
            asgn_id = asgn.assignment_id

        del_resp = self.client.delete(f"/api/faculty/assignments/{asgn_id}", headers=self.headers_faculty_1)
        self.assertEqual(del_resp.status_code, 200)

        # Verify not found
        get_resp = self.client.get(f"/api/faculty/assignments/{asgn_id}", headers=self.headers_faculty_1)
        self.assertEqual(get_resp.status_code, 404)

    def test_submissions_roster_and_evaluation(self):
        """Test student submission roster and grading submission."""
        asgn = CourseAssignment(
            offering_id=self.offering_1_id,
            faculty_id=self.faculty_1_id,
            title="Graded Assignment",
            maximum_marks=100,
            due_date=datetime.utcnow() + timedelta(days=2),
        )
        with self.app.app_context():
            db.session.add(asgn)
            db.session.commit()
            asgn_id = asgn.assignment_id

            # Create submission for student 1
            sub = AssignmentSubmission(
                assignment_id=asgn_id,
                student_id=self.student_1_id,
                submission_text="Here is my code implementation",
                submitted_at=datetime.utcnow(),
                review_status="PENDING",
            )
            db.session.add(sub)
            db.session.commit()
            sub_id = sub.submission_id

        # Get roster
        roster_resp = self.client.get(f"/api/faculty/assignments/{asgn_id}/submissions", headers=self.headers_faculty_1)
        self.assertEqual(roster_resp.status_code, 200)
        data = roster_resp.get_json()
        self.assertEqual(data["total_enrolled"], 2)
        self.assertEqual(data["total_submitted"], 1)
        self.assertEqual(data["total_reviewed"], 0)

        # Check student 1 is submitted, student 2 is not
        st1_entry = next(r for r in data["submissions"] if r["student_id"] == self.student_1_id)
        st2_entry = next(r for r in data["submissions"] if r["student_id"] == self.student_2_id)
        self.assertTrue(st1_entry["submitted"])
        self.assertFalse(st2_entry["submitted"])
        self.assertEqual(st2_entry["review_status"], "NOT_SUBMITTED")

        # Evaluate submission
        eval_resp = self.client.post(
            f"/api/faculty/assignments/submissions/{sub_id}/evaluate",
            headers=self.headers_faculty_1,
            json={"marks_obtained": 92.5, "feedback": "Excellent work!"},
        )
        self.assertEqual(eval_resp.status_code, 200)
        eval_data = eval_resp.get_json()["submission"]
        self.assertEqual(eval_data["marks_obtained"], 92.5)
        self.assertEqual(eval_data["review_status"], "REVIEWED")

        # Test invalid marks exceeding max marks
        inv_resp = self.client.post(
            f"/api/faculty/assignments/submissions/{sub_id}/evaluate",
            headers=self.headers_faculty_1,
            json={"marks_obtained": 150, "feedback": "Invalid"},
        )
        self.assertEqual(inv_resp.status_code, 400)

    def test_notes_crud(self):
        """Test study materials / notes upload, listing, and deletion."""
        data = {
            "offering_id": str(self.offering_1_id),
            "title": "Week 1 Lecture Notes",
            "description": "Introduction to algorithm complexity",
            "category": "LECTURE_NOTES",
            "file": (io.BytesIO(b"Notes content text"), "lecture_week1.txt"),
        }
        upload_resp = self.client.post(
            "/api/faculty/assignments/notes",
            headers=self.headers_faculty_1,
            data=data,
            content_type="multipart/form-data",
        )
        self.assertEqual(upload_resp.status_code, 201)
        note_id = upload_resp.get_json()["note"]["material_id"]

        # List notes
        list_resp = self.client.get("/api/faculty/assignments/notes", headers=self.headers_faculty_1)
        self.assertEqual(list_resp.status_code, 200)
        notes = list_resp.get_json()["notes"]
        self.assertEqual(len(notes), 1)
        self.assertEqual(notes[0]["title"], "Week 1 Lecture Notes")
        self.assertEqual(notes[0]["category"], "LECTURE_NOTES")

        # Download note
        dl_resp = self.client.get(f"/api/faculty/assignments/notes/{note_id}/download", headers=self.headers_faculty_1)
        self.assertEqual(dl_resp.status_code, 200)
        self.assertEqual(dl_resp.data, b"Notes content text")

        # Delete note
        del_resp = self.client.delete(f"/api/faculty/assignments/notes/{note_id}", headers=self.headers_faculty_1)
        self.assertEqual(del_resp.status_code, 200)

    def test_summary_and_class_overview(self):
        """Test summary metrics and class overview endpoints."""
        asgn = CourseAssignment(
            offering_id=self.offering_1_id,
            faculty_id=self.faculty_1_id,
            title="Summary Test Asgn",
            due_date=datetime.utcnow() + timedelta(days=1),
        )
        with self.app.app_context():
            db.session.add(asgn)
            db.session.commit()

            sub = AssignmentSubmission(
                assignment_id=asgn.assignment_id,
                student_id=self.student_1_id,
                review_status="PENDING",
            )
            db.session.add(sub)
            db.session.commit()

        # Summary check
        sum_resp = self.client.get("/api/faculty/assignments/summary", headers=self.headers_faculty_1)
        self.assertEqual(sum_resp.status_code, 200)
        sum_data = sum_resp.get_json()["summary"]
        self.assertEqual(sum_data["total_assignments"], 1)
        self.assertEqual(sum_data["total_submissions"], 1)
        self.assertEqual(sum_data["pending_review"], 1)

        # Overview check
        ov_resp = self.client.get("/api/faculty/assignments/class-overview", headers=self.headers_faculty_1)
        self.assertEqual(ov_resp.status_code, 200)
        classes = ov_resp.get_json()["classes"]
        self.assertEqual(len(classes), 1)
        self.assertEqual(classes[0]["course_code"], "CS101")
        self.assertEqual(classes[0]["assignments_count"], 1)
        self.assertEqual(classes[0]["total_enrolled"], 2)

    def test_cross_faculty_authorization_protection(self):
        """Test that faculty cannot access or modify another faculty's assignments."""
        asgn = CourseAssignment(
            offering_id=self.offering_2_id,  # Owned by Faculty 2
            faculty_id=self.faculty_2_id,
            title="Faculty 2 Assignment",
            due_date=datetime.utcnow() + timedelta(days=2),
        )
        with self.app.app_context():
            db.session.add(asgn)
            db.session.commit()
            asgn_id = asgn.assignment_id

        # Faculty 1 attempts to modify Faculty 2's assignment -> 403 Forbidden
        mod_resp = self.client.put(
            f"/api/faculty/assignments/{asgn_id}",
            headers=self.headers_faculty_1,
            json={"title": "Hacked Title"},
        )
        self.assertEqual(mod_resp.status_code, 403)

        del_resp = self.client.delete(f"/api/faculty/assignments/{asgn_id}", headers=self.headers_faculty_1)
        self.assertEqual(del_resp.status_code, 403)


if __name__ == "__main__":
    unittest.main()
