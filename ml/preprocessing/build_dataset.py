"""Turn the user_activity log into training data. Pure Python.

Sequences are per-user ordered lists of skill slugs the user searched/viewed/completed. A user needs at least
`min_len` events to yield a training example. With no real activity this returns nothing, and that is correct:
we do not synthesise interactions.
"""
from __future__ import annotations

SKILL_EVENTS = {"skill_search", "skill_view", "roadmap_completed", "resource_completed"}


def sequences(events: list[dict], min_len: int = 3) -> dict[int, list[str]]:
    """events: [{user_id, event_type, meta:{skill}, id}] in any order."""
    by_user: dict[int, list[tuple[int, str]]] = {}
    for e in events:
        s = (e.get("meta") or {}).get("skill")
        if e.get("event_type") in SKILL_EVENTS and s:
            by_user.setdefault(e["user_id"], []).append((e["id"], s))
    out = {}
    for u, rows in by_user.items():
        seq = [s for _, s in sorted(rows)]
        dedup = [s for i, s in enumerate(seq) if i == 0 or s != seq[i - 1]]
        if len(dedup) >= min_len:
            out[u] = dedup
    return out


def next_item_examples(seqs: dict[int, list[str]], max_len: int = 20) -> list[tuple[list[str], str]]:
    """(history, next) pairs for next-skill prediction."""
    ex = []
    for seq in seqs.values():
        for i in range(1, len(seq)):
            ex.append((seq[max(0, i - max_len):i], seq[i]))
    return ex


def user_skill_pairs(scores_by_user: dict[int, dict[str, float]], threshold: float = 20.0) -> list[tuple[int, str]]:
    """Positive (user, skill) interactions for the two-tower model: skills the user has meaningfully engaged with."""
    return [(u, s) for u, sc in scores_by_user.items() for s, v in sc.items() if v >= threshold]
