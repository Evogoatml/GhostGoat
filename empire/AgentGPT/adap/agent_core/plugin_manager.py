import os, importlib, inspect

def scan_plugins():
    """Scan the plugins directory for .py files and dynamically load them."""
    plugin_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "plugins"))
    if not os.path.exists(plugin_dir):
        print("⚠️ No plugins directory found.")
        return []

    loaded = []
    for file in os.listdir(plugin_dir):
        if file.endswith(".py") and not file.startswith("_"):
            name = file[:-3]
            try:
                importlib.import_module(f"adap.plugins.{name}")
                loaded.append(name)
            except Exception as e:
                print(f"❌ Failed to load {name}: {e}")
    return loaded


class PluginManager:
    def __init__(self, plugins_dir=None):
        self.plugins_dir = plugins_dir or os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "plugins"))
        self.plugins = {}

    def discover_plugins(self):
        for fname in os.listdir(self.plugins_dir):
            if fname.endswith(".py") and not fname.startswith("_"):
                modname = fname[:-3]
                try:
                    mod = importlib.import_module(f"adap.plugins.{modname}")
                    for name, func in inspect.getmembers(mod, inspect.isfunction):
                        doc = (func.__doc__ or "")
                        if "@jarviscmd" in doc:
                            self.plugins[modname] = func
                except Exception as e:
                    print(f"[PLUGIN ERROR] {modname}: {e}")

    def get_commands(self):
        return self.plugins
