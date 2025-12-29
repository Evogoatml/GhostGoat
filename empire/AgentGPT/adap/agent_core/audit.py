
import os, json, time
from .crypto_core import sign_json

AUDIT = "adap/data/logs/audit.log"

def append(event: dict):
    os.makedirs(os.path.dirname(AUDIT), exist_ok=True)
    record = {"ts": int(time.time()), **event}
    record["sig"] = sign_json(record)
    with open(AUDIT, "a") as f:
        f.write(json.dumps(record) + "\n")
    return record
