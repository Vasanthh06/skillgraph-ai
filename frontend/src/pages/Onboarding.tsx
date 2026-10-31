import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import AssessmentForm from "../components/AssessmentForm";
import ResumePanel from "../components/ResumePanel";
import RolePicker from "../components/RolePicker";
import { PageTitle } from "../components/ui";
import { useGet } from "../hooks/useApi";
import type { Json } from "../types/api";

type Step = "role" | "assess" | "resume";

export default function Onboarding() {
  const profile = useGet<Json>("/profile");
  const nav = useNavigate();
  const [step, setStep] = useState<Step>("role");
  // Start on the first step that still needs doing, but never jump away while the user is mid-step.
  useEffect(() => { if (profile.data?.target_role && step === "role") setStep("assess"); }, [profile.data?.target_role]); // eslint-disable-line react-hooks/exhaustive-deps
  const steps: [Step, string][] = [["role", "Target role"], ["assess", "What you know"], ["resume", "Resume (optional)"]];

  return (
    <div className="max-w-3xl">
      <PageTitle title="Let's understand where you are" sub="Pick a role, tell us what you already know, and optionally add a resume. Each step has a Save button; nothing is applied until you press it." />
      <ol className="mb-8 flex gap-6 text-sm" aria-label="Steps">
        {steps.map(([k, l], i) => (
          <li key={k} className={step === k ? "font-semibold text-route" : "text-ink-faint"} aria-current={step === k ? "step" : undefined}>{i + 1}. {l}</li>
        ))}
      </ol>
      {step === "role" && (
        <>
          <RolePicker onSaved={() => setStep("assess")} />
          {profile.data?.target_role && <button type="button" className="btn-quiet mt-3" onClick={() => setStep("assess")}>Keep "{profile.data.target_role}" and continue</button>}
        </>
      )}
      {step === "assess" && <AssessmentForm saveLabel="Save and continue" onBack={() => setStep("role")} onSaved={() => setStep("resume")} />}
      {step === "resume" && (
        <>
          <h2 className="mb-2 text-xl font-bold">Add your resume <span className="text-sm font-normal text-ink-faint">(optional)</span></h2>
          <p className="mb-4 text-sm text-ink-soft">We extract skills and normalise names (ReactJS → React). You review them before anything is saved.</p>
          <ResumePanel />
          <button type="button" className="btn mt-8" onClick={() => nav("/dashboard")}>Go to my dashboard</button>
        </>
      )}
    </div>
  );
}
