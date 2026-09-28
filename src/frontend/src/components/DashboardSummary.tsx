import { useEffect, useState } from "react";
import { FileText, Users, Network, ShieldAlert, BarChart3, Building2 } from "lucide-react";
import { api, authHeaders } from "../api/client";
import type { components } from "../api/schema";
import { StatCard } from "./ui/StatCard";
import { Card, CardHeader } from "./ui/Card";

type Summary = components["schemas"]["DashboardSummaryOut"];

interface DashboardSummaryProps {
  refreshKey: number;
}

const CATEGORY_COLORS = [
  "bg-indigo-500",
  "bg-red-500",
  "bg-amber-500",
  "bg-emerald-500",
  "bg-sky-500",
  "bg-purple-500",
  "bg-pink-500",
  "bg-teal-500",
];

export default function DashboardSummary({ refreshKey }: DashboardSummaryProps) {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setError(null);
    setSummary(null);
    api.GET("/dashboard/summary", { params: { header: authHeaders() } }).then(({ data, error: err }) => {
      if (err) {
        setError(JSON.stringify(err));
        return;
      }
      if (data) setSummary(data);
    });
  }, [refreshKey]);

  if (error) {
    return (
      <Card className="border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-400">
        Error loading dashboard: {error}
      </Card>
    );
  }

  if (!summary) {
    return (
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Card key={i} className="p-5">
            <div className="h-3 w-20 animate-pulse rounded bg-slate-200 dark:bg-slate-800" />
            <div className="mt-4 h-8 w-16 animate-pulse rounded bg-slate-200 dark:bg-slate-800" />
          </Card>
        ))}
      </div>
    );
  }

  const maxCategoryCount = Math.max(...summary.by_crime_category.map((r) => r.count), 1);
  const maxStationCount = Math.max(...summary.by_station.map((r) => r.count), 1);

  return (
    <section className="space-y-6">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label="Total FIRs" value={summary.total_firs} icon={<FileText className="h-[18px] w-[18px]" />} tone="indigo" />
        <StatCard label="Total Suspects" value={summary.total_suspects} icon={<Users className="h-[18px] w-[18px]" />} tone="indigo" />
        <StatCard
          label="Offender Clusters"
          value={summary.total_clusters}
          icon={<Network className="h-[18px] w-[18px]" />}
          tone="amber"
        />
        <StatCard
          label="Flagged Syndicates"
          value={summary.total_syndicates}
          icon={<ShieldAlert className="h-[18px] w-[18px]" />}
          tone="red"
          hint={summary.total_syndicates > 0 ? "Requires exact evidence or high confidence" : undefined}
        />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader
            title="Crime Category Breakdown"
            subtitle="Distribution of FIRs in current scope"
            icon={<BarChart3 className="h-[18px] w-[18px]" />}
          />
          <div className="space-y-4 p-6">
            {summary.by_crime_category.map((row, i) => (
              <div key={row.crime_category}>
                <div className="mb-1.5 flex items-baseline justify-between text-sm">
                  <span className="font-medium text-slate-700 dark:text-slate-300">{row.crime_category}</span>
                  <span className="tabular-nums text-slate-400 dark:text-slate-500">{row.count}</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
                  <div
                    className={`h-full rounded-full ${CATEGORY_COLORS[i % CATEGORY_COLORS.length]}`}
                    style={{ width: `${(row.count / maxCategoryCount) * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </Card>

        <Card>
          <CardHeader title="By Station" subtitle="FIR volume per police station" icon={<Building2 className="h-[18px] w-[18px]" />} />
          <div className="max-h-80 overflow-y-auto p-6 pt-2">
            <table className="w-full text-sm">
              <tbody>
                {summary.by_station.map((row) => (
                  <tr key={row.station_id} className="border-b border-slate-50 last:border-0 dark:border-slate-800/60">
                    <td className="py-2.5 pr-3 font-medium text-slate-700 dark:text-slate-300">{row.station_name}</td>
                    <td className="w-32 py-2.5">
                      <div className="h-1.5 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
                        <div
                          className="h-full rounded-full bg-indigo-400"
                          style={{ width: `${(row.count / maxStationCount) * 100}%` }}
                        />
                      </div>
                    </td>
                    <td className="py-2.5 pl-3 text-right tabular-nums text-slate-400 dark:text-slate-500">{row.count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
    </section>
  );
}
