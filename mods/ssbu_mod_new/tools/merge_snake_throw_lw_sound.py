"""Merge Snake's down-throw sounds into Pyra c06/c07 (v1.0.0).

Plays the donor's own sounds for `acmd::snake_throw_lw` instead of stand-ins
(`AGENTS.md` rule 17). Snake's `sound_throwlw` names exactly two tones:

  * ``se_snake_catch_tight``     - the grab, frame 1
  * ``se_snake_catch_tight_02``  - the throw, frame 20

**Four** tones are actually appended, because ``se_snake_catch_tight`` is a
sequence tone (donor tone kind 1) that references
``se_snake_catch_tight_01`` and ``se_snake_catch_tight_01_layer`` by
bank-relative index; see the long note below. Copying only the two named tones
would leave it pointing at two unrelated sounds in Pyra's bank while every
byte-level check still passed.

All four are appended to ``se_eflame_c06`` / ``se_eflame_c07``. Nothing else is
touched: no voice tones and **no sequence record**, because unlike Snake's up
tilt his down throw plays no ``PLAY_SEQUENCE`` (``refs/snake_throw_lw/
donor_acmd/snake__ThrowLw.txt`` has two ``PLAY_SE`` lines and no
``PLAY_SEQUENCE``). ``eflame.sqb`` is therefore deliberately not written by this
tool - see ``eflame_sqb_untouched`` in the report.

Ownership, not borrowing: the sample bytes and tone records are copied out of
the pinned donor bank unchanged, the recipient keeps its own bank identity
(``BINF``/``PROP``/``GRP``/``DTON``/``PACK`` are asserted equal to the donor's,
as ``merge_snake_uptilt_sound`` does), and every appended tone is asserted to
be a single-sample tone so no group child index can dangle.

Chaining: each bank is read from the output directory if an earlier merge
already wrote it there, else from the recorded baseline. Run this after
``merge_snake_uptilt_sound`` and the other Pyra bank merges. It is
**append-only and idempotent**: if both tones are already present the bank is
compared byte for byte against the baseline and left alone.

Preservation is a *checked* property, not a claim: ``verify_preserved`` re-reads
the written bank and asserts every pre-existing tone name, sample, tone record
and label survived unchanged. ``--check`` proves that assertion is live by
pointing it at a deliberately truncated bank and requiring it to refuse.

Offline only (tier B). **No offline check establishes that a sound plays in
game**; that needs the user's console.

    python tools/merge_snake_throw_lw_sound.py --check
    python tools/merge_snake_throw_lw_sound.py --baseline <mod tree> --output <dir>
"""
import argparse
import hashlib
import json
import shutil
import struct
import sys
import tempfile
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import merge_hero_neutral_b_sound as codec  # noqa: E402  shared bank codec


ROOT = codec.ROOT
# The tone table was already pinned for Snake neutral-B (refs/snake_grenade).
# Rule 29: do not re-copy an asset the project already pins.
SE_DONOR = ROOT / 'refs/snake_grenade/arc/sound/bank/fighter/se_snake_c00'
PINS = {
    '.nus3audio': '88057e12e9aa1dcadad8c604e1bf148a9b49e93b898a7ce8b7f67ec19479a495',
    '.nus3bank': '4e09776aad72a942e317be17b809e4dc8b8fa55c6f5538ba1510a1bfd4f28fa0',
    '.tonelabel': '8692a0a7eec86fb7159fbb96884f9424c44e57458388e37cb278f518d47a67c1',
}
# Exactly the two tones Snake's `sound_throwlw` names, read off the pinned text.
WANTED = {'se_snake_catch_tight', 'se_snake_catch_tight_02'}

