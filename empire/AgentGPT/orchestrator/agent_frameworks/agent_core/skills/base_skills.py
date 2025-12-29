from .registry import registry

def create_skill(skill_name, registry):
    registry[skill_name] = lambda: f"Dynamically created skill: {skill_name} - READY TO EXPAND"
    return f"New skill '{skill_name}' registered successfully."

def run_step(step):
    if isinstance(step, dict):
        action = step.get("action", "")
        skill_name = step.get("skill_name", "")
    else:
        action = str(step)
        skill_name = ""

    # 1. Create new skill dynamically
    if action == "create_skill" and skill_name:
        return create_skill(skill_name, registry)

    # 2. Run an existing dynamic skill
    if action == "run_skill" and skill_name:
        if skill_name in registry:
            try:
                result = registry[skill_name]()
                return f"Executed {skill_name}: {result}"
            except Exception as e:
                return f"Error executing {skill_name}: {e}"
        else:
            return f"Skill '{skill_name}' not found in registry."

    # 3. Fallback: match keywords against the registry
    for key, func in registry.items():
        if key.lower() in action.lower():
            try:
                result = func()
                return f"Executed {key}: {result}"
            except Exception as e:
                return f"Error executing {key}: {e}"

    return f"No matching skill found for: {action}"
