# PRD: Windows Hook Console Popup Fix

## Problem

Windows 用户在 Claude Code 中使用 MemPalace 插件时，聊天过程中偶发弹出终端窗口。现象与 Stop / PreCompact hooks 触发时间一致，影响连续使用体验。

## Users

- Windows 上通过 Claude Code 插件使用 MemPalace 的开发者

## Root Cause

Claude 插件当前把 hook 顶层命令声明为 `bash ".../mempal-*.sh"`。在 Windows 上，`bash.exe` 属于控制台程序，宿主可能在 hook 启动时创建可见控制台窗口。`mempalace/hooks_cli.py` 里的后台子进程 detachment 只影响 Python hook 内部派生的子进程，无法隐藏顶层 `bash.exe` 自身的窗口。

## Decision

为 hooks 引入新的跨平台 `mempalace-hook` 入口，并把它注册为 `[project.gui-scripts]`。在 Windows 上该入口使用 GUI launcher 启动，避免控制台窗口；在入口代码内先恢复 OS 级 fd `0/1/2`，再手动把继承的 stdio 句柄重新绑定回 `sys.stdin` / `sys.stdout` / `sys.stderr`，再复用现有 Windows UTF-8 stdio 策略，最后调用现有 `mempalace.hooks_cli` 逻辑。

## Decision Drivers

1. 先移除最容易在 Windows 上显式弹窗的顶层 `bash.exe`。
2. 保持 hook 协议和 Python 业务逻辑不变，降低回归风险。
3. 改动局限在插件入口层，避免影响其他插件和 core hook logic。

## Options Considered

### Option A: 继续保留 shell wrapper，只在 shell 内部再做 Windows 分流

Pros:
- 最小化对现有 shell wrapper 的概念变化

Cons:
- 顶层仍然要先启动 `bash.exe`
- 无法从根上解决最外层控制台窗口创建

### Option B: 使用 `pythonw.exe` 或 GUI launcher 作为 hook 顶层入口

Pros:
- 理论上可隐藏控制台

Cons:
- 不能直接裸用 `pythonw.exe`；必须在应用代码里手动把继承句柄重新绑定回标准流
- 需要新增一个专门入口并补 Windows 专项测试

### Option C: 直接调用 `mempalace hook run ...`

Pros:
- 去掉最外层 `bash`，命令更短更直接
- 业务逻辑仍复用 `mempalace.hooks_cli`
- 与现有 tests 的 runner 语义接近，易于验证

Cons:
- 如果宿主对 `mempalace.exe` 仍以 console 方式启动，理论上仍可能存在少量窗口风险
- 失去 shell wrapper 内的 python fallback 链

## Chosen Approach

选择 Option B 的“GUI launcher + fd/std stream rebind”变体：

- 新增 `mempalace-hook` 入口
- 在 `pyproject.toml` 里注册为 `[project.gui-scripts]`
- Claude 插件 hook 配置改为直接调用 `mempalace-hook --hook ... --harness claude-code`
- 如无额外兼容性阻碍，Codex 插件 hooks 同步改为调用 `mempalace-hook --hook ... --harness codex`
- 入口内部复用 `mempalace.hooks_cli.run_hook(...)`

这样在 Windows 上，顶层 hook 进程不再是 console launcher；在 POSIX 上 `gui_scripts` 与普通脚本行为等价，仍可正常执行。并且通过 fd-first 恢复，兼容 `hooks_cli._output()` 和 `mcp_server` import-time fd 重定向契约。

## Scope

- 新增 `mempalace-hook` GUI entry point module
- 更新 `pyproject.toml`
- 更新 Claude 插件 hook 配置，改用 `mempalace-hook`
- 评估后优先同步更新 `.codex-plugin/hooks.json`，降低仓库入口漂移
- 更新对应测试
- 保留现有 `.claude-plugin/hooks/*.sh` 文件，不删除
- 保留现有 `.codex-plugin/hooks/mempal-hook.sh` 文件，不删除

## Out of Scope

- 改造 Claude 宿主自身的进程创建行为
- 重新设计 `mempalace/hooks_cli.py` 的业务逻辑
- 为所有插件统一引入一个跨平台 GUI runner

## Risks

- `gui_scripts` 在 Windows 上默认没有可用标准流，若 stdio rebind 实现不完整会破坏 hook 协议
- 某些环境里插件升级后如果 `mempalace-hook` entry point 没被正确安装，Claude hook 会直接找不到命令
- 这次修复只覆盖 hook 弹窗；MCP 启动路径若也存在 console popup，需要单独评估
- 保留旧 shell wrapper 但不再走主路径后，存在文档/测试与实际生产路径漂移风险

## Mitigations

- 复用现有 `hooks_cli` 逻辑，避免在新入口重写业务行为
- 新增 Windows 专项协议测试，验证 GUI-style 入口仍能恢复 fd `0/1/2`，并在导入 `mcp_server` 的 Stop hook 热路径下仍能通过 stdin 读 JSON 并向 stdout 回 JSON
- 保留 shell wrapper 文件本身，不做删除，避免文档与外部手工使用路径立即失效
- 在最终报告中明确 residual risk：若宿主 PATH / entry point 安装异常，需要重新安装插件/包
- 更新发布文档与自动化测试，确保 `mempalace-hook` 被声明、被配置引用且名称一致

## Acceptance Criteria

- `pyproject.toml` 新增 `mempalace-hook` 的 `[project.gui-scripts]` 声明
- Claude 插件 hook 配置不再含有 `bash "...mempal-*.sh"` 命令
- Claude 插件 hook 配置改为调用 `mempalace-hook --hook <name> --harness claude-code`
- Codex 插件 hooks 如进入本次改动范围，则同样改为调用 `mempalace-hook --hook <name> --harness codex`
- 新增测试证明 GUI-style hook 入口在 Windows 下仍保持 fd-first 的 stdin/stdout JSON 协议
- 新增测试/文档证明插件配置与 `pyproject.toml` 中的 hook entry point 名称对齐
- 现有 `mempalace/hooks_cli.py` 测试保持通过
- 与 Claude 插件 hook 相关的目标测试通过
