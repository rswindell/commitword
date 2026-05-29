# commitword format specification

**Format version:** 1
**Status:** the wire format, decode, and verify rules below are **normative** — a
conformant implementation MUST match them exactly. The minting strategy
(§6) is **informative**: it describes one valid way to produce codes and may
evolve without breaking decoders.

---

## 1. Overview

A **commitword** is a short, case-insensitive, all-lowercase string such as
`inner19sage` that pins the leading bits of a git commit SHA using words drawn
from an ordered wordlist. It is **lossy** (it does not encode a full SHA) but
**self-verifying** (given a candidate SHA, an implementation can confirm whether
the code matches it, with no repository access).

Two forms exist:

- **two-word:** `<word><N1><word>`
- **three-word:** `<word><N1><word><N2><word>`

The words pin successive slices of the commit's top bits; the numbers encode the
slice widths and double as separators.

---

## 2. Parameters and portability (normative)

### 2.1 The interop parameter: the hash

Decoding and verifying a commitword (§5) depend on exactly **one** shared parameter:
the **word-side hash function**. A decoder hashes the *literal words taken from
the code* — it never consults a wordlist (see §5.1). Two implementations agree on
decode and verify for every code if and only if they use the same hash.

This is **not** the commit's own object hash. Two distinct hashes are in play:
the *word-side* hash here (the only shared parameter), and the *commit object
hash* git uses to identify the commit, which the scheme consumes as opaque bits
(§4.3) and is agnostic to. They are independent: the default word-side hash is
`sha1` only by coincidence with git's historical object hash — you may hash
words with `sha1` against a SHA-256 repo, or vice versa.

| parameter | default | role                                                  |
|-----------|---------|-------------------------------------------------------|
| hash      | `sha1`  | hashes each literal word in the code (§4.3)            |
| `PROBE`   | `80`    | bits of each word-hash / of the SHA exposed to matching; must be ≥ any code's total bits |

Unlike the hash, `PROBE` is **not** an interop parameter: its exact value does
not affect how any code decodes. Since the top `n` bits of a word's hash are the
same whether you slice 80 bits or 128 and then shift, two implementations agree
on every code as long as both keep `PROBE ≥ total`. So `PROBE` is the maximum
identifying bits any single code can pin — a ceiling, not a target. The default
`80` is generous headroom (realistic codes pin ~20–40 bits) and a clean byte
boundary (10 bytes), so slicing the leading `PROBE` bits of a digest needs no
sub-byte handling.

A bare commitword is assumed to use **sha1**. A code is **portable** to any resolver
using the same hash, *regardless of which wordlist (if any) the producer used* —
the wordlist is not part of the resolution contract (§3 below).

Implementations MAY override the hash (reference implementation: the
`COMMITWORD_HASH` environment variable). A code minted under a non-default hash is
**not portable**: only a resolver using the identical hash recovers its bits, and
such a code MUST travel together with its hash. A bare code is never assumed to
use a non-default hash.

### 2.2 The wordlist (producer-side only)

The wordlist is an **input to minting** (§6), not to resolution. It determines
which words a producer may choose; it has **no effect** on how any code decodes
or verifies. **A resolver needs no wordlist.** Overriding the wordlist (reference
implementation: `COMMITWORD_LIST`) changes which codes a minter *emits* but never
affects whether an existing code resolves.

The rules below are *informative* — they matter for reproducing the reference
minter's output, not for the interop contract. The ordered wordlist is read from
a text file, one candidate per line. Each line is trimmed and lowercased, then
**kept** only if it is:

- length 3 to 10 inclusive,
- ASCII and composed solely of letters `a–z`,
- not already seen (first occurrence wins; duplicates dropped).

The surviving words, **in file order**, form the wordlist. Word *rank* is the
0-based index in this order (lower = earlier in the file). The reference
`curated.txt` yields **6,368** words; to reproduce the reference minter's choices
exactly, use the same file, identifiable by its SHA-256:

```
a61323513252e5fc2de0ac71f87633bd09a6bca0494569379337ee1c652ed068
```

---

## 3. Wire format (normative)

### 3.1 Grammar

```
two-word    = WORD NUM WORD
three-word  = WORD NUM WORD NUM WORD
WORD        = 1*( "a"…"z" )        ; in practice 3–10 letters (§2.3)
NUM         = 1*( "0"…"9" )        ; plain integer, no leading-zero padding
```

As anchored regular expressions:

- two-word: `^[a-z]+\d+[a-z]+$`
- three-word: `^[a-z]+\d+[a-z]+\d+[a-z]+$`

Numbers carry no padding and serve as the delimiters between words.

### 3.2 Case

Codes are case-insensitive. A decoder MUST lowercase the input before parsing.
`Inner19Sage`, `INNER19SAGE`, and `inner19sage` are the same code.

### 3.3 Hex-safety invariant

