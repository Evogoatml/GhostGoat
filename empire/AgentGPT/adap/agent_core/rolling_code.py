
from .crypto_core import rolling_key
import os, time

class RollingEngine:
    def __init__(self, seed: bytes = None):
        self.key = seed or os.urandom(32)
        self.counter = 0

    def next_key(self):
        self.counter += 1
        self.key = rolling_key(self.key, self.counter, time.time_ns().to_bytes(8,"big"))
        return self.key
