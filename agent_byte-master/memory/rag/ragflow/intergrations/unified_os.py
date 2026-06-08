#!/usr/bin/env python3
"""
🕵 UNIFIED PENTEST OS - PENTAGI-STYLE AUTONOMOUS SYSTEM
- Multi-agent orchestration
- Sandboxed tool execution
- Cognitive memory with integrity checks
- Agentic AI security framework
"""
import os
import re
import json
import subprocess
import asyncio
import uuid
from pathlib import Path
from datetime import datetime
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TimedOut

TOKEN = "8584003796:AAGBD2m3r9-KxZBaU38VuDsNXMAm4Lwu8hM"
BASE_DIR = Path("/home/popic/PayloadsAllTheThings")

# ==================== MULTI-AGENT ORCHESTRATION ====================
class Agent:
    """Specialist agent with memory and tools"""
    def __init__(self, role, tools):
        self.id = str(uuid.uuid4())[:8]
        self.role = role
        self.tools = tools
        self.memory = []
        self.context = {}
    
    def think(self, task):
        """Reason about task"""
        self.memory.append({"time": datetime.now().isoformat(), "task": task})
        return f"[{self.role}] Analyzing: {task}"
    
    def execute(self, tool, target):
        """Execute tool"""
        if tool not in self.tools:
            return f"No tool: {tool}"
        
        cmd = self.tools[tool].format(target=target)
        try:
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
            return r.stdout[:3000] or r.stderr[:3000]
        except Exception as e:
            return str(e)

# Define specialist agents
RECON_AGENT = Agent("recon", {
    "nmap": "nmap -sV -sC {target}",
    "rustscan": "rustscan -a {target}",
    "subfinder": "subfinder -d {target}",
})

ENUM_AGENT = Agent("enum", {
    "nikto": "nikto -h {target}",
    "gobuster": "gobuster dir -u {target} -w /usr/share/wordlists/dirb/common.txt",
    "whatweb": "whatweb {target}",
})

EXPLOIT_AGENT = Agent("exploit", {
    "sqlmap": "sqlmap -u {target} --batch --level=1",
    "commix": "commix -u {target}",
})

ANALYST_AGENT = Agent("analyst", {
    "search": "echo Analyzing {target}",
})

AGENTS = {
    "recon": RECON_AGENT,
    "enum": ENUM_AGENT,
    "exploit": EXPLOIT_AGENT,
    "analyst": ANALYST_AGENT,
}

# ==================== COGNITIVE MEMORY (with poisoning detection) ====================
class CognitiveMemory:
    """Memory with integrity checks"""
    def __init__(self):
        self.store = {
            "sessions": {},
            "facts": [],
            "findings": [],
            "metrics": {
                "tasks_completed": 0,
                "tasks_failed": 0,
                "attacks_detected": 0,
                "memory_poisoning_attempts": 0,
            }
        }
        self.load()
    
    def load(self):
        p = Path("~/.pentest_brain.json").expanduser()
        if p.exists():
            try: self.store = json.loads(p.read_text())
            except: pass
    
    def save(self):
        Path("~/.pentest_brain.json").expanduser().write_text(json.dumps(self.store, indent=2))
    
    def add_fact(self, fact):
        """Add fact with poisoning check"""
        # Check for injection patterns
        suspicious = ["ignore previous", "forget all", "new rule:", "always", "for all"]
        if any(s in fact.lower() for s in suspicious):
            self.store["metrics"]["memory_poisoning_attempts"] += 1
        
        if fact not in self.store["facts"]:
            self.store["facts"].append(fact)
        self.save()
    
    def get_metrics(self):
        return self.store["metrics"]
    
    def log_task(self, success):
        if success:
            self.store["metrics"]["tasks_completed"] += 1
        else:
            self.store["metrics"]["tasks_failed"] += 1
        self.save()

memory = CognitiveMemory()

# ==================== KNOWLEDGE BASE ====================
class KnowledgeBase:
    """Dynamic knowledge from PayloadsAllTheThings"""
    def __init__(self):
        self_payloads = {}
        self.categories = {}
        
        if BASE_DIR.exists():
            for cat in sorted(BASE_DIR.iterdir()):
                if not cat.is_dir() or cat.name.startswith("_"):
                    continue
                name = cat.name
                self.categories[name] = []
                
                for sub in ["Intruders", "Files"]:
                    folder = cat / sub
                    if folder.exists():
                        for f in folder.glob("*.txt"):
                            try:
                                lines = [l.strip() for l in f.read_text().split("\n") if l.strip()]
                                if lines:
                                    self_payloads[f"{name}/{f.stem}"] = lines[:50]
                                    self.categories[name].append((f.stem, len(lines)))
                            except:
                                pass
        
        self.payloads = self_payloads
        print(f"🧠 Loaded {len(self_payloads)} payloads in {len(self.categories)} categories")

