# commitword

Render a git commit as a memorable word code instead of a hex blob.

```
inner19sage      →  resolves to exactly one commit (d2a6dcb271…)
magic28moved     →  another commit (b40af06177…)
threats49thirty4carbon  →  a three-word code (rare; for the few that need it)
```

A *commitword* is an all-lowercase code like `inner19sage`: two (or, rarely, three)
words joined by a number. It is **memorable**, **case-insensitive**,
**self-verifying**, and — minted against a repo — **guaranteed to resolve to
exactly one commit** there as of mint time (the same kind of guarantee an
abbreviated SHA carries; see [Guarantees and caveats](#guarantees-and-caveats)).
It is **lossy**: you recover the commit by searching a repo, not by reversing
the code.

## Why

Count how often you reach for a commit SHA: `git cherry-pick d2a6dcb2`,
`git revert`, `git show`, a `git diff a..b` between two points, `git bisect`, or
dropping one into a code review, a bug report, a changelog, or "the fix landed in
`<sha>`" on a call. Now count how often you move that SHA by anything other than
copy/paste — you can't, because nobody reads `d2a6dcb27169796c…` aloud, holds it
in their head, or retypes it without a slip.

That's fine until the clipboard isn't an option: telling a colleague the commit
on a call or in standup, reading it off one screen to type into another, getting
it onto a phone or a detached box with no shared clipboard, or dictating it into
a ticket. Forty hex characters are hostile to every channel that isn't a paste.

Abbreviating helps, but only on one axis. That git shortens SHAs at all —
`git show d2a6dcb` — is proof that length is a real burden; nobody abbreviates
what doesn't hurt. But seven characters of random hex are no more sayable,
memorable, or dictatable than the full forty. Abbreviation solves the length;
it leaves the other problem untouched — hex doesn't survive a voice call, a
glance between two screens, or a retype without a slip. A shorter blob is still
a blob.

A commitword fixes that. `inner19sage` you can say out loud, read off a slide, or
type into anything without squinting — then resolve back to the exact commit with
`commitfind`. The encoder has the repo in hand at mint time, so it picks the
*shortest* code that's still unique among the repo's commits at mint time, and
verifies it before handing it back.

And unlike a git **tag** — the usual way to pin a friendly name on a commit — a
commitword costs nothing to create or hand out: there's no ref to `git tag`,
push, and have everyone fetch, and no namespace to clutter. It's *derived* from
the SHA, so anyone with the repo recomputes the same code on demand — a nickname
that already exists for every commit, not one you have to mint and distribute.

The words are pure `a–z` and every code carries at least one letter outside the
hex range (`g–z`), so a commitword can never be confused with a raw SHA.

## Quick start

Python 3, standard library only. No install step.

**Mint** the shortest unique code for a commit or ref:

```sh
./commitmint.py <sha-or-ref> --repo /path/to/repo
# e.g.
./commitmint.py HEAD --repo .
./commitmint.py v3.21 --repo ~/repo
```

**Resolve** a code back to its commit(s):

```sh
./commitfind.py inner19sage --repo ~/repo
# searches all refs by default; --head-only restricts to HEAD's history
```

Resolving a short handle to a unique commit is not new — git already does it
natively for abbreviated SHAs, tags, branches, and `name-rev`. `commitfind`
applies the same idea to a word code: it scans the repo, matches the bits each
word pins, and confirms a single commit. It exists only because git doesn't
*yet* understand the commitword format — a commitword isn't a hex prefix, so
`git show inner19sage` can't resolve it the way `git show d2a6dcb` can. If git
learned the format, resolution would be built in and `commitfind` would be
unnecessary, exactly as abbreviated-SHA lookup already is.

**Standalone encode** (no repo — joint-maximizes bits, does not guarantee
repo-uniqueness):

```sh
./commitword.py d2a6dcb27169796c
```

## How a commitword reads

Take `inner19sage`:

| piece    | role                                                            |
|----------|----------------------------------------------------------------|
| `inner`  | word 1 — its hash pins the commit's top bits                   |
| `19`     | a number that encodes how many bits each word pins **and**      |
|          | separates the words                                             |
| `sage`   | word 2 — its hash pins the next slice of bits                  |

The number is not part of the SHA; it is bookkeeping. `19` here means word 1
pins 12 bits and word 2 pins 11 bits, for 23 identifying bits total — enough to
single out one commit in a ~50k-commit repo with comfortable growth headroom.

A few commits (~0.16% in a large repo) have no unique two-word code; those get a
third word, e.g. `threats49thirty4carbon`.

## Guarantees and caveats

- **Unique within the ref scope it was minted over** — by construction, and
  verified at mint time, the code resolves to exactly one commit among those
  reachable from all refs (`git rev-list --all`) in the repo when it was minted.
- **Self-verifying** — a code carries the bits it claims; given a candidate SHA
  you can confirm the match offline, no repo needed.
- **Case-insensitive** — `Inner19Sage` == `inner19sage`.
- **Hash-bound** — resolving a code depends only on the *hash* (default sha1); a
  resolver hashes the literal words and needs **no wordlist**. The wordlist only
  affects which codes the *minter* picks. So `COMMITWORD_LIST` doesn't affect
  portability, but `COMMITWORD_HASH` does — codes minted under a non-default hash are
  only resolvable with that same hash. See the spec.
- **Lossy** — you find the commit by searching a repo; you cannot reconstruct a
  full SHA from the code alone.
- **Not a security primitive** — a commitword pins only a prefix of bits (~23 for
  a two-word code), so it is *not* collision-resistant: an adversary can cheaply
  craft a commit that matches a given code (≈ `2^total` hashes — seconds for a
  two-word code). "Self-verifying" means a candidate SHA can be checked against
  the code offline, not that the code is tamper-evident. Like an abbreviated SHA,
  it's a convenience handle for honest use; rely on a full SHA or a signed tag
  where authenticity matters.
- **Scope- and point-in-time-relative** — the uniqueness guarantee covers the
  commits the minter could see: all refs in that clone, at mint time. It is *not* global or
  permanent. Commits the minter never saw — a branch that lives only in another
  clone, or commits added later — can collide, exactly as an abbreviated SHA
  (`d2a6dcb`) that is unique in your clone today can turn ambiguous in another
  clone or as history grows. The uniqueness is about on par with git's
  abbreviated SHAs. To resolve deterministically, search a scope that includes
  the commit and is at least as wide as the mint scope: `commitfind` defaults to
  all refs to match the minter, and `--head-only` narrows it.

## Configuration

| env var         | default            | meaning                                  |
|-----------------|--------------------|------------------------------------------|
| `COMMITWORD_LIST`  | `curated.txt`      | ordered wordlist (one word per line)     |
| `COMMITWORD_HASH`  | `sha1`             | word-side hash (any `hashlib` name)      |

`COMMITWORD_LIST` only changes which codes the minter picks — codes stay resolvable
by anyone using the same hash. `COMMITWORD_HASH` is the one that affects
portability: codes minted under a non-default hash resolve only under that hash.

## Files

- `commitword.py` — the encode/decode/verify library + a standalone CLI.
- `commitmint.py` — repo-aware minter (the main entry point).
- `commitfind.py` — reverse lookup (code → commit).
- `curated.txt` — the 6,368-word canonical wordlist.
- `curate.py` / `blocklist.txt` — regenerate `curated.txt` (curation + exclusions).

## Prior art

[eirikeve/shawords](https://github.com/eirikeve/shawords) tackles the same
"speak a hash" problem with a different design. It maps a hash *positionally* —
each 10-hex-char chunk indexes into rotating word tables — so a 40-char SHA
always becomes four words (e.g. `ethane by piet matchmake`), reading like a
phrase. That encoding is lossy by wraparound, **not** repo-aware, and offers no
verification or reverse lookup.

commitword optimizes for different things:

| | eirikeve/shawords | commitword |
|---|---|---|
| mechanism | hash → index → word (positional) | pick words whose hash matches SHA bits |
| words per SHA | fixed 4 | 2 (≈0.16% need 3) |
| repo-unique | no (can collide) | yes, within mint scope |
| self-verifying | no | yes (offline, no repo) |
| reverse to commit | no | yes (`commitfind`), and needs no wordlist |
| reads like | a phrase | a compact token |

In short: shawords is a lossy, fixed-length hash→phrase mnemonic; commitword is
a shorter, repo-verified identifier you can resolve back to exactly one commit.

## Documentation

- **[SPEC.md](SPEC.md)** — the exact, normative wire format and bit
  semantics (what you need to reimplement decode/verify in another language),
  plus the reference minting strategy.

## Tests

```sh
python3 -m pytest
```

## License & credits

MIT — see [LICENSE](LICENSE).

`google-10000.txt` is the
[google-10000-english](https://github.com/first20hours/google-10000-english)
word list (MIT); `curate.py` filters it down to `curated.txt`.
