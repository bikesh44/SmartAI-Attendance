from cv.embedding import generate_embedding
from app.services.cv.face_service import cosine_similarity


IMAGE_A = r"..\tests\cv\images\person_a_1.jpg"
IMAGE_A_2 = r"..\tests\cv\images\person_a_2.jpeg"
IMAGE_B = r"..\tests\cv\images\person_b_1.jpeg"


embedding_a = generate_embedding(IMAGE_A)
embedding_a2 = generate_embedding(IMAGE_A_2)
embedding_b = generate_embedding(IMAGE_B)


same_person_score = cosine_similarity(
    embedding_a,
    embedding_a2,
)

different_person_score = cosine_similarity(
    embedding_a,
    embedding_b,
)


print("Same-person similarity:", same_person_score)
print("Different-person similarity:", different_person_score)