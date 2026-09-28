import { useEffect, useMemo, useRef, useState } from "react";
import ForceGraph2D, { type NodeObject } from "react-force-graph-2d";
import { Waypoints } from "lucide-react";
import { api, authHeaders } from "../api/client";
import type { components } from "../api/schema";
import { Card, CardHeader } from "./ui/Card";
import { useTheme } from "../lib/useTheme";

type Graph = components["schemas"]["GraphOut"];

interface CrimeGraphViewProps {
  refreshKey: number;
  onSelectSuspect: (suspectId: number) => void;
}

// Functional colors only — these encode node TYPE (the one place color carries
// meaning beyond the design system), not aesthetic choice.
const NODE_COLORS: Record<string, string> = {
  Suspect: "#ef4444", // red-500
  FIR: "#3b82f6", // blue-500
  Station: "#10b981", // emerald-500
  SyndicateHub: "#a855f7", // purple-500
};

const LEGEND: { label: string; color: string }[] = [
  { label: "Suspect", color: NODE_COLORS.Suspect },
  { label: "FIR", color: NODE_COLORS.FIR },
  { label: "Station", color: NODE_COLORS.Station },
  { label: "Syndicate hub", color: NODE_COLORS.SyndicateHub },
];

export default function CrimeGraphView({ refreshKey, onSelectSuspect }: CrimeGraphViewProps) {
  const [graph, setGraph] = useState<Graph>({ nodes: [], links: [] });
  const [error, setError] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const { theme } = useTheme();

  useEffect(() => {
    setError(null);
    api.GET("/graph", { params: { header: authHeaders() } }).then(({ data, error: err }) => {
      if (err) {
        setError(JSON.stringify(err));
        return;
      }
      if (data) setGraph(data);
    });
  }, [refreshKey]);

  // ForceGraph2D restarts its physics simulation whenever the graphData object
  // reference changes. Building a fresh {nodes, links} object inline on every
  // render (e.g. from an unrelated parent re-render) kept resetting the layout
  // before it could spread out, so it stayed collapsed near the center. Memoize
  // it against the actual fetched data instead.
  const graphData = useMemo(
    () => ({
      nodes: graph.nodes.map((n) => ({ ...n })),
      links: graph.links.map((l) => ({ ...l })),
    }),
    [graph],
  );

  const linkColor = theme === "dark" ? "rgba(148,163,184,0.25)" : "rgba(100,116,139,0.25)";

  return (
    <Card>
      <CardHeader
        title="Criminal Syndicate Graph"
        subtitle="Click a suspect or syndicate-hub node to open its dossier"
        icon={<Waypoints className="h-[18px] w-[18px]" />}
        action={
          <div className="hidden flex-wrap items-center gap-3 sm:flex">
            {LEGEND.map((item) => (
              <span key={item.label} className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-500 dark:text-slate-400">
                <span className="h-2 w-2 rounded-full" style={{ backgroundColor: item.color }} />
                {item.label}
              </span>
            ))}
          </div>
        }
      />

      <div className="flex flex-wrap gap-3 px-6 pt-4 sm:hidden">
        {LEGEND.map((item) => (
          <span key={item.label} className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-500 dark:text-slate-400">
            <span className="h-2 w-2 rounded-full" style={{ backgroundColor: item.color }} />
            {item.label}
          </span>
        ))}
      </div>

      {error && (
        <div className="m-6 rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-500/10 dark:text-red-400">
          Error loading graph: {error}
        </div>
      )}

      <div className="p-6 pt-4">
        <div
          ref={containerRef}
          className="overflow-hidden rounded-xl border border-slate-100 bg-slate-50/50 dark:border-slate-800 dark:bg-slate-950/40"
          style={{ height: "520px" }}
        >
          <ForceGraph2D
            graphData={graphData}
            nodeId="id"
            nodeLabel="label"
            nodeRelSize={4}
            nodeColor={(node: NodeObject) => NODE_COLORS[(node as unknown as { type: string }).type] ?? "#94a3b8"}
            linkColor={() => linkColor}
            linkWidth={1}
            backgroundColor="rgba(0,0,0,0)"
            width={containerRef.current?.clientWidth ?? 800}
            height={520}
            onNodeClick={(node: NodeObject) => {
              const n = node as unknown as { id: string; type: string };
              if (n.type === "Suspect" || n.type === "SyndicateHub") {
                const suspectId = Number(n.id.replace("suspect-", ""));
                if (!Number.isNaN(suspectId)) onSelectSuspect(suspectId);
              }
            }}
          />
        </div>
      </div>
    </Card>
  );
}
