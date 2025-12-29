import json
from .controller import detect_and_clone_github_url
from ..skills import registry as skills

def start_cli(agent=None):
    print("cli ready. type 'exit' to quit.")
    while True:
        try:
            line = input("adap> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        if line in {"exit","quit"}:
            break

        if line.startswith("ask "):
            if agent and hasattr(agent,"query_openai"):
                print(agent.query_openai(line[4:]))
            else:
                print("agent missing query_openai()")
            continue

        if line.startswith("tool "):
            # tool <name> <json_args>
            parts = line.split(" ", 2)
            if len(parts) < 3:
                print("usage: tool <name> <json>")
                continue
            name = parts[1]
            try:
                args = json.loads(parts[2])
            except Exception as e:
                print("bad json:", e); continue
            try:
                out = skills.call(name, args)
                print(json.dumps(out, ensure_ascii=False, indent=2))
            except Exception as e:
                print("tool error:", e)
            continue

        if line.startswith("clone "):
            url = detect_and_clone_github_url(line)
            print(url or "no github url found")
            continue

        print("unknown. try: ask <prompt> | tool <name> <json> | clone <url> | exit")
