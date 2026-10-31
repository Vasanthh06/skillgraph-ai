import { useEffect, useMemo, useState } from "react";
import CareerTabs from "../components/CareerTabs";
import { Link, useSearchParams } from "react-router-dom";
import Avatar from "../components/Avatar";
import SaveBar from "../components/SaveBar";
import { useProfile } from "../hooks/useProfile";
import { useQueryClient } from "@tanstack/react-query";
import { useMutation } from "@tanstack/react-query";
import { api } from "../services/api";
import { useDirtyFlag } from "../store/dirty";
import { useNotice } from "../store/notice";
import type { EducationLevel, ExperienceLevel, Profile as ProfileT, ProfileUpdate } from "../types";

const EDUCATION: [EducationLevel, string][] = [["high_school", "High school"], ["diploma", "Diploma"], ["bachelors", "Bachelor's"], ["masters", "Master's"], ["phd", "PhD"], ["other", "Other"]];
const EXPERIENCE: [ExperienceLevel, string][] = [["fresher", "Fresher"], ["internship", "Internship"], ["0-1", "0–1 years"], ["1-3", "1–3 years"], ["3-5", "3–5 years"], ["5+", "5+ years"]];
const ROLE_SUGGESTIONS = ["Software Developer", "Full Stack Developer", "Data Scientist", "Data Analyst", "Machine Learning Engineer", "AI Engineer", "Cloud Engineer", "DevOps Engineer", "Cybersecurity Analyst", "UI/UX Designer"];

const FIELDS = ["full_name", "phone", "location", "linkedin_url", "github_url", "portfolio_url", "degree", "university", "graduation_year", "education_level", "experience_level", "target_role"] as const;
type Field = (typeof FIELDS)[number];
type Form = Record<Field, string>;

const toForm = (p: ProfileT): Form => Object.fromEntries(FIELDS.map((k) => [k, p[k] == null ? "" : String(p[k])])) as Form;

