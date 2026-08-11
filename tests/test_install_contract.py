import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from common import ROOT


def render_fragment():
    text = (ROOT / "templates" / "hooks.fragment.json").read_text(encoding="utf-8")
    text = text.replace("{{PYTHON_COMMAND}}", "py -3")
    text = text.replace("{{INSTALL_DIR}}", "C:/Users/example/.codex/hooks/codex-meme")
    return json.loads(text)


def is_codex_meme_handler(handler):
    command = str(handler.get("command") or "").replace("\\", "/").lower()
    return "/codex-meme/" in command


def remove_codex_meme_handlers(document):
    result = copy.deepcopy(document)
    events = result.setdefault("hooks", {})
    for event_name in list(events):
        groups = []
        for group in events[event_name]:
            kept = [handler for handler in group.get("hooks", []) if not is_codex_meme_handler(handler)]
            if kept:
                updated = copy.deepcopy(group)
                updated["hooks"] = kept
                groups.append(updated)
        if groups:
            events[event_name] = groups
        else:
            events.pop(event_name, None)
    return result


def merge_fragment(document, fragment):
    result = remove_codex_meme_handlers(document)
    events = result.setdefault("hooks", {})
    for event_name, groups in fragment["hooks"].items():
        events.setdefault(event_name, []).extend(copy.deepcopy(groups))
    return result


class InstallContractTests(unittest.TestCase):
    def test_fragment_is_valid_and_contains_four_handlers(self):
        fragment = render_fragment()
        self.assertEqual({"SessionStart", "UserPromptSubmit", "Stop"}, set(fragment["hooks"]))
        commands = [
            handler["command"]
            for groups in fragment["hooks"].values()
            for group in groups
            for handler in group["hooks"]
        ]
        self.assertEqual(4, len(commands))
        self.assertTrue(all("/codex-meme/" in command for command in commands))

    def test_install_update_and_uninstall_preserve_unrelated_hooks(self):
        existing = {
            "custom": {"keep": True},
            "hooks": {
                "SubagentStart": [{
                    "matcher": "canvas-tool",
                    "hooks": [{"type": "command", "command": "sh C:/tools/context.sh"}],
                }],
                "Stop": [{
                    "hooks": [{"type": "command", "command": "python C:/tools/audit.py"}],
                }],
            },
        }
        fragment = render_fragment()
        installed = merge_fragment(existing, fragment)
        updated = merge_fragment(installed, fragment)
        commands = [
            handler["command"]
            for groups in updated["hooks"].values()
            for group in groups
            for handler in group.get("hooks", [])
        ]
        self.assertEqual(4, sum("/codex-meme/" in command for command in commands))
        self.assertIn("sh C:/tools/context.sh", commands)
        self.assertIn("python C:/tools/audit.py", commands)
        self.assertEqual({"keep": True}, updated["custom"])

        uninstalled = remove_codex_meme_handlers(updated)
        self.assertEqual(existing, uninstalled)

    def test_repository_has_no_agent_instruction_file(self):
        forbidden_name = "AGENT" + "S.md"
        self.assertEqual([], list(ROOT.rglob(forbidden_name)))

    def test_isolated_codex_home_install_update_run_and_uninstall(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            codex_home = root / ".codex"
            install_dir = codex_home / "hooks" / "codex-meme"
            assets_dir = root / "memes"
            backup_dir = codex_home / "backups" / "codex-meme" / "test-uninstall"
            install_dir.mkdir(parents=True)
            assets_dir.mkdir()
            hooks_file = codex_home / "hooks.json"

            existing = {
                "hooks": {
                    "SubagentStart": [{
                        "matcher": "canvas-tool",
                        "hooks": [{"type": "command", "command": "sh C:/tools/context.sh"}],
                    }]
                }
            }
            hooks_file.write_text(json.dumps(existing), encoding="utf-8")

            for filename in ("reaction.py", "session_start.py", "stop.py", "sync_remote.py"):
                shutil.copy2(ROOT / "hooks" / filename, install_dir / filename)

            manifest = []
            for index, suffix in enumerate((".jpg", ".png", ".gif"), start=1):
                asset = assets_dir / f"asset-{index}{suffix}"
                asset.write_bytes(b"test")
                manifest.append({
                    "id": f"{index:02d}",
                    "path": asset.as_posix(),
                    "label": f"asset {index}",
                    "enabled": True,
                })
            config = json.loads((ROOT / "templates" / "reaction.json").read_text(encoding="utf-8"))
            config["asset_roots"] = [assets_dir.as_posix()]
            (install_dir / "reaction.json").write_text(json.dumps(config), encoding="utf-8")
            (install_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

            fragment_text = (ROOT / "templates" / "hooks.fragment.json").read_text(encoding="utf-8")
            fragment_text = fragment_text.replace("{{PYTHON_COMMAND}}", "py -3")
            fragment_text = fragment_text.replace("{{INSTALL_DIR}}", install_dir.as_posix())
            fragment = json.loads(fragment_text)
            installed = merge_fragment(existing, fragment)
            updated = merge_fragment(installed, fragment)
            hooks_file.write_text(json.dumps(updated), encoding="utf-8")

            commands = [
                handler["command"]
                for groups in updated["hooks"].values()
                for group in groups
                for handler in group.get("hooks", [])
            ]
            self.assertEqual(4, sum("/codex-meme/" in command for command in commands))
            self.assertIn("sh C:/tools/context.sh", commands)

            startup = subprocess.run(
                [sys.executable, str(install_dir / "session_start.py")],
                input=json.dumps({"source": "startup", "session_id": "install-test"}),
                text=True,
                capture_output=True,
                check=True,
            )
            startup_payload = json.loads(startup.stdout)
            self.assertEqual("SessionStart", startup_payload["hookSpecificOutput"]["hookEventName"])

            sync = subprocess.run(
                [sys.executable, str(install_dir / "sync_remote.py")],
                text=True,
                capture_output=True,
                check=True,
            )
            self.assertEqual({}, json.loads(sync.stdout))

            direct = subprocess.run(
                [sys.executable, str(install_dir / "reaction.py")],
                input=json.dumps({
                    "session_id": "install-direct",
                    "turn_id": "turn-1",
                    "prompt": "send me a meme",
                }),
                text=True,
                capture_output=True,
                check=True,
            )
            direct_payload = json.loads(direct.stdout)
            self.assertIn("[rx:", direct_payload["hookSpecificOutput"]["additionalContext"])

            uninstalled = remove_codex_meme_handlers(updated)
            hooks_file.write_text(json.dumps(uninstalled), encoding="utf-8")
            backup_dir.parent.mkdir(parents=True)
            shutil.move(str(install_dir), str(backup_dir))

            self.assertEqual(existing, json.loads(hooks_file.read_text(encoding="utf-8")))
            self.assertFalse(install_dir.exists())
            self.assertTrue((backup_dir / "reaction.py").exists())
            self.assertEqual(3, len(list(assets_dir.iterdir())))


if __name__ == "__main__":
    unittest.main()
