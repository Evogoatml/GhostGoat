"""
Unified Configuration System for GhostGoat Ecosystem
Provides centralized configuration management for all agent systems
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class LLMProvider(Enum):
    """Supported LLM providers"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    MOCK = "mock"
    LOCAL = "local"


class MemoryBackend(Enum):
    """Supported memory backends"""
    CHROMADB = "chromadb"
    KNOWLEDGE_TANK = "knowledge_tank"
    SQLITE = "sqlite"
    MEMORY = "memory"


@dataclass
class LLMConfig:
    """LLM configuration"""
    provider: LLMProvider = LLMProvider.OPENAI
    model: str = "gpt-4"
    api_key: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 2000
    timeout: int = 30
    
    @classmethod
    def from_env(cls) -> 'LLMConfig':
        """Load from environment variables"""
        provider_str = os.getenv("LLM_PROVIDER", "openai").lower()
        try:
            provider = LLMProvider(provider_str)
        except ValueError:
            provider = LLMProvider.OPENAI
        
        return cls(
            provider=provider,
            model=os.getenv("LLM_MODEL", "gpt-4"),
            api_key=os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY"),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("LLM_MAX_TOKENS", "2000")),
            timeout=int(os.getenv("LLM_TIMEOUT", "30"))
        )


@dataclass
class MemoryConfig:
    """Memory configuration"""
    backend: MemoryBackend = MemoryBackend.CHROMADB
    path: str = "./data/vector_db"
    collection_name: str = "ghostgoat_memory"
    embedding_model: str = "all-MiniLM-L6-v2"
    
    @classmethod
    def from_env(cls) -> 'MemoryConfig':
        """Load from environment variables"""
        backend_str = os.getenv("MEMORY_BACKEND", "chromadb").lower()
        try:
            backend = MemoryBackend(backend_str)
        except ValueError:
            backend = MemoryBackend.CHROMADB
        
        return cls(
            backend=backend,
            path=os.getenv("MEMORY_PATH", "./data/vector_db"),
            collection_name=os.getenv("MEMORY_COLLECTION", "ghostgoat_memory"),
            embedding_model=os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        )


@dataclass
class AgentConfig:
    """Agent configuration"""
    name: str = "ghostgoat_agent"
    max_concurrent_tasks: int = 5
    retry_attempts: int = 3
    timeout: int = 300
    enable_logging: bool = True
    log_level: str = "INFO"
    
    @classmethod
    def from_env(cls) -> 'AgentConfig':
        """Load from environment variables"""
        return cls(
            name=os.getenv("AGENT_NAME", "ghostgoat_agent"),
            max_concurrent_tasks=int(os.getenv("MAX_CONCURRENT_TASKS", "5")),
            retry_attempts=int(os.getenv("RETRY_ATTEMPTS", "3")),
            timeout=int(os.getenv("AGENT_TIMEOUT", "300")),
            enable_logging=os.getenv("ENABLE_LOGGING", "true").lower() == "true",
            log_level=os.getenv("LOG_LEVEL", "INFO")
        )


@dataclass
class NetworkConfig:
    """Network configuration"""
    ssh_key_path: str = "~/.ssh/id_ed25519"
    default_port: int = 8022
    connection_timeout: int = 10
    enable_agent_network: bool = True
    
    @classmethod
    def from_env(cls) -> 'NetworkConfig':
        """Load from environment variables"""
        return cls(
            ssh_key_path=os.getenv("SSH_KEY_PATH", "~/.ssh/id_ed25519"),
            default_port=int(os.getenv("AGENT_PORT", "8022")),
            connection_timeout=int(os.getenv("CONNECTION_TIMEOUT", "10")),
            enable_agent_network=os.getenv("ENABLE_AGENT_NETWORK", "true").lower() == "true"
        )


