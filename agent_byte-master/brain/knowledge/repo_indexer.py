"""Index an external source repository (e.g. ``~/training``) into the KnowledgeTank.

The repo is *knowledge, not code*: files are read, chunked and ingested with the
category ``training`` so research goals, ``/api/knowledge/search`` and casual
chat all retrieve from them.

Incremental: a per-root manifest (file -> mtime/size) lives next to the tank's
``tank.jsonl``, so restarts only re-read changed files. Changed files are
replaced via ``delete_by_source``; files deleted from the repo have their
entries pruned on the next run. Notebooks contribute their markdown + code cell
sources only (outputs stripped); binaries and oversized files are skipped.

Entry ``source`` is ``"<root-name>/<relpath>"`` — two different roots with the
same basename and same subpaths would share a source key (index one root per
name).
"""

import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

ALLOWED_EXT = {
    ".py", ".md", ".txt", ".rst", ".ipynb", ".js", ".ts", ".cs", ".m",
    ".sh", ".yaml", ".yml", ".toml", ".cfg", ".ini",
}
SKIP_DIRS = {
    ".git", "__pycache__", ".ipynb_checkpoints", "node_modules",
    ".venv", "venv", ".tox", ".mypy_cache", ".pytest_cache",
}
MAX_FILE_BYTES = 5 * 1024 * 1024
CHUNK_CHARS = 6000
MAX_CHUNKS_PER_FILE = 60


def _manifest_path(tank: Any, root: Path) -> Path:
    key = hashlib.sha1(str(root).encode()).hexdigest()[:12]
    return Path(tank.storage_path) / f"manifest_repo_{key}.json"


def _load_manifest(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("files"), dict):
            return data
    except (OSError, ValueError):
        pass
    return {"files": {}}


def _read_text(path: Path) -> Optional[str]:
    try:
        with open(path, "rb") as f:
            head = f.read(4096)
        if b"\x00" in head:
            return None
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _notebook_cells(text: str) -> str:
    """Markdown + code cell sources of a notebook; outputs are never read."""
    try:
        nb = json.loads(text)
    except ValueError:
        return ""
    parts: List[str] = []
    for cell in nb.get("cells", []):
        if not isinstance(cell, dict) or cell.get("cell_type") not in ("markdown", "code"):
            continue
        src = cell.get("source") or []
        parts.append(src if isinstance(src, str) else "".join(src))
    return "\n\n".join(p for p in parts if p.strip())


def _chunks(text: str) -> List[str]:
    out: List[str] = []
    pos = 0
    while pos < len(text) and len(out) < MAX_CHUNKS_PER_FILE:
        end = min(pos + CHUNK_CHARS, len(text))
        if end < len(text):
            cut = text.rfind("\n\n", pos + CHUNK_CHARS // 2, end)
            if cut != -1:
                end = cut
        piece = text[pos:end].strip()
        if piece:
            out.append(piece)
        pos = end
    return out


def _tags_for(root_name: str, rel: str) -> List[str]:
    parts = list(Path(rel).with_suffix("").parts)
    tags = [root_name.lower()] + [p.lower()[:40] for p in parts]
    return tags[:9]


def index_repo(tank: Any, root: Path) -> Dict[str, Any]:
    """(Re)index ``root`` into ``tank``; returns counts for logging/tests."""
    root = Path(root).expanduser().resolve()
    manifest_file = _manifest_path(tank, root)
    files = _load_manifest(manifest_file).get("files", {})
    seen = set()
    stats = {"scanned": 0, "indexed": 0, "unchanged": 0,
             "removed": 0, "skipped": 0, "chunks": 0}

    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel_path = path.relative_to(root)
        if any(part in SKIP_DIRS or part.startswith(".") for part in rel_path.parts[:-1]):
            continue
        if path.suffix.lower() not in ALLOWED_EXT:
            continue
        try:
            stat = path.stat()
        except OSError:
            continue
        rel = rel_path.as_posix()
        seen.add(rel)
        source = f"{root.name}/{rel}"
        if stat.st_size > MAX_FILE_BYTES:
            stats["skipped"] += 1
            if files.pop(rel, None) is not None:
                tank.delete_by_source(source)
                stats["removed"] += 1
            continue
        stats["scanned"] += 1
        record = files.get(rel)
        if record and record.get("mtime") == int(stat.st_mtime) and record.get("size") == stat.st_size:
            stats["unchanged"] += 1
            continue

        text = _read_text(path)
        if text and path.suffix.lower() == ".ipynb":
            text = _notebook_cells(text)
        chunks = _chunks(text) if text else []
        if not chunks:
            if files.pop(rel, None) is not None:
                tank.delete_by_source(source)
                stats["removed"] += 1
            stats["skipped"] += 1
            continue

        tank.delete_by_source(source)  # replace the previous version
        tags = _tags_for(root.name, rel)
        for index, piece in enumerate(chunks):
            part_note = f" (part {index + 1}/{len(chunks)})" if len(chunks) > 1 else ""
            tank.ingest(
                content=f"[{source}]{part_note}\n{piece}",
                category="training",
                tags=tags,
                source=source,
                metadata={"root": str(root), "part": index + 1, "parts": len(chunks)},
            )
        files[rel] = {"mtime": int(stat.st_mtime), "size": stat.st_size, "chunks": len(chunks)}
        stats["indexed"] += 1
        stats["chunks"] += len(chunks)

    for rel in list(files):
        if rel not in seen:
            if tank.delete_by_source(f"{root.name}/{rel}"):
                stats["removed"] += 1
            files.pop(rel)

    manifest_file.parent.mkdir(parents=True, exist_ok=True)
    manifest_file.write_text(json.dumps({"root": str(root), "files": files}), encoding="utf-8")
    tank.persist()
    logger.info("Indexed repo %s: %s", root, stats)
    return stats


def index_repo_async(tank: Any, root: Path) -> None:
    """Fire-and-forget wrapper for background startup indexing."""
    try:
        index_repo(tank, root)
    except Exception:
        logger.exception("Background repo indexing failed for %s", root)
