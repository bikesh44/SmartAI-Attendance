import unittest
from unittest.mock import MagicMock
import numpy as np
from app.services.face_service import FaceService

class TestFaceEnrollment(unittest.TestCase):
    def setUp(self):
        self.service = FaceService.__new__(FaceService)
        self.image = np.zeros((100,100,3), dtype=np.uint8)
        self.encoding = np.zeros((1,128), dtype= np.float32)

        self.service.detector = MagicMock()
        self.service.detector.detect.return_value = (
            None, 
            np.array(
                [[
                    10, 10, 50, 50,
                    20, 20,
                    40, 20,
                    30, 30,
                    20, 40,
                    40, 40,
                    0.99,

                ]],
                dtype = np.float32,
            ),
        )
        self.service.extract_face = MagicMock(return_value=self.image)
        self.service.generate_encoding = MagicMock(return_value = self.encoding)

    def test_successful_enrollment(self):
        result = self.service.enroll_student(self.image)
        self.assertEqual(result["status"], "enrolled")
        np.testing.assert_array_equal(result["encoding"], self.encoding)

    def test_invalid_image_none(self):
        result = self.service.enroll_student(None)
        self.assertEqual(result["status"], "invalid_image")
        self.assertIsNone(result["encoding"])

    def test_invalid_empty_image(self):
        empty_image = np.array([], dtype=np.uint8)
        result = self.service.enroll_student(empty_image)
        self.assertEqual(result["status"], "invalid_image")
        self.assertIsNone(result["encoding"])

    def test_no_face_detected(self):
        self.service.detector.detect.return_value = (None, None)
        result = self.service.enroll_student(self.image)
        self.assertEqual(result["status"],"no_face")
        self.assertIsNone(result["encoding"])

    def test_multiple_faces_detected(self):
        self.service.detector.detect.return_value = (
            None,
            np.array(
                [
                    [
                        10, 10, 50, 50,
                        20, 20, 40, 20, 30, 30, 20, 40, 40, 40,
                        0.99,
                    ],
                    [
                        60, 60, 50, 50,
                        70, 70, 90, 70, 80, 80, 70, 90, 90, 90,
                        0.98,
                    ],
                ],
                dtype=np.float32,
            ),
        )
        result = self.service.enroll_student(self.image)
        self.assertEqual(result["status"], "multiple_faces")
        self.assertIsNone(result["encoding"])

    def test_encoding_failure(self):
        self.service.generate_encoding.side_effect = ValueError("Encoding failed")
        result = self.service.enroll_student(self.image)
        self.assertEqual(result["status"], "encoding_failed")
        self.assertIsNone(result["encoding"])

    def test_invalid_encoding_size(self):
        self.service.generate_encoding.return_value = np.zeros(
            (1,64), dtype=np.float32
        )
        result = self.service.enroll_student(self.image)
        self.assertEqual(result["status"], "invalid_encoding")
        self.assertIsNone(result["encoding"])

    def test_invalid_encoding_shape(self):
        self.service.generate_encoding.return_value = np.zeros(
            (128,), dtype=np.float32)
        result = self.service.enroll_student(self.image)
        self.assertEqual(result["status"], "invalid_encoding")
        self.assertIsNone(result["encoding"])

    def  test_invalid_encoding_dtype(self):
        self.service.generate_encoding.return_value = np.zeros(
            (1,128), dtype = np.float64
        )
        result = self.service.enroll_student(self.image)
        self.assertEqual(result["status"], "invalid_encoding")
        self.assertIsNone(result["encoding"])

    def test_encoding_with_non_finite_values(self):
        encoding = np.zeros((1,128), dtype = np.float32)
        encoding[0,0] = np.nan 
        self.service.generate_encoding.return_value = encoding 
        result = self.service.enroll_student(self.image)
        self.assertEqual(result["status"], "invalid_encoding")
        self.assertIsNone(result["encoding"])

if __name__ == "__main__":
    unittest.main()