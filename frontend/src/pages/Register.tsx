import { useMutation } from "@tanstack/react-query";
import { useState, type FormEvent, type KeyboardEvent } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import FormError from "../components/FormError";
import AuthLayout from "../layouts/AuthLayout";
import { api } from "../services/api";
import { useAuth } from "../store/auth";

export default function Register() {
  const { user, loading, signIn } = useAuth();
  const navigate = useNavigate();
  const [f, setF] = useState({ full_name: "", email: "", password: "", confirm_password: "", adult_eligible: false, terms_accepted: false });
  const [clientError, setClientError] = useState<string | null>(null);

  const m = useMutation({
    mutationFn: api.register,
    onSuccess: (t) => { signIn(t); navigate("/profile?onboarding=1", { replace: true }); },
  });

  if (loading) return <AuthLayout title="Create your account" subtitle="Next you'll set up your profile and choose a target role."><p role="status" className="text-ink-soft">Loading…</p></AuthLayout>;
  if (user) return <Navigate to="/dashboard" replace />;

  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement>) => setF({ ...f, [k]: e.target.value });

  // Click-driven like Login (see there): native form submission is blocked in sandboxed
  // preview frames without `allow-forms`, so a type="submit" button would do nothing at all.
  const doRegister = () => {
    if (f.password !== f.confirm_password) return setClientError("Passwords do not match.");
    setClientError(null);
    m.mutate({ ...f, full_name: f.full_name.trim(), email: f.email.trim().toLowerCase() });
  };
  const submit = (e: FormEvent) => { e.preventDefault(); doRegister(); };
  const onEnter = (e: KeyboardEvent<HTMLFormElement>) => {
    if (e.key === "Enter" && e.target instanceof HTMLInputElement) { e.preventDefault(); doRegister(); }
  };

  return (
    <AuthLayout title="Create your account" subtitle="Next you'll set up your profile and choose a target role.">
      <form onSubmit={submit} onKeyDown={onEnter} className="space-y-4" noValidate>
        <div>
          <label className="label" htmlFor="name">Full name</label>
          <input id="name" className="field" autoComplete="name" required value={f.full_name} onChange={set("full_name")} />
        </div>
        <div>
          <label className="label" htmlFor="email">Email</label>
          <input id="email" type="email" className="field" autoComplete="email" required value={f.email} onChange={set("email")} />
        </div>
        <div>
          <label className="label" htmlFor="pw">Password</label>
          <input id="pw" type="password" className="field" autoComplete="new-password" required value={f.password} onChange={set("password")} aria-describedby="pw-hint" />
          <p id="pw-hint" className="mt-1 text-xs text-ink-faint">Use 15–128 characters. Spaces and passphrases are welcome.</p>
        </div>
        <div>
          <label className="label" htmlFor="pw2">Confirm password</label>
          <input id="pw2" type="password" className="field" autoComplete="new-password" required value={f.confirm_password} onChange={set("confirm_password")} />
        </div>
        <label className="flex gap-3 text-sm"><input type="checkbox" checked={f.adult_eligible} onChange={e => setF({...f, adult_eligible: e.target.checked})} /> I am at least 18 years old.</label>
        <label className="flex gap-3 text-sm"><input type="checkbox" checked={f.terms_accepted} onChange={e => setF({...f, terms_accepted: e.target.checked})} /> <span>I accept the <Link to="/terms" className="underline">terms</Link> and acknowledge the <Link to="/privacy" className="underline">privacy notice</Link>.</span></label>
        <FormError message={clientError ?? (m.error as Error | null)?.message} />
        <button type="button" onClick={doRegister} className="btn w-full" disabled={m.isPending}>{m.isPending ? "Creating account…" : "Create account"}</button>
      </form>
      <p className="mt-6 text-sm text-ink-soft">
        Already have an account? <Link to="/login" className="font-semibold text-route underline">Log in</Link>
      </p>
    </AuthLayout>
  );
}
