"""Tests for Guild AI schema — validate_message and dataclass behavior.

Tests cover the validate_message() function (returns Optional[QuestMessage])
and correct creation/serialization of all message dataclass types.
"""

import json
import unittest

from guild.schema import (
    QuestMessageType,
    QuestPublish,
    QuestAccept,
    QuestHeartbeat,
    QuestDeliver,
    QuestVerify,
    QuestSettle,
    QuestError,
    HeartbeatStatus,
    VerifyStatus,
    validate_message,
    TYPE_REGISTRY,
    REQUIRED_FIELDS,
)


# ── validate_message: valid inputs ────────────────────────────────────────


class TestValidateMessageValid(unittest.TestCase):
    """validate_message returns a typed instance for well-formed dicts."""

    def test_valid_publish(self):
        msg = {
            "type": QuestMessageType.PUBLISH.value,
            "quest_id": "q-001",
            "title": "Research SOL volatility",
            "description": "Analyze weekend gaps",
            "reward": "0.0005_ETH",
            "bond": "0.0001_ETH",
            "max_duration": 3600,
            "required_capabilities": ["research"],
            "output_schema": {},
            "created_at": "2026-07-17T12:00:00",
        }
        result = validate_message(msg)
        self.assertIsNotNone(result)
        if result is not None:
            self.assertIsInstance(result, QuestPublish)
            self.assertEqual(result.quest_id, "q-001")
            self.assertEqual(result.reward, "0.0005_ETH")

    def test_valid_accept(self):
        msg = {
            "type": QuestMessageType.ACCEPT.value,
            "quest_id": "q-001",
            "agent": "alice",
            "estimated_delivery": 1800,
            "accepted_at": "2026-07-17T12:01:00",
        }
        result = validate_message(msg)
        self.assertIsNotNone(result)
        if result is not None:
            self.assertIsInstance(result, QuestAccept)
            self.assertEqual(result.agent, "alice")

    def test_valid_heartbeat(self):
        msg = {
            "type": QuestMessageType.HEARTBEAT.value,
            "quest_id": "q-001",
            "status": HeartbeatStatus.IN_PROGRESS.value,
            "progress_pct": 50,
            "message": "Collecting data",
        }
        result = validate_message(msg)
        self.assertIsNotNone(result)
        if result is not None:
            self.assertIsInstance(result, QuestHeartbeat)
            self.assertEqual(result.progress_pct, 50)

    def test_valid_deliver(self):
        msg = {
            "type": QuestMessageType.DELIVER.value,
            "quest_id": "q-001",
            "result": {"findings": ["gap up"]},
            "summary": "Analysis complete",
            "proof_hash": "abc123",
        }
        result = validate_message(msg)
        self.assertIsNotNone(result)
        if result is not None:
            self.assertIsInstance(result, QuestDeliver)
            self.assertIn("findings", result.result)

    def test_valid_verify_accepted(self):
        msg = {
            "type": QuestMessageType.VERIFY.value,
            "quest_id": "q-001",
            "status": VerifyStatus.ACCEPTED.value,
            "reason": None,
        }
        result = validate_message(msg)
        self.assertIsNotNone(result)
        if result is not None:
            self.assertIsInstance(result, QuestVerify)

    def test_valid_verify_rejected(self):
        msg = {
            "type": QuestMessageType.VERIFY.value,
            "quest_id": "q-001",
            "status": VerifyStatus.REJECTED.value,
            "reason": "Insufficient evidence",
        }
        result = validate_message(msg)
        self.assertIsNotNone(result)
        if result is not None:
            self.assertEqual(result.status, VerifyStatus.REJECTED.value)

    def test_valid_settle(self):
        msg = {
            "type": QuestMessageType.SETTLE.value,
            "quest_id": "q-001",
            "reward_released": True,
            "bond_returned": True,
        }
        result = validate_message(msg)
        self.assertIsNotNone(result)
        if result is not None:
            self.assertIsInstance(result, QuestSettle)
            self.assertTrue(result.reward_released)

    def test_valid_error(self):
        msg = {
            "type": QuestMessageType.ERROR.value,
            "quest_id": "q-001",
            "code": "CAPABILITY_MISMATCH",
            "message": "No agent has the required capabilities",
        }
        result = validate_message(msg)
        self.assertIsNotNone(result)
        if result is not None:
            self.assertIsInstance(result, QuestError)
            self.assertEqual(result.code, "CAPABILITY_MISMATCH")


