"""Contract tests for Claude plugin hook command wiring."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
CLAUDE_HOOK_CONFIG = REPO_ROOT / ".claude-plugin" / "hooks" / "hooks.json"
CODEX_HOOK_CONFIG = REPO_ROOT / ".codex-plugin" / "hooks.json"


@pytest.fixture(scope="module")
def claude_hook_config() -> dict:
    return json.loads(CLAUDE_HOOK_CONFIG.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def codex_hook_config() -> dict:
    return json.loads(CODEX_HOOK_CONFIG.read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    ("event", "expected_command"),
    [
        ("Stop", "mempalace-hook --hook stop --harness claude-code"),
        ("PreCompact", "mempalace-hook --hook precompact --harness claude-code"),
    ],
)
def test_claude_plugin_hook_commands_use_gui_entrypoint(
    claude_hook_config: dict, event: str, expected_command: str
) -> None:
    entries = claude_hook_config["hooks"][event]
    assert len(entries) == 1
    hook = entries[0]["hooks"][0]
    assert hook["command"] == expected_command
    assert "bash " not in hook["command"]


@pytest.mark.parametrize(
    ("event", "expected_command"),
    [
        ("SessionStart", "mempalace-hook --hook session-start --harness codex"),
        ("Stop", "mempalace-hook --hook stop --harness codex"),
        ("PreCompact", "mempalace-hook --hook precompact --harness codex"),
    ],
)
def test_codex_plugin_hook_commands_use_shared_hook_entrypoint(
    codex_hook_config: dict, event: str, expected_command: str
) -> None:
    entries = codex_hook_config["hooks"][event]
    assert len(entries) == 1
    hook = entries[0]["hooks"][0]
    assert hook["command"] == expected_command
    assert "mempal-hook.sh" not in hook["command"]
