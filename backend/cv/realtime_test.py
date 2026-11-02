import cv2

from cv.embedding import generate_embedding
from cv.config import CAMERA_INDEX, FACE_MATCH_THRESHOLD
from cv.recognizer import FaceRecognizer

from app import create_app
from app.services.cv.recognition_service import find_matching_student


def main():
    app = create_app()
    recognizer = FaceRecognizer()

    camera = cv2.VideoCapture(CAMERA_INDEX)

    if not camera.isOpened():
        raise RuntimeError("Unable to open camera")

    print("========================================")
    print("SAMS-FR REAL-TIME FACE RECOGNITION")
    print("Press Q to quit")
    print("========================================")

    try:
        while True:
            success, frame = camera.read()

            if not success:
                print("Unable to read camera frame")
                break

            faces = recognizer.detect_faces(frame)

            for (x, y, w, h) in faces:
                face_image = frame[y:y + h, x:x + w]

                try:
                    embedding = generate_embedding(face_image)

                    with app.app_context():
                        student_id, confidence = find_matching_student(
                            embedding,
                            threshold=FACE_MATCH_THRESHOLD,
                        )

                    if student_id is not None:
                        label = (
                            f"Student {student_id} "
                            f"{confidence:.3f}"
                        )
                    else:
                        label = "Unknown"

                except Exception as error:
                    print("Recognition error:", error)
                    label = "Recognition error"

                cv2.rectangle(
                    frame,
                    (x, y),
                    (x + w, y + h),
                    (0, 255, 0),
                    2,
                )

                cv2.putText(
                    frame,
                    label,
                    (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 0),
                    2,
                )

            cv2.imshow(
                "SAMS-FR Face Recognition",
                frame,
            )

            key = cv2.waitKey(1) & 0xFF

            if key == ord("q"):
                break

    finally:
        camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()