import json
import unittest
from unittest import mock

from common import RuntimeSandbox, reaction


class PromptClassificationTests(unittest.TestCase):
    def test_chinese_direct_requests(self):
        positives = [
            "来张表情包",
            "不来个表情包吗？",
            "要不你整个梗图吧",
            "给我一个表情包",
        ]
        negatives = [
            "不来个表情包",
            "不要发表情包",
            "表情包是什么",
            "我们讨论一下梗图",
        ]
        for prompt in positives:
            self.assertTrue(reaction.is_forced_request(prompt), prompt)
        for prompt in negatives:
            self.assertFalse(reaction.is_forced_request(prompt), prompt)

    def test_english_direct_requests(self):
        positives = [
            "send me a meme",
            "Could you show me one reaction image, please?",
            "How about a meme?",
            "Why not drop me a meme?",
            "Meme please",
        ]
        negatives = [
            "what is a meme",
            "meme",
            "do not send a meme",
            "we should discuss meme culture",
        ]
        for prompt in positives:
            self.assertTrue(reaction.is_forced_request(prompt), prompt)
        for prompt in negatives:
            self.assertFalse(reaction.is_forced_request(prompt), prompt)

    def test_followup_requests(self):
        positives = ["有别的吗？", "下一张", "another one", "one more meme", "anything else"]
        negatives = ["继续", "下一个", "another task", "what else should we fix"]
        for prompt in positives:
            self.assertTrue(reaction.is_followup_request(prompt), prompt)
        for prompt in negatives:
            self.assertFalse(reaction.is_followup_request(prompt), prompt)

    def test_dynamic_requests_and_technical_discussion(self):
        positives = [
            "动态的有没有？",
            "不来个动图吗？",
            "send me a GIF",
            "Do you have animated memes?",
            "What about an animated reaction?",
        ]
        negatives = [
            "GIF",
            "what is a GIF",
            "GIF vs PNG",
            "explain animated GIF compression",
            "动态",
        ]
        for prompt in positives:
            self.assertEqual("gif", reaction.requested_asset_kind(prompt), prompt)
        for prompt in negatives:
            self.assertIsNone(reaction.requested_asset_kind(prompt), prompt)

    def test_skip_rules_are_bilingual(self):
        cfg = reaction.load_config()
        for prompt in [
            "请认真回答这个事故问题",
            "只输出 JSON",
            "只给代码",
            "只返回补丁",
            "Please answer seriously about the accident",
            "Return only valid JSON",
            "Output only code",
            "Only the patch",
            "Do not send a meme",
        ]:
            self.assertIsNotNone(reaction.skip_reason(prompt, cfg), prompt)
        self.assertIsNone(reaction.skip_reason("this is a serious performance optimization", cfg))

    def test_ascii_skip_rules_preserve_words_and_mixed_language_boundaries(self):
        cfg = reaction.load_config()
        self.assertIsNone(reaction.skip_reason("I studied the codebase", cfg))
        self.assertIsNone(reaction.skip_reason("decode only once", cfg))
        self.assertEqual("keyword", reaction.skip_reason("The process died", cfg))
        self.assertEqual("phrase", reaction.skip_reason("json only", cfg))
        self.assertEqual("keyword", reaction.skip_reason("他died了", cfg))
        self.assertEqual("phrase", reaction.skip_reason("请json only", cfg))


