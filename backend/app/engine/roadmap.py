"""Dynamic roadmap (spec §22-23). Status is always derived from current scores and completions."""
from __future__ import annotations

from dataclasses import dataclass, field

from app.engine.catalog import Catalog
from app.engine.gap import PREREQ_OK, GapResult


@dataclass
class RoadmapNode:
    slug: str
    name: str
    status: str                 # completed | current | available | locked
    group: str
    score: float
    blocked_by: list[str] = field(default_factory=list)
    position: int = 0
    supporting: bool = False


def build(cat: Catalog, gap: GapResult, scores: dict[str, float], completed: set[str]) -> list[RoadmapNode]:
    sc = lambda s: scores.get(s, 0.0)
    done = {i.slug for i in gap.items if i.slug in completed or i.status == "strong"}
    by_slug = {i.slug: i for i in gap.items}

    known = sorted(done, key=lambda s: (cat.depth(s), cat.name(s)))
    ordered = known + [s for s in gap.order if s not in done]

    nodes: list[RoadmapNode] = []
    first_open_assigned = False
    for pos, slug in enumerate(ordered, 1):
        it = by_slug[slug]
        if slug in done:
            status, blockers = "completed", []
        else:
            blockers = [p for p in cat.skills[slug].prereqs if p not in done and sc(p) < PREREQ_OK]
            if blockers:
                status = "locked"
            elif not first_open_assigned:
                status, first_open_assigned = "current", True
            else:
                status = "available"
        nodes.append(RoadmapNode(slug, it.name, status, it.group, it.score, blockers, pos, it.supporting))
    return nodes


def progress(nodes: list[RoadmapNode]) -> dict:
    total = len(nodes)
    done = sum(1 for n in nodes if n.status == "completed")
    return {"completed": done, "total": total, "percent": round(100 * done / total) if total else 0}
