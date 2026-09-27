import { useEffect, useMemo, useRef, useState } from "react";
import ForceGraph2D, { type NodeObject } from "react-force-graph-2d";
import { api } from "../api/client";
import type { components } from "../api/schema";

type Graph = components["schemas"]["GraphOut"];

interface CrimeGraphViewProps {
  refreshKey: number;
  onSelectSuspect: (suspectId: number) => void;
}

// Functional colors only — these encode node TYPE (the one place color carries
// meaning in this otherwise unstyled prototype), not aesthetic choice.
const NODE_COLORS: Record<string, string> = {
  Suspect: "red",
  FIR: "blue",
  Station: "green",
  SyndicateHub: "purple",
};

export default function CrimeGraphView({ refreshKey, onSelectSuspect }: CrimeGraphViewProps) {
  const [graph, setGraph] = useState<Graph>({ nodes: [], links: [] });
  const [error, setError] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setError(null);
    api.GET("/graph").then(({ data, error: err }) => {
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

  if (error) return <p>Error loading graph: {error}</p>;

  return (
    <section>
      <h2>Criminal Syndicate Graph</h2>
      <p>
        Legend: <span style={{ color: "red" }}>red = suspect</span>,{" "}
        <span style={{ color: "blue" }}>blue = FIR</span>,{" "}
        <span style={{ color: "green" }}>green = station</span>,{" "}
        <span style={{ color: "purple" }}>purple = syndicate hub suspect</span>. Click a suspect node to open its
        dossier.
      </p>
      <div ref={containerRef} style={{ width: "100%", height: "500px", border: "1px solid black" }}>
        <ForceGraph2D
          graphData={graphData}
          nodeId="id"
          nodeLabel="label"
          nodeColor={(node: NodeObject) => NODE_COLORS[(node as unknown as { type: string }).type] ?? "gray"}
          linkLabel="type"
          width={containerRef.current?.clientWidth ?? 800}
          height={500}
          onNodeClick={(node: NodeObject) => {
            const n = node as unknown as { id: string; type: string };
            if (n.type === "Suspect" || n.type === "SyndicateHub") {
              const suspectId = Number(n.id.replace("suspect-", ""));
              if (!Number.isNaN(suspectId)) onSelectSuspect(suspectId);
            }
          }}
        />
      </div>
    </section>
  );
}
