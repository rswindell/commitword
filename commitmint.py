#!/usr/bin/env python3
"""Repo-aware commitword minting: emit the SHORTEST word code that resolves to
exactly one commit in the target repo, preferring codes that clear a (soft)
growth-margin bit floor. Two-word when a unique one exists, else a three-word
tail.

usage: commitmint.py <sha-or-ref> [--repo PATH] [--growth N] [--pmax P]
"""

import argparse
import math
import subprocess
import sys

import commitword as sw

# Cap on the word-1 prefix bits (`y`) the two-word search scans. `ybest`, the
# best single-word match against the SHA, is almost never large -- a word
# sharing >45 leading bits has probability ~ len(words) * 2^-45, vanishing -- so
# this only bounds the loop defensively. Any code pinning near 45 bits is far
# past every realistic growth-margin floor anyway.
Y_SEARCH_MAX = 45


def repo_shas(repo):
    out = subprocess.check_output(["git", "-C", repo, "rev-list", "--all"], text=True)
    return out.split()


def margin_floor(num_commits, growth=16.0, pmax=0.1):
    """Minimum identifying bits: stay <pmax-likely to collide after `growth`x
    repo growth. L_req = ceil(log2(M) + log2(growth / pmax))."""
    m = max(num_commits, 1)
    return math.ceil(math.log2(m) + math.log2(growth / pmax))


def _prefix_counts(shas, lo, hi):
    """counts[total][prefix] = number of shas sharing that top-`total`-bit prefix
    (for total in lo..hi, capped at 64-bit precision)."""
    counts = {t: {} for t in range(lo, hi + 1)}
    for s in shas:
        n = int(s[:16], 16)                  # top 64 bits; hi is capped <= 60
        for t in range(lo, hi + 1):
            v = n >> (64 - t)
            d = counts[t]
            d[v] = d.get(v, 0) + 1
    return counts


def is_plural(word, wordset):
    """True if `word` is the plural of a word also present in `wordset` (so
    `gifts`/`boxes` count, but `business`/`across` do not -- their singular form
    is not a word). The same near-duplicate test used to curate the list.

    Conservative by design, so it *under*-detects: a plural whose singular was
    excluded from the list isn't flagged -- e.g. `ends` (the 3-letter `end` is
    dropped by curate.py's >=4 length floor), or a plural of a blocklisted word.
    Acceptable because this only feeds a soft tie-breaker (avoid two-plural codes
    when free); a missed plural at worst leaves a code reading as two plurals."""
    return ((word.endswith("s") and word[:-1] in wordset)
            or (word.endswith("es") and word[:-2] in wordset))


def choose_pair(w1pool, w2pool, rank, wordset):
    """Pick (w1, w2) jointly from the two candidate pools, returning
    (w1, w2, alliterates, double_plural).

    Preference order: shortest total word length (so the code never grows for an
    aesthetic), then alliteration (shared first letter) *only when free*, then
    not-both-plural, then commoner words, then lexical (determinism). Prefers a
    distinct, hex-safe pair (>=1 word outside a-f); reuses a word or accepts an
    all-hex pair only when no better option exists.

    Pools at a given (y, k) are tiny (matching >=10 bits is ~1-in-1024), so the
    full cross product is cheap.
    """
    def search(require_distinct, require_hexsafe):
        best = None
        for a in w1pool:
            for b in w2pool:
                if require_distinct and a == b:
                    continue
                if require_hexsafe and sw.is_hexlike(a) and sw.is_hexlike(b):
                    continue
                allit = a[0] == b[0]
                dbl = is_plural(a, wordset) and is_plural(b, wordset)
                key = (len(a) + len(b), 0 if allit else 1, 0 if not dbl else 1,
                       rank[a] + rank[b], a, b)
                if best is None or key < best[0]:
                    best = (key, a, b, allit, dbl)
        return best

    best = (search(True, True) or search(True, False)
            or search(False, True) or search(False, False))
    if best is None:
        return None
    _key, a, b, allit, dbl = best
    return (a, b, allit, dbl)


