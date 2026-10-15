"""Installer pre-flight: confirm the Little Mac forward-smash family is
intact in the package about to be written to the card, and that the packaged NRO
really carries the handlers and sound names those entries depend on.

Why this exists rather than just running tools/audit_littlemac_fsmash.py: that
tool's first check asserts the two angled motion kinds are absent from the base
game, reading dumps/arc/fighter/eflame/... That export is not on disk in this
workspace, so the tool aborts before it reaches the checks an installer needs.
The vanilla-baseline question was already measured and recorded for 0.20.16;
what matters before writing to the card is the weaker question: do the four
motion kinds, their cancel frames, flags, clip names and script words still
decode correctly in the tree being installed, and are all of them present in the
NRO that will be copied?

Motion-list decoding is imported from the audit tool rather than reimplemented,
so there is one parser and not two.

Read-only; writes nothing. Exit 0 = all checks passed.

Usage:  python tools/check_forward_smash_package.py <package_root>

Run it on the candidate package AND on the currently installed release; the two
outputs should be identical, which is the control that shows a new install did
not disturb the forward smash.

Added 2026-10-02 by T-0042.
"""
import hashlib
import os
import sys

sys.path.insert(0, os.path.join("tools"))
import audit_littlemac_fsmash as A  # noqa: E402  (path set above)

failures = []


def fail(msg):
    failures.append(msg)
    print("FAIL " + msg)


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    mod = os.path.join(root, "ultimate", "mods", "pyra_gamewatch_reskin")
    if not os.path.isdir(mod):
        fail("mod tree not found at " + mod)
        return 1
    nro = os.path.join(root, "atmosphere", "contents", "01006A800016E000",
                       "romfs", "skyline", "plugins",
                       "libpyra_gamewatch_reskin.nro")
    print("mod tree : " + mod)
    for slot in ("c06", "c07"):
        p = os.path.join(mod, "fighter", "eflame", "motion", "body", slot,
                         "motion_list.bin")
        if not os.path.isfile(p):
            fail("%s: motion_list.bin missing" % slot)
            continue
        built = A.read_mlist(p)
        for kind, want in A.EXPECTED.items():
            h = A.hash40(kind)
            if h not in built:
                fail("%s: motion kind %s absent from the built list" % (slot, kind))
                continue
            e = built[h]
            if e["cancel"] != want["cancel"]:
                fail("%s: %s cancel %s, expected %d"
                     % (slot, kind, e["cancel"], want["cancel"]))
            if e["flags"] != want["flags"]:
                fail("%s: %s flags %#x, expected %#x"
                     % (slot, kind, e["flags"], want["flags"]))
            want_clip = A.KIND_CLIP[kind]
            if e["anims"] != (A.hash40(want_clip),):
                fail("%s: %s names %s, expected %s"
                     % (slot, kind, [hex(a) for a in e["anims"]], want_clip))
            else:
                print("PASS %s: %-15s cancel %s flags %#x clip %-24s game_script %#x"
                      % (slot, kind, e["cancel"], e["flags"], want_clip,
                         e["game_script"]))
            if not e["game_script"]:
                fail("%s: %s has an empty game_script word" % (slot, kind))
        # G&W's own values must be gone, or a stale recipient entry is winning.
        for kind, old in A.EXPECTED_RECIPIENT.items():
            e = built.get(A.hash40(kind))
            if e and e["cancel"] == old["cancel"] and e["flags"] == old["flags"]:
                fail("%s: %s still reads as the recipient's own move "
                     "(cancel %s flags %#x)" % (slot, kind, e["cancel"], e["flags"]))
        for kind, clip in A.KIND_CLIP.items():
            cp = os.path.join(mod, "fighter", "eflame", "motion", "body", slot, clip)
            if not os.path.isfile(cp):
                fail("%s: clip %s (%s) missing" % (slot, kind, clip))

    if os.path.isfile(nro):
        blob = open(nro, "rb").read()
        print("NRO      : sha256 %s (%d bytes)"
              % (hashlib.sha256(blob).hexdigest(), len(blob)))
        for name in A.REQUIRED_HANDLERS + A.SOUND_NAMES:
            if name.encode() not in blob:
                fail("packaged NRO does not carry %r" % name)
        if not failures:
            print("PASS NRO carries all %d required handler names and all %d "
                  "forward-smash sound names"
                  % (len(A.REQUIRED_HANDLERS), len(A.SOUND_NAMES)))
    else:
        fail("packaged NRO not found at " + nro)

    print("")
    if failures:
        print("RESULT: %d FAILURE(S)" % len(failures))
        return 1
    print("RESULT: all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
