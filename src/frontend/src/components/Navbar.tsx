import { useEffect, useState } from "react";
import { ShieldHalf, Moon, Sun, MapPin, ChevronDown } from "lucide-react";
import { api, setAuth, type Role } from "../api/client";
import type { components } from "../api/schema";
import { useTheme } from "../lib/useTheme";

type Station = components["schemas"]["StationOut"];

interface NavbarProps {
  onAuthChange: () => void;
}

const ROLE_LABELS: Record<Role, string> = {
  STATION_OFFICER: "Station Officer (PI)",
  DISTRICT_SP: "District SP",
  STATE_DGP: "State DGP",
};

function SelectField({
  value,
  onChange,
  children,
  icon,
}: {
  value: string | number;
  onChange: (e: React.ChangeEvent<HTMLSelectElement>) => void;
  children: React.ReactNode;
  icon?: React.ReactNode;
}) {
  return (
    <div className="relative">
      {icon && (
        <span className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400">{icon}</span>
      )}
      <select
        value={value}
        onChange={onChange}
        className={`appearance-none rounded-lg border border-slate-200 bg-white py-1.5 pr-8 text-sm font-medium text-slate-700 shadow-sm outline-none transition hover:border-slate-300 focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:border-slate-600 dark:focus:ring-indigo-500/20 ${icon ? "pl-8" : "pl-3"}`}
      >
        {children}
      </select>
      <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
    </div>
  );
}

// The whole RBAC demo lives here: pick a role (and, for STATION_OFFICER /
// DISTRICT_SP, a station) and every other panel on the page refetches through
// the scoped headers the api client now injects. This is intentionally the
// only "login" screen the app has.
export default function Navbar({ onAuthChange }: NavbarProps) {
  const [stations, setStations] = useState<Station[]>([]);
  const [role, setRole] = useState<Role>("STATE_DGP");
  const [stationId, setStationId] = useState<number | "">("");
  const { theme, toggleTheme } = useTheme();

  useEffect(() => {
    api.GET("/stations/all").then(({ data }) => {
      if (data) setStations(data);
    });
  }, []);

  function applyAuth(nextRole: Role, nextStationId: number | "") {
    setRole(nextRole);
    setStationId(nextStationId);
    setAuth({
      role: nextRole,
      stationId: nextRole === "STATE_DGP" ? null : (nextStationId === "" ? null : nextStationId),
    });
    onAuthChange();
  }

  function handleRoleChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const nextRole = e.target.value as Role;
    const fallbackStation = stations.length > 0 ? stations[0].id : "";
    applyAuth(nextRole, nextRole === "STATE_DGP" ? "" : (stationId === "" ? fallbackStation : stationId));
  }

  function handleStationChange(e: React.ChangeEvent<HTMLSelectElement>) {
    applyAuth(role, Number(e.target.value));
  }

  const currentStation = stations.find((s) => s.id === stationId);
  const scopeLabel =
    role === "STATE_DGP"
      ? "State-wide"
      : role === "DISTRICT_SP"
        ? currentStation
          ? `${currentStation.district} district`
          : "..."
        : currentStation
          ? `${currentStation.name}, ${currentStation.district}`
          : "...";

  return (
    <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/80 backdrop-blur-md dark:border-slate-800 dark:bg-slate-950/80">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-3 px-4 py-3 sm:px-6 lg:px-8">
        <div className="flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-600 to-indigo-700 text-white shadow-sm shadow-indigo-500/30">
            <ShieldHalf className="h-5 w-5" />
          </div>
          <div className="leading-tight">
            <h1 className="text-sm font-bold tracking-tight text-slate-900 dark:text-slate-50">Bob Engine</h1>
            <p className="text-[11px] font-medium text-slate-400 dark:text-slate-500">
              FIR Intelligence &amp; Crime Pattern Detector
            </p>
          </div>
        </div>

        <div className="ml-auto flex flex-wrap items-center gap-2">
          <SelectField value={role} onChange={handleRoleChange}>
            {(Object.keys(ROLE_LABELS) as Role[]).map((r) => (
              <option key={r} value={r}>
                {ROLE_LABELS[r]}
              </option>
            ))}
          </SelectField>

          {role !== "STATE_DGP" && (
            <SelectField value={stationId} onChange={handleStationChange} icon={<MapPin className="h-3.5 w-3.5" />}>
              {stations.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} ({s.district})
                </option>
              ))}
            </SelectField>
          )}

          <div className="hidden items-center gap-1.5 rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600 sm:flex dark:bg-slate-800 dark:text-slate-300">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
            {scopeLabel}
          </div>

          <button
            onClick={toggleTheme}
            aria-label="Toggle theme"
            className="flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 text-slate-500 transition hover:bg-slate-50 hover:text-slate-700 dark:border-slate-700 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-200"
          >
            {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </button>
        </div>
      </div>
    </header>
  );
}
