"""Agent-side quest handler for Guild AI.

A :class:`GuildAgent` advertises its capabilities, listens for quest
invitations, accepts or declines them, and executes accepted quests
while streaming progress heartbeats.
"""

from __future__ import annotations

import hashlib
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Generator

from guild.schema import (
    QuestAccept,
    QuestDeliver,
    QuestError,
    QuestHeartbeat,
    QuestPublish,
    HeartbeatStatus,
    validate_message,
)
from guild.transport import Transport


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


@dataclass
class GuildAgent:
    """Participates in Guild AI quests on behalf of a capability-bearing agent.

    Parameters
    ----------
    agent_id:
        Unique identifier for this agent instance.
    capabilities:
        List of capability strings this agent provides.
    transport:
        The messaging transport used to communicate with the guild.
    """

    agent_id: str
    capabilities: list[str]
    transport: Transport
    active_quests: dict[str, dict] = field(default_factory=dict)
    _max_concurrent: int = 3

    # ------------------------------------------------------------------
    # Capability manifest
    # ------------------------------------------------------------------

    def get_manifest(self) -> dict:
        """Return the capability manifest used for discovery by the guild.

        Returns
        -------
        dict
            Contains *agent_id*, *capabilities*, and a *max_concurrent* slot count.
        """
        return {
            "agent_id": self.agent_id,
            "capabilities": self.capabilities,
            "max_concurrent": self._max_concurrent,
        }

    # ------------------------------------------------------------------
    # Inbox polling
    # ------------------------------------------------------------------

    def listen(self, timeout: int = 30) -> list[dict]:
        """Poll the inbox for new quest messages (raw dicts).

        Use :func:`guild.schema.validate_message` to convert raw dicts
        into typed dataclass instances.

        Parameters
        ----------
        timeout:
            Maximum seconds to wait for messages.

        Returns
        -------
        list[dict]
            Raw message dicts from the inbox.
        """
        return self.transport.receive(timeout=timeout)

    # ------------------------------------------------------------------
    # Accept / decline logic
    # ------------------------------------------------------------------

    def handle_quest(self, msg: QuestPublish) -> QuestAccept | QuestError:
        """Decide whether to accept or decline a published quest.

        Returns :class:`QuestAccept` if this agent has all required
        capabilities and is not at capacity.  Otherwise returns
        :class:`QuestError` with a descriptive code and message.

        Parameters
        ----------
        msg:
            The incoming quest publish message.

        Returns
        -------
        QuestAccept or QuestError
        """
        # --- capacity check -------------------------------------------------
        if len(self.active_quests) >= self._max_concurrent:
            return QuestError(
                quest_id=msg.quest_id,
                code="CAPACITY_EXCEEDED",
                message=f"At capacity ({len(self.active_quests)}/{self._max_concurrent})",
            )

        # --- capability check ------------------------------------------------
        declared = set(self.capabilities)
        missing = [c for c in msg.required_capabilities if c not in declared]
        if missing:
            return QuestError(
                quest_id=msg.quest_id,
                code="MISSING_CAPABILITIES",
                message=f"Missing capabilities: {', '.join(missing)}",
            )

        # --- accept ---------------------------------------------------------
        bond_tx = _simulate_bond_tx(msg.quest_id, msg.bond)
        self.active_quests[msg.quest_id] = {
            "quest": msg,
            "state": "accepted",
            "started_at": time.time(),
            "progress_pct": 0,
        }
        return QuestAccept(
            quest_id=msg.quest_id,
            agent=self.agent_id,
            estimated_delivery=msg.max_duration,
            bond_tx=bond_tx,
        )

    # ------------------------------------------------------------------
    # Quest execution (generator)
    # ------------------------------------------------------------------

    def execute(
        self,
        quest: QuestPublish,
    ) -> Generator[QuestHeartbeat, None, QuestDeliver]:
        """Execute a quest, yielding heartbeats as work progresses.

        This is a **generator** — the caller drives it by iterating.
        Each intermediate ``yield`` sends a :class:`QuestHeartbeat`.
        The final value (``.return()``) is the :class:`QuestDeliver`.

        Parameters
        ----------
        quest:
            The quest to execute.

        Yields
        ------
        QuestHeartbeat
            During execution.

        Returns
        -------
        QuestDeliver
            The final delivery.
        """
        quest_id = quest.quest_id

        # Mark as executing
        if quest_id in self.active_quests:
            self.active_quests[quest_id]["state"] = "executing"

        # Stub execution loop — real agents override or wrap this method.
        for pct in range(0, 101, 25):
            time.sleep(0.05)
            yield QuestHeartbeat(
                quest_id=quest_id,
                status=HeartbeatStatus.IN_PROGRESS.value,
                progress_pct=pct,
                message=f"Processing... {pct}%",
            )

        result: dict[str, Any] = {"status": "completed"}
        summary = f"Quest '{quest.title}' completed by {self.agent_id}"

        self.active_quests.pop(quest_id, None)
        delivery = QuestDeliver(
            quest_id=quest_id,
            result=result,
            summary=summary,
            proof_hash=_compute_proof_hash(result),
        )
        return delivery  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Direct helpers
    # ------------------------------------------------------------------

    def send_heartbeat(self, quest_id: str, progress_pct: int, msg: str) -> None:
        """Send a one-off heartbeat for an active quest.

        Parameters
        ----------
        quest_id:
            The active quest identifier.
        progress_pct:
            Progress percentage (0–100).
        msg:
            Human-readable status message.
        """
        hb = QuestHeartbeat(
            quest_id=quest_id,
            status=HeartbeatStatus.IN_PROGRESS.value,
            progress_pct=progress_pct,
            message=msg,
        )
        self.transport.send(hb, recipient=self.agent_id)

    def deliver_result(
        self, quest_id: str, result: dict[str, Any], summary: str
    ) -> None:
        """Deliver a completed quest result.

        Parameters
        ----------
        quest_id:
            The completed quest identifier.
        result:
            Structured result payload.
        summary:
            One-line human summary of the outcome.
        """
        delivery = QuestDeliver(
            quest_id=quest_id,
            result=result,
            summary=summary,
            proof_hash=_compute_proof_hash(result),
        )
        self.transport.send(delivery, recipient=self.agent_id)
        self.active_quests.pop(quest_id, None)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _simulate_bond_tx(quest_id: str, bond_amount: str) -> str:
    """Deterministic mock transaction hash for the bond."""
    raw = f"{quest_id}:{bond_amount}:{uuid.uuid4().hex[:8]}"
    return f"0x{hashlib.sha256(raw.encode()).hexdigest()[:64]}"


def _compute_proof_hash(data: dict[str, Any]) -> str:
    """SHA-256 of the canonical JSON of *data*."""
    import json

    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()
