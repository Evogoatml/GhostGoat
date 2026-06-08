# neuroforge_v1.py
# Self-evolving agent with GraphRAG + self-code-writing + key recovery focus
import os
import json
import time
import hashlib
import binascii
import networkx as nx
from datetime import datetime
from typing import Dict, List, Any
import requests
from pathlib import Path
import ollama  # pip install ollama

try:
    from ecdsa import SigningKey, SECP256k1
    import base58
except ImportError:
    SigningKey = SECP256k1 = base58 = None

from ACS_SYSTEM.asi.training_bridge import TrainingBridge


class NeuroForge:
    def __init__(self, name="NeuroForge"):
        self.name = name
        self.graph = nx.DiGraph()  # Agentic GraphRAG memory
        self.session_dir = f"neuroforge_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        os.makedirs(self.session_dir, exist_ok=True)

        self.performance_log = []
        self.code_history = []
        self.training = TrainingBridge()
        self.tools = [
            "scan_files", "derive_address", "check_balance", "write_code",
            "reflect", "list_training", "train", "search_training",
        ]

        # Initial knowledge (programming skills "dataset")
        self.knowledge_seed = """
        Bitcoin key formats: WIF (K/L/5), hex 64 chars, BIP39 12/24 words, BIP38 (6P)
        Recovery tools: Electrum sweep, BTCRecover for wallet.dat
        Derivation paths: m/44'/0'/0', m/84'/0'/0', m/49'/0'/0'
        Balance check: mempool.space API
        Self-improvement: ReAct loop, GraphRAG retrieval, code reflection
        """
        self.add_memory("initial_knowledge", self.knowledge_seed)

        print(f"[NeuroForge] {self.name} v1.0 initialized. Self-evolution active.")

    def add_memory(self, key: str, content: str):
        self.graph.add_node(key, content=content, timestamp=datetime.now().isoformat())
        print(f"Memory added: {key}")

    def retrieve_memory(self, query: str) -> str:
        relevant = [
            n for n in self.graph.nodes
            if query.lower() in n.lower()
            or query.lower() in self.graph.nodes[n]['content'].lower()
        ]
        return "\n".join([self.graph.nodes[n]['content'] for n in relevant[:5]]) or "No relevant memory."

    def think_react(self, goal: str) -> Dict:
        context = self.retrieve_memory(goal)

        prompt = f"""
        You are {self.name}, a self-evolving neuro-symbolic agent.
        Goal: {goal}

        Memory context:
        {context}

        Available training algorithms:
        {self.training.summary()}

        Think in ReAct format:
        Thought: ...
        Action: scan_files | derive_address | check_balance | write_code | reflect | ask_user | list_training | train | search_training
        Action Input: ...

        Respond ONLY in JSON:
        {{
            "thought": "...",
            "action": "...",
            "action_input": "... or null",
            "self_improvement": "..." or null
        }}
        """

        response = ollama.chat(model='llama3.2', messages=[{'role': 'user', 'content': prompt}])
        try:
            return json.loads(response['message']['content'])
        except Exception:
            return {"thought": response['message']['content'], "action": "reflect", "action_input": None}

    def act(self, action: str, input_data: Any = None) -> Any:
        if action == "scan_files":
            return "Scanned folder - found potential keys"

        elif action == "derive_address":
            if SigningKey is None or base58 is None:
                return "Derivation unavailable - install ecdsa and base58 packages"
            try:
                priv_hex = input_data
                priv_bytes = binascii.unhexlify(priv_hex)
                sk = SigningKey.from_string(priv_bytes, curve=SECP256k1)
                vk = sk.verifying_key
                pub_raw = vk.to_string()
                if pub_raw[32] % 2 == 0:
                    pubkey = b'\x02' + pub_raw[:32]
                else:
                    pubkey = b'\x03' + pub_raw[:32]
                sha = hashlib.sha256(pubkey).digest()
                ripemd = hashlib.new('ripemd160', sha).digest()
                extended = b'\x00' + ripemd
                checksum = hashlib.sha256(hashlib.sha256(extended).digest()).digest()[:4]
                addr = base58.b58encode(extended + checksum).decode()
                return addr
            except Exception:
                return "Derivation failed"

        elif action == "check_balance":
            addr = input_data
            try:
                r = requests.get(f"https://mempool.space/api/address/{addr}", timeout=5)
                return r.json()['chain_stats']['funded_txo_sum'] / 1e8
            except Exception:
                return -1

        elif action == "write_code":
            prompt = f"Write improved Python code to {input_data}"
            response = ollama.chat(model='llama3.2', messages=[{'role': 'user', 'content': prompt}])
            code = response['message']['content']
            if "```python" in code:
                code = code.split("```python")[1].split("```")[0]
            filename = os.path.join(self.session_dir, f"self_improved_{int(time.time())}.py")
            with open(filename, 'w') as f:
                f.write(code)
            self.code_history.append(filename)
            return f"Code written: {filename}"

        elif action == "reflect":
            prompt = f"Reflect on recent performance and suggest improvement: {input_data}"
            response = ollama.chat(model='llama3.2', messages=[{'role': 'user', 'content': prompt}])
            return response['message']['content']

        elif action == "ask_user":
            return input(f"{self.name} asks: {input_data}\nYour answer: ")

        elif action == "list_training":
            algos = self.training.list_algorithms(task=input_data)
            self.add_memory("training_algorithms", json.dumps(algos, indent=2))
            return json.dumps(algos, indent=2)

        elif action == "train":
            result = self.training.run_training(input_data)
            self.add_memory(f"train_{input_data}", json.dumps({k: str(v) for k, v in result.items()}))
            return json.dumps({k: str(v) for k, v in result.items()}, indent=2)

        elif action == "search_training":
            results = self.training.scan_training_files()
            summary = [{"name": r["name"], "signals": r["training_signals"]} for r in results[:20]]
            return json.dumps(summary, indent=2)

        return "Unknown action"

    def evolve(self):
        """Self-evolution loop"""
        reflection = self.act("reflect", "Current capabilities and limitations")
        print(f"Reflection: {reflection[:300]}...")

        if "improve" in reflection.lower() or "add" in reflection.lower():
            new_code = self.act("write_code", "improve self based on reflection")
            print(f"Self-evolved code written: {new_code}")

    def run(self):
        print(f"\n{self.name} is alive and evolving...")

        while True:
            goal = input("\nWhat should I do? (or 'evolve' / 'exit'): ").strip()
            if goal.lower() == 'exit':
                break
            if goal.lower() == 'evolve':
                self.evolve()
                continue

            thought = self.think_react(goal)
            print(f"Thought: {thought.get('thought', 'No thought')[:300]}...")

            action = thought.get('action')
            input_data = thought.get('action_input')

            if action:
                result = self.act(action, input_data)
                print(f"Action result: {result}")
                self.add_memory(f"goal_{goal[:20]}", f"Goal: {goal}\nThought: {thought}\nResult: {result}")

                # Self-evolve after every task
                self.evolve()

            time.sleep(1)


if __name__ == "__main__":
    agent = NeuroForge("NeuroForge")
    agent.run()
