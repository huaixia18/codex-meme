import json
import unittest

from common import RuntimeSandbox, reaction, stop_hook


class StopHookTests(unittest.TestCase):
    @staticmethod
    def create_offer(sandbox, session_id="stop", turn_id="turn"):
        output = sandbox.run_main(
            reaction,
            {"session_id": session_id, "turn_id": turn_id, "prompt": "send me a meme"},
        )
        assert output
        return sandbox.read_state()["sessions"][session_id]["pending_offer"]

    def test_used_current_candidate_opens_followup_chain(self):
        with RuntimeSandbox() as sandbox:
            pending = self.create_offer(sandbox)
            path = pending["candidate_paths"][0]
            output = sandbox.run_main(
                stop_hook,
                {"session_id": "stop", "turn_id": "turn", "last_assistant_message": f"done\n![](<{path}>)"},
            )
            self.assertEqual("{}", output)
            self.assertEqual("USED_TEXT", sandbox.read_log()[-1]["event"])
            slot = sandbox.read_state()["sessions"]["stop"]
            self.assertTrue(slot["play_chain"])
            self.assertIsNone(slot["pending_offer"])

    def test_decline_closes_followup_chain(self):
        with RuntimeSandbox() as sandbox:
            self.create_offer(sandbox)
            sandbox.run_main(
                stop_hook,
                {"session_id": "stop", "turn_id": "turn", "last_assistant_message": "plain answer"},
            )
            self.assertEqual("DECLINED", sandbox.read_log()[-1]["event"])
            self.assertFalse(sandbox.read_state()["sessions"]["stop"]["play_chain"])

    def test_unoffered_asset_and_mixed_use_are_abnormal(self):
        specs = [
            ("01", "one.jpg", "one"),
            ("02", "two.jpg", "two"),
            ("03", "three.jpg", "three"),
            ("04", "four.jpg", "four"),
        ]
        for mixed in (False, True):
            with self.subTest(mixed=mixed), RuntimeSandbox(asset_specs=specs) as sandbox:
                pending = self.create_offer(sandbox)
                manifest = json.loads(sandbox.manifest_path.read_text(encoding="utf-8"))
                unoffered = next(item for item in manifest if item["id"] not in pending["candidate_ids"])
                message = unoffered["path"]
                if mixed:
                    message += " " + pending["candidate_paths"][0]
                sandbox.run_main(
                    stop_hook,
                    {"session_id": "stop", "turn_id": "turn", "last_assistant_message": message},
                )
                event = sandbox.read_log()[-1]
                self.assertEqual("USED_WITHOUT_OFFER", event["event"])
                self.assertIn(unoffered["id"], event["candidate_ids"])
                self.assertFalse(sandbox.read_state()["sessions"]["stop"]["play_chain"])

    def test_asset_without_pending_offer_is_abnormal(self):
        with RuntimeSandbox() as sandbox:
            path = json.loads(sandbox.manifest_path.read_text(encoding="utf-8"))[0]["path"]
            sandbox.run_main(
                stop_hook,
                {"session_id": "none", "turn_id": "turn", "last_assistant_message": path},
            )
            self.assertEqual("USED_WITHOUT_OFFER", sandbox.read_log()[-1]["event"])


if __name__ == "__main__":
    unittest.main()
