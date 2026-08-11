import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from common import reaction

import sync_remote


class RemoteSyncSandbox:
    def __init__(self):
        self._temporary = tempfile.TemporaryDirectory()
        self.root = Path(self._temporary.name)
        self.config_path = self.root / "reaction.json"
        self.local_manifest_path = self.root / "manifest.json"
        self.remote_manifest_path = self.root / ".remote_manifest.json"
        self.remote_state_path = self.root / ".remote_state.json"
        self.cache_dir = self.root / "remote-cache"
        self.local_manifest_path.write_text("[]", encoding="utf-8")
        self._patcher = mock.patch.multiple(
            sync_remote,
            REMOTE_MANIFEST_PATH=str(self.remote_manifest_path),
            REMOTE_STATE_PATH=str(self.remote_state_path),
            REMOTE_CACHE_DIR=str(self.cache_dir),
        )
        self._reaction_patcher = mock.patch.multiple(
            reaction,
            CONFIG_PATH=str(self.config_path),
            MANIFEST_PATH=str(self.local_manifest_path),
            REMOTE_MANIFEST_PATH=str(self.remote_manifest_path),
            REMOTE_CACHE_DIR=str(self.cache_dir),
        )
        self._patcher.start()
        self._reaction_patcher.start()

    def close(self):
        self._reaction_patcher.stop()
        self._patcher.stop()
        self._temporary.cleanup()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def write_config(self, **remote_overrides):
        remote = {
            "enabled": True,
            "manifest_url": "https://cdn.example.com/memes/manifest.json",
            "allowed_hosts": ["cdn.example.com"],
            "refresh_hours": 24,
            "retry_minutes": 15,
            "timeout_seconds": 5,
            "max_manifest_bytes": 64 * 1024,
            "max_asset_bytes": 1024,
            "max_assets": 20,
        }
        remote.update(remote_overrides)
        config = {
            "enabled": True,
            "asset_roots": [],
            "allowed_extensions": [".png", ".jpg", ".jpeg", ".gif", ".webp"],
            "remote": remote,
        }
        self.config_path.write_text(json.dumps(config), encoding="utf-8")
        return config


class RemoteUrlValidationTests(unittest.TestCase):
    def test_host_resolution_returns_unique_addresses(self):
        answers = [
            (socket_family, None, None, None, (address, 443))
            for socket_family, address in [(2, "93.184.216.34"), (2, "93.184.216.34"), (10, "2606:2800:220:1::")]
        ]
        with mock.patch.object(sync_remote.socket, "getaddrinfo", return_value=answers):
            self.assertEqual(
                ["2606:2800:220:1::", "93.184.216.34"],
                sync_remote.resolve_host_addresses("cdn.example.com"),
            )

    def test_remote_urls_require_https_allowlisted_public_hosts(self):
        public = lambda host: ["93.184.216.34"]
        private = lambda host: ["127.0.0.1"]
        allowed = ["cdn.example.com"]

        self.assertEqual(
            "https://cdn.example.com/memes/one.jpg",
            sync_remote.validate_remote_url(
                "https://cdn.example.com/memes/one.jpg",
                allowed,
                resolver=public,
            ),
        )
        for url, resolver in [
            ("", public),
            ("http://cdn.example.com/one.jpg", public),
            ("https://other.example.com/one.jpg", public),
            ("https://user:pass@cdn.example.com/one.jpg", public),
            ("https://cdn.example.com:8443/one.jpg", public),
            ("https://cdn.example.com/one.jpg", private),
            ("https://127.0.0.1/one.jpg", private),
        ]:
            with self.subTest(url=url), self.assertRaises(ValueError):
                sync_remote.validate_remote_url(url, allowed, resolver=resolver)
        with self.assertRaises(ValueError):
            sync_remote.validate_remote_url("https://cdn.example.com/one.jpg", allowed, resolver=lambda host: [])
        with self.assertRaises(ValueError):
            sync_remote.validate_remote_url(
                "https://cdn.example.com/one.jpg", allowed, resolver=lambda host: ["not-an-ip"]
            )

    def test_read_limited_rejects_oversized_responses(self):
        response = mock.Mock()
        response.headers = {}
        response.read.side_effect = [b"1234", b"5"]
        with self.assertRaises(ValueError):
            sync_remote.read_limited(response, 4)
        declared = mock.Mock()
        declared.headers = {"Content-Length": "5"}
        with self.assertRaises(ValueError):
            sync_remote.read_limited(declared, 4)

    def test_fetch_bytes_revalidates_final_url_and_normalizes_content_type(self):
        response = mock.MagicMock()
        response.__enter__.return_value = response
        response.geturl.return_value = "https://cdn.example.com/final.jpg"
        response.headers = {"Content-Type": "image/jpeg; charset=binary"}
        response.read.side_effect = [b"body", b""]
        opener = mock.Mock()
        opener.open.return_value = response
        with mock.patch.object(sync_remote, "build_opener", return_value=opener), mock.patch.object(
            sync_remote.ssl, "create_default_context", return_value=mock.Mock()
        ), mock.patch.object(
            sync_remote, "validate_remote_url", side_effect=lambda url, hosts, resolver: url
        ) as validate:
            body, content_type = sync_remote.fetch_bytes(
                "https://cdn.example.com/start.jpg",
                allowed_hosts=["cdn.example.com"],
                timeout=3,
                max_bytes=10,
                resolver=lambda host: ["93.184.216.34"],
            )
        self.assertEqual(b"body", body)
        self.assertEqual("image/jpeg", content_type)
        self.assertEqual(2, validate.call_count)

    def test_redirect_handler_revalidates_the_destination(self):
        resolver = lambda host: ["93.184.216.34"]
        handler = sync_remote.SafeRedirectHandler(["cdn.example.com"], resolver)
        with mock.patch.object(
            sync_remote.HTTPRedirectHandler, "redirect_request", return_value="redirected"
        ) as parent:
            result = handler.redirect_request(
                mock.Mock(), mock.Mock(), 302, "Found", {}, "https://cdn.example.com/final.jpg"
            )
        self.assertEqual("redirected", result)
        self.assertEqual("https://cdn.example.com/final.jpg", parent.call_args.args[-1])

    def test_catalog_shape_and_image_signatures_are_strict(self):
        for data in (b"not-json", b"{}", b"[]"):
            with self.subTest(data=data), self.assertRaises(ValueError):
                sync_remote.parse_catalog(data, 10)
        self.assertTrue(sync_remote.image_signature_matches(b"RIFFxxxxWEBPdata", ".webp"))
        self.assertFalse(sync_remote.image_signature_matches(b"not-an-image", ".webp"))
        self.assertFalse(sync_remote.image_signature_matches(b"data", ".bmp"))

    def test_cache_directory_must_be_a_direct_runtime_child(self):
        with RemoteSyncSandbox() as sandbox, tempfile.TemporaryDirectory() as outside:
            with mock.patch.object(sync_remote, "REMOTE_CACHE_DIR", str(Path(outside) / "cache")):
                with self.assertRaises(ValueError):
                    sync_remote.resolve_cache_dir()


