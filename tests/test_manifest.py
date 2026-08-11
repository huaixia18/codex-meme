import json
import tempfile
import unittest
from pathlib import Path

from common import RuntimeSandbox, reaction


class ManifestTests(unittest.TestCase):
    def test_manifest_is_an_explicit_validated_whitelist(self):
        with RuntimeSandbox(asset_specs=[]) as sandbox, tempfile.TemporaryDirectory() as outside_temp:
            valid = sandbox.assets_dir / "valid.jpg"
            duplicate_path = valid
            bad_extension = sandbox.assets_dir / "bad.txt"
            missing = sandbox.assets_dir / "missing.png"
            outside = Path(outside_temp) / "outside.jpg"
            for path in (valid, bad_extension, outside):
                path.write_bytes(b"test")
            manifest = [
                {"id": "01", "path": valid.as_posix(), "label": "valid", "enabled": True},
                {"id": "01", "path": (sandbox.assets_dir / "other.jpg").as_posix(), "label": "duplicate id"},
                {"id": "02", "path": duplicate_path.as_posix(), "label": "duplicate path"},
                {"id": "03", "path": bad_extension.as_posix(), "label": "bad extension"},
                {"id": "04", "path": missing.as_posix(), "label": "missing"},
                {"id": "05", "path": outside.as_posix(), "label": "outside root"},
                {"id": "06", "path": valid.as_posix(), "label": "disabled", "enabled": False},
                {"id": "07", "path": "", "label": "empty"},
            ]
            (sandbox.assets_dir / "other.jpg").write_bytes(b"test")
            sandbox.manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            assets = reaction.load_assets()
            self.assertEqual(["01"], [asset["id"] for asset in assets])

    def test_allowed_root_does_not_match_sibling_prefix(self):
        with RuntimeSandbox(asset_specs=[]) as sandbox:
            sibling = sandbox.root / "assets-other"
            sibling.mkdir()
            path = sibling / "image.jpg"
            path.write_bytes(b"test")
            self.assertFalse(reaction.path_is_allowed(str(path), reaction.load_config()))

    def test_manifest_sanitizes_labels_and_rejects_invalid_ids(self):
        with RuntimeSandbox(asset_specs=[]) as sandbox:
            filenames = [
                "valid.jpg",
                "empty-label.jpg",
                "unicode-id.jpg",
                "spaced-id.jpg",
                "long-id.jpg",
                "second-valid.jpg",
            ]
            paths = {}
            for filename in filenames:
                path = sandbox.assets_dir / filename
                path.write_bytes(b"test")
                paths[filename] = path.as_posix()

            manifest = [
                {
                    "id": "valid_01",
                    "path": paths["valid.jpg"],
                    "label": "  hello\n\tworld\u0000" + ("x" * 100),
                },
                {
                    "id": "empty_label",
                    "path": paths["empty-label.jpg"],
                    "label": "\n\t\u0000\u200b",
                },
                {"id": "中文", "path": paths["unicode-id.jpg"], "label": "unicode id"},
                {"id": "bad id", "path": paths["spaced-id.jpg"], "label": "spaced id"},
                {"id": "a" * 65, "path": paths["long-id.jpg"], "label": "long id"},
                {"id": "A-b_2", "path": paths["second-valid.jpg"], "label": "second"},
            ]
            sandbox.manifest_path.write_text(
                json.dumps(manifest, ensure_ascii=False),
                encoding="utf-8",
            )

            assets = reaction.load_assets()
            self.assertEqual(["valid_01", "A-b_2"], [asset["id"] for asset in assets])
            cleaned_label = assets[0]["label"]
            self.assertEqual(80, len(cleaned_label))
            self.assertTrue(cleaned_label.startswith("hello world"))
            self.assertNotIn("\n", cleaned_label)
            self.assertNotIn("\t", cleaned_label)
            self.assertNotIn("\u0000", cleaned_label)


if __name__ == "__main__":
    unittest.main()
