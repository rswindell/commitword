#!/usr/bin/env bash
# Install the `git word` subcommand by symlinking git-word onto your PATH.
#
#   ./install.sh                enable `git word`
#   ./install.sh cw             also enable `git cw`  (extra verbs as args)
#   ./install.sh --dir ~/bin    choose the target directory
#   ./install.sh --uninstall    remove every git-* symlink that points here
#
# Safe: it never clobbers a real file, re-points an existing symlink of ours,
# and reports exactly what it did.
set -eu

REPO="$(cd "$(dirname "$0")" && pwd)"
SRC="$REPO/git-word"

die() { echo "install.sh: $*" >&2; exit 1; }
on_path() { case ":$PATH:" in *":$1:"*) return 0 ;; *) return 1 ;; esac; }

usage() {
    sed -n '2,10p' "$0" | sed 's/^#\s\{0,1\}//'
}

[ -e "$SRC" ] || die "git-word not found next to this script ($SRC)"

uninstall=0
dir=""
verbs=()
while [ $# -gt 0 ]; do
    case "$1" in
        --uninstall) uninstall=1 ;;
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
        if [ "$(readlink -f "$f")" = "$(readlink -f "$SRC")" ]; then
            rm -f "$f"; echo "removed   git ${f##*/git-}  ($f)"; removed=1
        fi
    done
    [ "$removed" = 1 ] || echo "nothing of ours to remove in $dir"
    exit 0
fi

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
    echo "installed git $name  ->  $target"
done

echo
if on_path "$dir"; then
    echo "Done. Try:  git word --help"
else
    echo "Note: $dir is not on your PATH. Add it, then: git word --help"
fi
