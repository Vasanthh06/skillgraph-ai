"""Final ranking layer: blends candidate sources into one explainable list. Pure Python.

Rule score is always present. Model scores (two-tower / sasrec) are used only when supplied, so the system
degrades to rules when models are untrained. Each result records which signals contributed.
"""
from __future__ import annotations

DEFAULT_BLEND = {"rules": 0.6, "two_tower": 0.2, "sasrec": 0.2}


def blend(candidates: list[str], rules: dict[str, float], two_tower: dict[str, float] | None = None,
          sasrec: dict[str, float] | None = None, weights: dict[str, float] | None = None, eligible: set[str] | None = None) -> list[dict]:
    w = dict(weights or DEFAULT_BLEND)
    signals = {"rules": rules, "two_tower": two_tower or {}, "sasrec": sasrec or {}}
    active = {k: v for k, v in signals.items() if v}
    total_w = sum(w[k] for k in active) or 1.0
    out = []
    for c in candidates:
        if eligible is not None and c not in eligible:
            continue  # models can never recommend a skill whose prerequisites aren't met
        parts = {k: _norm(v, c) for k, v in active.items()}
        score = sum(w[k] * parts[k] for k in parts) / total_w
        out.append({"id": c, "score": round(score, 4), "signals": parts})
    out.sort(key=lambda r: (-r["score"], r["id"]))
    return out


def _norm(scores: dict[str, float], key: str) -> float:
    hi = max(scores.values()) if scores else 0.0
    return (scores.get(key, 0.0) / hi) if hi > 0 else 0.0