class RuntimeDecisionTests(unittest.TestCase):
    def test_default_config_is_portable_and_bounded(self):
        self.assertEqual(0.2, reaction.DEFAULTS["probability"])
        self.assertEqual([], reaction.DEFAULTS["asset_roots"])
        self.assertFalse(reaction.DEFAULTS["remote"]["enabled"])
        with RuntimeSandbox(config_overrides={
            "probability": 4,
            "cooldown_turns": -2,
            "warmup_turns": "bad",
            "max_sessions": 0,
            "remote": {
                "enabled": True,
                "allowed_hosts": [" CDN.EXAMPLE.COM ", ""],
                "timeout_seconds": 999,
                "max_asset_bytes": 1,
                "max_assets": 9999,
            },
        }):
            cfg = reaction.load_config()
            self.assertEqual(1.0, cfg["probability"])
            self.assertEqual(0, cfg["cooldown_turns"])
            self.assertEqual(2, cfg["warmup_turns"])
            self.assertEqual(1, cfg["max_sessions"])
            self.assertTrue(cfg["remote"]["enabled"])
            self.assertEqual(["cdn.example.com"], cfg["remote"]["allowed_hosts"])
            self.assertEqual(30, cfg["remote"]["timeout_seconds"])
            self.assertEqual(1024, cfg["remote"]["max_asset_bytes"])
            self.assertEqual(500, cfg["remote"]["max_assets"])

    def test_warmup_probability_offer_and_cooldown(self):
        with RuntimeSandbox() as sandbox:
            session = "flow"
            first = sandbox.run_main(reaction, {"session_id": session, "turn_id": "1", "prompt": "hello"})
            second = sandbox.run_main(reaction, {"session_id": session, "turn_id": "2", "prompt": "hello"})
            self.assertEqual("", first)
            self.assertEqual("", second)
            with mock.patch.object(reaction.random, "random", return_value=0.99):
                third = sandbox.run_main(reaction, {"session_id": session, "turn_id": "3", "prompt": "hello"})
            self.assertEqual("", third)
            with mock.patch.object(reaction.random, "random", return_value=0.0):
                fourth = sandbox.run_main(reaction, {"session_id": session, "turn_id": "4", "prompt": "hello"})
            payload = json.loads(fourth)
            self.assertEqual("UserPromptSubmit", payload["hookSpecificOutput"]["hookEventName"])
            fifth = sandbox.run_main(reaction, {"session_id": session, "turn_id": "5", "prompt": "hello"})
            self.assertEqual("", fifth)
            events = [entry["event"] for entry in sandbox.read_log()]
            self.assertEqual(["MISS", "MISS", "MISS", "OFFER", "COOL"], events)

    def test_direct_request_bypasses_warmup(self):
        with RuntimeSandbox() as sandbox:
            output = sandbox.run_main(
                reaction,
                {"session_id": "direct", "turn_id": "1", "prompt": "send me a meme"},
            )
            payload = json.loads(output)
            self.assertIn("[rx:", payload["hookSpecificOutput"]["additionalContext"])
            event = sandbox.read_log()[-1]
            self.assertEqual("FORCED", event["event"])
            self.assertEqual("direct", event["trigger"])

    def test_followup_bypasses_cooldown_only_with_play_chain(self):
        with RuntimeSandbox() as sandbox:
            sandbox.write_state({
                "version": reaction.STATE_VERSION,
                "sessions": {
                    "follow": {
                        "turn": 3,
                        "last_hit": 3,
                        "protocol_version": None,
                        "pending_offer": None,
                        "play_chain": True,
                    }
                },
            })
            output = sandbox.run_main(
                reaction,
                {"session_id": "follow", "turn_id": "4", "prompt": "another one"},
            )
            self.assertTrue(output)
            event = sandbox.read_log()[-1]
            self.assertEqual("FORCED", event["event"])
            self.assertEqual("followup", event["trigger"])

    def test_dynamic_request_only_offers_gifs(self):
        specs = [
            ("01", "one.gif", "one"),
            ("02", "two.gif", "two"),
            ("03", "three.gif", "three"),
            ("04", "four.jpg", "four"),
        ]
        with RuntimeSandbox(asset_specs=specs) as sandbox:
            output = sandbox.run_main(
                reaction,
                {"session_id": "gif", "turn_id": "1", "prompt": "send me a GIF"},
            )
            payload = json.loads(output)
            context = payload["hookSpecificOutput"]["additionalContext"]
            self.assertNotIn("four.jpg", context)
            self.assertEqual(3, context.lower().count(".gif"))
            self.assertEqual("gif", sandbox.read_log()[-1]["asset_kind"])

    def test_fewer_than_three_assets_logs_error(self):
        with RuntimeSandbox(asset_specs=[("01", "one.jpg", "one"), ("02", "two.jpg", "two")]) as sandbox:
            output = sandbox.run_main(
                reaction,
                {"session_id": "few", "turn_id": "1", "prompt": "send me a meme"},
            )
            self.assertEqual("", output)
            self.assertEqual("ERROR", sandbox.read_log()[-1]["event"])

    def test_skip_logs_never_include_default_rule_text(self):
        with RuntimeSandbox() as sandbox:
            cfg = reaction.load_config()
            keywords = [str(value) for value in cfg["skip_keywords"]]
            phrases = [str(value) for value in cfg["skip_phrases"]]
            for index, rule in enumerate(keywords + phrases, start=1):
                output = sandbox.run_main(
                    reaction,
                    {
                        "session_id": "privacy",
                        "turn_id": str(index),
                        "prompt": rule,
                    },
                )
                self.assertEqual("", output)

            entries = sandbox.read_log()
            self.assertEqual(len(keywords) + len(phrases), len(entries))
            self.assertEqual(
                ["keyword"] * len(keywords) + ["phrase"] * len(phrases),
                [entry.get("reason") for entry in entries],
            )
            serialized = sandbox.log_path.read_text(encoding="utf-8").lower()
            for rule in keywords + phrases:
                self.assertNotIn(rule.lower(), serialized, rule)

    def test_logging_can_be_disabled_without_disabling_reactions(self):
        with RuntimeSandbox(config_overrides={"log": False}) as sandbox:
            output = sandbox.run_main(
                reaction,
                {"session_id": "no-log", "turn_id": "1", "prompt": "send me a meme"},
            )
            self.assertTrue(output)
            self.assertFalse(sandbox.log_path.exists())

    def test_log_rotates_at_size_limit_and_keeps_one_backup(self):
        with RuntimeSandbox() as sandbox:
            current_contents = "x" * 128
            backup_path = sandbox.log_path.with_name(sandbox.log_path.name + ".1")
            sandbox.log_path.write_text(current_contents, encoding="utf-8")
            backup_path.write_text("older", encoding="utf-8")

            with mock.patch.object(reaction, "LOG_MAX_BYTES", 64):
                reaction.log_event(
                    reaction.load_config(),
                    "MISS",
                    session_id="rotate",
                    turn_id="1",
                    turn=1,
                    reason="probability",
                )

            self.assertEqual(current_contents, backup_path.read_text(encoding="utf-8"))
            self.assertEqual("MISS", sandbox.read_log()[0]["event"])


if __name__ == "__main__":
    unittest.main()
