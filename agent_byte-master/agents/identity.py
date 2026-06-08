import hashlib
from pathlib import Path
import json

class HolonIdentity:
    def __init__(self, path: Path):
        self.path = path.resolve()
        self.id = hashlib.blake2b(str(self.path).encode(), digest_size=32).hexdigest()
        self.key = hashlib.blake2b(self.id.encode(), digest_size=64).digest()

    def sign(self, data: dict) -> str:
        payload = json.dumps(data, sort_keys=True).encode()
        return hashlib.blake2b(payload + self.key, digest_size=32).hexdigest()

    def verify(self, data: dict, signature: str) -> bool:
        return self.sign(data) == signature
