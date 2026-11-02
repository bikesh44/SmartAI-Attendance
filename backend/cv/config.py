import os

API_BASE_URL = os.getenv(
    "SAMS_API_URL",
    "http://127.0.0.1:5000",
)

CAMERA_INDEX = int(
    os.getenv("CAMERA_INDEX", "0")
)

FACE_MATCH_THRESHOLD = float(
    os.getenv("FACE_MATCH_THRESHOLD", "0.60")
)