import { Link, useSearchParams } from "react-router-dom";
import { Card, DemoTag, ErrorNote, Loading, NeedsSetup, PageTitle, Section, Tag } from "../components/ui";
import { useAction, useGet } from "../hooks/useApi";
import { http } from "../services/api";
import type { Json } from "../types/api";
import { useState } from "react";
import { CalibrationBadge, CalibrationPanel, KnowledgeCheckPanel, ReviewBadge, ReviewList, ReviewPanel, fmtDate } from "../components/IntelligencePanels";

const track = (skill: string, url: string) => { http.post("/activity", { type: "resource_opened", skill, url }).catch(() => undefined); };

export default function Learn() {
  const [params] = useSearchParams();
  const skill = params.get("skill");
  const checkParam = params.get("check") === "recall" ? "recall" : params.get("check") === "calibration" ? "calibration" : null;
  const list = useGet<Json>(skill ? null : "/learn", ["learn"]);
  const one = useGet<Json>(skill ? `/learn/${skill}` : null, ["learn", skill]);
  const projects = useGet<Json>("/build");
  const certs = useGet<Json[]>("/certifications");
  const done = useAction((v: { slug: string; completed: boolean }) => http.put<Json>(`/learn/${v.slug}/complete`, { completed: v.completed }), "Saved.");
  const status = useAction((v: { key: string; status: string }) => http.post<Json>(`/projects/${v.key}/status`, { status: v.status }), "Saved: project status updated.");
  const [cert, setCert] = useState({ name: "", skill: "" });
  const addCert = useAction((b: Json) => http.post<Json>("/certifications", b), "Certification saved.");
  const submitCert = () => addCert.mutate({ name: cert.name, skill: cert.skill || null }, { onSuccess: () => setCert({ name: "", skill: "" }) });

  const q = skill ? one : list;
  if (q.isLoading) return <Loading />;
  if (q.error) return <ErrorNote error={q.error} />;
  const blocks: Json[] = skill ? [q.data] : q.data?.skills ?? [];
  if (!skill && q.data?.needs) return <><PageTitle title="Learn & Build" /><NeedsSetup needs={q.data.needs} /></>;

  return (
    <div className="max-w-4xl">
      <PageTitle title="Learn & Build" sub="Learn → Practise → Build → Prove, for the skills your roadmap says are next." />
      {!skill && q.data?.intelligence && (
        <Section title="Due for review">
          <div className="grid gap-4 md:grid-cols-2">
            <ReviewList reviews={q.data.due_reviews} />
            <Card>
              <h3 className="text-base font-bold">Upcoming reviews</h3>
              {q.data.upcoming_reviews?.length ? (
                <ul className="mt-2 space-y-2 text-sm">
                  {q.data.upcoming_reviews.slice(0, 5).map((r: Json) => (
                    <li key={r.slug} className="flex flex-wrap items-center justify-between gap-2">
                      <Link to={`/learn?skill=${r.slug}`} className="hover:underline">{r.name}</Link>
                      <span className="text-ink-faint">{r.status_label} · {fmtDate(r.next_review_at)}</span>
                    </li>
                  ))}
                </ul>
              ) : <p className="mt-2 text-sm text-ink-faint">No upcoming reviews are scheduled yet.</p>}
              <p className="mt-3 text-xs text-ink-faint">Strong recall spaces the next check further out; a weak result brings it closer and points back to the material. Completed milestones stay completed.</p>
            </Card>
          </div>
        </Section>
      )}
      {blocks.map((b) => (
        <Card key={b.skill.slug} className="mb-8">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="font-display text-2xl font-bold">{b.skill.name}</h2>
            <button className="btn-quiet" disabled={done.isPending} onClick={() => done.mutate({ slug: b.skill.slug, completed: !b.completed })}>{b.completed ? "Marked finished: undo" : "I finished the learning"}</button>
          </div>
          <p className="mt-1 text-sm text-ink-soft">Difficulty {b.skill.difficulty}/5{b.skill.prerequisites.length ? ` · Builds on ${b.skill.prerequisites.join(", ")}` : ""}</p>
          {b.intelligence && (
            <p className="mt-2 flex flex-wrap gap-1.5">
              {b.intelligence.bottleneck && <Tag tone="demo">◆ Bottleneck for your path</Tag>}
              <ReviewBadge review={b.intelligence.review} />
              <CalibrationBadge cal={b.intelligence.calibration} />
              {b.completed && b.intelligence.review && <Tag>Next review {fmtDate(b.intelligence.review.next_review_at)}</Tag>}
            </p>
          )}
          {!b.completed && <p className="mt-1 text-xs text-ink-faint">When you mark this finished, a short spaced recall check is scheduled automatically.</p>}
          {b.topics.length > 0 && <p className="mt-3 flex flex-wrap gap-2">{b.topics.map((t: string) => <Tag key={t}>{t}</Tag>)}</p>}

          <Section title="Learn">
            <ul className="grid gap-2 sm:grid-cols-2">
              {b.learn.videos.map((v: Json) => <li key={v.url}><a className="block rounded-md border border-mist p-3 text-sm hover:border-route" target="_blank" rel="noreferrer" href={v.url} onClick={() => track(b.skill.slug, v.url)}>▶ {v.title}{v.channel && <span className="text-ink-faint"> · {v.channel}</span>}{v.is_search_url && <> <Tag>YouTube search</Tag></>}</a></li>)}
              {b.learn.docs && <li><a className="block rounded-md border border-mist p-3 text-sm hover:border-route" target="_blank" rel="noreferrer" href={b.learn.docs} onClick={() => track(b.skill.slug, b.learn.docs)}>📄 Official documentation</a></li>}
            </ul>
          </Section>
          <Section title="Practise">
            <p className="mb-3 text-sm text-ink-soft">{b.practice.mcq_keys.length} quiz questions and {b.practice.open_keys.length} written questions for this skill. <Link className="text-route underline" to="/interview">Open Interview Prep</Link>.</p>
            <KnowledgeCheckPanel skill={b.skill.slug} skillName={b.skill.name}
              purpose={(skill === b.skill.slug && checkParam) || ((b.intelligence?.review?.status === "due" || b.intelligence?.review?.status === "overdue") ? "recall" : "calibration")}
              autoStart={skill === b.skill.slug && checkParam !== null} />
          </Section>
          {b.intelligence && (
            <Section title="Confidence & recall">
              <div className="grid gap-5 md:grid-cols-2">
                <div><h3 className="text-sm font-bold">Confidence check</h3><CalibrationPanel cal={b.intelligence.calibration} /></div>
                <div><h3 className="text-sm font-bold">Review schedule</h3><ReviewPanel review={b.intelligence.review} /></div>
              </div>
            </Section>
          )}
          <Section title="Build" aside={<DemoTag what="Demo projects" />}>
            {b.build.length === 0 ? <p className="text-sm text-ink-faint">No matching project yet.</p> : <ul className="space-y-2">{b.build.map((p: Json) => <li key={p.key} className="text-sm"><strong>{p.title}</strong> ({p.difficulty}, ~{p.hours}h): {p.expected_output}</li>)}</ul>}
          </Section>
          <Section title="Prove"><ul className="list-disc pl-5 text-sm text-ink-soft">{b.prove.map((x: string) => <li key={x}>{x}</li>)}</ul></Section>
        </Card>
      ))}

      <Section title="Projects for your gaps" aside={<DemoTag what="Demo projects" />}>
        {projects.data?.recommended.map((p: Json) => (
          <Card key={p.key} className="mb-3">
            <div className="flex flex-wrap items-center justify-between gap-2"><h3 className="font-bold">{p.title}</h3><span className="flex gap-2"><Tag>{p.difficulty}</Tag><Tag>~{p.hours}h</Tag>{!p.ready && <Tag tone="warn">Needs {p.missing_prerequisites.join(", ")}</Tag>}</span></div>
            <p className="mt-1 text-sm text-ink-soft">{p.description}</p>
            <p className="mt-1 text-sm"><strong>Needs:</strong> {p.requires_names.join(", ")} · <strong>You'll gain:</strong> {p.gains_names.join(", ")}</p>
            <p className="text-sm"><strong>Output:</strong> {p.expected_output} <strong>Portfolio value:</strong> {p.portfolio_value}</p>
            <p className="mt-1 text-xs text-ink-faint">{p.why}</p>
            <div className="mt-3 flex gap-2">{["planned", "in_progress", "completed"].map((s) => <button key={s} className={`btn-quiet px-3 py-1 text-xs ${p.status === s ? "!border-route !bg-route-tint" : ""}`} disabled={status.isPending} onClick={() => status.mutate({ key: p.key, status: s })}>{s.replace("_", " ")}</button>)}</div>
          </Card>
        ))}
      </Section>

      <Section title="Certifications">
        <ul className="mb-3 text-sm">{certs.data?.map((c) => <li key={c.id}>{c.name}{c.skill && <> · {c.skill}</>}</li>)}{certs.data?.length === 0 && <li className="text-ink-faint">None added.</li>}</ul>
        {/* Click-driven like Login: form submission is blocked in sandboxed frames without `allow-forms`. */}
        <form className="flex flex-wrap gap-2" onSubmit={(e) => { e.preventDefault(); submitCert(); }}
          onKeyDown={(e) => { if (e.key === "Enter" && e.target instanceof HTMLInputElement) { e.preventDefault(); submitCert(); } }}>
          <input className="field max-w-xs" placeholder="Certificate name" aria-label="Certificate name" value={cert.name} onChange={(e) => setCert({ ...cert, name: e.target.value })} />
          <input className="field max-w-[12rem]" placeholder="Skill (e.g. python)" aria-label="Related skill" value={cert.skill} onChange={(e) => setCert({ ...cert, skill: e.target.value })} />
          <button type="button" onClick={submitCert} className="btn" disabled={cert.name.length < 2}>Add</button>
        </form>
        {addCert.error && <ErrorNote error={addCert.error} />}
      </Section>
    </div>
  );
}
