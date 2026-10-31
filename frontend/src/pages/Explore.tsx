import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import SkillGraph from "../components/SkillGraph";
import { Card, ErrorNote, Loading, PageTitle, Section, Tag } from "../components/ui";
import { useGet } from "../hooks/useApi";
import type { Json } from "../types/api";

function Tree({ node }: { node: Json }) {
  return (
    <ul className="ml-4 border-l border-mist pl-3 text-sm">
      {node.children.map((c: Json) => (
        <li key={c.name} className="py-0.5">{c.name}{c.children?.length > 0 && <Tree node={c} />}</li>
      ))}
    </ul>
  );
}

export default function Explore() {
  const [params, setParams] = useSearchParams();
  const q = params.get("q") ?? "";
  const [input, setInput] = useState(q);
  useEffect(() => setInput(q), [q]);
  const res = useGet<Json>(q ? `/search?q=${encodeURIComponent(q)}` : null, ["search", q]);
  const go = (s: string) => setParams(s ? { q: s } : {});
  const search = () => go(input.trim());

  return (
    <div className="max-w-4xl">
      <PageTitle title="Explore skills" sub="Search any technology. Verified entries come from our curated catalog; anything else is clearly marked." />
      {/* type="button" + keydown Enter, as on Login: native form submission is blocked in
          sandboxed frames without `allow-forms`, so Search must work from a click handler. */}
      <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); search(); }}
        onKeyDown={(e) => { if (e.key === "Enter" && e.target instanceof HTMLInputElement) { e.preventDefault(); search(); } }} role="search">
        <label htmlFor="sq" className="sr-only">Search skills</label>
        <input id="sq" className="field" value={input} onChange={(e) => setInput(e.target.value)} placeholder="Python, React, Kubernetes, machine learning…" />
        <button type="button" onClick={search} className="btn">Search</button>
      </form>
      {res.isLoading && <div className="mt-4"><Loading /></div>}
      {res.error && <div className="mt-4"><ErrorNote error={res.error} /></div>}

      {res.data && !res.data.exact && (
        <div className="mt-6">
          <p className="text-ink-soft">No verified entry for "{res.data.query}".</p>
          {res.data.matches.length > 0 && <p className="mt-2 flex flex-wrap gap-2">{res.data.matches.map((m: Json) => <button key={m.slug} className="btn-quiet" onClick={() => go(m.slug)}>{m.name}</button>)}</p>}
          {res.data.related.length > 0 && <><p className="mt-4 text-sm font-medium">Related verified skills <Tag>similarity match</Tag></p><p className="mt-2 flex flex-wrap gap-2">{res.data.related.map((m: Json) => <button key={m.slug} className="btn-quiet" onClick={() => go(m.slug)}>{m.name}</button>)}</p></>}
          {res.data.can_generate && <Card className="mt-4"><p className="text-sm">Nothing close in the verified catalog. Generating a taxonomy needs a language model, which isn't configured on this server, so no unverified content is shown.</p></Card>}
        </div>
      )}

      {res.data?.exact && (() => {
        const s = res.data.exact;
        return (
          <article className="mt-8">
            <h2 className="font-display text-3xl font-bold">{s.name} <Tag tone="good">Verified</Tag></h2>
            <p className="mt-2 text-ink-soft">{s.description}</p>
            <p className="mt-2 text-sm text-ink-faint">{s.category} · difficulty {s.difficulty}/5{s.prerequisites.length > 0 && <> · prerequisites: {s.prerequisites.map((p: Json) => p.name).join(", ")}</>}</p>

            <Section title="Learning path">
              <ol className="flex flex-wrap items-center gap-2 text-sm">{s.learning_path.map((p: Json, i: number) => <li key={p.slug} className="flex items-center gap-2">{i > 0 && <span aria-hidden>→</span>}<button className={`rounded-md border px-2 py-1 ${p.slug === s.slug ? "border-route bg-route-tint font-semibold" : "border-mist bg-white"}`} onClick={() => go(p.slug)}>{p.name}</button></li>)}</ol>
            </Section>
            <Section title="Skill graph"><SkillGraph graph={s.graph} onSelect={go} /></Section>
            {s.taxonomy && <Section title="Taxonomy"><p className="font-medium">{s.name}</p><Tree node={s.taxonomy} /></Section>}
            <Section title="Career paths"><ul className="flex flex-wrap gap-2">{s.career_paths.map((c: Json) => <li key={c.role}><Tag>{c.role}{!c.required && " (optional)"}</Tag></li>)}</ul></Section>
            <Section title="Related skills"><p className="flex flex-wrap gap-2">{s.related.map((r: Json) => <button key={r.slug} className="btn-quiet px-3 py-1 text-sm" onClick={() => go(r.slug)}>{r.name}</button>)}</p></Section>
            <div className="grid gap-6 sm:grid-cols-2">
              <Section title="Projects (demo)"><ul className="space-y-1 text-sm">{s.projects.map((p: Json) => <li key={p.key}>{p.title} <Tag>{p.difficulty}</Tag></li>)}{s.projects.length === 0 && <li className="text-ink-faint">None yet</li>}</ul></Section>
              <Section title="Jobs (demo)"><ul className="space-y-1 text-sm">{s.jobs.map((j: Json) => <li key={j.key}>{j.title}, {j.company}</li>)}{s.jobs.length === 0 && <li className="text-ink-faint">None yet</li>}</ul></Section>
            </div>
            <p className="mt-6 text-sm text-ink-soft">{s.questions} interview questions for this skill. {s.docs_url && <a className="text-route underline" href={s.docs_url} target="_blank" rel="noreferrer">Official docs</a>} · <Link to={`/learn?skill=${s.slug}`} className="text-route underline">Learn this skill</Link></p>
          </article>
        );
      })()}
    </div>
  );
}
