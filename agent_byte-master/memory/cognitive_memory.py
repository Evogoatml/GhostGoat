#!/usr/bin/env python3
"""
Cognitive Memory System - Learns from each interaction
"""

import json
import os
from pathlib import Path
from datetime import datetime
from collections import defaultdict

class CognitiveMemory:
    """The bot learns from every interaction"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.memory_file = Path(f"~/.pentest_bot/memory_{user_id}.json").expanduser()
        self.memory_file.parent.mkdir(exist_ok=True)
        
        self.data = self._load()
    
    def _load(self) -> dict:
        if self.memory_file.exists():
            try:
                return json.loads(self.memory_file.read_text())
            except:
                pass
        
        return {
            "targets_scanned": [],           # History of targets
            "findings": [],                   # Vulnerabilities found
            "techniques_used": [],          # What actually worked
            "lessons": [],                    # Things user learned
            "patterns": {},                   # Target patterns (IPs, tech)
            "preferred_tools": {},            # Tool success rates
            "last_scan": None,
            "total_scans": 0,
        }
    
    def _save(self):
        self.memory_file.write_text(json.dumps(self.data, indent=2))
    
    # Learning functions
    def record_scan(self, target: str, tool: str, result: str):
        """Record a scan - learns what works"""
        timestamp = datetime.now().isoformat()
        
        # Record target
        if target not in self.data["targets_scanned"]:
            self.data["targets_scanned"].append(target)
        
        # Check for findings
        findings = []
        result_lower = result.lower()
        
        if any(x in result_lower for x in ["vulnerability", "cve-", "exploit", "open port", "interesting"]):
            findings.append({
                "target": target,
                "tool": tool,
                "timestamp": timestamp,
                "snippet": result[:200]
            })
            self.data["findings"].append(findings[-1])
        
        # Record technique
        if tool not in self.data["techniques_used"]:
            self.data["techniques_used"].append(tool)
        
        # Build target patterns
        if "." in target:
            # Extract IP or domain pattern
            parts = target.replace("http://", "").replace("https://", "").split(".")
            if len(parts) >= 2:
                domain = parts[-2] + "." + parts[-1]
                if domain not in self.data["patterns"]:
                    self.data["patterns"][domain] = {"scans": 0, "last": None}
                self.data["patterns"][domain]["scans"] += 1
                self.data["patterns"][domain]["last"] = timestamp
        
        self.data["last_scan"] = {
            "target": target,
            "tool": tool,
            "timestamp": timestamp
        }
        self.data["total_scans"] = self.data.get("total_scans", 0) + 1
        
        self._save()
        
        return {
            "scans": self.data["total_scans"],
            "findings": len(self.data["findings"])
        }
    
    def record_lesson(self, topic: str, understanding: str):
        """User learns something - record it"""
        self.data["lessons"].append({
            "topic": topic,
            "note": understanding,
            "timestamp": datetime.now().isoformat()
        })
        self._save()
    
    def get_insights(self) -> str:
        """Give cognitive insights"""
        insights = []
        
        # What worked best
        if self.data["total_scans"] > 0:
            insights.append(f"🔍 You've run {self.data['total_scans']} scans")
        
        # Findings
        if self.data["findings"]:
            insights.append(f"💎 Found {len(self.data['findings'])} interesting results")
        
        # Targets
        if self.data["targets_scanned"]:
            recent = self.data["targets_scanned"][-3:]
            insights.append(f"📱 Recent: {', '.join(recent)}")
        
        # Patterns
        if self.data["patterns"]:
            top = sorted(self.data["patterns"].items(), 
                        key=lambda x: x[1]["scans"], reverse=True)[:2]
            patterns = ", ".join([f"{k}({v['scans']})" for k, v in top])
            insights.append(f"🔗 Patterns: {patterns}")
        
        return "\n".join(insights) if insights else "No memory yet. Start scanning!"
    
    def get_preferred_tool(self) -> str:
        """Which tool works best for this user"""
        # Could build preference based on success
        return "nmap"  # Default
    
    def recall_target(self, search: str = None) -> list:
        """Recall targets matching pattern"""
        if not search:
            return self.data["targets_scanned"][-10:]
        
        search = search.lower()
        return [t for t in self.data["targets_scanned"] 
                if search in t.lower()]

# Global memory store per user
user_memories = {}

def get_memory(user_id: str) -> CognitiveMemory:
    if user_id not in user_memories:
        user_memories[user_id] = CognitiveMemory(user_id)
    return user_memories[user_id]

# Test
if __name__ == "__main__":
    # Demo
    mem = get_memory("test_user")
    
    # Simulate some learning
    mem.record_scan("192.168.1.1", "nmap", "Found open port 22 and some interesting HTTP headers")
    mem.record_scan("10.0.0.5", "nikto", "Some vulnerabilities found")
    mem.record_scan("api.target.com", "sqlmap", "Parameter returns database error - possible SQLi")
    
    print("=== COGNITIVE MEMORY ===")
    print(mem.get_insights())
    print()
    print("=== RECALL ===")
    print(mem.recall_target())