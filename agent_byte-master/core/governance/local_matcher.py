# local_matcher.py
import sqlite3, hashlib, json
try:
    import ssdeep
except Exception:
    ssdeep=None

DB="registry.db"

def sha256_file(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def match_exact(sha256):
    conn=sqlite3.connect(DB)
    cur=conn.cursor()
    cur.execute("SELECT id,name FROM signatures WHERE sha256=?",(sha256,))
    r=cur.fetchone(); conn.close()
    return r

def match_ssdeep(path):
    if ssdeep is None:
        return None
    s=ssdeep.hash_from_file(path)
    conn=sqlite3.connect(DB)
    cur=conn.cursor()
    cur.execute("SELECT id,name,ssdeep FROM signatures WHERE ssdeep IS NOT NULL")
    rows=cur.fetchall(); conn.close()
    best=None
    for rid,name,rs in rows:
        score=ssdeep.compare(s, rs)
        if score>60:
            best=(rid,name,score)
            break
    return best

# simple rule matching (regex) example
import regex
def match_rules(path):
    text=open(path,"rb",errors="ignore").read().decode("utf-8",errors="ignore")
    conn=sqlite3.connect(DB)
    cur=conn.cursor()
    cur.execute("SELECT id,name,meta FROM signatures WHERE rule_tag IS NOT NULL")
    for rid,name,meta in cur:
        meta=json.loads(meta) if meta else {}
        rules=meta.get("regex_patterns",[])
        for pat in rules:
            if regex.search(pat, text):
                return (rid,name,pat)
    conn.close()
    return None
