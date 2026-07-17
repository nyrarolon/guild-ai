"""
Guild AI — File-based Inbox/Outbox Transport.

Provides a simple file-based messaging layer for the Guild AI quest protocol.
Messages are written as JSON files to agent-specific inbox and outbox directories
under ``~/.hermes/peer/guild/``.

Inbox path:  ~/.hermes/peer/guild/inbox/<agent_id>/
Outbox path: ~/.hermes/peer/guild/outbox/<recipient_id>/
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("guild.transport")

# ── Default paths ──────────────────────────────────────────────────────────────

DEFAULT_BASE = Path.home() / ".hermes" / "peer" / "guild"

INBOX_DIR = DEFAULT_BASE / "inbox"
OUTBOX_DIR = DEFAULT_BASE / "outbox"


# ── Helpers ────────────────────────────────────────────────────────────────────


def _ensure_dir(path: Path) -> None:
    """Create a directory (and parents) if it doesn't exist."""
    path.mkdir(parents=True, exist_ok=True)


def _filename(message: dict[str, Any], timestamp: str) -> str:
    """
    Build a deterministic, sortable filename for a message.

    Format: ``<quest_id>_<type>_<timestamp>.json``

    Falls back to ``unknown`` for any missing field so the file is always
    nameable.
    """
    quest_id = message.get("quest_id", "unknown")
    msg_type = message.get("type", "unknown").replace(".", "_")
    return f"{quest_id}_{msg_type}_{timestamp}.json"


# ── Public API ─────────────────────────────────────────────────────────────────


def send_message(recipient_id: str, message: dict[str, Any]) -> bool:
    """
    Write a message to the outbox of a specific recipient.

    The message is serialised to JSON and written to::

        outbox/<recipient_id>/<quest_id>_<type>_<timestamp>.json

    Args:
        recipient_id: Identifier for the target agent (e.g. ``"nyra_ops"``).
        message: The message dict to send. Should include at least ``type``
            and ``quest_id`` (those used for the filename).

    Returns:
        True on success, False on any write error (logged).
    """
    # Inject a timestamp if not already present so filenames are meaningful
    timestamp = datetime.now(timezone.utc).isoformat()
    recipient_dir = OUTBOX_DIR / recipient_id
    filename = _filename(message, timestamp)
    filepath = recipient_dir / filename

    try:
        _ensure_dir(recipient_dir)
        with open(filepath, "w") as f:
            json.dump(message, f, indent=2, ensure_ascii=False, sort_keys=True)
        logger.debug(
            "Sent message to '%s': %s (%s bytes)",
            recipient_id,
            filepath,
            filepath.stat().st_size,
        )
        return True
    except OSError as exc:
        logger.error("Failed to write outbox message to %s: %s", filepath, exc)
        return False


def poll_inbox(agent_id: str) -> list[dict[str, Any]]:
    """
    Read all unprocessed messages from an agent's inbox.

    Reads every ``.json`` file from::

        inbox/<agent_id>/

    Returns messages parsed from JSON, sorted chronologically by filename
    (the filename encoding ensures lexical sort matches time order).

    Files that cannot be parsed as JSON are skipped with a warning.

    Args:
        agent_id: Identifier for this agent (messages are addressed to this).

    Returns:
        A list of parsed message dicts, newest last.
    """
    inbox_dir = INBOX_DIR / agent_id
    if not inbox_dir.is_dir():
        logger.debug("Inbox directory does not exist yet: %s", inbox_dir)
        return []

    messages: list[dict[str, Any]] = []

    try:
        # Sort lexically — filenames start with <quest_id>_<type>_<timestamp>
        # so lexical order equals chronological order.
        paths = sorted(inbox_dir.iterdir())
    except OSError as exc:
        logger.error("Failed to list inbox directory %s: %s", inbox_dir, exc)
        return []

    for filepath in paths:
        if not filepath.is_file() or filepath.suffix != ".json":
            continue
        # Skip already-processed files
        if filepath.name.startswith("_processed_"):
            continue

        try:
            with open(filepath) as f:
                msg = json.load(f)
            if not isinstance(msg, dict):
                logger.warning(
                    "Skipping non-dict content in %s", filepath
                )
                continue
            messages.append(msg)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to read/parse inbox message %s: %s", filepath, exc)

    return messages


# ── Adapter class for agent / orchestrator code ─────────────────────────────

class Transport:
    """Wrapper around the file-based guild transport that provides the
    ``send()`` / ``receive()`` interface expected by :class:`GuildAgent`
    and :class:`GuildOrchestrator`.

    Parameters
    ----------
    agent_id:
        This participant's own identifier.  Used to determine which
        inbox to poll on ``receive()`` and (optionally) which outbox
        to write to on ``send()``.
    """

    def __init__(self, agent_id: str) -> None:
        self.agent_id = agent_id

    def send(self, msg: Any, *, recipient: str | None = None) -> bool:
        """Send *msg* to *recipient* (or to the default guild peer).

        Parameters
        ----------
        msg:
            Message to deliver.  Converted to a dict via ``__dict__``
            or ``dataclasses.asdict`` before writing.
        recipient:
            Target agent id.  If ``None``, defaults to the orchestrator
            identifier ``"guild"`` (the well-known guild peer).

        Returns
        -------
        bool
            ``True`` if the write succeeded.
        """
        from dataclasses import asdict

        target = recipient or "guild"
        payload = asdict(msg) if hasattr(msg, "__dataclass_fields__") else dict(msg)
        return send_message(target, payload)

    def receive(self, timeout: int = 30) -> list[Any]:
        """Poll this agent's inbox for incoming messages.

        Parameters
        ----------
        timeout:
            Ignored in this file-based implementation (poll is
            non-blocking).  Included for interface compatibility.

        Returns
        -------
        list[Any]
            Parsed message dicts.
        """
        return poll_inbox(self.agent_id)


def mark_read(message_path: str) -> None:
    """
    Mark a message as processed by moving it to a ``_processed_`` location.

    The file is renamed to::

        <original_dir>/_processed_<original_filename>

    This avoids overwriting other files and keeps the processed messages
    co-located with the inbox for debugging.

    Args:
        message_path: Absolute or relative path to the message JSON file.

    Returns:
        None. Logs a warning if the move fails.
    """
    src = Path(message_path).expanduser().resolve()
    if not src.is_file():
        logger.warning("Cannot mark as read — file not found: %s", src)
        return

    processed_name = f"_processed_{src.name}"
    dst = src.with_name(processed_name)

    try:
        src.rename(dst)
        logger.debug("Marked message as read: %s → %s", src.name, processed_name)
    except OSError as exc:
        logger.error("Failed to move %s to %s: %s", src, dst, exc)