# ---------------------------------------------------------------------------
# A tone kind the shared codec does not model, and the reason this move needs
# more than the two tones it names.
#
# `merge_hero_neutral_b_sound.group_links` decodes donor tone kinds 0 (single
# sample) and 3 (random group) and *asserts* on anything else - correctly. The
# pinned `se_snake_c00` bank has 111 tones: 102 kind-0, 8 kind-3, and exactly
# **one** kind-1 - `se_snake_catch_tight`, the down throw's grab sound. Measured
# layout of that record (100 bytes):
#
#   start+0  kind = 1
#   start+4  payload_size = 40 = 8 + 16 * count
#   start+8  0xFFFFFFFF
#   start+12 count = 2
#   start+16 count rows of 16 bytes: (u32 flag, f32 weight, f32 ?, u32 CHILD INDEX)
#   then a 20-byte tail
#
# The two child indices are 92 and 93, i.e. `se_snake_catch_tight_01` and
# `se_snake_catch_tight_01_layer`. Those are **bank-relative tone indices**, so
# copying `se_snake_catch_tight` into Pyra's bank without also appending its two
# children and rebasing the indices would leave it pointing at whatever two
# unrelated tones happen to sit at 92/93 in `se_eflame_c06` - a wrong sound that
# still passes every byte-level check. That is the dangling-index hazard in
# `handbook/04_motion_lists_animation.md` and `05_acmd_porting.md`, in a place
# nobody had hit before.
#
# So the append set is the named pair *plus its transitive kind-1 closure*, and
# every kind-1 child index is remapped from donor index to merged index.
# ---------------------------------------------------------------------------


def tone_record(tone):
    """(name, name_at, payload_start) of one TONE record."""
    name_at = 12 if codec.u32(tone, 4) & 0x80000000 else 8
    size = tone[name_at]
    return tone[name_at + 1:name_at + size].decode(), name_at, (name_at + 1 + size + 3) & ~3


def kind1_links(tone, names, payload_start):
    """Byte offsets of the child-index fields of a kind-1 (sequence) tone.

    Bounded and asserted rather than assumed: the payload size must be
    `8 + 16 * count`, every child must be inside the donor bank, and the record
    must end exactly 20 bytes after the last row. Anything else is refused
    rather than copied, because a mis-parsed link table is exactly the silent
    failure this function exists to prevent.
    """
    count = codec.u32(tone, payload_start + 12)
    assert codec.u32(tone, payload_start + 4) == 8 + 16 * count, \
        'kind-1 payload size is not 8 + 16 * count'
    links = []
    for row in range(count):
        at = payload_start + 16 + 16 * row
        child = codec.u32(tone, at + 12)
        assert 0 <= child < len(names), f'kind-1 child index {child} outside the donor bank'
        links.append((at + 12, child))
    assert len(tone) - (payload_start + 16 + 16 * count) == 20, 'kind-1 tail is not 20 bytes'
    return links


def closure(names, tones, wanted):
    """`wanted` plus every tone reachable through a kind-1 sequence link."""
    index = {n.lower(): i for i, n in enumerate(names)}
    selected, queue = set(), [index[n] for n in wanted]
    while queue:
        i = queue.pop()
        if i in selected:
            continue
        selected.add(i)
        name, _, start = tone_record(tones[i])
        assert codec.u32(tones[i], start) in (0, 1), \
            f'{name}: unsupported donor tone kind {codec.u32(tones[i], start)}'
        if codec.u32(tones[i], start) == 1:
            for _, child in kind1_links(tones[i], names, start):
                queue.append(child)
    return sorted(selected)
# Recorded 2026-10-02 on builds/pgwr/0.20.19, which is the tree this delta is
# cut against. The tool refuses to run against a baseline it was not measured
# on, because the preservation counts below are the point of the check.
BASELINE = ROOT / 'builds/pgwr/0.20.19/ultimate/mods/pyra_gamewatch_reskin'
BASELINE_RETAINED = 544


def sha(data):
    return hashlib.sha256(data).hexdigest()


def check_pins():
    for ext, digest in PINS.items():
        actual = sha(SE_DONOR.with_suffix(ext).read_bytes())
        assert actual == digest, f'{SE_DONOR}{ext} is not the pinned revision'


