#!/usr/bin/env python3
"""🕵 NEURO-SWARM: Simple ReAct + Ollama Telegram Bot"""
import asyncio
import re
import subprocess
import os
import json
import time
from telegram import Bot
from core.init_dual_brain import initialize_dual_brain

# At startup
dual_brain = initialize_dual_brain(orchestrator=your_orchestrator)

TOKEN = "8584003796:AAGBD2m3r9-KxZBaU38VuDsNXMAm4Lwu8hM"
PAYLOADS = "/home/popic/PayloadsAllTheThings"
MEMORY_FILE = os.path.expanduser("~/.pentest_brain.json")

GREETINGS = ["hi", "hello", "hey", "alive", "sup", "yo"]

def ollama(prompt, t=20):
    try:
        r = subprocess.run(
            ["ollama", "run", "opencode", prompt],
            capture_output=True, text=True, timeout=t
        )
        return r.stdout.strip() if r.stdout else None
    except:
        return None

def react_think(task):
    prompt = f"""You are a pentesting assistant.
Task: {task}
Choose ONE action:
- nmap_scan: run nmap on URL
- gobuster: directory brute-force
- sqlmap: test SQL injection
- search_payloads: find in PayloadsAllTheThings
- greeting: friendly response
- chat: conversational response

Respond ONLY: action|custom_response
Example: "nmap_scan|Scan complete: 3 open ports"
Example: "greeting|Hey! Ready to hack." """
    return ollama(prompt) or fallback_route(task)

def fallback_route(task):
    t = task.lower()
    if any(g in t for g in GREETINGS):
        return "greeting|🕵 Hey! What do you need?"
    if "find" in t or "payload" in t:
        return "search_payloads|Found matching folders"
    if "nmap" in t:
        return "nmap_scan|Running nmap"
    if "gobuster" in t or "dir" in t:
        return "gobuster|Running gobuster"
    return "chat|I can run nmap, gobuster, sqlmap. Send URL!"

def act(action, task):
    parts = task.split()
    urls = re.findall(r'([a-z0-9.-]+\.[a-z]{2,})', task.lower())
    target = urls[0] if urls else None
    
    if action == "nmap_scan" and target:
        r = subprocess.run(f"nmap -sV {target}", shell=True, capture_output=True, text=True, timeout=45)
        return r.stdout[:2000] if r.stdout else "No output"
    
    if action == "gobuster" and target:
        r = subprocess.run(f"gobuster dir -u http://{target} -w /usr/share/wordlists/dirb/common.txt -q", 
                          shell=True, capture_output=True, text=True, timeout=45)
        return r.stdout[:1500] if r.stdout else "No output"
    
    if action == "sqlmap" and target:
        r = subprocess.run(f"sqlmap -u {target} --batch -v 0", 
                          shell=True, capture_output=True, text=True, timeout=45)
        return r.stdout[:1500] if r.stdout else "No output"
    
    if action == "search_payloads":
        folders = sorted([d.split("/")[-1] for d in os.listdir(PAYLOADS) if os.path.isdir(f"{PAYLOADS}/{d}")])
        matches = [f for f in folders if any(q in f.lower() for q in parts if len(q) > 2)]
        return ", ".join(matches[:10]) if matches else "No matches"
    
    if action == "greeting":
        return "🕵 Hey! What do you need? Send URL or request tool."
    
    return "Send a URL or ask for help!"

def save_memory(key, val):
    try:
        data = json.load(open(MEMORY_FILE)) if os.path.exists(MEMORY_FILE) else {}
        data[key] = {"val": val, "time": time.time()}
        json.dump(data, open(MEMORY_FILE, "w"), indent=2)
    except:
        pass

async def main():
    bot = Bot(token=TOKEN)
    offset = None
    print("Neuro-Swarm ready!")
    
    while True:
        try:
            updates = await bot.get_updates(timeout=30, offset=offset)
            
            for u in updates:
                offset = u.update_id + 1
                if not u.message:
                    continue
                
                txt = u.message.text.strip()
                cid = u.message.chat.id
                print(f"-> {txt}")
                
                response = react_think(txt)
                if "|" in response:
                    action, result = response.split("|", 1)
                else:
                    action, result = fallback_route(txt)
                
                act_result = act(action.strip(), txt)
                save_memory(f"req_{time.time()}", {"task": txt, "action": action})
                
                if len(act_result) > 500:
                    await bot.send_message(cid, f"```{act_result[:2200]}```", parse_mode="MarkdownV2")
                else:
                    await bot.send_message(cid, act_result)
                
        except Exception as e:
            print(f"Error: {e}")
            await asyncio.sleep(2)

if __name__ == "__main__":
    while True:
        try:
            asyncio.run(main())
        except:
            print("Restarting...")
            asyncio.sleep(3)
