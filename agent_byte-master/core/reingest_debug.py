#!/usr/bin/env python3
"""Debug version of reingest to find the root cause."""
from __future__ import annotations
import json, sys, importlib.util, traceback
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
print("Fit complete")

# Test first 3 files with detailed debugging
for i, f in enumerate(PROJECTS.glob("*.workflow.json")):
    if i >= 3:
        break
    print(f"\n--- Processing {f.name} ---")
    try:
        wf = json.loads(f.read_text(encoding="utf-8"))
        pn = wf.get("project_name", f.stem)
        ptype = wf.get("project_type", "")
        print(f"  pn type={type(pn).__name__}, value={repr(str(pn)[:60])}")
        print(f"  pt type={type(ptype).__name__}, value={repr(str(ptype)[:60])}")
        
        nodes = wf.get("nodes", [])
        print(f"  nodes type={type(nodes).__name__}, len={len(nodes) if hasattr(nodes, '__len__') else 'N/A'}")
        
        node_labels = []
        for j, n in enumerate((nodes or [])[:5]):
            print(f"    node[{j}] type={type(n).__name__}")
            label = n.get("label", "") if hasattr(n, "get") else str(n)
            node_labels.append(str(label))
        
        rich_text = f"{pn} {ptype} {' '.join(node_labels)}"
        print(f"  rich_text type={type(rich_text).__name__}")
        print(f"  rich_text={repr(rich_text[:80])}")
        
        vec = embedder.embed(rich_text)
        print(f"  SUCCESS, vec len={len(vec)}")
    except Exception as e:
        print(f"  ERROR: {type(e).__name__}: {e}")
        traceback.print_exc()

