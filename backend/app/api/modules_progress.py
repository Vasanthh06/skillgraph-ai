"""Roadmap, learn & build, projects, certifications, jobs, interview, recommendations, dashboard."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.engine import intelligence as INT
from app.engine import interview as I
from app.engine import jobs as J
from app.engine import recommend as R
from app.engine.catalog import get_catalog
from app.models import (Application, Certification, InterviewAttempt, InterviewQuestion, Job, Project, Roadmap, RoadmapItem, User, UserProgress, UserProject)
from app.repositories.scoped import UserScope
from app.services import analysis as A
from app.services import intelligence as intel_svc
from app.services import views
from app.services.seed import ensure_seeded, skill_maps

cat = get_catalog()
roadmap_router = APIRouter(tags=["roadmap"])
learn_router = APIRouter(tags=["learn"])
jobs_router = APIRouter(tags=["jobs"])
interview_router = APIRouter(tags=["interview"])
reco_router = APIRouter(tags=["recommendations"])
dash_router = APIRouter(tags=["dashboard"])


def _skill(slug: str) -> str:
    s = slug if slug in cat.skills else cat.resolve(slug)
    if not s:
        raise HTTPException(404, "Unknown skill")
    return s


def _set_progress(db: Session, user: User, slug: str, item_type: str, completed: bool) -> None:
    to_id, _ = skill_maps(db)
    row = UserScope(db, user.id).upsert(UserProgress, {"skill_id": to_id[slug], "item_type": item_type, "item_id": 0})
    was_completed = bool(row.completed)
    row.completed = completed
    if completed and not was_completed:
        now = datetime.now(timezone.utc)
        row.completed_at = now
        # Learning creates future recall work; re-opening later keeps the schedule history intact.
        intel_svc.ensure_schedule(db, user.id, slug, source=item_type, when=now)


# ---------------- roadmap ----------------
class CompleteIn(BaseModel):
    completed: bool = True


@roadmap_router.get("/roadmap")
def get_roadmap(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return views.roadmap_view(A.analyze_user(db, user))


@roadmap_router.post("/roadmap/generate")
def generate_roadmap(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    a = A.refresh(db, user)
    if not a.role:
        raise HTTPException(409, "Choose a target role first")
    to_id, _ = skill_maps(db)
    role_row = A.ensure_role_row(db, a.role)
    me = UserScope(db, user.id)
    for old in me.all(Roadmap, Roadmap.is_active.is_(True)):
        old.is_active = False
    rm = me.add(Roadmap(role_id=role_row.id, is_active=True))
    db.flush()
    prio = {i.slug: i.priority for i in a.gap.items}
    for n in a.nodes:
        db.add(RoadmapItem(roadmap_id=rm.id, skill_id=to_id[n.slug], position=n.position, status=n.status, priority_score=prio.get(n.slug, 0.0)))
    db.commit()
    return views.roadmap_view(a)


@roadmap_router.put("/roadmap/{slug}/complete")
def complete_roadmap_item(slug: str, body: CompleteIn = CompleteIn(), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = _skill(slug)
    a = A.analyze_user(db, user)
    node = next((n for n in a.nodes if n.slug == s), None)
    if node is None:
        raise HTTPException(404, "That skill isn't on your roadmap")
    if body.completed and node.status == "locked":
        raise HTTPException(409, "Finish " + ", ".join(cat.name(b) for b in node.blocked_by) + " first")
    _set_progress(db, user, s, "roadmap", body.completed)
    A.log_activity(db, user.id, "roadmap_completed" if body.completed else "roadmap_reopened", "skill", None, {"skill": s})
    db.commit()
    return views.roadmap_view(A.refresh(db, user))


# ---------------- learn & build ----------------
@learn_router.get("/learn")
def learn(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    a = A.analyze_user(db, user)
    if views.needs(a):
        return {"needs": views.needs(a), "skills": [], "onboarding": views.onboarding(a)}
    focus = [n.slug for n in a.nodes if n.status in ("current", "available")][:3]
    return {"needs": None, "skills": [views.resources_for_skill(a, s) for s in focus],
            "intelligence": a.intelligence, "due_reviews": a.intelligence.get("due_reviews", []),
            "upcoming_reviews": a.intelligence.get("upcoming_reviews", []),
            "youtube_note": "Links marked is_search_url open a YouTube search. Configure YOUTUBE_API_KEY for specific videos."}


@learn_router.get("/learn/{slug}")
def learn_skill(slug: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return views.resources_for_skill(A.analyze_user(db, user), _skill(slug))


@learn_router.put("/learn/{slug}/complete")
def complete_resource(slug: str, body: CompleteIn = CompleteIn(), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = _skill(slug)
    _set_progress(db, user, s, "resource", body.completed)
    if body.completed:
        A.log_activity(db, user.id, "resource_completed", "skill", None, {"skill": s})
    db.commit()
    a = A.refresh(db, user)
    return {"skill": s, "completed": body.completed, "readiness": a.readiness,
            "review": (a.intelligence.get("reviews") or {}).get(s), "intelligence": views.skill_intel(a, s)}


@learn_router.get("/build")
def build(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    a = A.analyze_user(db, user)
    mine = [{"key": k, "title": cat.projects[k].title, "status": st} for k, st in a.project_status.items()]
    return {"recommended": views.recommended_projects(a, 6), "mine": mine}


class ProjectStatusIn(BaseModel):
    status: Literal["planned", "in_progress", "completed"]
    repo_url: str | None = Field(default=None, max_length=400)


@learn_router.get("/projects")
def projects(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Every project with this user's readiness and status (the Project Recommendations page filters it client-side)."""
    a = A.analyze_user(db, user)
    return {"needs": views.needs(a), "is_demo_data": True, "projects": views.all_projects(a)}


