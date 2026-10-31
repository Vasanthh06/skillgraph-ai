import { Link, Navigate } from "react-router-dom";
import { useAuth } from "../store/auth";

const QUESTIONS = [
  ["Where am I?", "Your current skills, scored from your self-assessment and your resume together."],
  ["Where do I want to go?", "A target role with a clear list of what it takes."],
  ["What am I missing?", "A ranked skill gap, with prerequisites in the right order."],
  ["What should I do next?", "One next action, with the reason it was chosen for you."],
  ["Am I ready?", "Readiness, job match and interview score, updated as you progress."],
];

export default function Landing() {
  const { user, loading } = useAuth();
  if (loading) return null;
  if (user) return <Navigate to="/dashboard" replace />;
  return (
    <div className="mx-auto min-h-screen max-w-5xl px-6 py-10">
      <header className="flex items-center justify-between gap-3">
        <span className="flex items-center gap-2.5">
          <img src="/logo-mark.png" alt="" className="h-11 w-11 drop-shadow-[0_0_10px_rgba(124,92,255,0.55)]" />
          <span className="font-display text-xl font-bold">SkillGraph <span className="gradient-text">AI</span></span>
        </span>
        <nav className="flex gap-3">
          <Link className="btn-quiet" to="/login">Log in</Link>
          <Link className="btn" to="/register">Create account</Link>
        </nav>
      </header>
      <section className="grid items-center gap-10 py-16 md:grid-cols-[1.3fr_1fr] md:py-24">
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-glow-cyan">AI career copilot</p>
          <h1 className="mt-2 font-display text-5xl font-bold leading-[1.05] md:text-6xl">
            Understand your skills. Discover your gaps. <span className="gradient-text">Build your career.</span>
          </h1>
          <p className="mt-6 max-w-xl text-lg text-ink-soft">Pick the role you want. SkillGraph compares it with what you already know and tells you what to learn next, and why.</p>
          <Link to="/register" className="btn mt-8 px-6 py-3 text-base">Start with your target role</Link>
        </div>
        <img src="/logo-full-dark.png" alt="SkillGraph AI" className="mx-auto w-full max-w-sm drop-shadow-[0_0_40px_rgba(124,92,255,0.45)]" />
      </section>
      <section aria-label="What SkillGraph answers">
        <ol className="relative max-w-2xl space-y-6 border-l-2 border-mist pl-8">
          {QUESTIONS.map(([q, a]) => (
            <li key={q} className="relative">
              <span aria-hidden className="absolute -left-[41px] top-1.5 h-4 w-4 rounded-full border-2 border-glow-violet bg-fog shadow-glow" />
              <h2 className="text-xl font-bold">{q}</h2>
              <p className="text-ink-soft">{a}</p>
            </li>
          ))}
        </ol>
      </section>
    </div>
  );
}
