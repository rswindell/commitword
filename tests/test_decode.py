import commitword as sw

WORDS = sw.load_words()
WHASH = sw.word_hashes(WORDS)
SHA = "0e9127ed1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d"


def test_decode_two_word():
    w1, y, w2, k = sw.encode(SHA, WORDS)
    code = sw.format_two(w1, y, w2, k)
    total, expected = sw.decode_to_bits(code)
    assert total == y + k
    assert expected == sw.sha_to_bits(SHA, total)


def test_decode_three_word():
    rank = {w: i for i, w in enumerate(WORDS)}
    y, k, w1c, w2c = sw.plan_twoword(SHA, WORDS, WHASH)
    m, w3c = sw.plan_third(SHA, WORDS, WHASH, y, k)
    w1, w2, w3 = sw.select_words([w1c, w2c, w3c], rank)
    code = sw.format_three(w1, y, w2, k, w3, m)
    total, expected = sw.decode_to_bits(code)
    assert total == y + k + m
    assert expected == sw.sha_to_bits(SHA, total)
    assert sw.decode_and_verify(code, SHA)


def test_decode_case_insensitive():
    w1, y, w2, k = sw.encode(SHA, WORDS)
    code = sw.format_two(w1, y, w2, k)
    assert sw.decode_to_bits(code.upper()) == sw.decode_to_bits(code)
    assert sw.decode_and_verify(code.title(), SHA)


def test_decode_rejects_garbage():
    assert sw.decode_to_bits("not-a-code") is None
    assert sw.decode_to_bits("deadbeef") is None        # all hex, no digit group split
    assert sw.decode_and_verify("xxx", SHA) is False


import re as _re


def _decorate(code, sep):
    """Insert `sep` at every letter<->digit boundary of a canonical code."""
    return _re.sub(r"(?<=[a-z])(?=[0-9])|(?<=[0-9])(?=[a-z])", sep, code)


def test_decode_accepts_boundary_separators():
    w1, y, w2, k = sw.encode(SHA, WORDS)
    code = sw.format_two(w1, y, w2, k)
    for sep in ("-", "_", "."):
        deco = _decorate(code, sep)
        assert deco != code
        assert sw.decode_to_bits(deco) == sw.decode_to_bits(code)
        assert sw.decode_and_verify(deco, SHA)
    # a separator on only one boundary is fine too
    one = code.replace(str(sw.pack1(y, k)), "-" + str(sw.pack1(y, k)), 1)
    assert sw.decode_to_bits(one) == sw.decode_to_bits(code)


def test_decode_accepts_separators_three_word():
    rank = {w: i for i, w in enumerate(WORDS)}
    y, k, w1c, w2c = sw.plan_twoword(SHA, WORDS, WHASH)
    m, w3c = sw.plan_third(SHA, WORDS, WHASH, y, k)
    w1, w2, w3 = sw.select_words([w1c, w2c, w3c], rank)
    code = sw.format_three(w1, y, w2, k, w3, m)
    deco = _decorate(code, ".")
    assert _re.fullmatch(r"[a-z]+\.\d+\.[a-z]+\.\d+\.[a-z]+", deco)
    assert sw.decode_and_verify(deco, SHA)


def test_decode_rejects_misplaced_separators():
    w1, y, w2, k = sw.encode(SHA, WORDS)
    code = sw.format_two(w1, y, w2, k)            # e.g. what9plug
    assert sw.decode_to_bits("-" + code) is None         # leading
    assert sw.decode_to_bits(code + "-") is None         # trailing
    assert sw.decode_to_bits(code[:2] + "-" + code[2:]) is None   # inside word 1
    doubled = _decorate(code, "-").replace("-", "--", 1)
    assert sw.decode_to_bits(doubled) is None            # doubled at boundary


def test_decode_rejects_hex_lookalike_with_separators():
    # strips to all-hex -> still a raw SHA prefix, not a commitword
    for s in ("dead-12-beef", "dead_12_beef", "dead.12.beef"):
        assert sw.decode_to_bits(s) is None
        assert sw.decode_and_verify(s, SHA) is False


def test_separate_roundtrips():
    w1, y, w2, k = sw.encode(SHA, WORDS)
    code = sw.format_two(w1, y, w2, k)
    for sep in ("-", "_", "."):
        deco = sw.separate(code, sep)
        assert deco == _decorate(code, sep)
        assert sw.decode_to_bits(deco) == sw.decode_to_bits(code)


def test_decode_rejects_out_of_range_numbers():
    # The grammar's \d+ is unbounded, but a real code never pins more than PROBE
    # bits (SPEC §2.1). An over-wide number must return None, not raise on the
    # negative shift in _top -- commitfind feeds untrusted CLI input here.
    for code in ("word999word", "alpha9999999beta", "one5gamma9999999delta"):
        assert sw.decode_to_bits(code) is None
        assert sw.decode_and_verify(code, SHA) is False


def test_decode_rejects_all_hex_lookalike():
    # An all-[0-9a-f] string is a raw SHA prefix, not a word code -- even when it
    # matches the word/N/word shape. dead12beef = dead/12/beef but is valid hex.
    # The encoder guarantees a g-z letter (hex-safety), so decode must refuse hex.
    assert sw.decode_to_bits("dead12beef") is None
    assert sw.decode_to_bits("a1b2c3d4") is None
    assert sw.decode_and_verify("dead12beef", SHA) is False
    # a real code (has g-z letters) still decodes fine
    w1, y, w2, k = sw.encode(SHA, WORDS)
    assert sw.decode_to_bits(sw.format_two(w1, y, w2, k)) is not None


def test_commitfind_decodes_three_word_form():
    # commitfind relies on decode_to_bits; assert a three-word code decodes to a
    # larger bit-width than the two-word code for the same sha.
    y, k, w1c, w2c = sw.plan_twoword(SHA, WORDS, WHASH)
    m, w3c = sw.plan_third(SHA, WORDS, WHASH, y, k)
    rank = {w: i for i, w in enumerate(WORDS)}
    w1, w2, w3 = sw.select_words([w1c, w2c, w3c], rank)
    two = sw.format_two(w1, y, w2, k)
    three = sw.format_three(w1, y, w2, k, w3, m)
    assert sw.decode_to_bits(three)[0] > sw.decode_to_bits(two)[0]
