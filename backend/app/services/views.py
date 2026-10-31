"""Shapes engine output into API responses. No business logic here beyond presentation."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.data.skills_data import DOCS_URLS, taxonomy_leaves
from app.engine import actions as ACT
from app.engine import gap as G
from app.engine import jobs as J
from app.engine import recommend as R
from app.models import Application, Job, UserActivity
from app.repositories.scoped import UserScope
from app.services import intelligence as intel_svc
from app.services import profile_service, youtube
from app.services.analysis import MIN_COVERAGE, Analysis

DIFFICULTY_ORDER = {"beginner": 0, "intermediate": 1, "advanced": 2}
SELF_LEVELS = [("never_used", "Never used"), ("beginner", "Beginner"), ("basic", "Basic"), ("intermediate", "Intermediate"), ("advanced", "Advanced"), ("expert", "Expert")]


def skill_json(a: Analysis, slug: str) -> dict:
    e = a.estimates.get(slug)
    return {"slug": slug, "name": a.cat.name(slug), "score": e.score if e else 0, "level": e.level if e else "none",
            "confidence": e.confidence if e else 0, "sources": e.sources if e else {}, "capped": bool(e and e.capped)}


def intel(a: Analysis) -> dict:
    return getattr(a, "intelligence", None) or {}


def skill_intel(a: Analysis, slug: str) -> dict:
    return intel_svc.skill_intelligence(a, slug)


def needs(a: Analysis) -> str | None:
    """What is missing before personalised numbers can be shown (spec §16). None = enough data."""
    if a.role is None:
        return "target_role"
    if a.coverage < MIN_COVERAGE:
        return "assessment"
    return None


def onboarding(a: Analysis) -> dict:
    """First-login checklist. Every figure is derived from this user's own stored data."""
    prof = profile_service.to_out(a.user)
    answered = a.answered_self
    if answered == 0 and not a.attempts:
        assess = "not_started"
    elif a.role_total and answered >= 0.8 * a.role_total:
        assess = "complete"
    else:
        assess = "in_progress"
    steps = [
        {"key": "profile", "label": "Profile", "status": "done" if prof.profile_complete else "todo", "detail": None if prof.profile_complete else "Still needed: " + ", ".join(f for f in prof.missing_fields if f != "Target role") or None},
        {"key": "target_role", "label": "Target role", "status": "done" if a.role else "todo", "detail": a.role.name if a.role else None},
        {"key": "knowledge", "label": "Knowledge", "status": "done" if a.coverage >= MIN_COVERAGE else "todo", "percent": round(100 * a.coverage), "detail": f"{round(100 * a.coverage)}% of {a.role.name} skills have evidence" if a.role else None},
        {"key": "resume", "label": "Resume", "status": "done" if a.resume else "optional", "detail": a.resume["filename"] if a.resume else "Optional"},
        {"key": "assessment", "label": "Assessment", "status": assess, "detail": f"{answered} of {a.role_total} skills answered" if a.role else None},
    ]
    nxt = next((x["key"] for x in steps if x["key"] in ("profile", "target_role", "knowledge") and x["status"] == "todo"), None)
    return {"steps": steps, "next": nxt, "ready": needs(a) is None, "min_coverage_percent": round(100 * MIN_COVERAGE)}


