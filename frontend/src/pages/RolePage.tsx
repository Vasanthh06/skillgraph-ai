import RolePicker from "../components/RolePicker";
import CareerTabs from "../components/CareerTabs";
import { PageTitle } from "../components/ui";

export default function RolePage() {
  return (
    <div className="max-w-3xl">
      <CareerTabs />
      <PageTitle title="Target role" />
      <RolePicker />
    </div>
  );
}
