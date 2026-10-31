import { createContext, useCallback, useContext, useMemo, useRef, useState, type ReactNode } from "react";

interface NoticeState { message: string | null; notify: (m: string) => void; clear: () => void }
const Ctx = createContext<NoticeState | null>(null);

/** A single "Saved" confirmation shown after any save, so the user always sees that something was kept. */
export function NoticeProvider({ children }: { children: ReactNode }) {
  const [message, setMessage] = useState<string | null>(null);
  const timer = useRef<number | undefined>(undefined);
  const clear = useCallback(() => setMessage(null), []);
  const notify = useCallback((m: string) => {
    setMessage(m);
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => setMessage(null), 6000);
  }, []);
  const value = useMemo(() => ({ message, notify, clear }), [message, notify, clear]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useNotice(): NoticeState {
  const c = useContext(Ctx);
  if (!c) throw new Error("useNotice must be used inside NoticeProvider");
  return c;
}
