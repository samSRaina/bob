import { useEffect, useState } from "react";
import { Users, ShieldAlert, MapPin, FileText, Sparkles } from "lucide-react";
import { api, authHeaders } from "../api/client";
import type { components } from "../api/schema";
import { Card, CardHeader } from "./ui/Card";
import { Badge } from "./ui/Badge";
import { ConfidenceBar } from "./ui/ConfidenceBar";

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
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setError(null);
    setLoading(true);
    api.GET("/offenders", { params: { header: authHeaders() } }).then(({ data, error: err }) => {
      setLoading(false);
      if (err) {
        setError(JSON.stringify(err));
        return;
      }
      if (data) setClusters(data);
    });
  }, [refreshKey]);

  return (
    <Card>
      <CardHeader
        title="Flagged Repeat Offenders"
        subtitle="Ranked by confidence — explainable, evidence-backed links only"
        icon={<ShieldAlert className="h-[18px] w-[18px]" />}
      />

      {error && (
        <div className="m-6 rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-500/10 dark:text-red-400">
          Error loading offenders: {error}
        </div>
      )}

      {loading && !error && (
        <div className="space-y-3 p-6">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-16 animate-pulse rounded-xl bg-slate-100 dark:bg-slate-800" />
          ))}
        </div>
      )}

      {!loading && !error && clusters.length === 0 && (
        <p className="p-6 text-sm text-slate-500 dark:text-slate-400">No repeat-offender clusters visible in this scope.</p>
      )}

      {!loading && !error && clusters.length > 0 && (
        <div className="divide-y divide-slate-100 dark:divide-slate-800">
          {clusters.map((c) => (
            <div
              key={c.canonical_id}
              className={`p-6 transition ${c.syndicate_flag ? "bg-red-50/40 dark:bg-red-500/[0.03]" : ""}`}
            >
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="flex items-start gap-3">
                  <div
                    className={`mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-full ${
                      c.syndicate_flag
                        ? "bg-red-100 text-red-600 dark:bg-red-500/15 dark:text-red-400"
                        : "bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400"
                    }`}
                  >
                    <Users className="h-[18px] w-[18px]" />
                  </div>
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="font-semibold text-slate-900 dark:text-slate-100">{c.primary_name}</h3>
                      {c.syndicate_flag && (
                        <Badge tone="red" icon={<Sparkles className="h-3 w-3" />}>
                          SYNDICATE
                        </Badge>
                      )}
                    </div>
                    <div className="mt-1.5 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500 dark:text-slate-400">
                      <span className="inline-flex items-center gap-1">
                        <MapPin className="h-3 w-3" /> {c.districts_involved.join(", ")}
                      </span>
                      <span className="inline-flex items-center gap-1">
                        <FileText className="h-3 w-3" /> FIRs {c.linked_fir_ids.join(", ")}
                      </span>
                    </div>
                  </div>
                </div>
                <ConfidenceBar value={c.confidence_score} />
              </div>

              <ul className="mt-3 ml-[3.25rem] space-y-1 pl-0 text-xs text-slate-500 dark:text-slate-400">
                {c.match_reasons.map((r, i) => (
                  <li key={i} className="flex gap-1.5">
                    <span className="text-slate-300 dark:text-slate-600">&bull;</span>
                    {r}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}
