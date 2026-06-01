#!/usr/bin/env python3
"""
SHA -> memorable word encoding.

Two-word form `<word1><N1><word2>` and three-word form
`<word1><N1><word2><N2><word3>`:
  - word1: longest-prefix match of sha1(word) against the target's top bits (y bits)
  - word2: sha1(word)'s top k bits equal target[y : y+k]
  - word3 (three-word): sha1(word)'s top m bits equal target[y+k : y+k+m]
  - N1 packs (y, k); N2 packs m. Plain integers, no zero-padding.

Encode jointly maximizes y+k. Decode (case-insensitive) re-derives the bits from
the words and verifies against a candidate SHA. Repo-aware minting lives in
commitmint.py; reverse lookup in commitfind.py.
"""

import argparse
import hashlib
import os
import re
import sys
from pathlib import Path

HASH_NAME = os.environ.get("COMMITWORD_HASH", "sha1")
_DEFAULT_LIST = Path(__file__).resolve().parent / "curated.txt"
WORDLIST_PATH = Path(os.environ.get("COMMITWORD_LIST", str(_DEFAULT_LIST)))

PROBE = 80                      # bits of hash/target exposed to matching
Y_MIN = 10                      # word1 minimum prefix bits (no Y maximum)
K_MIN, K_MAX = 10, 18           # word2 slice bits
K_SPAN = K_MAX - K_MIN + 1      # 9
M_MIN, M_MAX = 8, 24            # word3 slice bits (M_MIN guarantees a candidate)

HEX_LETTERS = frozenset("abcdef")


def load_words(path=WORDLIST_PATH):
    """Lowercase a-z only, length 3..10, no possessives/proper nouns leaking in."""
    words = []
    seen = set()
    for line in path.read_text().splitlines():
        w = line.strip().lower()
        if not (3 <= len(w) <= 10):
            continue
        if not w.isalpha() or not w.isascii():
            continue
        if w in seen:
            continue
        seen.add(w)
        words.append(w)
    return words


def _leading_bits(digest, nbits):
    """First `nbits` of a big-endian byte string, as a left-aligned int."""
    n_bytes = (nbits + 7) // 8
    v = int.from_bytes(digest[:n_bytes], "big")
    return v >> (n_bytes * 8 - nbits)


def hash_bits(word, nbits=64):
    """Return the first nbits of HASH_NAME(word) as an int (left-aligned)."""
    return _leading_bits(hashlib.new(HASH_NAME, word.encode()).digest(), nbits)


def sha_to_bits(sha_hex, nbits):
    """First nbits of a hex string, as int."""
    return _leading_bits(bytes.fromhex(sha_hex), nbits)


def common_prefix_bits(a, b, max_bits):
    """How many leading bits are equal in a and b, each of length max_bits."""
    x = a ^ b
    if x == 0:
        return max_bits
    # bit_length of x tells us position of highest differing bit
    return max_bits - x.bit_length()


def word_hashes(words):
    """Precompute each word's top-PROBE hash bits as an int."""
    return {w: hash_bits(w, PROBE) for w in words}


def match_len_at(whash_val, target, offset):
    """Leading bits of `whash_val` equal to `target` starting at MSB `offset`."""
    aligned = (target << offset) & ((1 << PROBE) - 1)
    return common_prefix_bits(aligned, whash_val, PROBE)


def is_hexlike(word):
    """True if the word is composed only of hex letters (a-f) -> looks like hex."""
    return all(c in HEX_LETTERS for c in word)


def plan_twoword(sha_hex, words, whash):
    """Joint-maximize y+k. Return (y, k, w1_candidates, w2_candidates) or None."""
    target = sha_to_bits(sha_hex, PROBE)
    plens = [(match_len_at(whash[w], target, 0), w) for w in words]
    y_best = max(p for p, _ in plens)
    if y_best < Y_MIN:
        return None
    best = None                       # (total, y, k, w1_cands, w2_cands)
    for y in range(Y_MIN, y_best + 1):
        w1_cands = [w for p, w in plens if p >= y]
        mlens = [(min(match_len_at(whash[w], target, y), K_MAX), w) for w in words]
        k = max(ml for ml, _ in mlens)
        if k < K_MIN:
            continue
        w2_cands = [w for ml, w in mlens if ml >= k]
        total = y + k
        if best is None or total > best[0]:
            best = (total, y, k, w1_cands, w2_cands)
    if best is None:
        return None
    _total, y, k, w1_cands, w2_cands = best
    return (y, k, w1_cands, w2_cands)


