# Codex Meme

[English](README.en.md)

给 Codex Desktop 加一层会看场合的本地表情包反应。

Codex Meme 是一个完全本地运行的社区项目。它通过 `SessionStart`、`UserPromptSubmit` 和 `Stop` 三段 Hook，在不改变正常回答的前提下，偶尔允许 Codex 从用户自己的素材中挑一张表情包。模型可以使用候选，也可以认为场合不合适并拒绝。

> 当前版本：`v0.1-alpha` · Windows · Codex Desktop · Python 3.10+

## 效果演示

自然触发：Codex 正常完成回答后，可以在合适的轻松场景使用一张本地候选。

![Codex Meme 自然触发演示](docs/images/demo-natural-reaction.jpg)

反问式点播：“不来个表情包吗？”这类表达也能被识别。

![Codex Meme 反问式点播演示](docs/images/demo-direct-request.jpg)

GIF 定向点播：“来张动图”等请求只会从启用的 GIF 素材中选择。

![Codex Meme GIF 定向点播演示](docs/images/demo-gif-request.webp)

## 它会做什么

- 普通对话经过预热、冷却和概率判断后，随机提供 3 张候选。
- “来张表情包”“send me a meme”等明确点播会绕过概率和冷却。
- “有别的吗”“another one”等追图表达只在上一轮确实显示图片后生效。
- “来个动图”“send me a GIF”等请求只从 GIF 素材中选择。
- 严肃话题、禁图要求、严格 JSON、代码或补丁输出会在本地直接拦截。
- Stop Hook 会记录使用、拒绝以及候选外图片等异常情况。

## 它不会做什么

- 运行时不生成或下载图片；本仓库不捆绑任何可供 Hook 使用的表情包素材。
- 不上传提示词、图片、日志或统计数据。
- Hook 运行时不使用网络、MCP、服务器或第三方 API。
- 不创建、读取或修改任何 `AGENTS.md`。
- 不在运行时扫描素材目录；只有 `manifest.json` 中明确列出的图片能够成为候选。

## 工作方式

```text
SessionStart       注入一段很短的低优先级行为协议
UserPromptSubmit   本地判断是否提供 3 张候选
Stop               检查本轮是否使用了合法候选并更新连续追图状态
```

未命中时，UserPromptSubmit Hook 不向模型增加任何表情包候选上下文。所有状态和日志都保存在本机 Codex 用户目录中。

## 使用 Agent 安装

本项目不要求用户手工编辑 `hooks.json`。把仓库交给你信任的编码 Agent，并发送：

```text
请读取这个仓库中的 INSTALL_FOR_AGENT.md，并按照其中的规范为我安装 Codex Meme。
保留我已有的所有 Hook，不要创建或修改任何 AGENTS.md。
修改前先备份，完成后运行验证并告诉我备份和回滚位置。
```

安装 Agent 会询问你使用已有的本地表情包目录，还是在你明确同意后从 [ChineseBQB](https://github.com/zhaoolee/ChineseBQB) 获取素材。随后，它只会检查你确认的目录，为图片建立显式 manifest，并把三段 Hook 合并到用户级 `~/.codex/hooks.json`。安装或修改 Hook 后，Codex 会要求你审查并信任新的 Hook 定义；不要让 Agent 手工伪造信任记录。

官方 Hook 说明：[OpenAI Codex Hooks](https://developers.openai.com/codex/hooks)

## 素材要求

没有现成素材库时，可以把 [ChineseBQB](https://github.com/zhaoolee/ChineseBQB) 作为可选来源交给安装 Agent。下载只发生在安装阶段，必须由你确认保存位置；下载后的目录仍是 Codex Meme 之外的外部素材目录。

- 至少 3 张有效素材。
- 支持 `.png`、`.jpg`、`.jpeg`、`.gif`、`.webp`。
- GIF 定向点播需要至少 3 张启用的 GIF。
- 每张图片需要唯一 `id`、绝对路径和简短 `label`。
- 素材版权由用户自行负责；ChineseBQB 是独立的第三方项目，其仓库及图片不受 Codex Meme 的 MIT License 覆盖。

manifest 示例见 [`templates/manifest.example.json`](templates/manifest.example.json)。

## 默认配置

| 配置 | 默认值 | 说明 |
| --- | ---: | --- |
| `probability` | `0.20` | 普通、非冷却回合提供候选的概率 |
| `cooldown_turns` | `5` | 命中后的普通回合冷却 |
| `warmup_turns` | `2` | 新会话前两轮不随机触发 |
| `log` | `true` | 只记录本地事件元数据，不记录提示词正文 |
| `max_sessions` | `40` | 本地状态最多保留的会话数 |

## 卸载

让 Agent 读取 [`UNINSTALL_FOR_AGENT.md`](UNINSTALL_FOR_AGENT.md)。卸载规范只移除 Codex Meme 自己的 Handler 和安装目录，不删除外部素材，也不碰其他 Hook。

## 开发与测试

```powershell
py -3 -m py_compile hooks\reaction.py hooks\session_start.py hooks\stop.py
py -3 -m unittest discover -s tests -v
```

项目只使用 Python 标准库。

## 友情链接

- [LinuxDo](https://linux.do)

感谢 LinuxDo 社区，为我学习 AI 提供了很多帮助。

## 许可与声明

代码使用 [MIT License](LICENSE)。用户素材不受本项目许可证覆盖。README 演示截图仅用于功能展示；截图界面及其中的第三方图片不在本项目 MIT License 的授权范围内。

Codex Meme 是非官方社区项目，与 OpenAI 没有隶属或背书关系。
