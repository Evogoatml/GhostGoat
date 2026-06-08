#!/usr/bin/env python3
"""Router - Directs requests to appropriate adapters"""
import os
import json
from core.adapters import OllamaAdapter, TelegramAdapter, CodeExecutor, SkillMemory

class RequestRouter:
    def __init__(self, ollama_adapter, telegram_adapter):
        self.ollama = ollama_adapter
        self.telegram = telegram_adapter
        self.executor = CodeExecutor()
        self.memory = SkillMemory()
        self.history = {}
    
    def route(self, chat_id, message):
        """Route message to appropriate handler"""
        if "execute" in message.lower() or "run code" in message.lower():
            return self.handle_code(chat_id, message)
        elif "learn" in message.lower() or "remember" in message.lower():
            return self.handle_learn(chat_id, message)
        elif "self-modify" in message.lower():
            return self.handle_modify(chat_id, message)
        else:
            return self.handle_chat(chat_id, message)
    
    def handle_chat(self, chat_id, message):
        """Chat with LLM"""
        h = self.history.setdefault(chat_id, [])
        h.append(message)
        if len(h) > 20:
            h.pop(0)
        
        skills = self.memory.load()
        context = f"Known skills: {list(skills.get('code', {}).keys())}"
        reply = self.ollama.chat(message, h)
        return reply
    
    def handle_code(self, chat_id, message):
        """Extract and execute code"""
        import re
        code = None
        if "```python" in message:
            start = message.find("```python") + 9
            end = message.find("```", start)
            code = message[start:end].strip()
        
        if code:
            result = self.executor.run(code)
            return f"Executed:\n{result[:500]}"
        return "No code found to execute."
    
    def handle_learn(self, chat_id, message):
        """Save skill or pattern"""
        import re
        match = re.search(r'learn (\w+) as (.+)', message)
        if match:
            name, code = match.groups()
            self.memory.add_code(name, code)
            return f"Learned: {name}"
        return "What do you want me to learn?"
    
    def handle_modify(self, chat_id, message):
        """Modify self"""
        import re
        code = None
        if "```self-modify" in message:
            start = message.find("```self-modify") + 13
            end = message.find("```", start)
            code = message[start:end].strip()
        
        if code:
            with open("/home/popic/GhostGoat/simple_bot.py") as f:
                current = f.read()
            with open("/home/popic/GhostGoat/simple_bot.py.bak", "w") as f:
                f.write(current)
            current += "\n" + code
            with open("/home/popic/GhostGoat/simple_bot.py", "w") as f:
                f.write(current)
            
            import subprocess
            import time
            subprocess.run(["pkill", "-f", "simple_bot"])
            time.sleep(1)
            subprocess.Popen(["python3", "/home/popic/GhostGoat/simple_bot.py"])
            return "Modified and restarted!"
        return "No modification found."