def select_words(cand_lists, rank, key=None):
    """Best word per slot, deduped, guaranteeing >=1 non-hexlike word.

    `key` maps a word to a sort value (lowest is preferred); it defaults to
    frequency rank. Pass e.g. ``lambda w: (len(w), rank[w], w)`` to prefer the
    shortest word (ties broken by commonness, then alphabetically).

    Fills the most-constrained slot (fewest candidates) first, so a slot whose
    only candidate is some word `w` claims `w` before a larger slot can take it,
    avoiding forced duplicates. Falls back to reusing a word only when a slot has
    no distinct candidate left. Precondition: every candidate list is non-empty.
    """
    if key is None:
        key = lambda w: rank[w]
    order = sorted(range(len(cand_lists)), key=lambda i: len(cand_lists[i]))
    chosen = [None] * len(cand_lists)
    used = set()
    for i in order:
        pool = [w for w in cand_lists[i] if w not in used] or cand_lists[i]
        w = min(pool, key=key)
        chosen[i] = w
        used.add(w)
    if all(is_hexlike(w) for w in chosen):
        for i in order:
            others = used - {chosen[i]}
            pool = [w for w in cand_lists[i] if not is_hexlike(w) and w not in others]
            if pool:
                used.discard(chosen[i])
                chosen[i] = min(pool, key=key)
                used.add(chosen[i])
                break
    return chosen


def encode(sha_hex, words, rank=None, whash=None):
    """Standalone (no-repo) two-word encode. Return (w1, y, w2, k) or None.

    Best-effort: it joint-maximizes bits and lets select_words avoid an all-hex
    pair, but does not guarantee repo-uniqueness or re-verify its output. The
    guaranteed path is commitmint.mint, which checks uniqueness and decode-
    verifies (enforcing hex-safety) before returning."""
    if rank is None:
        rank = {w: i for i, w in enumerate(words)}
    if whash is None:
        whash = word_hashes(words)
    plan = plan_twoword(sha_hex, words, whash)
    if plan is None:
        return None
    y, k, w1c, w2c = plan
    w1, w2 = select_words([w1c, w2c], rank)
    return (w1, y, w2, k)


def pack1(y, k):
    return (y - Y_MIN) * K_SPAN + (k - K_MIN)