Every valid commitword contains **at least one letter in `g–z`** (outside the hex
alphabet `0-9a-f`). Therefore any string composed solely of `[0-9a-f]` is a raw
SHA (or SHA prefix), **not** a commitword.

A decoder MUST reject an input whose characters are all in `[0-9a-f]` (return
"not a commitword") so that, e.g., `dead12beef` is treated as a hex SHA prefix and
never mis-parsed as word/number/word. Producers MUST guarantee this invariant
(the reference minter ensures at least one chosen word is non-hex-like).

---

## 4. Bit semantics (normative)

### 4.1 Constants

```
PROBE = 80      ; bits of hash / SHA used for matching
Y_MIN = 10      ; minimum bits pinned by word 1
K_MIN = 10      ; minimum bits pinned by word 2
K_MAX = 18      ; maximum bits pinned by word 2
K_SPAN = 9      ; = K_MAX - K_MIN + 1
M_MIN = 8       ; minimum bits pinned by word 3
```

(The reference minter also bounds `m ≤ 24` while searching for a third word;
this is a minting-search limit, not a decode constraint — see §4.2, where `m`
has no maximum.)

`y` = bits pinned by word 1, `k` = bits pinned by word 2, `m` = bits pinned by
word 3 (three-word form only).

### 4.2 Number packing

```
N1 = (y - Y_MIN) * K_SPAN + (k - K_MIN)
   = (y - 10) * 9 + (k - 10)

N2 = m - M_MIN
   = m - 8
```

Decoding the numbers:

```
y = N1 // 9 + 10
k = N1 %  9 + 10
m = N2 + 8
```

Constraints when packing: `y ≥ 10`, `10 ≤ k ≤ 18`, `m ≥ 8`. (`y` has no fixed
maximum; in practice it is bounded by how many leading bits some word's hash
matches.)

### 4.3 Hash bits

`hash_bits(word, n)` = the first `n` bits of `HASH(word)`'s digest, MSB-first,
left-aligned as an integer. Concretely: take the first `⌈n/8⌉` bytes of the
digest, interpret big-endian, and right-shift by `(8·⌈n/8⌉ − n)` to drop the
trailing excess bits. The SHA side is read identically: `sha_to_bits(sha, n)` =
the first `n` bits of the commit's binary hash.

The commit hash is consumed purely as opaque bits — the scheme never depends on
which algorithm produced it. Any commit-identifier hash that supplies at least
`PROBE` bits works (git's SHA-1 at 160 bits or SHA-256 at 256 bits, both with
ample margin). A given code is, however, bound to the commit's *actual* hash
value: if a repo transitions object formats (e.g. SHA-1 → SHA-256), every
commit's identity changes and codes minted against the old identities no longer
resolve — the same way an abbreviated SHA would not survive the transition.

### 4.4 What each word pins

Let `target` be the commit's SHA. Under the format:

- word 1's top `y` hash bits equal `target[0 : y]`
- word 2's top `k` hash bits equal `target[y : y + k]`
- word 3's top `m` hash bits equal `target[y+k : y+k+m]` (three-word only)

The code therefore pins a contiguous prefix of `total` bits of the SHA, where
`total = y + k` (two-word) or `total = y + k + m` (three-word).

---

## 5. Decode and verify (normative)

### 5.1 Decode to bits

Given a code, after lowercasing and the §3.3 hex-safety check:

1. Match against the three-word grammar; else the two-word grammar; else it is
   not a commitword.
2. Recover `y, k` (and `m`) via §4.2.
3. Compute the expected SHA prefix as a single integer:

   - two-word: `expected = (top(hash(w1), y) << k) | top(hash(w2), k)`
   - three-word:
     `expected = (top(hash(w1), y) << (k+m)) | (top(hash(w2), k) << m) | top(hash(w3), m)`

   where `top(h, n)` is the first `n` bits of that word's hash (§4.3).
4. Result is the pair `(total, expected)` with `total = y + k [+ m]`.

`hash` here is the agreed hash (§2.1). The words need not be in the wordlist to
decode — decoding is purely arithmetic over the literal words' hashes, so a
resolver needs no wordlist.

### 5.2 Verify against a candidate SHA

A candidate commit SHA *matches* the code iff its top `total` bits equal
`expected`:

```
match  ⇔  sha_to_bits(candidate, total) == expected
```

This requires no repository — only the candidate SHA and the code.

---

## 6. Reference minting strategy (informative)

This section describes how the reference implementation (`commitmint.py`) chooses a
code. A producer is free to use any strategy provided its output decodes and
verifies (§9); the choices here are not part of the interop contract.

### 6.1 Goal

Emit the **shortest** code that resolves to **exactly one** commit among the
target repo's commits (`git rev-list --all`), preferring codes that clear a soft
growth-margin bit floor.

### 6.2 Margin floor

