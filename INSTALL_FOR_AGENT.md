# Codex Meme — Agent Installation Contract

> 此文件面向执行安装的编码 Agent。只有在用户明确要求安装 Codex Meme 时才能执行。不得创建或修改任何 `AGENTS.md`。

This is the normative installation specification. Follow it exactly when the user explicitly asks to install Codex Meme.

## Non-negotiable invariants

1. Install only at the user level. Do not add project-local hooks.
2. Never create, read for configuration, or modify any global or project `AGENTS.md`.
3. Preserve every unrelated hook and configuration entry.
4. Back up affected files before the first write and before every update.
5. Never scan a directory the user did not explicitly select.
6. Never copy, upload, publish, or modify the user's external meme assets.
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
reaction.json
manifest.json
```

Runtime state and logs will later appear there as `.reaction_state.json` and `reaction.log`.

## 1. Inspect without changing state

1. Resolve the repository root containing this file.
2. Confirm `hooks/reaction.py`, `hooks/session_start.py`, `hooks/stop.py`, `templates/reaction.json`, and `templates/hooks.fragment.json` exist.
3. Confirm the repository contains no `AGENTS.md`.
4. Detect Python in this order:
   - `py -3 --version`
   - `python --version`
5. Require Python 3.10 or newer. Record the working command as `PYTHON_COMMAND` (`py -3` or `python`).
6. Run the repository tests before installation, replacing `py -3` with the detected command when needed:

```powershell
py -3 -m py_compile hooks\reaction.py hooks\session_start.py hooks\stop.py
py -3 -m unittest discover -s tests -v
```

7. Read the existing hooks file if present. Treat missing or empty content as `{ "hooks": {} }`. Stop and report malformed JSON rather than overwriting it.

## 2. Obtain and curate assets

If the user did not already provide an asset directory, ask for one absolute local directory.

1. Enumerate only that directory. Default to non-recursive enumeration; recurse only with explicit user permission.
2. Accept `.png`, `.jpg`, `.jpeg`, `.gif`, and `.webp` files.
3. Require at least 3 selected files. If fewer exist, stop before modifying Codex configuration.
4. Use descriptive filename stems as labels when they are meaningful.
5. If filenames are opaque, inspect images in batches of at most 30, propose concise labels, and ask the user to confirm the manifest summary before writing it.
6. Assign stable unique IDs, preserve absolute paths, normalize stored paths to forward slashes, and set `enabled: true`.
7. Add short tags only when useful. Tags are metadata and are not required by the runtime selector.
8. Inform the user when fewer than 3 enabled GIFs exist: normal reactions will work, but directed GIF requests will not.

The resulting `manifest.json` is an explicit whitelist. The runtime must never replace it with directory scanning.

## 3. Back up

Create a timestamped backup directory under the backup root.

- If `<CODEX_HOME>\hooks.json` exists, copy it to the backup directory.
- If the install directory already exists, copy the complete install directory into the backup directory.
- Record every backup path for the completion report.

Do not continue if backup creation fails.

## 4. Stage the isolated installation

1. Create the install directory if needed.
2. Copy the three Python files from `hooks/` into the install directory.
3. Copy `templates/reaction.json` to `reaction.json`.
4. Set `asset_roots` in `reaction.json` to the user-selected absolute directory. Preserve the published defaults unless the user explicitly requests different values.
5. Write the user-confirmed manifest to `manifest.json`.
6. On update, preserve existing user `reaction.json` and `manifest.json` unless a schema change or explicit user request requires replacement. Update the three Python files normally.

## 5. Merge the hook definitions

1. Load `templates/hooks.fragment.json` as JSON.
2. Replace `{{PYTHON_COMMAND}}` with the detected Python command.
3. Replace `{{INSTALL_DIR}}` with the absolute install directory normalized to forward slashes.
4. In the existing hooks object, remove only handlers whose normalized command contains `/codex-meme/`:
   - Remove the matching handler from its matcher group.
   - Remove a matcher group only when its `hooks` array becomes empty.
   - Remove an event only when its event array becomes empty.
5. Append the three matcher groups from the rendered fragment.
6. Preserve all unknown top-level fields, events, matcher groups, and handlers exactly by value.
7. Verify there is exactly one Codex Meme handler under each of `SessionStart`, `UserPromptSubmit`, and `Stop`.
8. Serialize valid UTF-8 JSON with readable indentation and write it atomically.

Never alter unrelated handlers, including `SubagentStart` handlers.

## 6. Verify the installed copy

1. Compile all three installed Python files.
2. Parse installed `reaction.json`, `manifest.json`, and the merged hooks file as JSON.
3. Confirm every enabled manifest path exists, is inside an allowed root, has an allowed extension, and has a unique ID and path.
4. Confirm at least 3 valid assets load through `reaction.load_assets()`.
5. Feed a temporary `SessionStart` startup event to the installed `session_start.py` and verify it emits valid JSON with `hookEventName: SessionStart`.
6. Feed a direct request such as `send me a meme` to `reaction.py` using a disposable session ID and verify it emits a `UserPromptSubmit` candidate signal.
7. Remove the disposable `install-test` and `install-direct` sessions from `.reaction_state.json`, or remove the state file if it contains no real sessions.
8. Confirm no repository file, global/project `AGENTS.md`, external asset, or unrelated hook was changed.

## 7. Hand control back to the user

Do not attempt to trust the hook automatically. Tell the user to review and trust the three new definitions in the Codex Hook interface or `/hooks`.

Report:

- Install directory.
- Hooks file changed.
- Asset root and enabled asset count.
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
