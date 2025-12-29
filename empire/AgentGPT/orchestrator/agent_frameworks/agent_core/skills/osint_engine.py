#!/usr/bin/env python3
"""
AUTO INTEL BOT - OSINT Intelligence Module
Integrates reconnaissance and intelligence gathering capabilities
"""
import sys
import os
import json
import re
import socket
import subprocess
from typing import Dict, List, Any
from datetime import datetime

# Add OSINT path if available
OSINT_PATH = "/home/claude/osint-main"
if os.path.exists(OSINT_PATH):
    sys.path.insert(0, OSINT_PATH)


class OSINTEngine:
    """Intelligence gathering engine using multiple OSINT techniques"""
    
    def __init__(self):
        self.results_cache = {}
        self.osint_available = self._check_osint_availability()
        
        if self.osint_available:
            self._init_osint_modules()
    
    def _check_osint_availability(self) -> bool:
        """Check if OSINT toolkit is available"""
        try:
            from osint import QBDns
            return True
        except ImportError:
            print("⚠️  OSINT toolkit not available, using fallback methods")
            return False
    
    def _init_osint_modules(self):
        """Initialize OSINT modules"""
        try:
            from osint import (QBDns, QBScan, QBHost, QBWhois, 
                             QBTraceRoute, QBPing, QBExtract, QBCached)
            
            self.qbdns = QBDns()
            self.qbscan = QBScan()
            self.qbhost = QBHost()
            self.qbwhois = QBWhois()
            self.qbtraceroute = QBTraceRoute()
            self.qbping = QBPing()
            self.qbextract = QBExtract()
            self.qbcached = QBCached()
            
            print("✅ OSINT modules initialized")
        except Exception as e:
            print(f"⚠️  Error initializing OSINT: {e}")
            self.osint_available = False
    
    def full_recon(self, target: str, ports: List[int] = None) -> Dict:
        """Perform full reconnaissance on target"""
        if ports is None:
            ports = [80, 443, 8080, 8443, 22, 21, 25, 53]
        
        print(f"🔍 Starting full recon on: {target}")
        
        results = {
            "target": target,
            "timestamp": datetime.now().isoformat(),
            "dns": {},
            "ports": {},
            "whois": {},
            "host_info": {},
            "traceroute": {},
            "ping": {}
        }
        
        if self.osint_available:
            results = self._osint_full_recon(target, ports)
        else:
            results = self._fallback_recon(target, ports)
        
        # Cache results
        self.results_cache[target] = results
        
        return results
    
    def _osint_full_recon(self, target: str, ports: List[int]) -> Dict:
        """Full recon using OSINT toolkit"""
        results = {
            "target": target,
            "timestamp": datetime.now().isoformat(),
            "method": "osint_toolkit"
        }
        
        try:
            # DNS resolution
            print("  📡 DNS lookup...")
            targets = self.qbdns.convert_to_ips([target])
            results["dns"] = targets
            
            # Port scanning
            if targets:
                print(f"  🔓 Scanning ports: {ports}")
                targets = self.qbscan.run(targets, ports)
                results["ports"] = targets
                
                # Host information
                print("  🌐 Getting host info...")
                targets = self.qbhost.run(targets)
                results["host_info"] = targets
                
                # WHOIS lookup
                print("  📋 WHOIS lookup...")
                targets = self.qbwhois.run(targets)
                results["whois"] = targets
                
                # Traceroute
                print("  🗺️  Traceroute...")
                targets = self.qbtraceroute.run(targets)
                results["traceroute"] = targets
                
                # Ping
                print("  📶 Ping test...")
                targets = self.qbping.run(targets)
                results["ping"] = targets
            
            print("✅ OSINT recon complete")
            
        except Exception as e:
            print(f"❌ Error during OSINT recon: {e}")
            results["error"] = str(e)
        
        return results
    
    def _fallback_recon(self, target: str, ports: List[int]) -> Dict:
        """Fallback reconnaissance using standard tools"""
        results = {
            "target": target,
            "timestamp": datetime.now().isoformat(),
            "method": "fallback"
        }
        
        # DNS lookup
        results["dns"] = self._fallback_dns(target)
        
        # Basic port scan
        results["ports"] = self._fallback_port_scan(target, ports)
        
        # WHOIS (if available)
        results["whois"] = self._fallback_whois(target)
        
        return results
    
    def _fallback_dns(self, target: str) -> Dict:
        """Fallback DNS lookup"""
        try:
            ip = socket.gethostbyname(target)
            return {
                "target": target,
                "resolved_ip": ip,
                "status": "success"
            }
        except Exception as e:
            return {
                "target": target,
                "status": "failed",
                "error": str(e)
            }
    
    def _fallback_port_scan(self, target: str, ports: List[int]) -> Dict:
        """Simple port connectivity check"""
        open_ports = []
        
        for port in ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex((target, port))
                sock.close()
                
                if result == 0:
                    open_ports.append(port)
                    print(f"    ✓ Port {port} open")
            except:
                pass
        
        return {
            "target": target,
            "open_ports": open_ports,
            "scanned_ports": ports
        }
    
    def _fallback_whois(self, target: str) -> Dict:
        """Fallback WHOIS lookup"""
        try:
            result = subprocess.run(
                ['whois', target],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return {
                    "target": target,
                    "data": result.stdout[:500],  # Truncate
                    "status": "success"
                }
        except:
            pass
        
        return {
            "target": target,
            "status": "unavailable"
        }
    
    def quick_scan(self, target: str) -> Dict:
        """Quick scan - just DNS and common ports"""
        print(f"⚡ Quick scan: {target}")
        
        results = {
            "target": target,
            "timestamp": datetime.now().isoformat(),
            "type": "quick_scan"
        }
        
        # DNS
        results["dns"] = self._fallback_dns(target)
        
        # Quick port check (top 10)
        common_ports = [80, 443, 22, 21, 25, 3389, 3306, 5432, 8080, 8443]
        results["ports"] = self._fallback_port_scan(target, common_ports)
        
        return results
    
    def cached_lookup(self, target: str) -> Dict:
        """Check archive.org for cached pages"""
        if not self.osint_available:
            return {"error": "OSINT toolkit not available"}
        
        try:
            print(f"🗄️  Checking cached pages for: {target}")
            targets = self.qbdns.convert_to_ips([target])
            if targets:
                targets = self.qbcached.run(targets)
                return targets
        except Exception as e:
            return {"error": str(e)}
        
        return {}
    
    def extract_web_content(self, target: str) -> Dict:
        """Extract content from web target"""
        if not self.osint_available:
            return {"error": "OSINT toolkit not available"}
        
        try:
            print(f"📄 Extracting content from: {target}")
            targets = self.qbdns.convert_to_ips([target])
            if targets:
                targets = self.qbhost.run(targets)
                targets = self.qbextract.run(targets, function="all")
                return targets
        except Exception as e:
            return {"error": str(e)}
        
        return {}
    
    def get_cached_results(self, target: str) -> Dict:
        """Get cached results for a target"""
        return self.results_cache.get(target, {})
    
    def clear_cache(self):
        """Clear results cache"""
        self.results_cache = {}
        print("🗑️  Cache cleared")


class ThreatAnalyzer:
    """Analyze reconnaissance data for threats and patterns"""
    
    def __init__(self):
        self.threat_patterns = self._load_threat_patterns()
    
    def _load_threat_patterns(self) -> Dict:
        """Load known threat patterns"""
        return {
            "suspicious_ports": [4444, 5555, 6666, 31337, 12345],
            "dangerous_services": ["telnet", "ftp", "rsh"],
            "common_exploits": {
                22: "SSH brute force",
                3389: "RDP exploits",
                445: "SMB vulnerabilities"
            }
        }
    
    def analyze(self, recon_data: Dict) -> Dict:
        """Analyze reconnaissance data"""
        threats = []
        risk_score = 0
        
        # Check for suspicious open ports
        if "ports" in recon_data and "open_ports" in recon_data["ports"]:
            open_ports = recon_data["ports"]["open_ports"]
            
            for port in open_ports:
                if port in self.threat_patterns["suspicious_ports"]:
                    threats.append({
                        "type": "suspicious_port",
                        "port": port,
                        "severity": "high"
                    })
                    risk_score += 3
                
                if port in self.threat_patterns["common_exploits"]:
                    threats.append({
                        "type": "exploitable_service",
                        "port": port,
                        "exploit": self.threat_patterns["common_exploits"][port],
                        "severity": "medium"
                    })
                    risk_score += 2
        
        return {
            "threats": threats,
            "risk_score": risk_score,
            "risk_level": self._get_risk_level(risk_score),
            "timestamp": datetime.now().isoformat()
        }
    
    def _get_risk_level(self, score: int) -> str:
        """Determine risk level from score"""
        if score == 0:
            return "minimal"
        elif score < 5:
            return "low"
        elif score < 10:
            return "medium"
        else:
            return "high"


if __name__ == "__main__":
    print("🔍 Initializing OSINT Engine...")
    engine = OSINTEngine()
    analyzer = ThreatAnalyzer()
    
    # Test with a target
    test_target = "scanme.nmap.org"  # Safe scanning target
    
    print(f"\n🎯 Testing quick scan on: {test_target}")
    results = engine.quick_scan(test_target)
    
    print(f"\n📊 Results:")
    print(json.dumps(results, indent=2))
    
    print(f"\n🛡️  Threat Analysis:")
    threats = analyzer.analyze(results)
    print(json.dumps(threats, indent=2))
