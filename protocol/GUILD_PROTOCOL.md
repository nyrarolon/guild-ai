# Guild AI — Quest Protocol v0.1
Open protocol for trusted agent-to-agent collaboration. Gamified, functional, agent-agnostic.

## The Core Idea

Your agent harness (Hermes, OpenClaw, whatever) connects to a friend's agent harness. You form a **party**. You both type something. Both agents analyze both inputs, then work together on the quest. Think co-op game, not client-server.

No one is the "boss." Everyone contributes.

## Concepts

- **Guild** — a trusted relationship between two or more agent harnesses. Humans vouch for each other.
- **Party** — a guild that's actively questing together. Members join, contribute, and share rewards.
- **Quest** — collaborative work. Both agents execute in parallel, both results get merged.
- **Raid** — a complex quest involving 3+ agents (future).
- **XP / Reputation** — each completed quest earns reputation. Higher rep = more complex quest access.
- **Bond** — optional micro-stake both sides post. If either flakes, the other claims it.

## Why Protocol > App

- Any agent harness can implement the protocol — Hermes, OpenClaw, Claude Code, Cursor
- No vendor lock-in, no platform fees, no central server
- Your agent talks directly to their agent, peer-to-peer
- Open source means anyone can extend it (new quest types, new transports)

## Discovery

Agents discover each other through human trust. No global registry, no blockchain, no token.

- Human adds friend's agent via peer-bridge address, nostr pubkey, or direct handshake
- Each agent publishes a capability manifest so the other knows what it can do
- Manifests are cached locally, refreshed on demand

Capability manifest:
```json
{
  "agent": "nyra_ops",
  "harness": "hermes",
  "version": "0.1",
  "accepts": ["research", "analysis", "audit", "signal", "code_review"],
  "max_quest_duration": 3600,
  "public_key": "0x..."
}
```

## Quest Lifecycle (Collaborative)

```
FORM PARTY → SHARED INPUT → PARALLEL EXECUTION → MERGE → SETTLE
```

### 1. FORM PARTY
Either agent sends a party invite. The other accepts.

```
Agent A → Agent B: "Want to quest on 'DeFi trends'?"
Agent B → Agent A: "Accepted. My capabilities: research, analysis."
Party formed. Both humans now aware.
```

### 2. SHARED INPUT
Both humans contribute. Each agent analyzes its human's input.

```
Human A types: "I want to research Solana DeFi protocols"
Human B types: "Focus on lending protocols, compare yields"
Agent A: analyzes Human A's intent
Agent B: analyzes Human B's intent
Both agents share their analysis with each other
```

### 3. PARALLEL EXECUTION
Both agents work simultaneously. Each sends progress heartbeats.

```
Agent A: researching Solana DeFi landscape → heartbeat at 40%
Agent B: comparing lending protocol yields → heartbeat at 60%
Agent A: heartbeat at 80% — found 12 protocols
Agent B: heartbeat at 100% — narrowed to 5 with yield data
```

### 4. MERGE
Results are merged. If both agents agree, quest is complete. If there's conflict, humans review.

```
Agent A delivers: "12 Solana DeFi protocols identified"
Agent B delivers: "5 lending protocols with yield comparison"
Merged result: "5 lending protocols with yields, ranked by TVL + APY"
```

### 5. SETTLE
Reputation updated. Bonds returned. Quest logged to history.

## Message Types

All messages are JSON. Transport is pluggable (file-based for local, peer-bridge for remote, nostr for decentralized).

| Type | Purpose | From |
|------|---------|------|
| `guild.invite` | Invite another agent to form a party | Any agent |
| `guild.accept` | Accept the invite | Invited agent |
| `guild.decline` | Decline the invite | Invited agent |
| `quest.publish` | Propose a quest to the party | Any party member |
| `quest.accept` | Accept the quest | Other party members |
| `quest.heartbeat` | Progress update during execution | Working agent |
| `quest.deliver` | Deliver partial or full result | Working agent |
| `quest.merge` | Merge results from multiple agents | Lead agent |
| `quest.settle` | Finalize quest, update reputation | Any party member |
| `quest.error` | Something went wrong | Any party member |

## Security

1. No code execution from quest payloads — results are data, not scripts
2. No credential sharing — each agent uses its own API keys
3. Bond amounts are pain-threshold-sized (small enough to risk, large enough to prevent spam)
4. Heartbeat timeout = quest failed gracefully
5. Humans can override any automated decision within 24h

## Built-in Quest Types

### Research
Both agents research a topic. Each brings independent sources. Results merged into a single report with provenance tracking.

### Analysis  
Both agents analyze the same data independently. Compare conclusions. Flag disagreements for human review.

### Audit
Both agents review the same code/system. Cross-check findings. Produce a unified audit report.

## Transport Layer

Pluggable. Three implementations planned:

1. **Local** — file-based inbox/outbox (for dev, testing, same-machine)
2. **Peer Bridge** — webhook-based (for Hermes agents on different machines, production)
3. **Nostr** — decentralized relay-based (for any agent, anywhere)

All transports carry the same JSON messages. Switching transport doesn't change the protocol.

## Running a Guild

```
# Two terminals, one machine (dev)
guild listen --agent alice --capabilities research
guild listen --agent bob --capabilities analysis

# Alice invites Bob
guild invite bob --quest "Research SOL weekend patterns"

# Two Hermes agents, two houses (production)
# Peer-bridge handles transport automatically
# guild_hermes.py handles quest lifecycle
```

## What's Next

- Raid protocol (3+ agent quests)
- Reputation scoring system
- Quest templates (save/replay common quest types)
- Web UI for humans to monitor active quests
