from pathlib import Path
import unittest
from unittest.mock import MagicMock
import cv2
from app.services.face_service import FaceService

IMAGE_DIR = Path(__file__).parent / "images"
SIMILARITY_THRESHOLD = 0.54

REQUIRED_KEYS = {
    "student_id",
    "matched",
    "similarity_score",
    "status",
}


def load_image(image_path):
    """Load an image and ensure it is valid."""
    image = cv2.imread(str(image_path))

    if image is None:
        raise ValueError(f"Could not load image: {image_path}")

    return image


def get_encoding(service, image_path):
    """Generate a face encoding from an image containing exactly one face."""
    image = load_image(image_path)

    height, width = image.shape[:2]
    service.detector.setInputSize((width, height))

    _, faces = service.detector.detect(image)

    if faces is None or len(faces) != 1:
        raise ValueError(
            f"Expected exactly one face in {image_path}, "
            f"but found {0 if faces is None else len(faces)}."
        )

    aligned_face = service.extract_face(image, faces[0])

    return service.generate_encoding(aligned_face)


def assert_result_contract(result):
    """Verify that every recognition result follows the contract."""
    assert REQUIRED_KEYS.issubset(result.keys())


def get_registered_students(service):
    """Create registered student data used by recognition tests."""
    person_a_1 = IMAGE_DIR / "person_a_1.jpg"
    person_b_1 = IMAGE_DIR / "person_b_1.jpeg"

    return [
        {
            "student_id": "STU001",
            "encoding": get_encoding(service, person_a_1),
        },
        {
            "student_id": "STU002",
            "encoding": get_encoding(service, person_b_1),
        },
    ]

