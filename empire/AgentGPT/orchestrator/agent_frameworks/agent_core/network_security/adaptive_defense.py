#!/usr/bin/env python3
"""
Network Security Module
Honeypots, Port Forwarding, Sandboxing with AI-driven adaptive defense
"""

import socket
import threading
import time
import json
import hashlib
from typing import Dict, List, Set, Callable, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import queue
import random


@dataclass
class ConnectionAttempt:
    """Record of a connection attempt"""
    source_ip: str
    source_port: int
    target_port: int
    timestamp: float
    protocol: str
    payload_snippet: bytes
    threat_score: int = 0
    
    def to_dict(self):
        return {
            **asdict(self),
            'payload_snippet': self.payload_snippet.hex()
        }


@dataclass
class PortConfig:
    """Configuration for a port"""
    port: int
    is_honeypot: bool
    real_backend: Optional[Tuple[str, int]]  # (host, port) if forwarding
    sandbox_enabled: bool
    service_banner: str


class ThreatAnalyzer:
    """Analyze connection attempts for threats"""
    
    # Known malicious patterns
    SUSPICIOUS_PATTERNS = [
        b'SELECT', b'UNION', b'DROP TABLE',  # SQL injection
        b'<script>', b'javascript:', b'onerror=',  # XSS
        b'../../../', b'..\\..\\..\\',  # Path traversal
        b'eval(', b'exec(', b'system(',  # Code injection
        b'{{', b'${',  # Template injection
        b'\x00',  # Null byte injection
    ]
    
    SCAN_SIGNATURES = [
        b'nmap', b'masscan', b'zmap',
        b'User-Agent: Mozilla/5.00',  # Default scanner UA
    ]
    
    def __init__(self):
        self.ip_attempt_counts: Dict[str, int] = {}
        self.ip_threat_scores: Dict[str, int] = {}
        
    def analyze_connection(self, attempt: ConnectionAttempt) -> int:
        """
        Analyze connection attempt and return threat score (0-100)
        """
        score = 0
        
        # Track attempts per IP
        self.ip_attempt_counts[attempt.source_ip] = \
            self.ip_attempt_counts.get(attempt.source_ip, 0) + 1
        
        # Rapid connection attempts
        if self.ip_attempt_counts[attempt.source_ip] > 10:
            score += 20
        if self.ip_attempt_counts[attempt.source_ip] > 50:
            score += 30
        
        # Check payload for malicious patterns
        payload_lower = attempt.payload_snippet.lower()
        for pattern in self.SUSPICIOUS_PATTERNS:
            if pattern.lower() in payload_lower:
                score += 15
        
        # Check for scanner signatures
        for signature in self.SCAN_SIGNATURES:
            if signature.lower() in payload_lower:
                score += 25
        
        # Port scanning behavior (multiple ports from same IP)
        # Would need state tracking across ports
        
        # Update and return
        self.ip_threat_scores[attempt.source_ip] = max(
            self.ip_threat_scores.get(attempt.source_ip, 0),
            score
        )
        
        return min(100, score)
    
    def is_blocked(self, ip: str) -> bool:
        """Check if IP should be blocked"""
        return self.ip_threat_scores.get(ip, 0) > 70
    
    def get_threat_report(self) -> Dict:
        """Generate threat report"""
        return {
            "total_ips": len(self.ip_attempt_counts),
            "blocked_ips": len([ip for ip, score in self.ip_threat_scores.items() if score > 70]),
            "high_threat_ips": [
                {"ip": ip, "score": score}
                for ip, score in sorted(self.ip_threat_scores.items(), 
                                       key=lambda x: x[1], reverse=True)[:10]
            ],
            "total_attempts": sum(self.ip_attempt_counts.values())
        }


class Sandbox:
    """Isolated execution environment for suspicious connections"""
    
    def __init__(self, name: str):
        self.name = name
        self.active = True
        self.contained_ips: Set[str] = set()
        self.interaction_log: List[Dict] = []
        
    def contain_connection(self, connection: ConnectionAttempt):
        """Route connection to sandbox"""
        self.contained_ips.add(connection.source_ip)
        self.interaction_log.append({
            "timestamp": datetime.now().isoformat(),
            "source": connection.source_ip,
            "action": "contained",
            "details": connection.to_dict()
        })
        
    def get_fake_response(self, request: bytes) -> bytes:
        """Generate fake response to keep attacker engaged"""
        # Simulate realistic but fake service
        responses = [
            b"HTTP/1.1 200 OK\r\nServer: Apache/2.4.41\r\n\r\n<html><body>Welcome</body></html>",
            b"SSH-2.0-OpenSSH_7.9\r\n",
            b"220 mail.example.com ESMTP Postfix\r\n",
            b"MySQL Server Error: Access Denied\r\n"
        ]
        return random.choice(responses)
    
    def analyze_behavior(self) -> Dict:
        """Analyze attacker behavior in sandbox"""
        return {
            "sandbox": self.name,
            "contained_ips": list(self.contained_ips),
            "interaction_count": len(self.interaction_log),
            "latest_interactions": self.interaction_log[-5:]
        }


