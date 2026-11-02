"""
Unit & Integration Tests for Student Assignments & Notes Module
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
from app.routes.student_assignments import student_assignments_bp


class TestStudentAssignments(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = Flask(__name__)
        cls.app.config.update(
            TESTING=True,
            SECRET_KEY="test-student-assignments-secret",
            JWT_SECRET_KEY="test-jwt-student-assignments-key-32-bytes",
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
        cls.app.register_blueprint(student_assignments_bp)

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

            # Create Faculty
            user_fac = User(
                name="Prof. Donald Knuth",
                email="knuth@sams.edu",
                password_hash="test-hash",
                role="FACULTY",
            )
            db.session.add(user_fac)
            db.session.flush()

            faculty = Faculty(
                user_id=user_fac.user_id,
                department_id=dept.department_id,
                employee_id="FAC999",
                designation="Professor",
            )
            db.session.add(faculty)
            db.session.flush()

            # Create Student 1 (Enrolled in Course 1)
            user_st1 = User(
                name="Aarav Sharma",
                email="aarav@sams.edu",
                password_hash="test-hash",
                role="STUDENT",
            )
            # Create Student 2 (Enrolled in Course 2, not Course 1)
            user_st2 = User(
                name="Sneha Patel",
                email="sneha@sams.edu",
                password_hash="test-hash",
                role="STUDENT",
            )
            db.session.add_all([user_st1, user_st2])
            db.session.flush()

            student_1 = Student(
                user_id=user_st1.user_id,
                department_id=dept.department_id,
                enrollment_no="STU2026001",
                semester=3,
                section="A",
                academic_year="2026-2027",
            )
            student_2 = Student(
                user_id=user_st2.user_id,
                department_id=dept.department_id,
                enrollment_no="STU2026002",
                semester=3,
                section="B",
                academic_year="2026-2027",
            )
            db.session.add_all([student_1, student_2])
            db.session.flush()

            # Create Courses & Offerings
            c1 = Course(
                department_id=dept.department_id,
                course_code="CS101",
                course_name="Data Structures",
                semester=3,
                credits=4,
            )
            c2 = Course(
                department_id=dept.department_id,
                course_code="MATH101",
                course_name="Calculus",
                semester=3,
                credits=4,
            )
            db.session.add_all([c1, c2])
            db.session.flush()

            off1 = CourseOffering(
                course_id=c1.course_id,
                faculty_id=faculty.faculty_id,
                academic_year="2026-2027",
                semester=3,
                section="A",
            )
            off2 = CourseOffering(
                course_id=c2.course_id,
                faculty_id=faculty.faculty_id,
                academic_year="2026-2027",
                semester=3,
                section="B",
            )
            db.session.add_all([off1, off2])
            db.session.flush()

            # Enroll Student 1 in Offering 1
            enr1 = Enrollment(
                student_id=student_1.student_id,
                offering_id=off1.offering_id,
                status="ACTIVE",
            )
            # Enroll Student 2 in Offering 2
            enr2 = Enrollment(
                student_id=student_2.student_id,
                offering_id=off2.offering_id,
                status="ACTIVE",
            )
            db.session.add_all([enr1, enr2])
            db.session.commit()

            # Store scalar IDs
            self.user_st1_id = user_st1.user_id
            self.user_st2_id = user_st2.user_id
            self.student_1_id = student_1.student_id
            self.student_2_id = student_2.student_id
            self.faculty_id = faculty.faculty_id
            self.offering_1_id = off1.offering_id
            self.offering_2_id = off2.offering_id

            # Create JWT tokens
            with self.app.test_request_context():
                tok1 = create_access_token(
                    identity=str(self.user_st1_id),
                    additional_claims={"role": "STUDENT"},
                )
                self.headers_st1 = {"Authorization": f"Bearer {tok1}"}

                tok2 = create_access_token(
                    identity=str(self.user_st2_id),
                    additional_claims={"role": "STUDENT"},
                )
                self.headers_st2 = {"Authorization": f"Bearer {tok2}"}

    def test_summary_and_enrolled_classes(self):
        """Test summary metrics and enrolled classes endpoint for student."""
        # Create published assignment and note in Offering 1
        with self.app.app_context():
            asgn = CourseAssignment(
                offering_id=self.offering_1_id,
                faculty_id=self.faculty_id,
                title="Linked List Implementation",
                maximum_marks=50,
                due_date=datetime.utcnow() + timedelta(days=5),
                status="PUBLISHED",
            )
            note = StudyMaterial(
                offering_id=self.offering_1_id,
                faculty_id=self.faculty_id,
                title="Linked List Lecture Notes",
                category="LECTURE_NOTES",
                file_path="dummy.pdf",
                file_name="notes.pdf",
                file_type="pdf",
                visibility="PUBLISHED",
            )
            db.session.add_all([asgn, note])
            db.session.commit()

        # Student 1 summary
        res = self.client.get("/api/student/assignments/summary", headers=self.headers_st1)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()["summary"]
        self.assertEqual(data["total_assignments"], 1)
        self.assertEqual(data["pending_assignments"], 1)
        self.assertEqual(data["submitted_assignments"], 0)
        self.assertEqual(data["notes_available"], 1)

        # Enrolled classes
        classes_res = self.client.get("/api/student/assignments/enrolled-classes", headers=self.headers_st1)
        self.assertEqual(classes_res.status_code, 200)
        classes_data = classes_res.get_json()["classes"]
        self.assertEqual(len(classes_data), 1)
        self.assertEqual(classes_data[0]["course_code"], "CS101")

        # Student 2 (not enrolled in Offering 1) sees 0
        res2 = self.client.get("/api/student/assignments/summary", headers=self.headers_st2)
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(res2.get_json()["summary"]["total_assignments"], 0)

    def test_assignments_visibility_and_details(self):
        """Test student assignment listing respects publication status and course enrollment."""
        with self.app.app_context():
            # Published assignment in Offering 1
            asgn_pub = CourseAssignment(
                offering_id=self.offering_1_id,
                faculty_id=self.faculty_id,
                title="Published Tree Assignment",
                due_date=datetime.utcnow() + timedelta(days=3),
                status="PUBLISHED",
            )
            # Draft assignment in Offering 1 (MUST NOT be visible to student)
            asgn_draft = CourseAssignment(
                offering_id=self.offering_1_id,
                faculty_id=self.faculty_id,
                title="Draft Quiz Hidden",
                due_date=datetime.utcnow() + timedelta(days=2),
                status="DRAFT",
            )
            # Published assignment in Offering 2 (Student 1 NOT enrolled)
            asgn_off2 = CourseAssignment(
                offering_id=self.offering_2_id,
                faculty_id=self.faculty_id,
                title="Calculus Integration",
                due_date=datetime.utcnow() + timedelta(days=4),
                status="PUBLISHED",
            )
            db.session.add_all([asgn_pub, asgn_draft, asgn_off2])
            db.session.commit()
            asgn_pub_id = asgn_pub.assignment_id
            asgn_off2_id = asgn_off2.assignment_id

        # Student 1 lists assignments
        res = self.client.get("/api/student/assignments", headers=self.headers_st1)
        self.assertEqual(res.status_code, 200)
        asgns = res.get_json()["assignments"]
        self.assertEqual(len(asgns), 1)
        self.assertEqual(asgns[0]["title"], "Published Tree Assignment")

        # Student 1 gets detail of published assignment
        det_res = self.client.get(f"/api/student/assignments/{asgn_pub_id}", headers=self.headers_st1)
        self.assertEqual(det_res.status_code, 200)
        self.assertEqual(det_res.get_json()["assignment"]["title"], "Published Tree Assignment")

        # Student 1 attempts to get assignment from Offering 2 -> 403 Forbidden
        forb_res = self.client.get(f"/api/student/assignments/{asgn_off2_id}", headers=self.headers_st1)
        self.assertEqual(forb_res.status_code, 403)

    def test_assignment_submission_workflow(self):
        """Test submitting assignment text and file, deadline enforcement, and late detection."""
        with self.app.app_context():
            asgn = CourseAssignment(
                offering_id=self.offering_1_id,
                faculty_id=self.faculty_id,
                title="Graph Algorithms",
                maximum_marks=100,
                due_date=datetime.utcnow() + timedelta(days=2),
                submission_type="FILE_UPLOAD",
                allowed_file_types="pdf,txt",
                maximum_file_size_mb=5,
                allow_late_submission=True,
                status="PUBLISHED",
            )
            db.session.add(asgn)
            db.session.commit()
            asgn_id = asgn.assignment_id

        # Submit with file
        data = {
            "file": (io.BytesIO(b"Graph code implementation"), "solution.txt"),
            "submission_text": "Completed Dijkstra and BFS",
        }
        sub_res = self.client.post(
            f"/api/student/assignments/{asgn_id}/submit",
            headers=self.headers_st1,
            data=data,
            content_type="multipart/form-data",
        )
        self.assertEqual(sub_res.status_code, 201)
        sub_id = sub_res.get_json()["submission"]["submission_id"]

        # Duplicate submission without resubmit flag should be rejected
        dup_data = {
            "file": (io.BytesIO(b"Duplicate attempt"), "solution.txt"),
            "submission_text": "Trying again",
        }
        dup_res = self.client.post(
            f"/api/student/assignments/{asgn_id}/submit",
            headers=self.headers_st1,
            data=dup_data,
            content_type="multipart/form-data",
        )
        self.assertEqual(dup_res.status_code, 400)

        # Download submitted file
        dl_res = self.client.get(f"/api/student/assignments/submissions/{sub_id}/download", headers=self.headers_st1)
        self.assertEqual(dl_res.status_code, 200)
        self.assertEqual(dl_res.data, b"Graph code implementation")

        # Student 2 cannot download Student 1's submission
        dl_forb = self.client.get(f"/api/student/assignments/submissions/{sub_id}/download", headers=self.headers_st2)
        self.assertEqual(dl_forb.status_code, 404)

    def test_late_submission_rejection_when_disallowed(self):
        """Test overdue assignment rejects submission when late submission is disallowed."""
        with self.app.app_context():
            asgn = CourseAssignment(
                offering_id=self.offering_1_id,
                faculty_id=self.faculty_id,
                title="Strict Deadline Assignment",
                due_date=datetime.utcnow() - timedelta(hours=2),  # Already passed
                allow_late_submission=False,
                status="PUBLISHED",
            )
            db.session.add(asgn)
            db.session.commit()
            asgn_id = asgn.assignment_id

        res = self.client.post(
            f"/api/student/assignments/{asgn_id}/submit",
            headers=self.headers_st1,
            json={"submission_text": "Late answer"},
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("deadline has passed", res.get_json()["message"].lower())

    def test_study_materials_notes_tab(self):
        """Test student study materials listing and download authorization."""
        with self.app.app_context():
            note_pub = StudyMaterial(
                offering_id=self.offering_1_id,
                faculty_id=self.faculty_id,
                title="Syllabus and Slides",
                category="LECTURE_NOTES",
                file_path=os.path.join(os.path.dirname(__file__), "test_student_assignments.py"),
                file_name="slides.pdf",
                file_type="pdf",
                visibility="PUBLISHED",
            )
            note_draft = StudyMaterial(
                offering_id=self.offering_1_id,
                faculty_id=self.faculty_id,
                title="Unpublished Draft Note",
                category="OTHER",
                file_path="draft.pdf",
                file_name="draft.pdf",
                file_type="pdf",
                visibility="DRAFT",
            )
            db.session.add_all([note_pub, note_draft])
            db.session.commit()
            note_pub_id = note_pub.material_id

        # Student 1 lists notes
        res = self.client.get("/api/student/assignments/notes", headers=self.headers_st1)
        self.assertEqual(res.status_code, 200)
        notes = res.get_json()["notes"]
        self.assertEqual(len(notes), 1)
        self.assertEqual(notes[0]["title"], "Syllabus and Slides")

        # Student 2 (not enrolled in Offering 1) attempts download -> 403 Forbidden
        dl_res = self.client.get(f"/api/student/assignments/notes/{note_pub_id}/download", headers=self.headers_st2)
        self.assertEqual(dl_res.status_code, 403)

    def test_results_and_feedback(self):
        """Test that evaluated results and feedback are visible once reviewed."""
        with self.app.app_context():
            asgn = CourseAssignment(
                offering_id=self.offering_1_id,
                faculty_id=self.faculty_id,
                title="Graded Quiz",
                maximum_marks=50,
                due_date=datetime.utcnow() + timedelta(days=2),
                status="PUBLISHED",
            )
            db.session.add(asgn)
            db.session.commit()

            sub = AssignmentSubmission(
                assignment_id=asgn.assignment_id,
                student_id=self.student_1_id,
                marks_obtained=45.0,
                feedback="Well structured code!",
                review_status="REVIEWED",
                reviewed_at=datetime.utcnow(),
            )
            db.session.add(sub)
            db.session.commit()

        res = self.client.get("/api/student/assignments/results", headers=self.headers_st1)
        self.assertEqual(res.status_code, 200)
        results = res.get_json()["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["marks_obtained"], 45.0)
        self.assertEqual(results[0]["maximum_marks"], 50.0)
        self.assertEqual(results[0]["percentage"], 90.0)
        self.assertEqual(results[0]["feedback"], "Well structured code!")


if __name__ == "__main__":
    unittest.main()
