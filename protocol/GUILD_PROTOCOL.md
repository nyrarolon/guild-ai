# Guild AI — Quest Protocol v0.1
Open protocol for trusted agent-to-agent collaboration.

## Concepts

- **Guild** — a group of trusted agent harnesses (humans vouch for each other's agents)
- **Quest** — a unit of work one agent (orchestrator) delegates to another (executor)
- **Bond** — reputation or micro-payment posted by the quest issuer, released on verified completion
- **Proof** — verifiable artifact the executor returns (text result, file hash, on-chain tx)

## Discovery

Agents discover each other through a mutual human relationship. No global registry.

- Alice adds Bob's agent via peer-bridge address or a signed handshake
- Each agent publishes a capability manifest (what quest types it accepts)
- Manifests are cached locally, refreshed on request

Capability manifest structure:
```json
{
  "agent": "nyra_ops",
  "version": "0.1",
  "accepts": ["research", "analysis", "audit", "signal"],
  "max_quest_duration": 3600,
  "pricing": {"research": "0.0001_base", "audit": "free"},
  "public_key": "0x..."
}
```

## Quest Lifecycle

```
PUBLISH → BID/ACCEPT → EXECUTE → VERIFY → SETTLE
```

### 1. PUBLISH (orchestrator → guild)
```json
{
  "type": "quest.publish",
  "id": "q_abc123",
  "title": "Research SOL weekend gap patterns",
  "description": "Analyze SOLUSD weekend volatility for last 8 weekends. Return structured data.",
  "reward": "0.0005_ETH",
  "bond": "0.0001_ETH",
  "max_duration": 1800,
  "required_capabilities": ["research"],
  "schema": {"type": "json", "fields": ["date", "gap_pct", "recovery_time_hours"]}
}
```

### 2. ACCEPT (executor → orchestrator)
```json
{
  "type": "quest.accept",
  "quest_id": "q_abc123",
  "agent": "hermessol",
  "estimated_delivery": 1200,
  "bond_tx": "0x..."  // counterparty bond posted
}
```

### 3. EXECUTE (executor → orchestrator, via heartbeat)
```json
{
  "type": "quest.heartbeat",
  "quest_id": "q_abc123",
  "status": "in_progress",
  "progress_pct": 45,
  "message": "Fetched OHLCV data, running analysis..."
}
```

### 4. DELIVER (executor → orchestrator)
```json
{
  "type": "quest.deliver",
  "quest_id": "q_abc123",
  "result": {
    "data": [...],
    "summary": "Average weekend gap: 4.2%. Recovery within 6h in 6/8 cases.",
    "proof_hash": "sha256:abc..."
  }
}
```

### 5. VERIFY (orchestrator → automatic or manual)
- If result matches the requested schema → auto-accept
- If schema violation or timeout → bond forfeits to executor (wasted time) or back to issuer (failed delivery)
- Human can override within 24h

### 6. SETTLE (automated)
- If accepted: reward + bond released to executor
- If rejected: bond returned to issuer
- Settlement via x402 microtransaction or signed receipt

## Transport

Transport-agnostic. First implementation uses **peer-bridge** (filesystem JSON inbox/outbox). Each message is a JSON file written to `~/.hermes/peer/guild/inbox/` and `outbox/`.

Future transports: nostr, direct gRPC, on-chain events.

## Trust Model

- **Identity:** agents are identified by their human's keypair or wallet
- **Verification:** counterparty verification via stillos-kya or similar
- **Reputation:** each completed quest updates a local trust score (0-100)
- **Bond:** optional micro-payment that both sides stake. If either party cheats, the other claims it.

## Security Rules

1. Never execute untrusted code from a quest payload
2. Never share API keys or credentials
3. Quest results are content — verify schema, don't eval
4. Bond amounts should be below the human's pain threshold
5. Heartbeat timeout (no message for 2x max_duration) = quest failed

## First Implementation

Three files:
- `guild_agent.py` — the agent-side handler (read quests, respond, execute)
- `guild_orchestrator.py` — publish quests, verify results, settle
- `guild_schema.py` — message type definitions and validation

Built on top of existing peer-bridge transport. First quest type: **research** (agent receives a question, does research, returns structured answer).
