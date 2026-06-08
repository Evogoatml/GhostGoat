"""
Training Bridge — connects the ML vault and training algorithms to ASI agents.

Provides:
  - Discovery: scan and list all training resources (scripts, notebooks, datasets)
  - Loading: dynamically import training classes/functions from the ML library
  - Execution: run training with a unified interface regardless of algorithm style
  - Integration: drop-in helpers for NeuroForge, SelfEvolvingAgent, and EvoAgent
"""

import os
import sys
import importlib
import importlib.util
import json
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

# ---------------------------------------------------------------------------
# Path constants — resolved relative to the repo root
# ---------------------------------------------------------------------------
_THIS_DIR = Path(__file__).resolve().parent  # ACS_SYSTEM/asi/
_REPO_ROOT = _THIS_DIR.parent.parent         # GhostGoat/

ML_BASE = _REPO_ROOT / "core" / "reasoning" / "brain" / "training" / "algorithms"
ML_EXT = _REPO_ROOT / "core" / "reasoning" / "brain" / "training" / "extended"
NN_BASE = _REPO_ROOT / "core" / "reasoning" / "brain" / "training" / "neural_networks"
ML_VAULT_PATH = _REPO_ROOT / "core" / "reasoning" / "brain" / "training" / "ml_vault.py"

# ---------------------------------------------------------------------------
# Registry of known algorithms with their module paths and interface info
# ---------------------------------------------------------------------------
ALGORITHM_REGISTRY: List[Dict[str, Any]] = [
    {
        "name": "decision_tree",
        "module_file": ML_BASE / "decision_tree.py",
        "class_name": "Decision_Tree",
        "interface": "class",       # class with .train(X, y) / .predict(x)
        "task": "regression",
        "init_params": {"depth": 10, "min_leaf_size": 10},
        "train_method": "train",
        "predict_method": "predict",
    },
    {
        "name": "logistic_regression",
        "module_file": ML_BASE / "logistic_regression.py",
        "class_name": None,
        "interface": "function",    # standalone function logistic_reg(alpha, X, y)
        "task": "classification",
        "entry_function": "logistic_reg",
    },
    {
        "name": "gradient_descent",
        "module_file": ML_BASE / "gradient_descent.py",
        "class_name": None,
        "interface": "script",      # run via run_gradient_descent()
        "task": "regression",
        "entry_function": "run_gradient_descent",
    },
    {
        "name": "perceptron",
        "module_file": ML_BASE / "perceptron.py",
        "class_name": "Perceptron",
        "interface": "class",
        "task": "classification",
        "train_method": "train",
        "predict_method": "predict",
    },
    {
        "name": "random_forest_classification",
        "module_file": ML_BASE / "random_forest_classification.py",
        "class_name": "RandomForest",
        "interface": "class",
        "task": "classification",
        "train_method": "fit",
        "predict_method": "predict",
    },
    {
        "name": "random_forest_regression",
        "module_file": ML_BASE / "random_forest_regression.py",
        "class_name": "RandomForest",
        "interface": "class",
        "task": "regression",
        "train_method": "fit",
        "predict_method": "predict",
    },
    {
        "name": "bpnn",
        "module_file": NN_BASE / "bpnn.py",
        "class_name": "BPNN",
        "interface": "class",
        "task": "neural_network",
        "train_method": "train",
        "extra_classes": ["DenseLayer"],
    },
    {
        "name": "k_means_clustering",
        "module_file": ML_BASE / "k_means_clust.py",
        "class_name": None,
        "interface": "script",
        "task": "clustering",
    },
    {
        "name": "linear_regression",
        "module_file": ML_BASE / "linear_regression.py",
        "class_name": None,
        "interface": "function",
        "task": "regression",
    },
]

# Also try to register anything in the extended ML folder
if ML_EXT.exists():
    _ext_extras = [
        ("xgboost_classifier", "xgboost_classifier.py", "classification"),
        ("xgboost_regressor", "xgboost_regressor.py", "regression"),
        ("support_vector_machines", "support_vector_machines.py", "classification"),
        ("polynomial_regression", "polynomial_regression.py", "regression"),
        ("gradient_boosting_classifier", "gradient_boosting_classifier.py", "classification"),
        ("k_nearest_neighbours", "k_nearest_neighbours.py", "classification"),
        ("linear_discriminant_analysis", "linear_discriminant_analysis.py", "classification"),
        ("self_organizing_map", "self_organizing_map.py", "clustering"),
    ]
    for _name, _file, _task in _ext_extras:
        _path = ML_EXT / _file
        if _path.exists():
            ALGORITHM_REGISTRY.append({
                "name": _name,
                "module_file": _path,
                "class_name": None,
                "interface": "auto",
                "task": _task,
            })


# ---------------------------------------------------------------------------
# Dynamic module loader
# ---------------------------------------------------------------------------
def _load_module(filepath: Path, module_name: str = None):
    """Import a .py file as a module at runtime."""
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"Training module not found: {filepath}")
    if module_name is None:
        module_name = f"_training_{filepath.stem}"
    spec = importlib.util.spec_from_file_location(module_name, str(filepath))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# TrainingBridge — the main integration class
