import unittest
from pathlib import Path

from common import ROOT


class PrivacyTests(unittest.TestCase):
    def test_repository_contains_no_private_runtime_artifacts(self):
        forbidden_names = {"reaction.log", ".reaction_state.json", "manifest.json"}
        found = []
        for path in ROOT.rglob("*"):
            if any(part in {".git", "__pycache__"} for part in path.parts):
                continue
            if path.is_file() and path.name in forbidden_names:
                found.append(path.relative_to(ROOT).as_posix())
            if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp"}:
                found.append(path.relative_to(ROOT).as_posix())
        self.assertEqual([], found)

    def test_repository_contains_no_private_path_literals(self):
        forbidden = ["xx" + "H7r", "G:" + "/r"]
        matches = []
        for path in ROOT.rglob("*"):
            if any(part in {".git", "__pycache__"} for part in path.parts) or not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for value in forbidden:
                if value in text:
                    matches.append((path.relative_to(ROOT).as_posix(), value))
        self.assertEqual([], matches)

    def test_hooks_have_no_network_dependencies(self):
        combined = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "hooks").glob("*.py"))
        for module in ["requests", "urllib", "http.client", "socket"]:
            self.assertNotIn("import " + module, combined)


if __name__ == "__main__":
    unittest.main()
