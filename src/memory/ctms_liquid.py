"""
ctms_liquid.py
--------------
Autonomous Hybrid Causal Thought Mapping System (CTMS)
Full stack: CTMS notation + Liquid-S4 expander + CRDT state + importable API.

Usage:
    from ctms_liquid import map_liquid_s4, ThoughtMapper
    print(map_liquid_s4())
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
import uuid
from copy import deepcopy
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Protocol, Set, Tuple

logger = logging.getLogger("ghostgoat.ctms")


@dataclass
class ThoughtNode:
    id: str
    predecessor: str
    consequence: str
    context: str
    depth: int = 0
    score: float = 0.0
    timestamp: float = field(default_factory=time.time)
    origin: str = "local"
    parent_id: Optional[str] = None

    def to_ctms(self) -> str:
        return f"?({self.predecessor}) → !({self.consequence}) <{self.context}>"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


Tag = Tuple[str, str]  # (replica_id, unique_add_id)


def _tag_key(tag: Tag) -> str:
    return f"{tag[0]}:{tag[1]}"


def _parse_tag(key: str) -> Tag:
    replica, _, uid = key.partition(":")
    return (replica, uid)


def _content_id(*parts: str) -> str:
    """Deterministic content-addressed node id — makes expand() idempotent."""
    digest = hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()
    return f"th-{digest[:16]}"


_NODE_FIELDS = {f.name for f in fields(ThoughtNode)}


def _payload_to_node(data: Dict[str, Any]) -> ThoughtNode:
    """Tolerant payload → ThoughtNode: ignores unknown keys from other versions."""
    return ThoughtNode(**{k: v for k, v in data.items() if k in _NODE_FIELDS})


class ORSet:
    """
    Observed-Remove Set.

    An element is in the set iff it has at least one add-tag that has not
    been observed-and-removed.

    Merge is union of add-tags and union of removed tags (commutative,
    associative, idempotent). A later add after a remove uses a fresh tag
    and therefore resurrects the element.
    """

    def __init__(self, replica_id: str):
        self.replica_id = replica_id
        self.adds: Dict[str, Set[str]] = {}       # element -> {tag_key}
        self.removed: Set[str] = set()            # observed add-tag keys

    def _fresh_tag(self) -> Tag:
        return (self.replica_id, str(uuid.uuid4()))

    def add(self, element: str) -> Tag:
        tag = self._fresh_tag()
        key = _tag_key(tag)
        self.adds.setdefault(element, set()).add(key)
        return tag

    def remove(self, element: str) -> Set[str]:
        """Observe every currently known add-tag for this element and remove them."""
        observed = set(self.adds.get(element, set()))
        self.removed |= observed
        return observed

    def contains(self, element: str) -> bool:
        return any(tag not in self.removed for tag in self.adds.get(element, set()))

    def elements(self) -> List[str]:
        return [el for el in self.adds if self.contains(el)]

    def merge(self, other: "ORSet") -> None:
        for element, tags in other.adds.items():
            bucket = self.adds.setdefault(element, set())
            bucket |= tags
        self.removed |= other.removed

    def to_dict(self) -> Dict[str, Any]:
        return {
            "replica_id": self.replica_id,
            "adds": {el: sorted(tags) for el, tags in self.adds.items()},
            "removed": sorted(self.removed),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ORSet":
        s = cls(replica_id=data.get("replica_id", "unknown"))
        s.adds = {el: set(tags) for el, tags in data.get("adds", {}).items()}
        s.removed = set(data.get("removed", []))
        return s


class LWWRegister:
    """Last-Write-Wins register ordered by hybrid logical clock (wall, lamport, writer).

    The lamport counter breaks ties and masks replica clock skew; old serialized
    data without a lamport field loads as 0 and still compares correctly.
    """

    def __init__(self, replica_id: str):
        self.replica_id = replica_id
        self.value: Any = None
        self.timestamp: float = -1.0
        self.lamport: int = 0
        self.writer: str = ""

    def set(self, value: Any, timestamp: Optional[float] = None, lamport: int = 0) -> None:
        ts = time.time() if timestamp is None else timestamp
        self.value = value
        self.timestamp = ts
        self.lamport = lamport
        self.writer = self.replica_id

    def order_key(self) -> Tuple[float, int, str]:
        return (self.timestamp, self.lamport, self.writer)

    def merge(self, other: "LWWRegister") -> None:
        if other.order_key() > self.order_key():
            self._take(other)

    def _take(self, other: "LWWRegister") -> None:
        self.value = deepcopy(other.value)
        self.timestamp = other.timestamp
        self.lamport = other.lamport
        self.writer = other.writer

    def to_dict(self) -> Dict[str, Any]:
        return {
            "value": self.value,
            "timestamp": self.timestamp,
            "lamport": self.lamport,
            "writer": self.writer,
        }

    @classmethod
    def from_dict(cls, replica_id: str, data: Dict[str, Any]) -> "LWWRegister":
        reg = cls(replica_id)
        reg.value = data.get("value")
        reg.timestamp = data.get("timestamp", -1.0)
        reg.lamport = int(data.get("lamport", 0))
        reg.writer = data.get("writer", "")
        return reg


class HybridClock:
    """Hybrid logical clock: (wall, lamport) that survives replica clock skew."""

    def __init__(self, wall: float = 0.0, lamport: int = 0):
        self.wall = wall
        self.lamport = lamport

    def tick(self, remote_wall: Optional[float] = None, remote_lamport: int = 0) -> Tuple[float, int]:
        """Return the next HLC timestamp, observing any remote values first."""
        if remote_wall is not None:
            self.wall = max(self.wall, remote_wall)
        self.lamport = max(self.lamport, remote_lamport) + 1
        self.wall = max(self.wall, time.time())
        return (self.wall, self.lamport)

    def observe(self, wall: float, lamport: int) -> None:
        """Adopt the high-water mark of a merged register."""
        self.wall = max(self.wall, wall)
        self.lamport = max(self.lamport, lamport)


def edge_key(parent_id: str, child_id: str) -> str:
    return f"{parent_id}>{child_id}"


def split_edge_key(key: str) -> Tuple[str, str]:
    parent, _, child = key.partition(">")
    return parent, child


class CausalDAG:
    """
    DAG CRDT for thought order.

    Edges live in an OR-Set keyed as 'parent_id>child_id'.
    Membership of endpoints is decided by the node OR-Set; an edge is
    visible only if the edge tag is live AND both endpoints are live.

    Concurrent writes from the same parent become sibling edges.
    Merge is the OR-Set union — no LWW on structure.
    Linear order is a deterministic topological sort (depth, then id).
    """

    def __init__(self, replica_id: str):
        self.replica_id = replica_id
        self.edges = ORSet(replica_id)

    def link(self, parent_id: str, child_id: str) -> None:
        if parent_id == child_id:
            return
        self.edges.add(edge_key(parent_id, child_id))

    def unlink(self, parent_id: str, child_id: str) -> None:
        self.edges.remove(edge_key(parent_id, child_id))

    def merge(self, other: "CausalDAG") -> None:
        self.edges.merge(other.edges)

    def visible_edges(self, live_nodes: Set[str]) -> List[Tuple[str, str]]:
        out: List[Tuple[str, str]] = []
        for key in self.edges.elements():
            parent, child = split_edge_key(key)
            if parent in live_nodes and child in live_nodes:
                out.append((parent, child))
        return out

    def children_map(self, live_nodes: Set[str]) -> Dict[str, List[str]]:
        cmap: Dict[str, List[str]] = {nid: [] for nid in live_nodes}
        for parent, child in self.visible_edges(live_nodes):
            cmap.setdefault(parent, []).append(child)
            cmap.setdefault(child, [])
        for kids in cmap.values():
            kids.sort()
        return cmap

    def roots(self, live_nodes: Set[str]) -> List[str]:
        children = {c for _, c in self.visible_edges(live_nodes)}
        return sorted(nid for nid in live_nodes if nid not in children)

    def topological_order(self, live_nodes: Set[str]) -> List[str]:
        """Deterministic Kahn sort: roots first, then children by id."""
        cmap = self.children_map(live_nodes)
        incoming = {nid: 0 for nid in live_nodes}
        for parent, kids in cmap.items():
            for child in kids:
                incoming[child] = incoming.get(child, 0) + 1
        ready = sorted(nid for nid, deg in incoming.items() if deg == 0)
        order: List[str] = []
        seen: Set[str] = set()
        while ready:
            nid = ready.pop(0)
            if nid in seen:
                continue
            seen.add(nid)
            order.append(nid)
            nxt = []
            for child in cmap.get(nid, []):
                incoming[child] -= 1
                if incoming[child] == 0:
                    nxt.append(child)
            ready = sorted(ready + nxt)
        # cycles or detached: append leftovers deterministically
        leftover = sorted(live_nodes - seen)
        return order + leftover

    def forks(self, live_nodes: Set[str]) -> Dict[str, List[str]]:
        """Parents with more than one live child — concurrent hypotheses."""
        return {
            parent: kids
            for parent, kids in self.children_map(live_nodes).items()
            if len(kids) > 1
        }

    def render_tree(
        self,
        live_nodes: Set[str],
        labels: Dict[str, str],
    ) -> str:
        cmap = self.children_map(live_nodes)
        roots = self.roots(live_nodes)
        lines: List[str] = []

        def walk(nid: str, prefix: str, is_last: bool, is_root: bool) -> None:
            label = labels.get(nid, nid)
            if is_root:
                lines.append(label)
            else:
                lines.append(prefix + ("└─ " if is_last else "├─ ") + label)
            kids = cmap.get(nid, [])
            next_prefix = prefix + ("" if is_root else ("   " if is_last else "│  "))
            for i, kid in enumerate(kids):
                walk(kid, next_prefix, i == len(kids) - 1, False)

        for r in roots:
            walk(r, "", True, True)
        return "\n".join(lines) if lines else "[empty dag]"

    def to_dict(self) -> Dict[str, Any]:
        return {"replica_id": self.replica_id, "edges": self.edges.to_dict()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CausalDAG":
        dag = cls(data.get("replica_id", "unknown"))
        if "edges" in data:
            dag.edges = ORSet.from_dict(data["edges"])
        return dag


class CRDTThoughtState:
    """
    Replica state:
    - OR-Set for node membership (add/remove/resurrect)
    - LWW register per node payload
    - observed order filtered to live OR-Set elements
    """

    def __init__(self, replica_id: Optional[str] = None):
        self.replica_id = replica_id or str(uuid.uuid4())[:8]
        self.membership = ORSet(self.replica_id)
        self.payloads: Dict[str, LWWRegister] = {}
        self.dag = CausalDAG(self.replica_id)
        self.clock = HybridClock()
        self.order: List[str] = []
        self.version: int = 0

    @property
    def tombstones(self) -> Set[str]:
        """Derived: elements that have only removed tags (not visible)."""
        return {el for el in self.membership.adds if not self.membership.contains(el)}

    @property
    def nodes(self) -> Dict[str, Dict[str, Any]]:
        live: Dict[str, Dict[str, Any]] = {}
        for nid in self.membership.elements():
            reg = self.payloads.get(nid)
            if reg and isinstance(reg.value, dict):
                live[nid] = reg.value
        return live

    def add(self, node: ThoughtNode) -> None:
        self.membership.add(node.id)
        payload = node.to_dict()
        reg = self.payloads.get(node.id)
        if reg is None:
            reg = LWWRegister(self.replica_id)
            self.payloads[node.id] = reg
        wall, lamport = self.clock.tick(remote_wall=node.timestamp)
        incoming = LWWRegister(self.replica_id)
        incoming.set(payload, timestamp=wall, lamport=lamport)
        incoming.writer = getattr(node, "origin", None) or self.replica_id
        reg.merge(incoming)
        if node.parent_id:
            self.dag.link(node.parent_id, node.id)
        if node.id not in self.order:
            self.order.append(node.id)
        self._refresh_order()
        self.version += 1

    def remove(self, node_id: str) -> None:
        # Membership removal hides the node; DAG edges stay tagged so a later
        # resurrect reattaches the node to its original tree position.
        # visible_edges already filters endpoints by live membership.
        self.membership.remove(node_id)
        self._refresh_order()
        self.version += 1

    def merge(self, other: "CRDTThoughtState") -> None:
        self.membership.merge(other.membership)

        for nid, other_reg in other.payloads.items():
            self.clock.observe(other_reg.timestamp, other_reg.lamport)
            local = self.payloads.get(nid)
            if local is None:
                cloned = LWWRegister(self.replica_id)
                cloned.merge(other_reg)
                self.payloads[nid] = cloned
            else:
                local.merge(other_reg)

        self.dag.merge(other.dag)
        self._refresh_order()
        # version joins via max (CRDT semilattice) so double-merging is
        # byte-idempotent; only local add/remove bump it.
        self.version = max(self.version, other.version)

    def _refresh_order(self) -> None:
        live = set(self.membership.elements())
        self.order = self.dag.topological_order(live)

    def get_chain(self) -> List[ThoughtNode]:
        out: List[ThoughtNode] = []
        live = set(self.membership.elements())
        for nid in self.order:
            if nid not in live:
                continue
            data = self.payloads.get(nid)
            if data and isinstance(data.value, dict):
                out.append(_payload_to_node(data.value))
        return out

    def render_dag(self) -> str:
        live = set(self.membership.elements())
        labels: Dict[str, str] = {}
        for nid in live:
            reg = self.payloads.get(nid)
            if reg and isinstance(reg.value, dict):
                ctx = reg.value.get("context", "")
                cons = reg.value.get("consequence", nid)
                labels[nid] = f"!({cons}) <{ctx}>"
            else:
                labels[nid] = nid
        return self.dag.render_tree(live, labels)

    def forks(self) -> Dict[str, List[str]]:
        return self.dag.forks(set(self.membership.elements()))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "replica_id": self.replica_id,
            "membership": self.membership.to_dict(),
            "payloads": {nid: reg.to_dict() for nid, reg in self.payloads.items()},
            "dag": self.dag.to_dict(),
            "order": self.order,
            "tombstones": sorted(self.tombstones),
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CRDTThoughtState":
        state = cls(replica_id=data.get("replica_id"))
        if "membership" in data:
            state.membership = ORSet.from_dict(data["membership"])
            state.membership.replica_id = state.replica_id
        else:
            # backward compat with old tombstone JSON
            for nid, payload in data.get("nodes", {}).items():
                if nid not in data.get("tombstones", []):
                    node = _payload_to_node(payload)
                    state.add(node)
            for nid in data.get("tombstones", []):
                state.remove(nid)
        for nid, pdata in data.get("payloads", {}).items():
            state.payloads[nid] = LWWRegister.from_dict(state.replica_id, pdata)
        if "dag" in data:
            state.dag = CausalDAG.from_dict(data["dag"])
            state.dag.replica_id = state.replica_id
        state._refresh_order()
        state.version = data.get("version", 0)
        return state

    def save(self, path: str | Path) -> Path:
        p = Path(path)
        p.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False))
        return p

    @classmethod
    def load(cls, path: str | Path) -> "CRDTThoughtState":
        return cls.from_dict(json.loads(Path(path).read_text()))


class Expander(Protocol):
    """Any causal expander: seed concept → chain of ThoughtNodes."""

    def expand(self, seed: str, depth: int = 10) -> List[ThoughtNode]: ...


class LLMExpander:
    """Expander backed by any completion callable.

    Plugs into GhostGoat directly:
        LLMExpander(complete=lambda p: asyncio.run(gateway.complete(p)))
    Asks for one causal consequence per step in a strict parseable format:
        <consequence> ||| <context label>
    """

    FORMAT = "{consequence} ||| {context}"

    def __init__(self, complete: Callable[[str], str], max_words: int = 40):
        self.complete = complete
        self.max_words = max_words

    def _prompt(self, seed: str, history: List[str]) -> str:
        trail = " → ".join(history[-3:])
        return (
            "You are a causal thought mapper. Trail so far:\n"
            f"  {trail}\n"
            f"Continue it with ONE next causal consequence (max {self.max_words} words) "
            "and a short context label.\n"
            f"Respond with exactly: {self.FORMAT}\n"
            "No preamble, no bullets."
        )

    def expand(self, seed: str, depth: int = 10) -> List[ThoughtNode]:
        seed = seed.strip()
        root_id = _content_id("seed", seed, seed, "seed")
        chain = [
            ThoughtNode(
                id=root_id,
                predecessor=seed,
                consequence=seed,
                context="seed",
                depth=0,
                score=1.0,
                parent_id=None,
            )
        ]
        history = [seed]
        current = seed
        prev_id = root_id
        for i in range(1, depth + 1):
            raw = self.complete(self._prompt(seed, history)).strip()
            consequence, sep, context = raw.partition("|||")
            consequence = consequence.strip() or f"unparsed step {i}"
            context = (context.strip() or f"step {i}") if sep else f"step {i}"
            nid = _content_id(root_id, current, consequence, context)
            chain.append(
                ThoughtNode(
                    id=nid,
                    predecessor=current,
                    consequence=consequence,
                    context=context,
                    depth=i,
                    score=max(0.1, 0.95 - (i * 0.03)),
                    parent_id=prev_id,
                )
            )
            current = consequence
            prev_id = nid
            history.append(consequence)
        return chain


class LiquidS4Expander:
    """Autonomous Liquid-S4 specialized causal expander."""

    TRAJECTORY = [
        (
            "adaptive sequence modeling architecture that fuses liquid time-constant networks with structured state-space models",
            "core definition",
        ),
        (
            "built on linearized LTC dynamics dx/dt = (A + Bu)x + Bu combined with S4 DPLR parameterization",
            "technical foundation",
        ),
        (
            "introduces a liquid kernel that encodes input-sample similarities and autocorrelations at train and inference time",
            "key innovation",
        ),
        (
            "delivers long-range modeling with parameter efficiency versus classic S4 (224K vs 307K on Speech Commands with higher accuracy)",
            "empirical advantage",
        ),
        (
            "reaches 87.32% average accuracy on Long-Range Arena across ListOps, text, image, and path-finding tasks",
            "benchmark result",
        ),
        (
            "shows particular strength on raw audio and medical time-series where continuous-time adaptive dynamics are a natural prior",
            "domain strength",
        ),
        (
            "occupies an intermediate position between liquid neural networks and later selective SSMs such as Mamba",
            "conceptual placement",
        ),
        (
            "current limit is milder, structured input dependence compared with fully selective state mechanisms",
            "boundary",
        ),
        (
            "most promising evolution is hybridizing the liquid kernel with stronger input-dependent selection and discretization",
            "evolution vector",
        ),
        (
            "connects continuous-time adaptive computation, biological neural dynamics, and efficient long-context sequence modeling",
            "unexpected connection",
        ),
    ]

    def expand(self, seed: str, depth: int = 10) -> List[ThoughtNode]:
        current = seed.strip()
        seed_id = _content_id("seed", current, current, "seed")
        chain = [
            ThoughtNode(
                id=seed_id,
                predecessor=current,
                consequence=current,
                context="seed",
                depth=0,
                score=1.0,
                parent_id=None,
            )
        ]
        prev_id = seed_id
        for i, (cons, ctx) in enumerate(self.TRAJECTORY[:depth], start=1):
            nid = _content_id(seed_id, current, cons, ctx)
            node = ThoughtNode(
                id=nid,
                predecessor=current,
                consequence=cons,
                context=ctx,
                depth=i,
                score=max(0.1, 0.95 - (i * 0.03)),
                parent_id=prev_id,
            )
            chain.append(node)
            current = cons
            prev_id = nid
        return chain


class ThoughtMapper:
    def __init__(
        self,
        path: str = "liquid_s4_crdt_map.json",
        replica_id: Optional[str] = None,
        expander: Optional[Expander] = None,
    ):
        self.path = Path(path)
        self.state = CRDTThoughtState(replica_id=replica_id)
        self.expander: Expander = expander or LiquidS4Expander()
        self._lock = threading.RLock()
        if self.path.exists():
            try:
                self.state = CRDTThoughtState.load(self.path)
            except Exception as exc:
                logger.warning("Could not load %s, starting fresh: %s", self.path, exc)

    def run(self, concept: str = "liquid s4", depth: int = 10) -> str:
        with self._lock:
            for node in self.expander.expand(concept, depth=depth):
                self.state.add(node)
            self.state.save(self.path)
            linear = "\n".join(
                f"[{i}|d{node.depth}] {node.to_ctms()}"
                for i, node in enumerate(self.state.get_chain())
            )
            return linear + "\n\n--- DAG ---\n" + self.state.render_dag()

    def merge_peer(self, other: "str | Path | Dict[str, Any] | CRDTThoughtState") -> None:
        """Merge a peer replica from a file path, a serialized dict, or a live state."""
        if isinstance(other, CRDTThoughtState):
            incoming = other
        elif isinstance(other, dict):
            incoming = CRDTThoughtState.from_dict(other)
        elif isinstance(other, (str, Path)):
            incoming = CRDTThoughtState.load(other)
        else:
            raise TypeError(f"unsupported peer type: {type(other)!r}")
        with self._lock:
            self.state.merge(incoming)
            self.state.save(self.path)

    def get_state(self) -> CRDTThoughtState:
        return self.state


def map_liquid_s4(depth: int = 10) -> str:
    return ThoughtMapper().run("liquid s4", depth=depth)


if __name__ == "__main__":
    print(map_liquid_s4())
