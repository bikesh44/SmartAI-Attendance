import json

import numpy as np


def serialize_embedding(embedding):
    """
    Convert a face embedding into bytes for database storage.
    """
    try:
        array = np.asarray(embedding, dtype=np.float32)
    except (TypeError, ValueError):
        raise ValueError("Face embedding must contain numeric values")

    if array.ndim != 1:
        raise ValueError(
            "Face embedding must be a 1-dimensional vector"
        )

    if array.size == 0:
        raise ValueError(
            "Face embedding cannot be empty"
        )

    if not np.isfinite(array).all():
        raise ValueError("Face embedding must contain only finite values")

    return json.dumps(
        array.tolist(),
        allow_nan=False,
    ).encode("utf-8")


def deserialize_embedding(embedding_bytes):
    """
    Convert stored bytes back into a NumPy embedding.
    """
    if not embedding_bytes:
        raise ValueError(
            "Stored face embedding is empty"
        )

    values = json.loads(
        embedding_bytes.decode("utf-8")
    )

    return np.asarray(
        values,
        dtype=np.float32,
    )


def cosine_similarity(embedding_a, embedding_b):
    """
    Calculate cosine similarity between two embeddings.
    """

    a = np.asarray(
        embedding_a,
        dtype=np.float32,
    )

    b = np.asarray(
        embedding_b,
        dtype=np.float32,
    )

    if a.ndim != 1 or b.ndim != 1:
        raise ValueError(
            "Embeddings must be 1-dimensional"
        )

    if a.shape != b.shape:
        raise ValueError(
            "Embedding dimensions do not match"
        )

    a_norm = np.linalg.norm(a)
    b_norm = np.linalg.norm(b)

    if a_norm == 0 or b_norm == 0:
        raise ValueError(
            "Cannot compare zero-vector embeddings"
        )

    return float(
        np.dot(a, b)
        / (a_norm * b_norm)
    )
