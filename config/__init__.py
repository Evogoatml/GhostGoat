"""
GhostGoat configuration — thin wrapper so `from config import config` works.
"""

import os


class _Config:
    """Simple config object that agents can import."""

    @property
    def log_level(self) -> str:
        return os.getenv("LOG_LEVEL", "INFO")

    @property
    def log_file(self) -> str:
        return os.getenv("LOG_FILE", "logs/ghostgoat.log")

    @property
    def llm_provider(self) -> str:
        return os.getenv("LLM_PROVIDER", "mock")

    @property
    def base_path(self) -> str:
        return os.getenv("GHOSTGOAT_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


config = _Config()
