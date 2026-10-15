"""P8-LUA-LIST negative controls (scratch driver for the deliverable check).

Each control damages one input in a way the report depends on and asserts
that evidence/P8-LUA-LIST/check_p8_lua_list.py exits NON-ZERO and says why.

  1. byte flip  - flip one byte of the instruction word the report cites at
                  collection_tips_list main.p2 pc108 (MOD). The report quotes
                  that opcode, so the check must reject it.
  2. setconst   - rewrite the string constant 'update_tips_list' the report
                  cites at collection_tips_list main.p1 pc62. The tool must
                  refuse without --allow-used; with it the check must report
                  the hash mismatch and the wrong constant.
  3. forbidden  - append a 'set_text_message' constant to collection_tips_list,
                  a name the report asserts is absent. The absence assertion
                  must fire.

Every control runs against a damaged COPY, selected with the check script's
P8_GD_ROOT / P5_GD_ROOT overrides. Nothing in gamedata/ is touched: the script
re-hashes the real files at the end and refuses to report success if they
changed.
"""
import hashlib
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "mods", "mii_customizer", "tools",
                                "lua53-inspect"))
import lua53_inspect as L  # noqa: E402

CHECK = os.path.join(ROOT, "mods", "mii_customizer", "evidence",
                     "P8-LUA-LIST", "check_p8_lua_list.py")
P8 = os.path.join(ROOT, "gamedata", "mii_customizer", "P8-LUA-LIST")
P5 = os.path.join(ROOT, "gamedata", "mii_customizer", "P5-UI-API")
CT = os.path.join(P8, "ui", "script", "menu", "collection",
                  "collection_tips_list.lc")
WORK = os.path.join(HERE, "negctl")


def sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def run_check(label, shadow=None, expect_nonzero=True):
    env = dict(os.environ)
    if shadow:
        env["P8_GD_ROOT"] = shadow
        env["P5_GD_ROOT"] = P5
    proc = subprocess.run([sys.executable, CHECK], cwd=ROOT, env=env,
                          capture_output=True, text=True)
    out = (proc.stdout or "") + (proc.stderr or "")
    rejected = proc.returncode != 0
    ok = rejected == expect_nonzero
    print("--- %s" % label)
    print("    exit %d  (%s)" % (proc.returncode,
                                "rejected, as required" if rejected else
                                ("accepted, as required" if not expect_nonzero
                                 else "NOT REJECTED")))
    for line in out.strip().splitlines()[:6]:
        print("    " + line)
    return ok, proc.returncode, out


def shadow_tree():
    """A full copy of the P8 gamedata tree that controls may damage."""
    dst = os.path.join(WORK, "shadow")
    if os.path.isdir(dst):
        shutil.rmtree(dst)
    shutil.copytree(os.path.join(P8, "ui"), os.path.join(dst, "ui"))
    return dst


def main_run():
    results = []
    if os.path.isdir(WORK):
        shutil.rmtree(WORK)
    os.makedirs(WORK)
    pristine_ct = sha(CT)
    pristine_ob = sha(os.path.join(
        P8, "ui", "script", "menu", "option", "option_button_top.lc"))

    ok, rc, _ = run_check("baseline, undamaged (must pass)",
                          expect_nonzero=False)
    results.append(("baseline", ok, rc))

    # ---- control 1: flip one byte of a cited instruction ----------------
    sh = shadow_tree()
    target = os.path.join(sh, "ui", "script", "menu", "collection",
                          "collection_tips_list.lc")
    with open(target, "rb") as fh:
        data = bytearray(fh.read())
    hdr, main = L.load_chunk(bytes(data))
    proto = L.find_proto(main, "main.p2")
    ins = proto.code[108]                    # MOD, cited by the report
    assert ins.name == "MOD", ins.name
    data[ins.offset] ^= 0x01
    with open(target, "wb") as fh:
        fh.write(bytes(data))
    ok, rc, out = run_check("control 1: flip one byte at main.p2 pc108 (MOD)",
                            shadow=sh)
    ok = ok and ("pc108" in out and "sha256" in out)
    results.append(("control 1 byte flip", ok, rc))

    # ---- control 2: setconst a cited constant ---------------------------
    sh = shadow_tree()
    target = os.path.join(sh, "ui", "script", "menu", "collection",
                          "collection_tips_list.lc")
    with open(target, "rb") as fh:
        hdr, main = L.load_chunk(fh.read())
    # the CLI refuses to touch a constant an instruction consumes
    cli = subprocess.run(
        [sys.executable, os.path.join(ROOT, "mods", "mii_customizer", "tools",
                                      "lua53-inspect", "lua53_inspect.py"),
         "setconst", CT, os.path.join(WORK, "cli_refused.lc"),
         "main.p1", "33", "update_tops_list"],
        cwd=ROOT, capture_output=True, text=True)
    refused = cli.returncode == 1
    print("--- control 2: CLI setconst without --allow-used")
    print("    exit %d (%s)" % (cli.returncode,
                                "refused" if refused else "NOT REFUSED"))
    for line in ((cli.stdout or "") + (cli.stderr or "")).strip().splitlines()[
            :4]:
        print("    " + line)
    L.set_string_constant(main, "main.p1", 33, "update_tops_list")
    with open(target, "wb") as fh:
        fh.write(L.encode_chunk(hdr, main))
    ok, rc, out = run_check(
        "control 2: 'update_tips_list' -> 'update_tops_list' (main.p1 pc62)",
        shadow=sh)
    ok = ok and refused and "sha256" in out
    results.append(("control 2 setconst", ok, rc))

    # ---- control 3: inject a name the report asserts is absent ----------
    sh = shadow_tree()
    target = os.path.join(sh, "ui", "script", "menu", "collection",
                          "collection_tips_list.lc")
    with open(target, "rb") as fh:
        hdr, main = L.load_chunk(fh.read())
    k = L.append_constant(main, hdr, "main.p2", "string", "set_text_message")
    print("--- control 3: appended 'set_text_message' as K[%d] in main.p2"
          % k.index)
    with open(target, "wb") as fh:
        fh.write(L.encode_chunk(hdr, main))
    ok, rc, out = run_check(
        "control 3: inject 'set_text_message' into collection_tips_list",
        shadow=sh)
    ok = ok and "set_text_message" in out
    results.append(("control 3 forbidden name", ok, rc))

    # ---- integrity: nothing under gamedata/ was modified ----------------
    same = sha(CT) == pristine_ct and sha(os.path.join(
        P8, "ui", "script", "menu", "option",
        "option_button_top.lc")) == pristine_ob
    print("--- gamedata/ untouched: %s (collection_tips_list sha256 %s)" %
          (same, sha(CT)))
    results.append(("gamedata untouched", same, 0))

    ok, rc, _ = run_check("post-control rerun (must pass)",
                          expect_nonzero=False)
    results.append(("post-control rerun", ok, rc))

    print()
    allok = all(r[1] for r in results)
    for label, good, code in results:
        print("%-28s %s (exit %d)" % (label, "OK" if good else "BAD", code))
    print()
    print("controls: %s" % ("ALL BEHAVED AS EXPECTED" if allok else
                            "SOME CONTROL DID NOT FIRE"))
    return 0 if allok else 1


sys.exit(main_run())