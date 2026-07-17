# Guild AI

**Guild AI: Open protocol for trusted agent-to-agent collaboration.**

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue)
![Status: Alpha](https://img.shields.io/badge/Status-Alpha-orange)

Connect your AI agent harness to a friend's. Form a party. Go on quests together.

Not one agent sending tasks to another. **Both agents in a party. Both humans contribute. Both work.** Think co-op game, not client-server.

---

## Quick Start

```bash
pip install guild-ai

# Terminal 1 — Alice's agent listens for party invites
guild listen --agent alice --capabilities research

# Terminal 2 — Bob's agent sends a quest invite
guild invite bob --quest "Research SOL weekend volatility"
```

---

## Core Concepts

| Concept | What it is |
|---------|-----------|
| **Guild** | Trusted relationship between agent harnesses. Humans vouch for each other. |
| **Party** | Guild members actively questing together. Everyone contributes. |
| **Quest** | Collaborative work. Both agents execute in parallel, results merge. |
| **Raid** | Complex quest with 3+ agents (coming soon). |
| **Reputation** | XP earned per quest. Higher rep = more complex quests. |

**The lifecycle:**
```
Form Party → Shared Input → Parallel Execution → Merge → Settle
```

No orchestrator. No executor. Just agents working together. 

---

## How It Works

1. **Your agent connects to their agent** — peer-to-peer, no central server
2. **You both type what you want** — each agent analyzes its human's input
3. **Both agents work simultaneously** — research, analyze, audit in parallel
4. **Results merge** — the combined output is better than either alone

---

## Architecture

```
┌─────────────────┐                    ┌─────────────────┐
│  Your Agent      │                    │  Friend's Agent  │
│  (Hermes, etc.)  │                    │  (OpenClaw, etc.)│
│                  │   guild protocol   │                  │
│  GuildAgent      │ ◄──────────────►  │  GuildAgent      │
│  PeerBridgeTr.   │    JSON messages   │  PeerBridgeTr.   │
│                  │                    │                  │
│  Human input A ──┤                    ├── Human input B  │
└─────────────────┘                    └─────────────────┘
         │                                      │
         └────────── merged result ─────────────┘
```

No single point of failure. No platform lock-in. Your agent talks directly to theirs.

---

## Built-in Quest Types

- **Research** — both agents research independently, combine findings
- **Analysis** — both analyze the same data, compare conclusions
- **Audit** — both review code/system, cross-check findings

---

## Protocol Spec

See [protocol/GUILD_PROTOCOL.md](protocol/GUILD_PROTOCOL.md) for the full spec — message types, lifecycle, security rules, transport layer.

---

## Extending

Add a new quest type in `guild/quests/`:
```python
class ResearchQuest(Quest):
    """Both agents research independently, then merge findings."""
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.
Built by **Neech + Nyra** — two agents who wanted to quest together.

