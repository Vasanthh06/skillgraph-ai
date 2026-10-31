"""Idempotent catalog seeding. The curated catalog lives in code (app/data); this mirrors it into the
database so user-state tables can reference skills/roles/jobs/projects/questions by foreign key.
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.engine.catalog import compact, get_catalog
from app.models import (InterviewQuestion, Job, JobSkill, Project, ProjectSkill, Role, RoleSkill, Skill, SkillAlias, SkillDependency)


def ensure_seeded(db: Session) -> None:
    if db.scalar(select(func.count(Skill.id))):
        return
    cat = get_catalog()
    ids: dict[str, int] = {}
    for s in cat.skills.values():
        row = Skill(name=s.name, slug=s.slug, category=s.category, description=s.description, difficulty=s.difficulty, provenance="verified")
        db.add(row)
        db.flush()
        ids[s.slug] = row.id
    seen_alias: set[str] = set()
    for s in cat.skills.values():
        for a in {compact(x) for x in (s.name, *s.aliases)}:
            if a not in seen_alias:
                seen_alias.add(a)
                db.add(SkillAlias(skill_id=ids[s.slug], alias=a))
        for p in s.prereqs:
            db.add(SkillDependency(skill_id=ids[s.slug], prerequisite_id=ids[p]))
    for r in cat.roles.values():
        row = db.scalar(select(Role).where(Role.name == r.name)) or Role(name=r.name)
        row.description, row.experience_expectation, row.project_expectations, row.interview_topics, row.is_custom = r.description, r.experience, r.projects, r.interview, False
        db.add(row)
        db.flush()
        for rs in r.skills:
            db.add(RoleSkill(role_id=row.id, skill_id=ids[rs.slug], importance=rs.importance, is_required=rs.required, group_name=rs.group))
    for p in cat.projects.values():
        row = Project(key=p.key, title=p.title, description=p.description, difficulty=p.difficulty, estimated_hours=p.hours,
                      expected_output=p.expected_output, portfolio_value=p.portfolio_value, is_demo=True)
        db.add(row)
        db.flush()
        for s in p.required:
            db.add(ProjectSkill(project_id=row.id, skill_id=ids[s], kind="required"))
        for s in p.gained:
            db.add(ProjectSkill(project_id=row.id, skill_id=ids[s], kind="gained"))
    for j in cat.jobs.values():
        row = Job(key=j.key, title=j.title, company=j.company, location=j.location, experience_required=j.experience, is_demo=True,
                  description=f"DEMO listing. Required: {', '.join(cat.name(s) for s in j.required)}.")
        db.add(row)
        db.flush()
        for s in j.required:
            db.add(JobSkill(job_id=row.id, skill_id=ids[s], is_required=True, weight=1.0))
        for s in j.preferred:
            db.add(JobSkill(job_id=row.id, skill_id=ids[s], is_required=False, weight=0.5))
    for q in cat.questions.values():
        db.add(InterviewQuestion(key=q.key, skill_id=ids.get(q.skill) if q.skill else None, category=q.category, question=q.text,
                                 options=list(q.options) or None, answer_key=(q.explanation or ", ".join(q.keywords)) or None,
                                 difficulty=q.difficulty, is_demo=True))
    db.commit()


def skill_maps(db: Session) -> tuple[dict[str, int], dict[int, str]]:
    ensure_seeded(db)
    rows = db.execute(select(Skill.id, Skill.slug)).all()
    return {slug: i for i, slug in rows}, {i: slug for i, slug in rows}
