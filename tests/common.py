import io
import json
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
HOOKS_DIR = ROOT / "hooks"
if str(HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(HOOKS_DIR))

import reaction  # noqa: E402
import session_start  # noqa: E402
import stop as stop_hook  # noqa: E402


class RuntimeSandbox:
    def __init__(self, asset_specs=None, config_overrides=None):
        self._temporary = tempfile.TemporaryDirectory()
        self.root = Path(self._temporary.name)
        self.assets_dir = self.root / "assets"
        self.assets_dir.mkdir()
        self.config_path = self.root / "reaction.json"
        self.manifest_path = self.root / "manifest.json"
        self.state_path = self.root / ".reaction_state.json"
        self.log_path = self.root / "reaction.log"
        self._patcher = mock.patch.multiple(
            reaction,
            CONFIG_PATH=str(self.config_path),
            MANIFEST_PATH=str(self.manifest_path),
            STATE_PATH=str(self.state_path),
            LOG_PATH=str(self.log_path),
        )
        self._patcher.start()
        self.write_config(config_overrides or {})
        specs = asset_specs if asset_specs is not None else [
            ("01", "one.jpg", "one"),
            ("02", "two.png", "two"),
            ("03", "three.gif", "three"),
        ]
        self.write_assets(specs)

    def close(self):
        self._patcher.stop()
        self._temporary.cleanup()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def write_config(self, overrides=None):
        config = {
            "enabled": True,
            "probability": 0.2,
            "cooldown_turns": 5,
            "warmup_turns": 2,
            "asset_roots": [self.assets_dir.as_posix()],
            "log": True,
            "max_sessions": 40,
        }
        config.update(overrides or {})
        self.config_path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")

    def write_assets(self, specs):
        manifest = []
        for asset_id, filename, label in specs:
            path = self.assets_dir / filename
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"test")
            manifest.append({
                "id": asset_id,
                "path": path.resolve().as_posix(),
                "label": label,
                "enabled": True,
            })
        self.manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
        return manifest

    def read_state(self):
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def write_state(self, value):
        self.state_path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")

    def read_log(self):
        if not self.log_path.exists():
            return []
        return [json.loads(line) for line in self.log_path.read_text(encoding="utf-8").splitlines() if line]

    @staticmethod
    def run_main(module, event):
        output = io.StringIO()
        stdin = io.StringIO(json.dumps(event, ensure_ascii=False))
        with mock.patch.object(sys, "stdin", stdin), redirect_stdout(output):
            try:
                module.main()
            except SystemExit:
                pass
        return output.getvalue()