def gap_view(a: Analysis) -> dict:
    if needs(a):  # not enough of THIS user's data: return no numbers at all
        return {"needs": needs(a), "role": a.role.name if a.role else None, "onboarding": onboarding(a)}
    g = a.gap
    bottlenecks = {b["slug"]: b for b in intel(a).get("bottlenecks", [])}
    item = lambda i: {"slug": i.slug, "name": i.name, "group": i.group, "importance": i.importance, "required": i.required, "score": i.score,
                      "status": i.status, "critical": i.critical, "supporting": i.supporting, "rank": i.rank, "priority": i.priority,
                      "downstream_count": i.downstream_count, "downstream_importance": i.downstream_importance,
                      "is_bottleneck": i.slug in bottlenecks,
                      "bottleneck_score": bottlenecks[i.slug]["bottleneck_score"] if i.slug in bottlenecks else None,
                      "intelligence": skill_intel(a, i.slug),
                      "unlocks": [a.cat.name(u) for u in i.unlocks[:4]], "blocked_by": [a.cat.name(b) for b in i.blocked_by]}
    items = [item(i) for i in g.items]
    return {
        "needs": needs(a), "role": a.role.name, "role_is_generated": a.role.is_custom, "derived_from": a.role.derived_from,
        "readiness": a.readiness, "groups": g.group_readiness,
        "strong": [i for i in items if i["status"] == "strong"], "weak": [i for i in items if i["status"] == "weak"],
        "missing": [i for i in items if i["status"] == "missing"], "critical": [i for i in items if i["critical"]],
        "learn_next": [i for i in items if i["rank"]][:10], "remaining": g.remaining,
        "limited_coverage": a.role.limited_coverage,
        "bottlenecks": intel(a).get("bottlenecks", []), "intelligence": intel(a),
    }


def roadmap_view(a: Analysis) -> dict:
    from app.engine.roadmap import progress

    if needs(a):
        return {"needs": needs(a), "role": a.role.name if a.role else None, "nodes": [], "progress": None, "struggling": [], "onboarding": onboarding(a)}
    top = intel(a).get("top_bottleneck")
    current = next((n for n in a.nodes if n.status == "current"), None)
    nodes = []
    for n in a.nodes:
        si = skill_intel(a, n.slug)
        b, review = si.get("bottleneck"), si.get("review")
        if b:
            why = b["why"]
        elif n.blocked_by:
            why = f"Waiting on {', '.join(a.cat.name(x) for x in n.blocked_by)} first."
        elif n.status == "current":
            why = "This is the first unfinished step whose prerequisites are ready."
        else:
            why = None
        nodes.append({"slug": n.slug, "name": n.name, "status": n.status, "group": n.group, "score": n.score,
                      "blocked_by": [a.cat.name(x) for x in n.blocked_by], "position": n.position, "supporting": n.supporting,
                      "intelligence": si, "is_bottleneck": b is not None,
                      "bottleneck_score": b["bottleneck_score"] if b else None,
                      "review_status": review["status"] if review else None, "why_prioritized": why})
    if top and current and top["slug"] == current.slug:
        order_note = f"{top['name']} comes first because it is currently holding back {top['downstream_count']} later skill(s)."
    elif top and current and top["slug"] in a.cat.all_prereqs(current.slug):
        order_note = f"{top['name']} is the main bottleneck behind your current step, {current.name}."
    elif top:
        order_note = top["why"]
    else:
        order_note = "No single bottleneck stands out right now; the order follows prerequisites, career importance and readiness."
    return {"needs": needs(a), "role": a.role.name if a.role else None, "nodes": nodes, "progress": progress(a.nodes),
            "struggling": R.struggling(a.cat, a.scores, a.attempt_avgs, a.gap) if a.gap else [],
            "bottlenecks": intel(a).get("bottlenecks", []), "due_reviews": intel(a).get("due_reviews", []),
            "review_summary": intel(a).get("review_summary", {}), "order_explanation": order_note,
            "intelligence": intel(a)}


def resources_for_skill(a: Analysis, slug: str) -> dict:
    cat = a.cat
    name = cat.name(slug)
    mcqs = [q.key for q in cat.questions.values() if q.skill == slug and q.category == "mcq"]
    open_q = [q.key for q in cat.questions.values() if q.skill == slug and q.category != "mcq"]
    return {
        "skill": {"slug": slug, "name": name, "difficulty": cat.skills[slug].difficulty, "prerequisites": [cat.name(p) for p in cat.skills[slug].prereqs]},
        "topics": taxonomy_leaves(slug)[:14],
        "learn": {"videos": youtube.resources_for(name, slug), "docs": DOCS_URLS.get(slug)},
        "practice": {"mcq_keys": mcqs, "open_keys": open_q},
        "build": [p for p in recommended_projects(a, limit=50) if slug in p["gains"] or slug in p["requires"]][:3],
        "prove": ["Finish a project that uses it and publish the repository", "Pass the practice quiz above", "Add a certificate if you earn one"],
        "completed": slug in a.state.completed_resources or slug in a.state.completed_roadmap,
        "intelligence": skill_intel(a, slug),
    }


