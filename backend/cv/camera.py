import cv2

from cv.config import CAMERA_INDEX


def open_camera():
    camera = cv2.VideoCapture(CAMERA_INDEX)

    if not camera.isOpened():
        raise RuntimeError(
            "Unable to open camera"
        )

    return camera


def read_frame(camera):
    success, frame = camera.read()

    if not success:
        raise RuntimeError(
            "Unable to read frame from camera"
        )

    return frame


def release_camera(camera):
    camera.release()
    cv2.destroyAllWindows()