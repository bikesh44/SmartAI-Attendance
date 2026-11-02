
import time

import cv2
import numpy as np

from cv.config import CAMERA_INDEX
from app import create_app
from app.models import FaceProfile
from app.services.face_service import FaceService
from app.services.cv.attendance_service import (
    get_active_session,
    mark_face_attendance,
)

FACULTY_ID = 1
RECOGNITION_INTERVAL = 1.5
SIMILARITY_THRESHOLD = 0.54


def main():
    app = create_app()
    face_service = FaceService()

    with app.app_context():
        active_session = get_active_session(FACULTY_ID)

        if not active_session:
            print("No active attendance session found.")
            return

        session_id = active_session.session_id

        profiles = FaceProfile.query.filter_by(
            is_active=True,
            model_version="sface_2021dec",
        ).all()

        registered_students = []

        for profile in profiles:
            encoding = np.frombuffer(
                profile.embedding,
                dtype=np.float32,
            )

            if (
                encoding.shape != (128,)
                or not np.isfinite(encoding).all()
            ):
                continue

            registered_students.append({
                "student_id": profile.student_id,
                "encoding": encoding.reshape(1, 128),
            })

        print(f"Active session: {session_id}")
        print(f"Registered SFace profiles: {len(registered_students)}")

    if not registered_students:
        print("No valid SFace profiles found. Enroll a face first.")
        return

    camera = cv2.VideoCapture(CAMERA_INDEX)

    if not camera.isOpened():
        raise RuntimeError("Unable to open camera.")

    last_recognition_time = 0.0
    display_text = "Waiting for face..."

    try:
        while True:
            success, frame = camera.read()

            if not success:
                print("Unable to read camera frame.")
                break

            current_time = time.time()

            if current_time - last_recognition_time >= RECOGNITION_INTERVAL:
                last_recognition_time = current_time

                try:
                    with app.app_context():
                        result = face_service.recognize_student(
                            frame,
                            registered_students,
                            SIMILARITY_THRESHOLD,
                        )

                        if result["status"] == "recognized":
                            student_id = result["student_id"]
                            confidence = result["similarity_score"]

                            record, message = mark_face_attendance(
                                session_id=session_id,
                                student_id=student_id,
                                confidence_score=confidence,
                                faculty_id=FACULTY_ID,
                            )

                            display_text = (
                                f"Student {student_id}: {message}"
                            )

                            print(
                                f"Student={student_id}, "
                                f"similarity={confidence:.3f}, "
                                f"message={message}"
                            )
                        else:
                            display_text = "Face not recognized"
                            print(
                                "Recognition status:",
                                result["status"],
                                "similarity:",
                                result["similarity_score"],
                            )

                except (cv2.error, ValueError) as error:
                    display_text = "Recognition error"
                    print("Recognition error:", error)

            cv2.putText(
                frame,
                display_text[:70],
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (0, 255, 0),
                2,
            )

            cv2.putText(
                frame,
                f"Session: {session_id}",
                (20, 75),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2,
            )

            cv2.putText(
                frame,
                "Press Q to quit",
                (20, 105),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2,
            )

            cv2.imshow("SAMS-FR Live Attendance", frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    finally:
        camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