def mint(sha_hex, shas, words, rank, whash, growth=16.0, pmax=0.1, min_words=2,
         reach_floor=False):
    """Shortest unique-in-`shas` code for `sha_hex` that clears the growth-margin
    floor. `shas` must include `sha_hex`.

    Two independent ways to spend a third word for more future-collision
    headroom:
    - `min_words=3` forces a (maximum-bit) three-word code unconditionally, even
      when a unique two-word code exists.
    - `reach_floor=True` promotes the otherwise-soft margin floor to a gate:
      grow a third word *only when* the best unique two-word code sits below the
      floor (`--growth`/`--pmax` set where the floor is). If a three-word code
      can't be built, the unique sub-floor two-word code is kept.

    With both defaults (min_words=2, reach_floor=False) the floor stays a soft
    preference: two words when possible, three only when no unique two-word code
    exists."""
    floor = max(margin_floor(len(shas), growth, pmax), sw.Y_MIN + sw.K_MIN)
    target = sw.sha_to_bits(sha_hex, sw.PROBE)
    ml0 = {w: sw.match_len_at(whash[w], target, 0) for w in words}
    ybest = max(ml0.values())
    if ybest < sw.Y_MIN:
        raise RuntimeError("no encoding: word1 matched < %d bits" % sw.Y_MIN)

    hi = min(ybest + sw.K_MAX + sw.M_MAX, 60)
    counts = _prefix_counts(shas, sw.Y_MIN + sw.K_MIN, hi)

    def unique(total):
        exp = sw.sha_to_bits(sha_hex, total)
        c = counts.get(total)
        if c is not None:
            return c.get(exp, 0) == 1
        return sum(1 for s in shas if sw.sha_to_bits(s, total) == exp) == 1

    wordset = set(words)
    # short, then non-plural, then common (three-word slot selection)
    shortkey = lambda w: (len(w), is_plural(w, wordset), rank[w], w)

    # Two-word: among ALL unique-in-repo two-word codes, pick the shortest,
    # preferring those that clear the margin floor. The floor is a *soft*
    # preference, not a hard gate: a short unique sub-floor code beats growing a
    # third word just to reach the floor. Uniqueness is the only hard rule.
    # Skipped entirely when min_words forces a three-word code.
    best = None              # (floor?, len(code), allit?, dbl-plural?, -total, ranks, code)
    if min_words <= 2:
        for y in range(sw.Y_MIN, min(ybest, Y_SEARCH_MAX) + 1):
            w1pool = [w for w in words if ml0[w] >= y]
            if not w1pool:
                continue
            mly = {w: min(sw.match_len_at(whash[w], target, y), sw.K_MAX) for w in words}
            for k in range(sw.K_MIN, sw.K_MAX + 1):
                total = y + k
                if not unique(total):
                    continue
                w2pool = [w for w in words if mly[w] >= k]
                if not w2pool:
                    continue
                pair = choose_pair(w1pool, w2pool, rank, wordset)
                if pair is None:
                    continue
                w1, w2, allit, dbl = pair
                code = sw.format_two(w1, y, w2, k)
                # prefer: clears floor, then shorter, then alliterates, then not
                # double-plural (both aesthetics free -- ranked below length), then
                # MORE bits (free margin), then commoner words, then lexicographic
                cand = (0 if total >= floor else 1, len(code),
                        0 if allit else 1, 0 if not dbl else 1,
                        -total, rank[w1] + rank[w2], code)
                if best is None or cand < best:
                    best = cand
    # Keep the two-word code unless reach_floor wants to climb a below-floor one
    # (best[0] == 1 means "below floor"). min_words >= 3 leaves best None here.
    if best is not None and not (reach_floor and best[0] == 1):
        return _checked(best[-1], sha_hex)

    # Three-word code (more bits): forced by min_words, or no unique two-word
    # code exists, or reach_floor is climbing a sub-floor two-word code.
    y, k, w1c, w2c = sw.plan_twoword(sha_hex, words, whash)
    third = sw.plan_third(sha_hex, words, whash, y, k)
    if third is not None:
        m, w3c = third
        if unique(y + k + m):
            w1, w2, w3 = sw.select_words([w1c, w2c, w3c], rank, key=shortkey)
            return _checked(sw.format_three(w1, y, w2, k, w3, m), sha_hex)

    # No valid three-word code. If reach_floor left a unique sub-floor two-word
    # code in hand, keep it; otherwise there is genuinely no encoding.
    if best is not None:
        return _checked(best[-1], sha_hex)
    raise RuntimeError("no unique commitword: three-word code unavailable")


def _checked(code, sha_hex):
    """Self-verify a minted code before returning it: it must decode and verify
    against its own SHA (also catches the hex-safety guarantee -- an all-hex code
    would decode to None and fail to verify)."""
    if not sw.decode_and_verify(code, sha_hex):
        raise RuntimeError(f"minted code {code!r} does not verify (internal error)")
    return code


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sha", help="commit SHA or ref to mint")
    ap.add_argument("--repo", default=".", help="path to git repo (default: cwd)")
    ap.add_argument("--growth", type=float, default=16.0,
                    help="repo-growth factor for the margin floor (default 16)")
    ap.add_argument("--pmax", type=float, default=0.1,
                    help="max future-collision probability for the floor (default 0.1)")
    ap.add_argument("--min-words", type=int, choices=(2, 3), default=2,
                    help="minimum words in the code; 3 forces a three-word code "
                         "for extra future-uniqueness headroom (default 2)")
    ap.add_argument("--reach-floor", action="store_true",
                    help="grow a third word when a two-word code can't clear the "
                         "margin floor (default: floor is a soft preference)")
    ap.add_argument("--sep", choices=("-", "_", "."), default=None,
                    help="insert this separator at word/number boundaries for "
                         "readability, e.g. what-9-plug (default: none/canonical)")
    args = ap.parse_args()
    try:
        full = subprocess.check_output(
            ["git", "-C", args.repo, "rev-parse", "--verify", args.sha],
            text=True, stderr=subprocess.DEVNULL).strip()
    except subprocess.CalledProcessError:
        print(f"error: cannot resolve {args.sha!r} in repo {args.repo}", file=sys.stderr)
        sys.exit(2)
    words = sw.load_words()
    rank = {w: i for i, w in enumerate(words)}
    whash = sw.word_hashes(words)
    shas = repo_shas(args.repo)
    if full not in shas:
        shas.append(full)
    code = mint(full, shas, words, rank, whash, args.growth, args.pmax,
                args.min_words, args.reach_floor)
    print(sw.separate(code, args.sep) if args.sep else code)


if __name__ == "__main__":
    main()
