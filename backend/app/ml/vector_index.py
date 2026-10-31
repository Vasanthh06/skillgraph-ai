"""Vector index: FAISS when installed, exact brute force otherwise. Same interface, same results."""
from __future__ import annotations


class BruteForceIndex:
    backend = "bruteforce"

    def __init__(self, dim: int):
        self.dim, self.ids, self.vecs = dim, [], []

    def add(self, ids: list[str], vectors: list[list[float]]) -> None:
        self.ids.extend(ids)
        self.vecs.extend(vectors)

    def search(self, query: list[float], k: int = 5) -> list[tuple[str, float]]:
        scored = [(i, sum(a * b for a, b in zip(query, v))) for i, v in zip(self.ids, self.vecs)]
        scored.sort(key=lambda t: -t[1])
        return scored[:k]


class FaissIndex:  # pragma: no cover - needs optional dependency
    backend = "faiss"

    def __init__(self, dim: int):
        import faiss
        import numpy as np

        self._faiss, self._np = faiss, np
        self.dim, self.ids = dim, []
        self._index = faiss.IndexFlatIP(dim)  # vectors are L2-normalised, so inner product == cosine

    def add(self, ids, vectors):
        self.ids.extend(ids)
        self._index.add(self._np.asarray(vectors, dtype="float32"))

    def search(self, query, k=5):
        d, i = self._index.search(self._np.asarray([query], dtype="float32"), min(k, len(self.ids)))
        return [(self.ids[j], float(s)) for s, j in zip(d[0], i[0]) if j >= 0]


def make_index(dim: int):
    try:
        return FaissIndex(dim)
    except Exception:
        return BruteForceIndex(dim)
