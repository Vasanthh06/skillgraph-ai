import { useEffect, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { Bar, Card, EmptyState, ErrorNote, Tag } from "./ui";
import { useAction } from "../hooks/useApi";
import { http } from "../services/api";
import type { Json } from "../types/api";

/**
 * Contextual bottleneck / calibration / recall panels. Every value comes from the backend's single
 * derived `intelligence` payload - this file only presents it, inside the existing pages.
 */

export const CAL_LABEL: Record<string, string> = {
  aligned: "Confidence looks aligned",
  higher_than_demonstrated: "Rating is higher than recent practice",
  lower_than_demonstrated: "Practice is stronger than your rating",
  insufficient_evidence: "Needs more evidence",
};

const CAL_TONE: Record<string, "plain" | "warn" | "good" | "demo"> = {
  aligned: "good", higher_than_demonstrated: "demo", lower_than_demonstrated: "good", insufficient_evidence: "plain",
};

export const REVIEW_LABEL: Record<string, string> = {
  overdue: "Review overdue", due: "Review due today", upcoming: "Review coming up", scheduled: "Review scheduled",
};

export function fmtDate(v?: string | null): string {
  if (!v) return "—";
  const d = new Date(v);
  return Number.isNaN(d.getTime()) ? "—" : d.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}

export function CalibrationBadge({ cal }: { cal?: Json | null }) {
  if (!cal) return <Tag>Needs more evidence</Tag>;
  return <Tag tone={CAL_TONE[cal.status] ?? "plain"}>{CAL_LABEL[cal.status] ?? cal.status}</Tag>;
}

export function ReviewBadge({ review }: { review?: Json | null }) {
  if (!review) return null;
  const tone = review.status === "overdue" ? "warn" : review.status === "due" ? "demo" : "plain";
  return <Tag tone={tone}>{review.status_label}</Tag>;
}

export function BottleneckCard({ bottleneck }: { bottleneck?: Json | null }) {
  if (!bottleneck) {
    return (
      <Card>
        <h3 className="text-base font-bold">Biggest bottleneck</h3>
        <p className="mt-1 text-sm text-ink-soft">No single foundational skill is holding back several later skills right now. Your roadmap order follows prerequisites, career importance and readiness.</p>
      </Card>
    );
  }
  const c = bottleneck.components ?? {};
  return (
    <Card>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-glow-cyan">Biggest bottleneck</p>
          <h3 className="mt-1 text-lg font-bold">
            <Link to={`/skill-graph?sel=${bottleneck.slug}`} className="hover:underline">{bottleneck.name}</Link>
          </h3>
        </div>
        <Tag tone="demo">Impact {Math.round(bottleneck.bottleneck_score)}/100</Tag>
      </div>
      <div className="mt-2 max-w-sm"><Bar value={bottleneck.current_score} label={`${bottleneck.name} current evidence`} /></div>
      <p className="mt-2 text-sm text-ink-soft">{bottleneck.why}</p>
      {bottleneck.blocked_downstream?.length > 0 && (
        <p className="mt-2 text-sm"><span className="font-medium">Unlocks progress in:</span>{" "}
          {bottleneck.blocked_downstream.map((d: Json, i: number) => (
            <span key={d.slug}>{i > 0 && ", "}<Link to={`/skill-graph?sel=${d.slug}`} className="text-route underline">{d.name}</Link></span>
          ))}
        </p>
      )}
      <details className="mt-3 text-xs text-ink-faint">
        <summary className="cursor-pointer text-ink-soft">How this priority is calculated</summary>
        <p className="mt-1">A fixed formula over your own evidence: how far the skill is from the target, how many unfinished
          skills depend on it, how important those skills are for your role, and whether it blocks your current roadmap step.</p>
        <ul className="mt-1 list-disc pl-4">
          <li>Room to grow: {Math.round((c.weakness ?? 0) * 100)}%</li>
          <li>Downstream importance: {Math.round((c.downstream_importance ?? 0) * 100)}%</li>
          <li>Skills waiting on it: {bottleneck.downstream_count}</li>
          <li>Blocks your current stage: {bottleneck.is_current_stage ? "yes" : "not directly"}</li>
        </ul>
      </details>
      <Link to={bottleneck.action.route} className="btn mt-4">{bottleneck.action.label} →</Link>
    </Card>
  );
}

export function ReviewList({ reviews, title = "Due for review" }: { reviews?: Json[]; title?: string }) {
  const rows = reviews ?? [];
  return (
    <Card>
      <div className="mb-2 flex items-center justify-between gap-2">
        <h3 className="text-base font-bold">{title}</h3>
        <span className="text-sm text-ink-faint">{rows.length}</span>
      </div>
      {rows.length === 0 ? (
        <p className="text-sm text-ink-faint">Nothing is due. Finishing a learning activity automatically schedules a short recall check.</p>
      ) : (
        <ul className="divide-y divide-mist">
          {rows.map((r) => (
            <li key={r.slug} className="py-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <Link to={`/skill-graph?sel=${r.slug}`} className="font-medium hover:underline">{r.name}</Link>
                <ReviewBadge review={r} />
              </div>
              <p className="mt-1 text-sm text-ink-soft">{r.diagnostic ? "Knowledge check" : "Recall check"} · about {r.estimated_minutes} min · next {fmtDate(r.next_review_at)}</p>
              {r.weak_topics?.length > 0 && <p className="mt-1 text-xs text-ink-faint">Worth revisiting: {r.weak_topics.join("; ")}</p>}
              <Link to={r.action.route} className="btn-quiet mt-2 px-3 py-1 text-sm">{r.action.label} →</Link>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

function StatRow({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="grid gap-1 border-b border-mist/60 py-2 last:border-0 sm:grid-cols-[11rem_1fr]">
      <dt className="text-sm font-medium text-ink-faint">{label}</dt>
      <dd className="text-sm">{children}</dd>
    </div>
  );
}

export function CalibrationPanel({ cal }: { cal?: Json | null }) {
  if (!cal) return <EmptyState title="Needs more evidence">Rate this skill or answer a few scored questions and the comparison will appear here.</EmptyState>;
  const latest = cal.latest_result;
  return (
    <div>
      <div className="flex flex-wrap items-center gap-2"><CalibrationBadge cal={cal} /><span className="text-xs text-ink-faint">Based on {cal.objective_attempts} scored answer(s)</span></div>
      <p className="mt-2 text-sm text-ink-soft">{cal.reason}</p>
      <dl className="mt-2">
        <StatRow label="System estimate">{cal.estimate_score}% ({cal.estimate_level}) — blended from all your evidence</StatRow>
        <StatRow label="Your rating">{cal.self_rating === null ? "Not recorded yet" : `${cal.self_rating}%${cal.self_source === "self_level" ? ` (from your ${String(cal.self_level ?? "").replace("_", " ")} level)` : ""}`}</StatRow>
        <StatRow label="Recent scored practice">{cal.demonstrated_score === null ? "No scored practice yet" : `${cal.demonstrated_score}% across recent objective questions`}</StatRow>
        <StatRow label="Latest result">{latest ? `${latest.score}% · ${fmtDate(latest.at)} (${latest.age_days} day(s) ago)` : "None yet"}</StatRow>
        <StatRow label="Evidence freshness">{cal.evidence_freshness === "unknown" ? "No dated evidence yet" : `${cal.evidence_freshness} · latest ${fmtDate(cal.last_evidence_at)}`}</StatRow>
        <StatRow label="Question coverage">{cal.available_questions ? `${Math.round((cal.topic_coverage ?? 0) * 100)}% of the available scored questions tried` : "No scored question bank for this skill yet"}</StatRow>
      </dl>
      {cal.missed_topics?.length > 0 && (
        <div className="mt-2"><p className="text-sm font-medium">Topics to revisit</p>
          <ul className="mt-1 list-disc pl-5 text-sm text-ink-soft">{cal.missed_topics.map((t: string) => <li key={t}>{t}</li>)}</ul></div>
      )}
      {cal.unchecked_topics?.length > 0 && <p className="mt-2 text-xs text-ink-faint">Not ticked in your checklist yet: {cal.unchecked_topics.join(", ")}</p>}
      <p className="mt-3 text-xs text-ink-faint">A short quiz is one signal, not a final verdict. Your estimate still weighs projects, learning and other evidence.</p>
      {cal.action && <Link to={cal.action.route} className="btn-quiet mt-3 px-3 py-1 text-sm">{cal.action.label} →</Link>}
    </div>
  );
}

export function ReviewPanel({ review }: { review?: Json | null }) {
  if (!review) return <p className="text-sm text-ink-faint">No review is scheduled yet. Mark a roadmap step or learning resource complete and spaced recall checks will start automatically.</p>;
  return (
    <div>
      <div className="flex flex-wrap items-center gap-2"><ReviewBadge review={review} />{review.diagnostic && <Tag>Knowledge check, not assumed forgotten</Tag>}</div>
      <dl className="mt-2">
        <StatRow label="Learned">{fmtDate(review.learned_at)}</StatRow>
        <StatRow label="Last review">{review.last_reviewed_at ? `${fmtDate(review.last_reviewed_at)}${review.last_score !== null ? ` · ${review.last_score}%` : ""}` : "Not reviewed yet"}</StatRow>
        <StatRow label="Next review">{fmtDate(review.next_review_at)} · every {review.interval_days} day(s) at the current stage</StatRow>
        <StatRow label="Reviews so far">{review.review_count} ({review.successful_reviews} strong)</StatRow>
      </dl>
      {review.weak_topics?.length > 0 && <p className="mt-2 text-sm text-ink-soft">Focus next time: {review.weak_topics.join("; ")}</p>}
      <p className="mt-2 text-xs text-ink-faint">A due review never reopens a completed milestone — it only checks that the skill is still usable.</p>
      <Link to={review.action.route} className="btn-quiet mt-3 px-3 py-1 text-sm">{review.action.label} →</Link>
    </div>
  );
}

export function KnowledgeCheckPanel({ skill, skillName, purpose = "calibration", autoStart = false }:
  { skill: string; skillName: string; purpose?: "calibration" | "recall"; autoStart?: boolean }) {
  const [session, setSession] = useState<Json | null>(null);
  const [answers, setAnswers] = useState<Record<string, { choice?: number; answer?: string }>>({});
  const [result, setResult] = useState<Json | null>(null);
  const start = useAction(() => http.post<Json>("/interview/check/start", { skill, purpose, count: 3 }));
  const submit = useAction((body: Json) => http.post<Json>("/interview/check/submit", body), "Saved. Your evidence, confidence comparison and review schedule are up to date.");
  const begin = () => start.mutate(undefined, { onSuccess: (r) => { setSession(r); setAnswers({}); setResult(null); } });
  // Starting a check writes nothing, so letting this run on mount (twice under dev StrictMode) is
  // harmless - and safer than a ref guard, whose first mutation can be stranded by the remount.
  useEffect(() => {
    if (autoStart) begin();
  }, [autoStart, skill, purpose]); // eslint-disable-line react-hooks/exhaustive-deps

  const qs: Json[] = session?.questions ?? [];
  const complete = qs.length > 0 && qs.every((q) => q.category === "mcq" ? answers[q.key]?.choice !== undefined : (answers[q.key]?.answer ?? "").trim().length > 0);
  const send = () => submit.mutate(
    { skill, purpose, session_id: session.session_id, answers: qs.map((q) => ({ question_key: q.key, choice: answers[q.key]?.choice ?? null, answer: answers[q.key]?.answer ?? null })) },
    { onSuccess: (r) => setResult(r) });

  return (
    <Card>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="text-base font-bold">{purpose === "recall" ? "Recall check" : "Knowledge check"} · {skillName}</h3>
          <p className="mt-1 text-sm text-ink-soft">A few scored questions. The result updates your evidence and confidence comparison{purpose === "recall" ? " and sets the next review date" : ""} — it is blended with your other evidence, not treated as a final verdict.</p>
        </div>
        {!session && <button type="button" className="btn" disabled={start.isPending} onClick={begin}>{start.isPending ? "Preparing…" : "Start check"}</button>}
      </div>
      {start.error && <div className="mt-3"><ErrorNote error={start.error} /></div>}
      {session && !result && (
        <div className="mt-4 space-y-5">
          {qs.map((q, qi) => (
            <fieldset key={q.key}>
              <legend className="font-medium">{qi + 1}. {q.text}</legend>
              {q.category === "mcq" ? (
                <div className="mt-2 space-y-2">
                  {q.options.map((o: string, i: number) => (
                    <label key={i} className="flex items-center gap-2 rounded-md border border-mist p-2 text-sm">
                      <input type="radio" name={q.key} checked={answers[q.key]?.choice === i}
                        onChange={() => setAnswers((p) => ({ ...p, [q.key]: { choice: i } }))} />{o}
                    </label>
                  ))}
                </div>
              ) : (
                <>
                  <label htmlFor={`check-${q.key}`} className="label mt-2">Your answer (scored by key ideas covered)</label>
                  <textarea id={`check-${q.key}`} className="field h-24" value={answers[q.key]?.answer ?? ""}
                    onChange={(e) => setAnswers((p) => ({ ...p, [q.key]: { answer: e.target.value } }))} />
                </>
              )}
            </fieldset>
          ))}
          {submit.error && <ErrorNote error={submit.error} />}
          <button type="button" className="btn" disabled={!complete || submit.isPending} onClick={send}>{submit.isPending ? "Scoring…" : "Submit check"}</button>
          {!complete && <span className="ml-3 text-xs text-ink-faint">Answer every question to submit.</span>}
        </div>
      )}
      {result && (
        <div className="mt-4" role="status">
          <p className="font-display text-3xl font-bold">{Math.round(result.score)}%</p>
          <p className="text-sm text-ink-soft">{result.correct} of {result.total} question(s) at a solid level.</p>
          <ul className="mt-3 space-y-2 text-sm">
            {result.results.map((r: Json, i: number) => (
              <li key={r.key} className="rounded-md border border-mist p-2">
                <b>Question {i + 1}: {Math.round(r.score)}%</b>
                {r.explanation && <span> — {r.explanation}</span>}
                {r.consider_mentioning?.length > 0 && <span> Consider mentioning: {r.consider_mentioning.join(", ")}.</span>}
              </li>
            ))}
          </ul>
          {result.schedule && <p className="mt-3 text-sm">{result.schedule.reason} <b>Next review: {fmtDate(result.schedule.next_review_at)}</b></p>}
          {result.intelligence?.calibration && <div className="mt-3"><CalibrationBadge cal={result.intelligence.calibration} /><p className="mt-1 text-sm text-ink-soft">{result.intelligence.calibration.reason}</p></div>}
          <div className="mt-4 flex flex-wrap gap-2">
            <button type="button" className="btn-quiet px-3 py-1 text-sm" onClick={() => { setSession(null); setResult(null); }}>Close check</button>
            <Link to={`/skill-graph?sel=${skill}`} className="btn-quiet px-3 py-1 text-sm">See it in your Skill Graph</Link>
          </div>
        </div>
      )}
    </Card>
  );
}
