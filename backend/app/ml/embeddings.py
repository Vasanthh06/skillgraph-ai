"""Embedding backends behind one interface.

HashingEmbedder: dependency-free character n-gram vectors. Lexical similarity, NOT true semantics, but it
works offline (DEMO_MODE) and handles typos/variants ("reactjs" ~ "react").
SentenceTransformerEmbedder: real semantic embeddings, used automatically when sentence-transformers is installed.
"""
from __future__ import annotations

import hashlib
import math
import re
from typing import Protocol


class Embedder(Protocol):
    name: str
    dim: int

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class HashingEmbedder:
    name = "hashing-char-ngrams-v1"

    def __init__(self, dim: int = 512, ngram: tuple[int, ...] = (3, 4)):
        self.dim, self.ngram = dim, ngram

    def _grams(self, text: str):
        t = re.sub(r"[^a-z0-9+#]+", " ", text.lower())
        for word in t.split():
            padded = f" {word} "
            for n in self.ngram:
                for i in range(max(1, len(padded) - n + 1)):
                    yield padded[i:i + n]
            yield "w:" + word

    def embed(self, texts: list[str]) -> list[list[float]]:
        out = []
        for text in texts:
            v = [0.0] * self.dim
            for g in self._grams(text):
                h = int.from_bytes(hashlib.blake2b(g.encode(), digest_size=8).digest(), "big")
                v[h % self.dim] += 1.0 if (h >> 63) & 1 else -1.0
            norm = math.sqrt(sum(x * x for x in v)) or 1.0
            out.append([x / norm for x in v])
        return out


class SentenceTransformerEmbedder:  # pragma: no cover - needs optional dependency + model download
    def __init__(self, model: str = "sentence-transformers/all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer

        self._m = SentenceTransformer(model)
        self.name, self.dim = model, self._m.get_sentence_embedding_dimension()

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [list(map(float, v)) for v in self._m.encode(texts, normalize_embeddings=True)]


def get_embedder(prefer_semantic: bool = False) -> Embedder:
    if prefer_semantic:
        try:
            return SentenceTransformerEmbedder()
        except Exception:
            pass  # fall through to the offline embedder
    return HashingEmbedder()
