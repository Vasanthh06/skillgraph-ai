"""Roles, assessment, resume, skills/search, skill gap."""
from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.data.skills_data import taxonomy_leaves
from app.engine.catalog import get_catalog
from app.graph import skill_graph as SG
from app.ml import semantic
from app.models import Resume, ResumeSkill, Role, User, UserSkillAssessment
from app.nlp import resume_parser as RP
from app.repositories.scoped import UserScope
from app.schemas.profile import ProfileUpdate
from app.services import analysis as A
from app.services import intelligence as intel_svc
from app.services import profile_service, views
from app.services.seed import skill_maps

cat = get_catalog()
VALID_LEVELS = {v for v, _ in views.SELF_LEVELS}

roles_router = APIRouter(tags=["roles"])
assessment_router = APIRouter(tags=["assessment"])
resume_router = APIRouter(tags=["resume"])
skills_router = APIRouter(tags=["skills"])
gap_router = APIRouter(tags=["skill-gap"])


# ---------------- roles ----------------
def _role_json(spec, row_id=None, detail=False):
    out = {"id": row_id, "name": spec.name, "description": spec.description, "skill_count": len(spec.skills),
           "limited_coverage": spec.limited_coverage, "is_custom": spec.is_custom, "derived_from": spec.derived_from}
    if detail:
        out.update({"experience": spec.experience, "projects": spec.projects, "interview_topics": spec.interview,
                    "skills": [{"slug": s.slug, "name": cat.name(s.slug), "importance": s.importance, "required": s.required, "group": s.group} for s in spec.skills]})
        out["required"] = [s for s in out["skills"] if s["required"]]
        out["optional"] = [s for s in out["skills"] if not s["required"]]
        out["tools"] = [s["name"] for s in out["skills"] if cat.skills[s["slug"]].category in ("Tools", "Frameworks", "Deployment", "Cloud")]
        out["programming_languages"] = [s["name"] for s in out["skills"] if cat.skills[s["slug"]].category == "Programming"]
    return out


class TargetIn(BaseModel):
    role_id: int | None = None
    name: str | None = Field(default=None, max_length=120)


@roles_router.get("/roles")
def list_roles(q: str = Query("", max_length=80), db: Session = Depends(get_db)):
    skill_maps(db)
    ids = {r.name: r.id for r in db.scalars(select(Role))}
    ql = q.strip().lower()
    return [_role_json(s, ids.get(n)) for n, s in cat.roles.items() if not ql or ql in n.lower() or ql in s.description.lower()]


@roles_router.get("/roles/{role_id}")
def get_role(role_id: int, db: Session = Depends(get_db)):
    row = db.get(Role, role_id)
    # Custom roles are user-typed text owned by whoever created them, so they are never readable by id.
    spec = A.resolve_role(cat, row.name) if row and not row.is_custom else None
    if not spec:
        raise HTTPException(404, "Unknown role")
    return _role_json(spec, row.id, detail=True)


