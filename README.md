# commitword

Render a git commit as a memorable word code instead of a hex blob.

```
inner19sage      →  resolves to exactly one commit (d2a6dcb271…)
magic28moved     →  another commit (b40af06177…)
threats49silver4carbon  →  a three-word code (rare; for the few that need it)
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

**Mint** the shortest unique code for a commit or ref. The repo is given with
`-C PATH` (or its alias `--repo PATH`), just like `git -C`; it defaults to the
current directory.

```sh
./commitmint.py <sha-or-ref> -C /path/to/repo
# e.g.
./commitmint.py HEAD -C .
./commitmint.py v3.21 -C ~/repo
# force a three-word code for extra future-uniqueness headroom
./commitmint.py HEAD -C . --min-words 3
# or grow a third word only when two words can't clear the margin floor
./commitmint.py HEAD -C . --reach-floor
# decorate the output with readability separators (-, _, or .): what-9-plug
./commitmint.py HEAD -C . --sep -
# don't like the default word pair? list alternatives and pick the least awkward
./commitmint.py HEAD -C . --list        # indexed, ranked candidates
./commitmint.py HEAD -C . --choose 3    # emit the candidate at index 3
./commitmint.py HEAD -C . -i            # pick interactively (arrow keys + Enter)
```

A commit usually has *many* valid commitwords — the minter just picks the
tidiest by default. They all resolve to the **same single commit**, so `--list`
shows the ranked alternatives and `--choose N` emits the one you want, letting a
human or an LLM swap in a less awkward word pair with no effect on resolution.
The list is ranked best-first (**index 0 is the default pick**), and each row
shows its **bit strength** — the one axis that
actually differs (more bits = more future-collision headroom):

```
$ ./commitmint.py HEAD -C ~/repo --list 5
# ranked best-first (index 0 = default pick); margin floor 23 bits …  ← on stderr
0  mothers19forces      23 bits
1  mothers19intention   23 bits
2  mothers19structures  23 bits
3  your1pays            21 bits
4  hacker1pays          21 bits

