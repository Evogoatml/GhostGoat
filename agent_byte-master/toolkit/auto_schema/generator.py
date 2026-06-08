"""GhostGoat Auto-Schema Generator — Register any Python callable as a tool."""
import inspect, json, typing, logging
from typing import Any, Callable, Dict, List, Optional, get_type_hints
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ParamSchema:
    name: str
    type: str
    description: str
    required: bool = True
    default: Any = None

@dataclass
class ToolSchema:
    name: str
    description: str
    parameters: List[ParamSchema]
    return_type: str = "Any"

def _type_name(t) -> str:
    if t is inspect.Parameter.empty:
        return "Any"
    if hasattr(t, "__name__"):
        return t.__name__
    return str(t).replace("typing.", "")

def _parse_docstring(func: Callable) -> Dict[str, str]:
    doc = inspect.getdoc(func) or ""
    lines = doc.strip().split("\n")
    desc = lines[0] if lines else "No description"
    param_docs = {}
    for line in lines:
        line = line.strip()
        if line.startswith(":param "):
            parts = line[6:].split(" ", 1)
            if parts:
                param_docs[parts[0]] = parts[1] if len(parts) > 1 else ""
    return {"description": desc, "params": param_docs}

def generate_schema(func: Callable, name: Optional[str] = None, description: Optional[str] = None) -> ToolSchema:
    sig = inspect.signature(func)
    hints = get_type_hints(func)
    param_map = {p.name: p for p in sig.parameters.values()}
    doc_info = _parse_docstring(func)
    params = []
    for pname, param in param_map.items():
        ptype = _type_name(hints.get(pname, param.annotation))
        default = param.default if param.default is not inspect.Parameter.empty else None
        params.append(ParamSchema(
            name=pname,
            type=ptype,
            description=doc_info["params"].get(pname, f"Parameter {pname}"),
            required=param.default is inspect.Parameter.empty,
            default=default
        ))
    return ToolSchema(
        name=name or func.__name__,
        description=description or doc_info["description"],
        parameters=params,
        return_type=_type_name(hints.get("return", inspect.Parameter.empty))
    )

def schema_to_json(schema: ToolSchema) -> Dict[str, Any]:
    return {
        "name": schema.name,
        "description": schema.description,
        "parameters": {
            "type": "object",
            "properties": {p.name: {"type": _json_type(p.type), "description": p.description}
                           for p in schema.parameters},
            "required": [p.name for p in schema.parameters if p.required]
        }
    }

def _json_type(py_type: str) -> str:
    mapping = {"str": "string", "int": "integer", "float": "number", "bool": "boolean",
               "list": "array", "dict": "object", "Any": "string"}
    for k, v in mapping.items():
        if k in py_type.lower():
            return v
    return "string"

class AutoRegister:
    registry: Dict[str, Any] = {}

    @classmethod
    def register(cls, func: Callable, name: Optional[str] = None, description: Optional[str] = None):
        schema = generate_schema(func, name=name, description=description)
        cls.registry[schema.name] = {"schema": schema, "callable": func, "json": schema_to_json(schema)}
        logger.info("Auto-registered tool: %s", schema.name)
        return func

    @classmethod
    def list_all(cls) -> List[Dict[str, Any]]:
        return [{"name": n, **schema_to_json(v["schema"])} for n, v in cls.registry.items()]

    @classmethod
    def run(cls, name: str, kwargs: Dict[str, Any]) -> Any:
        entry = cls.registry.get(name)
        if not entry:
            raise ValueError(f"Tool {name} not registered")
        return entry["callable"](**kwargs)

