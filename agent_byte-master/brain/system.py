#!/usr/bin/env python3
"""
High-level system façade for GhostGoat.
Provides chat API with LLM and knowledge retrieval.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import List, Dict, Any, Optional

# Import intelligence components
try:
    from core.intelligence.ability_manager import AbilityManager
    from core.intelligence.knowledge_frame_manager import KnowledgeFrameManager
    from core.intelligence.pattern_recognizer import PatternRecognizer
    from core.intelligence.analogical_transferer import AnalogicalTransferer
    from core.intelligence.self_directed_learner import SelfDirectedLearner
    INTELLIGENCE_AVAILABLE = True
except ImportError:
    INTELLIGENCE_AVAILABLE = False
    # Define stub classes for when intelligence components aren't available
    class AbilityManager:
        def __init__(self, *args, **kwargs): pass
        def extract_relevant_abilities(self, *args, **kwargs): return []
    class KnowledgeFrameManager:
        def __init__(self, *args, **kwargs): pass
        def get_relevant_frames(self, *args, **kwargs): return []
    class PatternRecognizer:
        def __init__(self, *args, **kwargs): pass
        def recognize_patterns(self, *args, **kwargs): return []
    class AnalogicalTransferer:
        def __init__(self, *args, **kwargs): pass
        def transfer_abilities(self, *args, **kwargs): return []
    class SelfDirectedLearner:
        def __init__(self, *args, **kwargs): pass
        def learn_from_experience(self, *args, **kwargs): pass

# ── Workflow Brain integration ────────────────────────────────────────────────
BRAIN_AVAILABLE = False
_brain = None

def _load_brain():
    """Lazy-load WorkflowSkillManager via importlib (avoids circular deps)."""
    global BRAIN_AVAILABLE, _brain
    if _brain is not None:
        return _brain
    try:
        import importlib.util, sys
        path = Path(__file__).resolve().parent.parent / "core" / "brain_modules" / "workflow_skill_manager.py"
        spec = importlib.util.spec_from_file_location("_gg_brain", path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules["_gg_brain"] = mod
        spec.loader.exec_module(mod)
        _brain = mod.WorkflowSkillManager()
        BRAIN_AVAILABLE = True
        return _brain
    except Exception as e:
        logging.getLogger("ghostgoat_system").debug("Brain load failed: %s", e)
        BRAIN_AVAILABLE = False
        return None


class SystemConfig:
    """Configuration for the system."""
    llm_provider: str = "ollama"
    llm_model: str = "llama3"
    ollama_base_url: str = "http://localhost:11434"
    openai_api_key: str = ""
    openai_api_base: str = ""
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    rag_top_k: int = 3
    log_level: str = "INFO"


def load_config() -> SystemConfig:
    """Load configuration from environment."""
    config = SystemConfig()
    config.llm_provider = os.environ.get("LLM_PROVIDER", "ollama")
    config.llm_model = os.environ.get("LLM_MODEL", "llama3")
    config.ollama_base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    config.openai_api_key = os.environ.get("OPENAI_API_KEY", "")
    config.openai_api_base = os.environ.get("OPENAI_API_BASE", "")
    config.deepseek_api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    config.deepseek_base_url = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    config.log_level = os.environ.get("LOG_LEVEL", "INFO")
    return config


def _setup_logging(level: str = "INFO") -> logging.Logger:
    """Setup logging."""
    logger = logging.getLogger("ghostgoat_system")
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(getattr(logging, level))
    return logger


async def _llm_call(
    prompt: str,
    system_prompt: str = "",
    config: Optional[SystemConfig] = None
) -> str:
    """Call LLM provider."""
    config = config or load_config()
    
    try:
        if config.llm_provider == "ollama":
            return await _call_ollama(config, prompt, system_prompt)
        elif config.llm_provider == "openai":
            return await _call_openai(config, prompt, system_prompt)
        elif config.llm_provider == "deepseek":
            return await _call_deepseek(config, prompt, system_prompt)
        else:
            return f"[Error] Unknown provider: {config.llm_provider}"
    except Exception as e:
        return f"[Error] {e}"


async def _call_ollama(config: SystemConfig, prompt: str, system_prompt: str) -> str:
    """Query local Ollama server."""
    import json
    
    url = f"{config.ollama_base_url}/api/generate"
    payload = {
        "model": config.llm_model,
        "prompt": f"{system_prompt}\n\n{prompt}" if system_prompt else prompt,
        "stream": False
    }
    
    try:
        import urllib.request
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode())
            return result.get("response", "[Error] No response")
    except Exception as e:
        return f"[Error] Ollama: {e}"


async def _call_openai(config: SystemConfig, prompt: str, system_prompt: str) -> str:
    """Query OpenAI API."""
    try:
        import openai
        client = openai.AsyncOpenAI(
            api_key=config.openai_api_key,
            base_url=config.openai_api_base or None
        )
        response = await client.chat.completions.create(
            model=config.llm_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content or "[Error] No content"
    except ImportError:
        return "[Error] openai library not installed"
    except Exception as e:
        return f"[Error] OpenAI: {e}"


async def _call_deepseek(config: SystemConfig, prompt: str, system_prompt: str) -> str:
    """Query DeepSeek API."""
    try:
        import openai
        client = openai.AsyncOpenAI(
            api_key=config.deepseek_api_key,
            base_url=config.deepseek_base_url
        )
        response = await client.chat.completions.create(
            model=config.llm_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content or "[Error] No content"
    except ImportError:
        return "[Error] openai library not installed"
    except Exception as e:
        return f"[Error] DeepSeek: {e}"


def _rag_query(query: str, top_k: int = 3) -> List[tuple[str, float]]:
    """Query workflow brain for semantic matches."""
    brain = _load_brain()
    if brain is None:
        return []
    try:
        candidates = brain.search(query, top_k=top_k, use_memory=True)
        results = []
        for c in candidates:
            label = c.get("label", c.get("project_name", "unknown"))
            content = c.get("content", "")[:500]
            score = c.get("similarity", c.get("boosted_score", 0.0))
            text = f"[{label}] {content}"
            results.append((text, score))
        return results
    except Exception as e:
        logging.getLogger("ghostgoat_system").warning("Brain RAG query failed: %s", e)
        return []


class GhostGoatSystem:
    """Main system with chat API."""
    
    def __init__(self, config: Optional[SystemConfig] = None):
        self.config = config or load_config()
        self.logger = _setup_logging(self.config.log_level)
        
# Initialize intelligence components if available and enabled
        if INTELLIGENCE_AVAILABLE and getattr(self.config, 'enable_intelligence', True):
            try:
                import sys
                sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / 'config'))
                from unified_config import get_config
                unified_config = get_config()
                self.intelligence_config = unified_config.intelligence
                self.ability_manager = AbilityManager(self.intelligence_config)
                self.knowledge_frame_manager = KnowledgeFrameManager(self.intelligence_config)
                self.pattern_recognizer = PatternRecognizer(self.intelligence_config)
                self.analogical_transferer = AnalogicalTransferer(self.intelligence_config)
                self.self_directed_learner = SelfDirectedLearner(self.intelligence_config)
                self.logger.info("Intelligence components initialized")
            except Exception as e:
                self.logger.warning("Intelligence components failed to load: %s", e)
        else:
            # Initialize stub components
            self.ability_manager = AbilityManager()
            self.knowledge_frame_manager = KnowledgeFrameManager()
            self.pattern_recognizer = PatternRecognizer()
            self.analogical_transferer = AnalogicalTransferer()
            self.self_directed_learner = SelfDirectedLearner()
            self.logger.info("Intelligence components running in stub mode")
    
    async def chat(
        self,
        *,
        message: str,
        user_id: int,
        username: str,
        history: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Process a user request."""
        # ── Semantic workflow brain retrieval ────────────────────────────────
        rag_context = ""
        few_shot_prompt = ""
        try:
            brain = _load_brain()
            if brain is not None:
                # Route to domain
                domain = brain.route(message)
                self.logger.info("Domain routed: %s", domain)

                # Semantic search
                candidates = brain.search(message, top_k=self.config.rag_top_k, use_memory=True)
                if candidates:
                    # Build few-shot prompt from top candidates
                    wids = []
                    for c in candidates[:3]:
                        wid = c.get("workflow_id") or c.get("id")
                        if c.get("type") == "FILE" and c.get("metadata", {}).get("workflow_id"):
                            wid = c["metadata"]["workflow_id"]
                        if wid:
                            wids.append(wid)
                    few_shot_prompt = brain.few_shot(
                        instruction=message,
                        workflow_ids=wids,
                        domain=domain,
                        shots=3,
                    )
                    # Build RAG context from candidate labels/content
                    rag_parts = []
                    for c in candidates:
                        label = c.get("label", c.get("project_name", "unknown"))
                        content = c.get("content", "")[:400]
                        if content:
                            rag_parts.append(f"[{label}]: {content}")
                    rag_context = "\n---\n".join(rag_parts)
        except Exception as e:
            self.logger.warning("RAG query failed: %s", e)
        
        # Build intelligence context if intelligence is enabled
        intelligence_context = ""
        if INTELLIGENCE_AVAILABLE and getattr(self.config, 'enable_intelligence', True):
            try:
                # Extract relevant abilities, frames, and patterns
                abilities = self.ability_manager.extract_relevant_abilities(message)
                frames = self.knowledge_frame_manager.get_relevant_frames(message)
                patterns = self.pattern_recognizer.recognize_patterns(message)
                transferred_abilities = self.analogical_transferer.transfer_abilities(
                    abilities, frames, patterns, message
                )
                
                # Build intelligence context string
                intelligence_parts = []
                if abilities:
                    intelligence_parts.append(f"[Relevant Abilities: {len(abilities)}]")
                if frames:
                    intelligence_parts.append(f"[Knowledge Frames: {len(frames)}]")
                if patterns:
                    intelligence_parts.append(f"[Recognized Patterns: {len(patterns)}]")
                if transferred_abilities:
                    intelligence_parts.append(f"[Transferred Abilities: {len(transferred_abilities)}]")
                
                if intelligence_parts:
                    intelligence_context = "\n".join(intelligence_parts)
                    
                # Learn from this interaction for future improvement
                # (This would typically be done after seeing the result, but we initiate the process)
                # In a full implementation, we'd store the interaction and learn after seeing outcome
            except Exception as e:
                self.logger.warning(f"Intelligence processing failed: {e}")
                intelligence_context = ""
        
        # Build the enriched prompt with all available context
        context_parts = []
        if few_shot_prompt:
            context_parts.append(few_shot_prompt)
        elif rag_context:
            context_parts.append(f"[Background Knowledge]\n{rag_context}")
        if intelligence_context:
            context_parts.append(intelligence_context)
        
        context_str = "\n\n".join(context_parts)
        enriched = f"{context_str}\n\nUser: {message}" if context_str else message
        
        if system_prompt is None:
            system_prompt = (
                f"You are GhostGoat, an autonomous AI assistant for {username}. "
                "Answer concisely, safely."
            )
        
        answer = await _llm_call(enriched, system_prompt, self.config)
        
        # Learn from the interaction (in a full implementation, we'd wait for the result)
        if INTELLIGENCE_AVAILABLE and getattr(self.config, 'enable_intelligence', True):
            try:
                # Initiate learning process - in practice, this would be deferred
                # until we know if the interaction was successful
                # self.self_directed_learner.learn_from_experience(
                #     message, answer, user_id, username, history
                # )
                pass  # Placeholder for actual learning implementation
            except Exception as e:
                self.logger.warning(f"Self-directed learning failed: {e}")
        
        return {"text": answer}


system = GhostGoatSystem()


def main():
    """CLI entry point."""
    import sys
    import asyncio
    
    config = load_config()
    client = GhostGoatSystem(config)
    
    message = " ".join(sys.argv[1:]) or "Hello"
    
    result = asyncio.run(client.chat(
        message=message,
        user_id=0,
        username="cli",
        history=[]
    ))
    print(result.get("text", result))


if __name__ == "__main__":
    main()


