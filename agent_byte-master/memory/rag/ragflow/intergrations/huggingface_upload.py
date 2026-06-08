"""
Hugging Face Hub Integration — Upload models, datasets, and spaces.

Usage:
    from integrations.huggingface_upload import HFUploader

    uploader = HFUploader(token="hf_...")   # or set HF_TOKEN env var

    # Upload a model directory
    uploader.upload_model("your-org/ghostgoat-model", "./path/to/model/")

    # Upload a dataset directory
    uploader.upload_dataset("your-org/ghostgoat-data", "./data/")

    # Upload the whole repo as a Space
    uploader.upload_space("your-org/ghostgoat-demo", ".")

    # Quick push of any folder
    uploader.push_folder("your-org/repo-name", "./folder", repo_type="model")

Requires:
    pip install huggingface_hub
"""

import logging
import os
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


class HFUploader:
    """Upload models, datasets, or spaces to Hugging Face Hub."""

    def __init__(self, token: Optional[str] = None):
        """
        Args:
            token: HF access token. Falls back to HF_TOKEN env var or
                   cached token from `huggingface-cli login`.
        """
        self.token = token or os.getenv("HF_TOKEN") or os.getenv("HUGGING_FACE_HUB_TOKEN")
        self._api = None

    @property
    def api(self):
        """Lazy-load the HfApi client."""
        if self._api is None:
            from huggingface_hub import HfApi
            self._api = HfApi(token=self.token)
        return self._api

    def login_interactive(self):
        """Run interactive login (saves token to disk)."""
        from huggingface_hub import login
        login()
        # Refresh token after login
        from huggingface_hub import HfFolder
        self.token = HfFolder.get_token()

    # ------------------------------------------------------------------
    # Core upload methods
    # ------------------------------------------------------------------

    def upload_model(
        self,
        repo_id: str,
        folder_path: str,
        commit_message: str = "Upload GhostGoat model",
        private: bool = False,
        ignore_patterns: Optional[List[str]] = None,
    ) -> str:
        """Upload a model directory to HF Hub.

        Args:
            repo_id: e.g. "Evogoatml/ghostgoat-model"
            folder_path: Local path to the model directory.
            commit_message: Commit message for the upload.
            private: Whether the repo should be private.
            ignore_patterns: File patterns to skip (e.g. ["*.pyc", "__pycache__"]).

        Returns:
            URL of the uploaded repo.
        """
        return self.push_folder(
            repo_id, folder_path,
            repo_type="model",
            commit_message=commit_message,
            private=private,
            ignore_patterns=ignore_patterns,
        )

    def upload_dataset(
        self,
        repo_id: str,
        folder_path: str,
        commit_message: str = "Upload GhostGoat dataset",
        private: bool = False,
        ignore_patterns: Optional[List[str]] = None,
    ) -> str:
        """Upload a dataset directory to HF Hub.

        Args:
            repo_id: e.g. "Evogoatml/ghostgoat-data"
            folder_path: Local path to the dataset directory.

        Returns:
            URL of the uploaded repo.
        """
        return self.push_folder(
            repo_id, folder_path,
            repo_type="dataset",
            commit_message=commit_message,
            private=private,
            ignore_patterns=ignore_patterns,
        )

    def upload_space(
        self,
        repo_id: str,
        folder_path: str,
        space_sdk: str = "gradio",
        commit_message: str = "Upload GhostGoat space",
        private: bool = False,
        ignore_patterns: Optional[List[str]] = None,
    ) -> str:
        """Upload a Spaces app to HF Hub.

        Args:
            repo_id: e.g. "Evogoatml/ghostgoat-demo"
            folder_path: Local path to the app directory.
            space_sdk: "gradio", "streamlit", or "docker".

        Returns:
            URL of the uploaded space.
        """
        self.api.create_repo(
            repo_id=repo_id,
            repo_type="space",
            space_sdk=space_sdk,
            private=private,
            exist_ok=True,
        )
        self.api.upload_folder(
            repo_id=repo_id,
            repo_type="space",
            folder_path=folder_path,
            commit_message=commit_message,
            ignore_patterns=ignore_patterns or _default_ignore(),
        )
        url = f"https://huggingface.co/spaces/{repo_id}"
        logger.info("Space uploaded: %s", url)
        return url

    def push_folder(
        self,
        repo_id: str,
        folder_path: str,
        repo_type: str = "model",
        commit_message: str = "Upload from GhostGoat",
        private: bool = False,
        ignore_patterns: Optional[List[str]] = None,
    ) -> str:
        """Generic folder push to any HF repo type.

        Creates the repo if it doesn't exist, then uploads the folder.
        """
        self.api.create_repo(
            repo_id=repo_id,
            repo_type=repo_type,
            private=private,
            exist_ok=True,
        )
        self.api.upload_folder(
            repo_id=repo_id,
            repo_type=repo_type,
            folder_path=folder_path,
            commit_message=commit_message,
            ignore_patterns=ignore_patterns or _default_ignore(),
        )
        base = "https://huggingface.co"
        if repo_type == "dataset":
            url = f"{base}/datasets/{repo_id}"
        elif repo_type == "space":
            url = f"{base}/spaces/{repo_id}"
        else:
            url = f"{base}/{repo_id}"
        logger.info("Uploaded %s to %s", repo_type, url)
        return url

    def upload_file(
        self,
        repo_id: str,
        local_path: str,
        path_in_repo: str,
        repo_type: str = "model",
        commit_message: str = "Upload file from GhostGoat",
    ) -> str:
        """Upload a single file to an existing HF repo."""
        self.api.upload_file(
            repo_id=repo_id,
            repo_type=repo_type,
            path_or_fileobj=local_path,
            path_in_repo=path_in_repo,
            commit_message=commit_message,
        )
        logger.info("File uploaded: %s -> %s:%s", local_path, repo_id, path_in_repo)
        return f"https://huggingface.co/{repo_id}"

    # ------------------------------------------------------------------
    # Convenience: upload GhostGoat project data
    # ------------------------------------------------------------------

    def upload_ghostgoat_data(self, repo_id: str, private: bool = True) -> str:
        """Upload GhostGoat's data/ directory as a dataset.

        Includes task_memory, user_behavior, vector_db exports, etc.
        Skips binary blobs and caches.
        """
        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        if not os.path.isdir(data_dir):
            raise FileNotFoundError(f"Data directory not found: {data_dir}")

        return self.upload_dataset(
            repo_id=repo_id,
            folder_path=data_dir,
            commit_message="Upload GhostGoat runtime data",
            private=private,
            ignore_patterns=["*.db", "*.sqlite", "__pycache__", "*.pyc", ".git"],
        )

    def upload_ghostgoat_project(self, repo_id: str, private: bool = False) -> str:
        """Upload the entire GhostGoat project as a model repo.

        Useful for sharing the system on HF Hub.
        """
        project_root = os.path.dirname(os.path.dirname(__file__))
        return self.upload_model(
            repo_id=repo_id,
            folder_path=project_root,
            commit_message="Upload GhostGoat multi-agent system",
            private=private,
            ignore_patterns=_default_ignore() + [
                ".git", ".git/**", "*.db", "*.sqlite",
                "node_modules", "node_modules/**",
                ".env", "*.env",
            ],
        )


def _default_ignore() -> List[str]:
    """Default file patterns to ignore during upload."""
    return [
        "__pycache__",
        "__pycache__/**",
        "*.pyc",
        ".git",
        ".git/**",
        "*.egg-info",
        "*.egg-info/**",
        ".env",
        "*.log",
    ]
