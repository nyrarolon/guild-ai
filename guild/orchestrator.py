"""Quest orchestrator for Guild AI — the publisher / guild side.

A :class:`GuildOrchestrator` creates quests, waits for agent
acceptance, monitors delivery, and triggers settlement.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from guild.schema import (
    QuestAccept,
    QuestDeliver,
    QuestError,
    QuestHeartbeat,
    QuestPublish,
    QuestSettle,
    QuestVerify,
    VerifyStatus,
    validate_message,
)
from guild.transport import Transport
from guild.verify import verify_schema


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


@dataclass
class GuildOrchestrator:
    """Publishes quests and manages their lifecycle on the guild side.

    Parameters
    ----------
    agent_id:
        The orchestrator's own identifier (the quest publisher).
    transport:
        Messaging transport for sending / receiving quest messages.
    """

    agent_id: str
    transport: Transport
    _pending_quests: dict[str, QuestPublish] = field(default_factory=dict)
    _acceptances: dict[str, QuestAccept] = field(default_factory=dict)
    _deliveries: dict[str, QuestDeliver] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Publish
    # ------------------------------------------------------------------

    def publish_quest(
        self,
        title: str,
        description: str,
        reward: str = "",
        bond: str = "",
        max_duration: int = 3600,
        required_capabilities: list[str] | None = None,
        output_schema: dict | None = None,
    ) -> str:
        """Create and publish a new quest to the guild.

        Parameters
        ----------
        title:
            Short human-readable title.
        description:
            Full quest description.
        reward:
            Reward offered (e.g. ``"0.0005_ETH"``).
        bond:
            Bond required from the accepting agent (e.g. ``"0.0001_ETH"``).
        max_duration:
            Maximum allowed execution time in seconds (default 1 hour).
        required_capabilities:
            Capabilities the agent must possess.
        output_schema:
            Optional schema dict for result verification.

        Returns
        -------
        str
            The generated ``quest_id``.
        """
        quest_id = _generate_quest_id(title)

        quest = QuestPublish(
            quest_id=quest_id,
            title=title.strip(),
            description=description.strip(),
            reward=reward,
            bond=bond,
            max_duration=max_duration,
            required_capabilities=required_capabilities or [],
            output_schema=output_schema or {},
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        self.transport.send(quest, recipient=self.agent_id)
        self._pending_quests[quest_id] = quest
        return quest_id

    # ------------------------------------------------------------------
    # Await acceptance
    # ------------------------------------------------------------------

    def await_acceptance(self, quest_id: str, timeout: int = 300) -> QuestAccept | None:
        """Block until an agent accepts the quest or *timeout* expires.

        Parameters
        ----------
        quest_id:
            The published quest identifier.
        timeout:
            Max seconds to wait.

        Returns
        -------
        QuestAccept or None
        """
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            raw = self.transport.receive(timeout=5)
            for d in raw:
                msg = validate_message(d)
                if isinstance(msg, QuestAccept) and msg.quest_id == quest_id:
                    self._acceptances[quest_id] = msg
                    return msg
        return None

    # ------------------------------------------------------------------
    # Await delivery
    # ------------------------------------------------------------------

    def await_delivery(self, quest_id: str, timeout: int = 7200) -> QuestDeliver | None:
        """Block until the agent delivers results or *timeout* expires.

        Parameters
        ----------
        quest_id:
            The quest identifier.
        timeout:
            Max seconds to wait.  Default 2 hours.

        Returns
        -------
        QuestDeliver or None
        """
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            raw = self.transport.receive(timeout=10)
            for d in raw:
                msg = validate_message(d)
                if isinstance(msg, QuestDeliver) and msg.quest_id == quest_id:
                    self._deliveries[quest_id] = msg
                    return msg
                # Heartbeats keep the line alive — ignore them here
        return None

    # ------------------------------------------------------------------
    # Verify result
    # ------------------------------------------------------------------

    def verify_result(self, quest: QuestPublish, delivery: QuestDeliver) -> QuestVerify:
        """Validate the delivered result against the quest's output schema.

        If the quest has no ``output_schema`` the result is always
        accepted.

        Parameters
        ----------
        quest:
            The originally published quest (carries the schema).
        delivery:
            The agent's delivery with the result payload.

        Returns
        -------
        QuestVerify
        """
        if not quest.output_schema:
            return QuestVerify(
                quest_id=quest.quest_id,
                status=VerifyStatus.ACCEPTED.value,
                reason="No output schema — accepted by default.",
            )

        valid = verify_schema(delivery.result, quest.output_schema)
        if valid:
            return QuestVerify(
                quest_id=quest.quest_id,
                status=VerifyStatus.ACCEPTED.value,
                reason="Result conforms to output schema.",
            )
        return QuestVerify(
            quest_id=quest.quest_id,
            status=VerifyStatus.REJECTED.value,
            reason="Result failed schema validation.",
        )

    # ------------------------------------------------------------------
    # Settlement
    # ------------------------------------------------------------------

    def settle(self, quest_id: str, accepted: bool) -> None:
        """Finalise a quest — send a :class:`QuestSettle` message.

        Parameters
        ----------
        quest_id:
            The quest to settle.
        accepted:
            ``True`` to release the reward, ``False`` to forfeit the bond.
        """
        accept = self._acceptances.get(quest_id)
        settle = QuestSettle(
            quest_id=quest_id,
            reward_released=accepted,
            bond_returned=accepted,
            tx_id=f"0x{uuid.uuid4().hex[:64]}" if accepted else None,
        )
        self.transport.send(settle, recipient=accept.agent if accept else None)

        # Cleanup
        self._pending_quests.pop(quest_id, None)
        self._acceptances.pop(quest_id, None)
        self._deliveries.pop(quest_id, None)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _generate_quest_id(title: str) -> str:
    """Create a short, unique human-readable quest identifier."""
    slug = "".join(c for c in title.lower() if c.isalnum() or c in "-_").strip("-")
    tag = uuid.uuid4().hex[:6]
    return f"{slug}-{tag}" if slug else f"quest-{tag}"
