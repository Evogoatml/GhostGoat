#!/usr/bin/env python3
"""
GhostGoat LLM Orchestrator CLI
Command-line interface for orchestrator operations
"""

import argparse
import json
import asyncio
import sys
from llm_orchestrator import LLMOrchestrator
from orchestrator_api import OrchestratorAPI


def print_json(data, indent=2):
    """Pretty print JSON"""
    print(json.dumps(data, indent=indent))


async def cmd_orchestrate(args):
    """Execute orchestration command"""
    orchestrator = LLMOrchestrator(
        llm_provider=args.provider,
        llm_model=args.model,
        llm_api_key=args.api_key
    )
    
    context = None
    if args.context:
        try:
            context = json.loads(args.context)
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON in context: {args.context}")
            sys.exit(1)
    
    print(f"Orchestrating: {args.query}")
    result = await orchestrator.orchestrate(args.query, context)
    
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"Result saved to {args.output}")
    else:
        print_json(result)


def cmd_status(args):
    """Get status"""
    api = OrchestratorAPI(llm_provider=args.provider)
    status = api.get_status()
    print_json(status)


def cmd_agents(args):
    """List agents"""
    api = OrchestratorAPI(llm_provider=args.provider)
    agents = api.get_agents()
    print_json({"agents": agents})


def cmd_tasks(args):
    """List tasks"""
    api = OrchestratorAPI(llm_provider=args.provider)
    tasks = api.get_tasks(status=args.status)
    print_json({"tasks": tasks})


def cmd_history(args):
    """Show execution history"""
    api = OrchestratorAPI(llm_provider=args.provider)
    history = api.get_execution_history(limit=args.limit)
    print_json({"history": history})


def main():
    parser = argparse.ArgumentParser(
        description="GhostGoat LLM Orchestrator CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Orchestrate a query
  python orchestrator_cli.py orchestrate "encrypt data with RSA"
  
  # Use specific LLM provider
  python orchestrator_cli.py orchestrate "find shortest path" --provider openai --model gpt-4
  
  # Get status
  python orchestrator_cli.py status
  
  # List agents
  python orchestrator_cli.py agents
  
  # Show tasks
  python orchestrator_cli.py tasks --status pending
        """
    )
    
    parser.add_argument(
        '--provider',
        default='mock',
        choices=['openai', 'anthropic', 'mock'],
        help='LLM provider'
    )
    parser.add_argument(
        '--model',
        default='gpt-4',
        help='LLM model name'
    )
    parser.add_argument(
        '--api-key',
        help='LLM API key (or set OPENAI_API_KEY/ANTHROPIC_API_KEY env var)'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Orchestrate command
    orchestrate_parser = subparsers.add_parser('orchestrate', help='Orchestrate a query')
    orchestrate_parser.add_argument('query', help='Natural language query')
    orchestrate_parser.add_argument('--context', help='JSON context')
    orchestrate_parser.add_argument('--output', help='Output file for result')
    orchestrate_parser.set_defaults(func=lambda args: asyncio.run(cmd_orchestrate(args)))
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Get orchestrator status')
    status_parser.set_defaults(func=cmd_status)
    
    # Agents command
    agents_parser = subparsers.add_parser('agents', help='List agents')
    agents_parser.set_defaults(func=cmd_agents)
    
    # Tasks command
    tasks_parser = subparsers.add_parser('tasks', help='List tasks')
    tasks_parser.add_argument('--status', help='Filter by status')
    tasks_parser.set_defaults(func=cmd_tasks)
    
    # History command
    history_parser = subparsers.add_parser('history', help='Show execution history')
    history_parser.add_argument('--limit', type=int, default=10, help='Limit results')
    history_parser.set_defaults(func=cmd_history)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    args.func(args)


if __name__ == "__main__":
    main()
