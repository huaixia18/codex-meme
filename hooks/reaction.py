#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Codex Meme v0.1-alpha UserPromptSubmit hook and shared helpers."""

import json
import os
import random
import re
import secrets
import sys
from datetime import datetime


def configure_utf8_stdio():
    """Codex hook pipes are UTF-8; Windows Python may otherwise use GBK."""
    for stream in (sys.stdin, sys.stdout):
        reconfigure = getattr(stream, "reconfigure", None)
        if not callable(reconfigure):
            continue
        try:
            reconfigure(encoding="utf-8")
        except Exception:
            pass


configure_utf8_stdio()


HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(HERE, "reaction.json")
MANIFEST_PATH = os.path.join(HERE, "manifest.json")
STATE_PATH = os.path.join(HERE, ".reaction_state.json")
LOG_PATH = os.path.join(HERE, "reaction.log")
PROTOCOL_VERSION = "codex-meme/0.1"
STATE_VERSION = 2
NO_HIT = -(10 ** 6)

DEFAULTS = {
    "enabled": True,
    "probability": 0.20,
    "cooldown_turns": 5,
    "warmup_turns": 2,
    "asset_roots": [],
    "allowed_extensions": [".png", ".jpg", ".jpeg", ".gif", ".webp"],
    "skip_keywords": [
        "自杀", "抑郁", "去世", "病危", "住院", "确诊", "癌",
        "事故", "报警", "遗嘱", "葬礼",
        "离婚", "分手", "裁员", "失业",
        "严肃", "认真回答", "别开玩笑", "正经点",
        "suicide", "depression", "died", "death", "terminal illness",
        "hospitalized", "diagnosed", "cancer", "funeral", "divorce",
        "breakup", "laid off", "unemployed", "answer seriously",
        "be serious", "no jokes",
    ],
    "skip_phrases": [
        "不要表情包", "别发表情包", "不要发表情包", "不要图片", "别发图片",
        "不要发图", "别发图", "纯文本", "只输出json", "仅输出json",
        "只返回json", "只给代码", "只输出代码", "只返回代码",
        "只给补丁", "只输出补丁", "只返回补丁", "不要markdown", "别用markdown",
        "no meme", "no memes", "don't send a meme", "do not send a meme",
        "don't send memes", "do not send memes", "no image", "no images",
        "don't send images", "do not send images", "plain text", "text only",
        "json only", "only json", "only valid json", "return only json",
        "output only json", "code only", "only code", "return only code",
        "output only code", "patch only", "only the patch", "return only the patch",
        "no markdown", "without markdown",
    ],
    "log": True,
    "max_sessions": 40,
}

FORCE_PATTERN_ZH = re.compile(
    r"^(?:请|麻烦)?(?:你)?(?:"
    r"(?:给我)?(?:发|来|甩)(?:一|1)?(?:张|个)?(?:表情包|梗图)(?:给我|看看|一下|吧|呗|呀)?"
    r"|给我(?:一|1)?(?:张|个)(?:表情包|梗图)(?:吧|呗)?"
    r"|只(?:给我)?发(?:一|1)?(?:张|个)?(?:表情包|梗图)"
    r"|不(?:给我)?(?:发|来|甩|整)(?:一|1)?(?:张|个)?(?:表情包|梗图)(?:吗|么)"
    r"|要不(?:你)?(?:给我)?(?:发|来|甩|整)(?:一|1)?(?:张|个)?(?:表情包|梗图)(?:吧|呗|呀|吗|么)?"
    r")$"
)

FORCE_PATTERN_EN = re.compile(
    r"^(?:"
    r"(?:please\s+)?(?:(?:can|could|would|will)\s+you\s+(?:please\s+)?)?"
    r"(?:send|show|give|drop)\s+(?:me\s+)?(?:a|one)\s+"
    r"(?:meme|meme image|reaction image|reaction meme)(?:\s+please)?"
    r"|(?:how|what)\s+about\s+(?:a|one)\s+(?:meme|meme image|reaction image|reaction meme)"
    r"|why\s+not\s+(?:send|show|give|drop)\s+(?:me\s+)?(?:a|one)\s+"
    r"(?:meme|meme image|reaction image|reaction meme)"
    r"|why\s+no\s+(?:meme|meme image|reaction image|reaction meme)"
    r"|(?:a\s+)?(?:meme|meme image|reaction image|reaction meme)\s+please"
    r")$",
    re.IGNORECASE,
)

