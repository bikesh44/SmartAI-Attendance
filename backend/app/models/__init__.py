from app.models.user import User
from app.models.department import Department
from app.models.student import Student
from app.models.faculty import Faculty
from app.models.course import Course
from app.models.course_offering import CourseOffering
from app.models.enrollment import Enrollment
from app.models.face_profile import FaceProfile
from app.models.attendance_session import AttendanceSession
from app.models.attendance_record import AttendanceRecord

from app.models.timetable_entry import TimetableEntry
from app.models.faculty_adjustment import FacultyAdjustment

from app.models.batch import Batch
from app.models.system_setting import SystemSetting
from app.models.activity_log import ActivityLog

from app.models.examination import Examination
from app.models.academic_result import AcademicResult
from app.models.academic_document import AcademicDocument
from app.models.assessment import Assessment
from app.models.result_submission import ResultSubmission
from app.models.result_correction import ResultCorrection
from app.models.assignment import CourseAssignment, Assignment
from app.models.study_material import StudyMaterial, Note
from app.models.assignment_submission import AssignmentSubmission

__all__ = [
    "User",
    "Department",
    "Student",
    "Faculty",
    "Course",
    "CourseOffering",
    "Enrollment",
    "FaceProfile",
    "AttendanceSession",
    "AttendanceRecord",
    "TimetableEntry",
    "FacultyAdjustment",
    "Batch",
    "SystemSetting",
    "ActivityLog",
    "Examination",
    "AcademicResult",
    "AcademicDocument",
    "Assessment",
    "ResultSubmission",
    "ResultCorrection",
    "CourseAssignment",
    "Assignment",
    "StudyMaterial",
    "Note",
    "AssignmentSubmission",
]
