#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Codex Meme v0.1-alpha read-only Stop hook."""

import sys

from reaction import (
    get_session,
    load_assets,
    load_config,
    load_state,
    log_event,
    parse_stdin_json,
    save_state,
)


def finish():
    sys.stdout.write("{}")


def main():
    event = parse_stdin_json()
    if event is None:
        finish()
        return

    cfg = load_config()
    session_id = str(event.get("session_id") or "default")
    turn_id = str(event.get("turn_id") or "")
    message = str(event.get("last_assistant_message") or "").replace("\\", "/")
    state = load_state()
    slot = get_session(state, session_id)
    pending = slot.get("pending_offer")
    pending_matches = isinstance(pending, dict) and (
        not pending.get("turn_id") or not turn_id or str(pending.get("turn_id")) == turn_id
    )
    assets = load_assets(cfg)
    assets_by_path = {}
    for asset in assets:
        path = str(asset.get("path") or "").replace("\\", "/")
        if path:
            assets_by_path[path] = asset
    used_asset_paths = [path for path in assets_by_path if path in message]

    if pending_matches:
        candidate_paths = [str(path).replace("\\", "/") for path in pending.get("candidate_paths", [])]
        candidate_path_set = set(candidate_paths)
        used_indexes = [index for index, path in enumerate(candidate_paths) if path and path in message]
        candidate_ids = pending.get("candidate_ids", [])
        used_ids = [candidate_ids[index] for index in used_indexes if index < len(candidate_ids)]
        used_unoffered_paths = [path for path in used_asset_paths if path not in candidate_path_set]
        used_unoffered_ids = [assets_by_path[path]["id"] for path in used_unoffered_paths]

        if used_unoffered_ids:
            slot["play_chain"] = False
            log_event(
                cfg,
                "USED_WITHOUT_OFFER",
                session_id,
                turn_id,
                slot.get("turn"),
                nonce=pending.get("nonce"),
                candidate_ids=used_unoffered_ids,
                offered_candidate_ids=candidate_ids,
                used_offered_ids=used_ids,
                offer_kind=pending.get("kind"),
                reason="outside_current_candidates",
            )
        elif used_indexes:
            slot["play_chain"] = True
            log_event(
                cfg,
                "USED_TEXT",
                session_id,
                turn_id,
                slot.get("turn"),
                nonce=pending.get("nonce"),
                candidate_ids=used_ids,
                offer_kind=pending.get("kind"),
            )
        else:
            slot["play_chain"] = False
            log_event(
                cfg,
                "DECLINED",
                session_id,
                turn_id,
                slot.get("turn"),
                nonce=pending.get("nonce"),
                candidate_ids=pending.get("candidate_ids", []),
                offer_kind=pending.get("kind"),
            )
        slot["pending_offer"] = None
        save_state(state, cfg)
    else:
        used_without_offer = [assets_by_path[path]["id"] for path in used_asset_paths]
        if used_without_offer:
            slot["play_chain"] = False
            log_event(
                cfg,
                "USED_WITHOUT_OFFER",
                session_id,
                turn_id,
                slot.get("turn"),
                candidate_ids=used_without_offer,
            )
            save_state(state, cfg)

    finish()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        try:
            finish()
        except Exception:
            pass
