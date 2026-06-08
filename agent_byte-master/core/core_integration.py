"""
GhostGoat Core Integration
Connects all core/ subsystems into a single coherent system.

Subsystems wired (lazy-loaded for low startup latency):
  - NeuroGraph        (core/neurograph.py)          nervous system graph
  - Optimizer         (core/optimizer.py)            performance tracking
  - DistributedAgents (core/agents/)                 folder agents + neural backend
  - AgentNetwork      (core/agents/agent_core/)      SSH agent mesh
  - CognitiveEngine   (core/agents/agent_core/)      reasoning engine
  - Diagnostics       (core/diagnostics/)            health checks + self-heal
  - Memory            (core/memory/)                 multi-backend memory
  - Reasoning         (core/reasoning/)              brain + reasoning core
  - Governance        (core/governance/)             decision governor + task routing
  - Learning          (core/learning/)               learning core + user behavior
  - TaskHandler       (core/task_handler.py)         task dispatch
  - ACS_SYSTEM        (ACS_SYSTEM/)                  post-quantum crypto, cipher DSL, hybrid encryption
  - AgentFrameworks   (frameworks/agents/)            CrewAI / Swarms multi-agent adapters

Architecture note:
  Subsystems are lazy-initialized on first access via descriptors.
  This keeps startup fast (~0ms) and only pays init cost for subsystems
  actually used in a given request path. Proper separation lowers latency.
"""

import os
import logging
import threading
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_CORE_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT_DIR = os.path.dirname(_CORE_DIR)


class _LazySubsystem:
    """Descriptor that lazily initializes a subsystem on first access.

    Each subsystem loads independently — a failure in one never blocks another.
    Init cost is paid once, on first access, then cached on the instance.
    """

    def __init__(self, attr_name: str, init_func_name: str):
        self.attr_name = attr_name
        self.private_name = f"_lazy_{attr_name}"
        self.sentinel_name = f"_loaded_{attr_name}"
        self.init_func_name = init_func_name

    def __set_name__(self, owner, name):
        pass

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        if not getattr(obj, self.sentinel_name, False):
            init_fn = getattr(obj, self.init_func_name)
            init_fn()
            setattr(obj, self.sentinel_name, True)
        return getattr(obj, self.private_name, None)

    def __set__(self, obj, value):
        setattr(obj, self.private_name, value)
        setattr(obj, self.sentinel_name, True)


