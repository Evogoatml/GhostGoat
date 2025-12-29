# modules/governance/decision_governor.py
"""
Decision Governor — controls subsystem autonomy.
"""

import os, configparser, time

POLICY_FILE = "mission.policy"

def load_policy():
    cfg = configparser.ConfigParser()
    if not os.path.exists(POLICY_FILE):
        print(f"[GOV] Policy file missing: {POLICY_FILE}")
        return {}
    cfg.read(POLICY_FILE)
    return {section: dict(cfg[section]) for section in cfg.sections()}

def can_execute(domain):
    """Checks whether subsystem can run autonomously per policy."""
    policy = load_policy()
    mode = policy.get("systems", {}).get(domain, "ask").lower()

    if mode == "auto":
        print(f"[GOV] {domain} granted autonomous execution.")
        return True
    elif mode == "deny":
        print(f"[GOV] {domain} execution denied by policy.")
        return False
    elif mode == "ask":
        print(f"[GOV] {domain} requires operator approval.")
        return confirm_action(domain)
    else:
        print(f"[GOV] Unknown policy mode '{mode}' for {domain}. Defaulting to ask.")
        return confirm_action(domain)

def confirm_action(domain):
    resp = input(f"⚠️ Approve action for subsystem '{domain}'? [y/N]: ").strip().lower()
    if resp == "y":
        print(f"[GOV] Approval granted for {domain}.")
        audit_governor_log(domain, "approved")
        return True
    else:
        print(f"[GOV] Action for {domain} declined.")
        audit_governor_log(domain, "declined")
        return False

def audit_governor_log(domain, result):
    os.makedirs("audit", exist_ok=True)
    with open("audit/governor_audit.log", "a") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} | {domain} | {result}\n")

def enforce(domain, func, *args, **kwargs):
    """Decorator-like wrapper for enforcing policy."""
    allowed = can_execute(domain)
    audit_governor_log(domain, "allowed" if allowed else "blocked")
    if allowed:
        return func(*args, **kwargs)
    return None

# in decision_governor.py
def allow_external_calls(context="diagnostic"):
    if context in ["diagnostic", "repair"]:
        return True  # Allowed only during self-repair or system update
    return False
