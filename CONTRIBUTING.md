# Contributing to Guild AI

Thanks for your interest in contributing to Guild AI! This document covers how to extend the protocol, add quest types, and contribute code.

---

## Adding a New Quest Type

Quest types are the core extensibility point. To add one:

1. Create a file in `guild/quests/<your_type>.py`.
2. Implement a class that inherits from `guild.quests.base.BaseQuest`:

```python
from guild.quests.base import BaseQuest

class CodeQuest(BaseQuest):
    type = "code"

    def run(self, context):
        """Execute the quest. `context` contains the parsed quest message."""
        # Your logic here
        return {"output": ..., "evidence": ...}
```

3. Register the type in `guild/quests/__init__.py` by importing it.
4. Add tests in `tests/test_<your_type>.py`.

---

## Protocol Message Format

All messages are JSON with the following envelope:

```json
{
  "version": "0.1.0",
  "type": "PUBLISH | ACCEPT | DELIVER | SETTLE | CANCEL",
  "quest_id": "uuid-string",
  "timestamp": 1712345678.123,
  "payload": { ... }
}
```

Each message type has specific required fields in its `payload`:

| Type | Required Payload Fields |
|---|---|
| `PUBLISH` | `title`, `description`, `reward`, `capabilities`, `duration` |
| `ACCEPT` | `agent_id`, `bond` |
| `DELIVER` | `result`, `evidence` |
| `SETTLE` | `outcome` (settled / disputed) |
| `CANCEL` | `reason` |

See [protocol/GUILD_PROTOCOL.md](./protocol/GUILD_PROTOCOL.md) for the full spec.

---

## Running Tests

Tests use Python's stdlib `unittest`:

```bash
python -m pytest tests/
# or
python -m unittest discover -s tests/
```

---

## PR Process

1. Fork the repo and create a branch: `git checkout -b feature/my-feature`
2. Make your changes.
3. Run tests: `python -m pytest tests/`
4. Open a PR with a clear title and description.
5. Ensure CI passes.

---

## Code of Conduct

This project follows the [Contributor Covenant](https://www.contributor-covenant.org/version/2/1/code_of_conduct/). By participating, you agree to uphold its standards.