class HoneypotService:
    """Honeypot service that mimics real service"""
    
    def __init__(self, port: int, service_type: str):
        self.port = port
        self.service_type = service_type
        self.interactions: List[ConnectionAttempt] = []
        
    def get_banner(self) -> bytes:
        """Get service banner"""
        banners = {
            "ssh": b"SSH-2.0-OpenSSH_8.2p1 Ubuntu-4ubuntu0.1\r\n",
            "http": b"HTTP/1.1 200 OK\r\nServer: nginx/1.18.0\r\n\r\n",
            "ftp": b"220 ProFTPD Server (ProFTPD) [::ffff:192.168.1.1]\r\n",
            "smtp": b"220 mail.example.com ESMTP Postfix\r\n",
            "mysql": b"\x4a\x00\x00\x00\x0a" + b"5.7.33-0ubuntu0.18.04.1" + b"\x00",
        }
        return banners.get(self.service_type, b"220 Service Ready\r\n")
    
    def handle_interaction(self, data: bytes, source_ip: str, source_port: int) -> bytes:
        """Handle honeypot interaction and log"""
        attempt = ConnectionAttempt(
            source_ip=source_ip,
            source_port=source_port,
            target_port=self.port,
            timestamp=time.time(),
            protocol=self.service_type,
            payload_snippet=data[:500]
        )
        self.interactions.append(attempt)
        
        # Return service-appropriate response
        return self.get_banner()


class PortForwarder:
    """Forward connections with optional filtering"""
    
    def __init__(self, listen_port: int, backend_host: str, backend_port: int):
        self.listen_port = listen_port
        self.backend_host = backend_host
        self.backend_port = backend_port
        self.active_forwards: List[threading.Thread] = []
        
    def forward_connection(self, client_socket: socket.socket, client_addr: Tuple):
        """Forward connection to backend"""
        try:
            # Connect to backend
            backend = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            backend.connect((self.backend_host, self.backend_port))
            
            # Bidirectional forwarding
            def forward_data(source: socket.socket, destination: socket.socket):
                try:
                    while True:
                        data = source.recv(4096)
                        if not data:
                            break
                        destination.sendall(data)
                except:
                    pass
                finally:
                    source.close()
                    destination.close()
            
            # Start forwarding threads
            t1 = threading.Thread(target=forward_data, args=(client_socket, backend))
            t2 = threading.Thread(target=forward_data, args=(backend, client_socket))
            
            t1.start()
            t2.start()
            
            self.active_forwards.append(t1)
            self.active_forwards.append(t2)
            
        except Exception as e:
            print(f"Forward error: {e}")
            client_socket.close()


