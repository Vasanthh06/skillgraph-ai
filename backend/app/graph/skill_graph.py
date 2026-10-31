"""Skill dependency graph and taxonomy views (spec §35-37, §59)."""
from __future__ import annotations

from app.data.skills_data import DOCS_URLS, TAXONOMY
from app.engine.catalog import Catalog


def neighborhood(cat: Catalog, slug: str, up: int = 2, down: int = 1) -> dict:
    """Nodes/edges around a skill: prerequisites `up` levels, dependants `down` levels."""
    nodes: dict[str, dict] = {slug: {"id": slug, "name": cat.name(slug), "category": cat.skills[slug].category, "role": "focus"}}
    edges: set[tuple[str, str]] = set()

    def walk(cur: str, depth: int, direction: str):
        if depth == 0:
            return
        nxt = cat.skills[cur].prereqs if direction == "up" else cat.dependents.get(cur, [])
        for n in nxt:
            nodes.setdefault(n, {"id": n, "name": cat.name(n), "category": cat.skills[n].category, "role": "prerequisite" if direction == "up" else "dependent"})
            edges.add((n, cur) if direction == "up" else (cur, n))  # edge points prerequisite -> dependent
            walk(n, depth - 1, direction)

    walk(slug, up, "up")
    walk(slug, down, "down")
    return {"nodes": list(nodes.values()), "edges": [{"source": a, "target": b} for a, b in sorted(edges)]}


def learning_path(cat: Catalog, slug: str) -> list[str]:
    """Prerequisites in dependency order, ending at the skill itself."""
    needed = cat.all_prereqs(slug) | {slug}
    return sorted(needed, key=lambda s: (cat.depth(s), cat.name(s)))


def taxonomy(slug: str) -> dict | None:
    tree = TAXONOMY.get(slug)
    if not tree:
        return None
    return {"name": slug, "children": [{"name": g, "children": [{"name": k} for k in kids]} for g, kids in tree.items()]}


def career_paths(cat: Catalog, slug: str) -> list[dict]:
    out = []
    for r in cat.roles.values():
        hit = next((x for x in r.skills if x.slug == slug), None)
        if hit:
            out.append({"role": r.name, "importance": hit.importance, "required": hit.required})
    return sorted(out, key=lambda x: -x["importance"])


def skill_detail(cat: Catalog, slug: str) -> dict:
    s = cat.skills[slug]
    return {
        "slug": slug, "name": s.name, "category": s.category, "difficulty": s.difficulty, "description": s.description,
        "provenance": "verified", "prerequisites": [{"slug": p, "name": cat.name(p)} for p in s.prereqs],
        "dependents": [{"slug": d, "name": cat.name(d)} for d in cat.dependents.get(slug, [])],
        "learning_path": [{"slug": p, "name": cat.name(p)} for p in learning_path(cat, slug)],
        "taxonomy": taxonomy(slug), "career_paths": career_paths(cat, slug),
        "related": [{"slug": r, "name": cat.name(r)} for r in sorted(
            {x for x in cat.skills if x != slug and cat.skills[x].category == s.category} | set(s.prereqs) | set(cat.dependents.get(slug, [])))][:10],
        "docs_url": DOCS_URLS.get(slug),
        "projects": [{"key": p.key, "title": p.title, "difficulty": p.difficulty} for p in cat.projects.values() if slug in p.required or slug in p.gained],
        "jobs": [{"key": j.key, "title": j.title, "company": j.company, "is_demo": True} for j in cat.jobs.values() if slug in j.required or slug in j.preferred],
        "questions": len([q for q in cat.questions.values() if q.skill == slug]),
    }