def application_status(db: Session, user_id: str) -> dict[str, str]:
    """job key -> this user's application status. Reads only the caller's applications (UserScope)."""
    keys = {j.id: j.key for j in db.scalars(select(Job)) if j.key}   # the job catalogue itself is global
    return {keys[x.job_id]: x.status for x in UserScope(db, user_id).all(Application) if x.job_id in keys}


def all_projects(a: Analysis) -> list[dict]:
    """Every catalogue project with this user's readiness and status. Recommended ones (they build a skill still needed) come first."""
    if needs(a):
        return []
    cat = a.cat
    rec = {p["key"]: p for p in recommended_projects(a, limit=100, include_completed=True)}
    out = []
    for p in cat.projects.values():
        lacking = [s for s in p.required if a.scores.get(s, 0) < G.WEAK]
        r = rec.get(p.key)
        out.append({"key": p.key, "title": p.title, "difficulty": p.difficulty, "hours": p.hours, "requires": list(p.required), "gains": list(p.gained),
                    "requires_names": [cat.name(s) for s in p.required], "gains_names": [cat.name(s) for s in p.gained], "description": p.description,
                    "expected_output": p.expected_output, "portfolio_value": p.portfolio_value, "ready": not lacking,
                    "missing_prerequisites": [cat.name(s) for s in lacking], "missing_slugs": lacking, "recommended": r is not None,
                    "relevance": r["relevance"] if r else 0.0, "why": r["why"] if r else "Not tied to a current gap, but a good portfolio piece.",
                    "status": a.project_status.get(p.key, "not_started"), "is_demo": True})
    order = {"beginner": 0, "intermediate": 1, "advanced": 2}
    out.sort(key=lambda p: (not p["recommended"], not p["ready"], -p["relevance"], order[p["difficulty"]]))
    return out


def roadmap_preview(a: Analysis, n: int = 4) -> list[dict]:
    """The next few unfinished roadmap steps, for the dashboard."""
    return [{"slug": x.slug, "name": x.name, "status": x.status, "score": x.score, "blocked_by": [a.cat.name(b) for b in x.blocked_by]}
            for x in a.nodes if x.status != "completed"][:n]


def recommended_projects(a: Analysis, limit: int = 6, include_completed: bool = False) -> list[dict]:
    if needs(a):
        return []
    cat, out = a.cat, []
    role_imp = {r.slug: r.importance for r in a.role.skills} if a.role else {}
    unmet = {i.slug for i in a.gap.items if i.status != "strong"} if a.gap else set()
    for p in cat.projects.values():
        if p.key in a.completed_projects and not include_completed:
            continue
        lacking = [s for s in p.required if a.scores.get(s, 0) < G.WEAK]
        useful = [s for s in p.gained if s in unmet]
        relevance = sum(role_imp.get(s, 0.3) for s in useful)
        if not useful and a.role:
            continue
        out.append({"key": p.key, "title": p.title, "difficulty": p.difficulty, "hours": p.hours, "requires": list(p.required), "gains": list(p.gained),
                    "requires_names": [cat.name(s) for s in p.required], "gains_names": [cat.name(s) for s in p.gained], "description": p.description,
                    "expected_output": p.expected_output, "portfolio_value": p.portfolio_value, "technologies": [cat.name(s) for s in p.required],
                    "ready": not lacking, "missing_prerequisites": [cat.name(s) for s in lacking], "relevance": round(relevance, 2),
                    "status": a.project_status.get(p.key, "not_started"), "is_demo": True,
                    "why": f"Builds {', '.join(cat.name(s) for s in useful[:3])}, which your {a.role.name} path still needs." if useful and a.role else "Suggested starter project."})
    out.sort(key=lambda p: (not p["ready"], -p["relevance"], DIFFICULTY_ORDER[p["difficulty"]]))
    return out[:limit]


def job_matches(a: Analysis, limit: int | None = None) -> list[dict]:
    if needs(a):
        return []
    p = a.user.profile
    return J.rank_jobs(a.cat, a.scores, a.role, p.experience_level, p.location, limit)


