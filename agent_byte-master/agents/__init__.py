"""
GhostGoat Agent Subsystem

Includes the base agent class, specialist agents, and the Agent Byte
neural-symbolic RL integration.
"""

from agents.base import AgentSpec, AgentFramework as BaseAgent

# Agent Byte integration (optional — only if package is present)
try:
    from integrations.agent_byte_integration import (
        AgentByteAgent,
        GhostGoatTaskEnvironment,
        register_agent_byte,
    )
    _AGENT_BYTE_AVAILABLE = True
except Exception as _abe:
    _AGENT_BYTE_AVAILABLE = False
    AgentByteAgent = None  # type: ignore
    GhostGoatTaskEnvironment = None  # type: ignore
    register_agent_byte = None  # type: ignore

__all__ = [
    "BaseAgent",
    
    "AgentByteAgent",
    "GhostGoatTaskEnvironment",
    "register_agent_byte",
]