# ── validate_message: invalid inputs → returns None ──────────────────────


class TestValidateMessageInvalid(unittest.TestCase):
    """validate_message returns None for malformed or incomplete dicts."""

    def test_missing_type(self):
        self.assertIsNone(validate_message({"quest_id": "q-001"}))

    def test_unknown_type(self):
        self.assertIsNone(validate_message({"type": "quest.unknown", "quest_id": "q-001"}))

    def test_missing_required_field(self):
        msg = {
            "type": QuestMessageType.PUBLISH.value,
            "quest_id": "q-001",
            # missing "title", "description", "reward", etc.
        }
        self.assertIsNone(validate_message(msg))

    def test_empty_required_field(self):
        msg = {
            "type": QuestMessageType.PUBLISH.value,
            "quest_id": "q-001",
            "title": "",
            "description": "desc",
            "reward": "0.001_ETH",
            "bond": "0.0001_ETH",
            "max_duration": 300,
            "created_at": "now",
        }
        self.assertIsNone(validate_message(msg))

    def test_heartbeat_invalid_status(self):
        msg = {
            "type": QuestMessageType.HEARTBEAT.value,
            "quest_id": "q-001",
            "status": "bogus",
            "progress_pct": 50,
        }
        self.assertIsNone(validate_message(msg))

    def test_heartbeat_invalid_progress(self):
        msg = {
            "type": QuestMessageType.HEARTBEAT.value,
            "quest_id": "q-001",
            "status": HeartbeatStatus.IN_PROGRESS.value,
            "progress_pct": 150,  # > 100
        }
        self.assertIsNone(validate_message(msg))

    def test_verify_invalid_status(self):
        msg = {
            "type": QuestMessageType.VERIFY.value,
            "quest_id": "q-001",
            "status": "maybe",
        }
        self.assertIsNone(validate_message(msg))

    def test_empty_dict(self):
        self.assertIsNone(validate_message({}))

    def test_non_dict_input(self):
        self.assertIsNone(validate_message("not a dict"))


# ── Dataclass creation (direct, not via validate) ────────────────────────


class TestDataclassCreation(unittest.TestCase):
    """Each dataclass can be created directly with correct field types."""

    def test_publish_defaults(self):
        q = QuestPublish()
        self.assertEqual(q.type, QuestMessageType.PUBLISH.value)
        self.assertEqual(q.required_capabilities, [])

    def test_accept_defaults(self):
        a = QuestAccept()
        self.assertEqual(a.type, QuestMessageType.ACCEPT.value)
        self.assertIsNone(a.bond_tx)

    def test_heartbeat_defaults(self):
        h = QuestHeartbeat()
        self.assertEqual(h.status, HeartbeatStatus.IN_PROGRESS.value)
        self.assertEqual(h.progress_pct, 0)

    def test_deliver_defaults(self):
        d = QuestDeliver()
        self.assertEqual(d.result, {})
        self.assertEqual(d.proof_hash, "")

    def test_verify_defaults(self):
        v = QuestVerify()
        self.assertEqual(v.status, VerifyStatus.ACCEPTED.value)

    def test_settle_defaults(self):
        s = QuestSettle()
        self.assertFalse(s.reward_released)

    def test_error_defaults(self):
        e = QuestError()
        self.assertEqual(e.code, "")

    def test_publish_fields(self):
        q = QuestPublish(
            quest_id="q-002",
            title="Code Review",
            description="Review PR",
            reward="0.001_ETH",
            bond="0.0002_ETH",
            max_duration=7200,
            required_capabilities=["code_review", "python"],
        )
        self.assertIn("python", q.required_capabilities)

    def test_accept_optional_bond_tx(self):
        a = QuestAccept(quest_id="q-001", agent="bob", bond_tx="0xdeadbeef")
        self.assertEqual(a.bond_tx, "0xdeadbeef")

    def test_deliver_with_result(self):
        d = QuestDeliver(
            quest_id="q-001",
            result={"answer": 42},
            summary="Done",
        )
        self.assertEqual(d.result["answer"], 42)


