from cv.embedding import generate_embedding
from app.services.cv.recognition_service import (
    DEFAULT_THRESHOLD,
    find_matching_student,
)


def recognize_face(face_image, threshold=DEFAULT_THRESHOLD):
    """
    Generate an embedding for a detected face image
    and find the best matching registered student.
    """

    embedding = generate_embedding(face_image)

    student_id, confidence = find_matching_student(
        embedding,
        threshold=threshold,
    )

    return student_id, confidence