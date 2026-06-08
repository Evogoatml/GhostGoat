#!/usr/bin/env python3
"""GhostGoat namespace shim v3."""
import sys, types, importlib, importlib.util, os

ROOT = os.path.dirname(os.path.abspath(__file__))
ABM  = os.path.join(ROOT, "agent_byte-master")
for p in [ROOT, ABM]:
    if p not in sys.path:
        sys.path.insert(0, p)

def _pkg(name):
    if name not in sys.modules:
        m = types.ModuleType(name)
        m.__path__ = []; m.__package__ = name
        sys.modules[name] = m
    return sys.modules[name]

def _load_file(modname, filepath):
    try:
        spec = importlib.util.spec_from_file_location(modname, filepath)
        mod  = importlib.util.module_from_spec(spec)
        sys.modules[modname] = mod
        parts = modname.split(".")
        for i in range(1, len(parts)):
            _pkg(".".join(parts[:i]))
        spec.loader.exec_module(mod)
        print(f"[shim]   OK  : {modname} (direct)")
        return mod
    except Exception as e:
        print(f"[shim]   FAIL: {modname}: {e}")
        return None

def _alias(fake, real):
    try:
        mod = importlib.import_module(real)
        sys.modules[fake] = mod
        parts = fake.split(".")
        for i in range(1, len(parts)):
            _pkg(".".join(parts[:i]))
        print(f"[shim]   OK  : {fake} -> {real}")
        return mod
    except Exception as e:
        print(f"[shim]   FAIL: {fake} -> {real}: {e}")
        return None

def _stub(modname, **attrs):
    m = types.ModuleType(modname)
    m.__path__ = []; m.__package__ = modname
    for k,v in attrs.items(): setattr(m, k, v)
    parts = modname.split(".")
    for i in range(1, len(parts)):
        _pkg(".".join(parts[:i]))
    sys.modules[modname] = m
    print(f"[shim]   OK  : {modname} (stub)")
    return m

print("[shim] v3 starting...")

B  = os.path.join(ABM, "brain")
KP = os.path.join(B, "knowledge", "processed", "knowledge")

for modname, fp in [
    ("brain.knowledge.processed.knowledge.pattern_interpreter", os.path.join(KP, "pattern_interpreter.py")),
    ("brain.knowledge.processed.knowledge.decision_maker",      os.path.join(KP, "decision_maker.py")),
    ("brain.knowledge.processed.knowledge.skill_discovery",     os.path.join(KP, "skill_discovery.py")),
]:
    _load_file(modname, fp)

for pkg in ["brain.knowledge.processed","brain.knowledge.processed.knowledge",
            "brain.knowledge.processed.test","brain.knowledge.processed.train",
            "brain.knowledge.processed.val","brain.knowledge.promoted",
            "brain.knowledge.raw","brain.knowledge.replay_buffer","brain.knowledge.metadata"]:
    _pkg(pkg)

_load_file("brain.orchestrator.memory.vault", os.path.join(B,"orchestrator","memory","vault.py"))
try:
    import brain.orchestrator.memory.vault as _v
    if not hasattr(_v, "Vault"):
        _v.Vault = _v.EncryptedVault
    print("[shim]   OK  : vault.Vault aliased")
except Exception as e:
    print(f"[shim]   WARN: vault: {e}")

class _NetworkedMemory:
    def __init__(self, storage_path=""):
        self.storage_path = storage_path; self._s = {}
    def store(self, k, v): self._s[k] = v
    def retrieve(self, k): return self._s.get(k)
    def stats(self): return {"entries": len(self._s)}

class _WorkflowEngine:
    def __init__(self, workflows_dir=""):
        self.workflows = {}
        if os.path.isdir(workflows_dir):
            for f in os.listdir(workflows_dir):
                self.workflows[f] = {"name": f}
    def list_workflows(self): return self.workflows
    def run(self, name, **kw): return {"workflow": name, "status": "ok"}

class _ServiceRegistry:
    def __init__(self): self._s = {}
    def register(self, n, live=True): self._s[n] = live
    def list_services(self): return self._s

async def _handle_async(desc, ctx=None): return {"status":"ok","result":"stub"}
def _handle(desc, ctx=None): return {"status":"ok","result":"stub"}
def _analyze(*a,**k): return {"efficiency":1.0}

_sr = _ServiceRegistry()
_srm = _stub("core.service_registry", ServiceRegistry=_ServiceRegistry, registry=_sr)
_srm.registry = _sr
_stub("core.task_handler", handle_task=_handle, handle_task_async=_handle_async)
_stub("core.agents.agent_core.efficiency_engine", analyze_efficiency=_analyze)
_stub("core.memory.networked_memory", NetworkedMemory=_NetworkedMemory)
_stub("core.workflows.engine", WorkflowEngine=_WorkflowEngine)

print("[shim] Real aliases (direct file load)...")

