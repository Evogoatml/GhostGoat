from .plugin_manager import PluginManager
from .memory import AgentMemory
from .cli import start_cli
from openai import OpenAI
import os, json
from ..skills import registry as skills

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class AdapAgent:
    def __init__(self, config_path="config.yaml"):
        self.memory = AgentMemory()
        self.plugin_manager = PluginManager()
        self.config_path = config_path

    def _tools_spec(self):
        # OpenAI tools schema
        spec = []
        for name, meta in skills.TOOLS.items():
            spec.append({
                "type":"function",
                "function":{
                    "name": name,
                    "description": f"Tool: {name}",
                    "parameters": meta["schema"],
                },
            })
        return spec

    def query_openai(self, prompt, model="gpt-4o-mini"):
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role":"user","content":prompt}],
            tools=self._tools_spec(),
            tool_choice="auto",
        )
        msg = resp.choices[0].message
        # If the model called a tool, execute and return tool result
        if getattr(msg, "tool_calls", None):
            call = msg.tool_calls[0]
            name = call.function.name
            try:
                args = json.loads(call.function.arguments or "{}")
            except Exception:
                args = {}
            try:
                result = skills.call(name, args)
            except Exception as e:
                result = {"error": str(e)}
            # Return tool result directly
            return json.dumps({"tool": name, "result": result}, ensure_ascii=False, indent=2)
        # Otherwise normal text
        return msg.content

    def start(self):
        print("adap agent starting.")
        self.plugin_manager.discover_plugins()
        start_cli(self)

if __name__ == "__main__":
    AdapAgent().start()
