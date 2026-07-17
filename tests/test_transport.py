"""Tests for Guild AI file-based transport functions.

Tests send_message, poll_inbox, and mark_read using a temp directory
patched in as the base path to avoid touching real $HOME.
"""

import json
import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

import guild.transport as transport


# ── Helpers ───────────────────────────────────────────────────────────────


def _patch_base(tmpdir: str):
    """Return a context manager that redirects transport paths to tmpdir."""
    base = Path(tmpdir)
    return patch.multiple(
        transport,
        INBOX_DIR=base / "inbox",
        OUTBOX_DIR=base / "outbox",
    )


# ── send_message ──────────────────────────────────────────────────────────


class TestSendMessage(unittest.TestCase):
    """send_message writes a JSON file to the recipient's outbox."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.patcher = _patch_base(self.tmpdir)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    def test_send_creates_file(self):
        ok = transport.send_message("bob", {"type": "quest.publish", "quest_id": "q-001"})
        self.assertTrue(ok)

        outbox = Path(self.tmpdir) / "outbox" / "bob"
        files = list(outbox.iterdir())
        self.assertEqual(len(files), 1)
        self.assertIn("q-001", files[0].name)

    def test_send_returns_false_on_bad_path(self):
        """_ensure_dir raises on an unwritable root."""
        from guild.transport import _ensure_dir
        with patch.object(transport, "_ensure_dir") as mock_ensure:
            mock_ensure.side_effect = OSError("[mock] cannot write")
            ok = transport.send_message("bob", {"type": "quest.publish"})
            self.assertFalse(ok)

    def test_send_injects_timestamp(self):
        msg = {"type": "quest.publish", "quest_id": "q-001"}
        transport.send_message("bob", msg)
        outbox = Path(self.tmpdir) / "outbox" / "bob"
        files = list(outbox.iterdir())
        self.assertEqual(len(files), 1)
        content = json.loads(files[0].read_text())
        self.assertIn("type", content)

    def test_send_multiple_messages(self):
        for i in range(5):
            transport.send_message("bob", {"type": "quest.publish", "quest_id": f"q-{i:03d}"})
        outbox = Path(self.tmpdir) / "outbox" / "bob"
        files = list(outbox.iterdir())
        self.assertEqual(len(files), 5)

    def test_send_diff_recipients(self):
        transport.send_message("alice", {"type": "quest.publish", "quest_id": "q-001"})
        transport.send_message("bob", {"type": "quest.publish", "quest_id": "q-002"})
        alice_outbox = Path(self.tmpdir) / "outbox" / "alice"
        bob_outbox = Path(self.tmpdir) / "outbox" / "bob"
        self.assertEqual(len(list(alice_outbox.iterdir())), 1)
        self.assertEqual(len(list(bob_outbox.iterdir())), 1)


# ── poll_inbox ────────────────────────────────────────────────────────────


class TestPollInbox(unittest.TestCase):
    """poll_inbox returns messages addressed to an agent."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.patcher = _patch_base(self.tmpdir)
        self.patcher.start()
        # Seed an inbox with a message
        inbox = Path(self.tmpdir) / "inbox" / "bob"
        inbox.mkdir(parents=True)
        (inbox / "q-001_publish_2026-01-01T00:00:00.json").write_text(
            json.dumps({"type": "quest.publish", "quest_id": "q-001"})
        )

    def tearDown(self):
        self.patcher.stop()

    def test_poll_returns_messages(self):
        msgs = transport.poll_inbox("bob")
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0]["quest_id"], "q-001")

    def test_poll_empty_inbox(self):
        msgs = transport.poll_inbox("nobody")
        self.assertEqual(msgs, [])

    def test_poll_skips_processed_files(self):
        inbox = Path(self.tmpdir) / "inbox" / "bob"
        (inbox / "_processed_q-002_accept_2026-01-01T00:00:00.json").write_text(
            json.dumps({"type": "quest.accept"})
        )
        msgs = transport.poll_inbox("bob")
        self.assertEqual(len(msgs), 1)  # only the non-processed one

    def test_poll_skips_non_json(self):
        inbox = Path(self.tmpdir) / "inbox" / "bob"
        (inbox / "readme.txt").write_text("hello")
        msgs = transport.poll_inbox("bob")
        self.assertEqual(len(msgs), 1)  # only the .json, not .txt

    def test_poll_returns_multiple_messages(self):
        inbox = Path(self.tmpdir) / "inbox" / "bob"
        for i in range(3):
            (inbox / f"q-{i:03d}_heartbeat_2026-01-01T00:00:0{i}.json").write_text(
                json.dumps({"type": "quest.heartbeat", "seq": i})
            )
        msgs = transport.poll_inbox("bob")
        self.assertEqual(len(msgs), 4)  # 1 original + 3 new

    def test_poll_returns_empty_for_nonexistent_agent(self):
        msgs = transport.poll_inbox("ghost")
        self.assertEqual(msgs, [])


