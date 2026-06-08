import structlog
from core.controllers.llm_controller import LLMController as LLMClient
from tools.github_tool import GitHubTool
from tools.hf_tool import HuggingFaceTool
from tools.code_tools import CodeEditor
from core.sandbox import CodeSandbox
from bot.keyboards import get_code_approval_keyboard

logger = structlog.get_logger()

class SelfImprover:
    def __init__(self):
        self.llm = LLMClient()
        self.github = GitHubTool()
        self.hf = HuggingFaceTool()
        self.editor = CodeEditor()
        self.sandbox = CodeSandbox()

    async def improve(self, issue_description: str, chat_id: int, user_id: int) -> dict:
        """Full self-improvement cycle. Returns proposal for user approval."""
        history = []  # short ReAct trace

        # Step 1: Analyze issue + decide if self-fix is possible
        prompt = f"""
        You are a self-improving Telegram task bot.
        Current issue: {issue_description}
        Analyze and plan: search GitHub/HF if needed, then propose code changes.
        Output JSON only:
        {{
          "needs_search": true/false,
          "search_query_github": "...",
          "search_query_hf": "...",
          "reason": "..."
        }}
        """
        plan = await self.llm.complete(prompt, temperature=0.0)
        history.append({"step": "plan", "output": plan})

        # Step 2: Search if needed
        if plan.get("needs_search"):
            if plan.get("search_query_github"):
                github_results = await self.github.search_code(plan["search_query_github"])
                history.append({"step": "github_search", "results": github_results[:3]})
            if plan.get("search_query_hf"):
                hf_results = await self.hf.search_models(plan["search_query_hf"])
                history.append({"step": "hf_search", "results": hf_results[:2]})

        # Step 3: Generate fix / optimization
        improve_prompt = f"""
        Using the above search results and issue: {issue_description}
        Generate a complete, safe code patch for the bot.
        Focus on one file at a time.
        Output JSON:
        {{
          "file_path": "core/agent.py",
          "new_code": "full new file content",
          "explanation": "why this fixes/optimizes",
          "test_command": "python -m pytest tests/test_agent.py"
        }}
        """
        proposal = await self.llm.complete(improve_prompt, temperature=0.2)
        history.append({"step": "proposal", "output": proposal})

        # Step 4: Sandbox test
        test_result = await self.sandbox.run(proposal["test_command"], proposal["new_code"])
        history.append({"step": "sandbox_test", "output": test_result})

        # Step 5: Send proposal to user via Telegram
        proposal_msg = f"""
        🛠 Self-Improvement Proposal
        Issue: {issue_description}
        File: {proposal['file_path']}
        Changes: {proposal['explanation']}
        Test passed: {test_result['passed']}
        
        Approve this change?
        """
        # In handler we would send this + keyboard
        return {
            "proposal": proposal,
            "history": history,
            "approval_keyboard": get_code_approval_keyboard(proposal["file_path"], proposal["new_code"])
        }
