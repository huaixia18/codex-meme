# Codex Meme — Agent Uninstall Contract

> 只有在用户明确要求卸载 Codex Meme 时才能执行。不得创建或修改任何 `AGENTS.md`。

Follow this specification only after an explicit uninstall request.

## Invariants

1. Preserve every unrelated Hook and configuration field.
2. Do not delete or modify external meme assets.
3. Do not create, read for configuration, or modify any `AGENTS.md`.
4. Back up before writing or deleting.
5. Use resolved, explicit paths. Never recursively delete a broad or unresolved path.

## Procedure

1. Resolve the active Codex user home and the exact install directory `<CODEX_HOME>\hooks\codex-meme`.
2. Verify the install directory resolves inside `<CODEX_HOME>\hooks` and its final directory name is exactly `codex-meme`.
3. Create `<CODEX_HOME>\backups\codex-meme\<YYYYMMDD-HHMMSS>-uninstall`.
4. Back up `hooks.json` and the complete install directory. Stop if backup fails.
5. Parse `hooks.json` as JSON. Stop on malformed JSON.
6. For every event and matcher group, remove only handlers whose normalized command contains `/codex-meme/`.
7. Remove a matcher group only if its `hooks` array becomes empty; remove an event only if its event array becomes empty. Preserve all other values.
8. Write the hooks file atomically and parse it again to verify valid JSON.
9. Confirm no remaining handler command contains `/codex-meme/`.
10. Move the verified install directory to the timestamped backup rather than permanently deleting it. External asset directories remain untouched.
11. Confirm no unrelated Hook, configuration file, project file, or `AGENTS.md` changed.

## Completion report

Report the updated hooks file, removed handler count, recoverable backup path, untouched asset path, and whether Codex needs restarting. Do not claim that external assets were removed.
