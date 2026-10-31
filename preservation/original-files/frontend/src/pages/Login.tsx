import { useMutation } from "@tanstack/react-query";
import { useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import FormError from "../components/FormError";
import AuthLayout from "../layouts/AuthLayout";
import { api } from "../services/api";
import { useAuth } from "../store/auth";

export default function Login() {
  const { user, loading, signIn } = useAuth();
  const navigate = useNavigate();
  const from = (useLocation().state as { from?: string } | null)?.from ?? "/dashboard";
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const m = useMutation({
    mutationFn: api.login,
    onSuccess: (t) => { signIn(t); navigate(from, { replace: true }); },
  });

  const formRef = useRef<HTMLFormElement>(null);

  // While the startup "is there already a valid session?" check is in flight, don't accept a
  // login yet: otherwise the two race and the stale check can resolve after the fresh login.
  // (The 401/token guards in services/api.ts + store/auth.tsx also protect this; belt & braces.)
  if (loading) return <AuthLayout title="Welcome back" subtitle="Log in to pick up where you left off."><p role="status" className="text-ink-soft">Loading…</p></AuthLayout>;
  if (user) return <Navigate to="/dashboard" replace />;

  // The primary action is a CLICK handler, not native form submission. In embedded/sandboxed
  // preview frames without `allow-forms`, the browser blocks form submission entirely
  // ("Blocked form submission ... the 'allow-forms' permission is not set") and the submit
  // handler never runs, so Log in simply stayed on this page. A button click, Enter-in-input
  // (keydown) and fetch all still work there; the form's onSubmit stays as a fallback for
  // ordinary top-level browsing. Trim/lower-case the email; never alter the password.
  const doLogin = () => {
    const f = formRef.current;
    if (f && !f.checkValidity()) { f.reportValidity(); return; }
    m.mutate({ email: email.trim().toLowerCase(), password });
  };
  const submit = (e: FormEvent) => { e.preventDefault(); doLogin(); };
  const onEnter = (e: KeyboardEvent<HTMLFormElement>) => {
    if (e.key === "Enter" && e.target instanceof HTMLInputElement) { e.preventDefault(); doLogin(); }
  };

  return (
    <AuthLayout title="Welcome back" subtitle="Log in to pick up where you left off.">
      <form ref={formRef} onSubmit={submit} onKeyDown={onEnter} className="space-y-4">
        <div>
          <label className="label" htmlFor="email">Email</label>
          <input id="email" type="email" className="field" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </div>
        <div>
          <label className="label" htmlFor="pw">Password</label>
          <input id="pw" type="password" className="field" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
        </div>
        <FormError message={(m.error as Error | null)?.message} />
        <button type="button" onClick={doLogin} className="btn w-full" disabled={m.isPending}>{m.isPending ? "Logging in…" : "Log in"}</button>
      </form>
      <p className="mt-6 text-sm text-ink-soft">
        New here? <Link to="/register" className="font-semibold text-route underline">Create an account</Link>
      </p>
    </AuthLayout>
  );
}