FOLLOWUP_PATTERN_ZH = re.compile(
    r"^(?:(?:(?:这个|这张)(?:不行|不好|不喜欢)|不要(?:这个|这张)))?"
    r"(?:"
    r"再(?:来|整|发|甩)(?:一|1)?(?:张|个|点)?(?:别的|其他的|不一样的)?(?:看看|一下|吧|呗|呀)?"
    r"|(?:给我)?换(?:(?:一|1)?(?:张|个)(?:别的|其他的|不一样的)?|(?:别的|其他的|不一样的))(?:看看|一下|吧|呗|呀)?"
    r"|(?:来|整|发)(?:一|1)?(?:张|个)?(?:别的|其他的|不一样的)(?:看看|一下|吧|呗|呀)?"
    r"|(?:还|再)?有(?:(?:没有|没)(?:别的|其他的)?|(?:别的|其他的)(?:吗|么|没)?|(?:吗|么))"
    r"|别的呢"
    r"|下(?:一|1)张(?:表情包|梗图)?(?:吧|呗|呀)?"
    r"|下(?:一|1)个(?:表情包|梗图)(?:吧|呗|呀)?"
    r")$"
)

FOLLOWUP_PATTERN_EN = re.compile(
    r"^(?:"
    r"another(?:\s+(?:one|meme|reaction image))?"
    r"|one\s+more(?:\s+(?:one|meme|reaction image))?"
    r"|(?:send|show|give|drop)\s+(?:me\s+)?another(?:\s+(?:one|meme|reaction image))?"
    r"|(?:a\s+)?different\s+(?:one|meme|reaction image)"
    r"|(?:something|anything)\s+else"
    r"|(?:do\s+you\s+have|have\s+you\s+got|got)\s+another(?:\s+(?:one|meme|reaction image))?"
    r"|next\s+(?:one|meme|reaction image)"
    r")$",
    re.IGNORECASE,
)

DYNAMIC_ASSET_PATTERN_ZH = (
    r"(?:"
    r"动态(?:的)?(?:表情包|梗图|图片)?"
    r"|会动的(?:表情包|梗图|图片)?"
    r"|动图"
    r"|gif(?:格式)?(?:的)?(?:表情包|梗图|图)?"
    r")"
)

DYNAMIC_REQUEST_PATTERN_ZH = re.compile(
    r"^(?:请|麻烦)?(?:你)?(?:"
    r"(?:能|可以)?(?:给我)?(?:再)?(?:发|来|甩|整|换)(?:一|1)?(?:张|个|点)?"
    + DYNAMIC_ASSET_PATTERN_ZH
    + r"(?:给我|看看|一下|吧|呗|呀|吗|么)?"
    r"|(?:给我(?:一|1)?(?:张|个)?|(?:一|1)(?:张|个))"
    + DYNAMIC_ASSET_PATTERN_ZH
    + r"(?:吧|呗|呀)?"
    r"|(?:有|还有|有没有|还有没有)"
    + DYNAMIC_ASSET_PATTERN_ZH
    + r"(?:吗|么)?"
    r"|"
    + DYNAMIC_ASSET_PATTERN_ZH
    + r"(?:有吗|有没有|还有吗|还有没有|呢)"
    r"|不(?:给我)?(?:发|来|甩|整|换)(?:一|1)?(?:张|个|点)?"
    + DYNAMIC_ASSET_PATTERN_ZH
    + r"(?:吗|么)"
    r"|要不(?:你)?(?:给我)?(?:发|来|甩|整|换)(?:一|1)?(?:张|个|点)?"
    + DYNAMIC_ASSET_PATTERN_ZH
    + r"(?:吧|呗|呀|吗|么)?"
    r")$",
    re.IGNORECASE,
)

