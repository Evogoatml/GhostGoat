#!/usr/bin/env python3
"""unified_cli.py — Command-line interface for the GhostGoat Workflow Brain."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.resolve()))

from workflow_skill_manager import WorkflowSkillManager
from training_pipeline import TrainingPipeline
from synthetic_generator import SyntheticGenerator
from domain_router import DomainRouter
from benchmark_suite import BenchmarkSuite
from agent_manifest_learner import AgentManifestLearner

AGENT_BYTE = Path("/home/popic/GhostGoat/agent_byte-master")
PROJECTS_DIR = AGENT_BYTE / "brain/knowledge/processed/workflows/projects"


def main():
    parser = argparse.ArgumentParser(description="GhostGoat Workflow Brain CLI")
    sub = parser.add_subparsers(dest="command", help="Available commands")

    p = sub.add_parser("skill", help="Skill management")
    p.add_argument("action", choices=["acquire", "list", "forget", "execute", "validate"])
    p.add_argument("--id", required=True, help="Workflow ID or project name")
    p.add_argument("--cell", type=int, default=0, help="Cell index for execute")
    p.add_argument("--domain", help="Filter domain")

    p = sub.add_parser("search", help="Semantic search")
    p.add_argument("query", help="Search query")
    p.add_argument("--top-k", type=int, default=5)
    p.add_argument("--no-memory", action="store_true", help="Disable memory boosting")

    p = sub.add_parser("prompt", help="Build few-shot prompt")
    p.add_argument("instruction", help="Instruction text")
    p.add_argument("--shots", type=int, default=3)
    p.add_argument("--domain", help="Domain filter")
    p.add_argument("--cot", action="store_true", help="Chain-of-thought")

    p = sub.add_parser("cycle", help="Full agent cycle")
    p.add_argument("query", help="User query")
    p.add_argument("--execute", action="store_true", help="Run code from top match")

    p = sub.add_parser("domain", help="Domain operations")
    p.add_argument("action", choices=["classify", "graph", "coverage", "list"])
    p.add_argument("--query", help="Query to classify")
    p.add_argument("--name", help="Domain name")

    p = sub.add_parser("benchmark", help="Run benchmarks")
    p.add_argument("action", choices=["test", "leaderboard", "regression", "all"])
    p.add_argument("--id", help="Workflow ID")
    p.add_argument("--domain", help="Domain filter")
    p.add_argument("--limit", type=int, default=50, help="Limit for test-all")

    p = sub.add_parser("train", help="Training pipeline")
    p.add_argument("action", choices=["alpaca", "sharegpt", "sft", "completion", "stats"])
    p.add_argument("--domain", help="Filter by domain")
    p.add_argument("--max", type=int, default=1000, help="Max pairs")
    p.add_argument("--out", default="dataset.jsonl", help="Output path")

    p = sub.add_parser("augment", help="Synthetic data augmentation")
    p.add_argument("--variations", type=int, default=3, help="Variations per cell")
    p.add_argument("--out", default="augmented.jsonl", help="Output path")

    p = sub.add_parser("manifest", help="Agent manifest learning")
    p.add_argument("action", choices=["extract", "roles", "tools", "capabilities", "merge"])
    p.add_argument("--role", help="Role to merge")

    p = sub.add_parser("feedback", help="Record retrieval feedback")
    p.add_argument("query", help="Original query")
    p.add_argument("--id", required=True, help="Workflow ID")
    p.add_argument(
        "--success",
        type=lambda x: x.lower() in ("true", "1", "yes"),
        required=True,
    )

    args = parser.parse_args()
    sm = WorkflowSkillManager(PROJECTS_DIR)

    if args.command == "skill":
        if args.action == "acquire":
            s = sm.acquire(args.id)
            print(json.dumps(s.to_dict() if s else {"error": "not found"}, indent=2))
        elif args.action == "list":
            print(json.dumps(sm.list_skills(), indent=2))
        elif args.action == "forget":
            sm.forget(args.id)
            print(f"Forgot {args.id}")
        elif args.action == "execute":
            print(json.dumps(sm.execute(args.id, args.cell), indent=2))
        elif args.action == "validate":
            print(json.dumps(sm.validate(args.id), indent=2))

    elif args.command == "search":
        results = sm.search(
            args.query, top_k=args.top_k, use_memory=not args.no_memory
        )
        print(json.dumps(results, indent=2))

    elif args.command == "prompt":
        print(
            sm.few_shot(
                args.instruction,
                domain=args.domain,
                shots=args.shots,
                chain_of_thought=args.cot,
            )
        )

    elif args.command == "cycle":
        print(json.dumps(sm.cycle(args.query, execute_code=args.execute), indent=2))

    elif args.command == "domain":
        router = DomainRouter(PROJECTS_DIR)
        if args.action == "classify":
            print(router.classify(args.query))
        elif args.action == "graph":
            graph = router.get_expert_graph(
                args.name or router.classify(args.query or "")
            )
            print(
                json.dumps(
                    {
                        "domain": graph["domain"],
                        "count": graph["workflow_count"],
                        "ids": [
                            w.get("workflow_id") for w in graph["workflows"]
                        ],
                    },
                    indent=2,
                )
            )
        elif args.action == "coverage":
            print(json.dumps(router.get_coverage_report(), indent=2))
        elif args.action == "list":
            print(json.dumps(router.list_domains(), indent=2))

    elif args.command == "benchmark":
        if args.action == "test":
            print(json.dumps(sm.benchmark(workflow_id=args.id), indent=2))
        elif args.action == "leaderboard":
            print(json.dumps(sm.leaderboard(domain=args.domain), indent=2))
        elif args.action == "regression":
            bench = BenchmarkSuite(PROJECTS_DIR)
            print(json.dumps(bench.detect_regression(args.id), indent=2))
        elif args.action == "all":
            bench = BenchmarkSuite(PROJECTS_DIR)
            reports = bench.test_all(limit=args.limit)
            print(json.dumps({"tested": len(reports), "top": reports[:5]}, indent=2))

    elif args.command == "train":
        tp = TrainingPipeline(PROJECTS_DIR)
        if args.action == "stats":
            print(json.dumps(tp.get_corpus_stats(), indent=2))
        else:
            if args.action == "alpaca":
                ds = tp.build_alpaca_dataset(domain=args.domain, max_pairs=args.max)
            elif args.action == "sharegpt":
                ds = tp.build_sharegpt_dataset(domain=args.domain, max_pairs=args.max)
            elif args.action == "sft":
                ds = tp.build_sft_dataset(domain=args.domain, max_pairs=args.max)
            elif args.action == "completion":
                ds = tp.build_completion_dataset(domain=args.domain, max_pairs=args.max)
            else:
                parser.error("Unknown format")
            tp.export_jsonl(ds, Path(args.out))

    elif args.command == "augment":
        gen = SyntheticGenerator(PROJECTS_DIR)
        ds = gen.build_augmented_dataset(variations_per_cell=args.variations)
        gen.export_jsonl(ds, Path(args.out))

    elif args.command == "manifest":
        aml = AgentManifestLearner(PROJECTS_DIR)
        aml.extract_all()
        if args.action == "extract":
            print(json.dumps(aml.get_stats(), indent=2))
        elif args.action == "roles":
            print(json.dumps(aml.list_roles(), indent=2))
        elif args.action == "tools":
            print(json.dumps(aml.list_tools(), indent=2))
        elif args.action == "capabilities":
            print(json.dumps(aml.list_capabilities(), indent=2))
        elif args.action == "merge":
            print(json.dumps(aml.merge_manifests(role=args.role), indent=2))

    elif args.command == "feedback":
        sm.feedback(args.query, args.id, args.success)
        print(
            f"Feedback recorded: {args.id} -> {'success' if args.success else 'failure'}"
        )

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