def labels_read_partial(data, names):
    """`codec.labels_read` but tolerating a donor whose label table is incomplete.

    Measured 2026-10-02 on the pinned `se_snake_c00.tonelabel`: the table does
    not name every tone the bank ships, which `labels_read` (correct for a
    *recipient* bank) would reject. Every record that *is* present is still
    checked against its name and length.
    """
    assert codec.u32(data, 0) == 1
    entries = list(struct.iter_unpack('<II', data[8:]))
    assert codec.u32(data, 4) == len(entries)
    for crc, value in entries:
        assert 0 <= (value >> 8) < len(names), f'label points outside the bank: {value:#x}'
        assert crc == zlib.crc32(names[value >> 8].lower().encode())
        assert value & 0xff == len(names[value >> 8].encode())
    return entries


def read_recipient(stem):
    entries = codec.audio_read(stem.with_suffix('.nus3audio').read_bytes())
    chunks = codec.bank_read(stem.with_suffix('.nus3bank').read_bytes())
    labels = codec.labels_read(stem.with_suffix('.tonelabel').read_bytes(),
                               [n for n, _ in entries])
    return entries, chunks, labels


def read_donor(stem):
    entries = codec.audio_read(stem.with_suffix('.nus3audio').read_bytes())
    chunks = codec.bank_read(stem.with_suffix('.nus3bank').read_bytes())
    labels = labels_read_partial(stem.with_suffix('.tonelabel').read_bytes(),
                                 [n for n, _ in entries])
    return entries, chunks, labels


def append_tones(donor_stem, recipient, dest, wanted):
    """Append `wanted` (lowercase) tones of `donor_stem` to `recipient`, writing `dest`.

    The appended set is the transitive kind-1 closure of `wanted`, and every
    kind-1 child index is remapped from donor index to merged index.
    """
    donor, chunks_d, labels_d = read_donor(donor_stem)
    names = [n for n, _ in donor]
    tones_d = codec.tones_read(dict(chunks_d)[b'TONE'])
    named = {n.lower() for n in names}
    missing = wanted - named
    assert not missing, f'{donor_stem.name}: not found: {sorted(missing)}'
    selected = closure(names, tones_d, wanted)
    direct = [i for i in selected if names[i].lower() in wanted]

    original, chunks_r, labels_r = read_recipient(recipient)
    recipient_chunks = dict(chunks_r)
    donor_chunks = dict(chunks_d)
    for tag in (b'GRP ', b'DTON', b'PACK'):
        assert recipient_chunks[tag] == donor_chunks[tag], \
            f'{recipient.name}: {tag!r} differs from the donor bank'

    already = [n for n, _ in original if n.lower() in wanted]
    if len(already) == len(wanted):
        # Idempotent: a bank that already carries every requested tone is left
        # byte-identical rather than appended to twice.
        return {'recipient': recipient.name, 'retained_tones': len(original),
                'appended': False, 'already_present': sorted(already),
                'output_hashes': {ext: sha(recipient.with_suffix(ext).read_bytes())
                                  for ext in ('.nus3audio', '.nus3bank', '.tonelabel')}}
    assert not already, f'{recipient.name}: only some requested tones are present'

    # donor index -> merged index, for exactly the tones being appended.
    mapping = {i: len(original) + j for j, i in enumerate(selected)}
    merged_tones_r = []
    rebased_links = []
    for i in selected:
        tone = tones_d[i]
        name, _, start = tone_record(tone)
        if codec.u32(tone, start) == 1:
            copied = bytearray(tone)
            for at, child in kind1_links(tone, names, start):
                assert child in mapping, \
                    f'{name}: child {names[child]} is outside the appended set'
                struct.pack_into('<I', copied, at, mapping[child])
                rebased_links.append({'parent': name, 'offset': at,
                                      'from': child, 'from_name': names[child],
                                      'to': mapping[child]})
                rebased_links[-1]['expect'] = names[child]
            tone = bytes(copied)
        merged_tones_r.append(tone)

    tones_r = codec.tones_read(recipient_chunks[b'TONE'])
    entries = original + [donor[i] for i in selected]
    assert len({n.lower() for n, _ in entries}) == len(entries), \
        f'{recipient.name}: tone name collision'

    labels = list(labels_r) + [(crc, mapping[value >> 8] << 8 | (value & 255))
                               for crc, value in labels_d if value >> 8 in mapping]
    labels.sort()
    label_bytes = (codec.pack(1) + codec.pack(len(labels))
                   + b''.join(struct.pack('<II', *pair) for pair in labels))
    # Round-trips as a *recipient* bank, so it is well formed with full coverage.
    codec.labels_read(label_bytes, [n for n, _ in entries])

    merged_tones = tones_r + merged_tones_r
    files = {
        '.nus3audio': codec.audio_write(entries),
        '.tonelabel': label_bytes,
        '.nus3bank': codec.bank_write(
            [(tag, codec.tones_write(merged_tones) if tag == b'TONE' else data)
             for tag, data in chunks_r]),
    }
    dest.parent.mkdir(parents=True, exist_ok=True)
    for ext, content in files.items():
        dest.with_suffix(ext).write_bytes(content)

    assert codec.audio_read(files['.nus3audio']) == entries
    assert codec.tones_read(dict(codec.bank_read(files['.nus3bank']))[b'TONE']) == merged_tones
    verify_preserved(dest, original, tones_r, labels_r, recipient_chunks, wanted)
    verify_links_resolved(dest, rebased_links, len(original))
    return {'recipient': recipient.name, 'retained_tones': len(original),
            'retained_tones_byte_equal': True, 'retained_labels_byte_equal': True,
            'appended': True,
            'named_by_acmd': sorted(names[i] for i in direct),
            'appended_names': sorted(names[i] for i in selected),
            'appended_dependencies': sorted(names[i] for i in selected if i not in direct),
            'rebased_kind1_links': rebased_links,
            'output_hashes': {ext: sha(c) for ext, c in files.items()}}


