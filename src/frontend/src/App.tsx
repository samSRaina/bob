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
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
      <Navbar onAuthChange={handleAuthChange} />

      <main className="mx-auto max-w-7xl space-y-6 px-4 py-6 sm:px-6 lg:px-8">
        <DashboardSummary refreshKey={refreshKey} />
        <RepeatOffenderList refreshKey={refreshKey} />
        <CrimeGraphView refreshKey={refreshKey} onSelectSuspect={setSelectedSuspectId} />
      </main>

      <footer className="mx-auto max-w-7xl px-4 py-8 text-center text-xs text-slate-400 sm:px-6 lg:px-8 dark:text-slate-600">
        Bob Engine — IBM Bob AI Hackathon x NFSU, Problem Statement #10. IBM Bob is used as the FIR extraction
        copilot; every downstream engine (entity resolution, MO clustering, RBAC) is deterministic.
      </footer>

      <SuspectSidePanel suspectId={selectedSuspectId} onClose={() => setSelectedSuspectId(null)} />
    </div>
  );
}
