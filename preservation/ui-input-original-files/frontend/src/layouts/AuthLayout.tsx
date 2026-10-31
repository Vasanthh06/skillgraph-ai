import { Link } from "react-router-dom";
import type { ReactNode } from "react";

const STOPS = [
  { q: "Where am I?", d: "Your skills, scored from what you know and what you've shown." },
  { q: "Where do I want to go?", d: "One target role, changeable any time." },
  { q: "Am I ready?", d: "Readiness, job match and interview score in one place." },
];

export default function AuthLayout({ title, subtitle, children }: { title: string; subtitle: string; children: ReactNode }) {
  return (
    <div className="grid min-h-screen md:grid-cols-[minmax(0,5fr)_minmax(0,6fr)]">
      <aside className="relative hidden flex-col justify-between overflow-hidden border-r border-mist bg-[#070C22]/80 px-12 py-12 md:flex">
        <div aria-hidden className="pointer-events-none absolute -right-24 -top-24 h-72 w-72 rounded-full bg-glow-violet/25 blur-3xl" />
        <Link to="/" aria-label="SkillGraph AI home"><img src="/logo-full-dark.png" alt="SkillGraph AI" className="w-60 drop-shadow-[0_0_24px_rgba(124,92,255,0.45)]" /></Link>
        <div className="relative">
          <h2 className="max-w-sm font-display text-4xl font-bold leading-tight">Understand your skills. Discover your gaps. <span className="gradient-text">Build your career.</span></h2>
          <ol className="relative mt-10 space-y-7 pl-8">
            <span aria-hidden className="absolute left-[7px] top-2 h-[calc(100%-1rem)] w-0.5 bg-gradient-to-b from-glow-cyan/60 to-glow-violet/20" />
            {STOPS.map((s, i) => (
              <li key={s.q} className="relative">
                <span aria-hidden className={`absolute -left-8 top-1 h-4 w-4 rounded-full border-2 ${i === 0 ? "border-glow-cyan bg-glow-cyan shadow-glow-cyan" : "border-glow-violet/70 bg-[#070C22]"}`} />
                <p className="font-medium">{s.q}</p>
                <p className="text-sm text-ink-soft">{s.d}</p>
              </li>
            ))}
          </ol>
        </div>
        <p className="relative text-sm text-ink-faint">Intelligent Skill, Career &amp; Learning Recommendation Platform</p>
      </aside>
      <main className="flex items-center justify-center px-6 py-12">
        <div className="w-full max-w-md">
          <Link to="/" className="mb-6 block md:hidden" aria-label="SkillGraph AI home"><img src="/logo-full-dark.png" alt="SkillGraph AI" className="mx-auto w-44" /></Link>
          <div className="rounded-3xl border border-mist bg-white/80 p-7 shadow-glow backdrop-blur">
            <h1 className="text-3xl font-bold">{title}</h1>
            <p className="mt-2 text-ink-soft">{subtitle}</p>
            <div className="mt-7">{children}</div>
          </div>
        </div>
      </main>
    </div>
  );
}
