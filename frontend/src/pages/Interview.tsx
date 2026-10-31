import { useState } from "react";
import { useEffect, useRef } from "react";
import { useLocation, useSearchParams } from "react-router-dom";
import { Bar, Card, DemoTag, ErrorNote, Loading, PageTitle, Section, Tag, pct } from "../components/ui";
import { BottleneckCard, CalibrationBadge, ReviewList } from "../components/IntelligencePanels";
import { useAction, useGet } from "../hooks/useApi";
import { http } from "../services/api";
import type { Json } from "../types/api";

const LABEL: Record<string, string> = { technical: "Technical", coding: "Coding", mcq: "MCQs", scenario: "Scenario", behavioral: "Behavioral", project: "Project", hr: "HR" };

export default function Interview() {
  const navState = useLocation().state as { jd?: string; jobKey?: string } | null;
  const jd = navState?.jd;
  const [params] = useSearchParams();
  const ov = useGet<Json>("/interview");
  const [qs, setQs] = useState<Json[]>([]);
  const [basis, setBasis] = useState("");
  const [idx, setIdx] = useState(0);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [purpose, setPurpose] = useState("interview");
  const start = useAction((b: Json) => http.post<Json>("/interview/start", b));
  const begin = (b: Json) => start.mutate(b, { onSuccess: (r) => { setQs(r.questions); setBasis(r.based_on); setIdx(0); setSessionId(r.session_id ?? null); setPurpose(r.purpose ?? b.purpose ?? "interview"); } });
  // Arriving from the Skill Graph ("Take a quiz") or a job ("Prep interview") starts the right session once, automatically.
  const autoStarted = useRef(false);
  useEffect(() => {
    if (autoStarted.current) return;
    const skill = params.get("skill");
    if (skill) { autoStarted.current = true; begin({ skill, category: "mcq", count: 5, purpose: params.get("purpose") === "calibration" ? "calibration" : "interview" }); }
    else if (navState?.jobKey) { autoStarted.current = true; begin({ job_key: navState.jobKey, count: 6 }); }
  }); // eslint-disable-line react-hooks/exhaustive-deps
  if (ov.isLoading) return <Loading />;
  if (ov.error) return <ErrorNote error={ov.error} />;
  const o = ov.data;

  return (
    <div className="max-w-3xl">
      <PageTitle title="Interview prep" sub="Questions chosen from your weakest role skills. Practising updates your skills and readiness." />
      <p className="mb-4 flex items-center gap-2 text-sm text-ink-soft"><DemoTag what="Demo question bank" /> Open answers are scored by keyword coverage, a self-check aid and not an expert grade. Coding, behavioral, HR and project answers are self-rated.</p>

      <Card>
        <p className="text-sm text-ink-faint">Interview readiness</p>
        {o.readiness.overall === null ? <p className="mt-1 text-ink-soft">Not measured yet. Answer a few questions below.</p> : (
          <>
            <p className="font-display text-5xl font-bold">{pct(o.readiness.overall)}</p>
            <div className="mt-3 space-y-1 text-sm">{Object.entries(o.readiness.components).map(([k, v]) => <div key={k} className="grid grid-cols-[9rem_1fr] items-center gap-2"><span className="capitalize">{k.replace("_", " ")}</span>{v === null ? <span className="text-ink-faint">Not measured</span> : <Bar value={v as number} label={k} />}</div>)}</div>
          </>
        )}
      </Card>
      {o.struggling.map((s: Json) => <Card key={s.skill} className="mt-3 border-signal"><p className="text-sm">{s.message}</p></Card>)}

      {o.intelligence && (
        <Section title="Use practice where it matters most">
          <div className="grid gap-4 md:grid-cols-2">
            <BottleneckCard bottleneck={o.intelligence.top_bottleneck} />
            <ReviewList reviews={o.intelligence.due_reviews} />
          </div>
          <p className="mt-3 text-sm text-ink-soft">Scored answers here also feed the confidence comparison on Assessment and Skill Graph. For a scheduled recall check that sets your next review date, use the check in Learn &amp; Build.</p>
        </Section>
      )}

      <Section title="Start a session">
        <div className="flex flex-wrap gap-2">
          <button className="btn" onClick={() => begin({ count: 6 })}>Adaptive mix (recommended)</button>
          {o.categories.map((c: Json) => <button key={c.name} className="btn-quiet" onClick={() => begin({ category: c.name, count: 6 })}>{LABEL[c.name]} <span className="ml-1 text-ink-faint">{c.attempted}/{c.available}</span></button>)}
          {jd && <button className="btn-quiet" onClick={() => begin({ jd_text: jd, count: 6 })}>For the job I pasted</button>}
        </div>
        {o.focus_topics.length > 0 && <p className="mt-3 text-sm text-ink-soft">Focus topics: {o.focus_topics.map((t: Json) => t.name).join(", ")}</p>}
        {start.error && <div className="mt-3"><ErrorNote error={start.error} /></div>}
      </Section>

      {qs.length > 0 && idx < qs.length && <Question key={qs[idx].key} q={qs[idx]} n={idx + 1} total={qs.length} basis={basis} purpose={purpose} sessionId={sessionId} onNext={() => setIdx(idx + 1)} />}
      {basis && qs.length === 0 && !start.isPending && <Card className="mt-8"><p className="font-bold">No questions for that yet.</p><p className="text-sm text-ink-soft">There are no questions in the bank for {basis} in this category. Try the adaptive mix, or another category.</p></Card>}
      {qs.length > 0 && idx >= qs.length && <Card className="mt-8"><p className="font-bold">Session complete.</p><p className="text-sm text-ink-soft">Your readiness and skill estimates have been updated.</p></Card>}
    </div>
  );
}

