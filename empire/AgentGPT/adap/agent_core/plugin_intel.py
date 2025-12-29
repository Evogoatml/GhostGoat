import os, importlib, inspect, json

PLUGIN_DIR = "/root/adap/plugins"
REGISTRY_PATH = "/root/adap/plugin_registry.json"

def scan_plugins():
    plugins = {}
    for f in os.listdir(PLUGIN_DIR):
        if f.endswith(".py") and f != "__init__.py":
            mod_name = f[:-3]
            try:
                module = importlib.import_module(f"adap.plugins.{mod_name}")
                for name, obj in inspect.getmembers(module):
                    if inspect.isclass(obj) and hasattr(obj, "execute"):
                        plugins[name] = {
                            "module": mod_name,
                            "doc": inspect.getdoc(obj) or "",
                        }
            except Exception as e:
                print(f"[skip] {mod_name}: {e}")
    return plugins

def build_registry():
    os.makedirs(os.path.dirname(REGISTRY_PATH), exist_ok=True)
    plugins = scan_plugins()
    with open(REGISTRY_PATH, "w") as f:
        json.dump(plugins, f, indent=2)
    print(f"[registry] {len(plugins)} plugins registered -> {REGISTRY_PATH}")
