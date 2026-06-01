"""Cross-validation tests for git-word.pl, the Perl consumer build: it must
decode/resolve commitwords identically to the Python tools (so a code minted by
commitmint.py resolves to the same commit), and pass-through must work. Skipped
where perl is unavailable."""
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
GWPL = ROOT / "git-word.pl"
MINT = ROOT / "commitmint.py"

pytestmark = pytest.mark.skipif(
    shutil.which("perl") is None or not GWPL.exists(),
    reason="perl / git-word.pl not available")


def _head():
    return subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                          capture_output=True, text=True, check=True).stdout.strip()


def _mint(*extra):
    return subprocess.run([sys.executable, str(MINT), "HEAD", "--repo", str(ROOT),
                           "--sep", *extra], capture_output=True, text=True,
                          check=True).stdout.strip()


def _pl(*args):
    # run from inside the repo so pass-through `git ...` sees the right repo
    return subprocess.run(["perl", str(GWPL), *args],
                          capture_output=True, text=True, cwd=str(ROOT))


def test_perl_resolves_python_minted_two_word():
    code = _mint()
    out = _pl(code)
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == _head()          # bit-identical decode -> same commit


def test_perl_resolves_python_minted_three_word():
    code = _mint("--min-words", "3")
    assert re.fullmatch(r"[a-z]+-\d+-[a-z]+-\d+-[a-z]+", code)
    out = _pl(code)
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == _head()


def test_perl_passthrough_resolves_commitword():
    code = _mint()
    out = _pl("show", "--no-patch", "--format=%H", code)
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == _head()


def test_perl_minting_is_refused():
    out = _pl("HEAD")                              # HEAD is a rev, not a commitword
    assert out.returncode != 0
    assert "mint" in out.stderr.lower()
