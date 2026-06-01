#!/usr/bin/env bash
# Install the `git word` subcommand by symlinking the bridge onto your PATH.
#
#   ./install.sh             enable `git word` (auto: Python if present, else Perl)
#   ./install.sh --perl      Perl consumer build: resolve + pass-through, no mint;
#                            runs on a bare Git install (no Python needed)
#   ./install.sh --python    force the Python build (full mint / resolve / pass-through)
#   ./install.sh cw          also enable `git cw` (extra verbs as args)
#   ./install.sh --dir ~/bin choose the target directory
#   ./install.sh --uninstall remove every git-* symlink that points here
#
# Safe: never clobbers a real file, re-points an existing symlink of ours, and
# reports what it did.
set -eu

REPO="$(cd "$(dirname "$0")" && pwd)"
PY="$REPO/git-word"
PL="$REPO/git-word.pl"

die() { echo "install.sh: $*" >&2; exit 1; }
on_path() { case ":$PATH:" in *":$1:"*) return 0 ;; *) return 1 ;; esac; }
usage() { sed -n '2,13p' "$0" | sed 's/^#\s\{0,1\}//'; }

uninstall=0
backend=""
dir=""
verbs=()
while [ $# -gt 0 ]; do
    case "$1" in
        --uninstall) uninstall=1 ;;
        --perl)      backend=perl ;;
        --python)    backend=python ;;
        --dir) shift; [ $# -gt 0 ] || die "--dir needs a directory"; dir="$1" ;;
        --dir=*) dir="${1#--dir=}" ;;
        -h|--help) usage; exit 0 ;;
        -*) die "unknown option: $1 (see --help)" ;;
        *) verbs+=("$1") ;;
    esac
    shift
done

# Target directory: explicit --dir, else the first of these on your PATH.
if [ -z "$dir" ]; then
    for d in "$HOME/.local/bin" "$HOME/bin"; do
        if [ -d "$d" ] && on_path "$d"; then dir="$d"; break; fi
    done
fi
[ -n "$dir" ] || die "no PATH dir found; pass --dir DIR (and make sure it's on PATH)"

if [ "$uninstall" = 1 ]; then
    removed=0
    for f in "$dir"/git-*; do
        [ -L "$f" ] || continue
        t="$(readlink -f "$f")"
        if [ "$t" = "$(readlink -f "$PY")" ] || [ "$t" = "$(readlink -f "$PL")" ]; then
            rm -f "$f"; echo "removed   git ${f##*/git-}  ($f)"; removed=1
        fi
    done
    [ "$removed" = 1 ] || echo "nothing of ours to remove in $dir"
    exit 0
fi

# Pick the backend (Python = full; Perl = consumer, no Python needed).
if [ -z "$backend" ]; then
    if   command -v python3 >/dev/null 2>&1; then backend=python
    elif command -v perl    >/dev/null 2>&1; then backend=perl
    else die "neither python3 nor perl found; install one, or pass --python/--perl"
    fi
fi
case "$backend" in
    python) SRC="$PY"; rt=python3; note="full mint / resolve / pass-through" ;;
    perl)   SRC="$PL"; rt=perl;    note="resolve + pass-through (consumer; no mint)" ;;
esac
[ -e "$SRC" ] || die "$SRC not found"
command -v "$rt" >/dev/null 2>&1 \
    || echo "warning: '$rt' is not on PATH; the $backend build won't run until it is" >&2

mkdir -p "$dir"
names=("word")
[ ${#verbs[@]} -gt 0 ] && names+=("${verbs[@]}")
for name in "${names[@]}"; do
    [ "$name" = "w" ] && echo "note: 'git w' is a likely slot for a personal alias; 'cw' is safer" >&2
    target="$dir/git-$name"
    if [ -e "$target" ] && [ ! -L "$target" ]; then
        echo "skip      git $name: $target exists and is not a symlink" >&2
        continue
    fi
    ln -sf "$SRC" "$target"
    echo "installed git $name  ->  $target  [$backend: $note]"
done

echo
if on_path "$dir"; then
    echo "Done. Try:  git word --help"
else
    echo "Note: $dir is not on your PATH. Add it, then: git word --help"
fi
