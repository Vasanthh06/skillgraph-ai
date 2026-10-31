import { useQueryClient } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, setUnauthorizedHandler, tokenStore } from "../services/api";
import type { TokenResponse, User } from "../types";

interface AuthState {
  user: User | null;
  loading: boolean;
  signIn: (t: TokenResponse) => void;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

/**
 * Only the bearer token is kept in the browser. Who the user is comes from the server (/auth/me) on every page
 * load, so a stale or tampered local copy can never display someone else's identity or data.
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const qc = useQueryClient();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const clear = useCallback(() => {
    tokenStore.clear();
    setUser(null);
    setLoading(false);
    qc.clear(); // drop every cached response so the next account in this tab starts empty
  }, [qc]);

  useEffect(() => setUnauthorizedHandler(clear), [clear]);

  useEffect(() => {
    // Capture the token this check was started for. If the user signs in meanwhile, this
    // stale check must not overwrite the new session with its result (and its 401 must not
    // clear the new token -- services/api.ts guards that side too).
    const startedToken = tokenStore.get();
    // Always ask the server: the session is in an HttpOnly cookie.
    api.me()
      .then((u) => { if (tokenStore.get() === startedToken) { setUser(u); } })
      .catch(() => { /* 401 already cleared the session; network errors keep the token */ })
      .finally(() => setLoading(false));
  }, []);

  const value = useMemo<AuthState>(
    () => ({
      user,
      loading,
      signIn: (t) => {
        qc.clear(); // never reuse another account's cached data
        tokenStore.set(t.access_token);
        setUser(t.user);
        setLoading(false);
      },
      signOut: async () => {
        try { await api.logout(); } catch { /* token may already be invalid; clear locally regardless */ }
        clear();
      },
    }),
    [user, loading, qc, clear],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
