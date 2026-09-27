import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { components } from "../api/schema";

type Summary = components["schemas"]["DashboardSummaryOut"];

interface DashboardSummaryProps {
  refreshKey: number;
}

export default function DashboardSummary({ refreshKey }: DashboardSummaryProps) {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setError(null);
    api.GET("/dashboard/summary").then(({ data, error: err }) => {
      if (err) {
        setError(JSON.stringify(err));
        return;
      }
      if (data) setSummary(data);
    });
  }, [refreshKey]);

  if (error) return <p>Error loading dashboard: {error}</p>;
  if (!summary) return <p>Loading dashboard...</p>;

  return (
    <section>
      <h2>Station Summary</h2>
      <table border={1} cellPadding={4}>
        <tbody>
          <tr>
            <td>Total FIRs</td>
            <td>{summary.total_firs}</td>
          </tr>
          <tr>
            <td>Total Suspects</td>
            <td>{summary.total_suspects}</td>
          </tr>
          <tr>
            <td>Repeat-Offender Clusters</td>
            <td>{summary.total_clusters}</td>
          </tr>
          <tr>
            <td>Flagged Syndicates</td>
            <td>{summary.total_syndicates}</td>
          </tr>
        </tbody>
      </table>

      <h3>By Crime Category</h3>
      <table border={1} cellPadding={4}>
        <thead>
          <tr>
            <th>Category</th>
            <th>Count</th>
          </tr>
        </thead>
        <tbody>
          {summary.by_crime_category.map((row) => (
            <tr key={row.crime_category}>
              <td>{row.crime_category}</td>
              <td>{row.count}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h3>By Station</h3>
      <table border={1} cellPadding={4}>
        <thead>
          <tr>
            <th>Station</th>
            <th>Count</th>
          </tr>
        </thead>
        <tbody>
          {summary.by_station.map((row) => (
            <tr key={row.station_id}>
              <td>{row.station_name}</td>
              <td>{row.count}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
