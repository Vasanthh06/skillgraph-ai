import { Navigate, Route, Routes } from "react-router-dom";
import ProtectedRoute from "./components/ProtectedRoute";
import AppLayout from "./layouts/AppLayout";
import Dashboard from "./pages/Dashboard";
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import Onboarding from "./pages/Onboarding";
import SkillGap from "./pages/SkillGap";
import Roadmap from "./pages/Roadmap";
import Learn from "./pages/Learn";
import Jobs from "./pages/Jobs";
import Interview from "./pages/Interview";
import Resume from "./pages/Resume";
import Explore from "./pages/Explore";
import Assessment from "./pages/Assessment";
import RolePage from "./pages/RolePage";
import Projects from "./pages/Projects";
import SkillGraph from "./pages/SkillGraph";
import Profile from "./pages/Profile";
import Register from "./pages/Register";

import AccountSecurity from "./pages/AccountSecurity";
import Admin from "./pages/Admin";
import Legal from "./pages/Legal";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/account/forgot" element={<AccountSecurity />} />
      <Route path="/account/reset" element={<AccountSecurity />} />
      <Route path="/account/verify" element={<AccountSecurity />} />
      <Route path="/privacy" element={<Legal />} />
      <Route path="/terms" element={<Legal />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route path="/admin" element={<Admin />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/profile" element={<Profile />} />
          <Route path="/onboarding" element={<Onboarding />} />
          <Route path="/assessment" element={<Assessment />} />
          <Route path="/role" element={<RolePage />} />
          <Route path="/skill-graph" element={<SkillGraph />} />
          <Route path="/projects" element={<Projects />} />
          <Route path="/skill-gap" element={<SkillGap />} />
          <Route path="/roadmap" element={<Roadmap />} />
          <Route path="/learn" element={<Learn />} />
          <Route path="/jobs" element={<Jobs />} />
          <Route path="/interview" element={<Interview />} />
          <Route path="/resume" element={<Resume />} />
          <Route path="/explore" element={<Explore />} />






        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
