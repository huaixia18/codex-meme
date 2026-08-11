import json
import unittest

from common import RuntimeSandbox, reaction, session_start


class SessionStartTests(unittest.TestCase):
    def test_startup_once_compact_reinjects_and_clear_resets(self):
        with RuntimeSandbox() as sandbox:
            startup = sandbox.run_main(
                session_start,
                {"source": "startup", "session_id": "session"},
            )
            resume = sandbox.run_main(
                session_start,
                {"source": "resume", "session_id": "session"},
            )
            compact = sandbox.run_main(
                session_start,
                {"source": "compact", "session_id": "session"},
            )
            state = sandbox.read_state()
            slot = state["sessions"]["session"]
            slot.update({"turn": 9, "last_hit": 7, "pending_offer": {"x": 1}, "play_chain": True})
            sandbox.write_state(state)
            clear = sandbox.run_main(
                session_start,
                {"source": "clear", "session_id": "session"},
            )

            self.assertEqual("SessionStart", json.loads(startup)["hookSpecificOutput"]["hookEventName"])
            self.assertEqual("", resume)
            self.assertEqual("SessionStart", json.loads(compact)["hookSpecificOutput"]["hookEventName"])
            self.assertEqual("SessionStart", json.loads(clear)["hookSpecificOutput"]["hookEventName"])
            reset = sandbox.read_state()["sessions"]["session"]
            self.assertEqual(0, reset["turn"])
            self.assertEqual(reaction.NO_HIT, reset["last_hit"])
            self.assertIsNone(reset["pending_offer"])
            self.assertFalse(reset["play_chain"])

    def test_protocol_is_compact_and_contains_core_guards(self):
        self.assertLessEqual(len(session_start.PROTOCOL), 600)
        for phrase in [
            "latest user message",
            "at most one",
            "exact current candidate",
            "without a current signal",
            "summaries/compaction",
        ]:
            self.assertIn(phrase, session_start.PROTOCOL)


if __name__ == "__main__":
    unittest.main()
