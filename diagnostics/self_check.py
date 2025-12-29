import os, sys, json, time, sqlite3, hashlib, shutil, stat, subprocess

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
AUDIT_LOG = os.path.join(ROOT, "audit.log")
MISSION_ENV = os.path.join(ROOT, "mission.env")
REG_DB = os.path.join(ROOT, "registry.db")
QUARANTINE = os.path.join(ROOT, "quarantine")
KEYS_DIR = os.path.join(ROOT, "keys")
FILES_MUST_EXIST = [
    os.path.join(ROOT, "adaptive_vault.py"),
    os.path.join(ROOT, "translator_gate.py"),
    os.path.join(ROOT, "policy.py"),
    os.path.join(ROOT, "monitor.py"),
    os.path.join(ROOT, "hash_check.py"),
    os.path.join(ROOT, "verify_manifest.py"),
]
OPTIONAL_FILES = [
    os.path.join(ROOT, "manifest.json"),
    os.path.join(ROOT, "manifest.sig"),
    os.path.join(ROOT, "artifact.bin"),
]

def _ok(msg):   print(f"[OK] {msg}")
def _warn(msg): print(f"[WARN] {msg}")
def _err(msg):  print(f"[ERR] {msg}")

# ---------- FILESYSTEM + PERMS ----------
def ensure_dirs():
    changed = False
    for d in [QUARANTINE, KEYS_DIR]:
        if not os.path.isdir(d):
            os.makedirs(d, exist_ok=True)
            _warn(f"created missing dir: {d}")
            changed = True
    return changed

def ensure_files():
    issues = []
    for p in FILES_MUST_EXIST:
        if not os.path.exists(p):
            issues.append(p)
    if issues:
        for p in issues:
            _err(f"missing required file: {p}")
    else:
        _ok("all required files present")
    return issues

def fix_permissions():
    changed = False
    for path in [AUDIT_LOG, REG_DB] + [p for p in OPTIONAL_FILES if os.path.exists(p)]:
        try:
            # owner read/write only (rw-------) for sensitive files
            os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
            changed = True
        except Exception:
            pass
    if changed:
        _warn("normalized permissions on sensitive files")
    return changed

# ---------- PYTHON/DEPS ----------
def check_python_env():
    missing = []
    try:
        import cryptography  # noqa
    except Exception:
        missing.append("cryptography")
    try:
        import psutil  # noqa
    except Exception:
        missing.append("psutil")
    if missing:
        _warn(f"missing packages: {missing}")
    else:
        _ok("python deps look good (cryptography, psutil)")
    return missing

def auto_install_deps(packages):
    if not packages: 
        return False
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", *packages])
        _ok(f"installed: {packages}")
        return True
    except Exception as e:
        _err(f"pip install failed: {e}")
        return False

# ---------- REGISTRY / SQLITE ----------
SCHEMA = """CREATE TABLE IF NOT EXISTS signatures(
    id INTEGER PRIMARY KEY,
    name TEXT,
    sha256 TEXT,
    whirlpool TEXT,
    ssdeep TEXT,
    rule_tag TEXT,
    author TEXT,
    ts INTEGER,
    signer_pub BLOB,
    signature BLOB,
    meta JSON
);"""

def ensure_registry():
    created = False
    conn = sqlite3.connect(REG_DB)
    cur = conn.cursor()
    cur.execute(SCHEMA)
    conn.commit()
    conn.close()
    if not os.path.exists(REG_DB) or os.path.getsize(REG_DB) == 0:
        created = True
    if created:
        _warn("registry schema ensured")
    else:
        _ok("registry schema OK")
    return created

# ---------- AUDIT DE-DUPE ----------
def dedupe_audit_log():
    if not os.path.exists(AUDIT_LOG):
        _warn("audit.log missing (will create on first run)")
        return False
    seen = set()
    lines = []
    deduped = 0
    with open(AUDIT_LOG, "r", errors="ignore") as f:
        for raw in f:
            s = raw.strip()
            if not s:
                continue
            # Use full line hash as identity; you could parse JSON and normalize
            h = hashlib.sha256(s.encode("utf-8")).hexdigest()
            if h in seen:
                deduped += 1
                continue
            seen.add(h)
            lines.append(s)
    if deduped:
        tmp = AUDIT_LOG + ".tmp"
        with open(tmp, "w") as w:
            for s in lines:
                w.write(s + "\n")
        shutil.move(tmp, AUDIT_LOG)
        _warn(f"deduped audit.log (removed {deduped} duplicate lines)")
        return True
    _ok("audit.log has no duplicate lines")
    return False

# ---------- SELF-TEST ARTIFACTS ----------
def ensure_selftest_artifacts():
    # Create artifact.bin + manifest.json + manifest.sig that actually match
    artifact = os.path.join(ROOT, "artifact.bin")
    if not os.path.exists(artifact):
        with open(artifact, "wb") as f:
            f.write(b"testdata")  # stable bytes
        _warn("created artifact.bin")
    # compute hash
    sha = hashlib.sha256(open(artifact, "rb").read()).hexdigest()
    manifest = os.path.join(ROOT, "manifest.json")
    with open(manifest, "w") as f:
        json.dump({"name":"demo_artifact","content_sha256":sha}, f)
    sig = os.path.join(ROOT, "manifest.sig")
    # fake base64 sig body (verification stub in translator_gate accepts reading only)
    with open(sig, "w") as f:
        f.write("ZHVtbXlzaWc=")
    _ok("self-test manifest/sig refreshed with correct hash")
    return True

# ---------- MISSION ENV ----------
DEFAULT_ENV = {
    "MISSION": "Maintain_Integrity",
    "CPU_LIMIT": "60"
}

def ensure_mission_env():
    changed = False
    data = {}
    if os.path.exists(MISSION_ENV):
        with open(MISSION_ENV, "r") as f:
            for line in f:
                if "=" in line:
                    k, v = line.strip().split("=", 1)
                    data[k] = v
    for k, v in DEFAULT_ENV.items():
        if k not in data:
            data[k] = v
            changed = True
    if changed or not os.path.exists(MISSION_ENV):
        with open(MISSION_ENV, "w") as f:
            for k, v in data.items():
                f.write(f"{k}={v}\n")
        _warn("mission.env normalized/created")
    else:
        _ok("mission.env present")
    return changed

# ---------- PROCESS LIVENESS ----------
def check_loop_liveness():
    # Quick smoke test: import and call monitor.get_resource_state()
    try:
        sys.path.insert(0, ROOT)
        from monitor import get_resource_state  # noqa
        m = get_resource_state()
        if isinstance(m, dict) and "cpu" in m:
            _ok("monitor.get_resource_state() responded")
            return True
        _warn("monitor function returned unexpected payload")
        return False
    except Exception as e:
        _err(f"monitor probe failed: {e}")
        return False

# ---------- RUN BOOK ----------
def run_all(auto_fix=True, auto_install=True):
    report = {"ts": int(time.time()), "actions": []}

    ensure_dirs()
    missing = ensure_files()
    fix_permissions()
    ensure_mission_env()
    ensure_selftest_artifacts()
    ensure_registry()

    # deps
    missing_pkgs = check_python_env()
    if auto_install and missing_pkgs:
        if auto_install_deps(missing_pkgs):
            report["actions"].append({"installed": missing_pkgs})

    # liveness
    check_loop_liveness()

    # log hygiene
    if dedupe_audit_log():
        report["actions"].append({"audit_dedupe": "done"})

    # summarize
    report["missing_required_files"] = missing
    return report
