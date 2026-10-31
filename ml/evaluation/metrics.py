"""Ranking metrics. Pure Python."""
from __future__ import annotations

import math


def recall_at_k(ranked: list[str], truth: str, k: int) -> float:
    return 1.0 if truth in ranked[:k] else 0.0


def ndcg_at_k(ranked: list[str], truth: str, k: int) -> float:
    for i, r in enumerate(ranked[:k]):
        if r == truth:
            return 1.0 / math.log2(i + 2)
    return 0.0


def evaluate(predict, examples: list[tuple[list[str], str]], k: int = 5) -> dict:
    """predict(history)->ranked slugs. Returns mean recall@k / ndcg@k over held-out examples."""
    if not examples:
        return {"n": 0, f"recall@{k}": None, f"ndcg@{k}": None}
    r = n = 0.0
    for hist, truth in examples:
        ranked = predict(hist)
        r += recall_at_k(ranked, truth, k)
        n += ndcg_at_k(ranked, truth, k)
    return {"n": len(examples), f"recall@{k}": round(r / len(examples), 4), f"ndcg@{k}": round(n / len(examples), 4)}


def split_by_user(seqs: dict[int, list[str]], holdout_frac: float = 0.2):
    """Leave-last-out per user is leakage-free for sequential models: train on seq[:-1], test on the last item."""
    train = {u: s[:-1] for u, s in seqs.items() if len(s) >= 3}
    test = [(s[:-1], s[-1]) for s in seqs.values() if len(s) >= 3]
    return train, test
