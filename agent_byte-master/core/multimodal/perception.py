"""GhostGoat Multi-Modal Perception — Vision, Audio, Image."""
import base64, json, logging, subprocess, tempfile, os, time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

class VisionAnalyzer:
    def __init__(self, model: str = "llava"):
        self.model = model

    def analyze(self, image_path: str, prompt: str = "Describe this image in detail.") -> str:
        try:
            if not Path(image_path).exists():
                return f"[Error: image not found {image_path}]"
            r = subprocess.run(
                ["ollama", "run", self.model, f"[img:{image_path}] {prompt}"],
                capture_output=True, text=True, timeout=60
            )
            return r.stdout.strip()
        except Exception as e:
            logger.error("Vision analyze failed: %s", e)
            return f"[Vision error: {e}]"

    def describe_screenshots(self, paths: List[str]) -> Dict[str, str]:
        return {p: self.analyze(p, "What is shown in this screenshot? Is there any text or UI elements?") for p in paths}

class AudioTranscriber:
    def __init__(self, model: str = "whisper"):
        self.model = model

    def transcribe(self, audio_path: str, language: str = "auto") -> str:
        try:
            if not Path(audio_path).exists():
                return f"[Error: audio not found {audio_path}]"
            r = subprocess.run(
                ["ollama", "run", self.model, f"Transcribe this audio. Language: {language}. File: {audio_path}"],
                capture_output=True, text=True, timeout=120
            )
            return r.stdout.strip()
        except Exception as e:
            logger.error("Audio transcribe failed: %s", e)
            return f"[Audio error: {e}]"

class ImageGenerator:
    def __init__(self, engine: str = "placeholder"):
        self.engine = engine

    def generate(self, prompt: str, width: int = 512, height: int = 512) -> str:
        if self.engine == "placeholder":
            out = Path.home() / ".ghostgoat" / "generated" / f"img_{hash(prompt) & 0xFFFFFFFF}.png"
            out.parent.mkdir(parents=True, exist_ok=True)
            logger.info("Image generation placeholder: %s -> %s", prompt[:40], out)
            return str(out)
        try:
            out = Path.home() / ".ghostgoat" / "generated" / f"img_{int(time.time())}.png"
            out.parent.mkdir(parents=True, exist_ok=True)
            return str(out)
        except Exception as e:
            return f"[Image error: {e}]"

