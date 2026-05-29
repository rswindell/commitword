import commitword as sw
import commitmint

WORDS = sw.load_words()
RANK = {w: i for i, w in enumerate(WORDS)}
WHASH = sw.word_hashes(WORDS)
SHA = "0e9127ed1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d"


def test_mint_two_word_when_unique():
    code = commitmint.mint(SHA, [SHA], WORDS, RANK, WHASH)
    import re
    assert re.fullmatch(r"[a-z]+\d+[a-z]+", code)     # two-word shape
    assert sw.decode_and_verify(code, SHA)


def _collider(sha, total):
    """A 40-hex sha sharing the top `total` bits of `sha` but diverging at bit `total`."""
    full = 160
    n = int(sha, 16)
    mask_top = ((1 << total) - 1) << (full - total)
    bitT = (n >> (full - total - 1)) & 1
    other = (n & mask_top) | ((1 - bitT) << (full - total - 1))
    return f"{other:040x}"


def test_mint_three_word_when_two_word_collides():
    y, k, _w1c, _w2c = sw.plan_twoword(SHA, WORDS, WHASH)
    total = y + k
    other = _collider(SHA, total)
    assert sw.sha_to_bits(other, total) == sw.sha_to_bits(SHA, total)   # collide at 2-word
    code = commitmint.mint(SHA, [SHA, other], WORDS, RANK, WHASH)
    import re
    assert re.fullmatch(r"[a-z]+\d+[a-z]+\d+[a-z]+", code)              # three-word shape
    assert sw.decode_and_verify(code, SHA)
    assert not sw.decode_and_verify(code, other)                        # resolves only SHA


def test_mint_min_words_forces_three():
    # min_words=3 must emit a three-word code even when a unique two-word code
    # exists, and it must verify, stay hex-safe, and pin strictly more bits.
    import re
    two = commitmint.mint(SHA, [SHA], WORDS, RANK, WHASH)
    three = commitmint.mint(SHA, [SHA], WORDS, RANK, WHASH, min_words=3)
    assert re.fullmatch(r"[a-z]+\d+[a-z]+", two)                 # default two-word
    assert re.fullmatch(r"[a-z]+\d+[a-z]+\d+[a-z]+", three)      # forced three-word
    assert sw.decode_and_verify(three, SHA)
    assert not all(c in "0123456789abcdef" for c in three)       # hex-safe
    assert sw.decode_to_bits(three)[0] > sw.decode_to_bits(two)[0]  # more bits


def test_mint_reach_floor_grows_third_word():
    # A floor set above any two-word code's reach (via a tiny pmax) leaves a
    # sub-floor two-word `best`. Default keeps it; reach_floor grows a third
    # word to climb toward the floor, pinning strictly more bits.
    import re
    hi = dict(growth=16.0, pmax=1e-13)        # floor ~48 bits, > any 2-word code
    two = commitmint.mint(SHA, [SHA], WORDS, RANK, WHASH, **hi)
    three = commitmint.mint(SHA, [SHA], WORDS, RANK, WHASH, **hi, reach_floor=True)
    assert re.fullmatch(r"[a-z]+\d+[a-z]+", two)                 # default: two-word
    assert re.fullmatch(r"[a-z]+\d+[a-z]+\d+[a-z]+", three)      # reach_floor: three-word
    assert sw.decode_and_verify(three, SHA)
    assert sw.decode_to_bits(three)[0] > sw.decode_to_bits(two)[0]


def test_mint_reach_floor_noop_when_two_word_clears_floor():
    # With the default (low) floor, a two-word code already clears it, so
    # reach_floor changes nothing.
    import re
    two = commitmint.mint(SHA, [SHA], WORDS, RANK, WHASH)
    same = commitmint.mint(SHA, [SHA], WORDS, RANK, WHASH, reach_floor=True)
    assert re.fullmatch(r"[a-z]+\d+[a-z]+", same)
    assert same == two


def test_mint_output_is_hex_safe():
    code = commitmint.mint(SHA, [SHA], WORDS, RANK, WHASH)
    assert not all(c in "0123456789abcdef" for c in code)               # has a g-z letter


import hashlib

_REPO = [SHA] + [hashlib.sha1(str(i).encode()).hexdigest() for i in range(400)]


def test_mint_clears_margin_floor():
    code = commitmint.mint(SHA, _REPO, WORDS, RANK, WHASH)
    assert sw.decode_and_verify(code, SHA)
    total = sw.decode_to_bits(code)[0]
    floor = max(commitmint.margin_floor(len(_REPO)), sw.Y_MIN + sw.K_MIN)
    assert total >= floor                                               # margin respected


def test_mint_no_longer_than_maxbits_encoding():
    # shortest-at-floor must never be longer than the old max-bits two-word code,
    # since that code is itself a candidate in the search (>= floor, unique here).
    minted = commitmint.mint(SHA, _REPO, WORDS, RANK, WHASH)
    w1, y, w2, k = sw.encode(SHA, WORDS, RANK, WHASH)
    maxbits = sw.format_two(w1, y, w2, k)
    assert len(minted) <= len(maxbits)
