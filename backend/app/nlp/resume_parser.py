"""Resume text extraction, structure detection, skill extraction and ATS-style analysis (spec §10, §32, §33).

Pure Python except optional PDF support (pypdf). Heuristics only: it never invents experience, and every
suggestion is phrased as a prompt for the user to add something they genuinely did.
"""
from __future__ import annotations

import io
import re
import zipfile
from dataclasses import dataclass, field
from defusedxml import ElementTree
from defusedxml.common import DefusedXmlException

from app.data.skills_data import SOFT_SKILLS
from app.engine.catalog import Catalog

MAX_TEXT_CHARS = 200_000


class UnsupportedResume(Exception):
    pass


def extract_text(data: bytes, filename: str) -> str:
    name = filename.lower()
    if name.endswith(".txt"):
        text = data.decode("utf-8", errors="replace")
    elif name.endswith(".docx"):
        text = _docx_text(data)
    elif name.endswith(".pdf"):
        text = _pdf_text(data)
    else:
        raise UnsupportedResume("Unsupported file type. Upload a PDF, DOCX or TXT resume.")
    text = text.replace("\x00", "").strip()
    if len(text) < 40:
        raise UnsupportedResume("Couldn't read any text from this file. If it's a scanned image, upload a text-based version.")
    return text[:MAX_TEXT_CHARS]


