from __future__ import annotations

import math

from engine.shared.exceptions import RAGEmbeddingError


def validate_embeddings(
    vectors: list[list[float]],
    *,
    expected_count: int,
    expected_dimensions: int,
) -> None:
    if len(vectors) != expected_count:
        raise RAGEmbeddingError(
            f"Expected {expected_count} vectors, got {len(vectors)}",
            details={"expected": expected_count, "got": len(vectors)},
        )

    for i, vec in enumerate(vectors):
        if len(vec) != expected_dimensions:
            raise RAGEmbeddingError(
                f"Vector {i} has {len(vec)} dimensions, expected {expected_dimensions}",
                details={"index": i, "dims": len(vec), "expected": expected_dimensions},
            )

        for j, val in enumerate(vec):
            if math.isnan(val) or math.isinf(val):
                raise RAGEmbeddingError(
                    f"Vector {i} contains NaN/Inf at position {j}",
                    details={"index": i, "position": j},
                )


def validate_single_embedding(
    vector: list[float],
    *,
    expected_dimensions: int,
) -> None:
    validate_embeddings(
        [vector],
        expected_count=1,
        expected_dimensions=expected_dimensions,
    )