export default function Profile() {
  const { data: p, isLoading } = useProfile();
  const [params] = useSearchParams();
  const qc = useQueryClient();
  const { notify } = useNotice();
  // The draft holds ONLY fields the user edited. What the form shows is: saved value, overridden by the draft.
  const [draft, setDraft] = useState<Partial<Form>>({});
  const [photo, setPhoto] = useState<File | null>(null);
  const preview = useMemo(() => (photo ? URL.createObjectURL(photo) : null), [photo]);
  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview); }, [preview]);

  const base = p ? toForm(p) : null;
  const edits = useMemo(() => (base ? (Object.keys(draft) as Field[]).filter((k) => (draft[k] ?? "") !== base[k]) : []), [draft, base]);
  const count = edits.length + (photo ? 1 : 0);
  useDirtyFlag("/profile", "Profile", count > 0);

  const save = useMutation({
    mutationFn: async () => {
      if (photo) await api.uploadPhoto(photo);
      if (edits.length) {
        const body: Record<string, unknown> = {};
        for (const k of edits) body[k] = k === "graduation_year" ? (draft[k] ? Number(draft[k]) : null) : (draft[k] ? draft[k] : null);
        if (!draft.full_name && edits.includes("full_name")) delete body.full_name;   // the name can't be blank
        return api.updateProfile(body as ProfileUpdate);
      }
      return api.profile();
    },
    onSuccess: () => {
      setDraft({}); setPhoto(null);
      qc.invalidateQueries();
      notify(edits.includes("target_role") ? "Profile saved. Your target role changed, so everything has been recalculated." : "Profile saved.");
    },
  });

  if (isLoading || !p || !base) return <p className="text-ink-soft">Loading your profile…</p>;

  const val = (k: Field) => draft[k] ?? base[k];
  const set = (k: Field) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const v = e.target.value;
    setDraft((d) => { const n = { ...d }; if (v === base[k]) delete n[k]; else n[k] = v; return n; });
  };
  const err = (save.error as Error | null)?.message;

  return (
    <div className="max-w-2xl">
      <CareerTabs />
      <h1 className="text-3xl font-bold">{params.get("onboarding") ? "Set up your profile" : "Your profile"}</h1>
      {!p.profile_complete && <p className="mt-2 text-ink-soft">Still needed: {p.missing_fields.join(", ")}.</p>}
      <p className="mt-2 text-sm text-ink-soft">Edit the fields, then press <b>Save</b>. Nothing changes until you do.</p>

      <div className="mt-8 flex items-center gap-4">
        {preview ? <img src={preview} alt="" className="h-[72px] w-[72px] rounded-full object-cover" /> : <Avatar name={p.full_name} src={p.photo_url} size={72} />}
        <div>
          <input type="file" accept="image/png,image/jpeg,image/webp" className="sr-only" id="photo" onChange={(e) => { const f = e.target.files?.[0]; if (f) setPhoto(f); e.target.value = ""; }} />
          <label htmlFor="photo" className="btn-quiet cursor-pointer">{photo ? "Choose another photo" : "Change photo"}</label>
          <p className="mt-1 text-xs text-ink-faint">{photo ? "New photo selected, not saved yet." : "PNG, JPEG or WebP, up to 2 MB."}</p>
        </div>
      </div>

      <form onSubmit={(e) => { e.preventDefault(); if (count) save.mutate(); }} className="mt-8 space-y-10" noValidate>
        <fieldset className="space-y-4">
          <legend className="text-xl font-bold">Personal</legend>
          <Text id="full_name" label="Full name" v={val("full_name")} on={set("full_name")} />
          <div><label className="label" htmlFor="email">Email</label><input id="email" className="field bg-fog" value={p.email} readOnly /></div>
          <div className="grid gap-4 sm:grid-cols-2">
            <Text id="location" label="Location" v={val("location")} on={set("location")} />
            <Text id="phone" label="Phone (optional)" v={val("phone")} on={set("phone")} type="tel" />
          </div>
          <Text id="linkedin_url" label="LinkedIn (optional)" v={val("linkedin_url")} on={set("linkedin_url")} type="url" ph="https://" />
          <Text id="github_url" label="GitHub (optional)" v={val("github_url")} on={set("github_url")} type="url" ph="https://" />
          <Text id="portfolio_url" label="Portfolio (optional)" v={val("portfolio_url")} on={set("portfolio_url")} type="url" ph="https://" />
        </fieldset>
        <fieldset className="space-y-4">
          <legend className="text-xl font-bold">Education and experience</legend>
          <div className="grid gap-4 sm:grid-cols-2">
            <Select id="education_level" label="Education level" v={val("education_level")} on={set("education_level")} options={EDUCATION} />
            <Text id="graduation_year" label="Graduation year" v={val("graduation_year")} on={set("graduation_year")} type="number" />
            <Text id="degree" label="Degree" v={val("degree")} on={set("degree")} />
            <Text id="university" label="University" v={val("university")} on={set("university")} />
          </div>
          <Select id="experience_level" label="Experience" v={val("experience_level")} on={set("experience_level")} options={EXPERIENCE} />
        </fieldset>
        <fieldset className="space-y-2">
          <legend className="text-xl font-bold">Career goal</legend>
          <label className="label" htmlFor="target_role">Target role</label>
          <input id="target_role" list="roles" className="field" value={val("target_role")} onChange={set("target_role")} placeholder="e.g. Machine Learning Engineer" />
          <datalist id="roles">{ROLE_SUGGESTIONS.map((r) => <option key={r} value={r} />)}</datalist>
          <p className="text-xs text-ink-faint">Changing your role recalculates your gap, roadmap, jobs and interview prep when you save. Your skills are kept. <Link to="/role" className="underline">Browse role cards</Link>.</p>
        </fieldset>
        <SaveBar count={count} saving={save.isPending} saveLabel="Save profile" onSave={() => save.mutate()} onDiscard={() => { setDraft({}); setPhoto(null); }} error={err} />
        <p className="text-sm"><Link to="/assessment" className="text-route underline">Next: assess your skills</Link></p>
      </form>
    </div>
  );
}

function Text({ id, label, v, on, type = "text", ph }: { id: string; label: string; v: string; on: (e: React.ChangeEvent<HTMLInputElement>) => void; type?: string; ph?: string }) {
  return <div><label className="label" htmlFor={id}>{label}</label><input id={id} type={type} className="field" value={v} onChange={on} placeholder={ph} /></div>;
}
function Select({ id, label, v, on, options }: { id: string; label: string; v: string; on: (e: React.ChangeEvent<HTMLSelectElement>) => void; options: [string, string][] }) {
  return (
    <div><label className="label" htmlFor={id}>{label}</label>
      <select id={id} className="field" value={v} onChange={on}><option value="">Select…</option>{options.map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select></div>
  );
}