DYNAMIC_REQUEST_PATTERN_EN = re.compile(
    r"^(?:"
    r"(?:please\s+)?(?:(?:can|could|would|will)\s+you\s+(?:please\s+)?)?"
    r"(?:send|show|give|drop|swap|replace)\s+(?:me\s+)?(?:another|a|an|one)?\s*"
    r"(?:gif|animated gif|animated meme|animated reaction|moving meme|moving image)"
    r"|(?:do\s+you\s+have|have\s+you\s+got|got\s+any|is\s+there\s+(?:a|an)|are\s+there\s+any)\s+"
    r"(?:gif|gifs|animated gif|animated gifs|animated meme|animated memes|animated reaction|animated reactions)"
    r"|(?:how|what)\s+about\s+(?:a|an|one)\s+"
    r"(?:gif|animated gif|animated meme|animated reaction|moving meme|moving image)"
    r"|why\s+not\s+(?:send|show|give|drop)\s+(?:me\s+)?(?:a|an|one)\s+"
    r"(?:gif|animated gif|animated meme|animated reaction|moving meme|moving image)"
    r")$",
    re.IGNORECASE,
)


def quiet_exit():
    sys.exit(0)


def load_json(path, fallback):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return fallback


def _bounded_float(value, default, minimum, maximum):
    try:
        return min(maximum, max(minimum, float(value)))
    except (TypeError, ValueError):
        return default


def _bounded_int(value, default, minimum=0):
    try:
        return max(minimum, int(value))
    except (TypeError, ValueError):
        return default


def load_config():
    cfg = dict(DEFAULTS)
    loaded = load_json(CONFIG_PATH, {})
    if isinstance(loaded, dict):
        cfg.update(loaded)
    cfg["enabled"] = bool(cfg.get("enabled", True))
    cfg["probability"] = _bounded_float(cfg.get("probability"), DEFAULTS["probability"], 0.0, 1.0)
    cfg["cooldown_turns"] = _bounded_int(cfg.get("cooldown_turns"), DEFAULTS["cooldown_turns"])
    cfg["warmup_turns"] = _bounded_int(cfg.get("warmup_turns"), DEFAULTS["warmup_turns"])
    cfg["max_sessions"] = _bounded_int(cfg.get("max_sessions"), DEFAULTS["max_sessions"], 1)
    for key in ("asset_roots", "allowed_extensions", "skip_keywords", "skip_phrases"):
        if not isinstance(cfg.get(key), list):
            cfg[key] = list(DEFAULTS[key])
    return cfg


def default_slot():
    return {
        "turn": 0,
        "last_hit": NO_HIT,
        "protocol_version": None,
        "pending_offer": None,
        "play_chain": False,
    }


def normalize_slot(value):
    slot = default_slot()
    if isinstance(value, dict):
        slot["turn"] = _bounded_int(value.get("turn"), 0)
        try:
            slot["last_hit"] = int(value.get("last_hit", NO_HIT))
        except (TypeError, ValueError):
            slot["last_hit"] = NO_HIT
        protocol_version = value.get("protocol_version")
        slot["protocol_version"] = protocol_version if isinstance(protocol_version, str) else None
        pending = value.get("pending_offer")
        slot["pending_offer"] = pending if isinstance(pending, dict) else None
        slot["play_chain"] = value.get("play_chain") is True
    return slot


def load_state():
    raw = load_json(STATE_PATH, {})
    sessions = {}
    if isinstance(raw, dict) and raw.get("version") == STATE_VERSION and isinstance(raw.get("sessions"), dict):
        source = raw["sessions"]
    elif isinstance(raw, dict):
        source = raw
    else:
        source = {}
    for session_id, value in source.items():
        if isinstance(session_id, str) and isinstance(value, dict):
            sessions[session_id] = normalize_slot(value)
    return {"version": STATE_VERSION, "sessions": sessions}


def get_session(state, session_id):
    sessions = state.setdefault("sessions", {})
    existing = sessions.pop(session_id, None)
    slot = normalize_slot(existing)
    sessions[session_id] = slot
    return slot