@roles_router.put("/roles/target")
def set_target(data: TargetIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    name = data.name
    if data.role_id is not None:
        row = db.get(Role, data.role_id)
        if not row:
            raise HTTPException(404, "Unknown role")
        name = row.name
    if not name or not name.strip():
        raise HTTPException(422, "Provide a role_id or a role name")
    profile_service.update(db, user, ProfileUpdate(target_role=name))
    a = A.analyze_user(db, user)
    return {"target_role": a.role.name, "is_generated": a.role.is_custom, "derived_from": a.role.derived_from, "readiness": a.readiness}


# ---------------- assessment ----------------
class AnswerIn(BaseModel):
    skill: str
    level: str | None = None
    checklist: dict[str, bool] | None = None
    confidence: float | None = Field(default=None, ge=0, le=100)  # "could use this independently" rating

    @field_validator("level")
    @classmethod
    def _lvl(cls, v):
        if v is not None and v not in VALID_LEVELS:
            raise ValueError(f"level must be one of {sorted(VALID_LEVELS)}")
        return v


class AssessmentIn(BaseModel):
    answers: list[AnswerIn] = Field(max_length=200)


@assessment_router.get("/assessment")
def get_assessment(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return views.assessment_form(A.analyze_user(db, user))


@assessment_router.post("/assessment")
def post_assessment(data: AssessmentIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    to_id, _ = skill_maps(db)
    me = UserScope(db, user.id)
    saved = 0
    for ans in data.answers:
        slug = cat.resolve(ans.skill) or (ans.skill if ans.skill in cat.skills else None)
        if slug is None:
            raise HTTPException(422, f"Unknown skill: {ans.skill}")
        if ans.level is None and not ans.checklist and ans.confidence is None:
            continue
        valid = set(taxonomy_leaves(slug))
        if ans.checklist and not set(ans.checklist) <= valid:
            raise HTTPException(422, f"Unknown checklist item for {cat.name(slug)}")
        row = me.upsert(UserSkillAssessment, {"skill_id": to_id[slug]})
        if ans.level is not None:
            row.self_level = ans.level
        if ans.checklist is not None:
            row.checklist = ans.checklist
        if ans.confidence is not None and row.confidence_rating != float(ans.confidence):
            row.confidence_rating = float(ans.confidence)
            intel_svc.add_evidence(db, user.id, slug, source="self_confidence", strength=float(ans.confidence),
                                   detail=f"Recorded self-confidence of {round(float(ans.confidence))}% before practical checks.")
        saved += 1
    A.log_activity(db, user.id, "assessment_saved", meta={"count": saved})
    db.commit()
    a = A.refresh(db, user)
    return {"saved": saved, "readiness": a.readiness, "needs": views.needs(a),
            "calibrations": a.intelligence.get("calibrations", {}), "intelligence": a.intelligence}


# ---------------- resume (two steps: upload stages it, confirm saves it) ----------------
def _extracted(parsed) -> dict:
    return {"skills": [{"slug": s, "name": cat.name(s), "evidence": e["evidence"], "mentions": e["mentions"], "written_as": e["raw"]} for s, e in parsed.skills.items()],
            "soft_skills": parsed.soft_skills, "education": parsed.education, "certifications": parsed.certifications, "experience_years": parsed.experience_years,
            "sections_found": sorted(k for k in parsed.sections if k != "header")}


def _resume_view(a: A.Analysis, pending: dict | None = None) -> dict:
    """The SAVED resume (the one that feeds the user's profile) plus any resume still awaiting review."""
    if not a.resume:
        return {"uploaded": False, "pending": pending}
    p = a.resume["parsed"]
    return {"uploaded": True, "filename": a.resume["filename"], "uploaded_at": a.resume["uploaded_at"].isoformat() if a.resume["uploaded_at"] else None,
            "extracted": _extracted(p), "analysis": a.resume["analysis"], "role": a.role.name if a.role else None, "pending": pending}


def _pending_view(db: Session, user: User, a: A.Analysis) -> dict | None:
    row = UserScope(db, user.id).first(Resume, Resume.analysis_status == "pending", order_by=Resume.id.desc())
    if row is None:
        return None
    parsed = RP.parse(cat, row.raw_text or "")
    return {"status": "pending", "filename": row.filename, "extracted": _extracted(parsed), "role": a.role.name if a.role else None,
            "analysis": RP.analyze(cat, parsed, a.role, a.scores) if a.role else None,
            "note": "Not saved yet. Review the skills we found, remove any that are wrong, then confirm."}


def _drop_pending(db: Session, me: UserScope) -> None:
    for old in me.all(Resume, Resume.analysis_status == "pending"):
        db.query(ResumeSkill).filter(ResumeSkill.resume_id == old.id).delete()  # old is owned: fetched via scope
        try:
            Path(old.file_path).unlink(missing_ok=True)
        except OSError:
            pass
        db.delete(old)


@resume_router.post("/resume/upload")
async def upload_resume(file: UploadFile, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Stage a resume for review. It does NOT change the user's skill profile until /resume/confirm."""
    s = get_settings()
    data = await file.read(s.MAX_RESUME_BYTES + 1)
    if len(data) > s.MAX_RESUME_BYTES:
        raise HTTPException(413, f"Resume must be under {s.MAX_RESUME_BYTES // 1024 // 1024} MB")
    name = (file.filename or "resume").replace("\\", "/").split("/")[-1][:120]
    ext = Path(name).suffix.lower()
    if ext not in (".pdf", ".docx", ".txt"):
        raise HTTPException(415, "Unsupported file type. Upload a PDF, DOCX or TXT resume.")
    try:
        text = RP.extract_text(data, name)
    except RP.UnsupportedResume as e:
        raise HTTPException(422, str(e))
    parsed = RP.parse(cat, text)
    if not parsed.skills and not any(k != "header" for k in parsed.sections):
        raise HTTPException(422, "This doesn't look like a resume: no sections or known skills were found.")
    folder = Path(s.UPLOAD_DIR) / "resumes"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{user.id}-{uuid.uuid4().hex}{ext}"
    path.write_bytes(data)
    to_id, _ = skill_maps(db)
    me = UserScope(db, user.id)
    _drop_pending(db, me)  # a newer upload replaces an unreviewed one
    row = me.add(Resume(filename=name, file_path=str(path), raw_text=text, analysis_status="pending",
                        parsed={"sections": sorted(parsed.sections), "skill_count": len(parsed.skills)}))
    db.flush()
    for slug, ev in RP.resume_evidence(parsed).items():
        db.add(ResumeSkill(resume_id=row.id, skill_id=to_id[slug], raw_text=", ".join(parsed.skills[slug]["raw"])[:160], confidence=ev / 100.0))
    db.commit()
    a = A.analyze_user(db, user)
    return _resume_view(a, _pending_view(db, user, a))


class ResumeConfirmIn(BaseModel):
    exclude: list[str] = Field(default_factory=list, max_length=100)  # skills the user says were detected wrongly


@resume_router.post("/resume/confirm")
def confirm_resume(body: ResumeConfirmIn = ResumeConfirmIn(), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Save the staged resume: drop the skills the user rejected, then let it feed the profile."""
    me = UserScope(db, user.id)
    row = me.first(Resume, Resume.analysis_status == "pending", order_by=Resume.id.desc())
    if row is None:
        raise HTTPException(404, "There is no uploaded resume waiting to be saved")
    to_id, _ = skill_maps(db)
    ids = []
    for raw in body.exclude:
        slug = raw if raw in cat.skills else cat.resolve(raw)
        if slug is None:
            raise HTTPException(422, f"Unknown skill: {raw}")
        ids.append(to_id[slug])
    if ids:
        db.query(ResumeSkill).filter(ResumeSkill.resume_id == row.id, ResumeSkill.skill_id.in_(ids)).delete(synchronize_session=False)
    row.analysis_status = "completed"
    A.log_activity(db, user.id, "resume_uploaded", meta={"filename": row.filename, "excluded": len(ids)})
    db.commit()
    a = A.refresh(db, user)
    return _resume_view(a, None)


@resume_router.delete("/resume/pending", status_code=204)
def discard_pending_resume(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _drop_pending(db, UserScope(db, user.id))
    db.commit()


@resume_router.delete("/resume", status_code=204)
def remove_saved_resume(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Remove the saved resume; the profile is recalculated without it."""
    me = UserScope(db, user.id)
    for r in me.all(Resume, Resume.analysis_status == "completed"):
        db.query(ResumeSkill).filter(ResumeSkill.resume_id == r.id).delete()
        try:
            Path(r.file_path).unlink(missing_ok=True)
        except OSError:
            pass
        db.delete(r)
    db.commit()
    A.refresh(db, user)


@resume_router.get("/resume")
def get_resume(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    a = A.analyze_user(db, user)
    return _resume_view(a, _pending_view(db, user, a))


@resume_router.post("/resume/analyze")
def analyze_resume(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    a = A.analyze_user(db, user)
    if not a.resume:
        raise HTTPException(404, "Upload a resume first")
    return _resume_view(a, _pending_view(db, user, a))


# ---------------- skills / search ----------------
def _slug_or_404(slug: str) -> str:
    s = slug if slug in cat.skills else cat.resolve(slug)
    if not s:
        raise HTTPException(404, "Unknown skill")
    return s


@skills_router.get("/skills")
def list_skills(category: str | None = None, q: str = Query("", max_length=80)):
    ql = q.strip().lower()
    return [{"slug": s.slug, "name": s.name, "category": s.category, "difficulty": s.difficulty}
            for s in cat.skills.values() if (not category or s.category == category) and (not ql or ql in s.name.lower())]


@skills_router.get("/skills/{slug}")
def get_skill(slug: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = _slug_or_404(slug)
    A.log_activity(db, user.id, "skill_view", "skill", None, {"skill": s})
    db.commit()
    d = SG.skill_detail(cat, s)
    d["graph"] = SG.neighborhood(cat, s)
    return d


@skills_router.get("/skills/{slug}/taxonomy")
def skill_taxonomy(slug: str):
    s = _slug_or_404(slug)
    t = SG.taxonomy(s)
    return {"slug": s, "provenance": "verified" if t else None, "taxonomy": t, "learning_path": [{"slug": p, "name": cat.name(p)} for p in SG.learning_path(cat, s)],
            "message": None if t else "No detailed taxonomy is curated for this skill yet. The learning path above is built from verified prerequisites."}


@skills_router.get("/skills/{slug}/projects")
def skill_projects(slug: str):
    return SG.skill_detail(cat, _slug_or_404(slug))["projects"]


@skills_router.get("/skills/{slug}/jobs")
def skill_jobs(slug: str):
    return SG.skill_detail(cat, _slug_or_404(slug))["jobs"]


@skills_router.get("/skills/{slug}/resources")
def skill_resources(slug: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return views.resources_for_skill(A.analyze_user(db, user), _slug_or_404(slug))


@skills_router.get("/search")
def search(q: str = Query("", max_length=80), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = q.strip()
    if not q:
        raise HTTPException(422, "Enter a skill or technology to search for")
    res = semantic.search(cat, q)
    A.log_activity(db, user.id, "skill_search", None, None, {"query": q, "skill": res["exact"]})
    db.commit()
    out = {"query": q, "exact": None, "matches": [{"slug": s, "name": cat.name(s), "category": cat.skills[s].category} for s in res["matches"]],
           "related": [{"slug": r["slug"], "name": cat.name(r["slug"]), "similarity": r["similarity"]} for r in res["related"]],
           "search_backend": {"index": res["backend"], "embedder": res.get("embedder")}}
    if res["exact"]:
        d = SG.skill_detail(cat, res["exact"])
        d["graph"] = SG.neighborhood(cat, res["exact"])
        out["exact"] = d
    out["can_generate"] = not res["exact"] and not res["matches"]
    return out


@skills_router.post("/skills/generate-taxonomy")
def generate_taxonomy(body: dict):
    """AI taxonomy generation needs a language model, which is not configured in demo mode.
    When one is added, results MUST be returned with provenance="generated" and shown as unverified."""
    raise HTTPException(501, "Taxonomy generation needs a language model, which isn't configured on this server. Showing related verified skills instead.")


# ---------------- skill gap ----------------
@gap_router.get("/skill-gap")
def skill_gap(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return views.gap_view(A.analyze_user(db, user))


@gap_router.get("/skill-graph")
def skill_graph(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return views.skill_graph(A.analyze_user(db, user))


@gap_router.post("/skill-gap/analyze")
def skill_gap_analyze(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return views.gap_view(A.refresh(db, user))