def _activity_text(ev: UserActivity, a: Analysis) -> str:
    m = ev.meta or {}
    nm = lambda s: a.cat.name(s) if s in a.cat.skills else s
    t = ev.event_type
    return {
        "assessment_saved": f"Updated your self-assessment ({m.get('count', 0)} skills)",
        "resume_uploaded": f"Uploaded resume {m.get('filename', '')}".strip(),
        "roadmap_completed": f"Completed {nm(m.get('skill', ''))} on your roadmap",
        "roadmap_reopened": f"Reopened {nm(m.get('skill', ''))}",
        "resource_opened": f"Opened a learning resource for {nm(m.get('skill', ''))}",
        "resource_completed": f"Finished learning resources for {nm(m.get('skill', ''))}",
        "role_changed": f"Changed target role to {m.get('role', '')}",
        "skill_search": f"Searched {nm(m.get('skill', m.get('query', '')))}",
        "skill_view": f"Opened {nm(m.get('skill', ''))}",
        "project_status": f"Marked project '{m.get('title', '')}' as {m.get('status', '').replace('_', ' ')}",
        "interview_answer": f"Practised a {m.get('category', '')} question",
        "knowledge_check": f"Checked {nm(m.get('skill', ''))} ({m.get('score', '')}%)",
        "recall_completed": f"Recalled {nm(m.get('skill', ''))} ({m.get('score', '')}%)",
        "job_viewed": f"Viewed {m.get('title', 'a job')}",
        "jd_analyzed": "Analysed a job description",
        "certification_added": f"Added certification {m.get('name', '')}",
    }.get(t, t.replace("_", " ").capitalize())


def recent_activity(db: Session, a: Analysis, n: int = 8) -> list[dict]:
    rows = UserScope(db, a.user.id).all(UserActivity, order_by=UserActivity.id.desc(), limit=n)
    return [{"text": _activity_text(r, a), "type": r.event_type, "at": r.created_at.isoformat() if r.created_at else None} for r in rows]


def skill_graph(a: Analysis) -> dict:
    """Interactive skill graph: the network plus, per skill, the evidence behind its colour and what it leads to."""
    if needs(a):
        return {"needs": needs(a), "role": a.role.name if a.role else None, "onboarding": onboarding(a)}
    nxt = R.next_skill(a.cat, a.gap, a.scores, a.role.name, a.intent)
    net = ACT.skill_network(a.cat, a.gap, current=nxt["slug"] if nxt else None, intelligence=intel(a))
    by = {i.slug: i for i in a.gap.items}
    road = {n.slug: n.status for n in a.nodes}
    has_quiz = {q.skill for q in a.cat.questions.values() if q.category == "mcq" and q.skill}
    for n in net["nodes"]:
        i, est = by[n["id"]], a.estimates.get(n["id"])
        sc = round(n["score"])
        why = {"acquired": f"Your evidence-based score is {sc}%, above the {G.STRONG:.0f}% line for a skill you have shown.",
               "in_progress": (f"This is the step you are on now. You have little evidence for it yet ({sc}%)." if n["current"] and n["status"] == "missing"
                               else f"You have shown part of it ({sc}%). It counts as acquired at {G.STRONG:.0f}%."),
               "missing": f"There is little or no evidence for this yet ({sc}%)."}[n["state"]]
        si = skill_intel(a, n["id"])
        n.update(level=est.level if est else "none", confidence=est.confidence if est else 0.0, sources=est.sources if est else {},
                 capped=bool(est and est.capped), verified=bool(est and any(k in est.sources for k in ACT.HARD_SOURCES)), required=i.required, why=why,
                 prerequisites=[{"slug": p, "name": a.cat.name(p)} for p in a.cat.skills[n["id"]].prereqs],
                 unlocks=[{"slug": u, "name": a.cat.name(u)} for u in i.unlocks[:6]], blocked_by=[a.cat.name(b) for b in i.blocked_by],
                 roadmap=road.get(n["id"]), has_quiz=n["id"] in has_quiz, intelligence=si,
                 is_bottleneck=si.get("bottleneck") is not None,
                 bottleneck_score=(si.get("bottleneck") or {}).get("bottleneck_score"),
                 calibration_status=(si.get("calibration") or {}).get("status"),
                 review_status=(si.get("review") or {}).get("status"))
    counts = {k: sum(1 for n in net["nodes"] if n["state"] == k) for k in ("acquired", "in_progress", "missing")}
    return {"needs": None, "role": a.role.name, "nodes": net["nodes"], "edges": net["edges"], "counts": counts,
            "groups": sorted({n["group"] for n in net["nodes"]}), "next_skill": nxt["slug"] if nxt else None,
            "intelligence": intel(a)}