class TestFaceRecognition(unittest.TestCase):
    def test_student_a_recognized(self):
        service = FaceService()
        registered_students = get_registered_students(service)
        image = load_image(IMAGE_DIR / "person_a_2.jpeg")
        result = service.recognize_student(
            image,
            registered_students,
            SIMILARITY_THRESHOLD,
        )
        self.assertTrue(REQUIRED_KEYS.issubset(result.keys()))
        self.assertIs(result["matched"], True)
        self.assertEqual(result["student_id"], "STU001")
        self.assertEqual(result["status"], "recognized")


    def test_student_b_recognized(self):
        service = FaceService()
        registered_students = get_registered_students(service)
        image = load_image(IMAGE_DIR / "person_b_2.jpeg")
        result = service.recognize_student(
            image,
            registered_students,
            SIMILARITY_THRESHOLD,
        )
        self.assertTrue(REQUIRED_KEYS.issubset(result.keys()))
        self.assertIs(result["matched"], True)
        self.assertEqual(result["student_id"], "STU002")
        self.assertEqual(result["status"], "recognized")


    def test_unknown_student(self):
        service = FaceService()
        registered_students = get_registered_students(service)
        image = load_image(IMAGE_DIR / "person_c_1.jpeg")
        result = service.recognize_student(
            image,
            registered_students,
            SIMILARITY_THRESHOLD,
        )
        self.assertTrue(REQUIRED_KEYS.issubset(result.keys()))
        self.assertIs(result["matched"], False)
        self.assertIs(result["student_id"], None)
        self.assertEqual(result["status"], "not_recognized")


    def test_no_face(self):
        service = FaceService()
        registered_students = get_registered_students(service)
        image = load_image(IMAGE_DIR / "no_face.jpg")
        result = service.recognize_student(
            image,
            registered_students,
            SIMILARITY_THRESHOLD,
        )
        self.assertTrue(REQUIRED_KEYS.issubset(result.keys()))
        self.assertIs(result["matched"], False)
        self.assertIs(result["student_id"], None)
        self.assertEqual(result["status"], "no_face")


    def test_multiple_faces(self):
        service = FaceService()
        registered_students = get_registered_students(service)
        image = load_image(IMAGE_DIR / "multiple_faces.jpg")
        result = service.recognize_student(
            image,
            registered_students,
            SIMILARITY_THRESHOLD,
        )
        self.assertTrue(REQUIRED_KEYS.issubset(result.keys()))
        self.assertIs(result["matched"], False)
        self.assertIs(result["student_id"], None)
        self.assertEqual(result["status"], "multiple_faces")


    def test_no_registered_students(self):
        service = FaceService()
        image = load_image(IMAGE_DIR / "person_a_2.jpeg")
        result = service.recognize_student(
            image,
            [],
            SIMILARITY_THRESHOLD,
        )
        self.assertTrue(REQUIRED_KEYS.issubset(result.keys()))
        self.assertIs(result["matched"], False)
        self.assertIs(result["student_id"], None)
        self.assertIs(result["similarity_score"], None)
        self.assertEqual(result["status"], "no_registered_students")


    def test_invalid_registered_encoding(self):
        service = FaceService()
        image = load_image(IMAGE_DIR / "person_a_2.jpeg")
        registered_students = [
            {
                "student_id": "STU001",
                "encoding": None,
            }
        ]
        result = service.recognize_student(
            image,
            registered_students,
            SIMILARITY_THRESHOLD,
        )
        self.assertTrue(REQUIRED_KEYS.issubset(result.keys()))
        self.assertIs(result["matched"], False)
        self.assertIs(result["student_id"], None)
        self.assertIs(result["similarity_score"], None)
        self.assertEqual(result["status"], "no_valid_registered_encoding")


    def test_missing_student_id_is_skipped(self):
        service = FaceService()
        encoding_a = get_encoding(
            service,
            IMAGE_DIR / "person_a_1.jpg",
        )
        image = load_image(IMAGE_DIR / "person_a_2.jpeg")
        registered_students = [
            {
                "student_id": None,
                "encoding": encoding_a,
            }
        ]
        result = service.recognize_student(
            image,
            registered_students,
            SIMILARITY_THRESHOLD,
        )
        self.assertTrue(REQUIRED_KEYS.issubset(result.keys()))
        self.assertIs(result["matched"], False)
        self.assertIs(result["student_id"], None)
        self.assertEqual(result["status"], "no_valid_registered_encoding")


    def test_mixed_valid_and_invalid_students(self):
        service = FaceService()
        encoding_a = get_encoding(
            service,
            IMAGE_DIR / "person_a_1.jpg",
        )
        encoding_b = get_encoding(
            service,
            IMAGE_DIR / "person_b_1.jpeg",
        )
        image = load_image(
            IMAGE_DIR / "person_a_2.jpeg"
        )
        registered_students = [
            {
                "student_id": None,
                "encoding": encoding_a,
            },
            {
                "student_id": "STU001",
                "encoding": encoding_a,
            },
            {
                "student_id": "STU002",
                "encoding": None,
            },
            {
                "student_id": "STU003",
                "encoding": encoding_b,
            },
        ]
        result = service.recognize_student(
            image,
            registered_students,
            SIMILARITY_THRESHOLD,
        )
        self.assertTrue(REQUIRED_KEYS.issubset(result.keys()))
        self.assertIs(result["matched"], True)
        self.assertEqual(result["student_id"], "STU001")
        self.assertEqual(result["status"], "recognized")

    @staticmethod
    def create_mock_service(similarity):
        """
        Create a controlled FaceService instance for
        deterministic threshold boundary testing.
        """
        service = FaceService()
        service.detector = MagicMock()
        service.detector.detect.return_value = (
            None,
            [MagicMock()],
        )
        service.extract_face = MagicMock(
        return_value=MagicMock()
        )
        service.generate_encoding = MagicMock(
        return_value=MagicMock()
        )
        service.compare_encoding = MagicMock(
            return_value={
                "cosine_similarity": similarity,
                "l2_distance": 0.0,
            }
        )
        return service


    def test_threshold_exactly_equal_is_recognized(self):
        service = self.create_mock_service(0.54)
        image = load_image(
            IMAGE_DIR / "person_a_2.jpeg"
        )
        registered_students = [
            {
                "student_id": "STU001",
                "encoding": MagicMock(),
            }
        ]
        result = service.recognize_student(
            image,
            registered_students,
            0.54,
        )
        self.assertTrue(REQUIRED_KEYS.issubset(result.keys()))
        self.assertIs(result["matched"], True)
        self.assertEqual(result["student_id"], "STU001")
        self.assertEqual(result["similarity_score"], 0.54)
        self.assertEqual(result["status"], "recognized")


    def test_threshold_below_boundary_is_not_recognized(self):
        service = self.create_mock_service(0.5399)
        image = load_image(
            IMAGE_DIR / "person_a_2.jpeg"
        )
        registered_students = [
            {
                "student_id": "STU001",
                "encoding": MagicMock(),
            }
        ]
        result = service.recognize_student(
            image,
            registered_students,
            0.54,
        )
        self.assertTrue(REQUIRED_KEYS.issubset(result.keys()))
        self.assertIs(result["matched"], False)
        self.assertIs(result["student_id"], None)
        self.assertEqual(result["similarity_score"], 0.5399)
        self.assertEqual(result["status"], "not_recognized")