$ ./commitmint.py HEAD -C ~/repo --choose 3      # emit just that one
your1pays
```

Or skip the index step entirely with `-i`, an interactive arrow-key picker
(↑/↓ to move, Enter to select, `q` to cancel) that draws its menu on the
terminal and prints just the chosen code to stdout — so `code=$(./commitmint.py
HEAD -C . -i)` still captures only the code.

`--choose` prints the bare code (scriptable); the ordering/floor note goes to
stderr; and `--sep` decorates every line (`--list --sep -` →
`mothers-19-forces …`).

**Resolve** a code back to its commit(s):

```sh
./commitfind.py inner19sage -C ~/repo
# searches all refs by default (--all); --head-only narrows to HEAD's history
# optional -, _, or . separators are ignored -- inner-19-sage resolves the same
./commitfind.py inner-19-sage -C ~/repo
```

Resolving a short handle to a commit is not new — git already does it natively
for abbreviated SHAs, tags, branches, and `name-rev`. The closest analogue is
`git show <prefix>`: `commitfind` is to a word code what short-SHA lookup is to
a hex prefix. It scans the repo, matches the bits each word pins, and confirms a
single commit. It exists only because git doesn't *yet* understand the
commitword format — a commitword isn't a hex prefix, so `git show inner19sage`
can't resolve it the way `git show d2a6dcb` can. If git learned the format,
resolution would be built in and `commitfind` would be unnecessary, exactly as
abbreviated-SHA lookup already is.

That analogy also explains the **search scope**. `git show <prefix>`
disambiguates a short SHA *repo-wide*, not just within your current branch — and
`commitfind` does the same, defaulting to **all refs** (`--all`) to reproduce
the scope `commitmint` minted over, so it inherits the "exactly one commit"
guarantee. (This inverts `git log`, which defaults to HEAD — but resolving a
handle is a `git show` job, not a `git log` one.) `--head-only` narrows to HEAD's
history: a safe subset that never yields a false match but may find nothing if
the commit lives on another branch.

**Standalone encode** (no repo — joint-maximizes bits, does not guarantee
repo-uniqueness):

```sh
./commitword.py d2a6dcb27169796c
```

## How a commitword reads

At heart a commitword is just an **abbreviated-SHA prefix rendered as words**.
Decoding recovers the SHA's leading bits directly, with no repo; the repo search
only maps that prefix to the one full SHA that carries it — the same job
`git show d2a6dcb` does for a hex prefix.

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
third word, e.g. `threats49silver4carbon`.

## Guarantees and caveats

- **Unique within the ref scope it was minted over** — by construction, and
  verified at mint time, the code resolves to exactly one commit among those
  reachable from all refs (`git rev-list --all`) in the repo when it was minted.
- **Self-verifying** — a code carries the bits it claims; given a candidate SHA
  you can confirm the match offline, no repo needed.
- **Case-insensitive** — `Inner19Sage` == `inner19sage`.
- **Separator-tolerant** — optional `-`, `_`, or `.` at word/number boundaries are
  ignored: `inner-19-sage` == `inner.19.sage` == `inner19sage`. Display only; the
  canonical (minted) form carries none. Mint a decorated form with `--sep`.
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
  abbreviated SHAs. To resolve deterministically, search the scope the minter
  used — all refs — wide enough to include the commit yet *no wider*, so nothing
  the minter never checked can slip in as a false match. `commitfind` defaults to
  exactly that (`--all`); `--head-only` safely *narrows* it (handy when the
  commit is on HEAD), whereas searching *wider* than the mint scope is what risks
  ambiguity.

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
- `curated.txt` — the 6,350-word canonical wordlist.
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

## Where commitword sits among the alternatives

Rendering an identifier as something a human can say is an old idea, and
commitword is one point in a well-populated space:

- **Abbreviated SHAs** (`d2a6dcb`) — git-native and resolvable everywhere, but
  still hex: not sayable, memorable, or dictatable.
- **Positional word lists** — bip39, Diceware, S/KEY (RFC 1751), the PGP word
  list, "friendly name" generators like Docker's `nostalgic_einstein`. Each word
  *is* an index into a fixed list, so they are dense (a full `log2(list)` bits
  per word) and need no inline number or fallback word — but a resolver **must
  ship the exact wordlist** to turn words back into bits.
- **Algorithmic syllables** — proquints (`lusab-babad`) encode bits as
  pronounceable consonant–vowel patterns: no wordlist, fixed length, but
  pronounceable *nonsense* rather than real words, so less memorable.

|                            | abbrev. SHA | positional (bip39 …) | proquints | commitword |
|----------------------------|:-----------:|:--------------------:|:---------:|:----------:|
| real, memorable words      | no          | yes                  | no        | **yes**    |
| resolve without a wordlist | n/a (hex)   | **no**               | yes       | **yes**    |
| deterministic length       | grows       | yes                  | yes       | no         |
| carries an inline number   | no          | no                   | no        | yes        |

commitword deliberately occupies the one cell none of the others reach: **real,
memorable words *and* wordlist-free resolution.** That combination forces the
mechanism. With real words, the only wordlist-independent map from a word to bits
is a *hash* — a positional `word → index` lookup *is* a wordlist — so commitword
matches words whose hash pins the SHA's bits instead of indexing them, and a
resolver needs only the hash (`sha1`), never the ~6,000-word list.

The price is paid in the format. Because a hash matches *however many* bits it
happens to (not a controlled amount), the code must record how many bits each
word pins — that is the inline number — and each word pins only ≈ `log2(list)` ≈
12–13 bits, so a rare commit needs a third word. A positional encoding avoids
both (no number, `inner.sage`, never a third word) at the cost of shipping the
list. If you prefer that trade, a positional scheme fits better; commitword bets
that wordlist-free resolution — recompute any code with nothing but git and a
stock hash — is worth a spoken number.

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
