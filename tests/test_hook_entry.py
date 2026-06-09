"""Tests for the GUI-friendly MemPalace hook entry point."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]


def _run_subprocess(code: str, payload: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", code],
        input=payload,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=REPO_ROOT,
        check=False,
        timeout=30,
    )


def _run_subprocess_isolated(
    code: str,
    payload: str,
    home_dir: Path,
    *,
    use_pythonw: bool = False,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["HOME"] = str(home_dir)
    env["USERPROFILE"] = str(home_dir)
    env["PYTHONPATH"] = str(REPO_ROOT)
    python = sys.executable
    if use_pythonw:
        candidate = str(Path(sys.executable).with_name("pythonw.exe"))
        python = candidate
    return subprocess.run(
        [python, "-c", code],
        input=payload,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=REPO_ROOT,
        env=env,
        check=False,
        timeout=30,
    )


def test_hook_entry_declared_in_pyproject():
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert '[project.gui-scripts]' in pyproject
    assert 'mempalace-hook = "mempalace.hook_entry:main"' in pyproject


def test_hook_entry_name_matches_plugin_configs():
    claude = json.loads((REPO_ROOT / ".claude-plugin" / "hooks" / "hooks.json").read_text("utf-8"))
    codex = json.loads((REPO_ROOT / ".codex-plugin" / "hooks.json").read_text("utf-8"))
    for event in ("Stop", "PreCompact"):
        assert claude["hooks"][event][0]["hooks"][0]["command"].startswith("mempalace-hook ")
    for event in ("SessionStart", "Stop", "PreCompact"):
        assert codex["hooks"][event][0]["hooks"][0]["command"].startswith("mempalace-hook ")


def test_hook_entry_session_start_round_trips_json():
    code = (
        "import io, json, sys\n"
        "from mempalace import hook_entry\n"
        "sys.argv = ['mempalace-hook', '--hook', 'session-start', '--harness', 'claude-code']\n"
        "sys.stdin = io.StringIO('{\"session_id\":\"abc123\"}')\n"
        "hook_entry.main()\n"
    )
    result = _run_subprocess(code)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {}


def test_hook_entry_stop_path_survives_mcp_server_import_fd_contract(tmp_path):
    transcript = tmp_path / "session.jsonl"
    transcript.write_text(
        "\n".join(
            json.dumps({"message": {"role": "user", "content": f"msg {i}"}})
            for i in range(15)
        ),
        encoding="utf-8",
    )
    home_dir = tmp_path / "home"
    palace_root = home_dir / ".mempalace"
    palace_root.mkdir(parents=True)
    (palace_root / "config.json").write_text(
        json.dumps({"hooks": {"auto_save": True, "silent_save": True, "desktop_toast": False}}),
        encoding="utf-8",
    )
    code = (
        "import json, os, sys\n"
        "import mempalace.hook_entry as entry\n"
        "import mempalace.hooks_cli as hc\n"
        "import mempalace.mcp_server as mcp_server\n"
        "sys.argv = ['mempalace-hook', '--hook', 'stop', '--harness', 'claude-code']\n"
        "hc.PALACE_ROOT = hc.Path.home() / '.mempalace'\n"
        "hc.STATE_DIR = hc.PALACE_ROOT / 'hook_state'\n"
        "hc._MINE_PID_DIR = hc.STATE_DIR / 'mine_pids'\n"
        "hc._state_dir_initialized = False\n"
        "hc._save_diary_direct = lambda *a, **kw: {'count': 1, 'themes': []}\n"
        "hc._ingest_transcript = lambda *a, **kw: None\n"
        "hc._maybe_auto_ingest = lambda *a, **kw: None\n"
        "entry.main()\n"
    )
    payload = json.dumps(
        {"session_id": "s1", "stop_hook_active": False, "transcript_path": str(transcript)}
    )
    result = _run_subprocess_isolated(code, payload, home_dir)
    assert result.returncode == 0, result.stderr
    out = json.loads(result.stdout)
    assert "systemMessage" in out
    assert "1 memories" in out["systemMessage"]


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only GUI stdio contract")
def test_pythonw_style_gui_launcher_can_round_trip_stdio_via_hook_entry(tmp_path):
    home_dir = tmp_path / "home"
    palace_root = home_dir / ".mempalace"
    palace_root.mkdir(parents=True)
    (palace_root / "config.json").write_text(
        json.dumps({"hooks": {"auto_save": True, "silent_save": True, "desktop_toast": False}}),
        encoding="utf-8",
    )
    transcript = tmp_path / "session.jsonl"
    transcript.write_text(
        "\n".join(
            json.dumps({"message": {"role": "user", "content": f"msg {i}"}})
            for i in range(15)
        ),
        encoding="utf-8",
    )
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    if not pythonw.exists():
        pytest.skip("pythonw.exe not available beside current interpreter")
    code = (
        "import sys\n"
        "import mempalace.hook_entry as entry\n"
        "import mempalace.hooks_cli as hc\n"
        "sys.argv = ['mempalace-hook', '--hook', 'stop', '--harness', 'claude-code']\n"
        "hc.PALACE_ROOT = hc.Path.home() / '.mempalace'\n"
        "hc.STATE_DIR = hc.PALACE_ROOT / 'hook_state'\n"
        "hc._MINE_PID_DIR = hc.STATE_DIR / 'mine_pids'\n"
        "hc._state_dir_initialized = False\n"
        "hc._save_diary_direct = lambda *a, **kw: {'count': 1, 'themes': []}\n"
        "hc._ingest_transcript = lambda *a, **kw: None\n"
        "hc._maybe_auto_ingest = lambda *a, **kw: None\n"
        "entry.main()\n"
    )
    payload = json.dumps(
        {
            "session_id": "win-session",
            "stop_hook_active": False,
            "transcript_path": str(transcript),
        }
    )
    result = _run_subprocess_isolated(code, payload, home_dir, use_pythonw=True)
    assert result.returncode == 0, result.stderr
    out = json.loads(result.stdout)
    assert "systemMessage" in out
