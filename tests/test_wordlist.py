import commitword as sw
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BLOCKLIST = {
    w.strip().lower()
    for w in (ROOT / "blocklist.txt").read_text().splitlines()
    if w.strip() and not w.lstrip().startswith("#")
}


def test_blocklist_nonempty_and_clean():
    assert BLOCKLIST
    # every blocklist entry is a plain lowercase a-z word (so exact-match works)
    assert all(w.isalpha() and w.isascii() and w.islower() for w in BLOCKLIST)


def test_no_blocklisted_word_in_curated():
    words = set(sw.load_words())
    leaked = words & BLOCKLIST
    assert not leaked, f"blocklisted words leaked into curated.txt: {sorted(leaked)}"


def test_a_few_known_words_are_blocked():
    # spot-check that the words that motivated the blocklist are gone
    words = set(sw.load_words())
    for w in ("lesbians", "naked", "kill", "murder", "slave", "drug"):
        assert w not in words
