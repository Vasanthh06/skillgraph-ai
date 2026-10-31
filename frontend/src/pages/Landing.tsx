import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../store/auth";
import IllustrativeGraph from "../components/IllustrativeGraph";

const STEPS = [
  ["Define your goal", "Choose a career role to give your learning a direction.", "◎"],
  ["Map your skills", "Add your resume or assess what you already know.", "⌘"],
  ["Discover the gaps", "Compare your evidence with the skills your role needs.", "◌"],
  ["Build your roadmap", "See a learning order that respects prerequisites.", "↗"],
  ["Track your progress", "Save completed steps and return to your learning path.", "✓"],
  ["Find your next step", "Understand what to learn next, and why it matters.", "→"],
];
const BENEFITS = [
  ["A direction, not another to-do list", "Your selected role gives context to the skills you're building.", "01"],
  ["See how the pieces connect", "Visualize foundations, prerequisites and the skills they unlock.", "02"],
  ["Pick up where you left off", "Your dashboard brings evidence, progress and next actions together.", "03"],
];
const PREVIEW = [
  {name:"Foundations", label:"Start with the essentials", skills:["HTML & CSS", "JavaScript fundamentals", "Git & version control"], description:"Build a reliable base before choosing frameworks and tools."},
  {name:"Build & connect", label:"Turn knowledge into working features", skills:["Component-based interfaces", "APIs & data modeling", "Account security"], description:"Connect the interface, application logic and persistent data."},
  {name:"Apply & refine", label:"Put the pieces together", skills:["Portfolio project", "Testing & debugging", "Deployment & review"], description:"Apply the skill relationships in an end-to-end learning project."},
];
export default function Landing() {
  const {user} = useAuth();
  const root = useRef<HTMLDivElement>(null);
  const [stage, setStage] = useState(0);
  const start = user ? "/dashboard" : "/register";
  useEffect(() => {
    if (matchMedia("(prefers-reduced-motion: reduce)").matches || !('IntersectionObserver' in window)) return;
    const observer = new IntersectionObserver(entries => entries.forEach(entry => {
      if (entry.isIntersecting) { entry.target.setAttribute("data-visible", "true"); observer.unobserve(entry.target); }
    }), {threshold:.08});
    root.current?.querySelectorAll('[data-reveal]').forEach(element => {element.setAttribute('data-visible','false');observer.observe(element);});
    return () => observer.disconnect();
  }, []);
  return <div ref={root} className="product-landing">
    <header className="landing-nav content-width">
      <Link to="/" className="flex items-center gap-2.5" aria-label="SkillGraph AI home"><img src="/logo-mark.png" alt="" className="h-10 w-10" /><span className="text-lg font-bold">SkillGraph <span className="text-route">AI</span></span></Link>
      <nav aria-label="Product" className="flex flex-wrap items-center gap-2"><a href="#how-it-works" className="hidden px-3 text-sm text-ink-soft hover:text-route lg:inline">How it works</a><a href="#methodology" className="hidden px-3 text-sm text-ink-soft hover:text-route lg:inline">Our approach</a><Link className="btn-quiet" to={user?"/dashboard":"/login"}>{user?"Dashboard":"Sign in"}</Link><Link className="btn hidden sm:inline-flex" to={start}>{user?"Continue learning":"Get started"}<span aria-hidden="true">↗</span></Link></nav>
    </header>
    <main>
      <section className="hero-section content-width" aria-labelledby="hero-title">
        <div className="hero-copy">
          <div className="hero-kicker"><span className="status-dot" aria-hidden="true" />A clearer path from skills to goals</div>
          <h1 id="hero-title">Your skills.<br />Your direction.<br /><span className="gradient-text">A path forward.</span></h1>
          <p className="hero-description">Turn what you know into what comes next. Discover your skill gaps and follow a structured learning roadmap toward your career goal.</p>
          <div className="mt-7 flex flex-wrap gap-3"><Link to={start} className="btn hero-cta">{user?"Open my dashboard":"Build my roadmap"}<span aria-hidden="true">→</span></Link><a href="#how-it-works" className="btn-quiet hero-cta">Explore how it works<span aria-hidden="true">↓</span></a></div>
          <div className="hero-notes"><span>✓ Prerequisite-aware</span><span>✓ Explained recommendations</span><span>✓ Saved progress</span></div>
          <p className="mt-4 text-xs text-ink-faint">Built around your evidence. No promises of job placement.</p>
        </div>
        <div className="hero-visual"><div className="hero-orbit" aria-hidden="true" /><IllustrativeGraph /><div className="graph-floating-label" aria-hidden="true"><span>↗</span><div><strong>Build on your foundations</strong><small>Every connection has a purpose</small></div></div></div>
      </section>
      <div className="content-width"><div className="product-strip"><span>ONE CONNECTED LEARNING JOURNEY</span><span>Skills <b>→</b> Gaps <b>→</b> Roadmap <b>→</b> Progress</span></div></div>
      <section className="content-width landing-section" aria-labelledby="problem-title" data-reveal>
        <div className="section-intro"><p className="eyebrow">From scattered learning to clear priorities</p><h2 id="problem-title">Knowing what to learn<br />shouldn't be the hardest part.</h2><p>It's easy to collect courses. It's harder to see what you already know, what's missing, and which foundation needs attention first.</p></div>
        <div className="problem-grid"><div className="problem-before"><p className="eyebrow">Without a clear map</p><div className="scattered-list"><span>Another tutorial?</span><span>What comes first?</span><span>Am I missing a skill?</span><span>Where did I stop?</span></div><p className="text-sm text-ink-soft">Scattered resources. Uncertain priorities.</p></div><div className="problem-after"><span className="feature-icon" aria-hidden="true">↗</span><h3 className="text-xl font-bold">A learning path with context.</h3><p className="mt-2 text-sm leading-relaxed text-ink-soft">Compare your skills with a target role, understand the prerequisites, and make the next step a deliberate one.</p><Link to={start} className="mt-5 inline-flex text-sm font-semibold text-route">Find my next step <span className="ml-2" aria-hidden="true">→</span></Link></div></div>
      </section>
      <section id="how-it-works" className="landing-section workflow-section" aria-labelledby="workflow-title"><div className="content-width" data-reveal><div className="section-intro"><p className="eyebrow">A simple, connected workflow</p><h2 id="workflow-title">Your ambition, with a plan.</h2><p>Start with a goal. Build your evidence. Keep moving with a roadmap you can return to.</p></div><ol className="workflow-grid">{STEPS.map(([title,description,icon],i)=><li key={title} className="workflow-card"><div className="flex items-center justify-between"><span className="feature-icon" aria-hidden="true">{icon}</span><span className="step-number">0{i+1}</span></div><h3>{title}</h3><p>{description}</p></li>)}</ol></div></section>
      <section className="landing-section content-width" aria-labelledby="benefits-title" data-reveal><div className="section-intro"><p className="eyebrow">Purposeful by design</p><h2 id="benefits-title">Less guessing. More understanding.</h2></div><div className="benefit-grid">{BENEFITS.map(([title,description,index])=><article className="benefit-card" key={index}><span className="benefit-index">{index}</span><h3>{title}</h3><p>{description}</p></article>)}</div></section>
      <section className="landing-section content-width roadmap-showcase" aria-labelledby="preview-title" data-reveal>
        <div><p className="eyebrow">See the path, not just the destination</p><h2 id="preview-title">Big goals.<br />Manageable steps.</h2><p className="mt-4 max-w-sm text-ink-soft">Move from foundations to application. Your own roadmap uses your selected role and stored skill evidence.</p><Link to={start} className="btn mt-6">{user?"Continue my roadmap":"Create my own roadmap"}<span aria-hidden="true">→</span></Link></div>
        <div className="preview-card"><div className="flex flex-wrap items-center justify-between gap-3"><div><p className="eyebrow">Example learning direction</p><h3 className="mt-1 text-lg font-bold">Full-stack development</h3></div><span className="sample-badge">Illustrative · not your results</span></div>
          <div className="preview-stages" role="group" aria-label="Explore example roadmap stage">{PREVIEW.map((s,i)=><button key={s.name} type="button" aria-pressed={stage===i} onClick={()=>setStage(i)}><span>0{i+1}</span>{s.name}</button>)}</div>
          <div className="preview-detail" aria-live="polite"><p className="text-sm font-semibold">{PREVIEW[stage].label}</p><p className="mt-1 text-xs text-ink-soft">{PREVIEW[stage].description}</p><ol>{PREVIEW[stage].skills.map((skill,i)=><li key={skill}><span aria-hidden="true">{i+1}</span><strong>{skill}</strong><span className="text-xs text-ink-faint">Suggested order</span></li>)}</ol></div><div className="preview-order"><span>Foundations</span><span className="preview-line" aria-hidden="true"><i style={{width:`${(stage+1)/3*100}%`}} /></span><span>Application</span></div><p className="mt-2 text-[11px] text-ink-faint">The indicator shows the example stage selected, not personal completion.</p>
        </div>
      </section>
      <section id="methodology" className="content-width landing-section" aria-labelledby="method-title" data-reveal><div className="method-panel"><div><p className="eyebrow">Transparent by design</p><h2 id="method-title">Not a black box.<br />A connected skill model.</h2><p className="mt-4 text-ink-soft">The main recommendation engine uses documented rules over a curated skill dependency graph and your stored evidence. See the gaps, explore the connections, and understand why a step is prioritized.</p></div><ol className="method-list"><li><span>01</span><div><h3>Compare the evidence</h3><p>Combine self-assessment, resume and learning activity into a skill profile.</p></div></li><li><span>02</span><div><h3>Respect the foundations</h3><p>Use prerequisites and role priorities to order learning steps.</p></div></li><li><span>03</span><div><h3>Keep your progress connected</h3><p>Persist your progress and refresh recommendations as your evidence changes.</p></div></li></ol></div></section>
      <section className="content-width landing-section" data-reveal><div className="final-cta"><p className="eyebrow">Clarity is a good place to start</p><h2>Your next step starts with<br />knowing what to learn.</h2><p>Your goals are personal. Your learning path should have context, too.</p><div className="mt-6 flex flex-wrap justify-center gap-3"><Link to={start} className="btn hero-cta">{user?"Go to my dashboard":"Create your account"} <span aria-hidden="true">→</span></Link><Link to={user?"/roadmap":"/login"} className="btn-quiet hero-cta">{user?"View my roadmap":"Sign in"}</Link></div></div></section>
    </main>
    <footer className="content-width landing-footer"><div className="flex items-center gap-2"><img src="/logo-mark.png" alt="" className="h-7 w-7" /><span className="text-sm font-bold">SkillGraph AI</span></div><p>Skills, connected to your next step.</p><nav aria-label="Legal"><Link to="/privacy">Privacy</Link><Link to="/terms">Terms</Link></nav><p className="footer-note">Academic project · Guidance, not a guarantee of career outcomes.</p></footer>
  </div>;
}
