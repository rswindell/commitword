#!/usr/bin/env python3
"""
Reverse lookup: given a commitword code, find matching SHAs in a git repo.

Accepts two-word (threats29thirty) and three-word (threats49thirty4carbon)
forms; case-insensitive.

Searches all refs by default (matching commitmint's mint scope); --head-only
restricts to HEAD's history.

usage: commitfind.py <code> [--repo PATH] [--head-only]
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
    ap.add_argument("--repo", default=".", help="path to git repo (default: cwd)")
    ap.add_argument("--head-only", action="store_true",
                    help="search only HEAD's history, not all refs "
                         "(default searches all refs, matching commitmint's mint scope)")
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
        print(f"no matches (searched {total_bits}-bit pattern)")
        sys.exit(1)

    print(f"# matched {total_bits} bits, {len(matches)} commit(s):")
    for sha, subject in matches:
        print(f"{sha[:12]} {subject}")


if __name__ == "__main__":
    main()
