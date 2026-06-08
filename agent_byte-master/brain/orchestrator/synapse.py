from pathlib import Path
import json
from .identity import HolonIdentity

class Synapse:
    def __init__(self, holon_path: Path):
        self.path = holon_path / "AGENT.md"
        self.config = self._load_or_create()

    def _load_or_create(self) -> dict:
        if not self.path.exists():
            default = {
                "role": self.path.parent.name,
                "capabilities": ["code_edit", "test", "review", "refactor"],
                "goals": ["maintain_sovereignty", "resolve_tasks", "evolve_lattice"],
                "tools": ["read", "write", "git", "test", "propose_patch"],
                "parent": str(self.path.parent.parent) if self.path.parent.parent != Path.cwd() else None,
                "version": "2.0"
            }
            self._save(default)
            return default
        # Parse frontmatter (simple for now — extend with yaml later)
        content = self.path.read_text()
        if "```json" in content:
            json_part = content.split("```json")[1].split("```")[0]
            return json.loads(json_part)
        return {}

    def _save(self, data: dict):
        content = f"""# 🧬 Holon Synapse — {self.path.parent.name}

```json
{json.dumps(data, indent=2)}
```

*This file is both documentation and executable config. Edit capabilities/goals to change holon behavior.*
"""
        self.path.write_text(content)
