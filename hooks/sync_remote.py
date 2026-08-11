#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fetch an explicit remote meme manifest into a bounded local cache."""

import hashlib
import ipaddress
import json
import os
import re
import socket
import ssl
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from urllib.request import HTTPSHandler, HTTPRedirectHandler, Request, build_opener

from reaction import ASSET_ID_PATTERN, load_config, load_json, sanitize_label


HERE = os.path.dirname(os.path.abspath(__file__))
REMOTE_MANIFEST_PATH = os.path.join(HERE, ".remote_manifest.json")
REMOTE_STATE_PATH = os.path.join(HERE, ".remote_state.json")
REMOTE_CACHE_DIR = os.path.join(HERE, "remote-cache")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
IMAGE_CONTENT_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
}


def resolve_host_addresses(host):
    addresses = set()
    for result in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM):
        addresses.add(result[4][0])
    return sorted(addresses)


def validate_remote_url(url, allowed_hosts, resolver=None):
    resolver = resolver or resolve_host_addresses
    text = str(url or "").strip()
    if not text or len(text) > 2048:
        raise ValueError("invalid_url")
    parsed = urlsplit(text)
    host = (parsed.hostname or "").lower()
    allowed = {str(item).strip().lower() for item in allowed_hosts if str(item).strip()}
    if parsed.scheme.lower() != "https" or not host or host not in allowed:
        raise ValueError("url_not_allowed")
    if parsed.username is not None or parsed.password is not None or parsed.port not in (None, 443):
        raise ValueError("url_authority_not_allowed")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise ValueError("ip_literal_not_allowed")
    addresses = resolver(host)
    if not addresses:
        raise ValueError("host_unresolved")
    for address in addresses:
        try:
            parsed_address = ipaddress.ip_address(address)
        except ValueError as error:
            raise ValueError("invalid_host_address") from error
        if not parsed_address.is_global:
            raise ValueError("host_not_public")
    normalized_netloc = host if parsed.port is None else "%s:%s" % (host, parsed.port)
    return urlunsplit(("https", normalized_netloc, parsed.path or "/", parsed.query, ""))


class SafeRedirectHandler(HTTPRedirectHandler):
    def __init__(self, allowed_hosts, resolver):
        super().__init__()
        self.allowed_hosts = allowed_hosts
        self.resolver = resolver

    def redirect_request(self, request, file_pointer, code, message, headers, new_url):
        safe_url = validate_remote_url(new_url, self.allowed_hosts, self.resolver)
        return super().redirect_request(request, file_pointer, code, message, headers, safe_url)


def read_limited(response, maximum_bytes):
    declared = response.headers.get("Content-Length") if getattr(response, "headers", None) else None
    if declared:
        try:
            if int(declared) > maximum_bytes:
                raise ValueError("response_too_large")
        except (TypeError, ValueError) as error:
            if str(error) == "response_too_large":
                raise
    chunks = []
    total = 0
    while True:
        chunk = response.read(min(65536, maximum_bytes - total + 1))
        if not chunk:
            break
        total += len(chunk)
        if total > maximum_bytes:
            raise ValueError("response_too_large")
        chunks.append(chunk)
    return b"".join(chunks)


def fetch_bytes(url, *, allowed_hosts, timeout, max_bytes, resolver=None):
    resolver = resolver or resolve_host_addresses
    safe_url = validate_remote_url(url, allowed_hosts, resolver)
    opener = build_opener(
        HTTPSHandler(context=ssl.create_default_context()),
        SafeRedirectHandler(allowed_hosts, resolver),
    )
    request = Request(
        safe_url,
        headers={
            "Accept": "application/json,image/avif,image/webp,image/png,image/jpeg,image/gif,*/*;q=0.1",
            "User-Agent": "codex-meme/0.1-alpha",
        },
        method="GET",
    )
    with opener.open(request, timeout=timeout) as response:
        validate_remote_url(response.geturl(), allowed_hosts, resolver)
        body = read_limited(response, max_bytes)
        content_type = str(response.headers.get("Content-Type") or "").split(";", 1)[0].strip().lower()
        return body, content_type


def image_signature_matches(data, extension):
    if extension in (".jpg", ".jpeg"):
        return data.startswith(b"\xff\xd8\xff")
    if extension == ".png":
        return data.startswith(b"\x89PNG\r\n\x1a\n")
    if extension == ".gif":
        return data.startswith((b"GIF87a", b"GIF89a"))
    if extension == ".webp":
        return len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP"
    return False


def atomic_write_json(path, value):
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_path = tempfile.mkstemp(prefix=destination.name + ".", suffix=".tmp", dir=destination.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary_path, destination)
    except Exception:
        try:
            os.unlink(temporary_path)
        except OSError:
            pass
        raise


