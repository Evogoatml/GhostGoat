# translator_gate.py  (stand-alone version)
import os, shutil, json, time, hashlib, base64

QUARANTINE_DIR = "quarantine"
os.makedirs(QUARANTINE_DIR, exist_ok=True)

# --- lightweight built-ins to make it run ---
def append_entry(data):
    # simple audit writer
    with open("audit.log","a") as f:
        f.write(json.dumps(data)+"\n")

def compute_sha256(path):
    h = hashlib.sha256()
    with open(path,"rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def verify_manifest(manifest_path, sig_path, pubkey_path="keys/pubkey.pem"):
    # fake verifier for now, just reads manifest
    with open(manifest_path) as f:
        return json.load(f)

# placeholder matchers so the file runs
def match_exact(_): return False
def match_ssdeep(_): return False
def match_rules(_): return False
# ------------------------------------------------

def quarantine_file(content_p, manifest):
    sha = compute_sha256(content_p)
    dst = os.path.join(QUARANTINE_DIR, sha)
    shutil.move(content_p, dst)
    append_entry({
        "action":"quarantine",
        "sha":sha,
        "ts":time.time(),
        "manifest_name":manifest.get("name")
    })
    return dst

def process_upload(manifest_p, sig_p, content_p):
    manifest = verify_manifest(manifest_p, sig_p)
    sha = compute_sha256(content_p)
    if sha != manifest.get("content_sha256"):
        append_entry({"status":"reject","reason":"hash_mismatch","sha":sha})
        return {"status":"reject","reason":"hash_mismatch"}

    if match_exact(sha):
        append_entry({"action":"allow","sha":sha,"why":"exact"})
        return {"status":"allow","why":"exact"}
    if match_ssdeep(content_p):
        append_entry({"action":"allow","sha":sha,"why":"fuzzy"})
        return {"status":"allow","why":"fuzzy"}
    if match_rules(content_p):
        append_entry({"action":"allow","sha":sha,"why":"rule"})
        return {"status":"allow","why":"rule"}

    qpath = quarantine_file(content_p, manifest)
    return {"status":"quarantine","path":qpath}


# quick self-test so you can run it standalone
if __name__ == "__main__":
    # create dummy files
    os.makedirs("keys", exist_ok=True)
    with open("artifact.bin","wb") as f: f.write(b"testdata")
    sha = compute_sha256("artifact.bin")
    with open("manifest.json","w") as f:
        json.dump({"name":"demo_artifact","content_sha256":sha}, f)
    open("manifest.sig","w").write(base64.b64encode(b"sig").decode())

    print("[TEST] Running translator_gate self-test")
    result = process_upload("manifest.json","manifest.sig","artifact.bin")
    print(result)
