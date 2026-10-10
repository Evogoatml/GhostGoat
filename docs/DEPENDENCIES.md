# Dependencies

`pyproject.toml` at the repo root is the single source of truth.

| Command | Installs |
|---|---|
| `pip install -e .` | core (API, LLM adapters, utilities) |
| `pip install -e ".[ml]"` | torch, faiss-cpu, chromadb, scikit-learn |
| `pip install -e ".[crypto]"` | cryptography, pycryptodome, liboqs-python |
| `pip install -e ".[agents]"` | crewai, langgraph |
| `pip install -e ".[pentest]"` | textual, rich, claude-agent-sdk |
| `pip install -e ".[dev]"` | pytest, black, mypy, ruff |
| `pip install -e ".[full]"` | all of the above |

Extras can be combined: `pip install -e ".[ml,agents]"`.

## Migration from the old requirements files

| Removed file | Replacement |
|---|---|
| `requirements-core.txt` | core dependencies |
| `requirements_brain.txt` | `ml` extra |
| `agent_byte-master/requirements.txt` | `ml` + `dev` extras (uses `faiss-cpu`; for CUDA, install `faiss-gpu-cu12` manually instead) |
| `agent_byte-master/utils/congo/FQES/requirements.txt` | `agents` + `crypto` extras |
| `requirements.txt` | now just `-e .[full]` |

Standalone sub-projects (e.g. PentestGPT, ragflow, ACS_SYSTEM/asi/evoagent) keep their own `pyproject.toml`.
