"""Tests for the `git-word` bridge: bidirectional mint/resolve, run against this
repo. git-word execs commitmint.py / commitfind.py, so this also exercises the
flag pass-through and commitfind's --sha output."""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GITWORD = ROOT / "git-word"

CW = re.compile(r"[a-z]+\d+[a-z]+(?:\d+[a-z]+)?")     # two- or three-word shape


def _head():
    return subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                          capture_output=True, text=True, check=True).stdout.strip()


def _word(*args):
    return subprocess.run([sys.executable, str(GITWORD), *args, "-C", str(ROOT)],
                          capture_output=True, text=True)


def test_mint_then_resolve_roundtrips_to_head():
    minted = _word("HEAD")
    assert minted.returncode == 0, minted.stderr
    code = minted.stdout.strip()
    assert CW.fullmatch(code)                          # auto-minted a commitword

    resolved = _word(code)                             # auto-resolved direction
    assert resolved.returncode == 0, resolved.stderr
    assert resolved.stdout.strip() == _head()          # bare full SHA, round-trips


def test_no_argument_mints_head():
    assert _word().stdout.strip() == _word("HEAD").stdout.strip()


def test_short_sha_is_minted_not_resolved():
    # a hex prefix is not a commitword (hex-safety), so it's treated as a git
    # rev and minted -- output is a word, not a SHA.
    short = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"],
                           capture_output=True, text=True, check=True).stdout.strip()
    out = _word(short)
    assert out.returncode == 0, out.stderr
    assert CW.fullmatch(out.stdout.strip())


def test_force_find_needs_a_commitword():
    out = _word("--find", "HEAD")                      # HEAD isn't a commitword
    assert out.returncode != 0                         # commitfind rejects it


def _word_in_repo(*args):
    # pass-through runs `git <args>`, so -C must precede the subcommand; easiest
    # to just run from inside the repo (as a user would).
    return subprocess.run([sys.executable, str(GITWORD), *args],
                          capture_output=True, text=True, cwd=str(ROOT))


def test_passthrough_runs_git_with_resolved_commitword():
    # `git word show <commitword>` resolves the commitword, then runs git show.
    code = _word_in_repo("HEAD").stdout.strip()
    assert CW.fullmatch(code)
    out = _word_in_repo("show", "--no-patch", "--format=%H", code)
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == _head()               # ran `git show <the commit>`


def _rev(spec):
    return subprocess.run(["git", "-C", str(ROOT), "rev-parse", spec],
                          capture_output=True, text=True, check=True).stdout.strip()


def test_passthrough_resolves_commitword_inside_rev_expression():
    # a commitword embedded in a rev-expression (<cw>~1) is resolved in place.
    code = _word_in_repo("HEAD").stdout.strip()
    out = _word_in_repo("show", "--no-patch", "--format=%H", f"{code}~1")
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == _rev("HEAD~1")


def test_passthrough_leaves_real_refs_and_shas_alone():
    # HEAD is a ref, not a commitword -> git handles it; output is HEAD's sha.
    out = _word_in_repo("show", "--no-patch", "--format=%H", "HEAD")
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == _head()
