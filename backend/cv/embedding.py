from deepface import DeepFace

MODEL_NAME = "Facenet512"
DETECTOR_BACKEND = "retinaface"


def generate_embedding(face_image):
    faces = DeepFace.extract_faces(
        img_path=face_image,
        detector_backend=DETECTOR_BACKEND,
        enforce_detection=True,
        align=False,
    )

    if len(faces) != 1:
        raise ValueError(
            f"Exactly one face must be detected, found {len(faces)}"
        )

    face_crop = faces[0]["face"]

    result = DeepFace.represent(
        img_path=face_crop,
        model_name=MODEL_NAME,
        detector_backend="skip",
        enforce_detection=False,
        align=False,
    )

    if not result:
        raise ValueError("No face embedding was generated")

    embedding = result[0]["embedding"]

    if len(embedding) != 512:
        raise ValueError(
            f"Unexpected embedding dimensions: {len(embedding)}"
        )

    return embedding


if __name__ == "__main__":
    import os
    import sys
    from pathlib import Path

    # Set UTF-8 encoding on Windows console if needed
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    print(f"DeepFace Embedding Generator (Model: {MODEL_NAME}, Detector: {DETECTOR_BACKEND})")

    # Determine test image path
    default_img = Path(__file__).resolve().parents[2] / "tests" / "cv" / "images" / "person_a_1.jpg"
    test_image = sys.argv[1] if len(sys.argv) > 1 else str(default_img)

    if not os.path.exists(test_image):
        print(f"Error: Face image not found at: {test_image}")
        print("Usage: python embedding.py <path_to_face_image>")
        sys.exit(1)

    print(f"Loading image: {test_image}")
    try:
        embedding = generate_embedding(test_image)
        print("\n✅ Embedding generated successfully!")
        print(f"Embedding length (dimensions): {len(embedding)}")
        print(f"Sample values (first 5): {embedding[:5]}")
    except Exception as exc:
        print(f"\n❌ Error generating embedding: {exc}")
