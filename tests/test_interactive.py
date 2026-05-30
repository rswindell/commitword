"""End-to-end tests for the `-i/--interactive` arrow-key picker.

The picker draws its menu on /dev/tty and prints only the chosen code to stdout.
These tests drive it through a pseudo-terminal: the child's controlling tty is a
pty (so /dev/tty works and arrow keys are read), while its stdout is a separate
pipe (so we can assert the menu never leaks onto stdout). POSIX-only.
"""
import os
import re
import select
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "commitmint.py"

pytestmark = pytest.mark.skipif(
    os.name != "posix" or not hasattr(os, "fork"),
    reason="interactive picker needs a POSIX pty")

try:
    import pty
except ImportError:                                   # pragma: no cover
    pty = None


def _choose(index):
    """Reference: the bare code the non-interactive --choose N prints."""
    out = subprocess.run(
        [sys.executable, str(SCRIPT), "HEAD", "--repo", str(ROOT),
         "--choose", str(index)],
        capture_output=True, text=True, check=True)
    return out.stdout.strip()


def _run_picker(keys):
    """Spawn `commitmint.py HEAD -i` under a pty, send the byte string `keys`
    once the menu has rendered, and return (stdout_text, exit_code). stdout is a
    pipe distinct from the tty, so it carries only the chosen code (if any)."""
    if pty is None:                                   # pragma: no cover
        pytest.skip("no pty module")
    r_out, w_out = os.pipe()
    exe = sys.executable
    pid, master = pty.fork()
    if pid == 0:                                      # child
        os.dup2(w_out, 1)                            # stdout -> pipe, not the tty
        os.close(r_out)
        os.close(w_out)
        os.execvp(exe, [exe, str(SCRIPT), "HEAD", "--repo", str(ROOT), "-i"])
        os._exit(127)                                # unreachable
    os.close(w_out)

    # Wait for the menu to render on the tty before sending keystrokes.
    deadline = time.time() + 5.0
    while time.time() < deadline:
        r, _, _ = select.select([master], [], [], 0.2)
        if r and os.read(master, 4096):
            break
    os.write(master, keys)

    out = b""
    while True:                                       # drain stdout; discard tty
        r, _, _ = select.select([r_out, master], [], [], 3.0)
        if not r:
            break
        done = False
        for f in r:
            try:
                chunk = os.read(f, 4096)
            except OSError:
                chunk = b""
            if f == r_out:
                if not chunk:
                    done = True
                else:
                    out += chunk
        if done:
            break
    _, status = os.waitpid(pid, 0)
    os.close(r_out)
    try:
        os.close(master)
    except OSError:
        pass
    code = os.waitstatus_to_exitcode(status)
    return out.decode("latin-1"), code


def test_interactive_enter_selects_default():
    # Enter with no movement picks index 0 -- the same code as the default mint.
    out, code = _run_picker(b"\r")
    assert code == 0
    assert "\x1b" not in out                          # no menu escapes on stdout
    assert out.strip() == _choose(0)


def test_interactive_down_selects_next():
    # Down then Enter selects index 1, matching --choose 1.
    out, code = _run_picker(b"\x1b[B\r")
    assert code == 0
    assert out.strip() == _choose(1)


def test_interactive_quit_cancels():
    # 'q' cancels: nonzero exit, nothing on stdout.
    out, code = _run_picker(b"q")
    assert code == 130
    assert out.strip() == ""
