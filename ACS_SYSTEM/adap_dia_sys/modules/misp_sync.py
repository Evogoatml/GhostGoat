# misp_sync.py
import sqlite3, time, json
from pymisp import PyMISP

# CONFIG: your MISP server + key
MISP_URL = "https://misp.example.local"   # or public instance
MISP_KEY = "YOUR_MISP_API_KEY"
VERIFY = False  # verify TLS certs? set True in prod

# Local DB path (same schema as registry.db earlier)
DB = "registry.db"

misp = PyMISP(MISP_URL, MISP_KEY, ssl=VERIFY)

def init_db():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS signatures(
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
    )""")
    conn.commit(); conn.close()

def upsert_hash(name, sha256, author="misp", meta=None):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT id FROM signatures WHERE sha256=?", (sha256,))
    if cur.fetchone():
        conn.close(); return False
    # create a lightweight meta entry (signed by you later via registry_cli)
    cur.execute("INSERT INTO signatures(name,sha256,author,ts,meta) VALUES(?,?,?,?,?)",
                (name, sha256, author, int(time.time()), json.dumps(meta or {})))
    conn.commit(); conn.close()
    return True

def sync_events(days=1):
    init_db()
    since = (time.time() - days*86400)
    # Pull events modified in last N days
    events = misp.search(timestamp=int(since))
    print(f"[SYNC] fetched {len(events)} events")
    for ev in events:
        # each event may have multiple attributes
        for attr in ev.get('Event', {}).get('Attribute', []):
            atype = attr.get('type')
            value = attr.get('value')
            if atype in ("sha256","md5","sha1"):
                print("[SYNC] adding hash", value)
                upsert_hash(ev['Event'].get('info','misp-event'), value, author="misp")
            # capture YARA rules or yara signature text
            if atype == "yara":
                # store as a rule_tag/meta for later mapping
                name = ev['Event'].get('info','misp-event')
                upsert_hash(name, None, author="misp", meta={"yara": value})
    print("[SYNC] done")

if __name__ == "__main__":
    sync_events(days=7)