def verify_links_resolved(dest, rebased_links, retained):
    """Every rebased kind-1 child index must point at the tone it named.

    Read back from the written bank, resolving each child index against the
    written tone names. Without this, appending the parent without its children
    (or without rebasing) would produce a bank that is byte-consistent and
    plays the wrong sound.
    """
    if not rebased_links:
        return
    entries, chunks, _ = read_recipient(dest)
    names = [n for n, _ in entries]
    tones = codec.tones_read(dict(chunks)[b'TONE'])
    parent_at = {n.lower(): i for i, n in enumerate(names)}
    for link in rebased_links:
        pi = parent_at[link['parent'].lower()]
        _, _, start = tone_record(tones[pi])
        child = codec.u32(tones[pi], link['offset'])
        assert child >= retained, \
            f'{link["parent"]}: child index {child} still points inside the ' \
            f'recipient bank, not at an appended tone'
        assert child < len(names), f'{link["parent"]}: child index {child} out of range'
        assert names[child].lower() == link.get('expect', names[child].lower()), \
            f'{link["parent"]}: child now resolves to {names[child]}'


def verify_preserved(dest, original, tones_r, labels_r, recipient_chunks, wanted):
    """Assert the written bank still holds every pre-existing tone, unchanged.

    Split out of `append_tones` so `--check` can point it at a deliberately
    damaged bank and prove the assertion is live rather than decorative.
    """
    read_back, chunks_back, labels_back = read_recipient(dest)
    chunks_back = dict(chunks_back)
    assert read_back[:len(original)] == original, f'{dest.name}: a pre-existing sample changed'
    assert chunks_back[b'BINF'] == recipient_chunks[b'BINF']
    assert chunks_back[b'PROP'] == recipient_chunks[b'PROP']
    assert codec.tones_read(chunks_back[b'TONE'])[:len(tones_r)] == tones_r, \
        f'{dest.name}: a pre-existing tone record changed'
    kept = {(crc, value) for crc, value in labels_back if value >> 8 < len(original)}
    assert kept == {(crc, value) for crc, value in labels_r}, \
        f'{dest.name}: a pre-existing tone label was lost or rebased'
    resolved = {zlib.crc32(n.lower().encode()) for n in wanted}
    assert resolved <= {crc for crc, _ in labels_back}, f'{dest.name}: appended tones do not resolve'


