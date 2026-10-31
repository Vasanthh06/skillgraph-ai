import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

type Preference = "light" | "dark" | "system";
interface Theme { preference: Preference; resolved: "light" | "dark"; setPreference: (p: Preference) => void }
const Context = createContext<Theme | null>(null);
export const THEME_KEY = "sg_theme";
const valid = (p: unknown): p is Preference => p === "light" || p === "dark" || p === "system";
export function ThemeProvider({children}: {children: ReactNode}) {
  const [preference, update] = useState<Preference>(() => {
    try { const p = localStorage.getItem(THEME_KEY); return valid(p) ? p : "system"; } catch { return "system"; }
  });
  const [systemDark, setSystemDark] = useState(() => matchMedia("(prefers-color-scheme: dark)").matches);
  const resolved = preference === "system" ? (systemDark ? "dark" : "light") : preference;
  const setPreference = (p: Preference) => {
    // Set root synchronously in the input event; React owns the single shared preference.
    document.documentElement.dataset.theme = p === "system" ? (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light") : p;
    update(p);
    try { localStorage.setItem(THEME_KEY, p); } catch { /* memory-only works when storage is blocked */ }
  };
  useEffect(() => {
    const media = matchMedia("(prefers-color-scheme: dark)");
    const change = () => setSystemDark(media.matches);
    media.addEventListener("change", change);
    const sync = (e: StorageEvent) => { if (e.key === THEME_KEY) update(valid(e.newValue) ? e.newValue : "system"); };
    window.addEventListener("storage", sync);
    return () => {media.removeEventListener("change", change); window.removeEventListener("storage", sync);};
  }, []);
  useEffect(() => {
    document.documentElement.dataset.theme = resolved;
    document.documentElement.style.colorScheme = resolved;
    document.querySelector('meta[name="theme-color"]')?.setAttribute("content", resolved === "dark" ? "#090e1d" : "#f5f7fc");
  }, [resolved]);
  return <Context.Provider value={{preference, resolved, setPreference}}>{children}</Context.Provider>;
}
export function useTheme() {
  const value = useContext(Context);
  if (!value) throw new Error("ThemeProvider required");
  return value;
}
