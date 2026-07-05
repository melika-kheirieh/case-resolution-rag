from __future__ import annotations

from hashlib import blake2b
from math import sqrt
import re


TOKEN_RE = re.compile(r"[a-z0-9_]+")


class DeterministicEmbeddingModel:
    """Tiny local embedding model for repeatable tests and API-key-free demos."""

    dimensions = 16

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for token in TOKEN_RE.findall(text.lower()):
            digest = blake2b(token.encode("utf-8"), digest_size=4).digest()
            bucket = digest[0] % self.dimensions
            sign = 1.0 if digest[1] % 2 == 0 else -1.0
            weight = 1.0 + digest[2] / 255.0
            vector[bucket] += sign * weight

        norm = sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    return sum(left_value * right_value for left_value, right_value in zip(left, right, strict=True))
