"""
Graph traversal agent.

Relocated from empire/AutoNode's TraversalAgent.
Navigates a graph of nodes by asking an LLM to select the next node,
then uses string similarity to match the LLM's choice to actual graph nodes.

Stripped of AutoNode-specific imports — works with any graph structure
that provides nodes with names and adjacency lists.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# Optional: jellyfish for Jaro-Winkler similarity
try:
    import jellyfish
    _HAS_JELLYFISH = True
except ImportError:
    _HAS_JELLYFISH = False


@dataclass
class GraphNode:
    """A node in a navigable graph."""
    id: str
    name: str
    description: str = ""
    type_description: str = ""
    adjacent_to: List[str] = field(default_factory=list)
    data: Dict[str, Any] = field(default_factory=dict)


class TraversalAgent:
    """Navigate a graph of nodes using LLM-guided selection.

    The agent presents child nodes to the LLM, asks it to pick one,
    then uses Jaro-Winkler similarity to map the LLM's text choice
    back to an actual node.

    Usage:
        graph = {"1": GraphNode(id="1", name="Login", adjacent_to=["2","3"]),
                 "2": GraphNode(id="2", name="Dashboard"),
                 "3": GraphNode(id="3", name="Settings")}
        agent = TraversalAgent(llm_callback=my_llm)
        node = agent.traverse(objective="Go to settings",
                              start_node=graph["1"], graph=graph)
    """

    def __init__(self, llm_callback: Callable, similarity_threshold: float = 0.70,
                 max_depth: int = 5):
        """
        Args:
            llm_callback: Callable(prompt: str) -> str
            similarity_threshold: Min Jaro-Winkler score to accept a match.
            max_depth: Max traversal depth before giving up.
        """
        self._llm = llm_callback
        self._threshold = similarity_threshold
        self._max_depth = max_depth

    def traverse(self, objective: str, start_node: GraphNode,
                 graph: Dict[str, GraphNode],
                 actions_taken: str = "") -> Optional[GraphNode]:
        """Traverse from start_node toward the objective.

        Returns the selected node, or None if no suitable node found.
        """
        current = start_node

        for depth in range(self._max_depth):
            if not current.adjacent_to:
                logger.info("Node '%s' has no children — traversal complete.", current.name)
                return current

            try:
                choice_text = self._ask_llm(objective, actions_taken, current, graph)
                matched = self._find_most_similar(choice_text, current, graph)
                if matched:
                    logger.info("Depth %d: selected '%s'", depth, matched.name)
                    return matched
            except Exception as e:
                logger.warning("Traversal error at depth %d: %s", depth, e)
                continue

        logger.warning("Max depth reached without finding a match.")
        return None

    def _ask_llm(self, objective: str, actions_taken: str,
                 parent: GraphNode, graph: Dict[str, GraphNode]) -> str:
        """Present options to the LLM and get a selection."""
        options_lines = []
        for idx, child_id in enumerate(parent.adjacent_to, 1):
            child = graph.get(str(child_id))
            if not child:
                continue
            line = f"{idx}. {child.name}"
            if child.description:
                line += f" — {child.description}"
            if child.type_description:
                line += f" (type: {child.type_description})"
            options_lines.append(line)

        prompt = (
            f"Objective: {objective}\n"
            f"Actions taken so far: {actions_taken or 'none'}\n\n"
            f"You are at: {parent.name}\n"
            f"Available options:\n" + "\n".join(options_lines) + "\n\n"
            f"Which option should we navigate to? Reply with the option name."
        )

        return self._llm(prompt)

    def _find_most_similar(self, choice_text: str, parent: GraphNode,
                           graph: Dict[str, GraphNode]) -> Optional[GraphNode]:
        """Match the LLM's text choice to an actual child node."""
        best_score = -1.0
        best_node = None

        for child_id in parent.adjacent_to:
            child = graph.get(str(child_id))
            if not child:
                continue

            score = self._similarity(child.name, choice_text)
            if score > best_score:
                best_score = score
                best_node = child

        if best_score >= self._threshold:
            return best_node

        logger.debug("No match above threshold %.2f (best: %.2f for '%s')",
                     self._threshold, best_score,
                     best_node.name if best_node else "none")
        return None

    @staticmethod
    def _similarity(a: str, b: str) -> float:
        """Jaro-Winkler similarity, with fallback to simple ratio."""
        a_lower = a.lower().strip()
        b_lower = b.lower().strip()

        if _HAS_JELLYFISH:
            return jellyfish.jaro_winkler_similarity(a_lower, b_lower)

        # Simple fallback: longest common substring ratio
        if not a_lower or not b_lower:
            return 0.0
        shorter, longer = sorted([a_lower, b_lower], key=len)
        if shorter in longer:
            return len(shorter) / len(longer)
        # Character overlap ratio
        common = sum(1 for c in shorter if c in longer)
        return common / max(len(shorter), len(longer))
