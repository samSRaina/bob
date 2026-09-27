import { useState } from "react";
import Navbar from "./components/Navbar";
import DashboardSummary from "./components/DashboardSummary";
import RepeatOffenderList from "./components/RepeatOffenderList";
import CrimeGraphView from "./components/CrimeGraphView";
import SuspectSidePanel from "./components/SuspectSidePanel";

export default function App() {
  // Bumping refreshKey re-triggers every panel's fetch — used both when the
  // Role Switcher changes (RBAC demo) and could be reused for a manual refresh.
  const [refreshKey, setRefreshKey] = useState(0);
  const [selectedSuspectId, setSelectedSuspectId] = useState<number | null>(null);

  function handleAuthChange() {
    setRefreshKey((k) => k + 1);
  }

  return (
    <div>
      <Navbar onAuthChange={handleAuthChange} />
      <hr />
      <main>
        <DashboardSummary refreshKey={refreshKey} />
        <hr />
        <RepeatOffenderList refreshKey={refreshKey} />
        <hr />
        <CrimeGraphView refreshKey={refreshKey} onSelectSuspect={setSelectedSuspectId} />
      </main>
      <SuspectSidePanel suspectId={selectedSuspectId} onClose={() => setSelectedSuspectId(null)} />
    </div>
  );
}
