# stix_sync.py
from taxii2client.v20 import Server
from stix2 import parse
import sqlite3, json, time

DB = "registry.db"
TAXII_URL = "https://cti-taxii.mitre.org/taxii/"
COLLECTION_NAME = "enterprise-attack"   # pick the collection you want

def init_db():
    conn = sqlite3.connect(DB)
    conn.execute("""CREATE TABLE IF NOT EXISTS signatures(
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

def upsert(name, sha256=None, rule_tag=None, meta=None):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT id FROM signatures WHERE sha256=?", (sha256,))
    if cur.fetchone():
        conn.close(); return False
    cur.execute("INSERT INTO signatures(name,sha256,rule_tag,author,ts,meta) "
                "VALUES(?,?,?,?,?,?)",
                (name, sha256, rule_tag, "stix-taxii", int(time.time()), json.dumps(meta or {})))
    conn.commit(); conn.close()
    return True

def sync():
    init_db()
    server = Server(TAXII_URL, user=None, password=None)
    api_root = server.api_roots[0]
    collections = api_root.collections
    for coll in collections:
        if COLLECTION_NAME.lower() in coll.title.lower():
            print(f"[+] Found collection: {coll.title}")
            objs = coll.get_objects()
            for o in objs["objects"]:
                try:
                    stix_obj = parse(o, allow_custom=True)
                except Exception:
                    continue
                if stix_obj.type == "indicator":
                    pattern = stix_obj.pattern
                    # Example pattern: "[file:hashes.'SHA-256' = 'abcdef123...']"
                    if "file:hashes.'SHA-256'" in pattern:
                        sha = pattern.split("'")[3]
                        upsert(stix_obj.name or "unknown", sha256=sha,
                               meta={"pattern": pattern})
                    elif "domain-name:value" in pattern:
                        domain = pattern.split("'")[3]
                        upsert(stix_obj.name or "unknown",
                               rule_tag="domain", meta={"domain": domain})
            print("[✓] Sync complete")
            break

if __name__ == "__main__":
    sync()
