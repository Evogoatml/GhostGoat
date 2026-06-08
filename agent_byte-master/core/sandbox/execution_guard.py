"""GhostGoat Execution Guard — Sandbox + Approval Gates."""
import asyncio, json, logging, os, re, subprocess, time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DANGEROUS_PATTERNS = [
    re.compile(r"rm\s+-rf\s+/"),
    re.compile(r"dd\s+if=.*of=/dev/"),
    re.compile(r"mkfs\."),
    re.compile(r":(){:|:&};:"),
    re.compile(r"DROP\s+TABLE"),
    re.compile(r"DELETE\s+FROM"),
    re.compile(r"shutdown\s+-h?"),
    re.compile(r"iptables\s+-F"),
    re.compile(r">\s*/dev/sd[a-z]"),
]

HIGH_RISK_TOOLS = {"nmap", "sqlmap", "metasploit", "msfconsole"}

@dataclass
class ApprovalRequest:
    req_id: str
    timestamp: float
    command: str
    risk_level: str
    reason_for_request: str
    approved: Optional[bool] = None
    approved_by: Optional[str] = None
    approved_at: Optional[float] = None

class ExecutionGuard:
    def __init__(self, auto_approve_low: bool = True, require_approval_above: str = "high"):
        self.auto_approve_low = auto_approve_low
        self.require_above = require_approval_above
        self.approval_queue: List[ApprovalRequest] = []
        self.history: List[ApprovalRequest] = []

    def scan(self, command: str, tool_name: Optional[str] = "") -> Dict[str, Any]:
        risk = "low"
        flags = []
        for pat in DANGEROUS_PATTERNS:
            if pat.search(command):
                risk = "critical"
                flags.append(f"matched_dangerous_pattern:{pat.pattern[:20]}")
        if tool_name and tool_name.lower() in HIGH_RISK_TOOLS:
            risk = "high" if risk == "low" else risk
            flags.append(f"high_risk_tool:{tool_name}")
        if "-sn" in command or "10.0.0.0/8" in command or "192.168.0.0/16" in command:
            risk = "high" if risk in ("low", "medium") else risk
            flags.append("broad_network_scope")
        if ">" in command or "| tee" in command:
            risk = "medium" if risk == "low" else risk
            flags.append("file_write_side_effect")
        return {"risk": risk, "flags": flags, "blocked": risk == "critical", "requires_approval": risk in ("high", "critical")}

    def request_approval(self, command: str, reason: str = "") -> str:
        result = self.scan(command)
        req = ApprovalRequest(
            req_id=f"req-{int(time.time() * 1000)}",
            timestamp=time.time(),
            command=command,
            risk_level=result["risk"],
            reason_for_request=reason or f"Auto-detected risk: {result['flags']}"
        )
        if result["blocked"]:
            self.history.append(req)
            raise PermissionError(f"Command blocked: {result['flags']}")
        if result["risk"] in ("low", "medium") and self.auto_approve_low:
            req.approved = True
            req.approved_by = "auto"
            req.approved_at = time.time()
            self.history.append(req)
            return req.req_id
        self.approval_queue.append(req)
        logger.warning("Approval required for command: %s", command[:80])
        return req.req_id

    def approve(self, req_id: str, approver: str = "human") -> bool:
        for req in self.approval_queue:
            if req.req_id == req_id:
                req.approved = True
                req.approved_by = approver
                req.approved_at = time.time()
                self.approval_queue.remove(req)
                self.history.append(req)
                logger.info("Approved %s by %s", req_id, approver)
                return True
        return False

    def sandbox_exec(self, command: List[str], timeout: int = 30, cwd: Optional[str] = None) -> Dict[str, Any]:
        cmd_str = " ".join(command)
        req_id = self.request_approval(cmd_str, reason="sandbox_exec")
        req = next((r for r in self.history if r.req_id == req_id), None)
        if req and req.approved is not True:
            return {"success": False, "error": f"Approval pending: {req_id}"}
        try:
            env = os.environ.copy()
            env["PATH"] = "/usr/bin:/bin"
            proc = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd,
                env=env,
            )
            return {
                "success": proc.returncode == 0,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "returncode": proc.returncode,
                "req_id": req_id,
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Timeout", "req_id": req_id}
        except Exception as e:
            return {"success": False, "error": str(e), "req_id": req_id}

