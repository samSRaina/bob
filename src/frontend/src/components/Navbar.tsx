import { useEffect, useState } from "react";
import { api, setAuth, type Role } from "../api/client";
import type { components } from "../api/schema";

type Station = components["schemas"]["StationOut"];

interface NavbarProps {
  onAuthChange: () => void;
}

// The whole RBAC demo lives here: pick a role (and, for STATION_OFFICER /
// DISTRICT_SP, a station) and every other panel on the page refetches through
// the scoped headers the api client now injects. This is intentionally the
// only "login" screen the app has.
export default function Navbar({ onAuthChange }: NavbarProps) {
  const [stations, setStations] = useState<Station[]>([]);
  const [role, setRole] = useState<Role>("STATE_DGP");
  const [stationId, setStationId] = useState<number | "">("");

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

  return (
    <nav>
      <span>
        <strong>Bob Engine</strong> - FIR Intelligence &amp; Crime Pattern Detector
      </span>
      {" | "}
      <label>
        Role:{" "}
        <select value={role} onChange={handleRoleChange}>
          <option value="STATION_OFFICER">Station Officer (PI)</option>
          <option value="DISTRICT_SP">District SP</option>
          <option value="STATE_DGP">State DGP</option>
        </select>
      </label>
      {" "}
      {role !== "STATE_DGP" && (
        <label>
          Station:{" "}
          <select value={stationId} onChange={handleStationChange}>
            {stations.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name} ({s.district})
              </option>
            ))}
          </select>
        </label>
      )}
      {" | "}
      <span>
        Viewing as: <strong>{role}</strong>
        {role === "STATION_OFFICER" && currentStation && ` at ${currentStation.name} (${currentStation.district})`}
        {role === "DISTRICT_SP" && currentStation && ` over ${currentStation.district} district`}
        {role === "STATE_DGP" && " (state-wide)"}
      </span>
    </nav>
  );
}
