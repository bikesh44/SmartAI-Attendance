from app.models import FaceProfile
from app.services.cv.face_service import (
    deserialize_embedding,
    cosine_similarity,
)


DEFAULT_THRESHOLD = 0.62


def find_matching_student(
    query_embedding,
    threshold=DEFAULT_THRESHOLD,
):
    """
    Compare a query face embedding against all active
    student face profiles and return the best match.
    """

    profiles = FaceProfile.query.filter_by(
        is_active=True
    ).all()

    best_student_id = None
    best_score = -1.0

    for profile in profiles:
        try:
            stored_embedding = deserialize_embedding(
                profile.embedding
            )

            score = cosine_similarity(
                query_embedding,
                stored_embedding,
            )

        except (ValueError, TypeError, UnicodeDecodeError):
            continue

        if score > best_score:
            best_score = score
            best_student_id = profile.student_id

    if (
        best_student_id is None
        or best_score < threshold
    ):
        return None, best_score

    return best_student_id, best_score