def save_state(state, cfg=None):
    cfg = cfg or load_config()
    sessions = state.get("sessions") if isinstance(state, dict) else None
    if not isinstance(sessions, dict):
        sessions = {}
    limit = max(1, int(cfg.get("max_sessions", 40)))
    if len(sessions) > limit:
        sessions = dict(list(sessions.items())[-limit:])
    payload = {"version": STATE_VERSION, "sessions": sessions}
    try:
        temp_path = STATE_PATH + ".tmp"
        with open(temp_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
        os.replace(temp_path, STATE_PATH)
    except Exception:
        pass


def log_event(cfg, event_name, session_id=None, turn_id=None, turn=None, **extra):
    if not cfg.get("log"):
        return
    record = {
        "time": datetime.now().astimezone().isoformat(timespec="seconds"),
        "event": event_name,
    }
    if session_id:
        record["session_id"] = session_id
    if turn_id:
        record["turn_id"] = turn_id
    if turn is not None:
        record["turn"] = turn
    for key, value in extra.items():
        if value is not None:
            record[key] = value
    try:
        mode = "a"
        if os.path.exists(LOG_PATH) and os.path.getsize(LOG_PATH) > 0:
            with open(LOG_PATH, "r", encoding="utf-8", errors="ignore") as handle:
                first = handle.read(256).lstrip()
            if first and not first.startswith("{"):
                mode = "w"
        with open(LOG_PATH, mode, encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
    except Exception:
        pass


def normalized_absolute_path(path):
    return os.path.abspath(path).replace("\\", "/")


def path_is_allowed(path, cfg):
    try:
        full = os.path.normcase(os.path.abspath(path))
        allowed_root = False
        for root in cfg.get("asset_roots", []):
            root_text = str(root).strip()
            if not root_text:
                continue
            root_full = os.path.normcase(os.path.abspath(root_text))
            try:
                if os.path.commonpath([full, root_full]) == root_full:
                    allowed_root = True
                    break
            except ValueError:
                continue
        if not allowed_root:
            return False
        allowed_extensions = {str(ext).lower() for ext in cfg.get("allowed_extensions", [])}
        if os.path.splitext(full)[1].lower() not in allowed_extensions:
            return False
        return os.path.isfile(full)
    except Exception:
        return False


def load_assets(cfg=None):
    cfg = cfg or load_config()
    raw = load_json(MANIFEST_PATH, [])
    if not isinstance(raw, list):
        return []
    assets = []
    seen_ids = set()
    seen_paths = set()
    for item in raw:
        if not isinstance(item, dict) or item.get("enabled") is False:
            continue
        asset_id = str(item.get("id", "")).strip()
        label = str(item.get("label", "")).strip()
        raw_path = str(item.get("path", "")).strip()
        if not asset_id or not label or not raw_path:
            continue
        path = normalized_absolute_path(raw_path)
        if asset_id in seen_ids or path in seen_paths or not path_is_allowed(path, cfg):
            continue
        assets.append({"id": asset_id, "label": label, "path": path})
        seen_ids.add(asset_id)
        seen_paths.add(path)
    return assets


def parse_stdin_json():
    try:
        raw = sys.stdin.read()
    except Exception:
        return None
    if not raw or not raw.strip():
        return {}
    try:
        value = json.loads(raw)
        return value if isinstance(value, dict) else None
    except Exception:
        return None


def compact_prompt(prompt):
    compact = re.sub(r"\s+", "", prompt or "")
    return compact.strip("。！？!?~～.,，、；;：:")


def word_prompt(prompt):
    text = str(prompt or "").lower().replace("’", "'")
    text = re.sub(r"[。！？!?~～.,，、；;：:\"()\[\]{}]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def skip_reason(prompt, cfg):
    lowered = str(prompt or "").lower().replace("’", "'")
    compact = compact_prompt(lowered)
    for keyword in cfg.get("skip_keywords", []):
        if str(keyword).lower() in lowered:
            return "keyword:" + str(keyword)
    for phrase in cfg.get("skip_phrases", []):
        phrase_compact = compact_prompt(str(phrase).lower())
        if phrase_compact and phrase_compact in compact:
            return "phrase:" + str(phrase)
    return None


def is_forced_request(prompt):
    return bool(
        FORCE_PATTERN_ZH.fullmatch(compact_prompt(prompt))
        or FORCE_PATTERN_EN.fullmatch(word_prompt(prompt))
    )


def is_followup_request(prompt):
    return bool(
        FOLLOWUP_PATTERN_ZH.fullmatch(compact_prompt(prompt))
        or FOLLOWUP_PATTERN_EN.fullmatch(word_prompt(prompt))
    )


def requested_asset_kind(prompt):
    return "gif" if (
        DYNAMIC_REQUEST_PATTERN_ZH.fullmatch(compact_prompt(prompt))
        or DYNAMIC_REQUEST_PATTERN_EN.fullmatch(word_prompt(prompt))
    ) else None


def filter_assets_by_kind(assets, asset_kind):
    if asset_kind == "gif":
        return [
            asset
            for asset in assets
            if os.path.splitext(str(asset.get("path") or ""))[1].lower() == ".gif"
        ]
    return assets


def build_offer(kind, turn_id, assets, asset_kind=None):
    nonce = secrets.token_hex(3)
    chosen = secrets.SystemRandom().sample(assets, 3)
    parts = []
    for asset in chosen:
        label = asset["label"].replace("|", "/").replace(";", "，")
        parts.append("%s=%s|%s" % (asset["id"], label, asset["path"]))
    signal = "[rx:%s] candidates: %s" % (nonce, " ; ".join(parts))
    pending = {
        "turn_id": turn_id or "",
        "nonce": nonce,
        "kind": kind,
        "asset_kind": asset_kind,
        "candidate_ids": [asset["id"] for asset in chosen],
        "candidate_paths": [asset["path"] for asset in chosen],
    }
    return nonce, chosen, signal, pending


def output_additional_context(event_name, text):
    payload = {
        "hookSpecificOutput": {
            "hookEventName": event_name,
            "additionalContext": text,
        }
    }
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))


def main():
    cfg = load_config()
    if not cfg.get("enabled"):
        quiet_exit()

    event = parse_stdin_json()
    if event is None:
        quiet_exit()

    session_id = str(event.get("session_id") or "default")
    turn_id = str(event.get("turn_id") or "")
    prompt = str(event.get("prompt") or "")
    state = load_state()
    slot = get_session(state, session_id)
    slot["turn"] += 1
    slot["pending_offer"] = None
    turn = slot["turn"]

    reason = skip_reason(prompt, cfg)
    if reason:
        slot["play_chain"] = False
        save_state(state, cfg)
        log_event(cfg, "SKIP", session_id, turn_id, turn, reason=reason)
        quiet_exit()

    asset_kind = requested_asset_kind(prompt)
    dynamic_forced = asset_kind == "gif"
    direct_forced = is_forced_request(prompt) or dynamic_forced
    followup_forced = bool(slot.get("play_chain")) and (
        is_followup_request(prompt) or dynamic_forced
    )
    forced = direct_forced or followup_forced
    force_source = "followup" if followup_forced else ("direct" if direct_forced else None)
    slot["play_chain"] = False

    if not forced and turn <= int(cfg.get("warmup_turns", 2)):
        save_state(state, cfg)
        log_event(cfg, "MISS", session_id, turn_id, turn, reason="warmup")
        quiet_exit()

    last_hit = int(slot.get("last_hit", NO_HIT))
    if not forced and (turn - last_hit) <= int(cfg.get("cooldown_turns", 5)):
        save_state(state, cfg)
        log_event(cfg, "COOL", session_id, turn_id, turn, since=turn - last_hit)
        quiet_exit()

    if not forced and random.random() >= float(cfg.get("probability", 0.20)):
        save_state(state, cfg)
        log_event(cfg, "MISS", session_id, turn_id, turn, reason="probability")
        quiet_exit()

    assets = filter_assets_by_kind(load_assets(cfg), asset_kind)
    if len(assets) < 3:
        save_state(state, cfg)
        reason = "fewer_than_3_%s_assets" % asset_kind if asset_kind else "fewer_than_3_valid_assets"
        log_event(cfg, "ERROR", session_id, turn_id, turn, reason=reason)
        quiet_exit()

    kind = "FORCED" if forced else "OFFER"
    nonce, chosen, signal, pending = build_offer(kind, turn_id, assets, asset_kind)
    slot["last_hit"] = turn
    slot["pending_offer"] = pending
    save_state(state, cfg)
    log_event(
        cfg,
        kind,
        session_id,
        turn_id,
        turn,
        nonce=nonce,
        candidate_ids=[asset["id"] for asset in chosen],
        trigger=force_source,
        asset_kind=asset_kind,
    )
    output_additional_context("UserPromptSubmit", signal)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        quiet_exit()
