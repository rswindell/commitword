import pytest
import commitword as sw

WORDS = sw.load_words()
WHASH = None


def whash():
    global WHASH
    if WHASH is None:
        WHASH = sw.word_hashes(WORDS)
    return WHASH


def test_word_hashes_cover_list():
    wh = whash()
    assert len(wh) == len(WORDS)
    assert all(0 <= v < (1 << sw.PROBE) for v in wh.values())


def test_match_len_at_offset_zero_is_prefix():
    # match at offset 0 equals common prefix of word hash vs target top bits
    sha = "abcdef0123456789abcdef0123456789abcdef01"
    target = sw.sha_to_bits(sha, sw.PROBE)
    w = WORDS[0]
    h = sw.hash_bits(w, sw.PROBE)
    assert sw.match_len_at(h, target, 0) == sw.common_prefix_bits(target, h, sw.PROBE)


def test_is_hexlike():
    assert sw.is_hexlike("dead")
    assert sw.is_hexlike("beef")
    assert not sw.is_hexlike("threats")
    assert not sw.is_hexlike("thirty")


SAMPLE = [
    "0e9127ed1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d",
    "ffffffffffffffffffffffffffffffffffffffff",
    "1234567890abcdef1234567890abcdef12345678",
    "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
]


def _greedy_total(sha):
    target = sw.sha_to_bits(sha, sw.PROBE)
    y = max(sw.match_len_at(WHASH[w], target, 0) for w in WORDS)
    y = max(y, sw.Y_MIN)
    k = max(min(sw.match_len_at(WHASH[w], target, y), sw.K_MAX) for w in WORDS)
    return y + k


def test_plan_twoword_joint_ge_greedy():
    whash()
    for sha in SAMPLE:
        y, k, w1c, w2c = sw.plan_twoword(sha, WORDS, WHASH)
        assert y + k >= _greedy_total(sha)
        assert w1c and w2c


def test_encode_roundtrip_verifies():
    whash()
    for sha in SAMPLE:
        w1, y, w2, k = sw.encode(sha, WORDS)
        code = sw.format_two(w1, y, w2, k)
        assert sw.decode_and_verify(code, sha)


def test_select_words_hex_safe_swaps():
    # both slots' top picks are hexlike -> a g-z candidate is substituted in.
    # Self-contained words/rank so the test never depends on curated.txt content.
    words = ["dead", "beef", "carbon", "thirty"]
    rank = {w: i for i, w in enumerate(words)}      # dead=0, beef=1, carbon=2, thirty=3
    chosen = sw.select_words([["dead", "carbon"], ["beef", "thirty"]], rank)
    assert any(not sw.is_hexlike(w) for w in chosen)  # 'carbon' forced in
    assert len(set(chosen)) == len(chosen)            # no duplicate word


def test_select_words_prefers_distinct_when_constrained():
    # slot1 has only 'mirror'; most-constrained-first must give it to slot1,
    # so slot0 takes a distinct word instead of duplicating 'mirror'.
    words = ["mirror", "bravo", "carbon"]
    rank = {w: i for i, w in enumerate(words)}      # mirror=0, bravo=1, carbon=2
    chosen = sw.select_words([["mirror", "bravo"], ["mirror"]], rank)
    assert chosen == ["bravo", "mirror"]
    assert len(set(chosen)) == 2


def test_plan_third_extends_prefix():
    whash()
    sha = SAMPLE[0]
    y, k, _w1c, _w2c = sw.plan_twoword(sha, WORDS, WHASH)
    res = sw.plan_third(sha, WORDS, WHASH, y, k)
    assert res is not None
    m, w3c = res
    assert sw.M_MIN <= m <= sw.M_MAX
    assert w3c


def test_format_three_roundtrip_verifies():
    whash()
    sha = SAMPLE[0]
    rank = {w: i for i, w in enumerate(WORDS)}
    y, k, w1c, w2c = sw.plan_twoword(sha, WORDS, WHASH)
    m, w3c = sw.plan_third(sha, WORDS, WHASH, y, k)
    w1, w2, w3 = sw.select_words([w1c, w2c, w3c], rank)
    code = sw.format_three(w1, y, w2, k, w3, m)
    assert sw.decode_and_verify(code, sha)
    # three-word shape: two digit groups
    import re
    assert re.fullmatch(r"[a-z]+\d+[a-z]+\d+[a-z]+", code)
