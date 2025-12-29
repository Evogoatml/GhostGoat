def choose_cipher(metrics, mission):
    cpu = metrics["cpu"]
    limit = int(mission.get("CPU_LIMIT", 60))
    return "chacha20poly1305" if cpu > limit else "aesgcm"
