# self_evolving_agent.py
# Self-Intelligent Adaptive Agent with GraphRAG + Self-Code-Writing
# Run: python self_evolving_agent.py
import os
import json
import time
import hashlib
import networkx as nx
from datetime import datetime
from typing import Dict, List, Any
import requests
from pathlib import Path

# === LOCAL LLM (change to your model) ===
# pip install ollama (or use huggingface transformers)
import ollama

from ACS_SYSTEM.asi.training_bridge import TrainingBridge


class SelfEvolvingAgent:
    def __init__(self, name="NeuroForge"):
        self.name = name
        self.graph = nx.DiGraph()  # Agentic GraphRAG memory
        self.session_dir = f"agent_memory_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        os.makedirs(self.session_dir, exist_ok=True)

        self.performance_log = []
        self.code_history = []
        self.training = TrainingBridge()

        print(f"[SelfEvolvingAgent] {self.name} initialized. Self-evolution mode: ACTIVE")

    def think(self, prompt: str) -> str:
        """Core reasoning with ReAct + GraphRAG"""
        # Retrieve relevant memory from graph
        context = self.retrieve_memory(prompt)

        full_prompt = f"""
        You are {self.name}, a self-improving neuro-symbolic agent.
        Current goal: {prompt}

        Memory context:
        {context}

        Available training algorithms:
        {self.training.summary()}

        Think step by step. Use tools if needed. Then decide:
        1. What to do
        2. Whether to write/improve code
        3. How to optimize yourself
        4. Whether to train a model using available algorithms

        Respond in JSON format:
        {{
            "thought": "...",
            "action": "code_write | code_fix | research | execute | reflect | train | list_training",
            "code": "```python\n...```" or null,
            "next_goal": "..."
        }}
        """

        response = ollama.chat(model='llama3.2', messages=[{'role': 'user', 'content': full_prompt}])
        return response['message']['content']

    def retrieve_memory(self, query: str) -> str:
        """GraphRAG retrieval"""
        if not self.graph.nodes:
            return "No memory yet."
        # Simple similarity search (can upgrade to embeddings)
        relevant = [n for n in self.graph.nodes if query.lower() in n.lower()]
        return "\n".join([self.graph.nodes[n]['content'] for n in relevant[:5]])

    def write_code(self, goal: str) -> str:
        """Self code writing"""
        prompt = f"Write a complete, optimized Python function to achieve: {goal}\nMake it clean, commented, and production-ready."
        response = ollama.chat(model='llama3.2', messages=[{'role': 'user', 'content': prompt}])

        code = response['message']['content']
        if "```python" in code:
            code = code.split("```python")[1].split("```")[0]

        # Save to history
        filename = os.path.join(self.session_dir, f"self_generated_{int(time.time())}.py")
        with open(filename, 'w') as f:
            f.write(code)

        self.code_history.append(filename)
        self.graph.add_node(filename, content=code, type="self_generated")

        print(f"Wrote new code -> {filename}")
        return code

    def reflect_and_optimize(self, result: str):
        """Self-diagnostic loop"""
        prompt = f"""
        You just ran a task. Result: {result}
        Analyze what went well and what can be improved.
        Suggest specific code improvements or new capabilities.
        """
        response = ollama.chat(model='llama3.2', messages=[{'role': 'user', 'content': prompt}])
        print(f"Reflection: {response['message']['content'][:300]}...")

    def run(self):
        print(f"\n{self.name} is now self-evolving...")

        while True:
            goal = input("\nWhat should I work on? (or 'exit'): ").strip()
            if goal.lower() in ['exit', 'quit']:
                break

            thought = self.think(goal)
            print(f"Thought: {thought[:300]}...")

            # Simple action parser
            if "code_write" in thought.lower() or "write code" in thought.lower():
                self.write_code(goal)
            elif "train" in thought.lower() and "list_training" not in thought.lower():
                # Extract algorithm name from thought if possible
                algos = self.training.list_algorithms()
                matched = [a["name"] for a in algos if a["name"] in thought.lower()]
                algo_name = matched[0] if matched else "decision_tree"
                result = self.training.run_training(algo_name)
                print(f"Training result: {json.dumps({k: str(v) for k, v in result.items()}, indent=2)}")
                self.graph.add_node(f"train_{algo_name}", content=str(result), type="training")
            elif "list_training" in thought.lower():
                algos = self.training.list_algorithms()
                print(f"Available algorithms: {json.dumps(algos, indent=2)}")
            elif "improve" in thought.lower() or "optimize" in thought.lower():
                self.reflect_and_optimize("Task completed with current capabilities.")

            time.sleep(1)


if __name__ == "__main__":
    agent = SelfEvolvingAgent("NeuroForge")
    agent.run()
