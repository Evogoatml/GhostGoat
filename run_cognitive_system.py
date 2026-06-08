#!/usr/bin/env python3
"""GhostGoat Cognitive System — Main Bootstrap."""
import asyncio, json, logging, os, sys
from functools import partial
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
ABM_ROOT = str(ROOT / "agent_byte-master")
if ABM_ROOT not in sys.path:
    sys.path.insert(0, ABM_ROOT)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("ghostgoat.bootstrap")

from config.unified_config import get_config
from core.reasoning.brain.core import DualBrain
from core.reasoning.brain.knowledge.knowledge_tank import KnowledgeTank
from core.graphrag.engine import GraphRAGEngine
from core.cognitive.neuro_react_engine import NeuroReactCognitiveEngine
from core.agents.agent_core.agent_network import AgentNetwork
from core.memory.networked_memory import NetworkedMemory
from core.workflows.engine import WorkflowEngine


def bootstrap() -> Dict[str, Any]:
    logger.info("=== GhostGoat Cognitive System Bootstrap ===")
    config = get_config()
    logger.info("Config loaded: base_path=%s", config.base_path)
    brain = DualBrain(name="ghostgoat", dimension=128, config={"learning_rate": 0.01})
    logger.info("[1/7] DualBrain ready: %s", brain.brain_id)
    kt = KnowledgeTank(storage_path=str(Path.home() / ".ghostgoat" / "knowledge_tank"))
    logger.info("[2/7] KnowledgeTank ready: %d entries", len(kt.entries))
    graphrag = GraphRAGEngine(storage_path=str(Path.home() / ".ghostgoat" / "graphrag"))
    logger.info("[3/7] GraphRAGEngine ready: %d nodes, %d edges", len(graphrag.nodes), len(graphrag.edges))
    mem = NetworkedMemory(storage_path=str(Path.home() / ".ghostgoat" / "memory"))
    logger.info("[4/7] NetworkedMemory ready")
    engine = NeuroReactCognitiveEngine(brain=brain, graphrag=graphrag, knowledge_tank=kt,
                                       config={"max_steps_per_query": 5, "temperature": 0.7})
    logger.info("[5/7] NeuroReactCognitiveEngine ready: %s", engine.engine_id)
    network = AgentNetwork(max_agents=50)
    network.spawn_default_fleet()
    logger.info("[6/7] AgentNetwork ready: %d agents", len(network.profiles))
    wf = WorkflowEngine(workflows_dir=str(Path(ABM_ROOT) / "core" / "workflows" / "definitions"))
    logger.info("[7/7] WorkflowEngine ready: %d workflows", len(wf.workflows))
    return {"config": config, "brain": brain, "knowledge_tank": kt, "graphrag": graphrag,
            "memory": mem, "engine": engine, "network": network, "workflows": wf}


async def demo_goal(system: Dict[str, Any], goal: str):
    engine = system["engine"]
    network = system["network"]
    agents = {aid: partial(network.dispatch, aid) for aid in network.executors.keys()}
    return await engine.process(goal, agents=agents)


async def interactive_shell(system: Dict[str, Any]):
    print("\n🧠 GhostGoat Cognitive System Online")
    print("Type a goal. Commands: status, agents, workflows, brain, graph, quit\n")
    while True:
        try: line = input("🎯 Goal > ").strip()
        except (EOFError, KeyboardInterrupt): break
        if not line: continue
        if line.lower() == "quit": break
        if line.lower() == "status":
            print(json.dumps({"brain": system["brain"].get_state(), "network": system["network"].get_fleet_status(),
                              "workflows": system["workflows"].list_workflows(), "memory": system["memory"].stats()}, indent=2, default=str))
            continue
        if line.lower() == "agents":
            print(json.dumps(system["network"].get_fleet_status(), indent=2, default=str)); continue
        if line.lower() == "workflows":
            print(json.dumps(system["workflows"].list_workflows(), indent=2, default=str)); continue
        if line.lower() == "brain":
            print(json.dumps(system["brain"].get_state(), indent=2, default=str)); continue
        if line.lower() == "graph":
            print(json.dumps(system["graphrag"].get_stats(), indent=2, default=str)); continue
        result = await demo_goal(system, line)
        print(json.dumps(result, indent=2, default=str))


async def main():
    system = bootstrap()
    if len(sys.argv) > 1:
        result = await demo_goal(system, " ".join(sys.argv[1:]))
        print(json.dumps(result, indent=2, default=str))
    else:
        await interactive_shell(system)


if __name__ == "__main__":
    asyncio.run(main())



