"""GUI-friendly hook entry point for MemPalace.

Windows ``gui_scripts`` launch without allocating a console window, which
avoids visible hook popups in GUI-hosted clients like Claude Code. The tradeoff
is that ``sys.stdin`` / ``sys.stdout`` / ``sys.stderr`` may not be wired up in
the normal console-script way, so this entry point restores OS-level fd 0/1/2
from inherited Win32 std handles before dispatching to ``hooks_cli.run_hook``.

On non-Windows platforms the helper is a thin wrapper around the same hook
dispatcher and behaves like a normal console script.
"""

from __future__ import annotations

import argparse
import io
import os
import sys

from ._stdio import reconfigure_stdio_utf8_on_windows
from .hooks_cli import run_hook


def _rebind_windows_standard_streams() -> None:
    """Restore fd-backed stdio under Windows GUI launchers.

    ``gui_scripts`` on Windows are commonly launched via ``pythonw.exe``-style
    semantics: no console window, but inherited anonymous pipes may still be
    present when a parent process wires stdin/stdout/stderr explicitly. The
    hook protocol depends on those pipes. This helper maps any available Win32
    standard handles back onto C-runtime fds 0/1/2 and then rebuilds Python
    text streams on top of them.
    """
    if sys.platform != "win32":
        return

    import ctypes
    import msvcrt

    kernel32 = ctypes.windll.kernel32
    std_specs = (
        (-10, 0, "stdin", "rb", "surrogateescape"),
        (-11, 1, "stdout", "wb", "strict"),
        (-12, 2, "stderr", "wb", "strict"),
    )

    for std_handle_id, fd_target, attr, mode, errors in std_specs:
        handle = kernel32.GetStdHandle(std_handle_id)
        if handle in (0, -1):
            continue
        try:
            flags = os.O_RDONLY if "r" in mode else os.O_WRONLY
            fd = msvcrt.open_osfhandle(handle, flags)
        except OSError:
            continue
        try:
            if fd != fd_target:
                os.dup2(fd, fd_target)
                os.close(fd)
        except OSError:
            try:
                os.close(fd)
            except OSError:
                pass
            continue

        raw = io.FileIO(fd_target, mode=mode, closefd=False)
        if "r" in mode:
            stream = io.TextIOWrapper(raw, encoding="utf-8", errors=errors)
        else:
            stream = io.TextIOWrapper(raw, encoding="utf-8", errors=errors, write_through=True)
        setattr(sys, attr, stream)


def main() -> None:
    """Entry point for ``mempalace-hook``."""
    os.environ.pop("PYTHONPATH", None)
    _rebind_windows_standard_streams()
    reconfigure_stdio_utf8_on_windows(
        stdin_errors="surrogateescape",
        stdout_errors="strict",
        stderr_errors="strict",
    )

    parser = argparse.ArgumentParser(description="Run MemPalace hook logic.")
    parser.add_argument("--hook", required=True, choices=("session-start", "stop", "precompact"))
    parser.add_argument("--harness", required=True)
    args = parser.parse_args()
    run_hook(hook_name=args.hook, harness=args.harness)


if __name__ == "__main__":
    main()
