#!/usr/bin/env python3
"""Re-ingest GraphRAG with semantic TF-IDF embeddings for better search quality."""
from __future__ import annotations
import json, sys, importlib.util
from pathlib import Path

PROJECTS = Path("/home/popic/GhostGoat/agent_byte-master/brain/knowledge/processed/workflows/projects")
STORAGE = Path("/home/popic/GhostGoat/agent_byte-master/brain/knowledge/graphrag")

def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

# Load embedder
emb_mod = load_module(Path("/home/popic/GhostGoat/agent_byte-master/core/workflow_embedder.py"), "_emb")
embedder = emb_mod.WorkflowEmbedder(dim=128)

# Build corpus
texts = []
for f in PROJECTS.glob("*.workflow.json"):
    try:
        wf = json.loads(f.read_text(encoding="utf-8"))
        texts.append(str(wf.get("project_name", "")))
        texts.append(str(wf.get("project_type", "")))
        for node in wf.get("nodes", []):
            c = node.get("content", {})
            if c.get("type") == "text":
                raw = c.get("content", "")
                if isinstance(raw, list):
                    raw = " ".join(str(x) for x in raw)
                texts.append(str(raw)[:2000])
    except Exception:
        pass

print(f"Fitting embedder on {len(texts)} text fragments...")
embedder.fit_on_corpus(texts)

# Load GraphRAGEngine
grage_mod = load_module(Path("/home/popic/GhostGoat/agent_byte-master/core/graphrag/engine.py"), "_grage")

# Wipe old storage and rebuild
if STORAGE.exists():
    for f in STORAGE.glob("*"):
        try:
            if f.is_file():
                f.unlink()
        except Exception:
            pass

engine = grage_mod.GraphRAGEngine(storage_path=str(STORAGE), embedding_dim=128)

# Ingest all workflows as PROJECT nodes
project_count = 0
for f in PROJECTS.glob("*.workflow.json"):
    try:
        wf = json.loads(f.read_text(encoding="utf-8"))
        wid = wf.get("workflow_id", f.stem)
        pn = wf.get("project_name", f.stem)
        ptype = wf.get("project_type", "")

        # Build rich text for embedding: name + type + first few node labels
        node_labels = [str(n.get("label", "")) for n in wf.get("nodes", [])[:5]]
        rich_text = f"{pn} {ptype} {' '.join(node_labels)}"
        vec = embedder.embed(rich_text)

        engine.add_node(
            label=pn,
            content=pn,
            node_type="PROJECT",
            vector=vec,
            metadata={
                "type": "PROJECT",
                "project_type": ptype,
                "node_count": len(wf.get("nodes", [])),
                "workflow_id": wid,
            },
        )
        project_count += 1
    except Exception as e:
        print(f"Skip {f.name}: {e}")

# Auto-link similar projects
for nid, node in list(engine.nodes.items()):
    engine._auto_link(node)

engine._persist()
print(f"Re-ingested {project_count} projects with semantic embeddings")
print(f"Total nodes: {len(engine.nodes)}, edges: {len(engine.edges)}")

# Quick quality check
print("\n--- Quality check ---")
for q in ["neural network", "decision tree", "steganography", "AES encryption"]:
    qvec = embedder.embed(q)
    results = engine.search(qvec, top_k=3)
    labels = [r.get("label", r.get("project_name", "unknown")) for r in results[:3]]
    print(f"'{q}' -> {', '.join(labels)}")