@learn_router.get("/projects/recommended")
def projects_recommended(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return views.recommended_projects(A.analyze_user(db, user), limit=5)


@learn_router.post("/projects/{key}/status")
def project_status(key: str, body: ProjectStatusIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if key not in cat.projects:
        raise HTTPException(404, "Unknown project")
    if body.repo_url and not body.repo_url.startswith(("http://", "https://")):
        raise HTTPException(422, "repo_url must start with http:// or https://")
    ensure_seeded(db)
    proj = db.scalar(select(Project).where(Project.key == key))
    row = UserScope(db, user.id).upsert(UserProject, {"project_id": proj.id}, title=proj.title)
    was_completed = row.status == "completed"
    row.status, row.repo_url = body.status, body.repo_url or row.repo_url
    if body.status == "completed" and not was_completed:
        for gained in cat.projects[key].gained:
            intel_svc.ensure_schedule(db, user.id, gained, source="project")
    A.log_activity(db, user.id, "project_status", "project", proj.id, {"title": proj.title, "status": body.status})
    db.commit()
    a = A.refresh(db, user)
    return {"key": key, "status": body.status, "readiness": a.readiness}


class CertIn(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    issuer: str | None = Field(default=None, max_length=160)
    skill: str | None = None
    credential_url: str | None = Field(default=None, max_length=400)


@learn_router.get("/certifications")
def list_certs(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _, to_slug = skill_maps(db)
    return [{"id": c.id, "name": c.name, "issuer": c.issuer, "skill": cat.name(to_slug[c.skill_id]) if c.skill_id else None, "credential_url": c.credential_url}
            for c in UserScope(db, user.id).all(Certification)]


@learn_router.post("/certifications", status_code=201)
def add_cert(body: CertIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    to_id, _ = skill_maps(db)
    sid = None
    if body.skill:
        sid = to_id[_skill(body.skill)]
    if body.credential_url and not body.credential_url.startswith(("http://", "https://")):
        raise HTTPException(422, "credential_url must start with http:// or https://")
    UserScope(db, user.id).add(Certification(name=body.name.strip(), issuer=body.issuer, skill_id=sid, credential_url=body.credential_url))
    if body.skill:
        intel_svc.ensure_schedule(db, user.id, _skill(body.skill), source="certification")
    A.log_activity(db, user.id, "certification_added", meta={"name": body.name})
    db.commit()
    A.refresh(db, user)
    return {"ok": True}


class ActivityIn(BaseModel):
    type: Literal["resource_opened"]
    skill: str
    url: str | None = Field(default=None, max_length=300)


@learn_router.post("/activity", status_code=201)
def record_activity(body: ActivityIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Whitelisted client-reported events (e.g. opening a video). The user comes from the token, never the body."""
    s = _skill(body.skill)
    A.log_activity(db, user.id, body.type, "skill", None, {"skill": s, "url": body.url})
    db.commit()
    return {"ok": True}


# ---------------- jobs ----------------
class JDIn(BaseModel):
    text: str = Field(min_length=30, max_length=20000)


class JobStatusIn(BaseModel):
    status: Literal["saved", "applied", "interviewing", "rejected", "offer"]


def _application_status(db: Session, user: User) -> dict[str, str]:
    return views.application_status(db, user.id)


@jobs_router.get("/jobs")
def list_jobs(min_match: int = Query(0, ge=0, le=100), q: str = Query("", max_length=60), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    a = A.analyze_user(db, user)
    ql = q.lower().strip()
    status = _application_status(db, user)
    rows = [{**j, "application_status": status.get(j["key"])} for j in views.job_matches(a)
            if j["match"] >= min_match and (not ql or ql in j["title"].lower() or ql in j["company"].lower())]
    return {"is_demo_data": True, "needs": views.needs(a), "jobs": rows, **({"onboarding": views.onboarding(a)} if views.needs(a) else {})}


@jobs_router.get("/jobs/recommended")
def jobs_recommended(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    status = _application_status(db, user)
    return {"is_demo_data": True, "jobs": [{**j, "application_status": status.get(j["key"])} for j in views.job_matches(A.analyze_user(db, user), 5)]}


@jobs_router.post("/jobs/analyze")
def analyze_jd(body: JDIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    a = A.analyze_user(db, user)
    res = J.analyze_jd(cat, body.text, a.scores)
    if res["recognised_skill_count"] == 0:
        raise HTTPException(422, "No known skills were found in this text. Paste the full job description.")
    A.log_activity(db, user.id, "jd_analyzed")
    db.commit()
    return res


@jobs_router.get("/jobs/{key}")
def get_job(key: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if key not in cat.jobs:
        raise HTTPException(404, "Unknown job")
    a = A.analyze_user(db, user)
    m = J.match_job(cat, cat.jobs[key], a.scores, a.role, a.user.profile.experience_level, a.user.profile.location)
    A.log_activity(db, user.id, "job_viewed", meta={"title": m["title"], "key": key})
    db.commit()
    return {**m, "application_status": _application_status(db, user).get(key)}


@jobs_router.delete("/jobs/{key}/status", status_code=204)
def clear_job_status(key: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Remove a saved job (or any application record) for the caller only."""
    if key not in cat.jobs:
        raise HTTPException(404, "Unknown job")
    ensure_seeded(db)
    job = db.scalar(select(Job).where(Job.key == key))
    UserScope(db, user.id).delete_where(Application, Application.job_id == job.id)
    db.commit()


@jobs_router.post("/jobs/{key}/status")
def job_status(key: str, body: JobStatusIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if key not in cat.jobs:
        raise HTTPException(404, "Unknown job")
    ensure_seeded(db)
    job = db.scalar(select(Job).where(Job.key == key))
    a = A.analyze_user(db, user)
    m = J.match_job(cat, cat.jobs[key], a.scores, a.role, a.user.profile.experience_level, a.user.profile.location)
    row = UserScope(db, user.id).upsert(Application, {"job_id": job.id})
    row.status, row.match_score = body.status, float(m["match"])
    db.commit()
    return {"key": key, "status": body.status}


# ---------------- interview ----------------
class StartIn(BaseModel):
    category: Literal["technical", "coding", "mcq", "scenario", "behavioral", "project", "hr"] | None = None
    job_key: str | None = None
    skill: str | None = Field(default=None, max_length=80)
    jd_text: str | None = Field(default=None, max_length=20000)
    count: int = Field(default=6, ge=1, le=15)
    purpose: Literal["interview", "calibration", "recall"] = "interview"


class AnswerIn(BaseModel):
    question_key: str
    answer: str | None = Field(default=None, max_length=5000)
    choice: int | None = Field(default=None, ge=0, le=9)
    self_rating: int | None = Field(default=None, ge=1, le=5)
    purpose: Literal["interview", "calibration", "recall"] = "interview"
    session_id: str | None = Field(default=None, max_length=36)


def _q_json(q, a: A.Analysis) -> dict:
    return {"key": q.key, "category": q.category, "skill": cat.name(q.skill) if q.skill else None, "skill_slug": q.skill,
            "topic": q.text[:200], "objective": q.category in INT.OBJECTIVE_WEIGHTS and (q.category == "mcq" or bool(q.keywords)),
            "difficulty": q.difficulty, "text": q.text,
            "options": list(q.options), "scoring": "exact" if q.category == "mcq" else ("self_rated" if (q.category in I.SELF_RATED or not q.keywords) else "keyword_coverage"),
            "is_demo": True}


@interview_router.get("/interview")
def interview_overview(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    a = A.analyze_user(db, user)
    answered = {x["key"] for x in a.attempts}
    cats = [{"name": c, "available": len([q for q in cat.questions.values() if q.category == c]),
             "attempted": len([k for k in answered if cat.questions[k].category == c])} for c in I.CATEGORIES]
    weak = []
    if a.gap and not views.needs(a):
        weak = [{"slug": s, "name": cat.name(s), "score": a.scores.get(s, 0), "questions": len([q for q in cat.questions.values() if q.skill == s])}
                for s in a.gap.order if any(q.skill == s for q in cat.questions.values())][:5]
    return {"role": a.role.name if a.role else None, "categories": cats, "readiness": a.interview, "focus_topics": weak,
            "struggling": R.struggling(cat, a.scores, a.attempt_avgs, a.gap) if a.gap and not views.needs(a) else [], "is_demo_content": True,
            "intelligence": None if views.needs(a) else a.intelligence}


@interview_router.post("/interview/start")
def interview_start(body: StartIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    a = A.analyze_user(db, user)
    imp = {r.slug: r.importance for r in a.role.skills} if a.role else {}
    focus, source = [], "your weakest role skills"
    if body.job_key:
        if body.job_key not in cat.jobs:
            raise HTTPException(404, "Unknown job")
        j = cat.jobs[body.job_key]
        focus, source = list(j.required), f"the {j.title} listing"
    elif body.skill:
        slug = _skill(body.skill)
        focus, source = [slug], f"a quiz on {cat.name(slug)}"
    elif body.jd_text:
        focus = list(dict.fromkeys(h[0] for h in cat.scan(body.jd_text)))
        source = "the job description you pasted"
        if not focus:
            raise HTTPException(422, "No known skills were found in that job description")
    answered = {x["key"] for x in a.attempts}
    qs = I.select_questions(cat, a.scores, imp, category=body.category, focus_skills=focus, exclude=answered, n=body.count)
    if not qs:  # everything answered once: allow repeats
        qs = I.select_questions(cat, a.scores, imp, category=body.category, focus_skills=focus, n=body.count)
    return {"based_on": source, "purpose": body.purpose, "session_id": str(uuid.uuid4()),
            "questions": [_q_json(q, a) for q in qs]}


@interview_router.post("/interview/answer")
def interview_answer(body: AnswerIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = cat.questions.get(body.question_key)
    if not q:
        raise HTTPException(404, "Unknown question")
    if q.category == "mcq" and (body.choice is None or body.choice >= len(q.options)):
        raise HTTPException(422, "Choose one of the options")
    if q.category not in I.SELF_RATED and q.category != "mcq" and q.keywords and not (body.answer or "").strip():
        raise HTTPException(422, "Write an answer first")
    score, method = I.score_answer(q, body.answer, body.choice, body.self_rating)
    ensure_seeded(db)
    row = db.scalar(select(InterviewQuestion).where(InterviewQuestion.key == q.key))
    is_correct = (body.choice == q.answer_index) if q.category == "mcq" else (score >= 70 if method == "keyword_coverage" else None)
    UserScope(db, user.id).add(InterviewAttempt(
        question_id=row.id, answer=(body.answer or (str(body.choice) if body.choice is not None else None)), score=score,
        purpose=body.purpose, session_id=body.session_id, topic=q.text[:200], is_correct=is_correct))
    A.log_activity(db, user.id, "interview_answer", "question", row.id, {"category": q.category, "purpose": body.purpose, "skill": q.skill})
    db.commit()
    a = A.refresh(db, user)
    fb: dict = {"score": score, "method": method}
    if q.category == "mcq":
        fb.update(correct_index=q.answer_index, explanation=q.explanation)
    elif method == "keyword_coverage":
        low = (body.answer or "").lower()
        fb["covered"] = [k for k in q.keywords if k.lower() in low]
        fb["consider_mentioning"] = [k for k in q.keywords if k.lower() not in low]
        fb["note"] = "Scored by keyword coverage, which is a self-check aid and not an expert assessment."
    return {**fb, "readiness": a.interview,
            "intelligence": views.skill_intel(a, q.skill) if q.skill else None,
            "top_bottleneck": a.intelligence.get("top_bottleneck")}


# ---------------- integrated knowledge checks (calibration + recall) ----------------
class CheckStartIn(BaseModel):
    skill: str = Field(max_length=80)
    purpose: Literal["calibration", "recall"] = "calibration"
    count: int = Field(default=3, ge=1, le=5)


class CheckAnswerIn(BaseModel):
    question_key: str
    answer: str | None = Field(default=None, max_length=5000)
    choice: int | None = Field(default=None, ge=0, le=9)


class CheckSubmitIn(BaseModel):
    skill: str = Field(max_length=80)
    purpose: Literal["calibration", "recall"] = "calibration"
    session_id: str = Field(min_length=8, max_length=36)
    answers: list[CheckAnswerIn] = Field(min_length=1, max_length=5)


def _objective_questions(slug: str):
    return [q for q in cat.questions.values()
            if q.skill == slug and q.category in INT.OBJECTIVE_WEIGHTS and (q.category == "mcq" or q.keywords)]


def _select_check_questions(a: A.Analysis, slug: str, purpose: str, count: int):
    pool = _objective_questions(slug)
    mine = [x for x in a.attempt_details if x.get("slug") == slug and x.get("objective")]
    answered = {x["key"] for x in mine}
    missed = {x["key"] for x in mine if x.get("missed_topics")}
    diff = {"beginner": 0, "intermediate": 1, "advanced": 2}

    def rank(q):
        missed_first = 0 if purpose == "recall" and q.key in missed else 1
        return (missed_first, 0 if q.key not in answered else 1, 0 if q.category == "mcq" else 1,
                diff.get(q.difficulty, 1), q.key)

    return sorted(pool, key=rank)[:count]


def _learned(a: A.Analysis, slug: str) -> bool:
    return bool((a.intelligence.get("reviews") or {}).get(slug) or slug in a.state.completed_roadmap
                or slug in a.state.completed_resources or slug in a.state.projects_gained)


@interview_router.post("/interview/check/start")
def knowledge_check_start(body: CheckStartIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Start a short, objectively scored check on one skill, reusing the existing question bank."""
    slug = _skill(body.skill)
    a = A.analyze_user(db, user)
    if body.purpose == "recall" and not _learned(a, slug):
        raise HTTPException(409, "Complete a learning activity for this skill first, or run a calibration check instead")
    qs = _select_check_questions(a, slug, body.purpose, body.count)
    if not qs:
        raise HTTPException(422, f"There are no scored practice questions for {cat.name(slug)} yet. Use the learning resources and a project to build evidence.")
    si = views.skill_intel(a, slug)
    return {"skill": slug, "skill_name": cat.name(slug), "purpose": body.purpose, "session_id": str(uuid.uuid4()),
            "questions": [_q_json(q, a) for q in qs], "intelligence": si,
            "note": "A short check, not a final verdict: results are blended with your other evidence."}


@interview_router.post("/interview/check/submit")
def knowledge_check_submit(body: CheckSubmitIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Score a whole check in one transaction: attempts + evidence (+ the next review date for recall)."""
    slug = _skill(body.skill)
    keys = [x.question_key for x in body.answers]
    if len(set(keys)) != len(keys):
        raise HTTPException(422, "Each question can be answered once per check")
    before = A.analyze_user(db, user)
    if body.purpose == "recall" and not _learned(before, slug):
        raise HTTPException(409, "Complete a learning activity for this skill first, or run a calibration check instead")

    scored = []  # validate and score everything before writing anything
    for ans in body.answers:
        q = cat.questions.get(ans.question_key)
        if not q or q.skill != slug or not (q.category in INT.OBJECTIVE_WEIGHTS and (q.category == "mcq" or q.keywords)):
            raise HTTPException(422, "That question is not a scored practice question for this skill")
        if q.category == "mcq" and (ans.choice is None or ans.choice >= len(q.options)):
            raise HTTPException(422, "Choose one option for every multiple-choice question")
        if q.category != "mcq" and not (ans.answer or "").strip():
            raise HTTPException(422, "Write an answer for every open question")
        score, method = I.score_answer(q, ans.answer, ans.choice, None)
        low = (ans.answer or "").lower()
        missed = ([q.text[:200]] if q.category == "mcq" and score < 100
                  else [k for k in q.keywords if k.lower() not in low] if q.category != "mcq" and score < 70 else [])
        scored.append({"q": q, "ans": ans, "score": float(score), "method": method, "missed": missed,
                       "covered": [k for k in q.keywords if k.lower() in low] if q.category != "mcq" else []})
    total_w = sum(INT.OBJECTIVE_WEIGHTS[s["q"].category] for s in scored)
    aggregate = round(sum(INT.OBJECTIVE_WEIGHTS[s["q"].category] * s["score"] for s in scored) / total_w, 1)
    weak_topics = list(dict.fromkeys(t for s in scored for t in s["missed"]))[:6]

    ensure_seeded(db)
    rows = {q.key: q for q in db.scalars(select(InterviewQuestion))}
    me = UserScope(db, user.id)
    for s in scored:
        q, ans = s["q"], s["ans"]
        me.add(InterviewAttempt(question_id=rows[q.key].id,
                                answer=(ans.answer or (str(ans.choice) if ans.choice is not None else None)),
                                score=s["score"], purpose=body.purpose, session_id=body.session_id,
                                topic=q.text[:200], is_correct=s["score"] >= 70))
    schedule = (intel_svc.record_review(db, user.id, slug, score=aggregate, weak_topics=weak_topics, source="recall")
                if body.purpose == "recall" else None)
    intel_svc.add_evidence(db, user.id, slug, source="knowledge_check" if body.purpose == "calibration" else "recall_review",
                           strength=aggregate,
                           detail=f"{body.purpose.title()} check: {len(scored)} question(s), {round(aggregate)}%."
                                  + (f" To revisit: {', '.join(weak_topics)}." if weak_topics else " No missed topics."))
    A.log_activity(db, user.id, "recall_completed" if body.purpose == "recall" else "knowledge_check",
                   "skill", None, {"skill": slug, "score": round(aggregate)})
    db.commit()
    a = A.refresh(db, user)
    return {"skill": slug, "skill_name": cat.name(slug), "purpose": body.purpose, "session_id": body.session_id,
            "score": aggregate, "correct": sum(1 for s in scored if s["score"] >= 70), "total": len(scored),
            "weak_topics": weak_topics,
            "results": [{"key": s["q"].key, "score": s["score"], "method": s["method"],
                         "correct_index": s["q"].answer_index if s["q"].category == "mcq" else None,
                         "explanation": s["q"].explanation if s["q"].category == "mcq" else None,
                         "covered": s["covered"], "consider_mentioning": s["missed"] if s["q"].category != "mcq" else []}
                        for s in scored],
            "schedule": schedule, "intelligence": views.skill_intel(a, slug),
            "top_bottleneck": a.intelligence.get("top_bottleneck"), "readiness": a.readiness, "interview": a.interview}


@learn_router.get("/learn/recall/due")
def recall_due(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Due/upcoming reviews for the signed-in user only (also embedded in /learn, /dashboard, /roadmap)."""
    a = A.analyze_user(db, user)
    return {"due_reviews": a.intelligence.get("due_reviews", []), "upcoming_reviews": a.intelligence.get("upcoming_reviews", []),
            "review_summary": a.intelligence.get("review_summary", {}), "methodology": a.intelligence.get("methodology", {})}


@interview_router.get("/interview/readiness")
def interview_readiness(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return A.analyze_user(db, user).interview


# ---------------- recommendations ----------------
def _recs(a: A.Analysis) -> dict:
    if views.needs(a):
        return {"needs": views.needs(a), "next_skill": None, "onboarding": views.onboarding(a)}
    nxt = R.next_skill(cat, a.gap, a.scores, a.role.name, a.intent)
    return {"needs": None, "source": "rules", "next_skill": nxt, "learning": views.resources_for_skill(a, nxt["slug"]) if nxt else None,
            "projects": views.recommended_projects(a, 3), "jobs": views.job_matches(a, 3),
            "interview_topics": [cat.name(s) for s in a.gap.order if any(q.skill == s for q in cat.questions.values())][:4],
            "intent": a.intent, "struggling": R.struggling(cat, a.scores, a.attempt_avgs, a.gap),
            "intelligence": a.intelligence,
            "model_status": {"two_tower": "not trained (no activity data yet)", "sasrec": "not trained (no activity data yet)",
                             "active_ranker": "rules + recency heuristic"}}


@reco_router.get("/recommendations")
def recommendations(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _recs(A.analyze_user(db, user))


@reco_router.get("/recommendations/next-best-action")
def next_best_action_endpoint(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """One recommended step with its reason. Identity comes only from the token."""
    a = A.analyze_user(db, user)
    nxt = None
    if not views.needs(a):
        nxt = R.next_skill(cat, a.gap, a.scores, a.role.name, a.intent)
    return views.next_best_action(a, nxt)


@reco_router.get("/recommendations/next-skill")
def next_skill(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _recs(A.analyze_user(db, user)).get("next_skill")


# ---------------- dashboard & progress ----------------
@dash_router.get("/api/dashboard")
@dash_router.get("/dashboard")
def dashboard(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return views.dashboard(db, A.analyze_user(db, user))


@dash_router.get("/api/progress")
@dash_router.get("/progress")
def progress(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.engine.roadmap import progress as rp

    a = A.analyze_user(db, user)
    levels: dict[str, int] = {}
    for e in a.estimates.values():
        levels[e.level] = levels.get(e.level, 0) + 1
    if views.needs(a):
        return {"needs": views.needs(a), "roadmap": None, "skill_levels": {}, "projects_completed": 0, "interview_attempts": len(a.attempts), "readiness": None, "onboarding": views.onboarding(a)}
    return {"roadmap": rp(a.nodes), "skill_levels": levels, "projects_completed": len(a.completed_projects), "interview_attempts": len(a.attempts),
            "readiness": a.readiness, "updated": True, "review_summary": a.intelligence.get("review_summary", {}),
            "calibration_summary": a.intelligence.get("calibration_summary", {})}
