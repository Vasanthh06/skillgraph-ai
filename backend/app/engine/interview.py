"""Adaptive interview practice and readiness (spec §29-31).

Scoring honesty: MCQs are exact. Open technical/scenario answers are scored by keyword coverage, which is a
self-check aid and NOT an expert grade. Coding, behavioral, HR and project answers are self-rated by the user.
"""
from __future__ import annotations

from app.engine.catalog import Catalog, Question

CATEGORIES = ["technical", "coding", "mcq", "scenario", "behavioral", "project", "hr"]
SELF_RATED = {"coding", "behavioral", "project", "hr"}
READINESS_WEIGHTS = {"technical": 0.30, "coding": 0.15, "communication": 0.15, "projects": 0.10, "resume": 0.10, "role_skills": 0.20}


def score_answer(q: Question, answer: str | None, choice: int | None, self_rating: int | None) -> tuple[float, str]:
    """Returns (score 0-100, method)."""
    if q.category == "mcq":
        return (100.0 if choice is not None and choice == q.answer_index else 0.0), "exact"
    if q.category in SELF_RATED or not q.keywords:
        r = max(1, min(5, int(self_rating or 3)))
        return float(r * 20), "self_rated"
    text = (answer or "").lower()
    words = len(text.split())
    hits = sum(1 for k in q.keywords if k.lower() in text)
    cov = min(1.0, hits / min(len(q.keywords), 4))
    score = 100.0 * cov
    if words < 15:
        score = min(score, 40.0)
    return round(score, 1), "keyword_coverage"


def select_questions(cat: Catalog, scores: dict[str, float], role_importance: dict[str, float], *, category: str | None = None,
                     focus_skills: list[str] | None = None, exclude: set[str] | None = None, n: int = 8) -> list[Question]:
    """Weakest, most role-relevant skills first (spec §30). Deterministic."""
    exclude = exclude or set()
    focus = set(focus_skills or [])
    ranked = []
    for q in cat.questions.values():
        if q.key in exclude or (category and q.category != category):
            continue
        # An explicitly focused session (a quiz on one skill, a job, a pasted JD) must never be
        # padded with questions about *other* skills: that mislabels the session and pollutes the
        # other skills' scores. Generic (skill-less) questions may still fill the mix. Returning
        # fewer than `n` questions is honest when the bank has fewer for the focus.
        if focus and q.skill is not None and q.skill not in focus:
            continue
        if q.skill is None:
            need = 0.35  # generic questions fill the mix but never outrank a real weak spot
        else:
            gap = 1.0 - min(1.0, scores.get(q.skill, 0) / 100.0)
            imp = role_importance.get(q.skill, 0.2)
            need = gap * (0.3 + 0.7 * imp)
            if focus:
                need = need + 1.0 if q.skill in focus else need * 0.2
        ranked.append((-need, q.key, q))
    ranked.sort(key=lambda t: (t[0], t[1]))
    return [q for _, _, q in ranked[:n]]


def readiness(attempts: list[dict], resume_match: float | None, role_skills_readiness: float | None) -> dict:
    """attempts: [{category, score}]. Components with no data stay None and are excluded from the overall."""
    avg = lambda cats: (sum(a["score"] for a in attempts if a["category"] in cats) / n) if (n := sum(1 for a in attempts if a["category"] in cats)) else None
    comp = {
        "technical": avg({"mcq", "technical", "scenario"}), "coding": avg({"coding"}), "communication": avg({"behavioral", "hr"}),
        "projects": avg({"project"}), "resume": resume_match, "role_skills": role_skills_readiness,
    }
    comp = {k: (None if v is None else round(v)) for k, v in comp.items()}
    practised = any(comp[k] is not None for k in ("technical", "coding", "communication", "projects"))
    if not practised:
        return {"overall": None, "components": comp, "attempts": 0}
    present = {k: v for k, v in comp.items() if v is not None}
    tw = sum(READINESS_WEIGHTS[k] for k in present)
    overall = sum(READINESS_WEIGHTS[k] * v for k, v in present.items()) / tw
    return {"overall": round(overall), "components": comp, "attempts": len(attempts)}