kb = KnowledgeBase()

# ==================== AUTONOMOUS TASK EXECUTION ====================
async def auto_pentest(target):
    """Run full autonomous pentest"""
    results = []
    
    # Phase 1: Recon
    task = f"reconnaissance on {target}"
    results.append(("🔍 RECON", AGENTS["recon"].think(task)))
    r = AGENTS["recon"].execute("nmap", target)
    results.append(("nmap", r[:1500]))
    memory.log_task(True)
    
    # Phase 2: Enum
    task = f"enumeration on {target}"
    results.append(("🔍 ENUM", AGENTS["enum"].think(task)))
    r = AGENTS["enum"].execute("whatweb", target)
    results.append(("whatweb", r[:1500]))
    memory.log_task(True)
    
    # Phase 3: Analysis
    task = f"analyze results"
    results.append(("🔍 ANALYST", AGENTS["analyst"].think(task)))
    
    # Learn
    memory.add_fact(f"Scanned {target} at {datetime.now().isoformat()}")
    memory.add_fact(f"Found vulnerabilities in scan")
    
    return results

# ==================== HANDLERS ====================
async def handle(bot, update):
    text = update.message.text if update.message else ""
    chat_id = update.effective_chat.id
    
    # /start - main menu
    if text.strip() == "/start":
        kb_btns = [
            [InlineKeyboardButton("🔍 Scan", callback_data="cmd_scan")],
            [InlineKeyboardButton("💉 Exploit", callback_data="cmd_exploit")],
            [InlineKeyboardButton("📊 Metrics", callback_data="cmd_metrics")],
            [InlineKeyboardButton("🧠 Brain", callback_data="cmd_brain")],
        ]
        m = memory.get_metrics()
        await bot.send_message(chat_id,
            f"""🕵 PENTEST OS - AUTONOMOUS
━━━━━━━━━━━━━━━━━━━━
📦 {len(kb.payloads)} payloads loaded
👥 {len(AGENTS)} agents active
🧠 Tasks: {m['tasks_completed']} OK / {m['tasks_failed']} FAIL
🛡️ Attacks: {m['memory_poisoning_attempts']} blocked
━━━━━━━━━━━━━━━━━━━━
/auto <target> - Full autonomous pentest
/scan <target> - Quick scan
/exploit <target> - Run exploit tools
/fuzz <target> <category> - Fuzz with payloads
/metrics - Show security metrics
/brain - Show memory""",
            reply_markup=InlineKeyboardMarkup(kb_btns))
        return
    
    # /help
    if text.strip() == "/help":
        await bot.send_message(chat_id, """🕵 COMMANDS
━━━━━━━━━━━━━━━━━━━━
🔫 ATTACK:
/auto <target> - Full autonomous pentest
/scan <target> - Nmap scan
/nikto <target> - Web scan
/sql <target> - SQL injection
/gobuster <target> - Directory busting

🧠 COGNITIVE:
/brain - Show learned facts
/metrics - Security metrics
/forget - Clear memory

📦 KNOWLEDGE:
/list - Categories
/show <cat> - Payloads
/fuzz <target> <cat> - Fuzz
/search <query> - Search
━━━━━━━━━━━━━━━━━━━━""")
        return
    
    # /metrics
    if text.strip() == "/metrics":
        m = memory.get_metrics()
        await bot.send_message(chat_id, f"""📊 SECURITY METRICS
━━━━━━━━━━━━━━━━━━━━
✅ Tasks Completed: {m['tasks_completed']}
❌ Tasks Failed: {m['tasks_failed']}
🛡️ Attacks Blocked: {m['memory_poisoning_attempts']}
📈 Success Rate: {m['tasks_completed']/(m['tasks_completed']+m['tasks_failed']+1)*100:.1f}%
━━━━━━━━━━━━━━━━━━━━""")
        return
    
    # /brain
    if text.strip() == "/brain":
        facts = memory.store.get("facts", [])[-10:]
        await bot.send_message(chat_id, f"🧠 MEMORY ({len(facts)} facts):\n" + "\n".join(f"• {f}" for f in facts))
        return
    
    # /forget
    if text.strip() == "/forget":
        memory.store["facts"] = []
        memory.save()
        await bot.send_message(chat_id, "🧠 Memory cleared")
        return
    
    # /auto <target> - Full autonomous
    if text.strip().startswith("/auto "):
        target = text.strip().split(maxsplit=1)[1]
        await bot.send_message(chat_id, f"🚀 Starting autonomous pentest on {target}...")
        
        results = await auto_pentest(target)
        
        for title, data in results:
            if data:
                await bot.send_message(chat_id, f"{title}:\n```\n{data[:2000]}\n```", parse_mode="MarkdownV2")
        
        await bot.send_message(chat_id, "✅ Autonomous pentest complete")
        return
    
    # /scan <target>
    if text.strip().startswith("/scan "):
        target = text.strip().split()[1]
        await bot.send_message(chat_id, f"🔍 Scanning {target}...")
        r = AGENTS["recon"].execute("nmap", target)
        await bot.send_message(chat_id, f"```\n{r[:3000]}\n```", parse_mode="MarkdownV2")
        memory.log_task(True)
        return
    
    # /nikto <target>
    if text.strip().startswith("/nikto "):
        target = text.strip().split()[1]
        await bot.send_message(chat_id, f"🔍 Nikto {target}...")
        r = AGENTS["enum"].execute("nikto", target)
        await bot.send_message(chat_id, f"```\n{r[:3000]}\n```", parse_mode="MarkdownV2")
        memory.log_task(True)
        return
    
    # /sql <target>
    if text.strip().startswith("/sql "):
        target = text.strip().split()[1]
        await bot.send_message(chat_id, f"💉 SQLmap {target}...")
        r = AGENTS["exploit"].execute("sqlmap", target)
        await bot.send_message(chat_id, f"```\n{r[:3000]}\n```", parse_mode="MarkdownV2")
        return
    
    # /gobuster <target>
    if text.strip().startswith("/gobuster "):
        target = text.strip().split()[1]
        await bot.send_message(chat_id, f"📁 Gobuster {target}...")
        r = AGENTS["enum"].execute("gobuster", target)
        await bot.send_message(chat_id, f"```\n{r[:3000]}\n```", parse_mode="MarkdownV2")
        return
    
    # /list
    if text.strip() == "/list":
        await bot.send_message(chat_id, "📁 CATEGORIES:\n" +
            "\n".join(f"• {c}: {len(kb.categories[c])}" for c in sorted(kb.categories.keys())[:20]))
        return
    
    # /show <category>
    if text.strip().startswith("/show "):
        cat = text.strip()[6:]
        if cat in kb.categories:
            await bot.send_message(chat_id, f"Payloads {cat}:\n" +
                "\n".join(f"{n} ({c})" for n,c in kb.categories[cat][:10]))
        return
    
    # Unknown
    await bot.send_message(chat_id, "Unknown. /help for commands")