class CoreIntegration:
    """Single object that holds references to every core subsystem.

    Subsystems are lazy-loaded: each one initializes on first access, not at
    construction time.  This means constructing CoreIntegration is near-instant
    and only the subsystems actually touched during a request path pay their
    initialization cost.
    """

    # Lazy descriptors — each maps a public attribute to its init method
    neurograph = _LazySubsystem("neurograph", "_init_neurograph")
    optimizer = _LazySubsystem("optimizer", "_init_optimizer")
    agent_system = _LazySubsystem("agent_system", "_init_distributed_agents")
    agent_network = _LazySubsystem("agent_network", "_init_agent_network")
    cognitive_engine = _LazySubsystem("cognitive_engine", "_init_cognitive_engine")
    diagnostics = _LazySubsystem("diagnostics", "_init_diagnostics")
    memory_context = _LazySubsystem("memory_context", "_init_context_memory")
    embedding_memory = _LazySubsystem("embedding_memory", "_init_embedding_memory")
    reasoning_core = _LazySubsystem("reasoning_core", "_init_reasoning")
    task_handler = _LazySubsystem("task_handler", "_init_task_handler")
    learning = _LazySubsystem("learning", "_init_learning")
    governance = _LazySubsystem("governance", "_init_governance")
    crystal_kyber = _LazySubsystem("crystal_kyber", "_init_crystal_kyber")
    cipher_dsl = _LazySubsystem("cipher_dsl", "_init_cipher_dsl")
    hybrid_crypto = _LazySubsystem("hybrid_crypto", "_init_hybrid_crypto")
    translator_gate = _LazySubsystem("translator_gate", "_init_translator_gate")
    asi = _LazySubsystem("asi", "_init_asi")
    agent_frameworks = _LazySubsystem("agent_frameworks", "_init_agent_frameworks")
    self_aware_loop = _LazySubsystem("self_aware_loop", "_init_self_aware_loop")

    def __init__(self, root_dir: Optional[str] = None):
        self.root_dir = root_dir or _ROOT_DIR
        self.core_dir = os.path.join(self.root_dir, "core")

        # Background diagnostics state
        self._bg_health: Dict[str, Any] = {}
        self._bg_health_lock = threading.Lock()
        self._bg_health_thread: Optional[threading.Thread] = None

        logger.info("CoreIntegration created (lazy init, subsystems load on demand)")

    # ------------------------------------------------------------------
    # Lazy init methods — each called at most once per subsystem
    # ------------------------------------------------------------------

    def _init_neurograph(self):
        try:
            from core.memory.neurograph import NeuroGraph
            self._lazy_neurograph = NeuroGraph()
            logger.info("NeuroGraph online")
        except Exception as e:
            self._lazy_neurograph = None
            logger.warning("NeuroGraph unavailable: %s", e)

    def _init_optimizer(self):
        try:
            from core.brain.memory.optimizer import Optimizer
            db_path = os.path.join(self.root_dir, "data", "performance.db")
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            self._lazy_optimizer = Optimizer(db_path)
            logger.info("Optimizer online (db: %s)", db_path)
        except Exception as e:
            self._lazy_optimizer = None
            logger.warning("Optimizer unavailable: %s", e)

    def _init_distributed_agents(self):
        try:
            from core.kernel.distributed_agent_system import DistributedAgentSystem
            self._lazy_agent_system = DistributedAgentSystem(root_dir=self.root_dir)
            logger.info("Distributed agent system online")
        except Exception as e:
            self._lazy_agent_system = None
            logger.warning("Distributed agent system unavailable: %s", e)

    def _init_agent_network(self):
        try:
            from core.brain.agent_core.agent_network import AgentNetwork
            self._lazy_agent_network = AgentNetwork()
            logger.info("AgentNetwork online")
        except Exception as e:
            self._lazy_agent_network = None
            logger.warning("AgentNetwork unavailable: %s", e)

    def _init_cognitive_engine(self):
        try:
            from core.kernel.engine.cognitive_engine import CognitiveEngine
            self._lazy_cognitive_engine = CognitiveEngine()
            logger.info("CognitiveEngine online")
        except Exception as e:
            self._lazy_cognitive_engine = None
            logger.warning("CognitiveEngine unavailable: %s", e)

    def _init_diagnostics(self):
        try:
            from core.diagnostics.self_check import run_all as run_diagnostics
            from core.diagnostics.network_context import internet_available
            self._lazy_diagnostics = {
                "run_all": run_diagnostics,
                "internet_available": internet_available,
            }
            logger.info("Diagnostics online")
        except Exception as e:
            self._lazy_diagnostics = None
            logger.warning("Diagnostics unavailable: %s", e)

    def _init_context_memory(self):
        try:
            from core.memory.context_memory import ContextMemory
            self._lazy_memory_context = ContextMemory()
            logger.info("ContextMemory online")
        except Exception as e:
            self._lazy_memory_context = None
            logger.warning("ContextMemory unavailable: %s", e)

    def _init_embedding_memory(self):
        try:
            from core.memory.embedding_memory import EmbeddingMemory
            self._lazy_embedding_memory = EmbeddingMemory()
            logger.info("EmbeddingMemory online")
        except Exception as e:
            self._lazy_embedding_memory = None
            logger.warning("EmbeddingMemory unavailable: %s", e)

    def _init_reasoning(self):
        try:
            from core.brain.agent_core.reasoning_core import ReasoningCore
            self._lazy_reasoning_core = ReasoningCore()
            logger.info("ReasoningCore online")
        except Exception as e:
            self._lazy_reasoning_core = None
            logger.warning("ReasoningCore unavailable: %s", e)

    def _init_learning(self):
        try:
            from core.brain.agent_core import reasoning_core as learning_core
            self._lazy_learning = {
                "record": learning_core.record,
                "load": learning_core.load,
                "summarize": learning_core.summarize,
                "user_behavior": user_behavior,
            }
            logger.info("Learning modules online")
        except Exception as e:
            self._lazy_learning = None
            logger.warning("Learning modules unavailable: %s", e)

    def _init_governance(self):
        try:
            from core.governance.decision_governor import allow_external_calls
            from core.governance.task_handler import handle as governance_handle
            self._lazy_governance = {
                "allow_external_calls": allow_external_calls,
                "handle": governance_handle,
            }
            logger.info("Governance online")
        except Exception as e:
            self._lazy_governance = None
            logger.warning("Governance unavailable: %s", e)

    def _init_task_handler(self):
        try:
            from core.governance.task_handler import handle_task
            self._lazy_task_handler = handle_task
            logger.info("TaskHandler online")
        except Exception as e:
            self._lazy_task_handler = None
            logger.warning("TaskHandler unavailable: %s", e)

    def _init_crystal_kyber(self):
        try:
            from ACS_SYSTEM.advanced_ciphers import CrystalKyber
            self._lazy_crystal_kyber = CrystalKyber(security_level=3)
            logger.info("CrystalKyber (NIST Level 3) online")
        except Exception as e:
            self._lazy_crystal_kyber = None
            logger.warning("CrystalKyber unavailable: %s", e)

    def _init_cipher_dsl(self):
        try:
            from ACS_SYSTEM.crystal_crypto.crypto_core import CipherDSL, CipherPolicy, CipherTemplate
            self._lazy_cipher_dsl = {
                "dsl": CipherDSL(),
                "policy": CipherPolicy,
                "templates": CipherTemplate,
            }
            logger.info("CipherDSL online")
        except Exception as e:
            self._lazy_cipher_dsl = None
            logger.warning("CipherDSL unavailable: %s", e)

    def _init_hybrid_crypto(self):
        try:
            from ACS_SYSTEM.crystal_crypto.crystal_system import HybridCryptoSystem
            self._lazy_hybrid_crypto = HybridCryptoSystem()
            logger.info("HybridCryptoSystem (Kyber+AES-GCM+Dilithium) online")
        except Exception as e:
            self._lazy_hybrid_crypto = None
            logger.warning("HybridCryptoSystem unavailable: %s", e)

    def _init_translator_gate(self):
        try:
            from ACS_SYSTEM.adap_dia_sys.translator_gate import process_upload, quarantine_file
            self._lazy_translator_gate = {
                "process_upload": process_upload,
                "quarantine_file": quarantine_file,
            }
            logger.info("TranslatorGate online")
        except Exception as e:
            self._lazy_translator_gate = None
            logger.warning("TranslatorGate unavailable: %s", e)

    def _init_asi(self):
        try:
            from pathlib import Path
            from ACS_SYSTEM.core.asi_core import SelfModifyingDiagnostics
            self._lazy_asi = SelfModifyingDiagnostics(nexus_root=Path(self.root_dir))
            logger.info("ASI self-modifying diagnostics online")
        except Exception as e:
            self._lazy_asi = None
            logger.warning("ASI diagnostics unavailable: %s", e)

    def _init_agent_frameworks(self):
        try:
            from frameworks.agents.registry import list_frameworks, get_framework
            available = list_frameworks()
            self._lazy_agent_frameworks = {
                "available": available,
                "list_frameworks": list_frameworks,
                "get_framework": get_framework,
            }
            live = [k for k, v in available.items() if v]
            logger.info("Agent frameworks online (installed: %s)",
                        ", ".join(live) if live else "none")
        except Exception as e:
            self._lazy_agent_frameworks = None
            logger.warning("Agent frameworks unavailable: %s", e)

    def _init_self_aware_loop(self):
        try:
            from core.brain.agents.self_aware_loop import SelfAwareLoop
            self._lazy_self_aware_loop = SelfAwareLoop(self)
            logger.info("SelfAwareLoop online")
        except Exception as e:
            self._lazy_self_aware_loop = None
            logger.warning("SelfAwareLoop unavailable: %s", e)

    # ------------------------------------------------------------------
    # Eager init (opt-in) — for startup scripts that want everything ready
    # ------------------------------------------------------------------

    def init_all(self):
        """Force-initialize every subsystem. Use for startup/warm-up only."""
        _ = self.neurograph
        _ = self.optimizer
        _ = self.agent_system
        _ = self.agent_network
        _ = self.cognitive_engine
        _ = self.diagnostics
        _ = self.memory_context
        _ = self.embedding_memory
        _ = self.reasoning_core
        _ = self.task_handler
        _ = self.learning
        _ = self.governance
        _ = self.crystal_kyber
        _ = self.cipher_dsl
        _ = self.hybrid_crypto
        _ = self.translator_gate
        _ = self.asi
        _ = self.agent_frameworks
        _ = self.self_aware_loop

        live = sum(1 for v in self.status().values() if v)
        total = len(self.status())
        logger.info("Core integration (eager): %d/%d subsystems online", live, total)

    # ------------------------------------------------------------------
    # Status / health
    # ------------------------------------------------------------------

    def status(self) -> Dict[str, bool]:
        """Return which subsystems have been loaded and are live.

        Only reports on subsystems that have actually been accessed (lazy).
        """
        def _loaded(attr: str) -> bool:
            return getattr(self, f"_loaded_{attr}", False) and getattr(self, f"_lazy_{attr}", None) is not None

        return {
            "neurograph": _loaded("neurograph"),
            "optimizer": _loaded("optimizer"),
            "distributed_agents": _loaded("agent_system"),
            "agent_network": _loaded("agent_network"),
            "cognitive_engine": _loaded("cognitive_engine"),
            "diagnostics": _loaded("diagnostics"),
            "context_memory": _loaded("memory_context"),
            "embedding_memory": _loaded("embedding_memory"),
            "reasoning_core": _loaded("reasoning_core"),
            "learning": _loaded("learning"),
            "governance": _loaded("governance"),
            "task_handler": _loaded("task_handler"),
            "crystal_kyber": _loaded("crystal_kyber"),
            "cipher_dsl": _loaded("cipher_dsl"),
            "hybrid_crypto": _loaded("hybrid_crypto"),
            "translator_gate": _loaded("translator_gate"),
            "asi_diagnostics": _loaded("asi"),
            "agent_frameworks": _loaded("agent_frameworks"),
            "self_aware_loop": _loaded("self_aware_loop"),
        }

    def health_check(self) -> Dict[str, Any]:
        """Run health checks across loaded subsystems."""
        report: Dict[str, Any] = {"subsystems": self.status()}

        if self.neurograph:
            report["neurograph"] = self.neurograph.health_check()

        if self.diagnostics:
            report["network"] = self.diagnostics["internet_available"]()

        if self.agent_system:
            report["registered_agents"] = len(self.agent_system.list_agents())

        if self.self_aware_loop:
            report["self_aware_loop"] = self.self_aware_loop.status()

        return report

    def start_self_aware(self):
        """Start the self-healing / self-optimizing / self-aware feedback loop.

        Call this once during startup.  The loop runs in a daemon thread and
        periodically checks all subsystems, heals problems, and adapts its
        own check frequency based on system stability.
        """
        sal = self.self_aware_loop
        if sal:
            sal.start()
        else:
            logger.warning("SelfAwareLoop not available — self-healing disabled")

    def health_check_async(self) -> Dict[str, Any]:
        """Return cached background health data (non-blocking).

        Call start_background_health() once to begin periodic checks.
        """
        with self._bg_health_lock:
            return dict(self._bg_health)

    def start_background_health(self, interval_s: float = 30.0):
        """Start background thread that periodically runs health_check().

        This keeps health data fresh without blocking the hot path.
        """
        if self._bg_health_thread is not None and self._bg_health_thread.is_alive():
            return

        import time

        def _loop():
            while True:
                try:
                    result = self.health_check()
                    with self._bg_health_lock:
                        self._bg_health = result
                except Exception as e:
                    logger.warning("Background health check failed: %s", e)
                time.sleep(interval_s)

        t = threading.Thread(target=_loop, daemon=True, name="ghostgoat-health")
        t.start()
        self._bg_health_thread = t
        logger.info("Background health monitor started (interval=%ss)", interval_s)

    # ------------------------------------------------------------------
    # Cross-system wiring helpers
    # ------------------------------------------------------------------

    def register_agent_in_graph(self, agent_id: str, agent_data: Dict):
        """Register an agent node in the NeuroGraph."""
        if self.neurograph:
            self.neurograph.add_node(agent_id, kind="agent", data=agent_data)

    def register_task_in_graph(self, task_id: str, task_data: Dict, agent_id: str = None):
        """Register a task node and optionally link it to an agent."""
        if self.neurograph:
            self.neurograph.add_node(task_id, kind="task", data=task_data)
            if agent_id:
                self.neurograph.add_edge(agent_id, task_id, relation="handles")

    def observe_performance(self, user_id: str, action: str, result: str):
        """Track performance through the optimizer."""
        if self.optimizer:
            self.optimizer.observe(user_id, action, result)

    def reason(self, context: Dict) -> Optional[Dict]:
        """Run cognitive reasoning on a context."""
        if self.cognitive_engine:
            return self.cognitive_engine.reason(context)
        return None

    def dispatch_task(self, task: str):
        """Route a task through the task handler."""
        if self.task_handler:
            return self.task_handler(task)
        logger.warning("No task handler available")
        return None

    def encrypt(self, data: bytes, recipient_public_key: bytes,
                sender_private_key: bytes = None) -> dict:
        """Encrypt data using the hybrid post-quantum crypto system."""
        if self.hybrid_crypto:
            return self.hybrid_crypto.encrypt(data, recipient_public_key, sender_private_key)
        raise RuntimeError("HybridCryptoSystem not available")

    def decrypt(self, package: dict, recipient_private_key: bytes,
                sender_public_key: bytes = None) -> bytes:
        """Decrypt data using the hybrid post-quantum crypto system."""
        if self.hybrid_crypto:
            return self.hybrid_crypto.decrypt(package, recipient_private_key, sender_public_key)
        raise RuntimeError("HybridCryptoSystem not available")

    def run_agent_task(self, agents, tasks, framework: str = None):
        """Run a multi-agent task through CrewAI or Swarms.

        Args:
            agents: List of AgentSpec dicts/objects.
            tasks: List of TaskSpec dicts/objects.
            framework: "crewai", "swarms", or None (auto-select).

        Returns:
            RunResult from the selected framework.
        """
        if not self.agent_frameworks:
            raise RuntimeError("No agent frameworks available")

        from frameworks.agents.base import AgentSpec, TaskSpec
        get_fw = self.agent_frameworks["get_framework"]
        fw = get_fw(framework)

        for a in agents:
            spec = a if isinstance(a, AgentSpec) else AgentSpec(**a)
            fw.add_agent(spec)

        task_specs = []
        for t in tasks:
            spec = t if isinstance(t, TaskSpec) else TaskSpec(**t)
            task_specs.append(spec)

        return fw.run(task_specs)

    def execute_cipher_chain(self, chain_dsl: str, data):
        """Parse and execute a CipherDSL chain string."""
        if self.cipher_dsl:
            dsl = self.cipher_dsl["dsl"]
            chain = dsl.parse_dsl(chain_dsl)
            return dsl.execute_chain(chain, data)
        raise RuntimeError("CipherDSL not available")


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
_instance: Optional[CoreIntegration] = None


def get_core(root_dir: Optional[str] = None) -> CoreIntegration:
    """Get or create the global CoreIntegration instance."""
    global _instance
    if _instance is None:
        _instance = CoreIntegration(root_dir=root_dir)
    return _instance
