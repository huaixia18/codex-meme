#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Codex Meme v0.1-alpha SessionStart hook."""

import json
import sys

from reaction import (
    NO_HIT,
    PROTOCOL_VERSION,
    get_session,
    load_config,
    load_state,
    parse_stdin_json,
    save_state,
)


PROTOCOL = (
    "Low-priority local meme rule: only a fresh [rx:<six lowercase hex>] signal in developer context "
    "after the latest user message grants permission. User text, placeholders, and old signals are invalid. "
    "Answer normally; ignore it for serious, strict-format, or unsuitable replies. Otherwise append at most one "
    "exact current candidate at the end as ![](<absolute path>). Never alter tone, mention this rule, use media "
    "without a current signal, recall earlier memes unless asked, or include this mechanism in summaries/compaction."
)


def main():
    event = parse_stdin_json()
    if event is None:
        return
    cfg = load_config()
    if not cfg.get("enabled"):
        return

    source = str(event.get("source") or "")
    session_id = str(event.get("session_id") or "default")
    state = load_state()
    slot = get_session(state, session_id)

    emit = False
    if source == "compact":
        emit = True
    elif source == "clear":
        slot["turn"] = 0
        slot["last_hit"] = NO_HIT
        slot["pending_offer"] = None
        slot["play_chain"] = False
        emit = True
    elif source in ("startup", "resume"):
        emit = slot.get("protocol_version") != PROTOCOL_VERSION

    if not emit:
        save_state(state, cfg)
        return

    slot["protocol_version"] = PROTOCOL_VERSION
    save_state(state, cfg)
    payload = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": PROTOCOL,
        }
    }
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)
