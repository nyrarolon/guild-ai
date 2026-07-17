"""
Guild AI — Quest Message Schema & Validation.

Defines all message types for the Guild AI quest protocol as pure dataclasses,
plus a validation function that parses raw dicts into typed message objects.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field, fields as dataclass_fields
from enum import Enum
from typing import Any, Optional, Union

logger = logging.getLogger("guild.schema")


# ── Message Type Enum ──────────────────────────────────────────────────────────


class QuestMessageType(str, Enum):
    """All quest message types in the protocol."""

    PUBLISH = "quest.publish"
    ACCEPT = "quest.accept"
    HEARTBEAT = "quest.heartbeat"
    DELIVER = "quest.deliver"
    VERIFY = "quest.verify"
    SETTLE = "quest.settle"
    ERROR = "quest.error"


# ── Heartbeat Status Enum ──────────────────────────────────────────────────────


class HeartbeatStatus(str, Enum):
    """Valid statuses for a quest heartbeat."""

    IN_PROGRESS = "in_progress"
    FAILED = "failed"
    COMPLETED = "completed"


# ── Verification Status Enum ───────────────────────────────────────────────────


class VerifyStatus(str, Enum):
    """Valid statuses for a quest verification."""

    ACCEPTED = "accepted"
    REJECTED = "rejected"


# ── Message Dataclasses ────────────────────────────────────────────────────────


@dataclass
class QuestPublish:
    """
    An orchestrator publishes a quest to the guild.

    Fields:
        type: Always "quest.publish".
        quest_id: Unique identifier for this quest (uuid4 string).
        title: Short human-readable title.
        description: Detailed description of the work.
        reward: Reward offered (e.g. "0.0005_ETH").
        bond: Bond staked by the publisher (e.g. "0.0001_ETH").
        max_duration: Maximum allowed execution time in seconds.
        required_capabilities: List of capabilities the executor must have.
        output_schema: JSON schema describing the expected result shape.
        created_at: ISO-8601 timestamp of when the quest was published.
    """

    type: str = QuestMessageType.PUBLISH.value
    quest_id: str = ""
    title: str = ""
    description: str = ""
    reward: str = ""
    bond: str = ""
    max_duration: int = 0
    required_capabilities: list[str] = field(default_factory=list)
    output_schema: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""


@dataclass
class QuestAccept:
    """
    An executor accepts a quest.

    Fields:
        type: Always "quest.accept".
        quest_id: The quest being accepted.
        agent: Name/identifier of the accepting agent.
        estimated_delivery: Estimated time to completion in seconds.
        bond_tx: Optional transaction hash for the counterparty bond.
        accepted_at: ISO-8601 timestamp of acceptance.
    """

    type: str = QuestMessageType.ACCEPT.value
    quest_id: str = ""
    agent: str = ""
    estimated_delivery: int = 0
    bond_tx: Optional[str] = None
    accepted_at: str = ""


@dataclass
class QuestHeartbeat:
    """
    Periodic progress update from the executor.

    Fields:
        type: Always "quest.heartbeat".
        quest_id: The quest this heartbeat belongs to.
        status: Current execution status ("in_progress", "failed", "completed").
        progress_pct: Percentage of work completed (0–100).
        message: Free-form status message.
    """

    type: str = QuestMessageType.HEARTBEAT.value
    quest_id: str = ""
    status: str = HeartbeatStatus.IN_PROGRESS.value
    progress_pct: int = 0
    message: str = ""


@dataclass
class QuestDeliver:
    """
    Final delivery of quest results from the executor.

    Fields:
        type: Always "quest.deliver".
        quest_id: The completed quest.
        result: The actual result data (dict).
        summary: Human-readable summary of the result.
        proof_hash: SHA-256 hash of the raw result data for verification.
    """

    type: str = QuestMessageType.DELIVER.value
    quest_id: str = ""
    result: dict[str, Any] = field(default_factory=dict)
    summary: str = ""
    proof_hash: str = ""


@dataclass
class QuestVerify:
    """
    Verification result from the orchestrator.

    Fields:
        type: Always "quest.verify".
        quest_id: The quest being verified.
        status: "accepted" or "rejected".
        reason: Optional explanation for rejection.
    """

    type: str = QuestMessageType.VERIFY.value
    quest_id: str = ""
    status: str = VerifyStatus.ACCEPTED.value
    reason: Optional[str] = None


@dataclass
class QuestSettle:
    """
    Final settlement — reward/bond release.

    Fields:
        type: Always "quest.settle".
        quest_id: The settled quest.
        reward_released: Whether the reward was released to the executor.
        bond_returned: Whether the bond was returned to the issuer.
        tx_id: Optional transaction hash for on-chain settlement.
    """

    type: str = QuestMessageType.SETTLE.value
    quest_id: str = ""
    reward_released: bool = False
    bond_returned: bool = False
    tx_id: Optional[str] = None


@dataclass
class QuestError:
    """
    Error message for any failure in the protocol.

    Fields:
        type: Always "quest.error".
        quest_id: The quest this error relates to (may be empty for protocol errors).
        code: Machine-readable error code.
        message: Human-readable error description.
    """

    type: str = QuestMessageType.ERROR.value
    quest_id: str = ""
    code: str = ""
    message: str = ""


# ── Union type for any quest message ───────────────────────────────────────────

QuestMessage = Union[
    QuestPublish,
    QuestAccept,
    QuestHeartbeat,
    QuestDeliver,
    QuestVerify,
    QuestSettle,
    QuestError,
]

# ── Type registry: maps message type strings to dataclass types ────────────────

TYPE_REGISTRY: dict[str, type] = {
    QuestMessageType.PUBLISH.value: QuestPublish,
    QuestMessageType.ACCEPT.value: QuestAccept,
    QuestMessageType.HEARTBEAT.value: QuestHeartbeat,
    QuestMessageType.DELIVER.value: QuestDeliver,
    QuestMessageType.VERIFY.value: QuestVerify,
    QuestMessageType.SETTLE.value: QuestSettle,
    QuestMessageType.ERROR.value: QuestError,
}

# ── Required fields per message type ───────────────────────────────────────────

REQUIRED_FIELDS: dict[str, list[str]] = {
    QuestMessageType.PUBLISH.value: [
        "quest_id",
        "title",
        "description",
        "reward",
        "bond",
        "max_duration",
        "created_at",
    ],
    QuestMessageType.ACCEPT.value: [
        "quest_id",
        "agent",
        "estimated_delivery",
        "accepted_at",
    ],
    QuestMessageType.HEARTBEAT.value: [
        "quest_id",
        "status",
        "progress_pct",
    ],
    QuestMessageType.DELIVER.value: [
        "quest_id",
        "summary",
        "proof_hash",
    ],
    QuestMessageType.VERIFY.value: [
        "quest_id",
        "status",
    ],
    QuestMessageType.SETTLE.value: [
        "quest_id",
    ],
    QuestMessageType.ERROR.value: [
        "quest_id",
        "code",
        "message",
    ],
}


# ── Validation ─────────────────────────────────────────────────────────────────


def _is_empty(value: Any) -> bool:
    """Check if a value is effectively empty (None, empty string, empty list, etc.)."""
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    if isinstance(value, (list, dict)) and len(value) == 0:
        return True
    if isinstance(value, (int, float)) and value == 0:
        return True
    return False


def validate_message(msg: Any) -> Optional[QuestMessage]:
    """
    Validate a raw dict and return the typed dataclass, or None on failure.

    Checks:
      1. The "type" field is a known quest message type.
      2. All required fields for that type are present and non-empty.
      3. Enum fields contain valid values.

    Invalid messages are logged at warning level and return None.

    Args:
        msg: Raw dictionary representing a quest message.

    Returns:
        A QuestMessage dataclass instance, or None if validation fails.
    """
    if not isinstance(msg, dict):
        logger.warning("Invalid message: expected dict, got %s", type(msg).__name__)
        return None

    msg_type_str = msg.get("type", "")
    if not isinstance(msg_type_str, str):
        logger.warning("Invalid message: 'type' field missing or not a string")
        return None

    msg_cls = TYPE_REGISTRY.get(msg_type_str)
    if msg_cls is None:
        logger.warning("Unknown message type: %s", msg_type_str)
        return None

    # Validate required fields are present and non-empty
    required = REQUIRED_FIELDS.get(msg_type_str, [])
    for field_name in required:
        if field_name not in msg:
            logger.warning(
                "Missing required field '%s' for message type '%s'",
                field_name,
                msg_type_str,
            )
            return None
        if _is_empty(msg.get(field_name)):
            logger.warning(
                "Empty required field '%s' for message type '%s'",
                field_name,
                msg_type_str,
            )
            return None

    # Enum-specific validation
    if msg_type_str == QuestMessageType.HEARTBEAT.value:
        status = msg.get("status", "")
        try:
            HeartbeatStatus(status)
        except ValueError:
            logger.warning(
                "Invalid heartbeat status '%s'. Must be one of: %s",
                status,
                [s.value for s in HeartbeatStatus],
            )
            return None
        progress = msg.get("progress_pct", -1)
        if not isinstance(progress, int) or progress < 0 or progress > 100:
            logger.warning(
                "Heartbeat progress_pct must be an int between 0 and 100, got: %s",
                progress,
            )
            return None

    if msg_type_str == QuestMessageType.VERIFY.value:
        status = msg.get("status", "")
        try:
            VerifyStatus(status)
        except ValueError:
            logger.warning(
                "Invalid verify status '%s'. Must be one of: %s",
                status,
                [s.value for s in VerifyStatus],
            )
            return None

    # Build the dataclass from the dict, ignoring extra keys
    cls_fields = {f.name for f in dataclass_fields(msg_cls)}
    filtered_kwargs = {k: v for k, v in msg.items() if k in cls_fields}

    try:
        instance = msg_cls(**filtered_kwargs)
    except (TypeError, ValueError) as exc:
        logger.warning("Failed to construct %s: %s", msg_cls.__name__, exc)
        return None

    return instance  # type: ignore[return-value]