def skill_overview(a: Analysis) -> dict:
    """Strong / developing / critical lists straight from the gap engine (the thresholds live only in the backend)."""
    items = [i for i in a.gap.items if not i.supporting]
    row = lambda i: {"slug": i.slug, "name": i.name, "score": i.score}
    crit = a.gap.critical or [i for i in items if i.status == "missing"]
    return {"strong": [row(i) for i in sorted((i for i in items if i.status == "strong"), key=lambda i: -i.score)[:5]],
            "developing": [row(i) for i in sorted((i for i in items if i.status == "weak"), key=lambda i: -i.score)[:5]],
            "critical": [row(i) for i in crit[:5] if not i.supporting]}


def journey(a: Analysis) -> list[dict]:
    """The user's progress through the career loop, from stored evidence only (no client-side guessing)."""
    prof = profile_service.to_out(a.user)
    steps = [("Profile", prof.profile_complete), ("Target role", a.role is not None), ("Skills assessed", a.coverage >= MIN_COVERAGE),
             ("Roadmap started", bool(a.state.completed_roadmap or a.state.completed_resources)), ("First project", len(a.completed_projects) > 0),
             ("Interview practised", len(a.attempts) > 0)]
    first = next((i for i, (_, ok) in enumerate(steps) if not ok), None)
    return [{"label": label, "done": ok, "next": i == first} for i, (label, ok) in enumerate(steps)]


def next_best_action(a: Analysis, nxt: dict | None = None) -> dict:
    """The single most useful next step, chosen by explicit rules from this user's own evidence (spec §15)."""
    project = (recommended_projects(a, 1) or [None])[0]
    return ACT.next_best_action(
        a.cat, needs=needs(a), role=a.role, gap=a.gap, scores=a.scores, estimates=a.estimates,
        declared_done=set(a.state.completed_roadmap) | set(a.state.completed_resources), attempt_avgs=a.attempt_avgs,
        projects_done=len(a.completed_projects), project=project, attempts=len(a.attempts), resume_present=a.resume is not None, recommended=nxt,
        intelligence=intel(a))


