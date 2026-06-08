import asyncio
import aiofiles
from pathlib import Path
import subprocess
import git
from typing import Dict, Any

class HolonTools:
    @staticmethod
    async def read_file(path: str) -> str:
        async with aiofiles.open(path, "r") as f:
            return await f.read()

    @staticmethod
    async def write_file(path: str, content: str):
        async with aiofiles.open(path, "w") as f:
            await f.write(content)

    @staticmethod
    def run_tests(path: str = ".") -> dict:
        try:
            result = subprocess.run(["pytest", "--tb=no"], cwd=path, capture_output=True, text=True, timeout=60)
            return {"passed": result.returncode == 0, "output": result.stdout + result.stderr}
        except Exception as e:
            return {"passed": False, "error": str(e)}

    @staticmethod
    def git_commit(message: str, path: str = ".") -> str:
        repo = git.Repo(path)
        repo.git.add(A=True)
        repo.index.commit(message)
        return repo.head.commit.hexsha
