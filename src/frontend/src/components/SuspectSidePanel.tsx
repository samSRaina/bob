import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { components } from "../api/schema";

type Dossier = components["schemas"]["SuspectDossierOut"];

interface SuspectSidePanelProps {
  suspectId: number | null;
  onClose: () => void;
}

// A minimal slide-out drawer. The only non-functional-purpose inline styles in
// the whole frontend live here (position/width) — everything else is plain
// unstyled HTML, per the prototype's "no styling" scope.
const panelStyle: React.CSSProperties = {
  position: "fixed",
  top: 0,
  right: 0,
  bottom: 0,
  width: "380px",
  overflowY: "auto",
  borderLeft: "1px solid black",
  background: "white",
  padding: "12px",
};

export default function SuspectSidePanel({ suspectId, onClose }: SuspectSidePanelProps) {
  const [dossier, setDossier] = useState<Dossier | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (suspectId === null) {
      setDossier(null);
      return;
    }
    setError(null);
    setDossier(null);
    api.GET("/suspects/{suspect_id}", { params: { path: { suspect_id: suspectId } } }).then(({ data, error: err }) => {
      if (err) {
        setError(JSON.stringify(err));
        return;
      }
      if (data) setDossier(data);
    });
  }, [suspectId]);

  if (suspectId === null) return null;

  return (
    <div style={panelStyle}>
      <button onClick={onClose}>Close X</button>
      <h2>Suspect Dossier</h2>
      {error && <p>Error: {error}</p>}
      {!error && !dossier && <p>Loading...</p>}
      {dossier && (
        <>
          <p>
            <strong>Name:</strong> {dossier.name ?? "(unnamed - identified by identifiers/description only)"}
          </p>
          <p>
            <strong>Aliases:</strong> {dossier.aliases.length ? dossier.aliases.join(", ") : "-"}
          </p>
          <p>
            <strong>Phone Numbers:</strong> {dossier.phone_numbers.length ? dossier.phone_numbers.join(", ") : "-"}
          </p>
          <p>
            <strong>Vehicle Numbers:</strong> {dossier.vehicle_numbers.length ? dossier.vehicle_numbers.join(", ") : "-"}
          </p>
          <p>
            <strong>Physical Description:</strong> {dossier.physical_description ?? "-"}
          </p>
          <p>
            <strong>Associated FIR IDs:</strong> {dossier.associated_fir_ids.join(", ")}
          </p>
          <h3>Cluster / Syndicate Link</h3>
          {dossier.cluster ? (
            <>
              <p>
                <strong>Confidence:</strong> {dossier.cluster.confidence_score.toFixed(2)}
              </p>
              <p>
                <strong>Syndicate flagged:</strong> {dossier.cluster.syndicate_flag ? "YES" : "No"}
              </p>
              <p>
                <strong>Districts involved:</strong> {dossier.cluster.districts_involved.join(", ")}
              </p>
              <p>
                <strong>Match reasons:</strong>
              </p>
              <ul>
                {dossier.cluster.match_reasons.map((r, i) => (
                  <li key={i}>{r}</li>
                ))}
              </ul>
            </>
          ) : (
            <p>Not part of any repeat-offender cluster (no other FIR currently links to this suspect).</p>
          )}
        </>
      )}
    </div>
  );
}
