#!/usr/bin/env python3
"""Human CLI for Guild AI — publish quests, listen for work, check status.

Usage
-----
    guild publish "title" "description" --reward 0.0005 --capabilities research
    guild listen
    guild status
    guild manifest
    guild quests
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timezone
from typing import Any

from guild.agent import GuildAgent
from guild.orchestrator import GuildOrchestrator
from guild.schema import (
    QuestAccept,
    QuestError,
    QuestHeartbeat,
    QuestPublish,
    HeartbeatStatus,
    validate_message,
)
from guild.transport import Transport


# ---------------------------------------------------------------------------
# Styling helpers
# ---------------------------------------------------------------------------

_RESET = "\033[0m"
_BOLD = "\033[1m"
_DIM = "\033[2m"
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_CYAN = "\033[36m"
_RED = "\033[31m"


def _hdr(text: str) -> str:
    return f"{_BOLD}{_CYAN}{text}{_RESET}" if sys.stdout.isatty() else text


def _ok(text: str) -> str:
    return f"{_GREEN}{text}{_RESET}" if sys.stdout.isatty() else text


def _warn(text: str) -> str:
    return f"{_YELLOW}{text}{_RESET}" if sys.stdout.isatty() else text


def _dim(text: str) -> str:
    return f"{_DIM}{text}{_RESET}" if sys.stdout.isatty() else text


# ---------------------------------------------------------------------------
# CLI transport — in-memory / print-to-stdout for interactive use
# ---------------------------------------------------------------------------


class _CliTransport(Transport):
    """Minimal transport that logs outgoing messages and discards incoming."""

    def __init__(self) -> None:
        self.agent_id = "cli"
        self._inbox: list[dict] = []

    def send(self, msg: Any, *, recipient: str | None = None) -> bool:
        print(_dim(f"  [tx → {recipient or 'guild'}] {type(msg).__name__}"))
        return True

    def receive(self, timeout: int = 30) -> list[dict]:
        items = list(self._inbox)
        self._inbox.clear()
        return items


# ---------------------------------------------------------------------------
# Subcommand implementations
# ---------------------------------------------------------------------------


def cmd_publish(args: argparse.Namespace) -> None:
    """guild publish"""
    orch = GuildOrchestrator(agent_id=args.agent_id, transport=_CliTransport())
    caps = args.capabilities.split(",") if args.capabilities else []

    quest_id = orch.publish_quest(
        title=args.title,
        description=args.description,
        reward=str(args.reward) if args.reward else "",
        bond=str(args.bond) if args.bond else "",
        max_duration=args.max_duration,
        required_capabilities=caps,
        output_schema=args.schema or {},
    )

    print(_hdr(f"\n  🏆  Published quest"))
    print(f"  ID:    {quest_id}")
    print(f"  Title: {args.title}")
    print(f"  Reward:  {args.reward}")
    print(f"  Bond:    {args.bond}")
    print(f"  Caps:    {', '.join(caps) or _dim('(none)')}")

    if args.wait:
        print(_dim("\n  Waiting for acceptance..."))
        accept = orch.await_acceptance(quest_id, timeout=args.wait)
        if accept is None:
            print(_warn("  ⏱  No acceptance within timeout."))
        else:
            print(_ok(f"  ✅ Accepted by {accept.agent} (bond_tx: {accept.bond_tx})"))

        print(_dim("  Waiting for delivery..."))
        delivery = orch.await_delivery(quest_id, timeout=args.max_duration + 60)
        if delivery is None:
            print(_warn("  ⏱  No delivery within timeout."))
        else:
            print(_ok(f"  📦 Delivered: {delivery.summary}"))
    print()


def cmd_listen(args: argparse.Namespace) -> None:
    """guild listen"""
    agent = GuildAgent(
        agent_id=args.agent_id,
        capabilities=args.capabilities.split(",") if args.capabilities else [],
        transport=_CliTransport(),
    )

    print(_hdr(f"\n  🎧  Listening for quests (agent: {agent.agent_id})"))
    print(_dim("  Press Ctrl+C to stop.\n"))

    try:
        while True:
            raw = agent.listen(timeout=10)
            for d in raw:
                msg = validate_message(d)
                if msg is None:
                    continue
                title = getattr(msg, "title", "") or ""
                print(_ok(f"  📩  {type(msg).__name__}: {title}"))
                if isinstance(msg, QuestPublish):
                    response = agent.handle_quest(msg)
                    tag = "✅ accepted" if isinstance(response, QuestAccept) else "❌ declined"
                    print(f"  ↳  {tag}")
                    agent.transport.send(response, recipient=args.agent_id)
            time.sleep(1)
    except KeyboardInterrupt:
        print(_dim("\n  Stopped."))


def cmd_status(args: argparse.Namespace) -> None:
    """guild status"""
    agent = GuildAgent(
        agent_id=args.agent_id,
        capabilities=args.capabilities.split(",") if args.capabilities else [],
        transport=_CliTransport(),
    )

    print(_hdr(f"\n  Agent Status: {agent.agent_id}\n"))
    print(f"  Capabilities: {_ok(', '.join(agent.capabilities))}")
    print(f"  Active quests: {len(agent.active_quests)}")
    for qid, info in agent.active_quests.items():
        print(f"    • {qid}: {info.get('state', 'unknown')}")
    if not agent.active_quests:
        print(_dim("    (none)"))
    print()


def cmd_manifest(args: argparse.Namespace) -> None:
    """guild manifest"""
    agent = GuildAgent(
        agent_id=args.agent_id,
        capabilities=args.capabilities.split(",") if args.capabilities else [],
        transport=_CliTransport(),
    )
    manifest = agent.get_manifest()
    print(_hdr(f"\n  Manifest: {manifest['agent_id']}\n"))
    for cap in manifest.get("capabilities", []):
        print(f"    ✅ {cap}")
    if not manifest.get("capabilities"):
        print(_dim("    (no capabilities registered)"))
    print()


def cmd_quests(args: argparse.Namespace) -> None:
    """guild quests"""
    print(_hdr("\n  Quest History"))
    print(_dim("    (backed by persistent storage — coming soon)"))
    print()


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument(
        "--agent-id", default="cli-agent",
        help="Agent / orchestrator identifier (default: cli-agent).",
    )
    shared.add_argument(
        "--capabilities", default="",
        help="Comma-separated capability list (e.g. research,code,analyze).",
    )

    parser = argparse.ArgumentParser(
        prog="guild",
        description="Guild AI — agent quest protocol CLI.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_get_epilog(),
        parents=[shared],
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # --- publish ------------------------------------------------------------
    p = sub.add_parser("publish", parents=[shared], help="Publish a new quest.")
    p.add_argument("title")
    p.add_argument("description")
    p.add_argument("--reward", type=str, default="", help="Reward string e.g. 0.001_ETH")
    p.add_argument("--bond", type=str, default="", help="Bond string e.g. 0.0001_ETH")
    p.add_argument("--max-duration", type=int, default=3600)
    p.add_argument("--schema", type=_json_load, default=None, help="JSON output schema")
    p.add_argument("--wait", type=int, default=0, help="Wait N seconds for acceptance")
    p.set_defaults(func=cmd_publish)

    # --- listen / status / manifest / quests --------------------------------
    for name in ("listen", "status", "manifest", "quests"):
        q = sub.add_parser(name, parents=[shared], help=name.capitalize())
        q.set_defaults(func=globals()[f"cmd_{name}"])

    return parser


def _get_epilog() -> str:
    return """\
Examples:
  guild publish "Research LLVM passes" "Find all..." --reward 0.0005 --capabilities research
  guild listen --agent-id my-bot --capabilities research,code
  guild status
  guild manifest
"""


def _json_load(raw: str) -> dict | None:
    import json

    return json.loads(raw) if raw.strip() else None


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
