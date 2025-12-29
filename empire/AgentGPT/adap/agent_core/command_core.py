# adap/agent_core/command_core.py
import importlib
import os

COMMANDS = {}

def register_command(name, func):
    COMMANDS[name] = func

def load_plugin_commands():
    plugin_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "plugins"))
    for file in os.listdir(plugin_dir):
        if file.endswith(".py") and not file.startswith("__"):
            modname = f"adap.plugins.{file[:-3]}"
            try:
                mod = importlib.import_module(modname)
                if hasattr(mod, "register"):
                    mod.register(register_command)
            except Exception as e:
                print(f"⚠️ Plugin {file} failed to load: {e}")

def execute_command(name):
    if name in COMMANDS:
        try:
            COMMANDS[name]()
        except Exception as e:
            print(f"❌ Command '{name}' failed: {e}")
    else:
        print(f"⚠️ Unknown command '{name}'")

def list_commands():
    return sorted(COMMANDS.keys())
