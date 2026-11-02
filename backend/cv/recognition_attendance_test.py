from cv.embedding import generate_embedding

from app import create_app
from app.extensions import db
from app.models import AttendanceRecord, Enrollment
from app.services.cv.attendance_service import get_active_session
from app.services.cv.recognition_service import find_matching_student


IMAGE_PATH = r"..\tests\cv\images\person_a_2.jpeg"
FACULTY_ID = 1
THRESHOLD = 0.60


def main():
    print("Generating query embedding...")

    query_embedding = generate_embedding(IMAGE_PATH)

    print("Embedding dimensions:", len(query_embedding))

    app = create_app()

    with app.app_context():
        # 1. Find the current active attendance session
        session = get_active_session(FACULTY_ID)

        if not session:
            print("No active attendance session found.")
            return

        session_id = session.session_id

        print("Active session ID:", session_id)
        print("Offering ID:", session.offering_id)
        print("Session status:", session.status)

        # 2. Recognize the student
        student_id, confidence = find_matching_student(
            query_embedding,
            threshold=THRESHOLD,
        )

        print("Recognized student:", student_id)
        print("Confidence:", confidence)

        if student_id is None:
            print("No matching student found.")
            return

        # 3. Verify student enrollment
        enrollment = Enrollment.query.filter_by(
            student_id=student_id,
            offering_id=session.offering_id,
            status="ACTIVE",
        ).first()

        if not enrollment:
            print("Student is not enrolled in this course.")
            return

        # 4. Prevent duplicate attendance
        existing = AttendanceRecord.query.filter_by(
            session_id=session_id,
            student_id=student_id,
        ).first()

        if existing:
            print("Attendance already exists.")
            print("Attendance ID:", existing.attendance_id)
            print("Session ID:", existing.session_id)
            return

        # 5. Create attendance
        attendance = AttendanceRecord(
            session_id=session_id,
            student_id=student_id,
            status="PRESENT",
            confidence_score=confidence,
            recognition_method="FACE",
        )

        db.session.add(attendance)
        db.session.commit()

        print("================================")
        print("ATTENDANCE MARKED SUCCESSFULLY")
        print("Attendance ID:", attendance.attendance_id)
        print("Student ID:", attendance.student_id)
        print("Session ID:", attendance.session_id)
        print("Status:", attendance.status)
        print("Confidence:", attendance.confidence_score)
        print("Method:", attendance.recognition_method)
        print("================================")


if __name__ == "__main__":
    main()