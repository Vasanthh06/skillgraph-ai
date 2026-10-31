import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import SkillGraphView, { GraphLegend, type GraphState } from "../components/SkillGraphView";
import { BottleneckCard, CalibrationBadge, CalibrationPanel, ReviewBadge, ReviewPanel } from "../components/IntelligencePanels";
import { Bar, Card, ErrorNote, NeedsSetup, PageSkeleton, PageTitle, Seg, StatePill, Tag } from "../components/ui";
import { useGet } from "../hooks/useApi";
import type { Json } from "../types/api";

const SRC: Record<string, string> = { resume: "Resume", self: "Self-assessment", assessment: "Quiz", projects: "Projects", learning: "Learning", interview: "Interview" };

function Detail({ node, onSelect, onClear }: { node: Json | null; onSelect: (slug: string) => void; onClear: () => void }) {
  const nav = useNavigate();
  if (!node) {
    return (
      <Card>
        <p className="text-xs font-semibold uppercase tracking-widest text-glow-cyan">Skill details</p>
        <h2 className="mt-1 text-xl font-bold">Select a skill</h2>
        <p className="mt-2 text-sm text-ink-soft">Click any dot to see why it is coloured that way, what evidence backs it, and what it unlocks. Connected skills stay highlighted.</p>
      </Card>
    );
  }
  const sources = Object.entries(node.sources as Record<string, number>);
  const intel = node.intelligence ?? {};
  const bottleneck = intel.bottleneck ?? null;
  const review = intel.review ?? null;
  return (
    <Card>
      <p className="text-xs font-semibold uppercase tracking-widest text-glow-cyan">{node.group}</p>
      <h2 className="mt-1 text-xl font-bold">{node.name}</h2>
      <p className="mt-2 flex flex-wrap gap-2"><StatePill state={node.state} />{node.verified ? <Tag tone="good">Verified by a quiz, project or interview</Tag> : <Tag>Not verified yet</Tag>}{node.current && <Tag tone="demo">Next up</Tag>}{bottleneck && <Tag tone="demo">◆ Bottleneck · impact {Math.round(bottleneck.bottleneck_score)}</Tag>}<ReviewBadge review={review} /><CalibrationBadge cal={intel.calibration} /></p>
      <p className="mt-2 text-sm text-ink-soft">{node.why}</p>
      {bottleneck && <p className="mt-2 rounded-lg border border-signal/50 bg-signal/10 p-2 text-sm"><b>Why this is a bottleneck:</b> {bottleneck.why}</p>}

      <h3 className="mt-4 text-sm font-bold">Evidence</h3>
      {sources.length ? (
        <div className="mt-1 space-y-1 text-sm text-ink-soft">
          {sources.map(([k, v]) => <div key={k} className="grid grid-cols-[6.5rem_1fr] items-center gap-2"><span>{SRC[k] ?? k}</span><Bar value={v} label={SRC[k] ?? k} /></div>)}
          <p className="text-xs text-ink-faint">Confidence {Math.round(node.confidence * 100)}%{node.capped ? " (capped: a self-report alone can't reach expert)" : ""}</p>
        </div>
      ) : <p className="mt-1 text-sm text-ink-faint">No evidence yet. A resume, assessment answer, quiz or project would add some.</p>}

      <h3 className="mt-5 text-sm font-bold">Confidence check</h3>
      <div className="mt-1"><CalibrationPanel cal={intel.calibration} /></div>

      <h3 className="mt-5 text-sm font-bold">Recall &amp; review</h3>
      <div className="mt-1"><ReviewPanel review={review} /></div>

      {node.prerequisites.length > 0 && (<><h3 className="mt-4 text-sm font-bold">Needs first</h3><div className="mt-1 flex flex-wrap gap-1.5">{node.prerequisites.map((p: Json) => <button key={p.slug} type="button" className="rounded-lg border border-mist px-2.5 py-0.5 text-sm hover:border-glow-violet" onClick={() => onSelect(p.slug)}>{p.name}</button>)}</div></>)}
      {node.unlocks.length > 0 && (<><h3 className="mt-3 text-sm font-bold">Unlocks</h3><div className="mt-1 flex flex-wrap gap-1.5">{node.unlocks.map((u: Json) => <button key={u.slug} type="button" className="rounded-lg border border-mist px-2.5 py-0.5 text-sm hover:border-glow-violet" onClick={() => onSelect(u.slug)}>{u.name}</button>)}</div></>)}

      <div className="mt-4 flex flex-wrap gap-2">
        <Link to={`/learn?skill=${node.id}`} className="btn px-3 py-1 text-xs">Learn this skill</Link>
        {node.has_quiz && <button type="button" className="btn-quiet px-3 py-1 text-xs" onClick={() => nav(`/interview?skill=${node.id}`)}>Take a quiz</button>}
        <Link to={`/learn?skill=${node.id}&check=calibration`} className="btn-quiet px-3 py-1 text-xs">Knowledge check</Link>
        {review && <Link to={review.action.route} className="btn-quiet px-3 py-1 text-xs">{review.action.label}</Link>}
        <Link to={`/explore?q=${node.id}`} className="btn-quiet px-3 py-1 text-xs">Explore</Link>
        <button type="button" className="btn-quiet px-3 py-1 text-xs" onClick={onClear}>Clear</button>
      </div>
    </Card>
  );
}

