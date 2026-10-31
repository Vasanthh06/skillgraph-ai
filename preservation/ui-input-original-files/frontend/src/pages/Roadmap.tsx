import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { AnimatedNumber } from "../components/dashboard";
import { Bar, Card, EmptyState, ErrorNote, NeedsSetup, PageSkeleton, PageTitle, Seg, Tag } from "../components/ui";
import { BottleneckCard, CalibrationBadge, ReviewBadge, ReviewList } from "../components/IntelligencePanels";
import { useAction, useGet } from "../hooks/useApi";
import { http } from "../services/api";
import type { Json } from "../types/api";

import AccountTools from "../components/AccountTools";

const ICON: Record<string, string> = { completed: "✓", current: "●", available: "○", locked: "🔒" };
const TONE: Record<string, string> = {
  completed: "is-completed border-moss/50 bg-green-50",
  current: "border-glow-violet bg-route-tint shadow-glow",
  available: "border-mist bg-white",
  locked: "border-mist bg-white opacity-70",
};
type Filter = "all" | "open" | "done" | "locked";

export default function Roadmap() {
  const { data: r, isLoading, error, refetch } = useGet<Json>("/roadmap");
  const toggle = useAction((v: { slug: string; completed: boolean }) => http.put<Json>(`/roadmap/${v.slug}/complete`, { completed: v.completed }), "Saved.");
  const [filter, setFilter] = useState<Filter>("all");
  // Remember each step's previous status so a step that JUST became complete can celebrate (and its connector fill in).
  const prev = useRef<Record<string, string>>({});
  const [justDone, setJustDone] = useState<Set<string>>(new Set());
  useEffect(() => {
    if (!r?.nodes) return;
    const fresh = new Set<string>();
    for (const n of r.nodes as Json[]) if (prev.current[n.slug] && prev.current[n.slug] !== "completed" && n.status === "completed") fresh.add(n.slug);
    prev.current = Object.fromEntries((r.nodes as Json[]).map((n) => [n.slug, n.status]));
    if (fresh.size) { setJustDone(fresh); const t = window.setTimeout(() => setJustDone(new Set()), 1200); return () => window.clearTimeout(t); }
  }, [r]);

  if (isLoading) return <PageSkeleton />;
  if (error || !r) return <ErrorNote error={error} onRetry={() => refetch()} />;
  if (r.needs) return <><PageTitle title="Learning Roadmap" /><NeedsSetup needs={r.needs} /></>;

  const nodes: Json[] = r.nodes;
  const current = nodes.find((n) => n.status === "current");
  const shown = nodes.filter((n) => filter === "all" || (filter === "done" && n.status === "completed") || (filter === "open" && (n.status === "current" || n.status === "available")) || (filter === "locked" && n.status === "locked"));

  return (
    <div className="max-w-3xl">
      <AccountTools />
      <PageTitle title="Learning Roadmap" sub={<>Your path to <b>{r.role}</b>, ordered by priority and prerequisites. Finishing a step unlocks the next.</>} />
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <small className="text-ink-faint">Progress</small>
          <p className="font-display text-5xl font-bold"><AnimatedNumber value={r.progress.percent} suffix="%" /></p>
          <p className="mb-2 text-sm text-ink-soft">{r.progress.completed} of {r.progress.total} steps completed</p>
          <Bar value={r.progress.percent} tone="moss" label="Roadmap progress" />
        </Card>
        <div className="rounded-2xl border border-mist bg-gradient-to-br from-glow-blue/20 to-glow-violet/25 p-5">
          {current ? (<>
            <p className="text-xs font-semibold uppercase tracking-widest text-glow-cyan">Continue where you left off</p>
            <h2 className="mt-1 text-xl font-bold">{current.name}</h2>
            <p className="mb-3 mt-1 text-sm text-ink-soft">{Math.round(current.score)}% now. {current.why_prioritized ?? "This is your current step."}</p>
            <Link to={`/learn?skill=${current.slug}`} className="btn">Open lessons →</Link>
          </>) : (<>
            <p className="text-xs font-semibold uppercase tracking-widest text-glow-cyan">Roadmap</p>
            <h2 className="mt-1 text-xl font-bold">Every step is complete</h2>
            <Link to="/jobs" className="btn mt-3">Find matching jobs →</Link>
          </>)}
        </div>
      </div>

      {r.intelligence && (
        <>
          <Card className="mt-4"><h2 className="text-base font-bold">Why this order?</h2><p className="mt-1 text-sm text-ink-soft">{r.order_explanation}</p><p className="mt-1 text-xs text-ink-faint">Completed steps stay completed. New evidence can move unfinished steps, and due reviews are shown separately instead of reopening milestones.</p></Card>
          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <BottleneckCard bottleneck={r.intelligence.top_bottleneck} />
            <ReviewList reviews={r.due_reviews} title="Reviews due alongside this roadmap" />
          </div>
        </>
      )}
      {r.struggling.map((s: Json) => <Card key={s.skill} className="mt-4 border-signal"><p className="text-sm">{s.message}</p></Card>)}
      {toggle.error && <div className="mt-4"><ErrorNote error={toggle.error} /></div>}

      <div className="mb-4 mt-6 flex flex-wrap items-center gap-3">
        <Seg<Filter> label="Filter roadmap steps" value={filter} onChange={setFilter} options={[
          { value: "all", label: "All" }, { value: "open", label: "Current & available" }, { value: "done", label: "Completed" }, { value: "locked", label: "Locked" }]} />
        <span className="text-sm text-ink-faint" aria-live="polite">{shown.length} of {nodes.length} steps</span>
      </div>

      {shown.length === 0 ? (
        <EmptyState title="No steps match this filter" action={<button type="button" className="btn-quiet px-3 py-1" onClick={() => setFilter("all")}>Show all steps</button>}>Try another filter.</EmptyState>
      ) : (
        <ol className="road space-y-3 pl-9">
          {shown.map((n) => (
            <li key={n.slug} className={`rounded-xl border p-3 ${TONE[n.status]} ${justDone.has(n.slug) ? "pop-in" : ""}`}>
              <span aria-hidden className="absolute -left-9 top-3 grid h-6 w-6 place-items-center rounded-full border border-mist bg-fog text-xs">{ICON[n.status]}</span>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <Link to={`/learn?skill=${n.slug}`} className="font-medium hover:underline">{n.name}</Link>
                <span className="sr-only">{n.status}</span>
                {n.status === "locked" ? <span className="text-xs text-ink-faint">Finish {n.blocked_by.join(", ")} first</span> : (
                  <button className="btn-quiet px-3 py-1 text-xs" disabled={toggle.isPending} onClick={() => toggle.mutate({ slug: n.slug, completed: n.status !== "completed" })}>
                    {n.status === "completed" ? "Undo" : "Mark complete"}
                  </button>
                )}
              </div>
              <div className="mt-2 flex flex-wrap items-center gap-1.5">
                {n.is_bottleneck && <Tag tone="demo">◆ Bottleneck · {Math.round(n.bottleneck_score)}</Tag>}
                <ReviewBadge review={n.intelligence?.review} />
                <CalibrationBadge cal={n.intelligence?.calibration} />
                {n.intelligence?.review && (n.review_status === "due" || n.review_status === "overdue") && (
                  <Link to={n.intelligence.review.action.route} className="text-xs text-route underline">{n.intelligence.review.action.label} (stays completed)</Link>
                )}
              </div>
              {(n.is_bottleneck || n.status === "locked") && n.why_prioritized && <p className="mt-1 text-xs text-ink-soft">{n.why_prioritized}</p>}
              {n.supporting && <p className="text-xs text-ink-faint">Prerequisite for other skills on this path</p>}
            </li>
          ))}
        </ol>
      )}
      <p className="mt-6 text-xs text-ink-faint">"Mark complete" is your own declaration. The score only becomes firmly verified once a quiz, project or resume backs it up.</p>
    </div>
  );
}
