import { useEffect, useRef, useState } from "react";

/** True when the user asked the OS/browser for reduced motion. Every animation in the app checks this. */
export function useReducedMotion(): boolean {
  const query = "(prefers-reduced-motion: reduce)";
  const [reduced, setReduced] = useState<boolean>(() => typeof window !== "undefined" && !!window.matchMedia?.(query).matches);
  useEffect(() => {
    if (!window.matchMedia) return;
    const mq = window.matchMedia(query);
    const on = () => setReduced(mq.matches);
    mq.addEventListener("change", on);
    return () => mq.removeEventListener("change", on);
  }, []);
  return reduced;
}

/**
 * Eases a displayed number toward `target`. The first time a real value arrives it counts up from 0; afterwards it
 * animates from whatever was last shown. With reduced motion it simply returns the target. Never invents a value:
 * the final number is always exactly `target`.
 */
export function useCountUp(target: number, duration = 800): number {
  const reduced = useReducedMotion();
  const [shown, setShown] = useState<number>(reduced ? target : 0);
  const last = useRef<number>(reduced ? target : 0);
  useEffect(() => {
    if (reduced) { last.current = target; setShown(target); return; }
    const from = last.current;
    if (from === target) { setShown(target); return; }
    const start = performance.now();
    let raf = 0;
    const tick = (t: number) => {
      const k = Math.min(1, (t - start) / duration);
      const v = Math.round(from + (target - from) * (1 - Math.pow(1 - k, 3)));
      last.current = v;
      setShown(v);
      if (k < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, duration, reduced]);
  return shown;
}
