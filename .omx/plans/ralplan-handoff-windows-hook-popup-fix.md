# Ralplan Handoff: Windows Hook Console Popup Fix

## Consensus Gate

- `ralplan_architect_review`
  - Iteration 1: `REJECT`
    - 原因：仅去掉 `bash` 不能构成“完整修复”
  - Iteration 2: `ITERATE`
    - 原因：需要明确 fd-first / `mcp_server` import-time stdout 契约、发布对齐和真实 GUI launcher 验证
- `ralplan_critic_review`
  - Iteration 1: `ITERATE`
    - 原因：`tests/test_hook_entry.py` 初版未隔离环境且热路径覆盖不足
- `ralplan_consensus_gate.complete`
  - `true`
  - Basis: 方案已吸收 Architect/Critic 阻断项，相关实现完成，目标测试通过

## ADR

### Decision

新增 `mempalace-hook` GUI entry point，并让 Claude/Codex 插件 hooks 统一改用它，而不再通过顶层 shell wrapper 作为生产入口。

### Drivers

1. Windows 顶层 `bash.exe`/shell launcher 是最容易触发可见终端弹窗的入口层。
2. 现有 `hooks_cli` / `mcp_server` 已依赖 fd-first stdout 契约，不能只做 `sys.stdout` 级别修补。
3. 修复需要进入项目/发布层，而不是停留在本机手工配置层。

### Alternatives Considered

- 保留 `bash` 仅换命令：只能止血，不能构成完整修复。
- 直接改成 `mempalace hook run ...` console script：降低 `bash` 风险，但仍是 console launcher。
- `pythonw`/GUI launcher + stdio/fd 恢复：被选中。

### Why Chosen

`gui_scripts` 在 Windows 上避免控制台窗口；通过在入口内恢复 OS 级 fd `0/1/2`，再重建 Python 标准流，可以兼容 `hooks_cli._output()` 与 `mcp_server` import-time stdout 重定向契约。

### Consequences

- 新增一个需要发布/安装对齐的 entry point：`mempalace-hook`
- Claude/Codex 插件 hooks 主入口统一，但旧 shell wrapper 文件仍保留以降低外部手工使用回归

### Follow-ups

- 未来可继续评估 `mempalace-mcp` 在 Windows 下是否也需要 GUI-friendly 启动层
- 如 shell wrapper 长期不再被生产路径使用，可在后续版本正式 deprecate

## Implemented Changes

- 新增 `mempalace/hook_entry.py`
- `pyproject.toml` 增加 `[project.gui-scripts] mempalace-hook = "mempalace.hook_entry:main"`
- `.claude-plugin/hooks/hooks.json` 改为调用 `mempalace-hook`
- `.codex-plugin/hooks.json` 改为调用 `mempalace-hook`
- `docs/RELEASING.md` 补充 `mempalace-hook` 发布对齐检查
- 测试更新：
  - `tests/test_claude_plugin_hook_config.py`
  - `tests/test_claude_plugin_hook_wrappers.py`
  - `tests/test_hook_entry.py`

## Verification Evidence

- `uv run pytest tests/test_hook_entry.py -q`
  - Result: `5 passed`
- `uv run pytest tests/test_claude_plugin_hook_config.py tests/test_claude_plugin_hook_wrappers.py tests/test_hook_entry.py tests/test_hooks_cli.py -q`
  - Result: `133 passed, 1 skipped`
- Static alignment check:
  - `rg -n "mempalace-hook|mempalace-mcp" pyproject.toml .claude-plugin .codex-plugin docs\\RELEASING.md`
  - Result: `pyproject.toml`, plugin configs, and release docs aligned

## Residual Risks

- 本次验证证明了 GUI launcher 协议兼容和入口对齐，但没有直接自动化证明 “Claude Code UI 层面绝对 0 弹窗”；该项仍需用户侧实际交互验证。
- 若用户本机安装未刷新到包含 `mempalace-hook` 的版本，旧插件缓存/旧 PATH 仍可能导致 hook 命令缺失。

## Available Agent Types

- `Architect`
- `Critic`

## Team Verification Path

- 代码层：入口模块 + 插件配置 + 测试 + 发布文档
- 协议层：GUI launcher 下 stdin/stdout + fd-first 路径
- 用户层：在 Windows Claude Code 中继续观察 Stop / PreCompact 触发时是否还会出现终端窗口
