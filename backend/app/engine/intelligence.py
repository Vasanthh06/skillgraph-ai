"""Integrated skill intelligence: bottleneck detection, confidence calibration and spaced recall.

All three features read the SAME derived state the rest of SkillGraph already computes (knowledge
estimates, the role gap, the roadmap) plus the user's attempt/learning history. Everything here is a
pure, deterministic function of that state - no AI-generated scores, no invented prerequisite edges -
so it can be unit-tested without a database and every number can be explained to the user.

Formulas (documented for the UI and README)
--------------------------------------------
Bottleneck score (0..100) for a not-yet-strong skill that other unmet skills depend on::

    weakness             = 1 - min(score, TARGET) / TARGET          (TARGET = 70, from gap.py)
    downstream_count_n   = min(1, unmet_downstream_count / 6)
    downstream_imp_n     = min(1, sum(importance of unmet downstream) / 3)
    current_stage        = 1.0  the skill is (or blocks) the current roadmap step
                           0.5  it blocks one of the next available/current steps
                           0.0  otherwise
    score = 100 * (0.35*weakness + 0.30*downstream_imp_n + 0.15*downstream_count_n
                   + 0.20*current_stage)

Confidence calibration compares the user's own rating with demonstrated performance on objectively
scored questions (MCQs = exact; technical/scenario = keyword coverage, weighted 0.6; self-rated
answers never count). Demonstrated performance is a recency-weighted mean with a 90-day half-life.
A label is only produced with enough fresh evidence (>= MIN_OBJECTIVE_ATTEMPTS attempts and the
latest within MAX_EVIDENCE_AGE_DAYS); otherwise the status is honestly ``insufficient_evidence``.

Spaced recall uses fixed intervals [1, 3, 7, 14, 30, 60] days. A strong recall (>= 80%) advances a
stage, a partial one (50-79%) halves the current interval, a weak one (< 50%) returns to 1 day and
points back at the learning material. A skill with no recent evidence is flagged for a *knowledge
check*, never assumed forgotten.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.data.skills_data import taxonomy_leaves
from app.engine import gap as G
from app.engine.catalog import Catalog
from app.engine.knowledge import SELF_LEVEL_SCORE, UserState, self_score

# ---- configurable policy (single place to tune all three features) ----
BOTTLENECK_WEIGHTS = {"weakness": 0.35, "downstream_importance": 0.30, "downstream_count": 0.15, "current_stage": 0.20}
DOWNSTREAM_COUNT_SATURATION = 6.0
DOWNSTREAM_IMPORTANCE_SATURATION = 3.0

CALIBRATION_BAND = 15.0            # |self - demonstrated| <= 15 points counts as aligned
MIN_OBJECTIVE_ATTEMPTS = 3
MAX_EVIDENCE_AGE_DAYS = 90
RECENCY_HALF_LIFE_DAYS = 90.0
OBJECTIVE_WEIGHTS = {"mcq": 1.0, "technical": 0.6, "scenario": 0.6}
FRESH_DAYS = 30

REVIEW_INTERVALS = [1, 3, 7, 14, 30, 60]
STRONG_RECALL = 80.0
PARTIAL_RECALL = 50.0
UPCOMING_WINDOW_DAYS = 7

CALIBRATION_METHOD = (
    "Your estimate blends all of your evidence (resume, self-assessment, quizzes, projects, learning). "
    "Calibration compares only your own rating with objectively scored questions - recent answers count "
    "more (90-day half-life) - and needs at least 3 recent objective answers before it labels your "
    "confidence aligned, higher or lower than demonstrated.")


def as_utc(dt: datetime | None) -> datetime | None:
    """SQLite returns naive datetimes for timezone columns; treat them as UTC so ages never crash."""
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def iso(dt: datetime | None) -> str | None:
    dt = as_utc(dt)
    return dt.isoformat() if dt else None


def _age_days(dt: datetime | None, now: datetime) -> int | None:
    dt = as_utc(dt)
    return max(0, (now - dt).days) if dt else None


def _recency_weight(at: datetime | None, now: datetime) -> float:
    age = _age_days(at, now) or 0
    return 0.5 ** (age / RECENCY_HALF_LIFE_DAYS)


def weighted_performance(attempts: list[dict], now: datetime, shrink: bool = False) -> float | None:
    """Recency-weighted mean of objectively scored attempts (optionally shrunk toward neutral with a
    one-attempt prior, so a single answer can't swing the knowledge model's assessment source)."""
    num = den = 0.0
    for a in attempts:
        w = OBJECTIVE_WEIGHTS.get(a.get("category", ""), 0.0) * _recency_weight(a.get("created_at"), now)
        if w <= 0 or a.get("score") is None:
            continue
        num += w * float(a["score"])
        den += w
    if den == 0:
        return None
    if shrink:
        num, den = num + 50.0, den + 1.0
    return round(num / den, 1)


# ---------------------------------------------------------------- calibration
def calibrate(slug: str, *, state: UserState, estimate, attempts: list[dict], available_objective: int,
              latest_evidence_at: datetime | None, now: datetime) -> dict:
    objective = [a for a in attempts if a.get("objective")]
    objective.sort(key=lambda a: (as_utc(a.get("created_at")) or now, a.get("id", 0)))
    recent = objective[-8:]
    demonstrated = weighted_performance(recent, now)
    latest = objective[-1] if objective else None
    latest_at = as_utc(latest.get("created_at")) if latest else None
    latest_age = _age_days(latest_at, now)

    explicit = state.confidence_ratings.get(slug)
    self_value = explicit if explicit is not None else self_score(state.self_levels.get(slug), state.checklists.get(slug))
    self_source = ("confidence_rating" if explicit is not None
                   else "self_level" if self_value is not None else None)

    missed: list[str] = []
    for a in reversed(objective):
        for t in a.get("missed_topics") or []:
            if t and t not in missed:
                missed.append(str(t)[:160])
        if len(missed) >= 6:
            break
    leaves = taxonomy_leaves(slug)
    checked = state.checklists.get(slug, {})
    unchecked = [x for x in leaves if not checked.get(x)][:8] if checked else []
    unique_topics = {a.get("key") for a in objective if a.get("key")}
    coverage = round(min(1.0, len(unique_topics) / available_objective), 2) if available_objective else 0.0

    age_any = _age_days(latest_evidence_at, now)
    freshness = ("unknown" if age_any is None else "fresh" if age_any <= FRESH_DAYS
                 else "recent" if age_any <= MAX_EVIDENCE_AGE_DAYS else "older")

    reason = None
    if self_value is None:
        status, reason = "insufficient_evidence", "You have not rated this skill yet."
    elif not objective:
        status, reason = "insufficient_evidence", "There is no scored practice for this skill yet."
    elif len(objective) < MIN_OBJECTIVE_ATTEMPTS:
        status, reason = "insufficient_evidence", f"Only {len(objective)} scored answer(s) so far; {MIN_OBJECTIVE_ATTEMPTS} are needed before confidence is labelled."
    elif latest_age is not None and latest_age > MAX_EVIDENCE_AGE_DAYS:
        status, reason = "insufficient_evidence", f"The latest scored practice is {latest_age} days old, so a fresh check is needed."
    else:
        delta = float(self_value) - float(demonstrated)  # type: ignore[arg-type]
        status = "aligned" if abs(delta) <= CALIBRATION_BAND else "higher_than_demonstrated" if delta > 0 else "lower_than_demonstrated"
        reason = {"aligned": "Your rating and your recent scored answers are close.",
                  "higher_than_demonstrated": "Your rating is higher than recent scored answers so far. The result comes from a small question set, so revisit the missed topics and check again.",
                  "lower_than_demonstrated": "Your recent scored answers are stronger than your rating. Your estimate still weighs all evidence sources, not this check alone."}[status]

    delta = round(float(self_value) - float(demonstrated), 1) if self_value is not None and demonstrated is not None else None
    action = ({"label": "Rate this skill", "route": "/assessment"} if self_value is None
              else {"label": "Take a quick knowledge check", "route": f"/learn?skill={slug}&check=calibration"} if status == "insufficient_evidence"
              else {"label": "Revisit the missed topics", "route": f"/learn?skill={slug}"} if status == "higher_than_demonstrated" and missed
              else {"label": "Open learning resources", "route": f"/learn?skill={slug}"} if status == "higher_than_demonstrated"
              else {"label": "Continue on your roadmap", "route": "/roadmap"})
    return {
        "slug": slug, "status": status, "reason": reason, "action": action, "method": CALIBRATION_METHOD,
        "estimate_score": round(estimate.score) if estimate else 0,
        "estimate_level": estimate.level if estimate else "none",
        "estimate_confidence": estimate.confidence if estimate else 0.0,
        "sources": estimate.sources if estimate else {},
        "self_rating": round(float(self_value)) if self_value is not None else None,
        "self_source": self_source,
        "self_level": state.self_levels.get(slug),
        "self_level_score": SELF_LEVEL_SCORE.get(state.self_levels.get(slug, "")),
        "demonstrated_score": round(demonstrated) if demonstrated is not None else None,
        "difference": round(delta) if delta is not None else None,
        "objective_attempts": len(objective), "attempts_needed": MIN_OBJECTIVE_ATTEMPTS,
        "topic_coverage": coverage, "available_questions": available_objective,
        "latest_result": ({"score": round(float(latest["score"])), "at": iso(latest_at), "age_days": latest_age,
                           "topic": latest.get("topic"), "correct": latest.get("correct")} if latest else None),
        "missed_topics": missed[:6], "unchecked_topics": unchecked,
        "evidence_freshness": freshness, "evidence_age_days": age_any, "last_evidence_at": iso(latest_evidence_at),
    }


# ---------------------------------------------------------------- bottleneck detection
def detect_bottlenecks(cat: Catalog, gap, nodes, *, limit: int = 5) -> list[dict]:
    if not gap:
        return []
    items = {i.slug: i for i in gap.items}
    current = next((n.slug for n in nodes if n.status == "current"), None)
    near_stage = {n.slug for n in nodes if n.status in ("current", "available")} | set(gap.order[:3])
    out = []
    w = BOTTLENECK_WEIGHTS
    for it in gap.items:
        if it.status == "strong" or it.downstream_count == 0:
            continue
        downstream = sorted(it.unlocks, key=lambda s: (-items[s].importance, s))
        weakness = 1.0 - min(it.score, G.TARGET) / G.TARGET
        count_n = min(1.0, it.downstream_count / DOWNSTREAM_COUNT_SATURATION)
        imp_n = min(1.0, it.downstream_importance / DOWNSTREAM_IMPORTANCE_SATURATION)
        blocks_current = bool(current) and (it.slug == current or it.slug in cat.all_prereqs(current))
        blocks_near = any(it.slug == s or it.slug in cat.all_prereqs(s) for s in near_stage)
        stage = 1.0 if blocks_current else 0.5 if blocks_near else 0.0
        score = round(100 * (w["weakness"] * weakness + w["downstream_importance"] * imp_n
                             + w["downstream_count"] * count_n + w["current_stage"] * stage), 1)
        names = [cat.name(s) for s in downstream[:3]]
        why = (f"{it.name} is at {round(it.score)}% and {it.downstream_count} skill(s) that still need work build on it"
               f" ({', '.join(names)}). Strengthening it makes those steps easier to start and finish.")
        if blocks_current and current and it.slug != current:
            why += f" It is also holding up your current step, {cat.name(current)}."
        out.append({
            "slug": it.slug, "name": it.name, "bottleneck_score": score, "priority": it.priority,
            "current_score": round(it.score), "status": it.status, "supporting": it.supporting,
            "downstream_count": it.downstream_count, "blocked_downstream": [{"slug": s, "name": cat.name(s)} for s in downstream[:6]],
            "components": {"weakness": round(weakness, 2), "downstream_count": round(count_n, 2),
                           "downstream_importance": round(imp_n, 2), "current_stage": stage},
            "weights": dict(w), "why": why, "is_current_stage": stage > 0,
            "action": {"label": f"Strengthen {it.name} first", "route": f"/learn?skill={it.slug}"},
        })
    out.sort(key=lambda b: (-b["bottleneck_score"], b["slug"]))
    return out[:limit]


# ---------------------------------------------------------------- spaced recall
def next_stage_and_interval(stage: int, score: float, current_interval: float | None = None) -> tuple[int, int, str, str]:
    """One recall outcome -> (new stage, days until the next review, result label, plain-English reason)."""
    stage = max(0, min(int(stage or 0), len(REVIEW_INTERVALS) - 1))
    if score >= STRONG_RECALL:
        new_stage = min(stage + 1, len(REVIEW_INTERVALS) - 1)
        return new_stage, REVIEW_INTERVALS[new_stage], "strong", "Strong recall, so the next check is further away."
    if score >= PARTIAL_RECALL:
        current = float(current_interval or REVIEW_INTERVALS[stage])
        days = max(1, round(current / 2))
        return stage, days, "partial", "Partial recall, so the next check comes sooner and the missed topics are worth one more look."
    return 0, REVIEW_INTERVALS[0], "weak", "Weak recall, so this returns to a short cycle - revisit the learning material before the next check."


def review_entry(slug: str, name: str, *, schedule: dict | None, learned_at: datetime | None,
                 calibration: dict, bottleneck: dict | None, now: datetime) -> dict | None:
    """Merged view of a persisted schedule (if any) and the learning completion that created it."""
    if schedule is None and learned_at is None:
        return None
    learned = as_utc((schedule or {}).get("learned_at") or learned_at)
    if schedule and schedule.get("next_review_at"):
        nxt = as_utc(schedule["next_review_at"])
        interval, stage = float(schedule.get("interval_days") or 1.0), int(schedule.get("review_stage") or 0)
        count, success = int(schedule.get("review_count") or 0), int(schedule.get("successful_reviews") or 0)
        last_score, last_result = schedule.get("last_score"), schedule.get("last_result")
        last_reviewed = as_utc(schedule.get("last_reviewed_at"))
        weak = list(schedule.get("weak_topics") or []) or calibration.get("missed_topics", [])
    elif learned:
        nxt, interval, stage, count, success = learned + timedelta(days=REVIEW_INTERVALS[0]), float(REVIEW_INTERVALS[0]), 0, 0, 0
        last_score = last_result = last_reviewed = None
        weak = calibration.get("missed_topics", [])
    else:
        return None
    days = (nxt.date() - now.date()).days
    status = "overdue" if days < 0 else "due" if days == 0 else "upcoming" if days <= UPCOMING_WINDOW_DAYS else "scheduled"
    # No objective evidence yet (or only old evidence): this is a check-in, not a verdict of forgetting.
    latest_age = (calibration.get("latest_result") or {}).get("age_days")
    diagnostic = calibration.get("objective_attempts", 0) == 0 or (latest_age is not None and latest_age > MAX_EVIDENCE_AGE_DAYS)
    label = {"overdue": f"Overdue by {abs(days)} day(s)", "due": "Due today",
             "upcoming": f"Due in {days} day(s)", "scheduled": f"Scheduled in {days} day(s)"}[status]
    return {
        "slug": slug, "name": name, "status": status, "status_label": label, "days_until": days,
        "diagnostic": bool(diagnostic),
        "reason": ("We don't assume this has been forgotten - a short check will show what is still solid."
                   if diagnostic else "A short recall check keeps this skill usable instead of only marked complete."),
        "learned_at": iso(learned), "last_reviewed_at": iso(last_reviewed), "next_review_at": iso(nxt),
        "interval_days": interval, "review_stage": stage, "review_count": count, "successful_reviews": success,
        "last_score": round(last_score) if last_score is not None else None, "last_result": last_result,
        "weak_topics": weak[:6], "estimated_minutes": 5 + min(10, 2 * len(weak[:5])),
        "bottleneck_score": bottleneck.get("bottleneck_score") if bottleneck else None,
        "action": {"label": "Start knowledge check" if diagnostic else "Start recall check",
                   "route": f"/learn?skill={slug}&check=recall"},
        "intervals_days": list(REVIEW_INTERVALS),
    }


# ---------------------------------------------------------------- one shared derived view
def build_intelligence(cat: Catalog, *, state: UserState, estimates: dict, gap, nodes,
                       attempt_details: list[dict], learning_events: dict[str, dict],
                       schedules: dict[str, dict], evidence_dates: dict[str, datetime],
                       now: datetime | None = None) -> dict:
    """The single bottleneck + calibration + recall view every page renders from."""
    now = as_utc(now) or datetime.now(timezone.utc)
    by_attempt: dict[str, list[dict]] = {}
    for a in attempt_details:
        if a.get("slug"):
            by_attempt.setdefault(a["slug"], []).append(a)
    available: dict[str, int] = {}
    for q in cat.questions.values():
        if q.skill and q.category in OBJECTIVE_WEIGHTS and (q.category == "mcq" or q.keywords):
            available[q.skill] = available.get(q.skill, 0) + 1

    slugs = set(estimates) | set(state.self_levels) | set(state.confidence_ratings) | set(by_attempt) \
        | set(learning_events) | set(schedules)
    if gap:
        slugs |= {i.slug for i in gap.items}
    calibrations = {s: calibrate(s, state=state, estimate=estimates.get(s), attempts=by_attempt.get(s, []),
                                  available_objective=available.get(s, 0),
                                  latest_evidence_at=evidence_dates.get(s), now=now)
                    for s in sorted(slugs) if s in cat.skills}
    bottlenecks = detect_bottlenecks(cat, gap, nodes)
    bottleneck_by = {b["slug"]: b for b in bottlenecks}

    reviews = {}
    for s in sorted(set(learning_events) | set(schedules)):
        if s not in cat.skills:
            continue
        entry = review_entry(s, cat.name(s), schedule=schedules.get(s),
                             learned_at=(learning_events.get(s) or {}).get("at"),
                             calibration=calibrations.get(s) or {}, bottleneck=bottleneck_by.get(s), now=now)
        if entry:
            reviews[s] = entry

    due = sorted((r for r in reviews.values() if r["status"] in ("overdue", "due")),
                 key=lambda r: (r["days_until"], -(r.get("bottleneck_score") or 0), r["slug"]))
    upcoming = sorted((r for r in reviews.values() if r["status"] in ("upcoming", "scheduled")),
                      key=lambda r: (r["days_until"], r["slug"]))
    by_skill = {s: {"slug": s, "name": cat.name(s), "calibration": calibrations.get(s),
                    "bottleneck": bottleneck_by.get(s), "review": reviews.get(s)} for s in sorted(calibrations)}
    counts: dict[str, int] = {}
    for c in calibrations.values():
        counts[c["status"]] = counts.get(c["status"], 0) + 1
    return {
        "methodology": {
            "bottleneck": {"weights": dict(BOTTLENECK_WEIGHTS), "target_score": G.TARGET,
                           "note": "Deterministic: weakness + unmet downstream count/importance + whether the skill blocks the current roadmap stage. Uses only curated prerequisite edges."},
            "calibration": CALIBRATION_METHOD,
            "recall": {"intervals_days": list(REVIEW_INTERVALS), "strong_at_or_above": STRONG_RECALL,
                       "partial_at_or_above": PARTIAL_RECALL,
                       "note": "Strong recall advances one interval, partial halves it, weak returns to 1 day. A due review never reopens a completed milestone."},
        },
        "bottlenecks": bottlenecks, "top_bottleneck": bottlenecks[0] if bottlenecks else None,
        "calibrations": calibrations, "calibration_summary": counts,
        "reviews": reviews, "due_reviews": due, "upcoming_reviews": upcoming,
        "review_summary": {"due": sum(1 for r in reviews.values() if r["status"] == "due"),
                           "overdue": sum(1 for r in reviews.values() if r["status"] == "overdue"),
                           "upcoming": sum(1 for r in reviews.values() if r["status"] in ("upcoming", "scheduled")),
                           "total": len(reviews)},
        "by_skill": by_skill,
    }
