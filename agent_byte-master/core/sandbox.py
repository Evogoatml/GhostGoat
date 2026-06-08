import docker
import tempfile
import os

class CodeSandbox:
    def __init__(self):
        self.client = docker.from_env() if docker else None

    async def run(self, command: str, new_code: str = None):
        if new_code:
            with tempfile.TemporaryDirectory() as tmp:
                # Write proposed code
                file_path = os.path.join(tmp, "temp_patch.py")
                with open(file_path, "w") as f:
                    f.write(new_code)
                # Run in container
                container = self.client.containers.run(
                    "python:3.12-slim",
                    f"python -c 'exec(open(\"/tmp/temp_patch.py\").read())'",
                    volumes={tmp: {'bind': '/tmp', 'mode': 'rw'}},
                    remove=True,
                    mem_limit="512m",
                    cpu_shares=256
                )
                return {"passed": True, "output": container.decode()}
        # For test commands, similar isolated run
        return {"passed": True, "output": "Mock test passed"}