def write_cached_asset(path, data):
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_path = tempfile.mkstemp(prefix="download-", suffix=".tmp", dir=destination.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
        os.replace(temporary_path, destination)
    except Exception:
        try:
            os.unlink(temporary_path)
        except OSError:
            pass
        raise


def cached_asset_is_valid(path, expected_hash, max_bytes):
    try:
        if not path.is_file() or path.stat().st_size > max_bytes:
            return False
        return hashlib.sha256(path.read_bytes()).hexdigest() == expected_hash
    except OSError:
        return False


def parse_catalog(data, maximum_assets):
    try:
        document = json.loads(data.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("invalid_manifest_json") from error
    items = document.get("assets") if isinstance(document, dict) else document
    if not isinstance(items, list):
        raise ValueError("invalid_manifest_shape")
    enabled_count = sum(1 for item in items if isinstance(item, dict) and item.get("enabled") is not False)
    if enabled_count < 1 or enabled_count > maximum_assets:
        raise ValueError("invalid_asset_count")
    return items


def resolve_cache_dir():
    runtime_root = Path(REMOTE_MANIFEST_PATH).resolve().parent
    cache_dir = Path(REMOTE_CACHE_DIR)
    if cache_dir.parent.resolve() != runtime_root:
        raise ValueError("unsafe_cache_directory")
    if cache_dir.exists() and cache_dir.is_symlink():
        raise ValueError("unsafe_cache_directory")
    cache_dir.mkdir(parents=True, exist_ok=True)
    resolved = cache_dir.resolve()
    if resolved.parent != runtime_root:
        raise ValueError("unsafe_cache_directory")
    return resolved


def build_cached_manifest(items, cfg, remote):
    allowed_hosts = remote["allowed_hosts"]
    allowed_extensions = {str(item).lower() for item in cfg.get("allowed_extensions", [])}
    maximum_bytes = remote["max_asset_bytes"]
    timeout = remote["timeout_seconds"]
    cache_dir = resolve_cache_dir()
    generated = []
    seen_ids = set()
    seen_urls = set()
    for item in items:
        if not isinstance(item, dict) or item.get("enabled") is False:
            continue
        asset_id = str(item.get("id") or "").strip()
        label = sanitize_label(item.get("label"))
        expected_hash = str(item.get("sha256") or "").strip().lower()
        if not ASSET_ID_PATTERN.fullmatch(asset_id) or not label or not SHA256_PATTERN.fullmatch(expected_hash):
            raise ValueError("invalid_asset_metadata")
        safe_url = validate_remote_url(item.get("url"), allowed_hosts)
        extension = os.path.splitext(urlsplit(safe_url).path)[1].lower()
        if extension not in allowed_extensions or extension not in IMAGE_CONTENT_TYPES:
            raise ValueError("invalid_asset_extension")
        if asset_id in seen_ids or safe_url in seen_urls:
            raise ValueError("duplicate_asset")
        cached_path = cache_dir / (expected_hash + extension)
        if not cached_asset_is_valid(cached_path, expected_hash, maximum_bytes):
            body, content_type = fetch_bytes(
                safe_url,
                allowed_hosts=allowed_hosts,
                timeout=timeout,
                max_bytes=maximum_bytes,
            )
            if content_type != IMAGE_CONTENT_TYPES[extension] or not image_signature_matches(body, extension):
                raise ValueError("invalid_asset_content")
            if hashlib.sha256(body).hexdigest() != expected_hash:
                raise ValueError("asset_hash_mismatch")
            write_cached_asset(cached_path, body)
        generated.append({
            "id": asset_id,
            "path": cached_path.resolve().as_posix(),
            "label": label,
            "enabled": True,
        })
        seen_ids.add(asset_id)
        seen_urls.add(safe_url)
    return generated


def save_attempt(state, now, error=None, success=False):
    updated = dict(state) if isinstance(state, dict) else {}
    updated["last_attempt"] = now
    if success:
        updated["last_success"] = now
        updated.pop("last_error", None)
    elif error:
        updated["last_error"] = error
    atomic_write_json(REMOTE_STATE_PATH, updated)


def source_fingerprint(remote):
    source = remote.get("manifest_url", "") + "\n" + "\n".join(remote.get("allowed_hosts", []))
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def bounded_timestamp(value, now):
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return 0.0
    if parsed < 0 or parsed != parsed:
        return 0.0
    return min(now, parsed)


def sync_remote_assets(force=False, now=None):
    now = time.time() if now is None else float(now)
    cfg = load_config()
    remote = cfg.get("remote", {})
    if remote.get("enabled") is not True:
        return {"status": "disabled", "asset_count": 0}
    if not remote.get("manifest_url") or not remote.get("allowed_hosts"):
        return {"status": "unconfigured", "asset_count": 0}

    state = load_json(REMOTE_STATE_PATH, {})
    if not isinstance(state, dict):
        state = {}
    current_source = source_fingerprint(remote)
    source_matches = state.get("source") == current_source
    if not source_matches:
        state = {}
    last_success = bounded_timestamp(state.get("last_success"), now)
    last_attempt = bounded_timestamp(state.get("last_attempt"), now)
    if not force and source_matches and os.path.isfile(REMOTE_MANIFEST_PATH):
        if last_success and now - last_success < remote["refresh_hours"] * 3600:
            return {"status": "fresh", "asset_count": 0}
        if last_attempt > last_success and now - last_attempt < remote["retry_minutes"] * 60:
            return {"status": "backoff", "asset_count": 0}

    try:
        manifest_body, manifest_type = fetch_bytes(
            remote["manifest_url"],
            allowed_hosts=remote["allowed_hosts"],
            timeout=remote["timeout_seconds"],
            max_bytes=remote["max_manifest_bytes"],
        )
        if manifest_type not in ("application/json", "text/plain", "application/octet-stream"):
            raise ValueError("invalid_manifest_content_type")
        items = parse_catalog(manifest_body, remote["max_assets"])
        generated = build_cached_manifest(items, cfg, remote)
        atomic_write_json(REMOTE_MANIFEST_PATH, generated)
        state["source"] = current_source
        save_attempt(state, now, success=True)
        return {"status": "updated", "asset_count": len(generated)}
    except Exception as error:
        try:
            state["source"] = current_source
            save_attempt(state, now, error=type(error).__name__)
        except Exception:
            pass
        return {"status": "failed", "asset_count": 0}


def main():
    sync_remote_assets(force="--force" in sys.argv[1:])
    sys.stdout.write("{}")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        try:
            sys.stdout.write("{}")
        except Exception:
            pass
