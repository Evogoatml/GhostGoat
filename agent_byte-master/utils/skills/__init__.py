"""
Agent K skill library — reusable reasoning patterns that survive across runs.

Quick start
-----------
    from core.brain.agents import tool_agent as skill_library

    skill = skill_library.lookup("encrypt a message with RSA")
    if skill:
        print(skill.solution)
    else:
        solution = run_heavy_llm_call(task)
        skill_library.record(task, solution, success=True)
"""

from core.brain.agents.tool_agent import Skill, SkillLibrary

# Module-level singleton — import and use directly
skill_library = SkillLibrary()

__all__ = ["Skill", "SkillLibrary", "skill_library"]
