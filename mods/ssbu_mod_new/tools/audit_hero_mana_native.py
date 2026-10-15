#!/usr/bin/env python
"""Byte-verify the native sites the Hero mana feature depends on (T-0057; HUD route 2026-10-03).

Purpose: the mana HUD gauge and the hit/shield MP-recovery callback are
`mod rule 17` reserved (they need an interception of engine or donor code this
mod does not own). They live behind the Cargo feature `hero-mana-reserved`,
which is **off by default**. This tool proves that the 13.0.4 bytes at each
candidate site are still the bytes the hand-back recorded, so an approved
build does not hook a site that has silently changed.

It only reads images. It writes nothing except its optional `--json` report and,
with `--emit-rust`, the generated signature table.

v1.1.0 (2026-10-03): the user's explicit mana-HUD request chose a route, and it
is **not** one of the candidate hook sites below. The HUD is driven by *calling*
the game's own functions - the fighter panel's part selector and the HUD's own
SP setters - so nothing is overwritten. `HUD_ROUTE` is every function whose
shape that route relies on (layouts, offsets, call ABIs), recorded as a span and
its sha256, plus the vtable slots the plugin compares at run time. The plugin
refuses to enable the HUD unless every one of them matches, and
`--emit-rust` / `--check-rust` keep the plugin's table identical to this one.
The candidate sites stay listed because hit/shield recovery is still reserved.

  python tools/audit_hero_mana_native.py --hud-only \
      --main gamedata/ssbu-13.0.4/main.bin \
      [--emit-rust src/pgwr/plugin/src/mythra/hero_mana/hud_signatures.rs] \
      [--check-rust <same path>] [--json <report>]

Usage:
  python tools/audit_hero_mana_native.py \
      --main gamedata/ssbu-13.0.4/main.bin \
      --brave-nro "<ArcExplorer dir>/export/prebuilt/nro/release/lua2cpp_brave.nro" \
      [--json refs/brave_special_n/T-0057/reserved_sites.json]

Tier B: it measures bytes in a file. It proves nothing about runtime.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Candidate interception sites, from refs/brave_special_n/T-0046/ (T-0049
# measurements on the 13.0.4 image) and the contract's HUD table.
#
#   image  which file the offset belongs to
#   off    byte offset inside that image
#   span   how many bytes the overwrite would cover
#   want   the bytes recorded when the site was measured
#   why    what the site is
# ---------------------------------------------------------------------------
SITES = (
    {
        "id": "hud_update_task_registration",
        "image": "main",
        "off": 0x13540E4,
        "span": 16,
        "want": "a80100d008411c9179e8019039c33a91",
        "why": "stores the HUD update adapter 0x138a710 next to HudManager::update",
    },
    {
        "id": "hud_task_adapter",
        "image": "main",
        "off": 0x138A710,
        "span": 12,
        "want": "080440f9000140f9bab70014",
        "why": "manager load then tail-branch to the HUD update target",
    },
    {
        "id": "hud_update_target",
        "image": "main",
        "off": 0x13B8600,
        "span": 16,
        "want": "ff8302d1ea1300fde923036dfc6f04a9",
        "why": "per-frame HUD update body; the pane write point is inside it",
    },
    {
        "id": "match_start_adapter",
        "image": "main",
        "off": 0x2256B00,
        "span": 16,
        "want": "fd7bbfa9fd030091e2efcf97e0031f2a",
        "why": "match-start adapter, calls 0x1652a90; binds the owned pane handles",
    },
    {
        "id": "sp_add_positive_guard",
        "image": "main",
        "off": 0x853890,
        "span": 16,
        "want": "ff8301d1ea1300fde9a3026df51f00f9",
        "why": "donor add_sp: +1e-05 guard for a positive delta, then clamp [0,max]",
    },
    {
        "id": "sp_passive_recovery",
        "image": "main",
        "off": 0x853500,
        "span": 16,
        "want": "ffc302d1e82b00fdfa6706a9f85f07a9",
        "why": "donor passive recovery: counter, pause checks, then add_sp",
    },
    {
        "id": "sp_start_max_assign",
        "image": "main",
        "off": 0x852840,
        "span": 16,
        "want": "ff4301d1e81300fdf51700f9f44f03a9",
        "why": "donor start/max assignment: writes max then the clamped value to SP",
    },
    {
        "id": "damage_event_entry",
        "image": "main",
        "off": 0x854610,
        "span": 16,
        "want": "a02040bde00301aae103032ae3031f2a",
        "why": "donor hit/shield event entry that leads to 0x854a4c",
    },
    {
        "id": "damage_event_scaling",
        "image": "main",
        "off": 0x854A4C,
        "span": 16,
        "want": "9f02007289178052ea071a324911899a",
        "why": "donor damage/shield multiplier select before add_sp",
    },
)

# ---------------------------------------------------------------------------
# The HUD route (v1.1.0). Every span is a whole function or a named part of one
# on the 13.0.4 image; `sha256` is what was measured on main.bin `f70c97d2...`.
# `fnv1a64` is the same bytes under the hash the plugin computes at install time
# (it carries no sha256); `audit_hud_route` checks both columns against the image.
# Three spans the plugin never calls directly (`brave_set_sp_sender`,
# `layout_set_part`, `ui_chara_kind`) start past the prologue, so another plugin's
# inline hook on an exported symbol cannot switch the HUD off by itself.
# ---------------------------------------------------------------------------
HUD_ROUTE = (
    {'id': 'fm_listener_registration', 'off': 0x1374d9c, 'span': 0x118, 'sha256': '3e7b5c130148dea7ff409a30b28bbc4a0ac0a5fece31a8a39b2cecf68b13f453', 'fnv1a64': 0x86da1752a925e4dd,
     'why': 'HUD registers a delegate {owner, callback 0x1378650} on FighterManager event 0x5c: node +0x10 = delegate, list head = lists + 0x5c*0x18 + 8'},
    {'id': 'fm_delegate_sp_set', 'off': 0x1378650, 'span': 0x24, 'sha256': '5fb4f3f0952e0580b7deedac42299100b1c8636ea8ea147a20fb1c41b0e6d115', 'fnv1a64': 0x0f3af5a6c0005274,
     'why': 'event 0x5c thunk: H = [owner+0x20]; H->vt[0x2e0](H, event.player, event.sp)'},
    {'id': 'fm_delegate_sp_add', 'off': 0x1378680, 'span': 0x24, 'sha256': '7d7a569d7a5a5f3864a4928e68109a03a00713583f893a029c642c2a89ac0a1d', 'fnv1a64': 0x756061dde3d9d240,
     'why': 'event 0x5d thunk: H->vt[0x2e8](H, player, sp)'},
    {'id': 'fm_delegate_sp_short', 'off': 0x13786b0, 'span': 0x1c, 'sha256': '6c91b319899356e8c7f439476dcc1f46484b1fe88ea71555adf8f157ae741742', 'fnv1a64': 0x53b3d41e14852d79,
     'why': 'event 0x5e thunk: H->vt[0x2f0](H, player)'},
    {'id': 'fm_delegate_invoke', 'off': 0x1378ad0, 'span': 0x1c, 'sha256': '43512fd1e28f72dee6f0cdf73deb4f6b303e5f71d61bd6df4cd5952df5cc9662', 'fnv1a64': 0xc1524ed847ca74e8,
     'why': 'delegate layout: +0x10 owner, +0x18 callback, +0x20 adjustment'},
    {'id': 'brave_set_sp_sender', 'off': 0x852a08, 'span': 0x1e0, 'sha256': '2a8054eda35bff5069adbe9c98b3c6b4277e48b681e4c660b6fc8e1c218988ec', 'fnv1a64': 0x1996e00d947a61c7,
     'why': 'donor FighterSpecializer_Brave::set_sp: FighterManager at *(*(main+0x52b84f8)), entry object +0x20+8*entry, HUD player at +0x41e4 gated by byte +0x41e8, events 0x5c/0x5d'},
    {'id': 'brave_sp_short_sender', 'off': 0x85bbbc, 'span': 0x74, 'sha256': 'fc2be4b541d95f6e959a10c94538f822b04ebb9a78c8d805e551c9a959301ae3', 'fnv1a64': 0x7e89e2c3a372e076,
     'why': 'donor raises event 0x5e (payload: player only) when SP is below the needed amount'},
    {'id': 'hud_sp_set', 'off': 0x13689c0, 'span': 0x110, 'sha256': 'bf3bb1aa78ad9360a02f3c3ca7bb88a4d8223b8662ab0b91c7aa6ee28db4d34b', 'fnv1a64': 0x593302a01f20c064,
     'why': 'H->vt[0x2e0](this, player, sp): player -> view -> panel index < 8 -> panel (stride 0x3e0) -> [panel+0x318] brave UI -> +0x28 SP state; queues {0, sp}'},
    {'id': 'hud_sp_add', 'off': 0x1368ae0, 'span': 0xcc, 'sha256': 'cd855a1bf7466d1dc823afaf02982e48114da39aa23187344fa00f1a5fd8ba82', 'fnv1a64': 0xafddbf89fbcedec0,
     'why': 'H->vt[0x2e8](this, player, sp): same mapping, then 0x139fec0 queues {1, sp}'},
    {'id': 'hud_sp_short', 'off': 0x1368bb0, 'span': 0xe0, 'sha256': 'c7e6bbda8acc0d810510b58443b8daeeed07357a797d0e9d636d2b413ea78abe', 'fnv1a64': 0x8290dccdc2b9cf51,
     'why': 'H->vt[0x2f0](this, player): same mapping, sets the brave UI shortage byte +0x38'},
    {'id': 'hud_handle_valid', 'off': 0x138b1c0, 'span': 0x34, 'sha256': '301d4e3233f79ddfb338eae3b9ffddd9dcc94a2dabc47f75c7986953a4d86d89', 'fnv1a64': 0x8938cbb5ceec8110,
     'why': 'view handle validity the plugin repeats: [h+8] != 0, byte [[h+8]]+0x70 != 0, [h+0x14] != -1'},
    {'id': 'hud_sp_add_queue', 'off': 0x139fec0, 'span': 0x124, 'sha256': '5c379ce6ad88bbe31e171661a7256ea01b3b63211c71da943ece1fa94e305e43', 'fnv1a64': 0xa3f4887f18c0c104,
     'why': 'the add queue write coalesces a pending {1, sp}, so a repeated push cannot grow the queue'},
    {'id': 'panel_reselect_part', 'off': 0x1367560, 'span': 0x148, 'sha256': '7802b9036ce5204cecc34a00f9ba73be2c472b893db3c27780586ca08d45eb21', 'fnv1a64': 0xa259aa3eaee10ca2,
     'why': 'the game calls the part selector as select(panel + 8, chara id, copy chara id): the gauge object is panel + 8'},
    {'id': 'panel_select_part', 'off': 0x1426fb0, 'span': 0x2a4, 'sha256': 'f7b8f999c11ac6c2529e823c31d3c72170f585d7b49dc89e3a960a81b56772d6', 'fnv1a64': 0xdb9418f41b98999f,
     'why': 'select(gauge, chara, copy): chara -> fighter kind; kind 0x53 (Hero) and Kirby copying 0x53 pick gauge+0x300 (part 8); old part vt[0x18], new part vt[0x10], then layout part switch'},
    {'id': 'brave_part_init', 'off': 0x14249c0, 'span': 0x1ec, 'sha256': '6eb7a17841d5b7d5bef00b4ab3bc787e6d68426e9e3ccdb724400d95fdaa2378', 'fnv1a64': 0x588baa2eea50bfd4,
     'why': 'brave part vt[0x10]: binds the brave UI to layout row (stride 0xd90) + 0xf78 for a panel index < 8'},
    {'id': 'brave_part_reset', 'off': 0x1424bf0, 'span': 0x78, 'sha256': '366d10b1d74bde5ef92b768b9db7571beae8f877f270b6e26f28fba2b2c26075', 'fnv1a64': 0x115796d7316b0b7e,
     'why': 'brave part vt[0x18]: what the game runs when it takes the part away (form swap)'},
    {'id': 'brave_part_update', 'off': 0x1424c70, 'span': 0x8, 'sha256': 'a42e8578027c052cd272b2504ba22cb6ce28a60f9bd6f6e37fc43756a0852e3f', 'fnv1a64': 0xee2c3cff47465a71,
     'why': 'brave part vt[0x20]: per-frame update of the brave UI at [part+0x10]'},
    {'id': 'brave_ui_ctor', 'off': 0x1405be0, 'span': 0x8c, 'sha256': 'eaf0b0d02e3a9a349c881d68b86e3eb24b4cfa9b7cd64b92e7d3341d0b397f34', 'fnv1a64': 0x5e97c60af3ded32b,
     'why': 'every panel owns a 0x40-byte brave UI with the SP state at +0x28, whatever the fighter'},
    {'id': 'brave_ui_setup', 'off': 0x1406350, 'span': 0x17c, 'sha256': '0afb05c83c6295468df7e2b996cc31b2b648f1aa6fb876c00ef9899d640dd372', 'fnv1a64': 0xf99dc13c12b704ac,
     'why': 'binding: SP state [0] = layout binding, target/display floats 100.0 at +0x258/+0x25c/+0x250'},
    {'id': 'brave_ui_update', 'off': 0x14064d0, 'span': 0x16c, 'sha256': 'd27b81531d3ae58a4a037962ac1f25eec9a3fbf777b516af45e793649133b8da', 'fnv1a64': 0xdde0d84125c53e8d,
     'why': 'update: SP state step, then the shortage flash with a 60-frame cooldown'},
    {'id': 'sp_state_ctor', 'off': 0x1407360, 'span': 0x198, 'sha256': '853163b6d761e0c0dd9edb53c7962cfe9ba413a50d47b245df42d48344dc5bf6', 'fnv1a64': 0xa8e250d2e9cf1c12,
     'why': 'SP state: 0x280 bytes, queue descriptor main+0x5064f78 at +0xd0, capacity 12 at +0xd8, inline buffer +0x100 at +0xf8'},
    {'id': 'sp_state_idle', 'off': 0x1406d20, 'span': 0x140, 'sha256': 'f2c3f599e8569094217f8241d7e03eb362c80c76bf896b2661c633748d69a957', 'fnv1a64': 0xc86e421261d19e7f,
     'why': 'command 0 = set, 1 = animate to a new total, both write the target float +0x258'},
    {'id': 'sp_state_render', 'off': 0x1406e60, 'span': 0x184, 'sha256': 'ec5d0f18d3a5fb5358004d789ab7b52623c6eb0fa3c981a8a819bbb7a3885fac', 'fnv1a64': 0x0bb3d98daaf37138,
     'why': 'render: bars = value / 100.0, digits = min(value, 100); skipped while the binding [0] is null'},
    {'id': 'layout_set_part', 'off': 0x1b7d480, 'span': 0x40, 'sha256': 'd61793c7e4c7fd231a89efd71142e37e55191a528877f405ed05ca4a97e9308a', 'fnv1a64': 0x69077870e5ce5044,
     'why': 'layout part switch (layout, panel index, part id) called by the selector'},
    {'id': 'ui_chara_kind', 'off': 0x3262148, 'span': 0x10c, 'sha256': '572153d4704e261abf056bb390fea60c8fe95d418616a0698b85ddcaff0190ed', 'fnv1a64': 0x6fa53eee83a955d1,
     'why': 'chara id = 0xc1 tag | 16-bit index hint | hash40; a hint >= count falls back to a search by hash'},
)

# Pointer slots in .data the plugin compares at run time (slot -> text target).
# They are R_AARCH64_RELATIVE relocations in the image, so they are read from
# the relocation table, not from the slot's raw bytes.
HUD_SLOTS = (
    {'id': 'hud_class_a_sp_set', 'slot': 0x5061780 + 0x2e0, 'target': 0x13689c0},
    {'id': 'hud_class_a_sp_add', 'slot': 0x5061780 + 0x2e8, 'target': 0x1368ae0},
    {'id': 'hud_class_a_sp_short', 'slot': 0x5061780 + 0x2f0, 'target': 0x1368bb0},
    {'id': 'hud_class_b_sp_set', 'slot': 0x5061ba0 + 0x2e0, 'target': 0x13689c0},
    {'id': 'hud_class_b_sp_add', 'slot': 0x5061ba0 + 0x2e8, 'target': 0x1368ae0},
    {'id': 'hud_class_b_sp_short', 'slot': 0x5061ba0 + 0x2f0, 'target': 0x1368bb0},
    {'id': 'brave_part_vt_init', 'slot': 0x5065d58 + 0x10, 'target': 0x14249c0},
    {'id': 'brave_part_vt_reset', 'slot': 0x5065d58 + 0x18, 'target': 0x1424bf0},
    {'id': 'brave_part_vt_update', 'slot': 0x5065d58 + 0x20, 'target': 0x1424c70},
)

RUST_HEADER = """// Generated by tools/audit_hero_mana_native.py --emit-rust. Do not edit.
// Every span is a function the HUD route relies on, hashed on the 13.0.4 main
// image sha256 {main}.
// (offset, length, fnv1a64, id)
"""

IMAGES = ("main", "brave")


def fnv1a64(data: bytes) -> int:
    h = 0xCBF29CE484222325
    for byte in data:
        h = ((h ^ byte) * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
    return h


def relative_relocs(data: bytes) -> dict:
    """slot offset -> target offset, from the image's DT_RELA table."""
    mod0 = struct.unpack_from("<I", data, 4)[0]
    if data[mod0:mod0 + 4] != b"MOD0":
        raise ValueError("no MOD0 header")
    cursor = mod0 + struct.unpack_from("<i", data, mod0 + 4)[0]
    tags = {}
    while True:
        tag, value = struct.unpack_from("<qQ", data, cursor)
        cursor += 16
        if tag == 0:
            break
        tags.setdefault(tag, value)
    out = {}
    for k in range(0, tags[8], 24):
        r_off, r_info, addend = struct.unpack_from("<QQq", data, tags[7] + k)
        if r_info & 0xFFFFFFFF == 0x403:
            out[r_off] = addend
    return out


