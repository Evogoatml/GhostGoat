"""
GhostGoat Ordinance System
Distributed Agent System with Central Neural Network

Every folder gets an AGENT.md auto-populated with its context.
All agents share one neural backend (.backend/).

Quick start
-----------
    from core.ordinance.distributed_system import DistributedAgentSystem; from core.ordinance.ordinance_client import OrdinanceClient

    # Generate AGENT.md in every folder
    system = DistributedAgentSystem()
    system.scan()

    # Query from anywhere
    client = OrdinanceClient()
    ctx    = client.get_folder_context("core/pipeline")
    hits   = client.search("block encoder")
"""
from core.ordinance.central_backend   import CentralNeuralBackend
from core.ordinance.folder_agent      import FolderAgent
from core.ordinance.distributed_system import DistributedAgentSystem
from core.ordinance.ordinance_client   import OrdinanceClient

__all__ = [
    "CentralNeuralBackend",
    "FolderAgent",
    "DistributedAgentSystem",
    "OrdinanceClient",
]
