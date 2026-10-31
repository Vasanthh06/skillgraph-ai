"""Next Best Action, readiness blockers and the skill-network view (spec §15, §23, §41).

Pure functions. Every output carries a reason built from the user's own evidence; nothing here invents a number.
"""
from __future__ import annotations

from app.engine import gap as G
from app.engine.catalog import Catalog, RoleSpec

READINESS_GOAL = 80
HARD_SOURCES = ("assessment", "projects", "interview")


def readiness_blockers(cat: Catalog, role: RoleSpec, scores: dict[str, float], projects_done: int, interview: float | None,
                       goal: int = READINESS_GOAL, limit: int = 4) -> dict:
    """What is preventing the user reaching `goal`? Each candidate fix is SIMULATED: we recompute readiness as if it
    were done and report the gain in points, so the list is ranked by real impact, not by guesswork."""
    base = G.overall_float(G.skills_readiness(role, scores), projects_done, interview)
    items = []
    for r in role.skills:
        if scores.get(r.slug, 0.0) >= G.TARGET:
            continue
        sim = {**scores, r.slug: float(G.TARGET)}
        gain = G.overall_float(G.skills_readiness(role, sim), projects_done, interview) - base
        if gain > 0.05:
            items.append({"kind": "skill", "slug": r.slug, "label": cat.name(r.slug), "gain": round(gain, 1), "route": f"/learn?skill={r.slug}"})
    if projects_done < G.PROJECT_TARGET:
        gain = G.overall_float(G.skills_readiness(role, scores), projects_done + 1, interview) - base
        label = "Complete your first project" if projects_done == 0 else f"Complete project {projects_done + 1} of {G.PROJECT_TARGET}"
        items.append({"kind": "project", "slug": None, "label": label, "gain": round(gain, 1), "route": "/learn"})
    unmeasured = None
    if interview is None:
        unmeasured = {"kind": "interview", "slug": None, "label": "Practise interview questions (your interview score isn't measured yet)", "gain": None, "route": "/interview"}
    elif interview < 70:
        gain = G.overall_float(G.skills_readiness(role, scores), projects_done, 80.0) - base
        if gain > 0.05:
            items.append({"kind": "interview", "slug": None, "label": "Improve your interview performance", "gain": round(gain, 1), "route": "/interview"})
    items.sort(key=lambda i: (-(i["gain"] or 0), i["label"]))
    items = items[:limit]
    if unmeasured and len(items) < limit + 1:
        items.append(unmeasured)
    return {"goal": goal, "current": G.half_up(base), "to_go": max(0, goal - G.half_up(base)), "reached": base >= goal, "blockers": items}


