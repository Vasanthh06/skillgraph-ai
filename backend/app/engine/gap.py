"""Skill-gap analysis, prioritisation and readiness (spec §14-16, §57)."""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from app.engine.catalog import Catalog, RoleSpec

STRONG = 55.0
WEAK = 20.0
PREREQ_OK = 45.0      # a prerequisite counts as "known well enough to build on"
TARGET = 70.0         # score at which a role skill earns full readiness credit
CRITICAL_MIN_DEPENDENTS = 2
PRIORITY_WEIGHTS = {"importance": 0.35, "unlock": 0.25, "demand": 0.15, "readiness": 0.15, "ease": 0.10}


@dataclass
class GapItem:
    slug: str
    name: str
    group: str
    importance: float
    required: bool
    score: float
    status: str                 # strong | weak | missing
    critical: bool = False
    supporting: bool = False    # not in the role itself, but a prerequisite of something the role needs
    unlocks: list[str] = field(default_factory=list)
    blocked_by: list[str] = field(default_factory=list)
    priority: float = 0.0
    rank: int | None = None     # position in the "learn next" order (None for strong skills)
    downstream_count: int = 0          # unmet skills (directly or transitively) waiting on this one
    downstream_importance: float = 0.0  # summed career importance of those downstream skills


@dataclass
class GapResult:
    items: list[GapItem]
    order: list[str]                         # learn-next order of non-strong slugs
    skills_readiness: float                  # 0..100
    group_readiness: dict[str, float]

    def by_status(self, status: str) -> list[GapItem]:
        return [i for i in self.items if i.status == status]

    @property
    def critical(self) -> list[GapItem]:
        return [i for i in self.items if i.critical]

    @property
    def remaining(self) -> int:
        return len([i for i in self.items if i.status != "strong"])


def status_for(score: float) -> str:
    return "strong" if score >= STRONG else ("weak" if score >= WEAK else "missing")


def job_demand(cat: Catalog, role_name: str) -> dict[str, float]:
    """Fraction of the (demo) jobs for this role that require each skill."""
    jobs = [j for j in cat.jobs.values() if j.role == role_name]
    if not jobs:
        return {}
    out: dict[str, float] = {}
    for j in jobs:
        for s in j.required:
            out[s] = out.get(s, 0) + 1
    return {s: n / len(jobs) for s, n in out.items()}


