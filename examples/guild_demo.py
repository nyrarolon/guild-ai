#!/usr/bin/env python3
"""
Guild AI — Live Demo.

Simulates two agents (Alice and Bob) forming a party and completing
a research quest using the local file-based transport.

Run: python3 guild_demo.py
"""

import sys, os, json, time, hashlib, tempfile, shutil
from datetime import datetime
from pathlib import Path
from dataclasses import asdict

sys.path.insert(0, str(Path.home() / "projects" / "guild-ai"))
from guild.schema import *
from guild.transport import INBOX_DIR, OUTBOX_DIR, send_message, poll_inbox
from guild.agent import GuildAgent

# Use a temp directory for isolation
tmp = Path(tempfile.mkdtemp())
demo_inbox = tmp / "inbox"
demo_outbox = tmp / "outbox"

# Override transport paths
import guild.transport as t
t.INBOX_DIR = demo_inbox
t.OUTBOX_DIR = demo_outbox

def deliver(src, dst, msg_dict):
    """Move a message from one agent's outbox to another's inbox."""
    msg_type = msg_dict.get("type", "unknown").replace(".", "_")
    qid = msg_dict.get("quest_id", "unknown")
    fname = f"{qid}_{msg_type}_{time.time()}.json"
    dst_dir = demo_inbox / dst
    dst_dir.mkdir(parents=True, exist_ok=True)
    (dst_dir / fname).write_text(json.dumps(msg_dict, indent=2))

def relay(src, dst, msg_dict):
    """Send from src outbox to dst inbox."""
    deliver(src, dst, msg_dict)

print("=" * 60)
print("  GUILD AI — LIVE DEMO")
print("  Two agents questing together")
print("=" * 60)

# ── STEP 1: Alice listens ──
print("\n[1/6] Alice's agent comes online...")
alice = GuildAgent(agent_id="alice", capabilities=["research", "analysis"], transport=None)

print("\n  Alice's manifest:")
print(json.dumps(alice.get_manifest(), indent=2))

# ── STEP 2: Bob publishes a quest ──
print("\n[2/6] Bob publishes a collaborative research quest...")

quest = QuestPublish(
    quest_id="quest-sol-gaps-001",
    title="Analyze SOL weekend gap patterns",
    description="Research SOLUSD weekend volatility. Alice will analyze on-chain data. Bob will cross-reference with market events.",
    reward="reputation+1",
    bond="",
    max_duration=3600,
    required_capabilities=["research", "analysis"],
    output_schema={"type": "object", "properties": {"findings": "array", "summary": "string"}},
    created_at=datetime.utcnow().isoformat(),
)
print(f"\n  Quest: {quest.title}")
print(f"  ID:    {quest.quest_id}")

# Bob sends to Alice
relay("bob", "alice", asdict(quest))

# ── STEP 3: Alice receives and accepts ──
print("\n[3/6] Alice receives the quest...")
inbox = poll_inbox("alice")
print(f"  Incoming messages: {len(inbox)}")

for raw in inbox:
    parsed = validate_message(raw)
    if isinstance(parsed, QuestPublish):
        print(f"  Quest: {parsed.title}")
        response = alice.handle_quest(parsed)
        if isinstance(response, QuestAccept):
            print(f"  ✅ Alice accepted! Estimated delivery: {response.estimated_delivery}s")
            relay("alice", "bob", asdict(response))

# ── STEP 4: Bob receives acceptance ──
print("\n[4/6] Bob receives Alice's acceptance...")
bob_inbox = poll_inbox("bob")
for raw in bob_inbox:
    parsed = validate_message(raw)
    if isinstance(parsed, QuestAccept):
        print(f"  ✅ Bob sees: Alice accepted the quest!")
        print(f"  Agent: {parsed.agent}")

# ── STEP 5: Both work ──
print("\n[5/6] Both agents work on the quest...")

# Alice heartbeats progress
hb1 = QuestHeartbeat(quest_id=quest.quest_id, status="in_progress", progress_pct=50, message="Analyzed 8 weekends of SOL on-chain data. Found 6 gaps >5%.")
relay("alice", "bob", asdict(hb1))
print(f"  Alice: {hb1.message}")

# Bob heartbeats progress
hb2 = QuestHeartbeat(quest_id=quest.quest_id, status="in_progress", progress_pct=60, message="Cross-referenced market events. 4 gaps correspond to Fed minutes, 2 to weekend liquidity drops.")
relay("bob", "alice", asdict(hb2))
print(f"  Bob:   {hb2.message}")

time.sleep(0.5)

# Alice delivers her part
alice_result = {
    "findings": [
        {"date": "2026-07-12", "gap_pct": 6.2, "recovery_hours": 4},
        {"date": "2026-07-05", "gap_pct": 8.1, "recovery_hours": 6},
    ],
    "data_source": "kraken_ohlcv",
    "method": "high-low gap analysis over weekends",
}
alice_deliver = QuestDeliver(
    quest_id=quest.quest_id,
    result=alice_result,
    summary="Identified 6 weekend gaps >5% in SOL. Average recovery: 5.2 hours.",
    proof_hash=hashlib.sha256(json.dumps(alice_result, sort_keys=True).encode()).hexdigest(),
)
relay("alice", "bob", asdict(alice_deliver))
print(f"  Alice delivers: {alice_deliver.summary}")

# Bob delivers his part
bob_result = {
    "cross_references": [
        {"gap_date": "2026-07-12", "event": "Fed minutes release", "correlation": "high"},
        {"gap_date": "2026-07-05", "event": "Weekend liquidity drop", "correlation": "medium"},
    ],
    "data_source": "market_calendar_feed",
}
bob_deliver = QuestDeliver(
    quest_id=quest.quest_id,
    result=bob_result,
    summary="4 of 6 gaps correlate with known macro events. 2 are pure liquidity gaps.",
    proof_hash=hashlib.sha256(json.dumps(bob_result, sort_keys=True).encode()).hexdigest(),
)
relay("bob", "alice", asdict(bob_deliver))
print(f"  Bob delivers:   {bob_deliver.summary}")

# ── STEP 6: Merge ──
print("\n[6/6] Results merged...")
merged = {
    "quest": quest.title,
    "contributors": ["alice", "bob"],
    "merged_findings": alice_result["findings"] + bob_result["cross_references"],
    "summary": (
        f"Alice analyzed 8 weekends of SOL on-chain data, "
        f"found 6 gaps >5% with avg 5.2h recovery. "
        f"Bob cross-referenced market events: "
        f"4 gaps correlate with macro events (Fed, earnings), "
        f"2 are pure weekend liquidity gaps. "
        f"Combined insight: trade SOL weekend gaps with 4h mean-reversion window, "
        f"avoid holding through Fed weeks."
    ),
    "merged_by": "both agents",
}

print(f"\n  📋 MERGED RESULT:")
print(f"  {merged['summary']}")
print(f"\n  Contributors: {', '.join(merged['contributors'])}")

# Cleanup
shutil.rmtree(tmp)

print("\n" + "=" * 60)
print("  ✅ DEMO COMPLETE")
print("  Two agents, one quest, better together")
print("=" * 60)
print()
print("  GitHub: https://github.com/nyrarolon/guild-ai")
print("  Protocol: protocol/GUILD_PROTOCOL.md")
print()
print("  Real production: replace file transport with PeerBridgeTransport")
