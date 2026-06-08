#!/usr/bin/env python3
"""
📊 DATASET BUILDER
Auto-expands training data from successful kernel execution logs.
"""

import os
import json
import re
from pathlib import Path
from typing import Dict, List, Any

PAYLOADS_DIR = "/home/popic/telegram-bot/PayloadsAllTheThings"
OUTPUT_JSONL = "/home/popic/telegram-bot/dataset/pentesting_train.jsonl"
OUTPUT_JSON = "/home/popic/telegram-bot/dataset/pentesting_train.json"
EXECUTION_LOG = "/home/popic/telegram-bot/logs/kernel_audit.jsonl"


def load_existing() -> set:
    """Load existing instructions to avoid duplicates."""
    seen = set()
    if os.path.exists(OUTPUT_JSONL):
        with open(OUTPUT_JSONL) as f:
            for line in f:
                try:
                    obj = json.loads(line)
                    seen.add(obj.get("instruction", ""))
                except:
                    pass
    return seen


def scan_payloads_directories() -> List[Dict[str, str]]:
    """Walk PayloadsAllTheThings for markdown files."""
    examples = []
    if not os.path.exists(PAYLOADS_DIR):
        return examples
    for root, _, files in os.walk(PAYLOADS_DIR):
        for fname in files:
            if fname.endswith(".md"):
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, errors="replace") as f:
                        content = f.read()
                    category = os.path.basename(root)
                    title = fname.replace(".md", "").replace("-", " ").title()
                    examples.append({
                        "path": fpath,
                        "category": category,
                        "title": title,
                        "content": content[:3000],
                    })
                except Exception:
                    pass
    return examples


def build_from_payloads(examples: List[Dict[str, str]], seen: set) -> List[Dict[str, Any]]:
    """Convert markdown examples to Alpaca format."""
    training = []
    for ex in examples:
        instruction = f"Explain {ex['title']} in {ex['category']}"
        if instruction in seen:
            continue
        output = ex["content"]
        training.append({
            "instruction": instruction,
            "input": "",
            "output": output,
            "category": ex["category"],
            "source": "PayloadsAllTheThings",
            "difficulty": "intermediate",
        })
        seen.add(instruction)
    return training


def build_from_logs(seen: set) -> List[Dict[str, Any]]:
    """Convert successful kernel executions to training examples."""
    training = []
    if not os.path.exists(EXECUTION_LOG):
        return training
    with open(EXECUTION_LOG) as f:
        for line in f:
            try:
                entry = json.loads(line)
                if not entry.get("success"):
                    continue
                cmd = entry.get("command", "")
                tool = cmd.split()[0] if cmd else ""
                instruction = f"How to use {tool} for pentesting?"
                if instruction in seen:
                    continue
                output = f"Command: {cmd}\nResult:\n{entry.get('stdout', '')[:1500]}"
                training.append({
                    "instruction": instruction,
                    "input": f"Target context from execution log",
                    "output": output,
                    "category": tool,
                    "source": "execution_log",
                    "difficulty": "advanced",
                })
                seen.add(instruction)
            except Exception:
                pass
    return training


def synthesize_scenarios(base_examples: List[Dict[str, Any]], seen: set) -> List[Dict[str, Any]]:
    """Generate synthetic quiz examples from existing data."""
    synthetic = []
    for ex in base_examples[:50]:
        instruction = f"Quiz: What technique does this describe?\n{ex['output'][:500]}"
        if instruction in seen:
            continue
        synthetic.append({
            "instruction": instruction,
            "input": "",
            "output": f"This describes: {ex['instruction']}",
            "category": ex.get("category", "general"),
            "source": "synthetic",
            "difficulty": "advanced",
        })
        seen.add(instruction)
    return synthetic


def save_dataset(examples: List[Dict[str, Any]]):
    """Append to JSONL and regenerate JSON."""
    with open(OUTPUT_JSONL, "a") as f:
        for ex in examples:
            f.write(json.dumps(ex) + "\n")

    # Rebuild JSON
    all_examples = []
    if os.path.exists(OUTPUT_JSONL):
        with open(OUTPUT_JSONL) as f:
            for line in f:
                try:
                    all_examples.append(json.loads(line))
                except:
                    pass
    with open(OUTPUT_JSON, "w") as f:
        json.dump(all_examples, f, indent=2)

    print(f"📊 Dataset updated: {len(all_examples)} total examples (+{len(examples)} new)")


def rebuild():
    """Full rebuild from all sources."""
    seen = load_existing()
    print(f"📊 Existing examples: {len(seen)}")

    # 1. From PayloadsAllTheThings
    payload_examples = scan_payloads_directories()
    from_payloads = build_from_payloads(payload_examples, seen)
    print(f"📁 From PATT: {len(from_payloads)}")

    # 2. From execution logs
    from_logs = build_from_logs(seen)
    print(f"📝 From logs: {len(from_logs)}")

    # 3. Synthetic
    synthetic = synthesize_scenarios(from_payloads + from_logs, seen)
    print(f"🧪 Synthetic: {len(synthetic)}")

    all_new = from_payloads + from_logs + synthetic
    if all_new:
        save_dataset(all_new)
    else:
        print("📊 No new examples to add")


if __name__ == "__main__":
    rebuild()

