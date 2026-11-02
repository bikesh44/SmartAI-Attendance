"""
Integration and unit tests for Admin Academic Results Management,
faculty submission, admin review, approval, return, publication, and corrections.
Tests use an isolated SQLite in-memory database to prevent modifying live records.
"""

import unittest
from datetime import datetime
from decimal import Decimal

from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token
from sqlalchemy.pool import StaticPool

from app.extensions import db
from app.models import (
    AcademicResult,
    Assessment,
    Course,
    CourseOffering,
    Department,
    Enrollment,
    Faculty,
    ResultCorrection,
    ResultSubmission,
    Student,
    User,
)
from app.routes.admin_academic_results import admin_academic_results_bp
from app.routes.student_academic import student_academic_bp


class TestAdminAcademicResults(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = Flask(__name__)
        cls.app.config.update(
            TESTING=True,
            SECRET_KEY="test-admin-academic-secret",
            JWT_SECRET_KEY="test-jwt-secret-admin-academic-key",
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
        cls.app.register_blueprint(admin_academic_results_bp)
        cls.app.register_blueprint(student_academic_bp)

        with cls.app.app_context():
            db.create_all()

    def setUp(self):
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()

        db.session.remove()
        db.drop_all()
        db.create_all()

        # 1. Users
        self.admin_user = User(
            name="Super Admin",
            email="admin@univ.edu",
            password_hash="admin_pw",
            role="ADMIN",
        )
        self.faculty_user1 = User(
            name="Prof. Sharma",
            email="sharma@univ.edu",
            password_hash="fac_pw_1",
            role="FACULTY",
        )
        self.faculty_user2 = User(
            name="Dr. Verma",
            email="verma@univ.edu",
            password_hash="fac_pw_2",
            role="FACULTY",
        )
        self.student_user = User(
            name="Ananya Student",
            email="ananya@univ.edu",
            password_hash="stu_pw",
            role="STUDENT",
        )
        db.session.add_all([self.admin_user, self.faculty_user1, self.faculty_user2, self.student_user])
        db.session.commit()

        # 2. Department & Faculty
        self.dept = Department(
            department_name="Computer Science & Engineering",
            department_code="CSE",
        )
        db.session.add(self.dept)
        db.session.commit()

        self.faculty1 = Faculty(
            user_id=self.faculty_user1.user_id,
            department_id=self.dept.department_id,
            employee_id="FAC001",
            designation="Professor",
        )
        self.faculty2 = Faculty(
            user_id=self.faculty_user2.user_id,
            department_id=self.dept.department_id,
            employee_id="FAC002",
            designation="Associate Professor",
        )
        db.session.add_all([self.faculty1, self.faculty2])
        db.session.commit()

        # 3. Student
        self.student = Student(
            user_id=self.student_user.user_id,
            department_id=self.dept.department_id,
            enrollment_no="CSE2024001",
            semester=6,
            section="A",
            academic_year="2024-2025",
        )
        db.session.add(self.student)
        db.session.commit()

        # 4. Course & Offering
        self.course = Course(
            department_id=self.dept.department_id,
            course_code="CSE301",
            course_name="Operating Systems",
            semester=6,
            credits=4,
        )
        db.session.add(self.course)
        db.session.commit()

        self.offering = CourseOffering(
            course_id=self.course.course_id,
            faculty_id=self.faculty1.faculty_id,  # Assigned to Prof. Sharma
            academic_year="2024-2025",
            semester=6,
            section="A",
        )
        db.session.add(self.offering)
        db.session.commit()

        # 5. Enrollment
        self.enrollment = Enrollment(
            student_id=self.student.student_id,
            offering_id=self.offering.offering_id,
            status="ACTIVE",
        )
        db.session.add(self.enrollment)
        db.session.commit()

        # Tokens
        self.admin_token = create_access_token(
            identity=str(self.admin_user.user_id),
            additional_claims={"role": "ADMIN"},
        )
        self.faculty1_token = create_access_token(
            identity=str(self.faculty_user1.user_id),
            additional_claims={"role": "FACULTY"},
        )
        self.faculty2_token = create_access_token(
            identity=str(self.faculty_user2.user_id),
            additional_claims={"role": "FACULTY"},
        )
        self.student_token = create_access_token(
            identity=str(self.student_user.user_id),
            additional_claims={"role": "STUDENT"},
        )

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    # ----------------------------------------------------
    # RBAC & SECURITY TESTS
    # ----------------------------------------------------

    def test_student_forbidden_from_admin_overview(self):
        resp = self.client.get(
            "/api/admin/academic-results/overview",
            headers={"Authorization": f"Bearer {self.student_token}"},
        )
        self.assertEqual(resp.status_code, 403)

    def test_faculty_forbidden_from_admin_overview(self):
        resp = self.client.get(
            "/api/admin/academic-results/overview",
            headers={"Authorization": f"Bearer {self.faculty1_token}"},
        )
        self.assertEqual(resp.status_code, 403)

    def test_admin_can_access_overview(self):
        resp = self.client.get(
            "/api/admin/academic-results/overview",
            headers={"Authorization": f"Bearer {self.admin_token}"},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()["data"]
        self.assertEqual(data["cards"]["pending_reviews"], 0)
        self.assertEqual(data["cards"]["published_results"], 0)

    # ----------------------------------------------------
    # FACULTY OWNERSHIP & SUBMISSION WORKFLOW
    # ----------------------------------------------------

    def test_unassigned_faculty_cannot_submit_marks(self):
        # Faculty 2 tries to submit for Faculty 1's offering
        resp = self.client.post(
            f"/api/admin/academic-results/faculty/offerings/{self.offering.offering_id}/submit",
            headers={"Authorization": f"Bearer {self.faculty2_token}"},
            json={
                "action": "SUBMIT",
                "scores": [{"student_id": self.student.student_id, "marks_obtained": 85.0}],
            },
        )
        self.assertEqual(resp.status_code, 403)

    def test_assigned_faculty_can_submit_marks(self):
        resp = self.client.post(
            f"/api/admin/academic-results/faculty/offerings/{self.offering.offering_id}/submit",
            headers={"Authorization": f"Bearer {self.faculty1_token}"},
            json={
                "action": "SUBMIT",
                "assessment_name": "End-Semester Examination",
                "max_marks": 100.0,
                "scores": [{"student_id": self.student.student_id, "marks_obtained": 88.0, "remarks": "Excellent"}],
            },
        )
        self.assertEqual(resp.status_code, 200)
        sub_data = resp.get_json()["data"]
        self.assertEqual(sub_data["status"], "SUBMITTED")
        self.assertEqual(sub_data["passed_students"], 1)

        # Verify child result is NOT published yet to the student
        result = AcademicResult.query.filter_by(student_id=self.student.student_id).first()
        self.assertIsNotNone(result)
        self.assertFalse(result.is_published)

        # Check student results endpoint - must NOT return unpublished marks
        stu_resp = self.client.get(
            "/api/student/academic-records/results",
            headers={"Authorization": f"Bearer {self.student_token}"},
        )
        self.assertEqual(stu_resp.status_code, 200)
        self.assertEqual(len(stu_resp.get_json()["data"]["results"]), 0)

    # ----------------------------------------------------
    # ADMIN REVIEW, RETURN & APPROVAL WORKFLOW
    # ----------------------------------------------------

    def test_admin_return_requires_reason(self):
        # First submit marks
        self.client.post(
            f"/api/admin/academic-results/faculty/offerings/{self.offering.offering_id}/submit",
            headers={"Authorization": f"Bearer {self.faculty1_token}"},
            json={
                "action": "SUBMIT",
                "scores": [{"student_id": self.student.student_id, "marks_obtained": 88.0}],
            },
        )
        sub = ResultSubmission.query.first()

        # Admin attempts to return without reason
        resp = self.client.post(
            f"/api/admin/academic-results/submissions/{sub.submission_id}/return",
            headers={"Authorization": f"Bearer {self.admin_token}"},
            json={"reason": ""},
        )
        self.assertEqual(resp.status_code, 400)

        # Admin returns with valid reason
        resp2 = self.client.post(
            f"/api/admin/academic-results/submissions/{sub.submission_id}/return",
            headers={"Authorization": f"Bearer {self.admin_token}"},
            json={"reason": "Practical marks distribution is missing from attendance records."},
        )
        self.assertEqual(resp2.status_code, 200)
        self.assertEqual(resp2.get_json()["data"]["status"], "RETURNED")

    def test_admin_approve_and_publish_flow(self):
        # 1. Faculty submits
        self.client.post(
            f"/api/admin/academic-results/faculty/offerings/{self.offering.offering_id}/submit",
            headers={"Authorization": f"Bearer {self.faculty1_token}"},
            json={
                "action": "SUBMIT",
                "scores": [{"student_id": self.student.student_id, "marks_obtained": 84.0}],
            },
        )
        sub = ResultSubmission.query.first()

        # Cannot publish before approving
        resp_pub_fail = self.client.post(
            f"/api/admin/academic-results/submissions/{sub.submission_id}/publish",
            headers={"Authorization": f"Bearer {self.admin_token}"},
        )
        self.assertEqual(resp_pub_fail.status_code, 400)

        # 2. Admin approves
        resp_app = self.client.post(
            f"/api/admin/academic-results/submissions/{sub.submission_id}/approve",
            headers={"Authorization": f"Bearer {self.admin_token}"},
            json={"remarks": "Verified by examination cell"},
        )
        self.assertEqual(resp_app.status_code, 200)
        self.assertEqual(resp_app.get_json()["data"]["status"], "APPROVED")

        # 3. Admin publishes
        resp_pub = self.client.post(
            f"/api/admin/academic-results/submissions/{sub.submission_id}/publish",
            headers={"Authorization": f"Bearer {self.admin_token}"},
        )
        self.assertEqual(resp_pub.status_code, 200)
        self.assertEqual(resp_pub.get_json()["data"]["status"], "PUBLISHED")

        # 4. Verify student can now see published result in Student Portal
        stu_resp = self.client.get(
            "/api/student/academic-records/results",
            headers={"Authorization": f"Bearer {self.student_token}"},
        )
        self.assertEqual(stu_resp.status_code, 200)
        results = stu_resp.get_json()["data"]["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["subject_code"], "CSE301")
        self.assertEqual(results[0]["marks"], 84.0)
        self.assertEqual(results[0]["status"], "Pass")

    # ----------------------------------------------------
    # POST-PUBLICATION CORRECTIONS & AUDIT HISTORY
    # ----------------------------------------------------

    def test_post_publication_correction_and_audit(self):
        # Submit, approve, publish
        self.client.post(
            f"/api/admin/academic-results/faculty/offerings/{self.offering.offering_id}/submit",
            headers={"Authorization": f"Bearer {self.faculty1_token}"},
            json={
                "action": "SUBMIT",
                "scores": [{"student_id": self.student.student_id, "marks_obtained": 84.0}],
            },
        )
        sub = ResultSubmission.query.first()
        app_resp = self.client.post(f"/api/admin/academic-results/submissions/{sub.submission_id}/approve", headers={"Authorization": f"Bearer {self.admin_token}"}, json={})
        self.assertEqual(app_resp.status_code, 200)
        pub_resp = self.client.post(f"/api/admin/academic-results/submissions/{sub.submission_id}/publish", headers={"Authorization": f"Bearer {self.admin_token}"}, json={})
        self.assertEqual(pub_resp.status_code, 200)

        res = AcademicResult.query.first()

        # Admin makes correction
        corr_resp = self.client.post(
            "/api/admin/academic-results/corrections",
            headers={"Authorization": f"Bearer {self.admin_token}"},
            json={
                "result_id": res.result_id,
                "new_marks": 92.0,
                "reason": "Re-evaluation discrepancy approved by Academic Council.",
            },
        )
        self.assertEqual(corr_resp.status_code, 200)
        self.assertEqual(corr_resp.get_json()["data"]["marks_obtained"], 92.0)
        self.assertEqual(corr_resp.get_json()["data"]["grade"], "A+")

        # Verify audit history
        audit_resp = self.client.get(
            "/api/admin/academic-results/audit-history",
            headers={"Authorization": f"Bearer {self.admin_token}"},
        )
        self.assertEqual(audit_resp.status_code, 200)
        events = audit_resp.get_json()["data"]
        self.assertTrue(any(e["type"] == "RESULT_CORRECTED" for e in events))
        self.assertTrue(any(e["type"] == "RESULT_PUBLISHED" for e in events))