def unpack1(n):
    return (n // K_SPAN + Y_MIN, n % K_SPAN + K_MIN)


def pack2(m):
    return m - M_MIN


def unpack2(n):
    return n + M_MIN


def format_two(w1, y, w2, k):
    return f"{w1}{pack1(y, k)}{w2}"


def plan_third(sha_hex, words, whash, y, k):
    """Best third word on the slice after y+k. Return (m, w3_candidates) or None."""
    target = sha_to_bits(sha_hex, PROBE)
    offset = y + k
    mlens = [(min(match_len_at(whash[w], target, offset), M_MAX), w) for w in words]
    m = max(ml for ml, _ in mlens)
    if m < M_MIN:
        return None
    w3_cands = [w for ml, w in mlens if ml >= m]
    return (m, w3_cands)


def format_three(w1, y, w2, k, w3, m):
    return f"{w1}{pack1(y, k)}{w2}{pack2(m)}{w3}"


def separate(code, sep):
    """Insert `sep` at each word/number boundary of a canonical code, for
    readable display ("what9plug" -> "what-9-plug"). Decoders ignore separators
    (see decode_to_bits, SPEC §3.4), so the decorated form resolves identically.
    `sep` should be an accepted separator character (one of `_SEP`)."""
    return re.sub(r"(?<=[a-z])(?=[0-9])|(?<=[0-9])(?=[a-z])", sep, code)


# Optional, ignored separators a human may insert at word/number boundaries for
# readability ("what-9-plug" == "what9plug"). They are stripped for the
# hex-safety test and excluded from the parsed tokens; the canonical (minted)
# form has none. The anchored grammars accept only a single boundary separator
# -- leading, trailing, doubled, and intra-token separators do not match, so the
# input is "not a commitword" (SPEC §3.4).
_SEP = "-_"
_STRIP_SEP = str.maketrans("", "", _SEP)

_RE_TWO = re.compile(r"^([a-z]+)[-_]?(\d+)[-_]?([a-z]+)$")
_RE_THREE = re.compile(r"^([a-z]+)[-_]?(\d+)[-_]?([a-z]+)[-_]?(\d+)[-_]?([a-z]+)$")


def _top(h, n):
    return h >> (PROBE - n)


def decode_to_bits(encoded):
    """Parse a code -> (total_bits, expected_prefix_int), or None if malformed.
    Case-insensitive; optional '-'/'_' separators at word/number boundaries are
    ignored (SPEC §3.4). Input is lowercased before parsing."""
    s = encoded.strip().lower()
    bare = s.translate(_STRIP_SEP)
    # A genuine commitword always carries a g-z letter (encoder guarantee, §3.3).
    # An all-[0-9a-f] string (e.g. "dead12beef", or "dead-12-beef" once its
    # separators are stripped) is a raw SHA prefix, not our code -- reject it so
    # the caller can treat it as a SHA instead of mis-parsing it as word/N/word.
    if not bare or all(c in "0123456789abcdef" for c in bare):
        return None
    m3 = _RE_THREE.match(s)
    if m3:
        w1, n1, w2, n2, w3 = m3.groups()
        y, k = unpack1(int(n1))
        m = unpack2(int(n2))
        total = y + k + m
        if total > PROBE:        # a valid code never pins more than PROBE bits (§2.1)
            return None
        expected = ((_top(hash_bits(w1, PROBE), y) << (k + m))
                    | (_top(hash_bits(w2, PROBE), k) << m)
                    | _top(hash_bits(w3, PROBE), m))
        return (total, expected)
    m2 = _RE_TWO.match(s)
    if m2:
        w1, n1, w2 = m2.groups()
        y, k = unpack1(int(n1))
        total = y + k
        if total > PROBE:        # a valid code never pins more than PROBE bits (§2.1)
            return None
        expected = (_top(hash_bits(w1, PROBE), y) << k) | _top(hash_bits(w2, PROBE), k)
        return (total, expected)
    return None


def decode_and_verify(encoded, sha_hex):
    """Parse the encoding, verify it matches the candidate SHA. Returns bool."""
    decoded = decode_to_bits(encoded)
    if decoded is None:
        return False
    total, expected = decoded
    return sha_to_bits(sha_hex, total) == expected


def main():
    ap = argparse.ArgumentParser(
        description="Standalone commitword encoder: render each commit SHA (hex) "
                    "as a word code. No repo and no uniqueness guarantee -- it just "
                    "joint-maximizes the pinned bits, always as a two-word code "
                    "(the rare three-word form exists only to keep a repo-minted "
                    "code unique, so it comes from commitmint.py). Use commitmint.py "
                    "for repo-unique codes and commitfind.py to resolve one.")
    ap.add_argument("sha", nargs="+", help="commit SHA(s) in hex to encode")
    args = ap.parse_args()

    words = load_words()
    rank = {w: i for i, w in enumerate(words)}
    whash = word_hashes(words)
    print(f"# loaded {len(words)} words ({HASH_NAME})", file=sys.stderr)
    rc = 0
    for sha in args.sha:
        sha = sha.lower()
        try:
            result = encode(sha, words, rank, whash)
        except ValueError:                      # not valid hex (e.g. odd length)
            print(f"error: {sha!r} is not a hex SHA", file=sys.stderr)
            rc = 2
            continue
        if result is None:
            print(f"{sha[:12]}...\tNO_ENCODING")
            continue
        w1, y, w2, k = result
        code = format_two(w1, y, w2, k)
        ok = decode_and_verify(code, sha)
        print(f"{sha[:12]}...\t{code}\t(y={y}, k={k}, total={y + k})\tverify={'OK' if ok else 'FAIL'}")
    sys.exit(rc)


if __name__ == "__main__":
    main()
