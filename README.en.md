# Codex Meme

[中文](README.md)

A local, context-aware meme reaction layer for Codex Desktop.

Codex Meme is a fully local community project built from three Codex hooks: `SessionStart`, `UserPromptSubmit`, and `Stop`. It occasionally lets Codex choose one image from the user's own collection without changing the normal answer. The model may use a candidate or decline all candidates when the moment is not appropriate.

> Current release: `v0.1-alpha` · Windows · Codex Desktop · Python 3.10+

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
- The Stop hook records legal use, declines, and use of assets outside the current offer.

## What it does not do

- The runtime does not generate or download images, and this repository bundles no meme assets for hook use.
- It does not upload prompts, images, logs, or analytics.
- The runtime uses no network service, MCP server, account, or external API.
- It never creates, reads, or modifies `AGENTS.md`.
- It never scans asset directories at runtime. Only explicit `manifest.json` entries are eligible.

## Architecture

```text
SessionStart       injects a short, low-priority behavior rule
UserPromptSubmit   decides locally whether to offer 3 candidates
Stop               audits candidate use and updates follow-up state
```

When no offer is made, the UserPromptSubmit hook adds no meme candidate context to the model. State and logs stay in the local Codex user directory.

## Install with an agent

Give this repository to a trusted coding agent and send:

```text
Read INSTALL_FOR_AGENT.md in this repository and install Codex Meme exactly as specified.
Preserve every existing hook and do not create or modify any AGENTS.md file.
Back up affected files before editing, run the verification steps, and report the backup and rollback paths.
```

The agent will ask whether to use an existing local asset directory or, with your explicit approval, obtain assets from [ChineseBQB](https://github.com/zhaoolee/ChineseBQB). It then inspects only the directory you approve, creates an explicit manifest, and merges the three handlers into the user-level `~/.codex/hooks.json`. Codex requires the user to review and trust new or changed hook definitions. The agent must never fabricate hook trust records.

Official reference: [OpenAI Codex Hooks](https://developers.openai.com/codex/hooks)

## Asset requirements

If you do not already have a collection, [ChineseBQB](https://github.com/zhaoolee/ChineseBQB) is an optional source that the installation agent can use. Downloading happens only during installation and only after you approve the destination. The downloaded directory remains external to Codex Meme.

- At least 3 valid assets.
- Supported extensions: `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`.
- Directed GIF requests require at least 3 enabled GIF files.
- Every item needs a unique `id`, absolute path, and concise `label`.
- Users are responsible for asset rights. ChineseBQB is an independent third-party project; its repository and images are not covered by the Codex Meme MIT License.

See [`templates/manifest.example.json`](templates/manifest.example.json).

## Defaults

| Setting | Default | Meaning |
| --- | ---: | --- |
| `probability` | `0.20` | Offer probability on eligible normal turns |
| `cooldown_turns` | `5` | Normal-turn cooldown after an offer |
| `warmup_turns` | `2` | No random offers on the first two turns |
| `log` | `true` | Local event metadata only; prompt text is not logged |
| `max_sessions` | `40` | Maximum session states retained locally |

## Uninstall

Ask the agent to read [`UNINSTALL_FOR_AGENT.md`](UNINSTALL_FOR_AGENT.md). The uninstall contract removes only Codex Meme handlers and its isolated install directory. External assets and unrelated hooks remain untouched.

## Development

```powershell
py -3 -m py_compile hooks\reaction.py hooks\session_start.py hooks\stop.py
py -3 -m unittest discover -s tests -v
```

The project uses only the Python standard library.

## Community links

- [LinuxDo](https://linux.do)

Thanks to the LinuxDo community for helping me so much in learning about AI.

## License and status

Code is licensed under the [MIT License](LICENSE). User-provided assets are not covered by this license. README screenshots are included only to demonstrate behavior; the captured interface and third-party images are not licensed under the Codex Meme MIT License.

Codex Meme is an unofficial community project and is not affiliated with or endorsed by OpenAI.
