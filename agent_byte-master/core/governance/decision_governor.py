
import os

# Simple policy gate. Expand with per-context rules as needed.
def allow_external_calls(context: str) -> bool:
    flag = os.getenv("ADAP_ALLOW_EXTERNAL", "1")
    return flag == "1"