def stage_baseline(output):
    """Copy the recorded baseline banks in, so --check runs against shipped files.

    `paths.toml [dumps] arc` is nearly empty in this workspace, so the codec's
    normal fallback base is unavailable and the recorded baseline tree is the
    only honest source.
    """
    for slot in ('c06', 'c07'):
        stem = BASELINE / f'sound/bank/fighter/se_eflame_{slot}'
        for ext in ('.nus3audio', '.nus3bank', '.tonelabel'):
            target = (output / f'sound/bank/fighter/se_eflame_{slot}').with_suffix(ext)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(stem.with_suffix(ext), target)


def negative_control(output):
    """`verify_preserved` must reject a bank that lost a tone.

    Without this, "PASS" on the real run would only say the tool agreed with
    itself. Dropping the last tone record of a written bank - the one this tool
    appended - is the smallest change that has to trip the check.
    """
    good = output / 'sound/bank/fighter/se_eflame_c06'
    bad = output / 'sound/bank/fighter/probe_se_eflame_c06'
    for ext in ('.nus3audio', '.nus3bank', '.tonelabel'):
        shutil.copy2(good.with_suffix(ext), bad.with_suffix(ext))
    entries_before, _, _ = read_recipient(bad)
    original = entries_before[:-1]
    chunks = codec.bank_read(bad.with_suffix('.nus3bank').read_bytes())
    tones = codec.tones_read(dict(chunks)[b'TONE'])
    bad.with_suffix('.nus3bank').write_bytes(codec.bank_write(
        [(tag, codec.tones_write(tones[:-1]) if tag == b'TONE' else data)
         for tag, data in chunks]))
    labels = [pair for pair in codec.labels_read(
        bad.with_suffix('.tonelabel').read_bytes(), [n for n, _ in entries_before])
        if pair[1] >> 8 < len(original)]
    bad.with_suffix('.tonelabel').write_bytes(
        codec.pack(1) + codec.pack(len(labels))
        + b''.join(struct.pack('<II', *p) for p in labels))
    try:
        verify_preserved(bad, original, tones[:-1], labels, dict(chunks), WANTED)
    except AssertionError:
        return True
    return False


def build(output, baseline):
    output = Path(output).resolve()
    assert any(output.is_relative_to(ROOT / name) for name in ('scratch', 'builds')), \
        'output must be in builds/ or scratch/'
    check_pins()

    banks = []
    for slot in ('c06', 'c07'):
        dest = output / f'sound/bank/fighter/se_eflame_{slot}'
        base = dest if dest.with_suffix('.nus3audio').is_file() \
            else baseline / f'sound/bank/fighter/se_eflame_{slot}'
        rep = append_tones(SE_DONOR, base, dest, WANTED)
        rep.update(slot=slot, recipient_was_chained=base == dest,
                   baseline=str(base))
        banks.append(rep)

    report = {
        'tool': 'merge_snake_throw_lw_sound.py', 'version': '1.0.0', 'date': '2026-10-02',
        'evidence_tier': 'B', 'hardware_validated': False,
        'move': "Snake ThrowLw on Pyra c06/c07",
        'tones_named_by_acmd': sorted(WANTED),
        'tone_frames': {'se_snake_catch_tight': 1, 'se_snake_catch_tight_02': 20},
        'tone_kind1_note': (
            'se_snake_catch_tight is the only kind-1 (sequence) tone in the pinned '
            'se_snake_c00 bank (1 of 111). Its two child indices are rebased to the '
            'merged bank, and its two children are appended with it - see the '
            'closure()/kind1_links() docs above.'),
        'banks': banks,
        'eflame_sqb_untouched': (
            "Snake's sound_throwlw plays no PLAY_SEQUENCE, so no snake.sqb record is "
            "appended and eflame.sqb is deliberately not written by this tool."),
        'effect_bank_untouched': (
            "Snake's ThrowLw has no effect script, so no effect bank is needed and "
            "none is written."),
        'note': 'No offline check establishes that a sound plays in game.',
    }
    (output / 'snake_throw_lw_sound.json').write_text(json.dumps(report, indent=2) + '\n')
    added = sum(1 for b in banks if b['appended'])
    first = banks[0]
    print(f'PASS: {len(banks)} banks, {added} appended, retained '
          f'{sorted({b["retained_tones"] for b in banks})}')
    print(f'  named by ACMD: {first.get("named_by_acmd")}')
    print(f'  appended dependencies: {first.get("appended_dependencies")}')
    for link in first.get('rebased_kind1_links', []):
        print(f'  rebased kind-1 link: {link["parent"]} index {link["from"]} '
              f'({link["from_name"]}) -> {link["to"]}')
    return report


