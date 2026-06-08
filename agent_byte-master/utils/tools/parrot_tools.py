#!/usr/bin/env python3
"""
FULL PARROT TOOLKIT - All tools from Parrot Security
"""

import subprocess
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

TOKEN = '8584003796:AAGBD2m3r9-KxZBaU38VuDsNXMAm4Lwu8hM'

# ALL Parrot Tools
PARROT_TOOLS = {
    # --- RECON ---
    "nmap": {"cat": "network", "desc": "Network scanner", "cmd": ["nmap", "-sV", "-sC", "-T4"]},
    "masscan": {"cat": "network", "desc": "Fast TCP scanner", "cmd": ["masscan"]},
    "netdiscover": {"cat": "network", "desc": "ARP scanner", "cmd": ["netdiscover", "-p"]},
    "arp-scan": {"cat": "network", "desc": "ARP enumeration", "cmd": ["arp-scan"]},
    
    # --- WEB ---
    "nikto": {"cat": "web", "desc": "Web vulnerability scanner", "cmd": ["nikto", "-h"]},
    "whatweb": {"cat": "web", "desc": "Fingerprinter", "cmd": ["whatweb"]},
    "gobuster": {"cat": "web", "desc": "Directory busting", "cmd": ["gobuster", "dir", "-w", "/usr/share/wordlists/dirb/common.txt"]},
    "dirb": {"cat": "web", "desc": "Directory scanner", "cmd": ["dirb"]},
    "dirbuster": {"cat": "web", "desc": "GUI directory", "cmd": ["dirbuster"]},
    "wpscan": {"cat": "web", "desc": "WordPress scanner", "cmd": ["wpscan", "--enumerate"]},
    "droopescan": {"cat": "web", "desc": "CMS scanner", "cmd": ["droopescan", "scan"]},
    "joomscan": {"cat": "web", "desc": "Joomla scanner", "cmd": ["joomscan"]},
    "cmsmap": {"cat": "web", "desc": "CMS scanner", "cmd": ["cmsmap"]},
    
    # --- SQL ---
    "sqlmap": {"cat": "sql", "desc": "SQL injection", "cmd": ["sqlmap", "-u"]},
    
    # --- SSL ---
    "sslscan": {"cat": "ssl", "desc": "SSL analyzer", "cmd": ["sslscan"]},
    "testssl": {"cat": "ssl", "desc": "SSL/TLS checker", "cmd": ["testssl"]},
    
    # --- DNS ---
    "dnsenum": {"cat": "dns", "desc": "DNS enumerator", "cmd": ["dnsenum"]},
    "fierce": {"cat": "dns", "desc": "DNS scanner", "cmd": ["fierce"]},
    "sublist3r": {"cat": "dns", "desc": "Subdomain finder", "cmd": ["sublist3r"]},
    "amass": {"cat": "dns", "desc": "Subdomain Enum", "cmd": ["amass", "enum"]},
    
    # --- PASSWORD ---
    "hydra": {"cat": "password", "desc": "Password cracker", "cmd": ["hydra"]},
    "john": {"cat": "password", "desc": "John the Ripper", "cmd": ["john"]},
    "hashcat": {"cat": "password", "desc": "GPU hasher", "cmd": ["hashcat"]},
    " crunch": {"cat": "password", "desc": "Wordlist gen", "cmd": ["crunch"]},
    
    # --- EXPLOIT ---
    "searchsploit": {"cat": "exploit", "desc": "Exploit-DB", "cmd": ["searchsploit"]},
    "msfconsole": {"cat": "exploit", "desc": "Metasploit", "cmd": ["msfconsole"]},
    "msfvenom": {"cat": "exploit", "desc": "Payload gen", "cmd": ["msfvenom"]},
    "nuclei": {"cat": "exploit", "desc": "Vulnerability scanner", "cmd": ["nuclei"]},
    
    # --- WIRELESS ---
    "aircrack": {"cat": "wifi", "desc": "WiFi cracker", "cmd": ["aircrack-ng"]},
    "reaver": {"cat": "wifi", "desc": "WPS cracker", "cmd": ["reaver"]},
    "wifite": {"cat": "wifi", "desc": "WiFi auditor", "cmd": ["wifite"]},
    
    # --- FORENSICS ---
    "steghide": {"cat": "forensics", "desc": "Steganalysis", "cmd": ["steghide"]},
    "binwalk": {"cat": "forensics", "desc": "Firmware analysis", "cmd": ["binwalk"]},
    "foremost": {"cat": "forensics", "desc": "Carver", "cmd": ["foremost"]},
    
    # --- SOCIAL ---
    "theHarvester": {"cat": "social", "desc": "Email harvester", "cmd": ["theHarvester"]},
    "recon-ng": {"cat": "social", "desc": "Recon framework", "cmd": ["recon-ng"]},
}

