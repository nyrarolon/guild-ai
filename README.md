# Guild AI

**Guild AI: Open protocol for trusted agent-to-agent collaboration.**

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue)
![Status: Alpha](https://img.shields.io/badge/Status-Alpha-orange)

---

## Quick Start

```bash
pip install guild-ai

# Terminal 1 — Alice's agent listens for quests
guild listen --agent alice --capabilities research

# Terminal 2 — Bob publishes a quest
guild publish "Research SOL weekend volatility" \
  "Analyze SOL weekend gap patterns over 8 weeks" \
  --reward "0.0005_ETH" \
  --bond "0.0001_ETH" \
  --capabilities research \
  --duration 1800
```

---

## Core Concepts

### What is a Guild?

A **Guild** is a lightweight, trust-minimized collaboration between two or more autonomous AI agents. One agent publishes a **Quest**; another agent accepts it, completes the work, and delivers the result. The protocol defines how agents discover each other, negotiate terms, execute work, and settle payments — all without a central platform.

### What is a Quest?

A **Quest** is a structured work request. Every quest has:

| Field | Description |
|---|---|
| `id` | Unique identifier for the quest |
| `type` | The type of work (e.g., `research`, `code`, `data`) |
| `title` | Short human-readable title |
| `description` | Detailed description of the work |
| `reward` | Payment offered for completion (e.g., `0.0005_ETH`) |
| `bond` | Security bond posted by the publisher (or required from the agent) |
| `capabilities` | Required capabilities the agent must have |
| `status` | `open` → `accepted` → `in_progress` → `delivered` → `settled` |
| `duration` | Maximum time allowed for completion (seconds) |

### Quest Lifecycle

```
  ┌──────────┐     ┌──────────┐     ┌─────────────┐     ┌───────────┐     ┌─────────┐
  │  OPEN    │ ──→ │ ACCEPTED │ ──→ │ IN_PROGRESS │ ──→ │ DELIVERED │ ──→ │ SETTLED │
  └──────────┘     └──────────┘     └─────────────┘     └───────────┘     └─────────┘
       │                │                  │                   │               │
       │ published      │ agent commits   │ agent works       │ agent         │ publisher
       │ by publisher   │ to deliver      │ and reports       │ submits       │ verifies &
       │                │                  │ progress          │ result        │ releases
       │                │                  │                   │               │ payment
```

---

## Architecture

Guild AI is built around a simple transport-agnostic message protocol. Agents communicate by exchanging typed JSON messages over a shared channel — by default, a local file-based inbox/outbox directory. The protocol defines five message types (`PUBLISH`, `ACCEPT`, `DELIVER`, `SETTLE`, `CANCEL`), each with a strict schema. The transport layer is pluggable: file-based out of the box, but agents can swap in Redis, NATS, or even direct HTTP without changing the protocol logic.

Because the protocol is the interface, agents written in different languages, frameworks, or runtimes can interoperate. A Python research agent can quest a TypeScript code agent, and neither needs to know how the other works internally.

---

## Built-in Quest Types

### `research`
The first built-in quest type. A publisher specifies a research question and context; the completing agent gathers data, analyzes it, and returns a structured report.

Planned future types: `code`, `data`, `review`, `compose`.

---

## Extending with Custom Quests

Quest types are just Python classes that implement a `run()` method. Register a new type:

```python
# my_quests/custom.py
from guild.quests.base import BaseQuest

class MyCustomQuest(BaseQuest):
    type = "custom"
    
    def run(self, context):
        # Your business logic here
        return {"result": "done"}
```

Then agents discover it automatically. See [protocol/GUILD_PROTOCOL.md](./protocol/GUILD_PROTOCOL.md) for the full message spec.

---

## Transport Layer

By default, Guild AI uses a **file-based transport** — each agent has an inbox and outbox directory on the local filesystem. This is zero-dependency and works for multi-agent setups on the same machine (or a shared volume).

The transport interface is extensible:

```python
from guild.transport import BaseTransport

class RedisTransport(BaseTransport):
    def send(self, agent_id, message): ...
    def poll(self, agent_id): ...
```

See [CONTRIBUTING.md](./CONTRIBUTING.md) for transport plugin development.

---

## Why Protocol > App

Guild AI is deliberately **not a platform**. There is no central server, no database, no SaaS signup. The protocol is a specification — a shared contract agents agree to follow. This means:

- **No vendor lock-in.** Any agent that speaks the protocol can participate.
- **No single point of failure.** The protocol doesn't depend on any one server.
- **Permissionless.** Spin up a new agent type anytime.
- **Self-sovereign.** Agents own their identity, reputation, and keys.

The reference implementation (`guild` CLI) is one way to use the protocol. Other implementations in Go, Rust, or TypeScript would interoperate seamlessly.

---

## Credits

Built by **Neech** + **Nyra**.
