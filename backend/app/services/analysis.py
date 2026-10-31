"""Single entry point that turns stored user evidence into every derived view (spec §39, §57).

Every module (dashboard, gap, roadmap, jobs, interview, resume) calls `analyze_user`, so they can never
disagree. Mutating endpoints call `refresh`, which re-runs the pipeline and caches the results.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engine import gap as G
from app.engine import intelligence as INT
from app.engine import interview as I
from app.engine import recommend as R
from app.engine import roadmap as RM
from app.engine.catalog import Catalog, RoleSpec, get_catalog
from app.engine.knowledge import SkillEstimate, UserState, build_profile
from app.ml.semantic import nearest_role
from app.models import (Certification, Evidence, InterviewAttempt, InterviewQuestion, Project, Recommendation, Resume, ResumeSkill, Role,
                        SkillRecallSchedule, User, UserActivity, UserProgress, UserProject, UserSkill, UserSkillAssessment)
from app.nlp import resume_parser as RP
from app.repositories.scoped import UserScope
from app.services.seed import skill_maps

# Below this share of role skills with evidence, personalised numbers would be guesswork, so modules show
# onboarding instead of scores (spec §16).
MIN_COVERAGE = 0.25

ROLE_ALIASES = {"ml engineer": "Machine Learning Engineer", "ux designer": "UI/UX Designer", "ui designer": "UI/UX Designer",
                "software engineer": "Software Developer", "web developer": "Full Stack Developer", "security analyst": "Cybersecurity Analyst",
                "cybersecurity engineer": "Cybersecurity Analyst", "devops": "DevOps Engineer", "ai developer": "AI Engineer"}


def resolve_role(cat: Catalog, name: str | None) -> RoleSpec | None:
    if not name or not name.strip():
        return None
    n = name.strip()
    for rn, spec in cat.roles.items():
        if rn.lower() == n.lower():
            return spec
    if n.lower() in ROLE_ALIASES:
        return cat.roles[ROLE_ALIASES[n.lower()]]
    near, _ = nearest_role(cat, n)
    b = cat.roles[near]
    return RoleSpec(name=n, description=f"Custom role. Requirements are GENERATED from the closest curated role ({near}); review them.",
                    experience=b.experience, projects=b.projects, interview=b.interview, skills=b.skills, limited_coverage=True,
                    is_custom=True, derived_from=near)


def ensure_role_row(db: Session, spec: RoleSpec) -> Role:
    row = db.scalar(select(Role).where(Role.name == spec.name))
    if row is None:
        row = Role(name=spec.name, description=spec.description, is_custom=spec.is_custom)
        db.add(row)
        db.flush()
    return row


def log_activity(db: Session, user_id: str, event: str, entity_type: str | None = None, entity_id: int | None = None, meta: dict | None = None) -> None:
    UserScope(db, user_id).add(UserActivity(event_type=event, entity_type=entity_type, entity_id=entity_id, meta=meta))


@dataclass
class Analysis:
    user: User
    cat: Catalog
    role: RoleSpec | None
    state: UserState
    estimates: dict[str, SkillEstimate]
    scores: dict[str, float]
    gap: G.GapResult | None
    nodes: list[RM.RoadmapNode]
    resume: dict | None          # {parsed, role_match, analysis}
    projects_done: int
    attempts: list[dict]
    attempt_avgs: dict[str, tuple[float, int]]
    interview: dict
    readiness: dict | None
    recent_skills: list[str]
    intent: dict | None
    completed_projects: set[str] = field(default_factory=set)
    project_status: dict[str, str] = field(default_factory=dict)
    coverage: float = 0.0          # share of the target role's skills for which we have ANY evidence
    answered_self: int = 0         # role skills the user has answered in the assessment
    role_total: int = 0
    attempt_details: list[dict] = field(default_factory=list)      # per-attempt topic/date detail for calibration
    learning_events: dict[str, dict] = field(default_factory=dict)  # slug -> latest completed-learning event
    evidence_dates: dict[str, datetime] = field(default_factory=dict)
    evidence_history: dict[str, list[dict]] = field(default_factory=dict)
    intelligence: dict = field(default_factory=dict)               # bottleneck + calibration + recall (engine/intelligence.py)


def _note_date(dates: dict[str, datetime], slug: str, at: datetime | None) -> None:
    at = INT.as_utc(at)
    if slug and at and (slug not in dates or at > dates[slug]):
        dates[slug] = at


def _note_learning(events: dict[str, dict], dates: dict[str, datetime], slug: str, at: datetime | None, source: str) -> None:
    at = INT.as_utc(at)
    if not slug or not at:
        return
    _note_date(dates, slug, at)
    cur = events.get(slug)
    if cur is None or at >= cur["at"]:
        sources = list(dict.fromkeys([*(cur["sources"] if cur else []), source]))
        events[slug] = {"at": at, "sources": sources}


def load_state(db: Session, user_id: str):
    cat = get_catalog()
    to_id, to_slug = skill_maps(db)
    me = UserScope(db, user_id)
    st = UserState()
    evidence_dates: dict[str, datetime] = {}
    learning_events: dict[str, dict] = {}
    for a in me.all(UserSkillAssessment):
        slug = to_slug.get(a.skill_id)
        if not slug:
            continue
        if a.self_level:
            st.self_levels[slug] = a.self_level
        if a.confidence_rating is not None:
            st.confidence_ratings[slug] = float(a.confidence_rating)
        if a.checklist:
            st.checklists[slug] = {k: bool(v) for k, v in a.checklist.items()}
        if a.self_level or a.confidence_rating is not None or a.checklist:
            _note_date(evidence_dates, slug, a.updated_at or a.created_at)
    resume = me.first(Resume, Resume.analysis_status == "completed", order_by=Resume.id.desc())  # pending uploads never count
    if resume:
        for rs in db.scalars(select(ResumeSkill).where(ResumeSkill.resume_id == resume.id)):  # resume is owned (fetched via scope)
            slug = to_slug.get(rs.skill_id) if rs.skill_id else None
            if slug:
                st.resume[slug] = round(rs.confidence * 100, 1)
                _note_date(evidence_dates, slug, getattr(rs, "updated_at", None) or resume.updated_at or resume.created_at)
    for p in me.all(UserProgress, UserProgress.completed.is_(True)):
        slug = to_slug.get(p.skill_id)
        if slug:
            (st.completed_roadmap if p.item_type == "roadmap" else st.completed_resources).add(slug)
            _note_learning(learning_events, evidence_dates, slug,
                           p.completed_at or p.updated_at or p.created_at, p.item_type)

    for c in me.all(Certification, Certification.skill_id.is_not(None)):
        slug = to_slug.get(c.skill_id)
        if slug:
            st.completed_resources.add(slug)  # a certificate counts as completed learning
            _note_learning(learning_events, evidence_dates, slug, c.issued_on or c.updated_at or c.created_at, "certification")

    completed_projects, project_status = set(), {}
    for up in me.all(UserProject):
        proj = db.get(Project, up.project_id) if up.project_id else None
        if proj and proj.key in cat.projects:
            project_status[proj.key] = up.status
            if up.status == "completed":
                completed_projects.add(proj.key)
                for s in cat.projects[proj.key].gained:
                    st.projects_gained[s] = max(st.projects_gained.get(s, 0), 80.0)
                    _note_learning(learning_events, evidence_dates, s, up.updated_at or up.created_at, "project")
                for s in cat.projects[proj.key].required:
                    st.projects_gained[s] = max(st.projects_gained.get(s, 0), 60.0)
                    _note_date(evidence_dates, s, up.updated_at or up.created_at)

    attempts, attempt_details, mcq_details, openq, per_skill = [], [], {}, {}, {}
    qs = {q.id: q for q in db.scalars(select(InterviewQuestion))}  # global question bank
    for att in me.all(InterviewAttempt, InterviewAttempt.score.is_not(None), order_by=InterviewAttempt.id.asc()):
        q = qs.get(att.question_id)
        if q is None:
            continue
        score, category, skill_id, key = float(att.score), q.category, q.skill_id, q.key
        attempts.append({"category": category, "score": score, "key": key})
        slug = to_slug.get(skill_id) if skill_id else None
        cq = cat.questions.get(key) if key else None
        objective = category in INT.OBJECTIVE_WEIGHTS and bool(cq) and (category == "mcq" or bool(cq.keywords))
        topic = att.topic or (cq.text[:200] if cq else q.question[:200])
        missed: list[str] = []
        if objective and cq:
            if category == "mcq" and score < 100:
                missed = [topic]
            elif cq.keywords and score < 70:
                low = (att.answer or "").lower()
                missed = [k for k in cq.keywords if k.lower() not in low] or [topic]
        attempt_details.append({"id": att.id, "slug": slug, "key": key, "category": category, "score": score,
                                "objective": objective, "topic": topic, "missed_topics": missed,
                                "correct": att.is_correct if att.is_correct is not None else score >= 70,
                                "purpose": att.purpose or "interview", "created_at": att.created_at})
        if slug:
            per_skill.setdefault(slug, []).append(score)
            _note_date(evidence_dates, slug, att.created_at)
            if category == "mcq":
                mcq_details.setdefault(slug, []).append(attempt_details[-1])
            else:
                openq.setdefault(slug, []).append(score)
    # The knowledge model's MCQ source is recency-weighted over the last 8 objective answers and
    # shrunk toward neutral, so one short quiz can inform the estimate without swinging it.
    now = datetime.now(timezone.utc)
    st.assessment = {s: v for s, rows in mcq_details.items()
                     if (v := INT.weighted_performance(rows[-8:], now, shrink=True)) is not None}
    st.interview = {s: sum(v) / len(v) for s, v in openq.items()}
    avgs = {s: (sum(v) / len(v), len(v)) for s, v in per_skill.items()}

    schedules: dict[str, dict] = {}
    for row in me.all(SkillRecallSchedule):
        slug = to_slug.get(row.skill_id)
        if slug:
            schedules[slug] = {"learned_at": row.learned_at, "last_reviewed_at": row.last_reviewed_at,
                               "next_review_at": row.next_review_at, "interval_days": row.interval_days,
                               "review_stage": row.review_stage, "review_count": row.review_count,
                               "successful_reviews": row.successful_reviews, "last_score": row.last_score,
                               "last_result": row.last_result, "weak_topics": list(row.weak_topics or []),
                               "source": row.source}
            _note_date(evidence_dates, slug, row.last_reviewed_at)

    evidence_history: dict[str, list[dict]] = {}
    for ev in me.all(Evidence, order_by=Evidence.id.desc()):
        slug = to_slug.get(ev.skill_id)
        if slug:
            _note_date(evidence_dates, slug, ev.created_at)
            rows = evidence_history.setdefault(slug, [])
            if len(rows) < 12:
                rows.append({"source": ev.source, "strength": ev.strength, "detail": ev.detail,
                             "at": INT.iso(ev.created_at)})
    return st, attempts, avgs, resume, completed_projects, project_status, attempt_details, learning_events, evidence_dates, schedules, evidence_history


def analyze_user(db: Session, user: User) -> Analysis:
    cat = get_catalog()
    st, attempts, avgs, resume_row, done, pstatus, attempt_details, learning_events, evidence_dates, schedules, evidence_history = load_state(db, user.id)
    estimates = build_profile(st)
    scores = {k: v.score for k, v in estimates.items()}
    role = resolve_role(cat, user.profile.target_role)
    gap = G.analyze(cat, role, scores, st.completed_roadmap) if role else None
    nodes = RM.build(cat, gap, scores, st.completed_roadmap) if gap else []

    resume = None
    if resume_row and resume_row.raw_text:
        parsed = RP.parse(cat, resume_row.raw_text)
        # The saved resume's evidence is the ResumeSkill rows, which /resume/confirm may have
        # pruned ("this skill was detected wrongly"). Re-parsing the raw text alone would resurrect
        # those rejected skills in the extracted list, role match and tips, even though they (correctly)
        # no longer feed the knowledge scores. Keep the parsed view consistent with the saved evidence.
        parsed.skills = {slug: e for slug, e in parsed.skills.items() if slug in st.resume}
        resume = {"parsed": parsed, "filename": resume_row.filename, "uploaded_at": resume_row.created_at,
                  "analysis": RP.analyze(cat, parsed, role, scores) if role else None}

    interview = I.readiness(attempts, resume["analysis"]["role_match"] if resume and resume["analysis"] else None, gap.skills_readiness if gap else None)
    readiness = G.overall_readiness(gap.skills_readiness, len(done), interview["overall"]) if gap else None

    to_id, _ = skill_maps(db)
    recent = []
    for ev in UserScope(db, user.id).all(UserActivity, UserActivity.event_type.in_(("skill_search", "skill_view")), order_by=UserActivity.id.desc(), limit=12):
        s = (ev.meta or {}).get("skill")
        if s:
            recent.append(s)
    recent.reverse()
    intent = R.infer_intent(cat, recent, scores)
    role_slugs = {r.slug for r in role.skills} if role else set()
    evidence = {s for s, e in estimates.items() if e.sources}
    coverage = len(role_slugs & evidence) / len(role_slugs) if role_slugs else 0.0
    answered = len(role_slugs & set(st.self_levels))
    intelligence = INT.build_intelligence(cat, state=st, estimates=estimates, gap=gap, nodes=nodes,
                                          attempt_details=attempt_details, learning_events=learning_events,
                                          schedules=schedules, evidence_dates=evidence_dates)
    return Analysis(user, cat, role, st, estimates, scores, gap, nodes, resume, len(done), attempts, avgs, interview, readiness, recent, intent, done, pstatus,
                    coverage, answered, len(role_slugs), attempt_details, learning_events, evidence_dates, evidence_history, intelligence)


def views_ready(a: "Analysis") -> bool:
    return a.coverage >= MIN_COVERAGE


def refresh(db: Session, user: User) -> Analysis:
    """Re-run the whole pipeline and cache the derived skill estimates and top recommendation (spec §57)."""
    a = analyze_user(db, user)
    to_id, _ = skill_maps(db)
    me = UserScope(db, user.id)
    live = set()
    calibrations = (a.intelligence or {}).get("calibrations", {})
    reviews = (a.intelligence or {}).get("reviews", {})
    for slug, est in a.estimates.items():
        sid = to_id.get(slug)
        if sid is None:
            continue
        live.add(sid)
        cal = calibrations.get(slug) or {}
        nxt = (reviews.get(slug) or {}).get("next_review_at")
        me.upsert(UserSkill, {"skill_id": sid}, score=est.score, level=est.level, confidence=est.confidence,
                  self_confidence=cal.get("self_rating"), demonstrated_score=cal.get("demonstrated_score"),
                  calibration_status=cal.get("status") or "insufficient_evidence",
                  last_evidence_at=a.evidence_dates.get(slug),
                  next_review_at=datetime.fromisoformat(nxt) if nxt else None)
        if cal.get("demonstrated_score") is not None:
            # Keep the existing per-skill assessment row's test score in step with demonstrated
            # performance; the attempt history itself stays untouched in InterviewAttempt.
            me.upsert(UserSkillAssessment, {"skill_id": sid}, test_score=float(cal["demonstrated_score"]))
    for stale in me.all(UserSkill):  # a removed resume/answer must not leave a stale cached skill behind
        if stale.skill_id not in live:
            db.delete(stale)
    me.delete_where(Recommendation, Recommendation.kind == "skill")
    if a.gap and a.role and views_ready(a):
        rec = R.next_skill(a.cat, a.gap, a.scores, a.role.name, a.intent)
        if rec and rec["slug"] in to_id:
            me.add(Recommendation(kind="skill", entity_id=to_id[rec["slug"]], score=1.0, explanation=rec, source="rules"))
    db.commit()
    return a
