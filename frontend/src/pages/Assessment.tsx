import AssessmentForm from "../components/AssessmentForm";
import CareerTabs from "../components/CareerTabs";
import { PageTitle } from "../components/ui";

export default function Assessment() {
  return (
    <div className="max-w-3xl">
      <CareerTabs />
      <PageTitle title="Skill assessment" sub="Update what you know at any time. Your readiness, gaps and roadmap are recalculated when you save." />
      <AssessmentForm />
    </div>
  );
}
