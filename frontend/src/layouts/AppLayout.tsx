import { useEffect, useRef, useState } from "react";
import { NavLink, Outlet, useBlocker, useLocation, useNavigate } from "react-router-dom";
import Avatar from "../components/Avatar";
import Icon, { type IconName } from "../components/Icon";
import { useProfile } from "../hooks/useProfile";
import { useAuth } from "../store/auth";
import { useDirty } from "../store/dirty";
import { useNotice } from "../store/notice";

import HistoryControls from "../components/HistoryControls";

interface Stop { to: string; label: string; icon: IconName; hub?: boolean }

// The seven primary destinations. Profile is a hub (Profile, Target Role, Assessment); the existing tools stay under "More tools".
const MAIN: Stop[] = [
  { to: "/dashboard", label: "Dashboard", icon: "dash" },
  { to: "/resume", label: "Resume Analysis", icon: "file" },
  { to: "/skill-graph", label: "Skill Graph", icon: "net" },
  { to: "/roadmap", label: "Learning Roadmap", icon: "route" },
  { to: "/jobs", label: "Job Matching", icon: "brief" },
  { to: "/projects", label: "Project Recommendations", icon: "rocket" },
  { to: "/profile", label: "Profile", icon: "user", hub: true },
];
const MORE: Stop[] = [
  { to: "/skill-gap", label: "Skill Gap", icon: "target" },
  { to: "/learn", label: "Learn & Build", icon: "book" },
  { to: "/interview", label: "Interview Prep", icon: "chat" },
  { to: "/explore", label: "Skill Explorer", icon: "compass" },
];
const HUB_PATHS = ["/profile", "/role", "/assessment", "/onboarding"];
const LABELS: Record<string, string> = Object.fromEntries([...MAIN, ...MORE].map((s) => [s.to, s.label]).concat([["/role", "Target Role"], ["/assessment", "Assessment"], ["/onboarding", "Onboarding"]]));

