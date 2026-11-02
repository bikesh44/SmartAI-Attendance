import sys
from pathlib import Path

# Add backend directory to sys.path so cv module can be imported when run directly
backend_dir = str(Path(__file__).resolve().parents[1])
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from cv.embedding import generate_embedding

# Robust image path that works from any working directory
image_path = str(Path(__file__).resolve().parents[2] / "tests" / "cv" / "images" / "person_a_1.jpg")

embedding = generate_embedding(
    image_path
)

print(
    "Embedding generated successfully"
)

print(
    "Embedding dimensions:",
    len(embedding)
)