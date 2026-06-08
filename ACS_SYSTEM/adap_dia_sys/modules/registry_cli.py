# registry_cli.py
import sqlite3, json, time, argparse
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

DB="registry.db"
def init_db():
    c=sqlite3.connect(DB)
    cur=c.cursor()
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
    c.commit(); c.close()

def load_privkey(path="keys/privkey.pem"):
    b=open(path,"rb").read()
    return Ed25519PrivateKey.from_private_bytes(b)

def add_entry(name, sha256=None, whirl=None, ssdeep=None, rule_tag=None, author="you", meta=None, privkey="keys/privkey.pem"):
    init_db()
    entry = {"name":name,"sha256":sha256,"whirlpool":whirl,"ssdeep":ssdeep,"rule_tag":rule_tag,"author":author,"ts":int(time.time()),"meta":meta or {}}
    payload = json.dumps(entry, sort_keys=True).encode()
    sk = load_privkey(privkey)
    sig = sk.sign(payload)
    pub = sk.public_key().public_bytes(encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)
    conn=sqlite3.connect(DB)
    cur=conn.cursor()
    cur.execute("INSERT INTO signatures(name,sha256,whirlpool,ssdeep,rule_tag,author,ts,signer_pub,signature,meta) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (name,sha256,whirl,ssdeep,rule_tag,author,entry["ts"],pub,sig,json.dumps(entry["meta"])))
    conn.commit(); conn.close()
    print("[OK] added", name)

def list_entries():
    init_db()
    conn=sqlite3.connect(DB)
    for row in conn.execute("SELECT id,name,sha256,whirlpool,ssdeep,rule_tag,author,ts FROM signatures"):
        print(row)
    conn.close()

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--add", action="store_true")
    p.add_argument("--name")
    p.add_argument("--sha256")
    p.add_argument("--whirlpool")
    p.add_argument("--ssdeep")
    p.add_argument("--rule_tag")
    p.add_argument("--list", action="store_true")
    args=p.parse_args()
    if args.add:
        add_entry(args.name, args.sha256, args.whirlpool, args.ssdeep, args.rule_tag)
    if args.list:
        list_entries()
