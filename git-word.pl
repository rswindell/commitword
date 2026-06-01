#!/usr/bin/env perl
# git word -- Perl consumer edition.
#
# Resolves commitwords and runs git commands with commitword arguments, using
# only Perl (core Digest::SHA) + git -- no Python, no wordlist. Perl and git both
# ship with Git for Windows, so this runs on a bare Git install. It is the
# *consumer* half of the toolset: it resolves and passes through, but does not
# mint (minting needs the wordlist + search; use commitmint.py on a dev box).
#
#   git word <commitword>          resolve a commitword -> its commit's full SHA
#   git word <git-command> [args]  run git, resolving commitword arguments first
#
# Direction is auto-detected: a commitword is resolved, anything else is treated
# as a git subcommand whose commitword arguments are resolved before it runs:
#
#   git word inner-19-sage
#   git word show inner-19-sage
#   git word diff fill-0-till..asking-9-move
#
# Flags: -C/--repo PATH (like git -C), --head-only (search HEAD only),
# --all (default), --find (force resolve). Install on Windows via a git alias:
#   git config --global alias.word '!perl "/c/path/to/git-word.pl"'
use strict;
use warnings;
use Digest::SHA qw(sha1);

# Wire-format constants (SPEC §4.1 / §4.2).
my $Y_MIN  = 10;
my $K_MIN  = 10;
my $K_SPAN = 9;
my $M_MIN  = 8;
my $MAX_TOTAL = 60;        # native-int safety bound; real codes are far smaller

sub unpack1 { my $n = shift; (int($n / $K_SPAN) + $Y_MIN, ($n % $K_SPAN) + $K_MIN) }

# Top $nbits of a big-endian byte string, as an integer (SPEC §4.3).
sub leading_bits {
    my ($digest, $nbits) = @_;
    my $nb = int(($nbits + 7) / 8);
    my $v = 0;
    $v = ($v << 8) | ord(substr($digest, $_, 1)) for 0 .. $nb - 1;
    return $v >> ($nb * 8 - $nbits);
}

sub word_bits { leading_bits(sha1($_[0]), $_[1]) }                 # top n of sha1(word)
sub sha_bits  { leading_bits(pack('H*', $_[0]), $_[1]) }           # top n of a hex SHA

# Decode a commitword -> (total_bits, expected_value), or () if not a commitword.
sub decode {
    my $code = lc($_[0] // '');
    return () unless length $code;
    (my $bare = $code) =~ tr/-_//d;
    return () if $bare =~ /^[0-9a-f]+$/;                # hex-safety: a raw SHA prefix
    if ($code =~ /^([a-z]+)[-_]?(\d+)[-_]?([a-z]+)$/) {
        my ($y, $k) = unpack1($2);
        my $total = $y + $k;
        return () if $total > $MAX_TOTAL;
        return ($total, (word_bits($1, $y) << $k) | word_bits($3, $k));
    }
    if ($code =~ /^([a-z]+)[-_]?(\d+)[-_]?([a-z]+)[-_]?(\d+)[-_]?([a-z]+)$/) {
        my ($y, $k) = unpack1($2);
        my $m = $4 + $M_MIN;
        my $total = $y + $k + $m;
        return () if $total > $MAX_TOTAL;
        my $e2 = (word_bits($1, $y) << $k) | word_bits($3, $k);
        return ($total, ($e2 << $m) | word_bits($5, $m));
    }
    return ();
}

sub repo_from {
    for (my $i = 0; $i < @_; $i++) {
        return $_[$i + 1] // '.' if $_[$i] eq '-C' or $_[$i] eq '--repo';
        return $1 if $_[$i] =~ /^--repo=(.*)$/;
    }
    return '.';
}

sub find_subject {
    for (my $i = 0; $i < @_; $i++) {
        my $x = $_[$i];
        if ($x eq '-C' or $x eq '--repo') { $i++; next; }
        next if $x =~ /^--repo=/;
        next if $x =~ /^-/ and $x ne '-';
        return $x;
    }
    return undef;
}

sub is_git_rev {
    my ($tok, $repo) = @_;
    my $pid = open(my $fh, '-|', 'git', '-C', $repo, 'rev-parse',
                   '--verify', '--quiet', "$tok\^{commit}");
    return 0 unless $pid;
    local $/; my $out = <$fh>; close $fh;
    return ($? == 0 && defined $out && length $out);
}

# All full SHAs in $repo whose top bits match commitword $code.
sub resolve {
    my ($code, $repo, $head_only) = @_;
    my ($total, $exp) = decode($code);
    return () unless defined $total;
    open(my $fh, '-|', 'git', '-C', $repo, 'rev-list',
         ($head_only ? 'HEAD' : '--all')) or die "git word: git rev-list failed\n";
    my @hits;
    while (my $sha = <$fh>) {
        chomp $sha;
        push @hits, $sha if sha_bits($sha, $total) == $exp;
    }
    close $fh;
    return @hits;
}

# Pass-through: replace each commitword run that resolves (and isn't a git ref)
# with its SHA, including inside rev-expressions like <cw>..<cw> and <cw>~3.
sub translate_arg {
    my ($arg, $repo) = @_;
    $arg =~ s{([A-Za-z0-9_-]+)}{
        my $tok = $1;
        my ($total) = decode($tok);
        if (defined $total && !is_git_rev($tok, $repo)) {
            my @s = resolve($tok, $repo, 0);
            @s ? $s[0] : $tok;
        } else { $tok }
    }ge;
    return $arg;
}

sub usage {
    open(my $fh, '<', $0) or return '';
    my @lines;
    while (<$fh>) { last unless /^#/ or /^#!/; push @lines, $_ }
    shift @lines;                                  # drop the shebang
    s/^#\s?// for @lines;
    return join('', @lines);
}

# ---- dispatch ----
my $force;
my @pass;
for (@ARGV) {
    if    ($_ eq '--find') { $force = 'find' }
    elsif ($_ eq '--mint') { $force = 'mint' }
    elsif ($_ eq '-h' or $_ eq '--help') { print usage(); exit 0 }
    else  { push @pass, $_ }
}

my $repo      = repo_from(@pass);
my $head_only = grep { $_ eq '--head-only' } @pass;
my $subject   = find_subject(@pass);

if (defined $force && $force eq 'mint') {
    die "git word: minting isn't supported in the Perl consumer build; "
      . "mint with commitmint.py (Python).\n";
}

sub do_resolve {
    my @shas = resolve($subject, $repo, $head_only);
    unless (@shas) {
        print STDERR "git word: no commitword match for '$subject'\n";
        exit 1;
    }
    print "$_\n" for @shas;
    exit 0;
}

if (defined $force && $force eq 'find') {
    die "git word: --find needs a commitword\n" unless defined $subject;
    do_resolve();
}

if (!defined $subject) {
    die "git word: nothing to do. This Perl build resolves and passes through; "
      . "it does not mint. Try: git word <commitword>  or  git word <git-cmd> ...\n";
}

do_resolve() if defined(decode($subject));            # a commitword -> resolve

if (is_git_rev($subject, $repo)) {                    # a git revision -> would mint
    die "git word: '$subject' is a git revision; minting isn't supported in the "
      . "Perl consumer build (use commitmint.py).\n";
}

# Otherwise: a git subcommand -> pass through, resolving commitword args.
my @translated = map { translate_arg($_, $repo) } @pass;
exec('git', @translated) or die "git word: exec git failed: $!\n";