class AdaptiveNetworkDefense:
    """
    AI-driven adaptive network defense system
    Manages honeypots, port forwarding, and sandboxing
    """
    
    def __init__(self):
        self.port_configs: Dict[int, PortConfig] = {}
        self.honeypots: Dict[int, HoneypotService] = {}
        self.sandboxes: List[Sandbox] = []
        self.forwarders: Dict[int, PortForwarder] = {}
        self.threat_analyzer = ThreatAnalyzer()
        self.running = False
        self.servers: List[socket.socket] = []
        
    def configure_port(self, config: PortConfig):
        """Configure a port as honeypot, forwarder, or sandboxed"""
        self.port_configs[config.port] = config
        
        if config.is_honeypot:
            service_type = config.service_banner.split()[0].lower()
            self.honeypots[config.port] = HoneypotService(config.port, service_type)
        
        if config.real_backend:
            self.forwarders[config.port] = PortForwarder(
                config.port,
                config.real_backend[0],
                config.real_backend[1]
            )
    
    def create_sandbox(self, name: str) -> Sandbox:
        """Create a new sandbox"""
        sandbox = Sandbox(name)
        self.sandboxes.append(sandbox)
        return sandbox
    
    def handle_connection(self, client_socket: socket.socket, client_addr: Tuple, port: int):
        """Handle incoming connection based on port configuration"""
        source_ip, source_port = client_addr
        
        # Initial data peek
        try:
            client_socket.settimeout(2.0)
            initial_data = client_socket.recv(1024, socket.MSG_PEEK)
        except:
            initial_data = b""
        
        # Create connection attempt record
        attempt = ConnectionAttempt(
            source_ip=source_ip,
            source_port=source_port,
            target_port=port,
            timestamp=time.time(),
            protocol="tcp",
            payload_snippet=initial_data[:500]
        )
        
        # Analyze threat
        threat_score = self.threat_analyzer.analyze_connection(attempt)
        attempt.threat_score = threat_score
        
        config = self.port_configs.get(port)
        
        # Blocked IP
        if self.threat_analyzer.is_blocked(source_ip):
            client_socket.close()
            return
        
        # High threat - route to sandbox
        if threat_score > 60 or (config and config.sandbox_enabled):
            sandbox = self.sandboxes[0] if self.sandboxes else self.create_sandbox("auto-sandbox-1")
            sandbox.contain_connection(attempt)
            
            # Send fake response
            try:
                fake_response = sandbox.get_fake_response(initial_data)
                client_socket.sendall(fake_response)
                time.sleep(0.5)
            except:
                pass
            client_socket.close()
            return
        
        # Honeypot
        if config and config.is_honeypot:
            honeypot = self.honeypots[port]
            try:
                data = client_socket.recv(4096)
                response = honeypot.handle_interaction(data, source_ip, source_port)
                client_socket.sendall(response)
                time.sleep(0.5)
            except:
                pass
            client_socket.close()
            return
        
        # Forward to real backend
        if config and config.real_backend:
            forwarder = self.forwarders[port]
            forwarder.forward_connection(client_socket, client_addr)
            return
        
        # Default: close
        client_socket.close()
    
    def start_listener(self, port: int):
        """Start listener for a port"""
        try:
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind(('0.0.0.0', port))
            server.listen(5)
            server.settimeout(1.0)  # Non-blocking
            self.servers.append(server)
            
            print(f"Listening on port {port} - {self.port_configs[port].service_banner}")
            
            while self.running:
                try:
                    client_socket, client_addr = server.accept()
                    # Handle in thread
                    t = threading.Thread(
                        target=self.handle_connection,
                        args=(client_socket, client_addr, port)
                    )
                    t.daemon = True
                    t.start()
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        print(f"Error on port {port}: {e}")
                    break
                    
        except Exception as e:
            print(f"Failed to start listener on port {port}: {e}")
    
    def start(self):
        """Start all configured listeners"""
        self.running = True
        
        threads = []
        for port in self.port_configs:
            t = threading.Thread(target=self.start_listener, args=(port,))
            t.daemon = True
            t.start()
            threads.append(t)
        
        return threads
    
    def stop(self):
        """Stop all listeners"""
        self.running = False
        for server in self.servers:
            try:
                server.close()
            except:
                pass
    
    def get_status_report(self) -> Dict:
        """Get comprehensive status report"""
        return {
            "timestamp": datetime.now().isoformat(),
            "active_ports": list(self.port_configs.keys()),
            "honeypot_ports": [p for p, c in self.port_configs.items() if c.is_honeypot],
            "forwarded_ports": [p for p in self.forwarders.keys()],
            "sandboxes": [s.analyze_behavior() for s in self.sandboxes],
            "threat_analysis": self.threat_analyzer.get_threat_report(),
            "honeypot_interactions": {
                port: len(hp.interactions)
                for port, hp in self.honeypots.items()
            }
        }


def demo():
    """Demo the adaptive network defense system"""
    print("=== Adaptive Network Defense System Demo ===\n")
    
    defense = AdaptiveNetworkDefense()
    
    # Configure ports
    print("Configuring defense topology...")
    
    # Honeypot SSH on 2222
    defense.configure_port(PortConfig(
        port=2222,
        is_honeypot=True,
        real_backend=None,
        sandbox_enabled=False,
        service_banner="SSH OpenSSH_8.2"
    ))
    
    # Honeypot HTTP on 8080
    defense.configure_port(PortConfig(
        port=8080,
        is_honeypot=True,
        real_backend=None,
        sandbox_enabled=False,
        service_banner="HTTP nginx/1.18"
    ))
    
    # Sandboxed MySQL on 3306
    defense.configure_port(PortConfig(
        port=3306,
        is_honeypot=False,
        real_backend=None,
        sandbox_enabled=True,
        service_banner="MySQL 5.7"
    ))
    
    # Create sandbox
    defense.create_sandbox("main-sandbox")
    
    print("Defense system configured!")
    print(f"Honeypot ports: 2222 (SSH), 8080 (HTTP)")
    print(f"Sandboxed ports: 3306 (MySQL)")
    print("\nIn production, start with: defense.start()")
    print("This demo shows configuration only (not starting listeners)")
    
    # Simulate some connection attempts for analysis
    print("\nSimulating threat analysis...")
    
    test_attempts = [
        ConnectionAttempt("192.168.1.100", 54321, 2222, time.time(), "tcp", b"SSH-2.0-client"),
        ConnectionAttempt("10.0.0.50", 12345, 8080, time.time(), "tcp", 
                         b"GET /../../../etc/passwd HTTP/1.1"),
        ConnectionAttempt("10.0.0.50", 12346, 3306, time.time(), "tcp",
                         b"SELECT * FROM users WHERE id=1 OR 1=1"),
    ]
    
    for attempt in test_attempts:
        score = defense.threat_analyzer.analyze_connection(attempt)
        print(f"  {attempt.source_ip}:{attempt.source_port} → :{attempt.target_port} "
              f"[Threat: {score}]")
    
    print("\nThreat Report:")
    report = defense.get_status_report()
    print(json.dumps(report["threat_analysis"], indent=2))


if __name__ == "__main__":
    demo()
