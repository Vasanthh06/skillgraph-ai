"""Explainable recommendations (spec §19, §43, §44) using transparent rules.

This is the rules baseline. `source` is always "rules". The Two-Tower and SASRec models in /ml replace the
candidate generation step only after they have been trained on real activity data.
"""
from __future__ import annotations

from app.engine.catalog import Catalog
from app.engine.gap import PREREQ_OK, GapResult, job_demand


def _join(names: list[str]) -> str:
    if not names:
        return ""
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def explain_skill(cat: Catalog, slug: str, gap: GapResult, scores: dict[str, float], role_name: str, intent: dict | None = None) -> dict:
    item = next(i for i in gap.items if i.slug == slug)
    known_pre = [cat.name(p) for p in cat.skills[slug].prereqs if scores.get(p, 0) >= PREREQ_OK]
    demand = job_demand(cat, role_name).get(slug)
    direct = [d for d in cat.dependents.get(slug, []) if any(i.slug == d and i.status != "strong" for i in gap.items)]
    why = (f"You already know {_join(known_pre)}." if known_pre else "It has no prerequisites you still need to learn.")
    if item.supporting and not item.unlocks:
        why_now = f"It is a prerequisite for skills on your {role_name} path."
    elif item.supporting:
        why_now = f"It is a prerequisite for skills your {role_name} path needs ({_join([cat.name(u) for u in item.unlocks[:3]])})."
    elif item.unlocks:
        why_now = f"It is the next prerequisite on your {role_name} path and unlocks {len(item.unlocks)} further skills."
    else:
        why_now = f"It is required for your {role_name} path and your prerequisites are in place."
    if demand is not None:
        impact = f"Required by {round(100 * demand)}% of the {role_name} jobs in the demo dataset."
    else:
        impact = f"Importance to {role_name}: {round(100 * item.importance)}%."
    nxt = f"After this, {_join([cat.name(d) for d in direct[:3]])} becomes available." if direct else "This completes a branch of your roadmap."
    out = {"slug": slug, "name": cat.name(slug), "what": cat.name(slug), "why": why, "why_now": why_now, "impact": impact, "next": nxt,
           "difficulty": cat.skills[slug].difficulty, "source": "rules"}
    if intent and intent.get("matches_skill") == slug:
        out["why_now"] += " It also matches what you've been exploring recently."
    return out


def next_skill(cat: Catalog, gap: GapResult, scores: dict[str, float], role_name: str, intent: dict | None = None) -> dict | None:
    candidates = [s for s in gap.order if not any(p in gap.order and scores.get(p, 0) < PREREQ_OK for p in cat.skills[s].prereqs)]
    if not candidates:
        return None
    pick = candidates[0]
    if intent and intent.get("suggested"):
        # Recent exploration may promote a skill only among the already-eligible top candidates.
        top = candidates[:3]
        for s in intent["suggested"]:
            if s in top:
                pick = s
                intent = {**intent, "matches_skill": s}
                break
    return explain_skill(cat, pick, gap, scores, role_name, intent)


def struggling(cat: Catalog, scores: dict[str, float], attempt_avgs: dict[str, tuple[float, int]], gap: GapResult) -> list[dict]:
    """Skills where the user has practised at least twice and averages under 40%: recommend prerequisite review."""
    out = []
    for slug, (avg, n) in attempt_avgs.items():
        if n >= 2 and avg < 40 and slug in cat.skills:
            weak_pre = [cat.name(p) for p in cat.skills[slug].prereqs if scores.get(p, 0) < PREREQ_OK + 20]
            out.append({"skill": cat.name(slug), "average": round(avg), "attempts": n,
                        "review_first": weak_pre,
                        "message": f"You've scored {round(avg)}% on {cat.name(slug)}. " + (f"Revisit {_join(weak_pre)} first." if weak_pre else "Repeat the learning resources, then retry.")})
    return out


def infer_intent(cat: Catalog, recent_skills: list[str], scores: dict[str, float]) -> dict | None:
    """Heuristic sequential intent (recency-weighted category vote). Stands in until SASRec has training data."""
    recent = [s for s in recent_skills if s in cat.skills][-8:]
    if len(recent) < 2:
        return None
    votes: dict[str, float] = {}
    for age, slug in enumerate(reversed(recent)):
        votes[cat.skills[slug].category] = votes.get(cat.skills[slug].category, 0) + 0.8 ** age
    top_cat, top_v = max(votes.items(), key=lambda kv: kv[1])
    in_cat = [s for s in cat.skills if cat.skills[s].category == top_cat]
    last = recent[-1]
    ahead = [d for d in cat.dependents.get(last, []) if scores.get(d, 0) < PREREQ_OK]
    ahead += [s for s in in_cat if s not in ahead and scores.get(s, 0) < PREREQ_OK and all(scores.get(p, 0) >= PREREQ_OK for p in cat.skills[s].prereqs)]
    return {"label": f"{top_cat} learning path", "confidence": round(top_v / sum(votes.values()), 2), "category": top_cat,
            "based_on": [cat.name(s) for s in recent[-5:]], "suggested": ahead[:5], "source": "heuristic"}
