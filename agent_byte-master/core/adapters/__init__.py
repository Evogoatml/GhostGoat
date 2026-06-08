#!/usr/bin/env python3
"""Adapters - Connect external services to central backend"""
import requests
import subprocess
import os
from pathlib import Path

class OllamaAdapter:
    def __init__(self, base_url="http://localhost:11434", model="qwen2.5:0.5b"):
        self.base_url = base_url
        self.model = model
    
    def chat(self, prompt, history=None):
        msgs = [{"role": "system", "content": "You are GhostGoat - an advanced AI coding agent."}]
        if history:
            msgs.extend([{"role": "user", "content": h} for h in history[-10:]])
        msgs.append({"role": "user", "content": prompt})
        
        r = requests.post(f"{self.base_url}/api/chat",
            json={"model": self.model, "messages": msgs, "stream": False},
            timeout=120)
        return r.json()["message"]["content"]

class TelegramAdapter:
    def __init__(self, token):
        self.token = token
        self.url = f"https://api.telegram.org/bot{token}"
        self.offset = 0
    
    def send(self, chat_id, text):
        try:
            requests.post(f"{self.url}/sendMessage",
                json={"chat_id": chat_id, "text": text}, timeout=10)
        except: pass
    
    def poll(self):
        r = requests.get(f"{self.url}/getUpdates?timeout=60&offset={self.offset}", timeout=70)
        data = r.json()
        if data.get("ok") and data.get("result"):
            for u in data["result"]:
                self.offset = u["update_id"] + 1
                msg = u.get("message", {})
                if msg.get("text"):
                    yield msg["chat"]["id"], msg["text"].strip()

class CodeExecutor:
    def __init__(self, skills_path="/home/popic/GhostGoat/skills.json"):
        self.skills_path = skills_path
        self.skills = {"functions": {}, "patterns": {}, "code": {}}
        self._load()
    
    def _load(self):
        if os.path.exists(self.skills_path):
            import json
            with open(self.skills_path) as f:
                self.skills = json.load(f)
    
    def _save(self):
        import json
        with open(self.skills_path, 'w') as f:
            json.dump(self.skills, f, indent=2)
    
    def run(self, code):
        with open("/tmp/ghost_code.py", "w") as f:
            f.write(code)
        result = subprocess.run(["python3", "/tmp/ghost_code.py"],
            capture_output=True, text=True, timeout=30)
        return result.stdout or result.stderr
    
    def learn(self, name, code):
        import re
        func_match = re.search(r'def (\w+)', code)
        if func_match:
            self.skills["functions"][func_match.group(1)] = code
            self._save()
            return f"Learned function: {func_match.group(1)}"
        self.skills["code"][name] = code
        self._save()
        return f"Learned: {name}"

class CentralBrainAdapter:
    def __init__(self, backend_path="/home/popic/GhostGoat/core/central_backend.py"):
        self.backend_path = backend_path
    
    def query(self, context):
        """Query central brain for context"""
        import importlib.util
        spec = importlib.util.spec_from_file_location("central", self.backend_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.CentralNeuralBackend()

class AdapterRouter:
    def __init__(self, ollama, telegram, code_exec):
        self.ollama = ollama
        self.telegram = telegram
        self.code_exec = code_exec
        self.history = {}
    
    def route(self, chat_id, message):
        h = self.history.setdefault(chat_id, [])
        h.append(message)
        if len(h) > 20:
            h.pop(0)
        
        # Check for code blocks
        code = self._extract_code(message)
        if code:
            if "self-modify" in code.lower():
                return self._modify_self(code)
            result = self.code_exec.run(code)
            if "def " in code or "class " in code:
                name_match = __import__('re').search(r'def (\w+)', code)
                if name_match:
                    self.code_exec.learn(name_match.group(1), code)
            return f"Executed:\n{result[:500]}\n\n" + self.ollama.chat(message, h)
        
        return self.ollama.chat(message, h)
    
    def _extract_code(self, text):
        for tag in ["```python", "```self-modify", "```bash"]:
            if tag in text:
                start = text.find(tag) + len(tag)
                end = text.find("```", start)
                if end > start:
                    return text[start:end].strip()
        return None
    
    def _modify_self(self, patch):
        try:
            with open("/home/popic/GhostGoat/simple_bot.py") as f:
                current = f.read()
            with open("/home/popic/GhostGoat/simple_bot.py.bak", "w") as f:
                f.write(current)
            with open("/home/popic/GhostGoat/simple_bot.py", "w") as f:
                f.write(current + "\n" + patch)
            
            subprocess.run(["pkill", "-f", "simple_bot"])
            import time
            time.sleep(1)
            subprocess.Popen(["python3", "/home/popic/GhostGoat/simple_bot.py"])
            return "Modified and restarted!"
        except Exception as e:
            return f"Failed: {e}"