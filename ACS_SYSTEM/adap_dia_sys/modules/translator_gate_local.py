# translator_gate_local.py
from verify_manifest import verify_manifest  # earlier code
from local_matcher import sha256_file, match_exact, match_ssdeep, match_rules
from audit import append_entry  # your hash-chain

def process_upload(manifest_p, sig_p, content_p):
    manifest = verify_manifest(manifest_p, sig_p)  # raises if invalid
    sha = sha256_file(content_p)
    if sha != manifest.get("content_sha256"):
        append_entry({"action":"reject","reason":"hash_mismatch","sha":sha})
        return {"status":"reject","reason":"hash_mismatch"}
    # exact match
    exact = match_exact(sha)
    if exact:
        append_entry({"action":"allow","sha":sha,"matched":"exact","id":exact[0]})
        return {"status":"allow","why":"exact"}
    # fuzzy
    fuzzy = match_ssdeep(content_p)
    if fuzzy:
        append_entry({"action":"allow","sha":sha,"matched":"fuzzy","id":fuzzy[0],"score":fuzzy[2]})
        return {"status":"allow","why":"fuzzy"}
    # rule match
    rule = match_rules(content_p)
    if rule:
        append_entry({"action":"allow","sha":sha,"matched":"rule","id":rule[0],"pattern":rule[2]})
        return {"status":"allow","why":"rule"}
    # unknown -> quarantine
    append_entry({"action":"quarantine","sha":sha})
    # move file to quarantine/...
    return {"status":"quarantine"}