def next_best_action(cat: Catalog, *, needs: str | None, role: RoleSpec | None, gap: G.GapResult | None, scores: dict[str, float],
                     estimates: dict, declared_done: set[str], attempt_avgs: dict[str, tuple[float, int]], projects_done: int,
                     project: dict | None, attempts: int, resume_present: bool, recommended: dict | None,
                     intelligence: dict | None = None) -> dict:
    """First applicable rule wins. Each rule says WHY, from this user's data."""
    def act(kind, title, reason, route, skill=None):
        return {"type": kind, "title": title, "reason": reason, "route": route, "skill": skill, "source": "rules"}

    if needs == "target_role" or role is None:
        return act("role", "Choose your target role", "Everything else (your gaps, roadmap, jobs and interview prep) is calculated against the role you want.", "/role")
    if needs == "assessment" or gap is None:
        return act("assessment", "Tell us what you already know", f"We need evidence of your skills for {role.name} before we can show your gaps. Answer the assessment or add a resume.", "/assessment")

    in_role = {i.slug for i in gap.items}
    # 1. Struggling: practised a skill twice and still under 40% -> fix the foundation first.
    for slug, (avg, n) in sorted(attempt_avgs.items(), key=lambda kv: kv[1][0]):
        if n >= 2 and avg < 40 and slug in in_role:
            weak_pre = [p for p in cat.skills[slug].prereqs if scores.get(p, 0) < G.PREREQ_OK + 20]
            if weak_pre:
                return act("review", f"Review {cat.name(weak_pre[0])} before retrying {cat.name(slug)}",
                           f"You've averaged {round(avg)}% on {cat.name(slug)} over {n} questions, and {cat.name(weak_pre[0])} is its weakest prerequisite for you.", f"/learn?skill={weak_pre[0]}", weak_pre[0])
            return act("review", f"Revisit {cat.name(slug)}", f"You've averaged {round(avg)}% on {cat.name(slug)} over {n} questions. Repeat the learning, then retry.", f"/learn?skill={slug}", slug)

    # 2. Verify: you declared it done, but nothing proves it. A quiz turns a claim into evidence.
    has_quiz = {q.skill for q in cat.questions.values() if q.category == "mcq" and q.skill}
    unverified = [i for i in gap.items if i.slug in declared_done and i.slug in has_quiz
                  and not any(k in (estimates.get(i.slug).sources if estimates.get(i.slug) else {}) for k in HARD_SOURCES)]
    if unverified:
        top = max(unverified, key=lambda i: i.importance)
        return act("verify", f"Verify {top.name} with a quiz", f"You marked {top.name} as done, but nothing proves it yet. A short quiz turns a claim into evidence and updates your readiness.", "/interview", top.slug)

    # 2b. A due recall check is a short, high-value step. It never reopens the finished milestone.
    due = (intelligence or {}).get("due_reviews") or []
    if due:
        top = due[0]
        topics = f" Revisit {top['weak_topics'][0]} if it comes up." if top.get("weak_topics") else ""
        return act("recall", f"{'Check' if top.get('diagnostic') else 'Recall'} {top['name']}",
                   f"{top['status_label']}. A few questions will confirm what is still solid and set the next review date.{topics}",
                   top["action"]["route"], top["slug"])

    skills_r = G.skills_readiness(role, scores)
    # 3. First project once the basics are in place.
    if projects_done == 0 and skills_r >= 40 and project:
        return act("project", f"Build your first project: {project['title']}", project.get("why") or "A finished project is the strongest evidence you can add.", "/learn")
    # 4. Never practised interviews.
    if attempts == 0 and skills_r >= 30:
        focus = next((s for s in gap.order if s in has_quiz), None)
        if focus:
            n = len([q for q in cat.questions.values() if q.skill == focus and q.category == "mcq"])
            return act("interview", f"Practise {n} {cat.name(focus)} interview questions", f"You haven't practised interviews yet, and {cat.name(focus)} is one of your most important open skills.", "/interview", focus)
    # 5. Learn the next prerequisite-ready skill.
    if recommended:
        return act("learn", f"Learn {recommended['name']}", f"{recommended['why']} {recommended['why_now']}", f"/learn?skill={recommended['slug']}", recommended["slug"])
    # 6. Nothing left to learn: put the evidence to work.
    if not resume_present:
        return act("resume", "Add your resume", f"You've covered your {role.name} skill gaps. Add a resume so we can check how well it presents them.", "/resume")
    return act("jobs", "Find matching jobs", f"You've covered your {role.name} skill gaps. Time to see which roles you match.", "/jobs")


def skill_state(status: str, is_current: bool) -> str:
    """What the user sees for a skill: acquired (strong evidence), in_progress (partly shown, or the step they are on now), missing."""
    if status == "strong":
        return "acquired"
    if status == "weak" or is_current:
        return "in_progress"
    return "missing"


def skill_network(cat: Catalog, gap: G.GapResult, current: str | None = None, intelligence: dict | None = None) -> dict:
    """Nodes = the role's skills (plus prerequisites the user still lacks); edges run prerequisite -> dependent."""
    ids = {i.slug for i in gap.items}
    by_skill = (intelligence or {}).get("by_skill") or {}
    nodes = [{"id": i.slug, "name": i.name, "group": i.group, "score": i.score, "status": i.status, "importance": i.importance,
              "supporting": i.supporting, "current": i.slug == current, "depth": cat.depth(i.slug),
              "is_bottleneck": (by_skill.get(i.slug) or {}).get("bottleneck") is not None,
              "review_status": (((by_skill.get(i.slug) or {}).get("review") or {}).get("status")),
              "state": skill_state(i.status, i.slug == current)} for i in gap.items]
    edges = [{"source": p, "target": i.slug} for i in gap.items for p in cat.skills[i.slug].prereqs if p in ids]
    return {"nodes": nodes, "edges": sorted(edges, key=lambda e: (e["source"], e["target"]))}
