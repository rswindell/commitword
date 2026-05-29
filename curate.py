#!/usr/bin/env python3
"""Build a curated word list: google-10k ∩ american-english common nouns/verbs.

Regeneration tool (curated.txt ships pre-built). Needs the Debian/Ubuntu
`wamerican` dictionary at /usr/share/dict/american-english; override with the
CURATE_SYSDICT env var to point at another american-english word list."""
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
SYSDICT = Path(os.environ.get("CURATE_SYSDICT", "/usr/share/dict/american-english")).read_text().splitlines()
GOOGLE = (HERE / "google-10000.txt").read_text().splitlines()

# Set of lowercase entries in sysdict
lower = set()
upper = set()
for w in SYSDICT:
    w = w.strip()
    if not w.isascii() or not w.isalpha():
        continue
    if w[0].isupper():
        upper.add(w.lower())
    else:
        lower.add(w)

# A "clean common-noun-ish" word: appears lowercased in sysdict, AND not also as a proper noun
clean_dict = lower - upper

# Words to exclude so minted codes read neutral/pleasant (see blocklist.txt).
# Whole-word, case-insensitive, exact match; # lines and blanks ignored.
BLOCKLIST = {
    w.strip().lower()
    for w in (HERE / "blocklist.txt").read_text().splitlines()
    if w.strip() and not w.lstrip().startswith("#")
}

# Curate: google's common words, intersected with clean dict, length 4..10
curated = []
seen = set()
blocked = 0
for w in GOOGLE:
    w = w.strip().lower()
    if not (4 <= len(w) <= 10):
        continue
    if not w.isalpha() or not w.isascii():
        continue
    if w not in clean_dict:
        continue
    if w in BLOCKLIST:
        blocked += 1
        continue
    if w in seen:
        continue
    seen.add(w)
    curated.append(w)

out = HERE / "curated.txt"
out.write_text("\n".join(curated) + "\n")
print(f"wrote {len(curated)} words to {out} ({blocked} blocked)")
print("first 20:", curated[:20])
print("last 20:", curated[-20:])
