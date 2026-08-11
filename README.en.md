# Codex Meme

[中文](README.md)

A context-aware meme reaction layer for Codex Desktop.

Codex Meme is a local-first community project built around `SessionStart`, `UserPromptSubmit`, and `Stop` hooks. It occasionally lets Codex choose one image from a local collection or a verified remote cache without changing the normal answer. The model may use a candidate or decline all candidates when the moment is not appropriate.

> This development branch is based on [`v0.1-alpha`](https://github.com/xxH7r/codex-meme/releases/tag/v0.1-alpha) and adds optional remote-manifest sync · Windows · Codex Desktop · Python 3.10+

## Demo

Natural reaction: after completing the normal answer, Codex may use one local candidate when the moment is appropriate and casual.

![Codex Meme natural reaction demo](docs/images/demo-natural-reaction.jpg)

Rhetorical direct request: expressions such as “Why not add a meme?” are recognized too.

![Codex Meme rhetorical request demo](docs/images/demo-direct-request.jpg)

Directed GIF request: requests such as “send me a GIF” draw only from enabled GIF assets.

![Codex Meme directed GIF request demo](docs/images/demo-gif-request.webp)

## What it does

- Randomly offers 3 candidates after warmup, cooldown, and probability checks.
- Direct requests such as “send me a meme” bypass probability and cooldown.
- Follow-ups such as “another one” work only after an image was actually shown.
- GIF requests only draw from enabled GIF assets.
- Serious topics, no-image requests, and strict JSON/code/patch formats are blocked locally.
- An optional startup handler can sync an explicit HTTPS manifest into a verified local cache.
- The Stop hook audits use, declines, and assets outside the current offer while updating follow-up state; optional logs can retain these diagnostic events.

## What it does not do

- It does not generate images, and this repository bundles no meme assets for hook use.
- It does not upload prompts, images, logs, or analytics.
- Normal replies, selection, and Stop hooks never use the network; only the explicitly enabled sync handler contacts allowlisted HTTPS hosts.
- It does not use MCP, accounts, or a third-party search API to find images dynamically.
- It never creates, reads, or modifies `AGENTS.md`.
- It never scans asset directories. Only explicit local or remote manifest entries are eligible.

## Architecture

```text
SessionStart       concurrently runs optional sync and behavior-rule injection
UserPromptSubmit   decides locally whether to offer 3 candidates
Stop               audits candidate use and updates follow-up state
```

Remote sync validates HTTPS hosts, response sizes, image types, and SHA-256 before writing to the local cache. A failed or offline refresh preserves the last successful cache. When no offer is made, the UserPromptSubmit hook adds no meme candidate context to the model. Cache, state, and logs stay in the local Codex user directory.

## Install with an agent

Give this repository to a trusted coding agent and send:

```text
Get Codex Meme from https://github.com/huaixia18/codex-meme,
read INSTALL_FOR_AGENT.md in the repository, and install it exactly as specified.
Preserve every existing hook and do not create or modify any AGENTS.md file.
Back up affected files before editing, run the verification steps, and report the backup and rollback paths.
```

The agent will ask whether to use an existing local asset directory, configure an HTTPS remote manifest, or obtain assets from [ChineseBQB](https://github.com/zhaoolee/ChineseBQB) with your explicit approval. Local mode inspects only the approved directory; remote mode contacts only the approved manifest and exact host allowlist. It then merges four handlers into the user-level `~/.codex/hooks.json`. Codex requires the user to review and trust new or changed hook definitions. The agent must never fabricate hook trust records.

Official reference: [OpenAI Codex Hooks](https://developers.openai.com/codex/hooks)

## Asset requirements

If you do not already have a collection, [ChineseBQB](https://github.com/zhaoolee/ChineseBQB) is an optional source that the installation agent can use. It contains a large number of images, so a complete download may require substantial time and disk space. You normally do not need to add the whole collection to the manifest; select only the subdirectories or images you actually want. Downloading happens only during installation and only after you approve the destination. The downloaded directory remains external to Codex Meme.

- At least 3 valid assets.
- Supported extensions: `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`.
- Directed GIF requests require at least 3 enabled GIF files.
- Every item needs a unique `id`, absolute path, and concise `label`.
- `id` may contain only ASCII letters, digits, hyphens, and underscores, with a length of 1–64 characters.
- Keep `label` on one line and at most 80 characters when possible. At runtime, whitespace is collapsed, control characters are removed, and longer labels are truncated; an entry whose cleaned label is empty is not loaded.
- Users are responsible for asset rights. ChineseBQB is an independent third-party project; its repository and images are not covered by the Codex Meme MIT License.

Let the installation agent generate and validate the manifest when possible. Follow the `id` and `label` rules above when editing it manually.

See [`templates/manifest.example.json`](templates/manifest.example.json).

## Remote asset manifests

Remote mode is disabled by default. When enabled, `sync_remote.py` checks for updates only on `SessionStart`; `reaction.py` still reads local files and never performs a just-in-time network request while answering.

Configure `reaction.json` like this:

```json
{
  "remote": {
    "enabled": true,
    "manifest_url": "https://cdn.example.com/memes/manifest.json",
    "allowed_hosts": ["cdn.example.com"],
    "refresh_hours": 24
  }
}
```

Every remote item requires an `id`, HTTPS `url`, lowercase 64-character `sha256`, `label`, and `enabled`. The manifest, images, and final redirect targets must use exact `allowed_hosts`. IP literals, private destinations, non-HTTPS URLs, oversized responses, mismatched content types, and hash failures are rejected. See [`templates/remote-manifest.example.json`](templates/remote-manifest.example.json) for the full shape; its domains and hashes are placeholders that must be replaced.

Successful sync writes an internal `.remote_manifest.json` and stores images under `remote-cache/`. A failed sync never replaces the previous successful result, and retries back off for 15 minutes by default. Enabling remote mode exposes ordinary HTTPS request metadata, such as IP address and User-Agent, to the manifest and image hosts. The manifest operator remains responsible for asset rights and hosting costs.

## Defaults

| Setting | Default | Meaning |
| --- | ---: | --- |
| `probability` | `0.20` | Offer probability on eligible normal turns |
| `cooldown_turns` | `5` | Normal-turn cooldown after an offer |
| `warmup_turns` | `2` | No random offers on the first two turns |
| `remote.enabled` | `false` | Enable remote-manifest synchronization |
| `remote.refresh_hours` | `24` | Refresh interval after a successful sync |
| `log` | `true` | Optional local diagnostic log, enabled by default |
| `max_sessions` | `40` | Maximum session states retained locally |

## Local logs

Codex Meme writes optional diagnostic events to `~/.codex/hooks/codex-meme/reaction.log` by default. They help explain warmup, cooldown, probability misses, candidate offers, use, declines, and runtime errors. Logging does not participate in selection, cooldown, or follow-up behavior.

The log contains timestamps, event types, session and turn identifiers, candidate IDs, and general trigger or skip reasons. It does not store complete prompts, assistant response text, or image contents, and it is never uploaded. Set `"log"` to `false` in `~/.codex/hooks/codex-meme/reaction.json` to disable it. Disabling or deleting the log does not affect core behavior, and logging can be enabled again later.

When the current log reaches approximately 2 MiB, it rotates to `reaction.log.1`. Only one previous log is retained.

## Adjusting the reaction frequency

`probability` is configurable from `0.0` to `1.0`. A value of `0.20` means a 20% offer chance on eligible normal turns, `0.50` means 50%, and `1.0` offers candidates on every eligible normal turn outside cooldown. Setting it to `0.0` disables random offers while direct requests and valid follow-ups continue to work.

The effective frequency is also reduced by `warmup_turns`, `cooldown_turns`, and local guards such as serious-topic detection. Direct requests and valid follow-ups bypass probability, warmup, and cooldown.

To customize it during installation, append a sentence like this to the installation prompt:

```text
Set the random offer probability for normal turns to 0.35 and keep the other defaults unchanged.
```

You do not need to reinstall when changing it later. Give the following prompt to a coding agent, replacing `0.35` with the value you want:

```text
Back up my installed Codex Meme configuration, then change probability to 0.35 in
~/.codex/hooks/codex-meme/reaction.json.
Parse and update the file as JSON, preserve every other field, validate it, and report the backup path and effective value.
```

## Uninstall

Ask the agent to read [`UNINSTALL_FOR_AGENT.md`](UNINSTALL_FOR_AGENT.md). The uninstall contract removes only Codex Meme handlers and its isolated install directory. External assets and unrelated hooks remain untouched.

## Feedback and contributions

For bugs, feature ideas, or code contributions, open a [GitHub Issue](https://github.com/huaixia18/codex-meme/issues) or Pull Request. Include your Windows, Python, and Codex versions when reporting a problem, but do not upload private prompts, images, logs, or local paths.

## Development

```powershell
py -3 -m py_compile hooks\reaction.py hooks\session_start.py hooks\stop.py hooks\sync_remote.py
py -3 -m unittest discover -s tests -v
```

The project uses only the Python standard library.

## Community links

- [LinuxDo](https://linux.do)

Thanks to the LinuxDo community for helping me so much in learning about AI.

## License and status

Code is licensed under the [MIT License](LICENSE). User-provided assets are not covered by this license. README screenshots are included only to demonstrate behavior; the captured interface and third-party images are not licensed under the Codex Meme MIT License.

Codex Meme is an unofficial community project and is not affiliated with or endorsed by OpenAI.
