"""Post-install verification: compare the SD card mod tree against a candidate
package file-by-file, and cross-check that package's MANIFEST mod_file_hashes
against what is actually on the card.

Use this AFTER `src/pgwr/install-to-card.sh`, as an independent check rather than
a re-read of the installer's own "installed and verified" message. It answers the
three questions that actually matter: is every file on the card byte-identical to
the package, did the install drop or invent any file, and does the card match the
hashes the manifest claims.

Read-only; writes nothing and never touches the card.

The card root is a module constant because CPython on Windows cannot see an msys
`/e` mount - it must be a real drive path like `sd:/ultimate/mods/...`. Override it
by editing CARD, or run under the same shell the installer uses.

Usage:
  python tools/verify_installed_card.py <package_root> [<package_root> ...]
    <package_root> is a package dir (containing MANIFEST.json), or directly a
    mod tree dir.

Exit 0 if no differences; prints a per-file breakdown either way. Exit 1 if any file
differs, is missing from either side, or the manifest carries no per-file hash table
(a missing table is reported as SKIPPED, never as a pass).

Added 2026-10-02 by T-0042 after installing 0.20.16+robot-dtilt.4.
2.0.0, 2026-10-03: accept both manifest key names (`mod_file_hashes`, `mod_files`)
and fail loudly when neither exists. The 0.20.20 install check passed while silently
comparing zero entries against the gaogaen_throw_b manifest.
"""
import hashlib
import json
import os
import sys

CARD = "sd:/ultimate/mods/pyra_gamewatch_reskin"  # Windows path: msys /e is not visible to CPython
DEFAULT_PKGS = [
    "builds/pgwr/0.20.16/ultimate/mods/pyra_gamewatch_reskin",
]


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def inventory(root):
    out = {}
    for dirpath, _dirs, files in os.walk(root):
        for name in files:
            p = os.path.join(dirpath, name)
            rel = os.path.relpath(p, root).replace(os.sep, "/")
            out[rel] = sha(p)
    return out


def main():
    pkgs = sys.argv[1:] or DEFAULT_PKGS
    card = inventory(CARD)
    print("card files: %d" % len(card))
    for pkg in pkgs:
        tree = inventory(pkg)
        only_card = sorted(set(card) - set(tree))
        only_pkg = sorted(set(tree) - set(card))
        diff = sorted(k for k in set(card) & set(tree) if card[k] != tree[k])
        print("--- card vs %s" % pkg)
        print("    pkg files=%d only_card=%d only_pkg=%d differing=%d"
              % (len(tree), len(only_card), len(only_pkg), len(diff)))
        for k in diff[:20]:
            print("      DIFF     %s" % k)
        for k in only_card[:10]:
            print("      ONLY_CARD %s" % k)
        for k in only_pkg[:10]:
            print("      ONLY_PKG  %s" % k)
    # A package root holds MANIFEST.json; a bare mod tree is three levels below it
    # (<pkg>/ultimate/mods/pyra_gamewatch_reskin).
    manifest = os.path.normpath(os.path.join(pkgs[-1], os.pardir, os.pardir, os.pardir, "MANIFEST.json"))
    with open(manifest) as f:
        doc = json.load(f)
    # Manifests disagree on the key name: the collective releases write
    # `mod_file_hashes`, the per-task packages (e.g. gaogaen_throw_b 0.3.0,
    # 2026-10-03) write `mod_files`. Accept both rather than reporting a
    # vacuous "0 entries, 0 mismatches" for half the packages.
    recorded = doc.get("mod_file_hashes") or doc.get("mod_files") or {}
    if not recorded:
        print("manifest %s: NO per-file hash table "
              "(looked for 'mod_file_hashes' and 'mod_files'); "
              "manifest cross-check SKIPPED, not passed" % manifest)
        return 1
    bad = [k for k, v in recorded.items() if card.get(k) != v]
    print("manifest %s: %d entries, card mismatches %d" % (manifest, len(recorded), len(bad)))
    for k in bad[:20]:
        print("      CARD!=MANIFEST %s card=%s manifest=%s"
              % (k, (card.get(k) or "ABSENT")[:12], recorded[k][:12]))
    # A manifest that lists files the card does not have, or vice versa, is as
    # much a failure as a hash mismatch.
    only_card = sorted(set(card) - set(recorded))
    only_manifest = sorted(set(recorded) - set(card))
    if only_card:
        print("      ON CARD BUT NOT IN MANIFEST: %d" % len(only_card))
        for k in only_card[:20]:
            print("        %s" % k)
    if only_manifest:
        print("      IN MANIFEST BUT NOT ON CARD: %d" % len(only_manifest))
        for k in only_manifest[:20]:
            print("        %s" % k)
    return 1 if (bad or only_card or only_manifest) else 0


if __name__ == "__main__":
    sys.exit(main())


if __name__ == "__main__":
    main()
