from cv.embedding import generate_embedding
from app import create_app
from app.services.cv.recognition_service import find_matching_student


IMAGE_PATH = r"..\tests\cv\images\person_a_2.jpeg"


def main():
    print("Generating query embedding...")

    query_embedding = generate_embedding(IMAGE_PATH)

    print("Query embedding dimensions:", len(query_embedding))

    app = create_app()

    with app.app_context():
        student_id, score = find_matching_student(query_embedding)

        print("Matched student ID:", student_id)
        print("Similarity score:", score)

        if student_id is not None:
            print("FACE RECOGNITION: MATCH")
        else:
            print("FACE RECOGNITION: NO MATCH")


if __name__ == "__main__":
    main()