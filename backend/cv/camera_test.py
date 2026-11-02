import cv2

from cv.camera import open_camera, release_camera
from cv.recognizer import FaceRecognizer


camera = open_camera()
recognizer = FaceRecognizer()

print("Camera started. Press Q to quit.")

while True:
    success, frame = camera.read()

    if not success:
        print("Failed to read camera frame")
        break

    faces = recognizer.detect_faces(frame)

    for x, y, w, h in faces:
        cv2.rectangle(
            frame,
            (x, y),
            (x + w, y + h),
            (255, 255, 255),
            2,
        )

    cv2.imshow(
        "SAMS-FR Face Detection",
        frame,
    )

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

release_camera(camera)