def dashboard(db: Session, a: Analysis) -> dict:
    p = a.user.profile
    base = {"user": {"id": a.user.id, "name": a.user.full_name, "email": a.user.email},
            "target_role": {"name": a.role.name, "description": a.role.description, "is_generated": a.role.is_custom, "derived_from": a.role.derived_from} if a.role else None,
            "needs": needs(a), "onboarding": onboarding(a), "recent_activity": recent_activity(db, a),
            "next_best_action": next_best_action(a), "journey": journey(a),
            "data_labels": {"jobs": "demo", "projects": "demo", "interview": "demo"}}
    if needs(a):  # new or sparse account: no readiness, no gaps, no fake numbers (spec §16)
        return {**base, "readiness_score": None, "current_skills": [], "critical_gaps": [], "recommended_next_skill": None,
                "roadmap_progress": None, "learning_recommendations": [], "youtube_resources": [], "project_recommendations": [],
                "job_matches": [], "interview_readiness": a.interview, "five_questions": five(a, None), "intelligence": None}
    from app.engine.roadmap import progress

    nxt = R.next_skill(a.cat, a.gap, a.scores, a.role.name, a.intent)
    jobs_status = application_status(db, a.user.id)
    top_skills = sorted((s for s in a.estimates.values() if s.score >= G.WEAK), key=lambda s: -s.score)[:8]
    role_slugs = {r.slug for r in a.role.skills}
    learn = []
    for s in [i for i in a.gap.order][:3]:
        if any(p_ in a.gap.order and a.scores.get(p_, 0) < G.PREREQ_OK for p_ in a.cat.skills[s].prereqs):
            continue
        learn.append(R.explain_skill(a.cat, s, a.gap, a.scores, a.role.name, a.intent))
    yt = youtube.resources_for(nxt["name"], nxt["slug"]) if nxt else []
    return {
        **base, "readiness_score": a.readiness["overall"], "readiness": a.readiness,
        "relevant_skill_count": len([s for s in a.estimates if s in role_slugs and a.estimates[s].score >= G.WEAK]),
        "skills_remaining": a.gap.remaining,
        "current_skills": [skill_json(a, s.slug) for s in top_skills],
        "critical_gaps": [{"slug": i.slug, "name": i.name, "score": i.score} for i in a.gap.critical][:5],
        "upcoming_gaps": [{"slug": s, "name": a.cat.name(s)} for s in a.gap.order if s not in {i.slug for i in a.gap.critical}][:4],
        "recommended_next_skill": nxt, "intent": a.intent,
        "roadmap_progress": progress(a.nodes), "learning_recommendations": learn, "youtube_resources": yt,
        "project_recommendations": recommended_projects(a, 3), "roadmap_preview": roadmap_preview(a),
        "job_matches": [{**j, "application_status": jobs_status.get(j["key"])} for j in job_matches(a, 3)],
        "interview_readiness": a.interview, "five_questions": five(a, nxt),
        "next_best_action": next_best_action(a, nxt), "journey": journey(a),
        "readiness_blockers": ACT.readiness_blockers(a.cat, a.role, a.scores, len(a.completed_projects), a.interview["overall"]),
        "skill_network": ACT.skill_network(a.cat, a.gap, current=nxt["slug"] if nxt else None, intelligence=intel(a)),
        "skill_overview": skill_overview(a),
        "intelligence": intel(a),
    }


def five(a: Analysis, nxt: dict | None) -> dict:
    """Spec §62: the five questions every user should be able to answer from the UI."""
    where = a.coverage >= MIN_COVERAGE
    return {
        "where_am_i": {"answered": where, "detail": f"{len([s for s in a.estimates.values() if s.score >= G.WEAK])} skills measured" if where else "Tell us what you know or upload a resume."},
        "where_to_go": {"answered": a.role is not None, "detail": a.role.name if a.role else "Choose a target role."},
        "what_am_i_missing": {"answered": bool(a.gap and where), "detail": f"{a.gap.remaining} skills remaining" if a.gap and where else "Needs your skills and a target role."},
        "what_next": {"answered": nxt is not None, "detail": nxt["name"] if nxt else "Available after your skill gap is calculated."},
        "am_i_ready": {"answered": bool(a.readiness and where), "detail": f"{a.readiness['overall']}% ready" if a.readiness and where else "Available after assessment."},
    }


def assessment_form(a: Analysis) -> dict:
    if a.role is None:
        return {"needs": "target_role", "groups": []}
    groups: dict[str, list] = {}
    for r in a.role.skills:
        slug = r.slug
        leaves = taxonomy_leaves(slug)
        checked = a.state.checklists.get(slug, {})
        groups.setdefault(r.group, []).append({
            "slug": slug, "name": a.cat.name(slug), "required": r.required, "importance": r.importance,
            "self_level": a.state.self_levels.get(slug),
            "confidence_rating": a.state.confidence_ratings.get(slug),
            "checklist": [{"label": l, "checked": bool(checked.get(l))} for l in leaves],
            "resume_evidence": slug in a.state.resume, "current": skill_json(a, slug) if slug in a.estimates else None,
            "calibration": (intel(a).get("calibrations") or {}).get(slug),
            "intelligence": skill_intel(a, slug)})
    return {"needs": None, "role": a.role.name, "levels": [{"value": v, "label": l} for v, l in SELF_LEVELS],
            "groups": [{"name": g, "skills": s} for g, s in groups.items()],
            "calibration_summary": intel(a).get("calibration_summary", {}),
            "methodology": intel(a).get("methodology", {})}
