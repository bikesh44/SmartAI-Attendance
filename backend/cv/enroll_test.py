from cv.embedding import generate_embedding

from app import create_app
from app.extensions import db
from app.models import FaceProfile
from app.services.cv.face_service import serialize_embedding


IMAGE_PATH = r"..\tests\cv\images\person_a_1.jpg"
STUDENT_ID = 1
MODEL_VERSION = "Facenet512"


def main():
    print("Generating face embedding...")

    embedding = generate_embedding(IMAGE_PATH)

    print("Embedding dimensions:", len(embedding))

    app = create_app()

    with app.app_context():
        existing = FaceProfile.query.filter_by(
            student_id=STUDENT_ID,
            is_active=True
        ).first()

        if existing:
            existing.embedding = serialize_embedding(embedding)
            existing.model_version = MODEL_VERSION
            db.session.commit()

            print("Existing face profile updated.")
            print("Face ID:", existing.face_id)
        else:
            profile = FaceProfile(
                student_id=STUDENT_ID,
                embedding=serialize_embedding(embedding),
                model_version=MODEL_VERSION,
                is_active=True,
            )

            db.session.add(profile)
            db.session.commit()

            print("Face profile created.")
            print("Face ID:", profile.face_id)


if __name__ == "__main__":
    main()