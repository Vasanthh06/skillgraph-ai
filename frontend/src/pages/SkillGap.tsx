import { Link } from "react-router-dom";
import { Bar, Card, ErrorNote, Loading, NeedsSetup, PageTitle, Section, Tag, pct } from "../components/ui";
import { useGet } from "../hooks/useApi";
import { BottleneckCard, CalibrationBadge } from "../components/IntelligencePanels";
import type { Json } from "../types/api";

export default function SkillGap() {
  const { data: g, isLoading, error } = useGet<Json>("/skill-gap");
  if (isLoading) return <Loading />;
  if (error || !g) return <ErrorNote error={error} />;
  if (g.needs) return <><PageTitle title="Skill gap" /><NeedsSetup needs={g.needs} /></>;

  const list = (items: Json[], empty: string) => items.length ? (
    <ul className="space-y-2">{items.map((i) => (
      <li key={i.slug}><Card className="py-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <Link to={`/explore?q=${i.slug}`} className="font-medium hover:underline">{i.name}</Link>
          <span className="flex flex-wrap gap-2">{i.is_bottleneck && <Tag tone="demo">◆ Bottleneck</Tag>}{i.critical && <Tag tone="warn">Critical</Tag>}{i.supporting && <Tag>Prerequisite</Tag>}{!i.required && <Tag>Optional</Tag>}<CalibrationBadge cal={i.intelligence?.calibration} /></span>
        </div>
        <Bar value={i.score} label={i.name} tone={i.status === "strong" ? "moss" : "route"} />
        {i.is_bottleneck && i.intelligence?.bottleneck && <p className="mt-1 text-xs text-ink-soft">{i.intelligence.bottleneck.why}</p>}
        {i.blocked_by.length > 0 && <p className="mt-1 text-xs text-ink-faint">Needs {i.blocked_by.join(", ")} first</p>}
        {i.unlocks.length > 0 && i.status !== "strong" && <p className="mt-1 text-xs text-ink-faint">Unlocks {i.unlocks.join(", ")}</p>}
      </Card></li>
    ))}</ul>
  ) : <p className="text-sm text-ink-faint">{empty}</p>;

  return (
    <div className="max-w-4xl">
      <PageTitle title="Skill gap" sub={<>Your skills against what <strong>{g.role}</strong> needs. Ordered by what to learn next, not alphabetically.</>} />
      {g.role_is_generated && <p className="mb-4"><Tag tone="generated">Requirements generated from {g.derived_from}</Tag> Review them: this role isn't in the curated set.</p>}
      {g.limited_coverage && !g.role_is_generated && <p className="mb-4 text-sm text-ink-soft"><Tag>Limited coverage</Tag> The skill catalog has few skills for this role so far.</p>}

      <Card>
        <div className="flex flex-wrap items-end gap-8">
          <div><p className="text-sm text-ink-faint">Overall readiness</p><p className="font-display text-5xl font-bold">{pct(g.readiness.overall)}</p></div>
          <div className="min-w-[14rem] flex-1 space-y-1 text-sm">
            {Object.entries(g.groups).map(([k, v]) => <div key={k} className="grid grid-cols-[8rem_1fr] items-center gap-2"><span>{k}</span><Bar value={v as number} label={k} /></div>)}
            <div className="grid grid-cols-[8rem_1fr] items-center gap-2"><span>Projects</span><Bar value={g.readiness.projects} tone="moss" label="Projects" /></div>
            <div className="grid grid-cols-[8rem_1fr] items-center gap-2"><span>Interview</span>{g.readiness.interview === null ? <span className="text-ink-faint">Not practised yet</span> : <Bar value={g.readiness.interview} tone="signal" label="Interview" />}</div>
          </div>
        </div>
      </Card>

      {g.intelligence && <Section title="Foundation holding the most back"><BottleneckCard bottleneck={g.intelligence.top_bottleneck} /></Section>}
      <Section title="Learn next">
        <ol className="space-y-2">{g.learn_next.map((i: Json) => <li key={i.slug} className="flex items-center gap-3"><span className="grid h-7 w-7 place-items-center rounded-full bg-route text-sm font-bold text-white">{i.rank}</span><Link to={`/learn?skill=${i.slug}`} className="font-medium hover:underline">{i.name}</Link>{i.is_bottleneck && <Tag tone="demo">◆ Bottleneck</Tag>}{i.critical && <Tag tone="warn">Critical</Tag>}</li>)}</ol>
      </Section>
      <Section title={`Critical (${g.critical.length})`}>{list(g.critical, "No critical gaps.")}</Section>
      <Section title={`Weak: partly known (${g.weak.length})`}>{list(g.weak, "None.")}</Section>
      <Section title={`Missing (${g.missing.length})`}>{list(g.missing, "None.")}</Section>
      <Section title={`Strong (${g.strong.length})`}>{list(g.strong, "None yet.")}</Section>
    </div>
  );
}