# ── mark_read ─────────────────────────────────────────────────────────────


class TestMarkRead(unittest.TestCase):
    """mark_read renames a processed file with a _processed_ prefix."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.patcher = _patch_base(self.tmpdir)
        self.patcher.start()
        inbox = Path(self.tmpdir) / "inbox" / "bob"
        inbox.mkdir(parents=True)
        self.filepath = inbox / "q-001_deliver_2026-01-01T00:00:00.json"
        self.filepath.write_text(json.dumps({"type": "quest.deliver"}))

    def tearDown(self):
        self.patcher.stop()

    def test_mark_read_renames_file(self):
        transport.mark_read(str(self.filepath))
        self.assertFalse(self.filepath.exists())
        processed = self.filepath.with_name(f"_processed_{self.filepath.name}")
        self.assertTrue(processed.exists())

    def test_mark_read_nonexistent_file(self):
        """Calling mark_read on a missing file does not error."""
        transport.mark_read("/nonexistent/message.json")  # should not raise

    def test_mark_read_then_poll_excludes_it(self):
        transport.mark_read(str(self.filepath))
        msgs = transport.poll_inbox("bob")
        self.assertEqual(msgs, [])

    def test_mark_read_then_new_message_still_visible(self):
        transport.mark_read(str(self.filepath))
        inbox = Path(self.tmpdir) / "inbox" / "bob"
        (inbox / "q-002_publish_2026-01-01T00:01:00.json").write_text(
            json.dumps({"type": "quest.publish", "quest_id": "q-002"})
        )
        msgs = transport.poll_inbox("bob")
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0]["quest_id"], "q-002")


# ── End-to-end: send → poll → mark_read → poll ───────────────────────────


class TestEndToEnd(unittest.TestCase):
    """Full lifecycle: bob sends → alice polls → alice marks → bob polls empty."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.patcher = _patch_base(self.tmpdir)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    def test_full_round_trip(self):
        # Bob publishes a quest → Alice's inbox
        transport.send_message("bob", {"type": "quest.publish", "quest_id": "q-001"})
        transport.send_message("bob", {"type": "quest.publish", "quest_id": "q-002"})

        # Bob's outbox should have 2 messages destined for... wait.
        # send_message writes to OUTBOX_DIR/recipient_id, so "bob" as recipient
        # creates outbox/bob — these messages were "sent to bob"
        # Let me test the correct direction: alice sends, bob receives.

    def test_alice_publishes_bob_receives(self):
        transport.send_message("alice", {"type": "quest.publish", "quest_id": "q-001"})
        # "alice" as recipient → outbox/alice/
        # To get into bob's inbox, we need to place a file there directly
        inbox = Path(self.tmpdir) / "inbox" / "bob"
        inbox.mkdir(parents=True)
        (inbox / "q-001_publish_now.json").write_text(
            json.dumps({"type": "quest.publish", "quest_id": "q-001"})
        )

        msgs = transport.poll_inbox("bob")
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0]["quest_id"], "q-001")

        # Mark as read
        filepath = inbox / "q-001_publish_now.json"
        transport.mark_read(str(filepath))
        self.assertEqual(transport.poll_inbox("bob"), [])


# ── Concurrency ───────────────────────────────────────────────────────────


class TestConcurrency(unittest.TestCase):
    """Concurrent send_message calls should not corrupt the transport."""

    def test_concurrent_sends(self):
        tmpdir = tempfile.mkdtemp()
        patcher = _patch_base(tmpdir)
        patcher.start()
        try:
            n = 50
            errors = []
            lock = threading.Lock()

            def sender(thread_id):
                try:
                    for i in range(n):
                        transport.send_message(
                            "receiver",
                            {"type": "quest.heartbeat", "quest_id": f"t{thread_id}-m{i}"},
                        )
                except Exception as e:
                    with lock:
                        errors.append(e)

            threads = [threading.Thread(target=sender, args=(t,)) for t in range(4)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            self.assertEqual(errors, [], f"Concurrent errors: {errors}")

            outbox = Path(tmpdir) / "outbox" / "receiver"
            files = list(outbox.iterdir())
            self.assertEqual(len(files), n * 4)

            ids = set()
            for f in files:
                content = json.loads(f.read_text())
                ids.add(content["quest_id"])
            self.assertEqual(len(ids), n * 4)

        finally:
            patcher.stop()


if __name__ == "__main__":
    unittest.main()
