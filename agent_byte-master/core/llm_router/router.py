"""GhostGoat LLM Router — Smart model selection by task profile."""
import json, logging, subprocess, time
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ModelProfile:
    name: str
    provider: str
    capabilities: List[str]
    cost_per_1k: float
    latency_ms_1k: float
    max_tokens: int
    context_window: int
    preferred_for: List[str]
    local: bool = True

DEFAULT_PROFILES = {
    "llama3.2": ModelProfile("llama3.2", "ollama", ["chat", "reasoning", "code", "tools"], 0.0, 800, 4096, 128000,
                             ["general", "fast", "local", "tools"], True),
    "mistral-small": ModelProfile("mistral-small", "ollama", ["chat", "reasoning", "long_context"], 0.0, 1200, 32768,
                                  32768, ["long_context", "local", "synthesis"], True),
    "nomic-embed-text": ModelProfile("nomic-embed-text", "ollama", ["embedding"], 0.0, 300, 0, 0,
                                     ["embedding", "local"], True),
    "llava": ModelProfile("llava", "ollama", ["vision", "image_understanding", "chat"], 0.0, 2000, 4096, 4096,
                          ["vision", "local"], True),
    "gpt-4o": ModelProfile("gpt-4o", "openai", ["chat", "reasoning", "code", "vision", "tools", "json_mode"], 0.005,
                           400, 4096, 128000, ["complex", "reliable", "vision"], False),
    "claude-3-5-sonnet": ModelProfile("claude-3-5-sonnet", "anthropic",
                                      ["chat", "reasoning", "code", "long_context", "writing"], 0.003, 600, 8192,
                                      200000, ["complex", "writing", "analysis"], False),
    "deepseek-coder": ModelProfile("deepseek-coder", "ollama", ["code", "chat", "reasoning"], 0.0, 1500, 4096, 16384,
                                   ["code", "local"], True),
}

class LLMRouter:
    def __init__(self, profiles: Optional[Dict[str, ModelProfile]] = None, budget_usd: Optional[float] = None):
        self.profiles = profiles or dict(DEFAULT_PROFILES)
        self.budget = budget_usd
        self.history: List[Dict[str, Any]] = []

    def route(self, task_type: str = "chat", complexity: str = "medium", latency_priority: str = "normal",
              requires: Optional[List[str]] = None) -> str:
        requires = requires or []
        candidates = [p for p in self.profiles.values() if all(c in p.capabilities for c in requires)]
        if not candidates:
            logger.warning("No model supports %s, falling back to llama3.2", requires)
            return "llama3.2"

        scores = []
        for p in candidates:
            score = 0.0
            score += len([c for c in requires if c in p.capabilities]) * 10
            if complexity == "high" and p.max_tokens >= 8192:
                score += 5
            if complexity == "low" and p.latency_ms_1k < 1000:
                score += 3
            if latency_priority == "fast":
                score += max(0, 2000 - p.latency_ms_1k) / 200
            elif latency_priority == "quality":
                score += min(5, p.context_window / 50000)
            if self.budget is not None and p.cost_per_1k == 0.0:
                score += 3
            scores.append((score, p))

        scores.sort(key=lambda x: (-x[0], x[1].latency_ms_1k))
        winner = scores[0][1]
        self.history.append({"task": task_type, "complexity": complexity, "winner": winner.name, "timestamp": time.time()})
        logger.info("Routed to %s (score=%.1f)", winner.name, scores[0][0])
        return winner.name

    def run_prompt(self, prompt: str, model: Optional[str] = None, system: Optional[str] = None,
                   timeout: int = 60) -> str:
        model = model or self.route()
        full = f"System: {system}\nUser: {prompt}\nAI:" if system else f"User: {prompt}\nAI:"
        try:
            start = time.time()
            r = subprocess.run(["ollama", "run", model, full], capture_output=True, text=True, timeout=timeout)
            latency = (time.time() - start) * 1000
            self.history.append({"model": model, "latency_ms": latency, "success": r.returncode == 0, "timestamp": time.time()})
            if r.returncode != 0:
                logger.error("Model %s error: %s", model, r.stderr[:200])
                return f"[Error: {r.stderr[:200]}]"
            return r.stdout.strip()
        except Exception as e:
            logger.error("Prompt execution failed: %s", e)
            return f"[Error: {e}]"

    def stats(self) -> Dict[str, Any]:
        if not self.history:
            return {"calls": 0}
        return {"calls": len(self.history),
                "avg_latency_ms": sum(h.get("latency_ms", 0) for h in self.history) / len(self.history),
                "model_distribution": {m: sum(1 for h in self.history if h.get("winner") == m)
                                       for m in set(h.get("winner") for h in self.history)}}