class RemoteSyncTests(unittest.TestCase):
    def test_sync_downloads_catalog_to_local_cache_manifest(self):
        with RemoteSyncSandbox() as sandbox:
            sandbox.write_config()
            payloads = {
                "https://cdn.example.com/memes/one.jpg": (b"\xff\xd8\xffone", "image/jpeg"),
                "https://cdn.example.com/memes/two.png": (b"\x89PNG\r\n\x1a\ntwo", "image/png"),
                "https://cdn.example.com/memes/three.gif": (b"GIF89athree", "image/gif"),
            }
            catalog = []
            for index, (url, (body, _)) in enumerate(payloads.items(), start=1):
                catalog.append({
                    "id": f"remote-{index}",
                    "url": url,
                    "sha256": hashlib.sha256(body).hexdigest(),
                    "label": f"remote {index}",
                    "enabled": True,
                })

            def fake_fetch(url, **kwargs):
                if url.endswith("manifest.json"):
                    return json.dumps(catalog).encode("utf-8"), "application/json"
                return payloads[url]

            with mock.patch.object(sync_remote, "fetch_bytes", side_effect=fake_fetch), mock.patch.object(
                sync_remote, "resolve_host_addresses", return_value=["93.184.216.34"]
            ):
                result = sync_remote.sync_remote_assets(force=True, now=1_000_000)

            self.assertEqual("updated", result["status"])
            self.assertEqual(3, result["asset_count"])
            generated = json.loads(sandbox.remote_manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(["remote-1", "remote-2", "remote-3"], [item["id"] for item in generated])
            for item in generated:
                cached_path = Path(item["path"])
                self.assertTrue(cached_path.is_file())
                self.assertTrue(cached_path.is_relative_to(sandbox.cache_dir.resolve()))
                self.assertNotIn("url", item)
                self.assertNotIn("sha256", item)

            loaded = reaction.load_assets()
            self.assertEqual(3, len(loaded))
            self.assertTrue(all(Path(item["path"]).is_file() for item in loaded))

    def test_fresh_cache_skips_network(self):
        with RemoteSyncSandbox() as sandbox:
            sandbox.write_config()
            sandbox.remote_manifest_path.write_text("[]", encoding="utf-8")
            remote = reaction.load_config()["remote"]
            sandbox.remote_state_path.write_text(
                json.dumps({
                    "last_attempt": 999_000,
                    "last_success": 999_000,
                    "source": sync_remote.source_fingerprint(remote),
                }),
                encoding="utf-8",
            )
            with mock.patch.object(sync_remote, "fetch_bytes") as fetch:
                result = sync_remote.sync_remote_assets(now=1_000_000)
            self.assertEqual("fresh", result["status"])
            fetch.assert_not_called()

    def test_changed_source_bypasses_old_freshness_state(self):
        with RemoteSyncSandbox() as sandbox:
            sandbox.write_config()
            sandbox.remote_manifest_path.write_text("[]", encoding="utf-8")
            sandbox.remote_state_path.write_text(
                json.dumps({"last_attempt": 999_000, "last_success": 999_000, "source": "old"}),
                encoding="utf-8",
            )
            with mock.patch.object(sync_remote, "fetch_bytes", side_effect=ValueError("offline")) as fetch:
                result = sync_remote.sync_remote_assets(now=1_000_000)
            self.assertEqual("failed", result["status"])
            fetch.assert_called_once()

    def test_malformed_timestamps_do_not_disable_future_syncs(self):
        with RemoteSyncSandbox() as sandbox:
            sandbox.write_config()
            remote = reaction.load_config()["remote"]
            sandbox.remote_manifest_path.write_text("[]", encoding="utf-8")
            sandbox.remote_state_path.write_text(
                json.dumps({
                    "last_attempt": "bad",
                    "last_success": "also-bad",
                    "source": sync_remote.source_fingerprint(remote),
                }),
                encoding="utf-8",
            )
            with mock.patch.object(sync_remote, "fetch_bytes", side_effect=ValueError("offline")) as fetch:
                result = sync_remote.sync_remote_assets(now=1_000_000)
            self.assertEqual("failed", result["status"])
            fetch.assert_called_once()

    def test_failed_sync_preserves_last_good_manifest(self):
        with RemoteSyncSandbox() as sandbox:
            sandbox.write_config()
            cached = sandbox.cache_dir / "existing.jpg"
            cached.parent.mkdir()
            cached.write_bytes(b"existing")
            previous = [{
                "id": "existing",
                "path": cached.as_posix(),
                "label": "existing",
                "enabled": True,
            }]
            original_text = json.dumps(previous)
            sandbox.remote_manifest_path.write_text(original_text, encoding="utf-8")
            catalog = [{
                "id": "broken",
                "url": "https://cdn.example.com/memes/broken.jpg",
                "sha256": "0" * 64,
                "label": "broken",
                "enabled": True,
            }]

            def fake_fetch(url, **kwargs):
                if url.endswith("manifest.json"):
                    return json.dumps(catalog).encode("utf-8"), "application/json"
                return b"tampered", "image/jpeg"

            with mock.patch.object(sync_remote, "fetch_bytes", side_effect=fake_fetch), mock.patch.object(
                sync_remote, "resolve_host_addresses", return_value=["93.184.216.34"]
            ):
                result = sync_remote.sync_remote_assets(force=True, now=1_000_000)

            self.assertEqual("failed", result["status"])
            self.assertEqual(original_text, sandbox.remote_manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(b"existing", cached.read_bytes())

    def test_disabled_remote_mode_never_touches_network(self):
        with RemoteSyncSandbox() as sandbox:
            sandbox.write_config(enabled=False)
            with mock.patch.object(sync_remote, "fetch_bytes") as fetch:
                result = sync_remote.sync_remote_assets(force=True)
            self.assertEqual("disabled", result["status"])
            fetch.assert_not_called()

    def test_unconfigured_and_retry_backoff_modes_skip_network(self):
        with RemoteSyncSandbox() as sandbox:
            sandbox.write_config(manifest_url="")
            with mock.patch.object(sync_remote, "fetch_bytes") as fetch:
                self.assertEqual("unconfigured", sync_remote.sync_remote_assets()["status"])
            fetch.assert_not_called()

            sandbox.write_config()
            remote = reaction.load_config()["remote"]
            sandbox.remote_manifest_path.write_text("[]", encoding="utf-8")
            sandbox.remote_state_path.write_text(
                json.dumps({
                    "last_attempt": 999_500,
                    "source": sync_remote.source_fingerprint(remote),
                }),
                encoding="utf-8",
            )
            with mock.patch.object(sync_remote, "fetch_bytes") as fetch:
                self.assertEqual("backoff", sync_remote.sync_remote_assets(now=1_000_000)["status"])
            fetch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