# ── Serialization / deserialization ──────────────────────────────────────


class TestSerialization(unittest.TestCase):
    """All dataclass instances survive a json round-trip."""

    def _roundtrip(self, instance):
        d = {k: v for k, v in instance.__dict__.items() if not k.startswith("_")}
        raw = json.dumps(d, default=str, sort_keys=True)
        loaded = json.loads(raw)
        for k, v in d.items():
            self.assertIn(k, loaded)
            self.assertEqual(loaded[k], v, f"Mismatch for field '{k}'")

    def test_publish(self):
        q = QuestPublish(
            quest_id="q-001",
            title="T",
            description="D",
            reward="0.001_ETH",
            bond="0.0001_ETH",
            max_duration=3600,
            created_at="now",
        )
        self._roundtrip(q)

    def test_accept(self):
        self._roundtrip(QuestAccept(quest_id="q-001", agent="alice", estimated_delivery=300))

    def test_heartbeat(self):
        self._roundtrip(QuestHeartbeat(quest_id="q-001", progress_pct=75))

    def test_deliver(self):
        self._roundtrip(QuestDeliver(quest_id="q-001", summary="Done"))

    def test_verify(self):
        self._roundtrip(QuestVerify(quest_id="q-001"))

    def test_settle(self):
        self._roundtrip(QuestSettle(quest_id="q-001", reward_released=True))

    def test_error(self):
        self._roundtrip(QuestError(quest_id="q-001", code="ERR", message="fail"))


# ── TYPE_REGISTRY / REQUIRED_FIELDS integrity ─────────────────────────────


class TestRegistry(unittest.TestCase):
    """Module-level registries match the actual dataclasses."""

    def test_all_types_have_required_fields(self):
        for msg_type in QuestMessageType:
            self.assertIn(
                msg_type.value,
                TYPE_REGISTRY,
                f"Missing TYPE_REGISTRY entry for {msg_type.value}",
            )
            self.assertIn(
                msg_type.value,
                REQUIRED_FIELDS,
                f"Missing REQUIRED_FIELDS entry for {msg_type.value}",
            )

    def test_registry_has_correct_types(self):
        self.assertEqual(TYPE_REGISTRY[QuestMessageType.PUBLISH.value], QuestPublish)
        self.assertEqual(TYPE_REGISTRY[QuestMessageType.ACCEPT.value], QuestAccept)
        self.assertEqual(TYPE_REGISTRY[QuestMessageType.DELIVER.value], QuestDeliver)
        self.assertEqual(TYPE_REGISTRY[QuestMessageType.HEARTBEAT.value], QuestHeartbeat)
        self.assertEqual(TYPE_REGISTRY[QuestMessageType.VERIFY.value], QuestVerify)
        self.assertEqual(TYPE_REGISTRY[QuestMessageType.SETTLE.value], QuestSettle)
        self.assertEqual(TYPE_REGISTRY[QuestMessageType.ERROR.value], QuestError)

    def test_required_fields_non_empty(self):
        for msg_type_str, fields in REQUIRED_FIELDS.items():
            self.assertTrue(
                len(fields) > 0,
                f"Empty REQUIRED_FIELDS for {msg_type_str}",
            )

    def test_publish_has_all_core_fields(self):
        required = REQUIRED_FIELDS[QuestMessageType.PUBLISH.value]
        for f in ("quest_id", "title", "description", "reward", "bond", "max_duration", "created_at"):
            self.assertIn(f, required)


if __name__ == "__main__":
    unittest.main()
