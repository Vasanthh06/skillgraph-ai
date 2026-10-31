"""Skill search and role similarity built on the embedder + index."""
from __future__ import annotations

from functools import lru_cache

from app.engine.catalog import Catalog, get_catalog
from app.ml.embeddings import get_embedder
from app.ml.vector_index import make_index

RELATED_THRESHOLD = 0.30


def _skill_text(cat: Catalog, slug: str) -> str:
    s = cat.skills[slug]
    return f"{s.name} {' '.join(s.aliases)} {s.category}"


@lru_cache
def _skill_index():
    cat, emb = get_catalog(), get_embedder()
    slugs = list(cat.skills)
    idx = make_index(emb.dim)
    idx.add(slugs, emb.embed([_skill_text(cat, s) for s in slugs]))
    return emb, idx


def search(cat: Catalog, query: str, k: int = 6) -> dict:
    """Exact/alias hit first, then name-substring hits, then nearest neighbours (labelled as related)."""
    q = query.strip()
    if not q:
        return {"query": q, "exact": None, "matches": [], "related": [], "backend": None}
    exact = cat.resolve(q)
    ql = q.lower()
    contains = [s for s in cat.skills if ql in cat.skills[s].name.lower() or any(ql in a for a in cat.skills[s].aliases)]
    emb, idx = _skill_index()
    near = [(s, round(sc, 3)) for s, sc in idx.search(emb.embed([q])[0], k + 3) if sc >= RELATED_THRESHOLD]
    matches = ([exact] if exact else []) + [s for s in contains if s != exact]
    related = [{"slug": s, "similarity": sc} for s, sc in near if s not in matches][:k]
    return {"query": q, "exact": exact, "matches": matches[:k], "related": related, "backend": idx.backend, "embedder": emb.name}


def nearest_role(cat: Catalog, text: str) -> tuple[str, float]:
    emb = get_embedder()
    names = list(cat.roles)
    docs = [f"{n} {cat.roles[n].description} " + " ".join(cat.name(r.slug) for r in cat.roles[n].skills) for n in names]
    idx = make_index(emb.dim)
    idx.add(names, emb.embed(docs))
    name, score = idx.search(emb.embed([text])[0], 1)[0]
    return name, score
