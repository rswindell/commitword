#!/usr/bin/env python3
"""
Reverse lookup: resolve a commitword code to the commit(s) it names -- the
word-code analogue of resolving an abbreviated SHA with `git show <prefix>`.

Accepts two-word (threats29thirty) and three-word (threats49thirty4carbon)
forms; case-insensitive.

Searches all refs by default (`--all`), matching commitmint's mint scope, so it
inherits the minter's "exactly one commit" guarantee -- just as `git show
<prefix>` disambiguates a short SHA repo-wide, not only within HEAD's history.
`--head-only` narrows to HEAD's history: a safe *subset* (it can never produce a
false match, but may find nothing if the target isn't reachable from HEAD).

usage: commitfind.py <code> [-C PATH] [--all | --head-only]
"""

import argparse
import subprocess
import sys

from commitword import decode_to_bits, sha_to_bits


def git_all_shas(repo, all_refs):
    args = ["git", "-C", repo, "log", "--format=%H %s"]
    if all_refs:
        args.append("--all")
    out = subprocess.check_output(args, text=True)
    for line in out.splitlines():
        sha, _, subject = line.partition(" ")
        yield sha, subject


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("encoded", help="commitword code, e.g. threats29thirty or threats49thirty4carbon")
    ap.add_argument("-C", "--repo", default=".",
                    help="path to git repo (like git -C; default: cwd)")
    scope = ap.add_mutually_exclusive_group()
    scope.add_argument("--all", dest="head_only", action="store_false",
                       help="search all refs -- the default; reproduces "
                            "commitmint's mint scope, like 'git show <prefix>' "
                            "resolving a short SHA repo-wide")
    scope.add_argument("--head-only", dest="head_only", action="store_true",
                       help="narrow the search to HEAD's history (a safe subset: "
                            "faster, and robust if other refs grew since minting)")
    ap.add_argument("--sha", action="store_true",
                    help="output only the matching full SHA(s), one per line, so "
                         "the result composes: git show $(commitfind <code> --sha)")
    ap.set_defaults(head_only=False)
    args = ap.parse_args()

    decoded = decode_to_bits(args.encoded)
    if decoded is None:
        print(f"error: cannot parse encoding {args.encoded!r}", file=sys.stderr)
        sys.exit(2)
    total_bits, expected = decoded

    matches = []
    for sha, subject in git_all_shas(args.repo, all_refs=not args.head_only):
        if sha_to_bits(sha, total_bits) == expected:
            matches.append((sha, subject))

    if not matches:
        print(f"no matches (searched {total_bits}-bit pattern)",
              file=sys.stderr if args.sha else sys.stdout)
        sys.exit(1)

    if args.sha:                       # bare full SHA(s) for shell composition
        for sha, _subject in matches:
            print(sha)
        return

    print(f"# matched {total_bits} bits, {len(matches)} commit(s):")
    for sha, subject in matches:
        print(f"{sha[:12]} {subject}")


if __name__ == "__main__":
    main()
