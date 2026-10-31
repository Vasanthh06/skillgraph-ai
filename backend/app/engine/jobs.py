"""Job matching and job-description analysis (spec §26-28)."""
from __future__ import annotations

import re

from app.engine.catalog import Catalog, Job, RoleSpec
from app.engine.gap import STRONG, WEAK

EXP_LADDER = {"fresher": 0, "internship": 0, "0-1": 1, "1-3": 2, "3-5": 3, "5+": 4}
W = {"skill": 0.60, "role": 0.20, "experience": 0.10, "location": 0.10}


def _classify(cat: Catalog, scores: dict[str, float], slugs: list[str]) -> tuple[list[str], list[str], list[str]]:
    have = [s for s in slugs if scores.get(s, 0) >= STRONG]
    weak = [s for s in slugs if WEAK <= scores.get(s, 0) < STRONG]
    missing = [s for s in slugs if scores.get(s, 0) < WEAK]
    return have, weak, missing


def _skill_match(scores: dict[str, float], required: list[str], preferred: list[str]) -> float:
    num = den = 0.0
    for slugs, w in ((required, 1.0), (preferred, 0.5)):
        for s in slugs:
            num += w * min(1.0, scores.get(s, 0) / STRONG)
            den += w
    return num / den if den else 0.0


def _experience_match(user_level: str | None, job_level: str) -> float:
    u, j = EXP_LADDER.get(user_level or "fresher", 0), EXP_LADDER.get(job_level, 0)
    return 1.0 if u >= j else max(0.0, 1.0 - 0.4 * (j - u))


def _location_match(user_loc: str | None, job_loc: str) -> float:
    if job_loc.lower() == "remote":
        return 1.0
    if not user_loc:
        return 0.5
    return 1.0 if user_loc.strip().lower() in job_loc.lower() else 0.3


def match_job(cat: Catalog, job: Job, scores: dict[str, float], target: RoleSpec | None, experience: str | None, location: str | None) -> dict:
    req, pref = list(job.required), list(job.preferred)
    skill = _skill_match(scores, req, pref)
    if target is None:
        role = 0.5
    elif job.role == target.name:
        role = 1.0
    else:
        ts = {r.slug for r in target.skills}
        role = 0.7 * len(ts & set(req)) / max(1, len(set(req)))
    exp = _experience_match(experience, job.experience)
    loc = _location_match(location, job.location)
    total = W["skill"] * skill + W["role"] * role + W["experience"] * exp + W["location"] * loc

    have, weak, missing = _classify(cat, scores, req + pref)
    req_cov = round(100 * sum(min(1.0, scores.get(s, 0) / STRONG) for s in req) / max(1, len(req)))
    gap_req = [s for s in req if scores.get(s, 0) < STRONG]
    gap_req.sort(key=lambda s: scores.get(s, 0))
    if gap_req:
        explanation = f"You match {req_cov}% of this role's required skills. Your primary remaining gap is {cat.name(gap_req[0])}."
    else:
        explanation = f"You meet all of this role's required skills ({req_cov}% match)."
    return {
        "key": job.key, "title": job.title, "company": job.company, "location": job.location, "experience": job.experience,
        "is_demo": job.is_demo, "match": round(100 * total),
        "components": {"skills": round(100 * skill), "role": round(100 * role), "experience": round(100 * exp), "location": round(100 * loc)},
        "have": [cat.name(s) for s in have], "weak": [cat.name(s) for s in weak], "missing": [cat.name(s) for s in missing],
        "required_match": req_cov, "explanation": explanation,
        "before_applying": [f"Learn {cat.name(s)} basics" for s in gap_req[:2]],
    }


def rank_jobs(cat, scores, target, experience, location, limit: int | None = None) -> list[dict]:
    out = [match_job(cat, j, scores, target, experience, location) for j in cat.jobs.values()]
    out.sort(key=lambda r: (-r["match"], r["title"]))
    return out[:limit] if limit else out


# ---------------- job description analysis ----------------
_PREFERRED_CUE = re.compile(r"\b(preferred|nice to have|nice-to-have|bonus|a plus|good to have|desirable|optional)\b", re.I)
_REQUIRED_CUE = re.compile(r"\b(requirements?|qualifications?|must have|must-have|required|what you.?ll need|you have)\b", re.I)
_RESP_CUE = re.compile(r"\b(responsibilit|what you.?ll do|your role|duties)\w*", re.I)
_YEARS = re.compile(r"(\d+)\s*(?:\+|-\s*\d+)?\s*(?:years?|yrs?)", re.I)
_EDU = re.compile(r"\b(b\.?tech|b\.?e\.?|b\.?sc|bachelor'?s?|m\.?tech|m\.?sc|master'?s?|mba|ph\.?d|diploma)\b", re.I)


def analyze_jd(cat: Catalog, text: str, scores: dict[str, float]) -> dict:
    required: dict[str, None] = {}
    preferred: dict[str, None] = {}
    responsibilities: list[str] = []
    mode = "required"
    for line in text.splitlines():
        ln = line.strip()
        if not ln:
            continue
        is_heading = len(ln) < 60 and not ln.startswith(("-", "*", "•")) and (ln.endswith(":") or ln.isupper() or ln.istitle())
        if is_heading or _PREFERRED_CUE.search(ln) and len(ln) < 60:
            if _PREFERRED_CUE.search(ln):
                mode = "preferred"
            elif _RESP_CUE.search(ln):
                mode = "responsibilities"
            elif _REQUIRED_CUE.search(ln):
                mode = "required"
        line_mode = "preferred" if (_PREFERRED_CUE.search(ln) and mode != "responsibilities") else mode
        if mode == "responsibilities" and ln.startswith(("-", "*", "•")) and len(responsibilities) < 8:
            responsibilities.append(ln.lstrip("-*• ").strip())
        for slug, _txt, _pos in cat.scan(ln):
            (preferred if line_mode == "preferred" else required).setdefault(slug, None)
    for s in list(preferred):
        if s in required:
            del preferred[s]
    req, pref = list(required), list(preferred)
    years = [int(m.group(1)) for m in _YEARS.finditer(text)]
    have, weak, missing = _classify(cat, scores, req)
    skill = _skill_match(scores, req, pref)
    return {
        "required_skills": [cat.name(s) for s in req], "preferred_skills": [cat.name(s) for s in pref],
        "experience_years": max(years) if years else None,
        "education": sorted({m.group(0) for m in _EDU.finditer(text)}, key=str.lower),
        "responsibilities": responsibilities,
        "match": round(100 * skill), "strong": [cat.name(s) for s in have], "weak": [cat.name(s) for s in weak], "missing": [cat.name(s) for s in missing],
        "recognised_skill_count": len(req) + len(pref),
    }
