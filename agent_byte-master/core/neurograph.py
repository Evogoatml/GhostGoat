import networkx as nx
from typing import Any, Dict, List, Optional, Tuple, Union

class NeuroGraph:
    """
    A neuro-graph acts as the 'nervous system' for multi-agent systems.
    Nodes: agents, tasks, concepts, memory fragments.
    Edges: relationships (handled, needs, suggests, reports, etc.).
    """

    def __init__(self):
        self.graph = nx.MultiDiGraph()  # Allows multi-edge, directed graph

    # --- Node management ---
    def add_node(self, node_id: str, kind: str, data: Dict[str, Any] = None):
        """
        Add or update a node with metadata.
        kind: 'agent', 'task', 'memory', 'concept', etc.
        """
        self.graph.add_node(node_id, kind=kind, data=data or {})

    def get_node(self, node_id: str) -> Optional[Dict]:
        return self.graph.nodes.get(node_id, None)

    # --- Edge management ---
    def add_edge(self, src: str, dst: str, relation: str, meta: Dict[str, Any] = None):
        """
        Create a labeled, possibly attributed edge.
        """
        self.graph.add_edge(src, dst, relation=relation, **(meta or {}))

    def neighbors(self, node_id: str, relation: Optional[str] = None) -> List[str]:
        nbrs = []
        for nbr in self.graph.successors(node_id):
            # If filtering by relation
            if relation:
                rels = [d['relation'] for k, d in self.graph.get_edge_data(node_id, nbr).items()]
                if relation in rels:
                    nbrs.append(nbr)
            else:
                nbrs.append(nbr)
        return nbrs

    # --- Context/Querying ---
    def get_context(self, node_id: str, radius: int = 2, kinds: List[str] = None) -> List[Tuple[str, Dict]]:
        """
        Get neighborhood context from node, radius hops.
        """
        context_nodes = nx.single_source_shortest_path_length(self.graph, node_id, cutoff=radius)
        result = []
        for n in context_nodes:
            node_data = self.graph.nodes[n]
            if not kinds or node_data['kind'] in kinds:
                result.append((n, node_data))
        return result

    # --- Self-healing & health ---
    def health_check(self) -> Dict[str, Any]:
        status = {"nodes": self.graph.number_of_nodes(),
                  "edges": self.graph.number_of_edges(),
                  "isolates": list(nx.isolates(self.graph)),
                  "ok": True}
        if not status["nodes"]:
            status["ok"] = False
            status["reason"] = "No nodes"
        return status

    def self_heal(self) -> bool:
        """Try to fix broken links or populate from backup."""
        try:
            # Example: Remove isolated nodes
            nx.set_node_attributes(self.graph, False, "broken")
            for n in nx.isolates(self.graph):
                self.graph.nodes[n]['broken'] = True
            return True
        except Exception as e:
            print(f"NeuroGraph self-heal failed: {e}")
            return False

    # --- Serialization (optional example) ---
    def save(self, path: str):
        nx.write_gpickle(self.graph, path)

    def load(self, path: str):
        self.graph = nx.read_gpickle(path)
