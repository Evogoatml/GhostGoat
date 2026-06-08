from pydantic import BaseModel, Field
from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

class NexusConfig(BaseModel):
    root: Path = Field(default=Path("."))
    llm_model: str = os.getenv("NEXUS_LLM_MODEL", "anthropic/claude-3-7-sonnet")
    llm_temperature: float = 0.3
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    pulse_interval: int = 30
    max_holons: int = 500

config = NexusConfig()
