import ResumePanel from "../components/ResumePanel";
import { PageTitle } from "../components/ui";

export default function Resume() {
  return (
    <div className="max-w-3xl">
      <PageTitle title="Resume Analysis" sub="Checked against your target role. You review what we extracted and press Save before it affects your profile. Suggestions only ever ask you to add things you genuinely did." />
      <ResumePanel />
    </div>
  );
}
