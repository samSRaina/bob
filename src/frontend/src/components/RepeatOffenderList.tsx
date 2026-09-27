import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { components } from "../api/schema";

type Cluster = components["schemas"]["OffenderClusterOut"];

interface RepeatOffenderListProps {
  refreshKey: number;
}

// Every row here is explainable on purpose: match_reasons is never hidden behind
// a black-box confidence number. A forensics/police audience needs to see WHY
// two suspects were linked, not just that they were.
export default function RepeatOffenderList({ refreshKey }: RepeatOffenderListProps) {
  const [clusters, setClusters] = useState<Cluster[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setError(null);
    api.GET("/offenders").then(({ data, error: err }) => {
      if (err) {
        setError(JSON.stringify(err));
        return;
      }
      if (data) setClusters(data);
    });
  }, [refreshKey]);

  if (error) return <p>Error loading offenders: {error}</p>;

  return (
    <section>
      <h2>Flagged Repeat Offenders</h2>
      {clusters.length === 0 && <p>No repeat-offender clusters visible in this scope.</p>}
      <table border={1} cellPadding={4}>
        <thead>
          <tr>
            <th>Primary Name</th>
            <th>Confidence</th>
            <th>Syndicate?</th>
            <th>Districts Involved</th>
            <th>Linked FIRs</th>
            <th>Match Reasons</th>
          </tr>
        </thead>
        <tbody>
          {clusters.map((c) => (
            <tr key={c.canonical_id}>
              <td>{c.primary_name}</td>
              <td>{c.confidence_score.toFixed(2)}</td>
              <td>{c.syndicate_flag ? "SYNDICATE" : "-"}</td>
              <td>{c.districts_involved.join(", ")}</td>
              <td>{c.linked_fir_ids.join(", ")}</td>
              <td>
                <ul>
                  {c.match_reasons.map((r, i) => (
                    <li key={i}>{r}</li>
                  ))}
                </ul>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