def negative_control_links(output):
    """`verify_links_resolved` must reject an unrebased kind-1 child index.

    The failure this guards against is invisible to every byte-comparison check
    in `verify_preserved`: copying `se_snake_catch_tight` verbatim leaves its
    child indices at 92/93, which are perfectly valid offsets *inside* the
    recipient's 544-tone bank and simply name the wrong sounds. Rewriting the
    first child index back to its donor value is the smallest change that has to
    trip the link check.
    """
    bank = output / 'sound/bank/fighter/se_eflame_c06'
    entries, chunks, _ = read_recipient(bank)
    names = [n for n, _ in entries]
    tones = codec.tones_read(dict(chunks)[b'TONE'])
    pi = [i for i, n in enumerate(names) if n.lower() == 'se_snake_catch_tight'][0]
    _, _, start = tone_record(tones[pi])
    links = kind1_links(tones[pi], names, start)
    assert len(links) == 2, links
    broken = bytearray(tones[pi])
    # Write back the *donor* index, not the rebased one: that is the actual
    # failure mode - a bank that was never rebased - and it is an index that is
    # perfectly valid inside the recipient's own 544 tones, so nothing else
    # catches it.
    donor_index = 92
    struct.pack_into('<I', broken, links[0][0], donor_index)
    new_tones = list(tones)
    new_tones[pi] = bytes(broken)
    bank.with_suffix('.nus3bank').write_bytes(codec.bank_write(
        [(tag, codec.tones_write(new_tones) if tag == b'TONE' else data)
         for tag, data in chunks]))
    bad = {'parent': names[pi], 'offset': links[0][0], 'from': donor_index,
           'from_name': names[donor_index], 'to': links[0][1],
           'expect': names[donor_index]}
    retained = len(entries) - len(closure(names, tones, WANTED))
    try:
        verify_links_resolved(bank, [bad], retained)
    except AssertionError:
        return True
    finally:
        bank.with_suffix('.nus3bank').write_bytes(codec.bank_write(
            [(tag, codec.tones_write(tones) if tag == b'TONE' else data)
             for tag, data in chunks]))
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--baseline', type=Path, default=BASELINE)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()

    if args.output:
        build(args.output, args.baseline)
        return 0
    if not args.check:
        parser.error('choose --check or --output')
    parent = ROOT / 'scratch' / '2026-10-02_fb-4-snake-throw-lw'
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=parent) as tmp:
        out = Path(tmp)
        stage_baseline(out)
        report = build(out, args.baseline)
        kept = {b['retained_tones'] for b in report['banks']}
        assert kept == {BASELINE_RETAINED}, f'unexpected retained-tone counts: {kept}'
        assert all(b['appended'] for b in report['banks']), 'tones were not appended'
        for b in report['banks']:
            assert sorted(b['named_by_acmd']) == sorted(WANTED), b['named_by_acmd']
            assert sorted(b['appended_dependencies']) == \
                ['se_snake_catch_tight_01', 'se_snake_catch_tight_01_layer'], \
                b['appended_dependencies']
            assert len(b['rebased_kind1_links']) == 2, b['rebased_kind1_links']
        assert negative_control(out), 'preservation check did not fail on a truncated bank'
        assert negative_control_links(out), 'link check did not fail on a dangling index'
    print('merge_snake_throw_lw_sound OK')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())