export default function AppLayout() {
  const { user, signOut } = useAuth();
  const { data: profile } = useProfile();
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const { message, clear } = useNotice();
  const { entries } = useDirty();
  const dirtyLabels = [...new Set(Object.values(entries))];
  const blocker = useBlocker(({currentLocation, nextLocation}) => dirtyLabels.length > 0 && (currentLocation.pathname !== nextLocation.pathname || currentLocation.search !== nextLocation.search));
  const stayRef = useRef<HTMLButtonElement>(null);
  const returnFocus = useRef<HTMLElement | null>(null);
  useEffect(() => {
    if (blocker.state === "blocked") {
      returnFocus.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
      stayRef.current?.focus();
    } else if (returnFocus.current?.isConnected) {
      returnFocus.current.focus();
      returnFocus.current = null;
    }
  }, [blocker.state]);
  const [collapsed, setCollapsed] = useState(false);   // a view preference only; kept in memory, not stored
  // Sidebar navigation never silently discards unsaved edits: ask first.
  // useBlocker guards links, history buttons AND native browser Back/Forward.
  const hubDirty = Object.keys(entries).some((k) => HUB_PATHS.includes(k));
  const page = pathname === "/admin" ? "Administration" : LABELS[pathname] ?? "SkillGraph";

  const item = (s: Stop) => {
    const active = s.hub ? HUB_PATHS.includes(pathname) : pathname === s.to || pathname.startsWith(`${s.to}/`);
    const dirty = s.hub ? hubDirty : !!entries[s.to];
    return (
      <li key={s.to} className="shrink-0">
        <NavLink to={s.to} title={s.label} aria-current={active ? "page" : undefined}
          className={`relative flex items-center gap-3 whitespace-nowrap rounded-xl border px-3 py-2 text-sm ${collapsed ? "md:justify-center md:px-0" : ""} ${
            active ? "border-mist bg-gradient-to-br from-glow-blue/30 to-glow-violet/30 font-semibold text-ink" : "border-transparent text-ink-soft hover:bg-route-tint hover:text-ink"
          }`}>
          <Icon name={s.icon} className="hidden h-[18px] w-[18px] md:block" />
          <span className={collapsed ? "md:sr-only" : ""}>{s.label}</span>
          {dirty && <span aria-label="unsaved changes" title="Unsaved changes" className={`inline-block h-2 w-2 rounded-full bg-signal shadow-[0_0_8px_#FBBF24] ${collapsed ? "md:absolute md:right-3 md:top-2" : "ml-auto"}`} />}
        </NavLink>
      </li>
    );
  };

  return (
    <div className={`min-h-screen md:grid ${collapsed ? "md:grid-cols-[4.75rem_minmax(0,1fr)]" : "md:grid-cols-[15.5rem_minmax(0,1fr)]"} transition-[grid-template-columns] duration-300`}>
      <aside className="flex flex-col border-b border-mist bg-elevated/95 backdrop-blur md:sticky md:top-14 md:h-[calc(100vh-3.5rem)] md:border-b-0 md:border-r">
        <div className={`flex items-center justify-between gap-3 px-5 py-4 md:py-5 ${collapsed ? "md:justify-center md:px-0" : ""}`}>
          <span className="flex items-center gap-2.5">
            <img src="/logo-mark.png" alt="" className="h-10 w-10 drop-shadow-[0_0_8px_rgba(124,92,255,0.5)]" />
            <span className={`font-display text-xl font-bold ${collapsed ? "md:hidden" : ""}`}>SkillGraph <span className="gradient-text">AI</span></span>
          </span>
          <span className="text-xs text-ink-faint md:hidden">{user?.full_name}</span>
        </div>

        <nav aria-label="Main" className="overflow-x-auto px-3 pb-3 md:flex-1 md:overflow-y-auto md:pb-0">
          <ol className="flex gap-1 md:block md:space-y-1">{MAIN.map(item)}</ol>
          <p className={`hidden px-3 pb-1 pt-5 text-[11px] uppercase tracking-widest text-ink-faint ${collapsed ? "" : "md:block"}`}>More tools</p>
          <ol className="flex gap-1 md:mt-1 md:block md:space-y-1">{MORE.map(item)}</ol>
        </nav>

        <button type="button" onClick={() => setCollapsed(!collapsed)} aria-pressed={collapsed} aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"} title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          className="mx-auto my-3 hidden h-9 w-9 items-center justify-center rounded-xl border border-mist hover:bg-route-tint md:flex">
          <Icon name="chev" className={`h-[18px] w-[18px] transition-transform ${collapsed ? "rotate-180" : ""}`} />
        </button>

        <div className={`hidden border-t border-mist p-4 md:block ${collapsed ? "md:px-0" : ""}`}>
          <div className={`flex items-center gap-3 ${collapsed ? "justify-center" : ""}`}>
            <Avatar name={user?.full_name ?? "?"} src={profile?.photo_url} size={38} />
            <div className={`min-w-0 ${collapsed ? "hidden" : ""}`}>
              <p className="truncate text-sm font-semibold">{user?.full_name}</p>
              <p className="truncate text-xs text-ink-faint">{profile?.target_role ?? "No target role yet"}</p>
              <button className="text-xs text-ink-faint underline hover:text-ink" onClick={async () => { await signOut(); navigate("/login"); }}>Log out</button>
            </div>
          </div>
        </div>
      </aside>

      <main className="min-w-0 px-5 py-6 md:px-10 md:py-8">
        <div className="workspace-toolbar mb-5 flex flex-wrap items-center gap-3 text-sm text-ink-soft">
          <HistoryControls />
          <span>SkillGraph / <b className="text-ink">{page}</b></span><span className="flex-1" />
          {profile?.target_role && <span className="hidden rounded-full border border-mist bg-white/80 px-3 py-0.5 text-xs sm:inline">Target: {profile.target_role}</span>}
        </div>
        {message && (
          <p role="status" className="mb-6 flex items-center justify-between rounded-xl border border-moss/40 bg-green-50 px-4 py-2 text-sm font-medium text-moss">
            <span>✓ {message}</span>
            <button type="button" className="text-xs underline" onClick={clear}>Dismiss</button>
          </p>
        )}
        {blocker.state === "blocked" && (
          <div className="dialog-backdrop" onKeyDown={e => {
            if (e.key === "Escape") blocker.reset();
            if (e.key === "Tab") {
              const buttons = e.currentTarget.querySelectorAll<HTMLButtonElement>("button");
              const first = buttons[0], last = buttons[buttons.length-1];
              if (e.shiftKey && document.activeElement === first) {e.preventDefault(); last.focus();}
              else if (!e.shiftKey && document.activeElement === last) {e.preventDefault(); first.focus();}
            }
          }}>
            <div role="alertdialog" aria-modal="true" aria-labelledby="unsaved-title" aria-describedby="unsaved-description" className="confirm-dialog">
              <p className="eyebrow">Before you go</p><h2 id="unsaved-title" className="text-xl font-bold">You have unsaved changes</h2>
              <p id="unsaved-description" className="mt-2 text-sm text-ink-soft">Your edits in {dirtyLabels.join(", ")} have not been saved. Leave this page and discard them?</p>
              <div className="mt-5 flex flex-wrap gap-2">
                <button ref={stayRef} type="button" className="btn" onClick={() => blocker.reset()}>Stay and save</button>
                <button type="button" className="btn-quiet" onClick={() => blocker.proceed()}>Leave without saving</button>
              </div>
            </div>
          </div>
        )}
        {/* keyed by path: the entrance plays when the page changes, not when data inside it changes */}
        <div key={pathname} className="page-enter"><Outlet /></div>
        <div className="mt-10 md:hidden">
          <button className="btn-quiet" onClick={async () => { await signOut(); navigate("/login"); }}>Log out</button>
        </div>
      </main>
    </div>
  );
}