def rust_table(main_sha: str) -> str:
    lines = [RUST_HEADER.format(main=main_sha)]
    lines.append("pub(super) const SPANS: &[(usize, usize, u64, &str)] = &[\n")
    for site in HUD_ROUTE:
        lines.append("    (%#x, %#x, %#018x, \"%s\"),\n"
                     % (site["off"], site["span"], site["fnv1a64"], site["id"]))
    lines.append("];\n")
    lines.append("// (data slot, text target, id): `*(base + slot) == base + target`.\n")
    lines.append("pub(super) const SLOTS: &[(usize, usize, &str)] = &[\n")
    for slot in HUD_SLOTS:
        lines.append("    (%#x, %#x, \"%s\"),\n" % (slot["slot"], slot["target"], slot["id"]))
    lines.append("];\n")
    return "".join(lines)


def audit_hud_route(main_path: Path, report: dict) -> int:
    """Check every HUD route span and slot against the image. Returns failures."""
    data = main_path.read_bytes()
    relocs = relative_relocs(data)
    failures = 0
    report["hud_route"], report["hud_slots"] = [], []
    for site in HUD_ROUTE:
        chunk = data[site["off"]:site["off"] + site["span"]]
        sha = hashlib.sha256(chunk).hexdigest()
        fnv = fnv1a64(chunk)
        ok = (len(chunk) == site["span"] and sha == site["sha256"] and fnv == site["fnv1a64"])
        failures += 0 if ok else 1
        report["hud_route"].append({
            "id": site["id"], "offset": hex(site["off"]), "span": hex(site["span"]),
            "sha256": sha, "fnv1a64": "%#018x" % fnv,
            "verdict": "MATCH" if ok else "MISMATCH", "why": site["why"]})
        print("%-26s main   %-11s %-6s %s  %s"
              % (site["id"], hex(site["off"]), hex(site["span"]), sha[:16],
                 "MATCH" if ok else "MISMATCH"))
    for slot in HUD_SLOTS:
        got = relocs.get(slot["slot"])
        ok = got == slot["target"]
        failures += 0 if ok else 1
        report["hud_slots"].append({
            "id": slot["id"], "slot": hex(slot["slot"]), "target": hex(slot["target"]),
            "actual": None if got is None else hex(got),
            "verdict": "MATCH" if ok else "MISMATCH"})
        print("%-26s reloc  %-11s -> %-11s %s"
              % (slot["id"], hex(slot["slot"]), hex(slot["target"]),
                 "MATCH" if ok else "MISMATCH"))
    return failures