# Load brain modules directly by absolute path
_load_file("brain.dual_brain",
    os.path.join(ABM, "brain", "dual_brain.py"))
_load_file("brain.knowledge.knowledge_tank",
    os.path.join(ABM, "brain", "knowledge", "knowledge_tank.py"))
# neuro_react_engine imports core.reasoning internally — load AFTER aliases registered
# handled below after alias registration
_load_file("brain.knowledge.holographic_node_graph_rag",
    os.path.join(ABM, "brain", "knowledge", "holographic_node_graph_rag.py"))

# Now alias phantom names to the loaded modules
for fake, real in [
    ("core.reasoning.brain.core",                     "brain.dual_brain"),
    ("core.reasoning.brain.dual_brain",               "brain.dual_brain"),
    ("core.reasoning.brain.knowledge.knowledge_tank", "brain.knowledge.knowledge_tank"),
    ("core.cognitive.neuro_react_engine",             "brain.neuro_react_engine"),
    ("core.agents.agent_core.agent_network",          "agents.agent_network"),
    ("core.agent_network",                            "agents.agent_network"),
    ("core.graphrag.engine",                          "brain.knowledge.holographic_node_graph_rag"),
]:
    if real in sys.modules:
        sys.modules[fake] = sys.modules[real]
        parts = fake.split(".")
        for i in range(1, len(parts)):
            _pkg(".".join(parts[:i]))
        print(f"[shim]   OK  : {fake} -> {real}")
    else:
        _alias(fake, real)

# Inject GraphRAGEngine alias into holographic_node_graph_rag before neuro_react loads
try:
    import brain.knowledge.holographic_node_graph_rag as _hrag
    if not hasattr(_hrag, "GraphRAGEngine"):
        _GraphRAGStore = _hrag.GraphRAGStore
        class GraphRAGEngine(_GraphRAGStore):
            def __init__(self, storage_path=None, root_path=None, **kw):
                super().__init__(root_path=storage_path or root_path, **kw)
                self.nodes = list(self.graph.nodes()) if self.graph else []
                self.edges = list(self.graph.edges()) if self.graph else []
            def get_stats(self):
                return {"nodes": len(self.nodes), "edges": len(self.edges)}
        def query_context(self, query: str, max_tokens: int = 1500) -> str:
                """Return relevant text chunks for the query."""
                if not self._chunks:
                    self._load_files()
                if not self._chunks:
                    return ""
                q = query.lower()
                hits = [c for c in self._chunks if any(w in c.lower() for w in q.split())]
                result = " ".join(hits[:10])
                return result[:max_tokens] if result else ""

        GraphRAGEngine.query_context = query_context
        def query_context(self, query: str, max_tokens: int = 1500) -> str:
                """Return relevant text chunks for the query."""
                if not self._chunks:
                    self._load_files()
                if not self._chunks:
                    return ""
                q = query.lower()
                hits = [c for c in self._chunks if any(w in c.lower() for w in q.split())]
                result = " ".join(hits[:10])
                return result[:max_tokens] if result else ""

        def query_context(self, query: str, max_tokens: int = 1500) -> str:
                if not self._chunks:
                    self._load_files()
                q = query.lower()
                hits = [c for c in self._chunks if any(w in c.lower() for w in q.split())]
                result = " ".join(hits[:10])
                return result[:max_tokens] if result else ""

        def add_node(self, label: str = "", content: str = "", **kw) -> str:
                import uuid as _uuid
                nid = f"n-{_uuid.uuid4().hex[:8]}"
                if self.graph is not None:
                    self.graph.add_node(nid, label=label, content=content, **kw)
                self.nodes.append(nid)
                return nid

        def add_edge(self, src: str, dst: str, rel: str = "", **kw) -> None:
                if self.graph is not None:
                    self.graph.add_edge(src, dst, rel=rel, **kw)
                self.edges.append((src, dst))

        def get_stats(self) -> dict:
                return {"nodes": len(self.nodes), "edges": len(self.edges)}

        GraphRAGEngine.query_context = query_context
        GraphRAGEngine.add_node = add_node
        GraphRAGEngine.add_edge = add_edge
        GraphRAGEngine.get_stats = get_stats
        _hrag.GraphRAGEngine = GraphRAGEngine
        print("[shim]   OK  : GraphRAGEngine wrapper created")
except Exception as e:
    print(f"[shim]   WARN: GraphRAGEngine alias failed: {e}")

# Now load neuro_react_engine AFTER core.reasoning.* are registered
_load_file("brain.neuro_react_engine",
    os.path.join(ABM, "brain", "neuro_react_engine.py"))
if "brain.neuro_react_engine" in sys.modules:
    sys.modules["core.cognitive.neuro_react_engine"] = sys.modules["brain.neuro_react_engine"]
    print("[shim]   OK  : core.cognitive.neuro_react_engine rebound")

print("[shim] Done.")
