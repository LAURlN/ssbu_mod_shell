#!/usr/bin/env python3
"""Pre-publication checks for an export folder.

Usage: python <dst>/tools/showcase-export/check_export.py --dst <dst> [--name <account-or-name> ...]

Reports, per check, every hit with file and line:
  1. e-mail addresses, phone-like numbers in prose, the --name words, drive-letter paths, user-profile paths,
     the words key/token/secret/password/Bearer, hex strings longer than 64 and base64-like strings;
  2. every file over 200 KB and every file that is not UTF-8 text;
  3. relative Markdown links in README.md and MANIFEST.md that do not resolve.
Exit code 0 always: hits need a human judgement (see MANIFEST.md "Final checks").
"""
import argparse
import os
import re

CHECKS = {
    "e-mail": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}\b"),
    "phone": re.compile(r"(?<![\w.#-])\+?\(?\d{2,4}\)?[ /-]\d{3,4}[ -]\d{3,5}(?![\w.-])"),
    "drive path": re.compile(r"(?<![A-Za-z0-9<])[A-Za-z]:(?:\\|/)(?!/)"),
    "user profile path": re.compile(r"(?i)\busers[\\/]+(?!me\b)[a-z]"),
    "key/token/secret/password/bearer": re.compile(r"(?i)\b(key|keys|token|tokens|secret|secrets|password|passwd|bearer)\b"),
    "hex > 64": re.compile(r"\b[0-9a-fA-F]{65,}\b"),
    "base64-like": re.compile(r"(?<![A-Za-z0-9+/_.-])(?=[A-Za-z0-9+/]*[0-9])(?=[A-Za-z0-9+/]*[A-Z])(?=[A-Za-z0-9+/]*[a-z])"
                              r"[A-Za-z0-9+/]{40,}={0,2}(?![A-Za-z0-9+/_.-])"),
}
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dst", required=True)
    ap.add_argument("--name", action="append", default=[])
    a = ap.parse_args()
    checks = dict(CHECKS)
    for n in a.name:
        checks[f"name #{len(checks)}"] = re.compile(re.escape(n), re.I)
    hits = {k: [] for k in checks}
    big, binary = [], []
    for dp, dn, fn in os.walk(a.dst):
        for f in fn:
            p = os.path.join(dp, f)
            r = os.path.relpath(p, a.dst).replace(os.sep, "/")
            size = os.path.getsize(p)
            if size > 200_000:
                big.append((r, size))
            try:
                text = open(p, "rb").read().decode("utf-8")
            except UnicodeDecodeError:
                binary.append(r)
                continue
            if r.startswith("tools/showcase-export/"):
                continue  # the export tooling names the patterns it looks for
            for i, line in enumerate(text.splitlines(), 1):
                for k, rx in checks.items():
                    for m in rx.finditer(line):
                        hits[k].append((r, i, m.group(0)))
    for k, v in hits.items():
        files = {}
        for r, i, s in v:
            files.setdefault(r, []).append(s)
        print(f"== {k}: {len(v)} hits in {len(files)} files")
        for r, ss in sorted(files.items(), key=lambda x: -len(x[1])):
            print(f"   {len(ss):4}  {r}  e.g. {sorted(set(ss))[:4]}")
    print(f"== files over 200 KB: {len(big)}")
    for r, s in big:
        print(f"   {s:9}  {r}")
    print(f"== non-text files: {len(binary)}")
    for r in binary:
        print(f"   {r}")
    bad = 0
    for doc in ("README.md", "MANIFEST.md", "NEEDS_DECISION.md"):
        p = os.path.join(a.dst, doc)
        if not os.path.isfile(p):
            continue
        links = LINK.findall(open(p, encoding="utf-8").read())
        for t in links:
            if re.match(r"[a-z]+://", t) or t.startswith("mailto:"):
                continue
            path, _, anchor = t.partition("#")
            target = os.path.normpath(os.path.join(a.dst, path)) if path else p
            ok = os.path.exists(target)
            if ok and anchor and target.endswith(".md"):
                heads = [re.sub(r"[^\w\- ]", "", h.strip("# ").lower()).replace(" ", "-")
                         for h in open(target, encoding="utf-8").read().splitlines() if h.startswith("#")]
                ok = anchor in heads
            if not ok:
                bad += 1
                print(f"   BROKEN LINK in {doc}: {t}")
        print(f"== links in {doc}: {len(links)} checked")
    print(f"== broken links: {bad}")


if __name__ == "__main__":
    main()
