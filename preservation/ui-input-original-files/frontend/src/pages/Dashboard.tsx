import { Link, useNavigate } from "react-router-dom";
import { AnimatedNumber, BlockersCard, JourneyStrip, NextBestActionCard, ProgressRing } from "../components/dashboard";
import { BottleneckCard, ReviewList } from "../components/IntelligencePanels";
import SkillGraphView, { GraphLegend } from "../components/SkillGraphView";
import { Bar, Card, DemoTag, EmptyState, ErrorNote, PageSkeleton, Section, Tag } from "../components/ui";
import { useAction, useGet } from "../hooks/useApi";
import { http } from "../services/api";
import { useAuth } from "../store/auth";
import type { Json } from "../types/api";

function Onboarding({ o, role }: { o: Json; role?: string }) {
  const mark = (st: string) => (st === "done" || st === "complete" ? "✓" : st === "optional" ? "–" : st === "in_progress" ? "◐" : "○");
  const label = (x: Json) => (x.key === "knowledge" ? `${x.percent}%` : x.status === "done" ? "Done" : x.status === "optional" ? "Optional" : x.status === "complete" ? "Complete" : x.status === "in_progress" ? "In progress" : x.status === "not_started" ? "Not started" : "To do");
  const next = o.next === "profile" ? "/profile" : "/assessment";
  return (
    <div className="mt-6 max-w-2xl">
      <h2 className="text-2xl font-bold">Let's build your career profile.</h2>
      <p className="mt-2 text-ink-soft">Your readiness, skill gaps and recommendations are calculated from <em>your</em> answers. Until there is enough to go on, we show nothing rather than guess.</p>
      <Card className="mt-5">
        <ul className="space-y-3">
          {o.steps.map((x: Json) => (
            <li key={x.key} className="flex items-start gap-3">
              <span aria-hidden className="mt-0.5 w-5 text-center text-glow-cyan">{mark(x.status)}</span>
              <div className="flex-1">
                <div className="flex justify-between gap-3"><span className="font-medium">{x.label}</span><span className="text-sm text-ink-soft">{label(x)}</span></div>
                {x.key === "knowledge" && <div className="mt-1"><Bar value={x.percent} label="Knowledge" /></div>}
                {x.detail && x.key !== "knowledge" && <p className="text-sm text-ink-faint">{x.detail}</p>}
              </div>
            </li>
          ))}
        </ul>
        <p className="mt-3 text-xs text-ink-faint">Dashboard unlocks once about {o.min_coverage_percent}% of {role ?? "your target role"}'s skills have evidence from your assessment or resume.</p>
        <Link to={next} className="btn mt-4">{o.next === "profile" ? "Complete my profile" : o.next === "target_role" ? "Choose my target role" : "Tell us what I know"}</Link>
      </Card>
    </div>
  );
}

function Skills({ title, items, tone, empty, total }: { title: string; items: Json[]; tone?: "moss" | "signal"; empty: string; total?: number }) {
  return (
    <Card lift>
      <div className="mb-2 flex items-center justify-between"><h3 className="text-base font-bold">{title}</h3><span className="text-sm text-ink-faint">{total ?? items.length}</span></div>
      {items.length === 0 ? <p className="text-sm text-ink-faint">{empty}</p> : items.map((i) => (
        <div key={i.slug} className="mb-2">
          <Link to={`/skill-graph?sel=${i.slug}`} className="text-sm hover:underline">{i.name}</Link>
          <Bar value={i.score} label={i.name} tone={tone} />
        </div>
      ))}
    </Card>
  );
}

const STEP_PILL: Record<string, string> = { current: "border-signal/50 bg-signal/10 text-signal", available: "border-mist text-ink-soft", locked: "border-alert/40 bg-red-50 text-alert" };

