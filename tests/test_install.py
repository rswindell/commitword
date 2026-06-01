"""Tests for install.sh: it symlinks git-word into a chosen dir, the symlink
runs the bridge, non-symlinks are never clobbered, and --uninstall removes only
our links. POSIX/bash only."""
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
INSTALL = ROOT / "install.sh"

pytestmark = pytest.mark.skipif(
    os.name != "posix" or not INSTALL.exists(),
    reason="install.sh / POSIX only")


def _run(*args):
    return subprocess.run(["bash", str(INSTALL), *args],
                          capture_output=True, text=True)


def test_install_run_and_uninstall(tmp_path):
    bind = tmp_path / "bin"
    r = _run("--dir", str(bind), "cw")
    assert r.returncode == 0, r.stderr
    gw, gcw = bind / "git-word", bind / "git-cw"
    assert gw.is_symlink() and gcw.is_symlink()
    assert os.path.realpath(gw) == str((ROOT / "git-word").resolve())

    # the installed symlink actually runs the bridge (mints HEAD)
    out = subprocess.run([str(gw), "HEAD", "-C", str(ROOT)],
                         capture_output=True, text=True)
    assert out.returncode == 0 and out.stdout.strip()

    r = _run("--dir", str(bind), "--uninstall")
    assert r.returncode == 0, r.stderr
    assert not gw.exists() and not gcw.exists()


def test_install_never_clobbers_a_real_file(tmp_path):
    bind = tmp_path / "bin"
    bind.mkdir()
    real = bind / "git-keep"
    real.write_text("important")
    r = _run("--dir", str(bind), "keep")            # ask to install verb "keep"
    assert r.returncode == 0
    assert real.read_text() == "important"          # left untouched
    assert not real.is_symlink()
