"""Tests for commitmint.choose_pair: joint word-pair selection that minimizes code
length first, then prefers alliteration (free only), then avoids double-plurals,
while keeping the hex-safety and distinctness guarantees."""
import commitmint
import commitword as sw


def _rank(*pools):
    words = []
    for p in pools:
        for w in p:
            if w not in words:
                words.append(w)
    return {w: i for i, w in enumerate(words)}


def test_prefers_shorter_total_length_over_free_alliteration():
    # 'go'+'out' (len 5, no alliteration) beats 'go'+'grand' (len 7, alliterates):
    # length is dominant, alliteration must never lengthen a code.
    w1pool = ["go", "tin"]
    w2pool = ["out", "grand"]
    rank = _rank(w1pool, w2pool)
    w1, w2, allit, dbl = commitmint.choose_pair(w1pool, w2pool, rank, set())
    assert (w1, w2) == ("go", "out")
    assert allit is False


def test_alliterates_when_free():
    # All pairs are length 6; only 'gap'+'gum' shares a first letter -> pick it.
    w1pool = ["gap", "tin"]
    w2pool = ["gum", "oak"]
    rank = _rank(w1pool, w2pool)
    w1, w2, allit, dbl = commitmint.choose_pair(w1pool, w2pool, rank, set())
    assert (w1, w2) == ("gap", "gum")
    assert allit is True


def test_avoids_double_plural_when_free():
    # No alliterating pair; among equal-length pairs prefer not-both-plural.
    wordset = {"cat", "cats", "mug", "mugs", "rope", "silk"}
    w1pool = ["cats", "rope"]
    w2pool = ["mugs", "silk"]
    rank = _rank(w1pool, w2pool)
    w1, w2, allit, dbl = commitmint.choose_pair(w1pool, w2pool, rank, wordset)
    assert dbl is False
    assert not (commitmint.is_plural(w1, wordset) and commitmint.is_plural(w2, wordset))


def test_alliteration_outranks_plural_limit():
    # Priority is length, THEN alliteration, THEN plural-limit: an alliterating
    # double-plural pair beats a non-alliterating clean pair at equal length.
    wordset = {"cat", "cats", "car", "cars", "rope", "silk"}
    w1pool = ["cats", "rope"]
    w2pool = ["cars", "silk"]   # cats+cars: alliterates (c) AND double-plural
    rank = _rank(w1pool, w2pool)
    w1, w2, allit, dbl = commitmint.choose_pair(w1pool, w2pool, rank, wordset)
    assert (w1, w2) == ("cats", "cars")
    assert allit is True and dbl is True


def test_guarantees_hex_safety():
    # 'dead','face','beef' are all-hex; only 'good' is non-hex. Result must keep
    # at least one non-hex word.
    w1pool = ["dead", "face"]
    w2pool = ["beef", "good"]
    rank = _rank(w1pool, w2pool)
    w1, w2, allit, dbl = commitmint.choose_pair(w1pool, w2pool, rank, set())
    assert not (sw.is_hexlike(w1) and sw.is_hexlike(w2))


def test_reuses_word_only_as_last_resort():
    # When the only candidate in each slot is the same word, fall back to reuse.
    rank = _rank(["only"])
    w1, w2, allit, dbl = commitmint.choose_pair(["only"], ["only"], rank, set())
    assert (w1, w2) == ("only", "only")


def test_is_plural_ignores_non_plural_s_words():
    wordset = {"business", "across", "gift", "gifts", "box", "boxes"}
    assert commitmint.is_plural("gifts", wordset) is True
    assert commitmint.is_plural("boxes", wordset) is True
    assert commitmint.is_plural("business", wordset) is False   # 'busines' not in set
    assert commitmint.is_plural("across", wordset) is False
    assert commitmint.is_plural("gift", wordset) is False