export default function Dashboard() {
  const { user } = useAuth();
  const nav = useNavigate();
  const { data: d, isLoading, error, refetch } = useGet<Json>("/dashboard");
  const setStatus = useAction((v: { key: string; status: string }) => http.post<Json>(`/jobs/${v.key}/status`, { status: v.status }), "Saved.");
  const clearStatus = useAction((key: string) => http.del<void>(`/jobs/${key}/status`), "Removed from saved jobs.");
  if (isLoading) return <PageSkeleton />;
  if (error || !d) return <ErrorNote error={error} onRetry={() => refetch()} />;
  const first = user?.full_name.split(" ")[0];
  const saveJob = (j: Json) => (j.application_status === "applied" ? undefined : j.application_status === "saved" ? clearStatus.mutate(j.key) : setStatus.mutate({ key: j.key, status: "saved" }));

  return (
    <div className="max-w-6xl">
      <div className="grid gap-5 lg:grid-cols-[minmax(0,1.5fr)_minmax(250px,1fr)]">
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-glow-cyan">AI career copilot</p>
          <h1 className="mt-1 text-3xl font-bold">Welcome, {first}</h1>
          <p className="mt-1 text-ink-soft">
            {d.target_role ? <>Target role: <strong className="text-ink">{d.target_role.name}</strong> {d.target_role.is_generated && <Tag tone="generated">Generated from {d.target_role.derived_from}</Tag>} · <Link to="/role" className="text-route underline">change</Link></> : "You haven't chosen a target role yet."}
          </p>
          <NextBestActionCard action={d.next_best_action} />
        </div>
        {!d.needs && (
          <Card className="flex flex-col items-center text-center">
            <small className="mb-2 text-ink-faint">Career readiness</small>
            <ProgressRing value={d.readiness_score} />
            <div className="mt-4 w-full space-y-1 text-left text-sm text-ink-soft">
              <div>Skills <Bar value={d.readiness.skills} label="Skills" /></div>
              <div>Projects <Bar value={d.readiness.projects} tone="moss" label="Projects" /></div>
              <div>Interview {d.readiness.interview === null ? <span className="text-xs text-ink-faint">not counted until you practise</span> : <Bar value={d.readiness.interview} tone="signal" label="Interview" />}</div>
            </div>
          </Card>
        )}
      </div>

      <JourneyStrip steps={d.journey} />

      {d.needs ? <Onboarding o={d.onboarding} role={d.target_role?.name} /> : (
        <>
          <div className="mt-5 grid gap-4 md:grid-cols-3">
            <Card lift><small className="text-ink-faint">Skill gap</small><p className="font-display text-4xl font-bold"><AnimatedNumber value={d.skills_remaining} /></p><p className="text-sm text-ink-soft">skills remaining</p><Link to="/skill-gap" className="mt-2 inline-block text-sm text-route underline">See the full gap</Link></Card>
            <Card lift><small className="text-ink-faint">Roadmap</small><p className="font-display text-4xl font-bold"><AnimatedNumber value={d.roadmap_progress.percent} suffix="%" /></p><p className="text-sm text-ink-soft">{d.roadmap_progress.completed} of {d.roadmap_progress.total} steps done</p><Link to="/roadmap" className="mt-2 inline-block text-sm text-route underline">Open roadmap</Link></Card>
            <Card lift><small className="text-ink-faint">Interview readiness</small><p className="font-display text-4xl font-bold">{d.interview_readiness.overall === null ? "–" : <AnimatedNumber value={d.interview_readiness.overall} suffix="%" />}</p><p className="text-sm text-ink-soft">{d.interview_readiness.overall === null ? "Not measured yet" : `from ${d.interview_readiness.attempts} answers`}</p><Link to="/interview" className="mt-2 inline-block text-sm text-route underline">Practise now</Link></Card>
          </div>

          <Section title="Your skills">
            <div className="grid gap-4 md:grid-cols-3">
              <Skills title="Matched skills" items={d.skill_overview.strong} tone="moss" empty="None yet." />
              <Skills title="Skills to improve" items={d.skill_overview.developing} empty="None right now." />
              <Skills title="Missing skills" items={d.skill_overview.critical} tone="signal" empty="No critical gaps." />
            </div>
          </Section>

          <Section title="AI insights">
            <div className="grid gap-4 md:grid-cols-2">
              <Card key={d.next_best_action.title} className="reveal">
                <div className="mb-2 flex items-center justify-between gap-2"><h3 className="text-base font-bold">✦ {d.recommended_next_skill ? d.recommended_next_skill.name : "Insight"}</h3><Tag>Rule-based, from your evidence</Tag></div>
                {d.recommended_next_skill ? (
                  <dl className="space-y-1.5 text-sm text-ink-soft">
                    {([["Why you", d.recommended_next_skill.why], ["Why now", d.recommended_next_skill.why_now], ["Impact", d.recommended_next_skill.impact], ["After this", d.recommended_next_skill.next]] as [string, string][]).map(([k, v]) => (
                      <div key={k} className="border-l-2 border-glow-violet pl-3"><dt className="inline font-semibold text-ink">{k}: </dt><dd className="inline">{v}</dd></div>
                    ))}
                  </dl>
                ) : <p className="text-sm text-ink-soft">No further skills to learn: you have covered your gaps.</p>}
                <Link to={d.next_best_action.route} className="btn mt-4">{d.next_best_action.title} →</Link>
                {d.intent && <p className="mt-3 text-xs text-ink-faint">Your recent activity suggests a <strong>{d.intent.label}</strong> (a heuristic, not a trained model).</p>}
              </Card>
              <BlockersCard data={d.readiness_blockers} />
            </div>
          </Section>

          {d.intelligence && (
            <Section title="What's holding you back & what's due">
              <div className="grid gap-4 md:grid-cols-2">
                <BottleneckCard bottleneck={d.intelligence.top_bottleneck} />
                <ReviewList reviews={d.intelligence.due_reviews} />
              </div>
              {d.intelligence.upcoming_reviews?.length > 0 && (
                <p className="mt-3 text-sm text-ink-soft">Coming up: {d.intelligence.upcoming_reviews.slice(0, 3).map((r: Json) => `${r.name} (${r.status_label.toLowerCase()})`).join(", ")}. <Link to="/learn" className="text-route underline">See reviews in Learn &amp; Build</Link></p>
              )}
            </Section>
          )}

          <Section title="Skill network" aside={<DemoTag what="Scores from your evidence" />}> 
            <Card>
              <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                <p className="text-sm text-ink-soft">Each dot is a skill for <b>{d.target_role.name}</b>. The number is your evidence-based score.</p>
                <Link to="/skill-graph" className="btn-quiet px-3 py-1 text-xs">Open full Skill Graph →</Link>
              </div>
              <SkillGraphView network={d.skill_network} role={d.target_role.name} animate onSelect={(slug) => nav(`/skill-graph?sel=${slug}`)} />
              <GraphLegend />
            </Card>
          </Section>

          <Section title="Learning roadmap">
            <Card>
              {d.roadmap_preview.length === 0 ? <p className="text-sm text-ink-faint">Every step is complete.</p> : d.roadmap_preview.map((n: Json) => (
                <div key={n.slug} className="flex flex-wrap items-center justify-between gap-2 py-1.5 text-sm">
                  <span><span className={`mr-2 rounded-full border px-2 py-0.5 text-xs capitalize ${STEP_PILL[n.status]}`}>{n.status}</span><Link to={`/learn?skill=${n.slug}`} className="hover:underline">{n.name}</Link></span>
                  <small className="text-ink-faint">{n.status === "locked" ? `Needs ${n.blocked_by.join(", ")}` : `${Math.round(n.score)}% now`}</small>
                </div>
              ))}
              <Link to="/roadmap" className="mt-2 inline-block text-sm text-route underline">Open the full roadmap →</Link>
            </Card>
          </Section>

          <Section title="Recommended projects" aside={<DemoTag what="Demo projects" />}>
            {d.project_recommendations.length === 0 ? (
              <EmptyState title="No project to suggest yet" action={<Link to="/skill-gap" className="btn-quiet px-3 py-1">See your gaps</Link>}>Projects appear when they build a skill you still need.</EmptyState>
            ) : (
              <ul className="grid gap-3 sm:grid-cols-3">
                {d.project_recommendations.map((p: Json) => (
                  <li key={p.key}>
                    <Card lift className="h-full">
                      <p className="font-bold">{p.title}</p><p className="mt-1 text-sm text-ink-soft">{p.why}</p>
                      <p className="mt-2 flex flex-wrap gap-1.5"><Tag>{p.difficulty}</Tag>{p.ready ? <Tag tone="good">Ready to start</Tag> : <Tag tone="warn">Needs {p.missing_prerequisites.join(", ")}</Tag>}</p>
                      <Link to={`/projects?open=${p.key}`} className="btn-quiet mt-3 px-3 py-1 text-xs">View details</Link>
                    </Card>
                  </li>
                ))}
              </ul>
            )}
          </Section>

          <Section title="Job matches" aside={<DemoTag what="Demo listings" />}>
            <ul className="grid gap-3 sm:grid-cols-3">
              {d.job_matches.map((j: Json) => (
                <li key={j.key}>
                  <Card lift className="h-full">
                    <p className="font-bold">{j.title}</p><p className="text-sm text-ink-faint">{j.company}</p>
                    <p className="mt-2 font-display text-2xl font-bold">{j.match}% match</p><p className="text-sm text-ink-soft">{j.explanation}</p>
                    <div className="mt-3 flex flex-wrap gap-2">
                      <Link to={`/jobs?open=${j.key}`} className="btn-quiet px-3 py-1 text-xs">View</Link>
                      <button type="button" disabled={setStatus.isPending || clearStatus.isPending} onClick={() => saveJob(j)} className={`px-3 py-1 text-xs ${j.application_status ? "btn-quiet border-moss/50 text-moss" : "btn"}`}>
                        {j.application_status === "applied" ? "Applied ✓" : j.application_status === "saved" ? "Saved ✓" : "Save job"}
                      </button>
                    </div>
                  </Card>
                </li>
              ))}
            </ul>
          </Section>
        </>
      )}

      <Section title="Recent activity">
        <ul className="space-y-1 text-sm text-ink-soft">{d.recent_activity.map((a: Json, i: number) => <li key={i}>{a.text}</li>)}{d.recent_activity.length === 0 && <li>Nothing yet.</li>}</ul>
      </Section>
    </div>
  );
}
