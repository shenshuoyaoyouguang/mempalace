# Test Spec: Windows Hook Console Popup Fix

## Verification Goals

1. Claude 插件 hook 配置已切换为调用 `mempalace-hook`
2. `mempalace-hook` 在 Windows GUI launcher 路径下仍可正确恢复 fd `0/1/2` 并透传 stdin/stdout JSON
3. 每个事件仍然只声明一个 hook command，timeout 边界不变
4. hook 业务逻辑核心测试不回退
5. `pyproject.toml` 与插件 hook 配置中的 hook entry point 名称保持一致

## Planned Tests

### Unit / Contract

- 更新 `tests/test_claude_plugin_hook_config.py`
  - 断言 `Stop` / `PreCompact` hook command 不再包含 `bash`
  - 断言命令精确等于 `mempalace-hook --hook <name> --harness claude-code`
  - 保持 timeout/cardinality 断言

- 更新 `tests/test_claude_plugin_hook_wrappers.py`
  - 从 shell-wrapper 执行测试转为插件 hook command 合约测试
  - 直接读取 `hooks.json` 并校验命令映射

- 新增 GUI hook entry 测试
  - Windows 下用 `pythonw`/GUI-style 路径运行入口模块
  - 验证轻路径：`session-start` 下 stdin JSON 可被读取、stdout JSON 可被写回
  - 验证热路径：`stop` 触发 `_save_diary_direct()` 并导入 `mcp_server` 后，fd-first 输出仍然可被父进程捕获

- 新增 entry point 对齐测试
  - 验证 `pyproject.toml` 存在 `mempalace-hook`
  - 验证 `.claude-plugin/hooks/hooks.json` 引用的命令名与 `pyproject.toml` 一致
  - 如果本次同步改动 `.codex-plugin/hooks.json`，同样验证其命令名与 `pyproject.toml` 一致

### Regression

- 运行 `tests/test_hooks_cli.py`
  - 确保 hook core logic 没被入口层改动波及

## Manual Validation

- 检查 `.claude-plugin/hooks/hooks.json` 配置已变更
- 检查 `pyproject.toml` 已声明 GUI entry point
- 检查 `docs/RELEASING.md` 已纳入 `mempalace-hook` 对齐检查
- 如可行，说明用户安装更新版本后，Windows 触发 hook 时走 GUI launcher 而非 `bash.exe`

## Exit Criteria

- 目标测试全部通过
- 无新增失败
- 最终报告明确 residual risk 与验证范围
