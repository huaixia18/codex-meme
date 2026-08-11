# Codex Meme — Agent Installation Contract

> 此文件面向执行安装的编码 Agent。只有在用户明确要求安装 Codex Meme 时才能执行。不得创建或修改任何 `AGENTS.md`。

This is the normative installation specification. Follow it exactly when the user explicitly asks to install Codex Meme.

## Non-negotiable invariants

1. Install only at the user level. Do not add project-local hooks.
2. Never create, read for configuration, or modify any global or project `AGENTS.md`.
3. Preserve every unrelated hook and configuration entry.
4. Back up affected files before the first write and before every update.
5. Never scan a directory the user did not explicitly select.
6. Never download, clone, or enable remote sync unless the user explicitly chooses the source and approves its destination or exact HTTPS host allowlist. Never upload, publish, or modify external meme assets.
7. Never fabricate a Codex hook trust hash. The user must review and trust hooks through Codex.
8. Use JSON parsing and serialization. Do not merge `hooks.json` with textual search-and-replace.

## Target layout

- Codex home: use the active Codex user home if discoverable; otherwise use `%USERPROFILE%\.codex`.
- Hooks file: `<CODEX_HOME>\hooks.json`.
- Install directory: `<CODEX_HOME>\hooks\codex-meme`.
- Backup root: `<CODEX_HOME>\backups\codex-meme\<YYYYMMDD-HHMMSS>`.

The install directory must contain only:

```text
reaction.py
session_start.py
stop.py
sync_remote.py
reaction.json
manifest.json
```

Runtime state and logs may later appear there as `.reaction_state.json` and `reaction.log`. Remote mode also creates `.remote_manifest.json`, `.remote_state.json`, and `remote-cache/` inside this isolated install directory.

## 1. Inspect without changing state

1. Resolve the repository root containing this file.
2. Confirm `hooks/reaction.py`, `hooks/session_start.py`, `hooks/stop.py`, `hooks/sync_remote.py`, `templates/reaction.json`, and `templates/hooks.fragment.json` exist.
3. Confirm the repository contains no `AGENTS.md`.
4. Detect Python in this order:
   - `py -3 --version`
   - `python --version`
5. Require Python 3.10 or newer. Record the working command as `PYTHON_COMMAND` (`py -3` or `python`).
6. Run the repository tests before installation, replacing `py -3` with the detected command when needed:

```powershell
py -3 -m py_compile hooks\reaction.py hooks\session_start.py hooks\stop.py hooks\sync_remote.py
py -3 -m unittest discover -s tests -v
```

7. Read the existing hooks file if present. Treat missing or empty content as `{ "hooks": {} }`. Stop and report malformed JSON rather than overwriting it.

## 2. Obtain and curate assets

If the user did not already provide an asset source, offer these three choices:

