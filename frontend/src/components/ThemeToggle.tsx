import { Link } from "react-router-dom";
import { useTheme } from "../store/theme";

export default function ThemeToggle() {
  const {resolved, setPreference} = useTheme();
  const dark = resolved === "dark";
  return <button type="button" role="switch" aria-label="Dark mode" aria-checked={dark}
    title={dark ? "Switch to light mode" : "Switch to dark mode"} className="theme-toggle"
    onClick={() => setPreference(dark ? "light" : "dark")}>
    <span className="theme-toggle-track" aria-hidden="true">
      <span className="theme-toggle-thumb" />
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><circle cx="12" cy="12" r="3.5" /><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5" /></svg>
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M20 14.5A8.5 8.5 0 0 1 9.5 4 8.5 8.5 0 1 0 20 14.5Z" /></svg>
    </span>
  </button>;
}
export function ThemeBar() {
  return <div className="theme-bar"><div className="theme-bar-inner">
    <Link to="/" className="inline-flex items-center gap-2 text-xs font-semibold"><span className="brand-glyph" aria-hidden="true">S</span><span>SkillGraph <span className="text-route">AI</span></span></Link>
    <ThemeToggle />
  </div></div>;
}
