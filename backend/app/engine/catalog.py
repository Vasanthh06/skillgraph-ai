from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache

from app.data.jobs_data import JOBS
from app.data.projects_data import PROJECTS
from app.data.questions_data import MCQ, OPEN
from app.data.roles_data import ROLES
from app.data.skills_data import DOCS_URLS, SKILLS, SOFT_SKILLS, TAXONOMY, taxonomy_leaves

_SEP = r"[\s._\-/]+"
# Aliases this short/ambiguous are matched in direct lookups but never scanned for in free text.
_NEVER_SCAN = {"cv"}


def compact(s: str) -> str:
    """'React.js', 'React JS', 'ReactJS' -> 'reactjs'."""
    return re.sub(_SEP, "", s.strip().lower())


@dataclass(frozen=True)
class Skill:
    slug: str
    name: str
    category: str
    difficulty: int
    aliases: tuple[str, ...]
    prereqs: tuple[str, ...]
    description: str


@dataclass(frozen=True)
class RoleSkill:
    slug: str
    importance: float
    required: bool
    group: str


@dataclass(frozen=True)
class RoleSpec:
    name: str
    description: str
    experience: str
    projects: str
    interview: str
    skills: tuple[RoleSkill, ...]
    limited_coverage: bool = False
    is_custom: bool = False
    derived_from: str | None = None  # custom roles borrow requirements from the nearest curated role


@dataclass(frozen=True)
class Project:
    key: str
    title: str
    difficulty: str
    hours: int
    required: tuple[str, ...]
    gained: tuple[str, ...]
    description: str
    expected_output: str
    portfolio_value: str


@dataclass(frozen=True)
class Job:
    key: str
    title: str
    company: str
    location: str
    experience: str
    role: str
    required: tuple[str, ...]
    preferred: tuple[str, ...]
    is_demo: bool = True


@dataclass(frozen=True)
class Question:
    key: str
    category: str
    skill: str | None
    difficulty: str
    text: str
    options: tuple[str, ...] = ()
    answer_index: int | None = None
    explanation: str = ""
    keywords: tuple[str, ...] = ()


@dataclass
class Catalog:
    skills: dict[str, Skill]
    roles: dict[str, RoleSpec]
    projects: dict[str, Project]
    jobs: dict[str, Job]
    questions: dict[str, Question]
    alias_index: dict[str, str] = field(default_factory=dict)
    dependents: dict[str, list[str]] = field(default_factory=dict)
    _scan: list[tuple[re.Pattern, str]] = field(default_factory=list)

    # ---- lookup ----
    def resolve(self, text: str) -> str | None:
        """Normalise a single skill string to a slug (exact, alias-aware)."""
        return self.alias_index.get(compact(text))

    def name(self, slug: str) -> str:
        return self.skills[slug].name if slug in self.skills else slug

    # ---- graph ----
    def all_prereqs(self, slug: str) -> set[str]:
        out: set[str] = set()
        stack = list(self.skills[slug].prereqs)
        while stack:
            s = stack.pop()
            if s not in out:
                out.add(s)
                stack.extend(self.skills[s].prereqs)
        return out

    def all_dependents(self, slug: str) -> set[str]:
        out: set[str] = set()
        stack = list(self.dependents.get(slug, []))
        while stack:
            s = stack.pop()
            if s not in out:
                out.add(s)
                stack.extend(self.dependents.get(s, []))
        return out

    def depth(self, slug: str) -> int:
        pre = self.skills[slug].prereqs
        return 0 if not pre else 1 + max(self.depth(p) for p in pre)

    # ---- text scanning ----
    def scan(self, text: str) -> list[tuple[str, str, int]]:
        """Find skill mentions in free text: [(slug, matched_text, start)].

        Boundary-safe and separator-tolerant. Overlapping matches (e.g. 'React' inside 'React.js')
        are resolved by keeping the longest match at each position.
        """
        raw = []
        for pat, slug in self._scan:
            for m in pat.finditer(text):
                raw.append((m.start(), m.end(), slug, m.group(0)))
        raw.sort(key=lambda h: (h[0], -(h[1] - h[0])))
        out, last_end = [], -1
        for start, end, slug, txt in raw:
            if start < last_end:
                continue
            out.append((slug, txt, start))
            last_end = end
        return out


def _pattern_for(alias: str) -> re.Pattern:
    parts = [re.escape(p) for p in re.split(_SEP, alias.strip().lower()) if p]
    body = r"[\s._\-/]*".join(parts)
    return re.compile(rf"(?<![a-z0-9+#]){body}(?![a-z0-9+#])", re.IGNORECASE)


@lru_cache
def get_catalog() -> Catalog:
    skills = {
        s[0]: Skill(s[0], s[1], s[2], s[3], tuple(s[4]), tuple(s[5]), s[6]) for s in SKILLS
    }
    roles = {}
    for name, d in ROLES.items():
        roles[name] = RoleSpec(
            name=name, description=d["description"], experience=d["experience"], projects=d["projects"],
            interview=d["interview"], limited_coverage=d.get("limited_coverage", False),
            skills=tuple(RoleSkill(s, imp, bool(req), grp) for s, imp, req, grp in d["skills"]),
        )
    projects = {p[0]: Project(p[0], p[1], p[2], p[3], tuple(p[4]), tuple(p[5]), p[6], p[7], p[8]) for p in PROJECTS}
    jobs = {j[0]: Job(j[0], j[1], j[2], j[3], j[4], j[5], tuple(j[6]), tuple(j[7])) for j in JOBS}
    questions: dict[str, Question] = {}
    for i, (sk, diff, q, opts, ans, expl) in enumerate(MCQ):
        k = f"mcq-{i+1}"
        questions[k] = Question(k, "mcq", sk, diff, q, tuple(opts), ans, expl)
    for i, (cat, sk, diff, q, kw) in enumerate(OPEN):
        k = f"{cat}-{i+1}"
        questions[k] = Question(k, cat, sk, diff, q, keywords=tuple(kw))

    cat = Catalog(skills, roles, projects, jobs, questions)
    for s in skills.values():
        for key in {compact(s.name), s.slug.replace("-", ""), *(compact(a) for a in s.aliases)}:
            cat.alias_index.setdefault(key, s.slug)
        for p in s.prereqs:
            cat.dependents.setdefault(p, []).append(s.slug)
        for alias in (s.name, *s.aliases):
            if len(compact(alias)) > 2 and compact(alias) not in _NEVER_SCAN:
                cat._scan.append((_pattern_for(alias), s.slug))
    return cat


__all__ = ["get_catalog", "Catalog", "Skill", "RoleSpec", "RoleSkill", "Project", "Job", "Question", "compact",
           "SOFT_SKILLS", "DOCS_URLS", "TAXONOMY", "taxonomy_leaves"]