function Question({ q, n, total, basis, purpose, sessionId, onNext }: { q: Json; n: number; total: number; basis: string; purpose: string; sessionId: string | null; onNext: () => void }) {
  const [choice, setChoice] = useState<number | null>(null);
  const [text, setText] = useState("");
  const [rating, setRating] = useState(3);
  const send = useAction((b: Json) => http.post<Json>("/interview/answer", { question_key: q.key, purpose, session_id: sessionId, ...b }));
  const fb = send.data;
  const selfRated = q.scoring === "self_rated";

  return (
    <Card className="mt-8">
      <p className="text-xs text-ink-faint">Question {n} of {total} · based on {basis}</p>
      <p className="mt-2 flex flex-wrap items-center gap-2"><Tag>{LABEL[q.category]}</Tag>{q.skill && <Tag>{q.skill}</Tag>}<Tag>{q.difficulty}</Tag></p>
      <p className="mt-3 text-lg font-medium">{q.text}</p>

      {q.category === "mcq" ? (
        <fieldset className="mt-3 space-y-2" disabled={!!fb}>
          <legend className="sr-only">Choose one</legend>
          {q.options.map((o: string, i: number) => (
            <label key={i} className={`flex items-center gap-2 rounded-md border p-2 text-sm ${fb && i === fb.correct_index ? "border-moss bg-green-50" : fb && i === choice ? "border-alert bg-red-50" : "border-mist"}`}>
              <input type="radio" name="opt" checked={choice === i} onChange={() => setChoice(i)} />{o}
            </label>
          ))}
        </fieldset>
      ) : (
        <>
          <label htmlFor="ans" className="label mt-3">Your answer {selfRated && "(optional notes)"}</label>
          <textarea id="ans" className="field h-28" value={text} onChange={(e) => setText(e.target.value)} disabled={!!fb} />
          {selfRated && !fb && (
            <div className="mt-3"><label htmlFor="rate" className="label">How well did you answer? (1–5)</label><input id="rate" type="range" min={1} max={5} value={rating} onChange={(e) => setRating(Number(e.target.value))} /> {rating}</div>
          )}
        </>
      )}

      {send.error && <div className="mt-3"><ErrorNote error={send.error} /></div>}
      {!fb ? (
        <button className="btn mt-4" disabled={send.isPending || (q.category === "mcq" && choice === null)}
          onClick={() => send.mutate(q.category === "mcq" ? { choice } : selfRated ? { answer: text || null, self_rating: rating } : { answer: text })}>Submit</button>
      ) : (
        <div className="mt-4 text-sm" role="status">
          <p className="font-bold">Score: {Math.round(fb.score)}%</p>
          {fb.explanation && <p className="mt-1">{fb.explanation}</p>}
          {fb.covered && <p className="mt-1">Covered: {fb.covered.join(", ") || "none of the key ideas"}. Consider mentioning: {fb.consider_mentioning.join(", ") || "nothing more"}.</p>}
          {fb.note && <p className="mt-1 text-ink-faint">{fb.note}</p>}
          {fb.intelligence?.calibration && (
            <div className="mt-3 rounded-lg border border-mist p-3">
              <CalibrationBadge cal={fb.intelligence.calibration} />
              <p className="mt-1">{fb.intelligence.calibration.reason}</p>
              {fb.intelligence.review && <p className="mt-1 text-ink-soft">Review: {fb.intelligence.review.status_label}.</p>}
              {fb.top_bottleneck && <p className="mt-1 text-ink-soft">Current biggest bottleneck: <b>{fb.top_bottleneck.name}</b>.</p>}
            </div>
          )}
          <button className="btn mt-3" onClick={onNext}>Next question</button>
        </div>
      )}
    </Card>
  );
}
