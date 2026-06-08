# cogno/nodes/quantum_graph.py

class QuantumGraph:
    def __init__(self):
        self.nodes: dict[str, QuantumNode] = {}
        self.edges: dict[str, list[str]] = {}  # {node_id: [neighbor_ids]}
        self.bus = EntanglementBus()

    def add_node(self, node: QuantumNode):
        self.nodes[node.node_id] = node
        self.edges[node.node_id] = []

    def connect(self, source_id: str, target_id: str, weight: float = 1.0):
        self.edges[source_id].append(target_id)
        self.nodes[target_id].weights[source_id] = weight

    def propagate(self, source_id: str, signal: float):
        """Fire a signal through the graph like an action potential."""
        visited = set()
        queue = [(source_id, signal)]
        
        while queue:
            current_id, sig = queue.pop(0)
            if current_id in visited:
                continue
            visited.add(current_id)
            
            node = self.nodes[current_id]
            node.receive_signal(source_id, sig)
            output = node.activate()
            
            if output is not None:
                for neighbor_id in self.edges.get(current_id, []):
                    queue.append((neighbor_id, output))
                    node.strengthen_synapse(current_id)  # plasticity

    def observe_all(self) -> dict[str, str]:
        """Collapse all nodes — snapshot of the graph's current reality."""
        return {nid: n.observe() for nid, n in self.nodes.items()}