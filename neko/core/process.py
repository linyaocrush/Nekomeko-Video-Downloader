"""Unified subprocess helpers for yt-dlp / ffmpeg calls.

All subprocess invocations should go through these helpers to ensure:
- Windows: no console window (CREATE_NO_WINDOW + STARTUPINFO)
- Consistent encoding (utf-8, errors='replace')
- PYTHONIOENCODING set for child processes
"""

import os
import subprocess

# ── Shared defaults ────────────────────────────────────────────

_IS_WIN = os.name == "nt"

_BASE_ENV = {**os.environ, "PYTHONIOENCODING": "utf-8"}


def _win_startupinfo():
    """Return a STARTUPINFO that hides the console window on Windows."""
    if not _IS_WIN:
        return None
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    return si


def _win_creationflags():
    """Return CREATE_NO_WINDOW on Windows, 0 elsewhere."""
    return subprocess.CREATE_NO_WINDOW if _IS_WIN else 0


def _merge_env(extra=None):
    """Merge extra env vars into the base environment."""
    if extra is None:
        return _BASE_ENV
    return {**_BASE_ENV, **extra}


# ── Public API ─────────────────────────────────────────────────

def run_text(cmd, *, cwd=None, env=None, capture=True):
    """Run a command and return a CompletedProcess with text output.

    Args:
        cmd: Command as a list of strings.
        cwd: Working directory.
        env: Extra environment variables (merged with base).
        capture: If True, capture stdout+stderr. If False, inherit stdio.

    Returns:
        subprocess.CompletedProcess with stdout/stderr as strings.
    """
    kwargs = {
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
        "cwd": cwd,
        "env": _merge_env(env),
        "startupinfo": _win_startupinfo(),
        "creationflags": _win_creationflags(),
    }
    if capture:
        kwargs["capture_output"] = True
    return subprocess.run(cmd, **kwargs)


def popen_text(cmd, *, cwd=None, env=None, extra_args=None):
    """Start a subprocess with text output, suitable for real-time stdout reading.

    Args:
        cmd: Command as a list of strings.
        cwd: Working directory.
        env: Extra environment variables (merged with base).
        extra_args: Extra keyword arguments passed to Popen (e.g., bufsize).

    Returns:
        subprocess.Popen with stdout=PIPE, stderr=STDOUT, text mode.
    """
    kwargs = {
        "stdout": subprocess.PIPE,
        "stderr": subprocess.STDOUT,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
        "cwd": cwd,
        "env": _merge_env(env),
        "startupinfo": _win_startupinfo(),
        "creationflags": _win_creationflags(),
    }
    if extra_args:
        kwargs.update(extra_args)
    return subprocess.Popen(cmd, **kwargs)


def kill_process(p):
    """Terminate/kill a subprocess cross-platform, including children.

    Args:
        p: A subprocess.Popen instance.
    """
    if p is None or p.poll() is not None:
        return
    try:
        if _IS_WIN:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(p.pid)],
                capture_output=True,
                creationflags=_win_creationflags(),
            )
        else:
            p.terminate()
            try:
                p.wait(timeout=3)
            except subprocess.TimeoutExpired:
                p.kill()
    except Exception:
        try:
            p.kill()
        except Exception:
            pass
