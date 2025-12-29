import re

def interpret_command(user_input: str) -> dict:
    text = user_input.strip().lower()

    if text.startswith("create skill"):
        skill_name = re.sub(r"^create skill\s+", "", text).strip().replace(" ", "_")
        return {
            "intent": "create_skill",
            "steps": [{"action": f"create_skill", "description": f"Create new skill '{skill_name}'", "skill_name": skill_name}]
        }

    if text.startswith("run") or text.startswith("execute"):
        skill_name = re.sub(r"^(run|execute)\s+", "", text).strip().replace(" ", "_")
        return {
            "intent": "run_skill",
            "steps": [{"action": f"run_skill", "description": f"Run skill '{skill_name}'", "skill_name": skill_name}]
        }

    return {
        "intent": "unknown",
        "steps": [
            {"action": "reflect", "description": "Reflect on unknown command"},
            {"action": "respond", "description": "Provide general response"},
        ],
    }

def plan_to_text(plan: dict) -> str:
    intent = plan.get("intent", "unknown")
    steps = plan.get("steps", [])
    lines = [f"Intent: {intent}"]
    for i, step in enumerate(steps, 1):
        action = step.get("action", "unknown")
        desc = step.get("description", "")
        lines.append(f"{i}. {action}: {desc}")
    return "\n".join(lines)