@dataclass
class UnifiedConfig:
    """Unified configuration for all systems"""
    llm: LLMConfig = field(default_factory=LLMConfig.from_env)
    memory: MemoryConfig = field(default_factory=MemoryConfig.from_env)
    agent: AgentConfig = field(default_factory=AgentConfig.from_env)
    network: NetworkConfig = field(default_factory=NetworkConfig.from_env)
    
    # System paths
    base_path: str = field(default_factory=lambda: str(Path.home() / "GhostGoat"))
    agents_path: str = field(default_factory=lambda: str(Path.home() / "AGENTS"))
    bots_path: str = field(default_factory=lambda: str(Path.home() / "BOTS"))
    adap_path: str = field(default_factory=lambda: str(Path.home() / "adap_lab"))
    
    # Feature flags
    enable_orchestrator: bool = True
    enable_knowledge_tank: bool = True
    enable_smart_moe: bool = True
    
    # API configuration
    api_port: int = 5000
    api_host: str = "0.0.0.0"
    enable_api: bool = True
    
    def __post_init__(self):
        """Post-initialization setup"""
        # Expand paths
        self.base_path = os.path.expanduser(self.base_path)
        self.agents_path = os.path.expanduser(self.agents_path)
        self.bots_path = os.path.expanduser(self.bots_path)
        self.adap_path = os.path.expanduser(self.adap_path)
        self.network.ssh_key_path = os.path.expanduser(self.network.ssh_key_path)
        self.memory.path = os.path.expanduser(self.memory.path)
    
    @classmethod
    def load(cls, config_path: Optional[str] = None) -> 'UnifiedConfig':
        """Load configuration from file or environment"""
        if config_path and os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config_data = json.load(f)
            return cls.from_dict(config_data)
        else:
            return cls.from_env()
    
    @classmethod
    def from_env(cls) -> 'UnifiedConfig':
        """Load from environment variables"""
        return cls(
            llm=LLMConfig.from_env(),
            memory=MemoryConfig.from_env(),
            agent=AgentConfig.from_env(),
            network=NetworkConfig.from_env(),
            base_path=os.getenv("GHOSTGOAT_BASE_PATH", str(Path.home() / "GhostGoat")),
            agents_path=os.getenv("AGENTS_PATH", str(Path.home() / "AGENTS")),
            bots_path=os.getenv("BOTS_PATH", str(Path.home() / "BOTS")),
            adap_path=os.getenv("ADAP_PATH", str(Path.home() / "adap_lab")),
            enable_orchestrator=os.getenv("ENABLE_ORCHESTRATOR", "true").lower() == "true",
            enable_knowledge_tank=os.getenv("ENABLE_KNOWLEDGE_TANK", "true").lower() == "true",
            enable_smart_moe=os.getenv("ENABLE_SMART_MOE", "true").lower() == "true",
            api_port=int(os.getenv("API_PORT", "5000")),
            api_host=os.getenv("API_HOST", "0.0.0.0"),
            enable_api=os.getenv("ENABLE_API", "true").lower() == "true"
        )
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UnifiedConfig':
        """Create from dictionary"""
        config = cls()
        
        if "llm" in data:
            llm_data = data["llm"]
            config.llm = LLMConfig(
                provider=LLMProvider(llm_data.get("provider", "openai")),
                model=llm_data.get("model", "gpt-4"),
                api_key=llm_data.get("api_key"),
                temperature=llm_data.get("temperature", 0.7),
                max_tokens=llm_data.get("max_tokens", 2000),
                timeout=llm_data.get("timeout", 30)
            )
        
        if "memory" in data:
            memory_data = data["memory"]
            config.memory = MemoryConfig(
                backend=MemoryBackend(memory_data.get("backend", "chromadb")),
                path=memory_data.get("path", "./data/vector_db"),
                collection_name=memory_data.get("collection_name", "ghostgoat_memory"),
                embedding_model=memory_data.get("embedding_model", "all-MiniLM-L6-v2")
            )
        
        if "agent" in data:
            agent_data = data["agent"]
            config.agent = AgentConfig(**agent_data)
        
        if "network" in data:
            network_data = data["network"]
            config.network = NetworkConfig(**network_data)
        
        # Update other fields
        for key, value in data.items():
            if key not in ["llm", "memory", "agent", "network"]:
                if hasattr(config, key):
                    setattr(config, key, value)
        
        return config
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "llm": asdict(self.llm),
            "memory": asdict(self.memory),
            "agent": asdict(self.agent),
            "network": asdict(self.network),
            "base_path": self.base_path,
            "agents_path": self.agents_path,
            "bots_path": self.bots_path,
            "adap_path": self.adap_path,
            "enable_orchestrator": self.enable_orchestrator,
            "enable_knowledge_tank": self.enable_knowledge_tank,
            "enable_smart_moe": self.enable_smart_moe,
            "api_port": self.api_port,
            "api_host": self.api_host,
            "enable_api": self.enable_api
        }
    
    def save(self, config_path: str):
        """Save configuration to file"""
        # Don't save API keys in config file
        config_dict = self.to_dict()
        if config_dict["llm"].get("api_key"):
            config_dict["llm"]["api_key"] = "***REDACTED***"
        
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, 'w') as f:
            json.dump(config_dict, f, indent=2)
        
        logger.info(f"Configuration saved to {config_path}")
    
    def validate(self) -> tuple[bool, list[str]]:
        """Validate configuration"""
        errors = []
        
        # Validate LLM config
        if self.llm.provider != LLMProvider.MOCK and not self.llm.api_key:
            errors.append("LLM API key required for non-mock provider")
        
        # Validate paths
        if not os.path.exists(self.base_path):
            errors.append(f"Base path does not exist: {self.base_path}")
        
        # Validate memory path
        memory_dir = os.path.dirname(self.memory.path)
        if memory_dir and not os.path.exists(memory_dir):
            try:
                os.makedirs(memory_dir, exist_ok=True)
            except Exception as e:
                errors.append(f"Cannot create memory directory: {e}")
        
        return len(errors) == 0, errors
    
    def get_system_config(self, system_name: str) -> Dict[str, Any]:
        """Get configuration for a specific system"""
        system_configs = {
            "ghostgoat_agent": {
                "llm": asdict(self.llm),
                "memory": asdict(self.memory),
                "agent": asdict(self.agent),
                "base_path": self.agents_path + "/ghostgoat_agent"
            },
            "nexusevo": {
                "llm": asdict(self.llm),
                "memory": asdict(self.memory),
                "base_path": self.agents_path + "/nexusevo"
            },
            "autonomous_agent": {
                "llm": asdict(self.llm),
                "memory": asdict(self.memory),
                "base_path": self.bots_path + "/autonomous_agent"
            },
            "orchestrator": {
                "llm": asdict(self.llm),
                "memory": asdict(self.memory),
                "network": asdict(self.network),
                "base_path": self.base_path
            }
        }
        
        return system_configs.get(system_name, {})


# Global configuration instance
_config: Optional[UnifiedConfig] = None


def get_config(config_path: Optional[str] = None) -> UnifiedConfig:
    """Get global configuration instance"""
    global _config
    
    if _config is None:
        default_path = os.path.expanduser("~/.ghostgoat/config.json")
        _config = UnifiedConfig.load(config_path or default_path)
        
        # Validate
        is_valid, errors = _config.validate()
        if not is_valid:
            logger.warning(f"Configuration validation errors: {errors}")
            logger.info("Using defaults, some features may not work")
    
    return _config


def set_config(config: UnifiedConfig):
    """Set global configuration"""
    global _config
    _config = config


# Convenience function
def init_config(config_path: Optional[str] = None) -> UnifiedConfig:
    """Initialize and return configuration"""
    return get_config(config_path)
