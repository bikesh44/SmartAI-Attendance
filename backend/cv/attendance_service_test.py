from cv.embedding import generate_embedding

from app import create_app
from app.services.cv.recognition_service import find_matching_student
from app.services.cv.attendance_service import mark_face_attendance


IMAGE_PATH = r"..\tests\cv\images\person_a_2.jpeg"
SESSION_ID = 1


def main():
    print("Generating face embedding...")

    embedding = generate_embedding(IMAGE_PATH)

    print("Embedding dimensions:", len(embedding))

    app = create_app()

    with app.app_context():
        student_id, confidence = find_matching_student(
            embedding
        )

        print("Recognized student:", student_id)
        print("Confidence:", confidence)

        if student_id is None:
            print("No matching student found.")
            return

        record, message = mark_face_attendance(
            session_id=SESSION_ID,
            student_id=student_id,
            confidence_score=confidence,
        )

        print("Message:", message)

        if record:
            print("Attendance ID:", record.attendance_id)
            print("Student ID:", record.student_id)
            print("Session ID:", record.session_id)
            print("Status:", record.status)
            print("Confidence:", record.confidence_score)
            print("Method:", record.recognition_method)


if __name__ == "__main__":
    main()