def analyze(cat: Catalog, role: RoleSpec, scores: dict[str, float], completed: frozenset[str] | set[str] = frozenset()) -> GapResult:
    """`completed` = skills the user declared finished. They count as met for status and ordering, but the
    displayed score stays the honest blended estimate (so it is visibly unverified until evidence arrives)."""
    sc = lambda s: scores.get(s, 0.0)
    st = lambda s: "strong" if s in completed else status_for(sc(s))
    items: dict[str, GapItem] = {}
    role_slugs = {r.slug for r in role.skills}

    for r in role.skills:
        items[r.slug] = GapItem(r.slug, cat.name(r.slug), r.group, r.importance, r.required, sc(r.slug), st(r.slug))

    # Supporting prerequisites the role depends on but does not list (e.g. Linux for Docker).
    for r in role.skills:
        for p in cat.all_prereqs(r.slug):
            if p in role_slugs or p in items:
                continue
            if sc(p) < STRONG and p not in completed:
                items[p] = GapItem(p, cat.name(p), "Prerequisites", round(0.4 * r.importance, 2), True, sc(p), st(p), supporting=True)
    for slug, it in items.items():
        if it.supporting:
            deps = [r.importance for r in role.skills if slug in cat.all_prereqs(r.slug)]
            it.importance = round(0.4 * max(deps, default=0.5), 2)

    unmet = {s for s, i in items.items() if i.status != "strong"}
    demand = job_demand(cat, role.name)

    for slug, it in items.items():
        dependents = [d for d in cat.all_dependents(slug) if d in unmet]
        it.unlocks = sorted(dependents, key=lambda d: cat.depth(d))
        it.downstream_count = len(dependents)
        it.downstream_importance = round(sum(items[d].importance for d in dependents), 2)
        it.blocked_by = [p for p in cat.skills[slug].prereqs if sc(p) < PREREQ_OK and p not in completed and p in items]
        it.critical = it.status != "strong" and len(dependents) >= CRITICAL_MIN_DEPENDENTS

    def priority(it: GapItem) -> float:
        pre = cat.skills[it.slug].prereqs
        ready = 1.0 if not pre else sum(1 for p in pre if sc(p) >= PREREQ_OK or p in completed) / len(pre)
        ease = 1.0 - (cat.skills[it.slug].difficulty - 1) / 4.0
        w = PRIORITY_WEIGHTS
        # "Unlock" blends how many unmet skills wait on this one with how much they matter for the
        # career, so a foundational bottleneck is scheduled ahead of an equally easy leaf skill. The
        # topological pass below still guarantees prerequisites are never scheduled out of order.
        unlock = 0.5 * min(1.0, it.downstream_count / 4.0) + 0.5 * min(1.0, it.downstream_importance / 3.0)
        return (w["importance"] * it.importance + w["unlock"] * unlock
                + w["demand"] * demand.get(it.slug, 0.0) + w["readiness"] * ready + w["ease"] * ease)

    for it in items.values():
        it.priority = round(priority(it), 4)

    # Priority-aware topological ordering: never schedule a skill before its unmet prerequisites.
    remaining = {s for s in unmet}
    placed: list[str] = []
    satisfied = lambda p: p not in remaining or p in placed
    while remaining:
        ready = [s for s in remaining if all(satisfied(p) or sc(p) >= PREREQ_OK or p in completed for p in cat.skills[s].prereqs)]
        pool = ready or list(remaining)  # a cycle can't happen with this catalog, but never loop forever
        nxt = max(pool, key=lambda s: (items[s].priority, -cat.depth(s), s))
        placed.append(nxt)
        remaining.discard(nxt)
    for i, s in enumerate(placed, 1):
        items[s].rank = i

    # Readiness over the role's own skills (supporting prerequisites don't count towards the score).
    num = den = 0.0
    groups: dict[str, list[float]] = {}
    for r in role.skills:
        w = r.importance * (1.0 if r.required else 0.5)
        credit = min(1.0, sc(r.slug) / TARGET)
        num += w * credit
        den += w
        g = groups.setdefault(r.group, [0.0, 0.0])
        g[0] += w * credit
        g[1] += w
    return GapResult(
        items=sorted(items.values(), key=lambda i: (i.rank is None, i.rank or 0, -i.score)),
        order=placed,
        skills_readiness=round(100 * num / den, 1) if den else 0.0,
        group_readiness={k: round(100 * a / b, 1) for k, (a, b) in groups.items() if b},
    )


PROJECT_TARGET = 3  # completed role-relevant projects that earn full "projects" credit


def half_up(x: float) -> int:
    """Round .5 up (Python's round() is banker's rounding: 98.5 -> 98, which users would not expect)."""
    return int(math.floor(x + 0.5))


def skills_readiness(role: RoleSpec, scores: dict[str, float]) -> float:
    """Weighted share of the role's own skills at TARGET, 0..100 (same formula `analyze` uses)."""
    num = den = 0.0
    for r in role.skills:
        w = r.importance * (1.0 if r.required else 0.5)
        num += w * min(1.0, scores.get(r.slug, 0.0) / TARGET)
        den += w
    return 100.0 * num / den if den else 0.0


def overall_float(skills: float, projects_done: int, interview: float | None) -> float:
    """Skills 70%, projects 15%, interview 15% (interview is left out until the user has practised)."""
    parts = {"skills": (skills, 0.70), "projects": (min(1.0, projects_done / PROJECT_TARGET) * 100, 0.15)}
    if interview is not None:
        parts["interview"] = (interview, 0.15)
    tw = sum(w for _, w in parts.values())
    return sum(v * w for v, w in parts.values()) / tw


def overall_readiness(skills: float, projects_done: int, interview: float | None) -> dict:
    overall = overall_float(skills, projects_done, interview)
    return {"overall": half_up(overall), "skills": half_up(skills), "projects": half_up(min(1.0, projects_done / PROJECT_TARGET) * 100),
            "interview": None if interview is None else half_up(interview)}