To stay robust against future repo growth, the minter prefers codes pinning at
least `L_req` bits:

```
L_req = ⌈ log2(M) + log2(growth / pmax) ⌉
```

where `M` = number of commits, `growth` = assumed future growth factor
(default 16), `pmax` = tolerated future-collision probability (default 0.1). The
floor is also clamped to at least `Y_MIN + K_MIN = 20` bits. For a ~50k-commit
repo this is ≈ 23 bits.

The floor is a **soft preference**, not a hard gate: a short code that is already
unique but sits below the floor is preferred over growing a third word merely to
reach the floor. **Uniqueness is the only hard requirement.**

### 6.3 Two-word search

For each feasible `y` (where some word's hash matches ≥ `y` leading bits) and
each `k` in `K_MIN..K_MAX`, if the `(y+k)`-bit prefix is unique among repo
commits, form a candidate. Among all unique candidates pick, in order:

1. clears the floor over not,
2. shorter rendered string,
3. **more** identifying bits (free safety margin),
4. commoner words (lower rank sum),
5. lexicographic (determinism).

Word selection per slot prefers short, then common, then alphabetical words,
fills the most-constrained slot first to avoid forced duplicates, and guarantees
at least one non-hex-like word (§3.3).

### 6.4 Three-word fallback

If **no** unique two-word code exists (~0.16% of commits in a large repo), append
a third word pinning the next `m` bits (`m` chosen as the best available match,
≥ `M_MIN`) and emit the verified three-word code.

### 6.5 Self-verification

The minter MUST confirm its own output decodes and verifies against the source
SHA (§5) before returning it. This also enforces the hex-safety invariant, since
an all-hex code would fail to decode.

---

## 7. Resolution and uniqueness (informative)

A commitword identifies a commit only **relative to a repository and a ref scope**.
The reference minter guarantees uniqueness over **all refs**
(`git rev-list --all`); resolve (`commitfind.py`) over the **same** scope to obtain
the single intended match. Restricting the search to a narrower scope (e.g.
HEAD-only) still yields at most that match but may find none if the commit is not
reachable there.

Outside the repository it was minted against, a code is only *probabilistically*
unique: it pins `total` bits, so two unrelated commits collide with probability
≈ `2^-total`. Uniqueness is a property of the mint-time repo, not a global one.

That `2^-total` figure is the *accidental* rate. A commitword is **not**
collision-resistant against an adversary: deliberately constructing a commit
whose top `total` bits match a given code costs only ≈ `2^total` hash trials
(seconds for a two-word code, and far cheaper than a full hash collision even
for three words). A commitword is therefore a convenience identifier, not a
security primitive — use a full SHA or a signed object where authenticity
matters.

---

## 8. Worked examples

### 8.1 `inner19sage` (two-word)

- Parse: `w1 = inner`, `N1 = 19`, `w2 = sage`.
- Unpack: `y = 19//9 + 10 = 12`, `k = 19%9 + 10 = 11`, `total = 23`.
- `top(sha1(inner), 12) = 3370`; `top(sha1(sage), 11) = 878`.
- `expected = (3370 << 11) | 878 = 6902638`.
- A commit matches iff its top 23 bits equal `6902638`. The commit
  `d2a6dcb27169796c…` does (its top 12 bits are also `3370`), so the code
  verifies.

### 8.2 `threats49thirty4carbon` (three-word)

- Parse: `w1 = threats`, `N1 = 49`, `w2 = thirty`, `N2 = 4`, `w3 = carbon`.
- Unpack: `y = 49//9 + 10 = 15`, `k = 49%9 + 10 = 14`, `m = 4 + 8 = 12`,
  `total = 41`.
- `expected = (top(sha1(threats),15) << 26) | (top(sha1(thirty),14) << 12)
  | top(sha1(carbon),12) = 1955335576866`.
- A commit matches iff its top 41 bits equal `1955335576866`.

### 8.3 Hex-safety

`dead12beef` is all `[0-9a-f]`, so it is **not** a commitword; a decoder returns
"not a commitword" and the caller treats it as a raw SHA prefix.

---

## 9. Conformance

The portable, testable surface is the **decoder/verifier**:

- A conformant **decoder** MUST: lowercase input; reject all-`[0-9a-f]` strings
  (§3.3); accept exactly the two grammars (§3.1); unpack numbers per §4.2; and
  compute `(total, expected)` per §5.1 using the agreed hash. No wordlist needed.
- A conformant **verifier** MUST report a match iff `sha_to_bits(candidate,
  total) == expected` (§5.2).
- A **producer/minter** need only emit codes that a conformant decoder accepts
  and that verify against the intended SHA. Its selection strategy (§6) is
  unconstrained by this specification.

Two implementations using the same hash (§2.1) MUST agree on decode and verify
for every input — independent of wordlist. They need not agree on which code a
minter produces for a given commit.
