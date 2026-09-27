"""Builds the criminal-syndicate graph and exports it in the standardized
{ nodes: [...], links: [...] } shape react-force-graph-2d expects.

Node types: Suspect (canonical, post-resolution), FIR, Station.
Edge types: named_in (Suspect->FIR), filed_at (FIR->Station), syndicate (Suspect<->Suspect).
"""
from __future__ import annotations

import networkx as nx

from app.schemas.fir_schema import GraphLink, GraphNode, GraphOut


def build_graph(
    stations: list[tuple[int, str]],  # (station_id, name)
    firs: list[tuple[int, str, int]],  # (fir_id, fir_number, station_id)
    suspects: list[tuple[int, str | None, int, str | None]],  # (suspect_id, name, fir_id, cluster_canonical_id)
    clusters: list[tuple[str, bool]],  # (canonical_id, syndicate_flag)
) -> GraphOut:
    g = nx.Graph()

    station_name_by_id = dict(stations)
    for sid, name in stations:
        g.add_node(f"station-{sid}", label=name, type="Station")

    for fid, fir_number, station_id in firs:
        node_id = f"fir-{fid}"
        g.add_node(node_id, label=fir_number, type="FIR")
        if station_id in station_name_by_id:
            g.add_edge(node_id, f"station-{station_id}", type="filed_at")

    syndicate_clusters = {cid for cid, flag in clusters if flag}

    for suspect_id, name, fir_id, cluster_id in suspects:
        node_id = f"suspect-{suspect_id}"
        label = name or f"Unnamed suspect #{suspect_id}"
        node_type = "SyndicateHub" if cluster_id in syndicate_clusters else "Suspect"
        g.add_node(node_id, label=label, type=node_type, cluster=cluster_id)
        g.add_edge(node_id, f"fir-{fir_id}", type="named_in")

    # syndicate edges: connect all suspects sharing a cluster_canonical_id
    by_cluster: dict[str, list[int]] = {}
    for suspect_id, _name, _fir_id, cluster_id in suspects:
        if cluster_id:
            by_cluster.setdefault(cluster_id, []).append(suspect_id)
    for cluster_id, members in by_cluster.items():
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                a, b = f"suspect-{members[i]}", f"suspect-{members[j]}"
                if not g.has_edge(a, b) or g.edges[a, b].get("type") != "syndicate":
                    g.add_edge(a, b, type="syndicate")

    nodes = [
        GraphNode(id=n, label=data.get("label", n), type=data.get("type", "Unknown"), meta={"cluster": data.get("cluster")})
        for n, data in g.nodes(data=True)
    ]
    links = [
        GraphLink(source=u, target=v, type=data.get("type", "related"))
        for u, v, data in g.edges(data=True)
    ]
    return GraphOut(nodes=nodes, links=links)
