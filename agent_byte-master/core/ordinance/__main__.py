"""
python -m core.ordinance [--root DIR] [--watch] [--poll SECS] [--list]
"""
import argparse
import logging
import os

logging.basicConfig(level=logging.INFO, format="%(message)s")


def main():
    parser = argparse.ArgumentParser(
        prog="python -m core.ordinance",
        description="GhostGoat Distributed Agent System — generate AGENT.md in every folder",
    )
    parser.add_argument("--root",  default=os.getcwd(),
                        help="Root directory to scan (default: cwd)")
    parser.add_argument("--watch", action="store_true",
                        help="Keep running and re-scan on file changes")
    parser.add_argument("--poll",  type=float, default=30,
                        help="Seconds between polls in watch mode (default: 30)")
    parser.add_argument("--list",  action="store_true",
                        help="List registered agents and exit")
    args = parser.parse_args()

    from core.ordinance.distributed_system import DistributedAgentSystem
    system = DistributedAgentSystem(root_dir=args.root)

    if args.list:
        agents = system.list_agents()
        if not agents:
            print("No agents registered yet. Run without --list to scan first.")
            return
        print(f"\n{'ID':10} {'Folder':50} {'Updated':20}")
        print("-" * 82)
        for a in agents:
            print(f"{a['agent_id']:10} {a['folder']:50} {a['updated']:20}")
        return

    stats = system.scan()
    print(f"\n{'='*55}")
    print("  ORDINANCE SCAN COMPLETE")
    print(f"{'='*55}")
    print(f"  Root:         {stats['root']}")
    print(f"  Files indexed:{stats['files_indexed']:>6}")
    print(f"  Agents built: {stats['agents']:>6}")
    print(f"  Backend:      {stats['backend']}")
    print(f"{'='*55}")

    if args.watch:
        print(f"\n  Watching for changes (poll={args.poll:.0f}s). Ctrl+C to stop.\n")
        system.watch(poll_secs=args.poll)


if __name__ == "__main__":
    main()