# Categorize tools
TOOL_CATS = {
    "🔍 RECON": ["nmap", "masscan", "netdiscover", "arp-scan"],
    "🌐 WEB": ["nikto", "whatweb", "gobuster", "dirb", "wpscan", "droopescan", "joomscan"],
    "💉 SQL": ["sqlmap"],
    "🔐 SSL": ["sslscan", "testssl"],
    "🌍 DNS": ["dnsenum", "fierce", "sublist3r", "amass"],
    "🔑 PASSWORD": ["hydra", "john", "hashcat", "crunch"],
    "💣 EXPLOIT": ["searchsploit", "msfconsole", "msfvenom", "nuclei"],
    "📶 WIRELESS": ["aircrack", "reaver", "wifite"],
    "🔎 FORENSICS": ["steghide", "binwalk", "foremost"],
    "🎭 SOCIAL": ["theHarvester", "recon-ng"],
}

# Check what's installed
INSTALLED = {}
def check_installed():
    for tool in PARROT_TOOLS:
        try:
            subprocess.run(["which", tool], capture_output=True, check=True)
            INSTALLED[tool] = True
        except:
            INSTALLED[tool] = False

check_installed()

class Runner:
    def run(self, tool, target):
        target = target.strip()
        
        # Add http for web tools
        web_tools = ["nikto", "whatweb", "gobuster", "dirb", "wpscan", "droopescan", "joomscan", "cmsmap"]
        if target and not target.startswith("http"):
            if tool in web_tools:
                target = "http://" + target
        
        template = PARROT_TOOLS[tool]["cmd"]
        cmd = template + [target]
        
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            return r.stdout[:4000] or r.stderr[:500]
        except FileNotFoundError:
            return f"{tool} not installed"
        except Exception as e:
            return f"Error: {e}"

runner = Runner()
user_targets = {}

async def start(update, ctx):
    # Build keyboard by category
    kb = []
    for cat, tools in TOOL_CATS.items():
        row = []
        for t in tools:
            if INSTALLED.get(t, False):
                label = f"{t}"
                row.append(InlineKeyboardButton(label, callback_data=f"run_{t}"))
        if row:
            kb.append(row)
    
    # Add utility
    kb.append([InlineKeyboardButton("📋 List Installed", callback_data="show_installed")])
    
    await update.message.reply_text(
        "<b>🕵️ FULL PARROT TOOLKIT</b>\n\nSelect tool:",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode='HTML'
    )

async def show_installed(update, ctx):
    query = update.callback_query
    await query.answer()
    
    installed = [t for t, ok in INSTALLED.items() if ok]
    missing = [t for t, ok in INSTALLED.items() if not ok]
    
    text = f"<b>✅ INSTALLED ({len(installed)}):</b>\n{', '.join(installed[:20])}"
    if len(installed) > 20:
        text += f"\n...and {len(installed)-20} more"
    
    if missing:
        text += f"\n\n<b>❌ MISSING ({len(missing)}):</b>\n{', '.join(missing[:10])}"
    
    await query.message.edit_text(text, parse_mode='HTML')

async def handle_callback(update, ctx):
    query = update.callback_query
    await query.answer()
    data = query.data
    chat_id = query.message.chat_id
    
    if data == "show_installed":
        await show_installed(update, ctx)
        return
    
    if data.startswith("run_"):
        tool = data.replace("run_", "")
        
        if tool not in PARROT_TOOLS:
            await query.message.edit_text(f"Unknown: {tool}", parse_mode='HTML')
            return
        
        # Need target
        if chat_id not in user_targets:
            await query.message.edit_text(
                f"Selected: <b>{tool}</b>\n\nEnter target IP or URL:",
                parse_mode='HTML'
            )
            return
        
        # Run
        target = user_targets[chat_id]
        tool_info = PARROT_TOOLS[tool]
        
        await query.message.edit_text(
            f"🔧 Running <b>{tool}</b> ({tool_info['desc']}) on {target}...",
            parse_mode='HTML'
        )
        
        result = runner.run(tool, target)
        
        if len(result) > 3500:
            for i in range(0, len(result), 3500):
                await query.message.reply_text(f"<code>{result[i:i+3500]}</code>", parse_mode='HTML')
        else:
            await query.message.reply_text(f"<code>{result}</code>", parse_mode='HTML')

async def handle_message(update, ctx):
    text = update.message.text.strip()
    chat_id = update.message.chat_id
    user_targets[chat_id] = text
    
    await update.message.reply_text(
        f"Target: <b>{text}</b>\n\nSelect tool:",
        parse_mode='HTML'
    )
    await start(update, ctx)

def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("🕵️ FULL PARROT TOOLKIT BOT")
    print(f"   Tools loaded: {len(PARROT_TOOLS)}")
    print(f"   Installed: {sum(INSTALLED.values())}")
    
    app.run_polling()

if __name__ == '__main__':
    main()