def _docx_text(data: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            info = z.getinfo("word/document.xml")
            if info.file_size > 2_000_000:
                raise UnsupportedResume("DOCX document XML exceeds the safe parsing limit")
            xml = z.read("word/document.xml")
    except (zipfile.BadZipFile, KeyError):
        raise UnsupportedResume("This DOCX file is damaged or not a valid Word document.")
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    try:
        root = ElementTree.fromstring(xml)
    except (ElementTree.ParseError, DefusedXmlException):
        raise UnsupportedResume("This DOCX contains invalid or unsafe XML") from None
    paras = []
    for p in root.iter("{%s}p" % ns["w"]):
        paras.append("".join(t.text or "" for t in p.iter("{%s}t" % ns["w"])))
    return "\n".join(paras)


def _pdf_text(data: bytes) -> str:
    try:
        from pypdf import PdfReader  # optional dependency
    except ImportError:
        raise UnsupportedResume("PDF parsing needs the 'pypdf' package on the server. Upload DOCX or TXT instead.")
    try:
        reader = PdfReader(io.BytesIO(data))
        return "\n".join((page.extract_text() or "") for page in reader.pages[:12])
    except Exception:
        raise UnsupportedResume("This PDF couldn't be read. Try exporting it again or upload DOCX/TXT.")


# ---------------- structure ----------------
SECTION_NAMES = {
    "summary": r"summary|objective|profile|about me",
    "experience": r"(work |professional )?experience|employment|internships?",
    "projects": r"projects?|academic projects|personal projects",
    "skills": r"(technical )?skills|technologies|tech stack|core competenc\w+",
    "education": r"education|academics?|qualifications?",
    "certifications": r"certifications?|certificates?|courses|licen[cs]es",
    "achievements": r"achievements?|awards?|accomplishments",
}


def split_sections(text: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {"header": []}
    current = "header"
    for line in text.splitlines():
        stripped = line.strip().strip(":").strip()
        matched = None
        if 0 < len(stripped) <= 40:
            for name, pat in SECTION_NAMES.items():
                if re.fullmatch(pat, stripped, re.I):
                    matched = name
                    break
        if matched:
            current = matched
            sections.setdefault(current, [])
        else:
            sections.setdefault(current, []).append(line)
    return {k: "\n".join(v).strip() for k, v in sections.items() if "\n".join(v).strip()}


_DEGREE = re.compile(r"\b(b\.?\s?tech|b\.?e\.?|b\.?sc|bachelor[^\n,;]*|m\.?\s?tech|m\.?sc|master[^\n,;]*|mba|ph\.?d|diploma[^\n,;]*|bca|mca)\b", re.I)
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE = re.compile(r"\+?\d[\d\s().-]{8,16}\d")
_YEARS = re.compile(r"(\d+(?:\.\d+)?)\+?\s+years?", re.I)
_NUMBER = re.compile(r"\d")
_BULLET = re.compile(r"^\s*(?:[-*•▪●]|\d+[.)])\s+")
_WEAK = ("responsible for", "worked on", "helped with", "assisted in", "duties included", "involved in", "participated in")
_STRONG_VERBS = {"built", "designed", "developed", "implemented", "led", "created", "reduced", "increased", "improved", "deployed",
                 "automated", "optimised", "optimized", "launched", "analysed", "analyzed", "trained", "engineered", "delivered", "migrated"}


@dataclass
class ParsedResume:
    text: str
    sections: dict[str, str]
    skills: dict[str, dict]            # slug -> {evidence: listed|applied, mentions, raw: [..]}
    soft_skills: list[str]
    education: list[str]
    certifications: list[str]
    experience_years: float | None
    has_email: bool
    has_phone: bool
    bullets: list[str] = field(default_factory=list)


def _has_phone(text: str) -> bool:
    return any(10 <= sum(c.isdigit() for c in m.group(0)) <= 13 for m in _PHONE.finditer(text))


def parse(cat: Catalog, text: str) -> ParsedResume:
    sections = split_sections(text)
    applied_text = "\n".join(sections.get(k, "") for k in ("experience", "projects", "achievements", "summary"))
    skills_text = sections.get("skills", "")
    skills: dict[str, dict] = {}

    def add(chunk: str, kind: str):
        for slug, raw, _ in cat.scan(chunk):
            e = skills.setdefault(slug, {"evidence": "listed", "mentions": 0, "raw": []})
            e["mentions"] += 1
            if raw not in e["raw"]:
                e["raw"].append(raw)
            if kind == "applied":
                e["evidence"] = "applied"

    add(skills_text, "listed")
    add(applied_text, "applied")
    if not sections.get("experience") and not sections.get("projects") and not skills_text:
        add(text, "listed")  # unstructured resume: everything counts as merely listed

    lower = text.lower()
    soft = sorted({s for s in SOFT_SKILLS if re.search(rf"\b{re.escape(s)}\b", lower)})
    edu = [m.group(0).strip() for m in _DEGREE.finditer(sections.get("education", ""))][:5]
    certs = [ln.strip(" -•*\t") for ln in sections.get("certifications", "").splitlines() if len(ln.strip(" -•*\t")) > 3][:10]
    yrs = [float(m.group(1)) for m in _YEARS.finditer(text)]
    bullets = [_BULLET.sub("", ln).strip() for ln in text.splitlines() if _BULLET.match(ln)]
    return ParsedResume(text, sections, skills, soft, edu, certs, max(yrs) if yrs else None,
                        bool(_EMAIL.search(text)), _has_phone(text), bullets)


def resume_evidence(parsed: ParsedResume) -> dict[str, float]:
    """slug -> 0..100. Listing a skill is weak evidence; using it in a project/job bullet is stronger."""
    out = {}
    for slug, e in parsed.skills.items():
        base = 45.0 if e["evidence"] == "listed" else 70.0
        if e["evidence"] == "applied" and e["mentions"] >= 3:
            base = 80.0
        out[slug] = base
    return out


def role_match(cat: Catalog, parsed: ParsedResume, role) -> dict:
    num = den = 0.0
    missing, found = [], []
    for r in role.skills:
        w = r.importance * (1.0 if r.required else 0.5)
        den += w
        if r.slug in parsed.skills:
            num += w * (1.0 if parsed.skills[r.slug]["evidence"] == "applied" else 0.6)
            found.append(cat.name(r.slug))
        elif r.required:
            missing.append(cat.name(r.slug))
    return {"match": round(100 * num / den) if den else 0, "found": found, "missing_keywords": missing}


def analyze(cat: Catalog, parsed: ParsedResume, role, user_scores: dict[str, float], self_reported_min: float = 40.0) -> dict:
    """ATS-style checks and improvement prompts. Never fabricates experience."""
    checks, tips = [], []

    def check(name, ok, detail):
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    for sec, label in (("experience", "Experience"), ("education", "Education"), ("skills", "Skills"), ("projects", "Projects")):
        present = sec in parsed.sections
        check(f"{label} section", present, "Found." if present else f"No clear '{label}' heading found. ATS parsers look for standard headings.")
    check("Email address", parsed.has_email, "Found." if parsed.has_email else "Add an email address in the header.")
    check("Phone number", parsed.has_phone, "Found." if parsed.has_phone else "Add a phone number in the header.")
    words = len(parsed.text.split())
    check("Length", 150 <= words <= 1100, f"{words} words." + ("" if 150 <= words <= 1100 else " Aim for one page for early career, two at most."))

    bullets = parsed.bullets
    quantified = [b for b in bullets if _NUMBER.search(b)]
    weak = [b for b in bullets if any(b.lower().startswith(w) or w in b.lower()[:40] for w in _WEAK)]
    no_verb = [b for b in bullets if b.split() and b.split()[0].lower().rstrip(",") not in _STRONG_VERBS and b not in weak]
    if bullets:
        check("Measurable results", len(quantified) / len(bullets) >= 0.3, f"{len(quantified)} of {len(bullets)} bullets include a number.")
        if len(quantified) / len(bullets) < 0.3:
            tips.append("Several bullets don't show a result. Where you have a real number (accuracy, time saved, users, rows processed), add it. If you don't have one, describe the concrete outcome instead.")
    else:
        check("Bullet points", False, "No bullet points detected. Describe projects and roles as short bullets starting with an action verb.")
    for b in weak[:3]:
        tips.append(f"Weak phrasing: \"{b[:90]}\". Replace the opener with what you actually did, e.g. \"Built…\", \"Analysed…\", \"Deployed…\".")
    if no_verb and len(no_verb) > len(bullets) / 2:
        tips.append("Most bullets don't open with an action verb. Starting with one (Built, Designed, Improved) makes ownership clear.")

    rm = role_match(cat, parsed, role)
    if rm["missing_keywords"]:
        tips.append("Role keywords not on your resume: " + ", ".join(rm["missing_keywords"][:8]) + ". Add only those you genuinely know.")

    # Skills the user claims but the resume does not evidence
    evidence_gaps = []
    for slug, score in user_scores.items():
        if score >= self_reported_min and slug in cat.skills and slug not in parsed.skills and any(r.slug == slug for r in role.skills):
            evidence_gaps.append({"skill": cat.name(slug), "suggestion": f"You report knowing {cat.name(slug)}, but your resume doesn't show it. Add a project, a measurable result, or relevant experience that demonstrates it."})
    for slug, e in parsed.skills.items():
        if e["evidence"] == "listed" and any(r.slug == slug for r in role.skills) and e["mentions"] == 1:
            evidence_gaps.append({"skill": cat.name(slug), "suggestion": f"{cat.name(slug)} appears only in your skills list. Show it in a project or experience bullet."})

    ats_score = round(100 * sum(1 for c in checks if c["ok"]) / len(checks))
    return {"role_match": rm["match"], "found_keywords": rm["found"], "missing_keywords": rm["missing_keywords"], "ats_score": ats_score,
            "checks": checks, "tips": tips, "evidence_gaps": evidence_gaps[:10]}
