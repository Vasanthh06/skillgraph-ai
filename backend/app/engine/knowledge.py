"""Weighted knowledge model (spec §11, §12, §40, §41).

Every source yields a 0-100 estimate for a skill, or None when it has no evidence. The final score is
the weight-normalised average over the sources that are present. Self-reports alone are capped, so a
checkbox can never make someone an expert (spec §41).
"""
from __future__ import annotations

from dataclasses import dataclass, field

DEFAULT_WEIGHTS = {"resume": 0.15, "self": 0.20, "assessment": 0.25, "projects": 0.20, "learning": 0.10, "interview": 0.10}
HARD_SOURCES = ("assessment", "projects", "learning", "interview")
SELF_ONLY_CAP = 60.0
SELF_LEVEL_SCORE = {"never_used": 0, "none": 0, "beginner": 25, "basic": 40, "intermediate": 60, "advanced": 80, "expert": 95}

LEVELS = [(85, "expert"), (65, "advanced"), (35, "intermediate"), (5, "beginner"), (-1, "none")]


def level_for(score: float) -> str:
    for threshold, name in LEVELS:
        if score >= threshold:
            return name
    return "none"


def self_score(level: str | None, checklist: dict[str, bool] | None, confidence_rating: float | None = None) -> float | None:
    parts = []
    if level:
        parts.append(float(SELF_LEVEL_SCORE.get(level, 0)))
    if checklist:
        parts.append(100.0 * sum(1 for v in checklist.values() if v) / len(checklist))
    if confidence_rating is not None:
        parts.append(max(0.0, min(100.0, float(confidence_rating))))
    return sum(parts) / len(parts) if parts else None


@dataclass
class SkillEvidence:
    resume: float | None = None
    self: float | None = None
    assessment: float | None = None
    projects: float | None = None
    learning: float | None = None
    interview: float | None = None

    def present(self) -> dict[str, float]:
        return {k: getattr(self, k) for k in DEFAULT_WEIGHTS if getattr(self, k) is not None}


@dataclass
class SkillEstimate:
    slug: str
    score: float
    level: str
    confidence: float  # 0..1
    sources: dict[str, float] = field(default_factory=dict)
    capped: bool = False


def estimate(slug: str, ev: SkillEvidence, weights: dict[str, float] | None = None) -> SkillEstimate:
    w = weights or DEFAULT_WEIGHTS
    present = ev.present()
    if not present:
        return SkillEstimate(slug, 0.0, "none", 0.0)
    total_w = sum(w[k] for k in present)
    score = sum(w[k] * v for k, v in present.items()) / total_w
    capped = False
    has_hard = any(k in present for k in HARD_SOURCES)
    if not has_hard and score > SELF_ONLY_CAP:
        score, capped = SELF_ONLY_CAP, True
    coverage = total_w / sum(w.values())
    vals = list(present.values())
    agreement = 1.0 - (max(vals) - min(vals)) / 100.0 if len(vals) > 1 else 1.0
    conf = min(1.0, coverage * 1.5) * (0.6 + 0.4 * agreement)
    if not has_hard:
        conf = min(conf, 0.35)
    return SkillEstimate(slug, round(score, 1), level_for(score), round(conf, 2), {k: round(v, 1) for k, v in present.items()}, capped)


@dataclass
class UserState:
    """Everything the knowledge model needs, already loaded from storage and keyed by skill slug."""
    self_levels: dict[str, str] = field(default_factory=dict)
    checklists: dict[str, dict[str, bool]] = field(default_factory=dict)
    resume: dict[str, float] = field(default_factory=dict)          # slug -> 0..100 resume evidence
    assessment: dict[str, float] = field(default_factory=dict)      # slug -> MCQ percentage
    interview: dict[str, float] = field(default_factory=dict)       # slug -> open-answer percentage
    completed_roadmap: set[str] = field(default_factory=set)
    completed_resources: set[str] = field(default_factory=set)      # skill slugs with a finished resource
    projects_gained: dict[str, float] = field(default_factory=dict) # slug -> 0..100 from completed projects
    confidence_ratings: dict[str, float] = field(default_factory=dict)  # explicit 0..100 self-confidence (appended last: positional callers stay compatible)


def build_profile(state: UserState, weights: dict[str, float] | None = None) -> dict[str, SkillEstimate]:
    slugs = set(state.self_levels) | set(state.confidence_ratings) | set(state.checklists) | set(state.resume) | set(state.assessment) | set(state.interview) \
        | state.completed_roadmap | state.completed_resources | set(state.projects_gained)
    out = {}
    for s in slugs:
        learning = 75.0 if s in state.completed_roadmap else (60.0 if s in state.completed_resources else None)
        ev = SkillEvidence(
            resume=state.resume.get(s),
            self=self_score(state.self_levels.get(s), state.checklists.get(s), state.confidence_ratings.get(s)),
            assessment=state.assessment.get(s),
            projects=state.projects_gained.get(s),
            learning=learning,
            interview=state.interview.get(s),
        )
        out[s] = estimate(s, ev, weights)
    return out