- Use an existing absolute local directory.
- Use an explicit HTTPS remote manifest and local verified cache.
- With explicit user approval, obtain assets from the independent third-party project [ChineseBQB](https://github.com/zhaoolee/ChineseBQB).

For the ChineseBQB option, explain that its repository and images are not covered by the Codex Meme license, ask the user to approve an absolute destination outside the Codex Meme install directory, and only then clone or download from the canonical URL `https://github.com/zhaoolee/ChineseBQB`. Treat the resulting directory as an external source from which the user may select assets, not as a collection that should be added to the manifest in full. Never add the whole repository by default. Because its images may be nested, ask separately for permission before recursive enumeration. Do not silently fall back to another source, and do not perform any network request if the user selects an existing local directory.

1. Enumerate only that directory. Default to non-recursive enumeration; recurse only with explicit user permission.
2. Ask the user to select or confirm the exact files to include. Never write every file from a downloaded collection to `manifest.json` by default.
3. Accept `.png`, `.jpg`, `.jpeg`, `.gif`, and `.webp` files.
4. For local-only mode, require at least 3 selected files. For mixed local/remote mode, verify the combined count later. If the intended mode cannot provide 3 valid assets, stop before modifying Codex configuration.
5. Use descriptive filename stems as labels when they are meaningful.
6. If filenames are opaque, inspect images in batches of at most 30, propose concise labels, and ask the user to confirm the manifest summary before writing it.
7. Normalize each label to one line by collapsing whitespace and removing control characters. Labels must contain 1 to 80 characters after normalization.
8. Assign stable unique IDs matching `[A-Za-z0-9_-]{1,64}`. Do not silently rewrite an invalid ID into a different value.
9. Preserve absolute paths, normalize stored paths to forward slashes, and set `enabled: true`.
10. Add short tags only when useful. Tags are metadata and are not required by the runtime selector.
11. Inform the user when fewer than 3 enabled GIFs exist: normal reactions will work, but directed GIF requests will not.

The resulting `manifest.json` is an explicit whitelist. The runtime must never replace it with directory scanning.

### Remote manifest mode

Use this mode only when the user explicitly supplies or approves the manifest URL and exact hostnames.

1. Require an `https://` manifest URL and a non-empty exact `allowed_hosts` list. Do not add wildcard hosts, IP literals, localhost, or private-network destinations.
2. Explain that enabling remote mode sends ordinary HTTPS request metadata, including IP address and User-Agent, to the approved hosts.
3. Fetch and inspect only the approved manifest. It may be a JSON array or `{ "version": 1, "assets": [...] }`.
4. Every enabled item must contain a unique valid `id`, HTTPS `url`, lowercase 64-character `sha256`, non-empty `label`, and `enabled`. Require at least 3 enabled assets in total after local and remote sources are combined.
5. Include every manifest host, image host, and legitimate redirect host in `allowed_hosts`; use exact lower-case hostnames only. Do not silently broaden the list after a validation failure.
6. Keep the published response-size, timeout, refresh, and retry limits unless the user explicitly asks to tighten them. Do not raise the hard runtime bounds.
7. Set `remote.enabled`, `remote.manifest_url`, and `remote.allowed_hosts` in `reaction.json`. Use an empty local `manifest.json` when the user selects remote-only mode.
8. Run the installed `sync_remote.py --force` once. Stop and report the generic failure status from `.remote_state.json` if no valid cache manifest is produced; never bypass URL, type, size, or SHA-256 validation.
9. Do not write remote URLs into the local candidate manifest yourself. Only `sync_remote.py` may produce `.remote_manifest.json`, whose entries point to verified files under `remote-cache/`.

## 3. Back up

Create a timestamped backup directory under the backup root.

- If `<CODEX_HOME>\hooks.json` exists, copy it to the backup directory.
- If the install directory already exists, copy the complete install directory into the backup directory.
- Record every backup path for the completion report.

Do not continue if backup creation fails.

## 4. Stage the isolated installation

1. Create the install directory if needed.
2. Copy the four Python files from `hooks/` into the install directory.
3. Copy `templates/reaction.json` to `reaction.json`.
4. For local mode, set `asset_roots` in `reaction.json` to the user-selected absolute directory. For remote mode, set only the approved `remote` fields. Preserve all other published defaults unless the user explicitly requests different values.
5. Write the user-confirmed local manifest to `manifest.json`, or `[]` for remote-only mode.
6. On update, preserve existing user `reaction.json` and `manifest.json` unless a schema change or explicit user request requires replacement. Update the four Python files normally.

## 5. Merge the hook definitions

1. Load `templates/hooks.fragment.json` as JSON.
2. Replace `{{PYTHON_COMMAND}}` with the detected Python command.
3. Replace `{{INSTALL_DIR}}` with the absolute install directory normalized to forward slashes.
4. In the existing hooks object, remove only handlers whose normalized command contains `/codex-meme/`:
   - Remove the matching handler from its matcher group.
   - Remove a matcher group only when its `hooks` array becomes empty.
   - Remove an event only when its event array becomes empty.
5. Append the three matcher groups from the rendered fragment. The SessionStart group contains two Codex Meme handlers; the other groups contain one each.
6. Preserve all unknown top-level fields, events, matcher groups, and handlers exactly by value.
7. Verify there are exactly two Codex Meme handlers under `SessionStart` and exactly one under each of `UserPromptSubmit` and `Stop`.
8. Serialize valid UTF-8 JSON with readable indentation and write it atomically.

Never alter unrelated handlers, including `SubagentStart` handlers.

## 6. Verify the installed copy

1. Compile all four installed Python files.
2. Parse installed `reaction.json`, `manifest.json`, and the merged hooks file as JSON.
3. Confirm every enabled local manifest path exists, is inside an allowed root, has an allowed extension, and has a unique ID and path. Confirm IDs match `[A-Za-z0-9_-]{1,64}` and normalized labels contain 1 to 80 characters.
4. If remote mode is enabled, run `sync_remote.py --force`, parse `.remote_manifest.json` and `.remote_state.json`, and confirm every generated path resolves inside `remote-cache/`. Do not print or upload image data.
5. Confirm at least 3 valid combined assets load through `reaction.load_assets()`.
6. Feed a temporary `SessionStart` startup event to the installed `session_start.py` and verify it emits valid JSON with `hookEventName: SessionStart`.
7. Feed a direct request such as `send me a meme` to `reaction.py` using a disposable session ID and verify it emits a `UserPromptSubmit` candidate signal.
8. Remove the disposable `install-test` and `install-direct` sessions from `.reaction_state.json`, or remove the state file if it contains no real sessions.
9. Confirm no repository file, global/project `AGENTS.md`, external asset, or unrelated hook was changed.

## 7. Hand control back to the user

Do not attempt to trust the hook automatically. Tell the user to review and trust the four new definitions in the Codex Hook interface or `/hooks`.

Report:

- Install directory.
- Hooks file changed.
- Local asset roots and enabled local asset count.
- Remote manifest URL, exact allowed hosts, cache path, last sync result, and remote asset count when enabled.
- GIF count.
- Effective probability, warmup, and cooldown.
- Test results.
- Backup paths.
- Exact rollback document: `UNINSTALL_FOR_AGENT.md`.

## Failure handling

If any write or validation step fails:

1. Restore `hooks.json` from the timestamped backup.
2. Restore the previous install directory when this was an update; otherwise remove only the newly created install directory after verifying its resolved path is exactly the intended child of `<CODEX_HOME>\hooks`.
3. Do not touch external assets.
4. Report the failure and restored paths.