# ---------------------------------------------------------------------------
class TrainingBridge:
    """Unified interface between ASI agents and the training algorithm library."""

    def __init__(self, repo_root: Path = None):
        self.repo_root = Path(repo_root) if repo_root else _REPO_ROOT
        self._loaded_modules: Dict[str, Any] = {}
        self._vault = None

    # ---- discovery ---------------------------------------------------------

    def list_algorithms(self, task: str = None) -> List[Dict[str, str]]:
        """Return a list of available training algorithms, optionally filtered by task."""
        results = []
        for entry in ALGORITHM_REGISTRY:
            if task and entry["task"] != task:
                continue
            available = Path(entry["module_file"]).exists()
            results.append({
                "name": entry["name"],
                "task": entry["task"],
                "interface": entry["interface"],
                "available": available,
                "path": str(entry["module_file"]),
            })
        return results

    def scan_training_files(self, directory: Path = None) -> List[Dict[str, str]]:
        """Walk a directory and return all .py / .ipynb files that look training-related."""
        search_dirs = [ML_BASE, ML_EXT, NN_BASE] if directory is None else [Path(directory)]
        results = []
        keywords = {"train", "fit", "epoch", "learning_rate", "model", "predict", "loss"}
        for d in search_dirs:
            if not d.exists():
                continue
            for f in d.rglob("*"):
                if f.suffix not in (".py", ".ipynb"):
                    continue
                if f.name.startswith("."):
                    continue
                try:
                    content = f.read_text(errors="ignore")[:3000].lower()
                    hits = [kw for kw in keywords if kw in content]
                except Exception:
                    hits = []
                results.append({
                    "path": str(f),
                    "name": f.stem,
                    "type": f.suffix,
                    "training_signals": hits,
                })
        return results

    def get_vault(self):
        """Lazy-load the MLVault from core/reasoning/brain/training/ml_vault.py."""
        if self._vault is not None:
            return self._vault
        try:
            mod = _load_module(ML_VAULT_PATH, "_ml_vault")
            self._vault = mod.MLVault(
                db_path=str(self.repo_root / "ml_vault.db")
            )
            return self._vault
        except Exception as exc:
            return {"error": str(exc)}

    def search_vault(self, query: str, **kwargs) -> List[Dict]:
        """Search the ML vault for training resources matching a query."""
        vault = self.get_vault()
        if isinstance(vault, dict):
            return [vault]
        return vault.search(query, **kwargs)

    # ---- loading -----------------------------------------------------------

    def load_algorithm(self, name: str) -> Dict[str, Any]:
        """Load a training algorithm by name. Returns the module + metadata."""
        entry = next((e for e in ALGORITHM_REGISTRY if e["name"] == name), None)
        if entry is None:
            return {"error": f"Unknown algorithm: {name}. Use list_algorithms() to see options."}

        if name in self._loaded_modules:
            return {"module": self._loaded_modules[name], **entry}

        try:
            mod = _load_module(entry["module_file"])
            self._loaded_modules[name] = mod
            return {"module": mod, **entry}
        except Exception as exc:
            return {"error": f"Failed to load {name}: {exc}"}

    # ---- execution ---------------------------------------------------------

    def run_training(self, name: str, X=None, y=None, **kwargs) -> Dict[str, Any]:
        """
        Run a training algorithm by name with the given data.

        For class-based algorithms: instantiates the class, calls train/fit.
        For function-based algorithms: calls the entry function directly.
        For script-based algorithms: calls the main entry point.

        Returns a dict with results, model reference, and any errors.
        """
        loaded = self.load_algorithm(name)
        if "error" in loaded:
            return loaded

        mod = loaded["module"]
        interface = loaded["interface"]

        try:
            if interface == "class" and loaded.get("class_name"):
                cls = getattr(mod, loaded["class_name"])
                init_params = loaded.get("init_params", {})
                # Allow overrides
                init_params.update({k: v for k, v in kwargs.items() if k in init_params})
                model = cls(**init_params)

                train_method = loaded.get("train_method", "train")
                train_fn = getattr(model, train_method)

                if X is not None and y is not None:
                    result = train_fn(X, y, **{k: v for k, v in kwargs.items() if k not in init_params})
                else:
                    result = train_fn(**kwargs)

                return {
                    "status": "success",
                    "algorithm": name,
                    "model": model,
                    "train_result": str(result) if result is not None else "trained",
                }

            elif interface == "function" and loaded.get("entry_function"):
                fn = getattr(mod, loaded["entry_function"])
                if X is not None and y is not None:
                    result = fn(X=X, y=y, **kwargs)
                else:
                    result = fn(**kwargs)
                return {
                    "status": "success",
                    "algorithm": name,
                    "result": str(result) if result is not None else "completed",
                }

            elif interface == "script" and loaded.get("entry_function"):
                fn = getattr(mod, loaded["entry_function"])
                result = fn()
                return {
                    "status": "success",
                    "algorithm": name,
                    "result": str(result) if result is not None else "completed",
                }

            else:
                # Auto-detect: look for common class or function names
                for attr_name in dir(mod):
                    obj = getattr(mod, attr_name)
                    if isinstance(obj, type) and hasattr(obj, "train"):
                        model = obj()
                        if X is not None and y is not None:
                            model.train(X, y)
                        return {"status": "success", "algorithm": name, "model": model}
                    if callable(obj) and attr_name.startswith(("train", "run", "fit")):
                        result = obj()
                        return {"status": "success", "algorithm": name, "result": str(result)}

                return {"error": f"Could not find a trainable interface in {name}"}

        except Exception as exc:
            return {
                "status": "error",
                "algorithm": name,
                "error": str(exc),
                "traceback": traceback.format_exc(),
            }

    # ---- convenience for agents --------------------------------------------

    def summary(self) -> str:
        """Human-readable summary for agent context injection."""
        algos = self.list_algorithms()
        available = [a for a in algos if a["available"]]
        tasks = set(a["task"] for a in available)
        lines = [
            f"Training Bridge: {len(available)} algorithms available",
            f"Tasks: {', '.join(sorted(tasks))}",
            "Algorithms:",
        ]
        for a in available:
            lines.append(f"  - {a['name']} ({a['task']}, {a['interface']})")
        return "\n".join(lines)