export default function SkillGraph() {
  const q = useGet<Json>("/skill-graph");
  const [params, setParams] = useSearchParams();
  const [filter, setFilter] = useState<GraphState | "all">("all");
  const [group, setGroup] = useState("all");
  const selected = params.get("sel");
  const select = (slug: string) => setParams(selected === slug ? {} : { sel: slug }, { replace: true });

  if (q.isLoading) return <PageSkeleton />;
  if (q.error || !q.data) return <ErrorNote error={q.error} onRetry={() => q.refetch()} />;
  const g = q.data;
  if (g.needs) return <><PageTitle title="Skill Graph" /><NeedsSetup needs={g.needs} /></>;

  const count = (s: string) => g.nodes.filter((n: Json) => n.state === s).length;
  const node = selected ? g.nodes.find((n: Json) => n.id === selected) ?? null : null;
  const filtered = filter !== "all" || group !== "all";

  return (
    <div className="max-w-6xl">
      <PageTitle title="Skill Graph" sub={<>Every skill for <b>{g.role}</b>. Colour shows your evidence-based state. Select a skill to see why.</>} />
      {g.intelligence && (
        <div className="mb-4 grid gap-4 lg:grid-cols-[minmax(0,1fr)_21rem]">
          <BottleneckCard bottleneck={g.intelligence.top_bottleneck} />
          <Card>
            <h2 className="text-base font-bold">Reviews &amp; confidence</h2>
            <p className="mt-2 text-sm text-ink-soft">{g.intelligence.review_summary.due + g.intelligence.review_summary.overdue} review(s) due · {g.intelligence.review_summary.upcoming} upcoming.</p>
            <p className="mt-1 text-sm text-ink-soft">Cyan dots mark skills due for recall; amber diamonds mark bottlenecks. Select any skill for its confidence comparison and next review date.</p>
            <Link to="/learn" className="btn-quiet mt-3 px-3 py-1 text-sm">Open due reviews in Learn &amp; Build →</Link>
          </Card>
        </div>
      )}
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <Seg label="Filter skills by state" value={filter} onChange={setFilter} options={[
          { value: "all", label: "All", count: g.nodes.length }, { value: "acquired", label: "Acquired", count: count("acquired") },
          { value: "in_progress", label: "In progress", count: count("in_progress") }, { value: "missing", label: "Missing", count: count("missing") }]} />
        <label className="sr-only" htmlFor="grp">Filter by group</label>
        <select id="grp" className="field w-auto" value={group} onChange={(e) => setGroup(e.target.value)}>
          <option value="all">All groups</option>
          {g.groups.map((x: string) => <option key={x} value={x}>{x}</option>)}
        </select>
        {filtered && <button type="button" className="btn-quiet px-3 py-1 text-xs" onClick={() => { setFilter("all"); setGroup("all"); }}>Clear filters</button>}
      </div>
      <div className="grid items-start gap-4 lg:grid-cols-[minmax(0,1fr)_21rem]">
        <Card>
          <SkillGraphView network={g} role={g.role} selected={selected} filter={filter} group={group} animate onSelect={select} />
          <GraphLegend />
          <p className="mt-2 text-xs text-ink-faint">Lines point from a prerequisite to the skill it unlocks.</p>
        </Card>
        <Detail node={node} onSelect={select} onClear={() => setParams({}, { replace: true })} />
      </div>
    </div>
  );
}
