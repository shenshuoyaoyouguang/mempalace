## Task Statement

为 MemPalace 设计并执行一个完整修复，解决 Windows 下 Claude Code 集成在聊天过程中因 Stop / PreCompact hooks 触发而偶发弹出终端窗口的问题；同时补测试并完成验证。

## Desired Outcome

- Windows 下 Claude 插件的 hook 触发不再依赖最外层 `bash` 包装。
- 现有 macOS/Linux 行为不回退。
- 插件 hook 仍然正确调用 `mempalace hook run --hook <name> --harness claude-code`。
- 测试覆盖新的配置与入口行为。

## Known Facts / Evidence

- `.claude-plugin/hooks/hooks.json` 当前直接执行 `bash "${CLAUDE_PLUGIN_ROOT}/hooks/mempal-stop-hook.sh"` 和 `bash "${CLAUDE_PLUGIN_ROOT}/hooks/mempal-precompact-hook.sh"`。
- `.claude-plugin/hooks/mempal-stop-hook.sh` / `mempal-precompact-hook.sh` 只是薄包装，最终调用 `mempalace hook run ...` 或 `python -m mempalace hook run ...`。
- `mempalace/hooks_cli.py` 已对 hook 内部再拉起的后台子进程做了 Windows detachment 处理，但这发生在最外层 hook runner 启动之后，无法消除顶层 `bash.exe` 自身的控制台弹窗。
- 本机 `~/.mempalace/hook_state/hook.log` 已记录真实 `TRIGGERING SAVE`，与“聊天聊着聊着偶尔弹一下”的现象吻合。
- `tests/test_claude_plugin_hook_wrappers.py` 和 `tests/test_claude_plugin_hook_config.py` 已覆盖 Claude 插件 hook wrapper 行为与 hook 配置边界。
- `.codex-plugin` 也有 hook 入口，但用户这次复现路径明确是 Claude Code。

## Constraints

- 保持 Simplified Chinese 沟通，但技术工件保持原文。
- 尽量缩小改动范围，避免牵连其他插件 hooks。
- 不能只在本机手工改 Claude 配置，必须在项目内形成可发布修复。
- 需要保留当前 hook 协议：stdin JSON 输入，stdout JSON 输出。

## Unknowns / Open Questions

- Claude 插件 hook 配置是否支持平台条件分流；仓库内暂无直接证据。
- Windows 下直接调用 `mempalace` console script 是否完全消除可见窗口，还是仅比 `bash.exe` 更不易弹窗。
- 是否需要同步修复 `.codex-plugin` 以避免同类问题在 Codex 路径复现。

## Likely Codebase Touchpoints

- `.claude-plugin/hooks/hooks.json`
- `.claude-plugin/hooks/mempal-stop-hook.sh`
- `.claude-plugin/hooks/mempal-precompact-hook.sh`
- `tests/test_claude_plugin_hook_config.py`
- `tests/test_claude_plugin_hook_wrappers.py`
- 可能扩展：`.codex-plugin/hooks.json`, `.codex-plugin/hooks/mempal-hook.sh`