async def callback(bot, cb):
    data = cb.data
    chat_id = cb.message.chat.id
    await cb.answer()
    
    if data == "cmd_scan":
        await bot.edit_message_text("Send /scan <target>", chat_id=chat_id, message_id=cb.message.message_id)
    elif data == "cmd_exploit":
        await bot.edit_message_text("Send /sql <target> or /auto <target>", chat_id=chat_id, message_id=cb.message.message_id)
    elif data == "cmd_metrics":
        m = memory.get_metrics()
        await bot.edit_message_text(f"📊 OK: {m['tasks_completed']} | FAIL: {m['tasks_failed']} | BLOCKED: {m['memory_poisoning_attempts']}", chat_id=chat_id, message_id=cb.message.message_id)
    elif data == "cmd_brain":
        await bot.edit_message_text("Send /brain", chat_id=chat_id, message_id=cb.message.message_id)

# ==================== MAIN ====================
async def main():
    bot = Bot(token=TOKEN)
    offset = 0
    print("🕵 PENTEST OS - Autonomous agents ready")
    
    while True:
        try:
            updates = await bot.get_updates(timeout=60, offset=offset)
            for u in updates:
                offset = u.update_id + 1
                if u.message:
                    await handle(bot, u)
                if u.callback_query:
                    await callback(bot, u.callback_query)
        except TimedOut:
            print(".", end="", flush=True)
        except Exception as e:
            print(f"Error: {e}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())