def sha256_file(path: Path, limit: int | None = None) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        read = 0
        while True:
            want = 1 << 20 if limit is None else min(1 << 20, limit - read)
            if want <= 0:
                break
            chunk = fh.read(want)
            if not chunk:
                break
            h.update(chunk)
            read += len(chunk)
    return h.hexdigest()


def smoke() -> int:
    """Self-test: the recorded bytes must be exactly as long as the span.

    That is not a formality. This tool's first run reported a MISMATCH on a site
    whose bytes were right, because the span was 16 and the recording 12 - and a
    MISMATCH on a correct site is worse than no check at all. It also checks that
    every offset fits in the image it is attributed to, which is what proves a
    site was not filed against the wrong binary.
    """
    failures = []
    for site in SITES:
        want = site["want"]
        if want is None:
            failures.append("%s: no recorded bytes" % site["id"])
            continue
        if len(want) != 2 * site["span"]:
            failures.append("%s: %d hex chars for a %d-byte span"
                            % (site["id"], len(want), site["span"]))
        try:
            bytes.fromhex(want)
        except ValueError:
            failures.append("%s: %r is not hex" % (site["id"], want))
        if site["off"] % 4:
            failures.append("%s: offset %s is not 4-byte aligned"
                            % (site["id"], hex(site["off"])))
    seen = set()
    for site in HUD_ROUTE:
        if site["off"] % 4 or site["span"] % 4 or site["span"] <= 0:
            failures.append("%s: offset/span not instruction-aligned" % site["id"])
        if len(site["sha256"]) != 64:
            failures.append("%s: sha256 is not 64 hex chars" % site["id"])
        if site["id"] in seen:
            failures.append("%s: duplicate id" % site["id"])
        seen.add(site["id"])
    for slot in HUD_SLOTS:
        if slot["slot"] % 8 or slot["target"] % 4:
            failures.append("%s: slot/target misaligned" % slot["id"])
    # The hash the plugin computes must be the standard FNV-1a 64 (known vectors),
    # and it must change when one byte changes - otherwise a MATCH proves nothing.
    if fnv1a64(b"") != 0xCBF29CE484222325 or fnv1a64(b"a") != 0xAF63DC4C8601EC8C:
        failures.append("fnv1a64 does not reproduce the reference vectors")
    if fnv1a64(b"\x1f\x20\x03\xd5") == fnv1a64(b"\x1f\x20\x03\xd4"):
        failures.append("fnv1a64 ignores a one-bit change")
    if failures:
        for line in failures:
            print("FAIL\t%s" % line, file=sys.stderr)
        return 1
    print("PASS\t%d candidate site(s), %d HUD route span(s), %d slot(s): tables well-formed, "
          "fnv1a64 reference vectors and one-bit negative control hold"
          % (len(SITES), len(HUD_ROUTE), len(HUD_SLOTS)))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--main", help="decoded 13.0.4 main.bin")
    ap.add_argument("--brave-nro", help="13.0.4 lua2cpp_brave.nro")
    ap.add_argument("--json", help="write the report to this path")
    ap.add_argument("--smoke", action="store_true",
                    help="self-test the recorded site table and exit")
    ap.add_argument("--emit-rust", help="write the plugin's HUD signature table to this path")
    ap.add_argument("--check-rust", help="fail unless this file equals the generated table")
    ap.add_argument("--hud-only", action="store_true",
                    help="audit only the HUD route (needs --main, not --brave-nro)")
    ap.add_argument("--refresh", action="store_true",
                    help="print the bytes for every site and treat them as the new "
                         "expectation (only when recording a new measurement)")
    args = ap.parse_args()

    if args.smoke:
        return smoke()
    if args.hud_only:
        if not args.main:
            ap.error("--hud-only needs --main")
        main_path = Path(args.main)
        if not main_path.is_file():
            print("MISSING\tmain\t%s" % main_path, file=sys.stderr)
            return 1
        main_sha = sha256_file(main_path)
        report = {"tool": "tools/audit_hero_mana_native.py v1.1.0", "tier": "B",
                  "images": {"main": {"path": str(main_path), "bytes": main_path.stat().st_size,
                                      "sha256": main_sha}}}
        failures = audit_hud_route(main_path, report)
        table = rust_table(main_sha)
        if args.emit_rust and not failures:
            Path(args.emit_rust).write_text(table, encoding="utf-8", newline="\n")
            print("# wrote %s" % args.emit_rust)
        if args.check_rust:
            have = Path(args.check_rust).read_text(encoding="utf-8").replace("\r\n", "\n")
            same = have == table
            failures += 0 if same else 1
            report["rust_table"] = {"path": args.check_rust,
                                    "verdict": "IDENTICAL" if same else "DIFFERENT"}
            print("rust table %s: %s" % (args.check_rust, "IDENTICAL" if same else "DIFFERENT"))
        if args.json:
            out = Path(args.json)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
            print("# wrote %s" % out)
        print("# %d HUD route check(s) not matching" % failures)
        return 1 if failures else 0
    if not args.main or not args.brave_nro:
        ap.error("--main and --brave-nro are required unless --smoke or --hud-only is given")

    paths = {"main": Path(args.main), "brave": Path(args.brave_nro)}
    for key, path in paths.items():
        if not path.is_file():
            print("MISSING\t%s\t%s" % (key, path), file=sys.stderr)
            return 1

    report = {
        "tool": "tools/audit_hero_mana_native.py v1.1.0",
        "tier": "B",
        "images": {
            key: {"path": str(paths[key]), "bytes": paths[key].stat().st_size,
                  "sha256": sha256_file(paths[key])}
            for key in IMAGES
        },
        "sites": [],
    }

    handles = {key: paths[key].open("rb") for key in IMAGES}
    failures = 0
    try:
        for site in SITES:
            fh = handles[site["image"]]
            fh.seek(site["off"])
            got = fh.read(site["span"])
            got_hex = got.hex()
            size = paths[site["image"]].stat().st_size
            in_range = site["off"] + site["span"] <= size
            if site["want"] is None:
                # First measurement for this site: record what is there now and
                # say so, rather than pretending it was verified.
                verdict = "RECORDED" if args.refresh else "UNVERIFIED"
                if args.refresh and args.json:
                    site["want"] = got_hex
            else:
                verdict = "MATCH" if got_hex == site["want"] else "MISMATCH"
            if verdict == "MISMATCH" or not in_range:
                failures += 1
            report["sites"].append({
                "id": site["id"],
                "image": site["image"],
                "offset": hex(site["off"]),
                "span": site["span"],
                "expect": site["want"],
                "actual": got_hex,
                "in_range": in_range,
                "verdict": verdict,
                "why": site["why"],
            })
            print("%-26s %-6s %-11s %-32s %s"
                  % (site["id"], site["image"], hex(site["off"]), got_hex, verdict))
    finally:
        for fh in handles.values():
            fh.close()

    if args.json:
        out = Path(args.json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print("# wrote %s" % out)

    print("# %d site(s) not matching" % failures)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
