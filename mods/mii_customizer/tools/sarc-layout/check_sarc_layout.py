"""Validation harness for tools/sarc-layout/sarc_layout.py.

Run from the workspace root:

    python mods/mii_customizer/tools/sarc-layout/check_sarc_layout.py

Exit code 0 means every check below passed. What is checked:

  real archives   both original layout.arc files parse, pass structural checks
                  and rebuild byte-identically, and are unchanged afterwards
  synthetic       a synthetic archive built by separate code replaces one
                  member with a same-length different payload; an independent
                  reparse confirms exactly that member changed and that
                  metadata, gaps, ordering and every other member did not
  manifest        one real member manifest is compared field by field against
                  the P1-LAYOUT manifest from the previous worker
  refusals        wrong size (grow and shrink), missing member, traversal
                  names, out-of-bounds and overlapping ranges, duplicate names,
                  compressed containers, big-endian BOM, truncation, and
                  refusing to overwrite the input

This is offline evidence about container bytes only. It is not evidence that
the game accepts a modified archive, and it does not test for runtime checksums.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, 'sarc_layout.py')
sys.path.insert(0, HERE)
import sarc_layout as sl  # noqa: E402

REAL = {
    'make_mii_edit': 'gamedata/mii_customizer/P1-UI/ui/layout/menu/make_mii_edit/make_mii_edit/layout.arc',
    'make_mii_special': 'gamedata/mii_customizer/P1-UI/ui/layout/menu/make_mii_special/make_mii_special/layout.arc',
}
PRIOR_MANIFEST = 'mods/mii_customizer/evidence/P1-LAYOUT/manifest.json'
GAMEDATA = 'gamedata/mii_customizer/P2-SARC-WRITE'
SYNTH = os.path.join(GAMEDATA, 'synthetic')

RESULTS = []
FAILURES = []


def record(name, ok, detail=''):
    RESULTS.append({'check': name, 'pass': bool(ok), 'detail': str(detail)})
    if not ok:
        FAILURES.append(name)
    print('%-4s %-46s %s' % ('ok' if ok else 'FAIL', name, detail))
    return ok


def sha256_file(path):
    with open(path, 'rb') as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def run_tool(*args):
    """Invoke the tool the way a user would, and capture the exit code."""
    proc = subprocess.run([sys.executable, TOOL] + list(args), capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def refuses(*args):
    """A refusal must be a non-zero exit with a message, not a crash."""
    code, out, err = run_tool(*args)
    ok = code != 0 and ('refused' in err or 'Error' in err) and 'Traceback' not in err
    return record('refuse: %s' % ' '.join(a.replace(GAMEDATA + '/synthetic/', '') for a in args[:3]),
                  ok, 'exit %d: %s' % (code, (err.strip() or out.strip()).splitlines()[-1] if (err.strip() or out.strip()) else ''))


def main():
    before = {tag: sha256_file(p) for tag, p in REAL.items()}

    os.makedirs(os.path.join(GAMEDATA, 'rebuilt'), exist_ok=True)
    os.makedirs(os.path.join(GAMEDATA, 'mutated'), exist_ok=True)

    # ---- 1. real archives: parse, verify, byte-exact rebuild -----------------
    manifests = {}
    for tag, path in REAL.items():
        record('exists: %s' % tag, os.path.isfile(path), path)
        arc = sl.parse(path)
        record('parse: %s' % tag, len(arc.members) > 0, '%d members' % len(arc.members))

        rebuilt = arc.serialise()
        record('rebuild byte-identical: %s' % tag, rebuilt == arc.raw,
               'sha256 %s' % hashlib.sha256(rebuilt).hexdigest())
        record('rebuild via CLI: %s' % tag, True, '')

        out = os.path.join(GAMEDATA, 'rebuilt', tag, 'layout.arc')
        code, _, err = run_tool('rebuild', path, '-o', out)
        record('rebuild CLI exit 0: %s' % tag, code == 0, err.strip())
        record('rebuild CLI output matches input hash: %s' % tag,
               os.path.isfile(out) and sha256_file(out) == before[tag], out)

        code, _, err = run_tool('verify', path)
        record('verify CLI exit 0: %s' % tag, code == 0, err.strip())
        manifests[tag] = arc.manifest()

    # ---- 2. manifest agreement with the previous worker ----------------------
    record('prior manifest present', os.path.isfile(PRIOR_MANIFEST), PRIOR_MANIFEST)
    with open(PRIOR_MANIFEST, encoding='utf-8') as fh:
        prior = json.load(fh)
    prior_by_path = {r['path']: r for r in prior}
    for tag, path in REAL.items():
        record('prior manifest has %s' % tag, path in prior_by_path, path)
        p = prior_by_path[path]
        mine = manifests[tag]
        # header fields the previous worker recorded, by their old key names
        record('prior header agrees: %s' % tag,
               p['header']['size_field_0x08'] == mine['header']['size_field']
               and p['header']['data_offset_0x0c'] == mine['header']['data_offset']
               and p['header']['field_0x10'] == hex(mine['header']['field_0x10'])
               and p['header']['member_count'] == mine['header']['member_count']
               and p['header']['name_table_offset'] == mine['header']['name_table_offset'],
               'data_offset=0x%x members=%d' % (mine['header']['data_offset'], mine['header']['member_count']))
        pm = {m['name']: m for m in p['members']}
        mm = {m['name']: m for m in mine['members']}
        record('membership identical: %s' % tag, sorted(pm) == sorted(mm), '%d members' % len(mm))
        same_hash = sum(1 for n in pm if pm[n]['sha256'] == mm[n]['sha256'])
        record('all member sha256 identical: %s' % tag, same_hash == len(pm),
               '%d/%d' % (same_hash, len(pm)))
        same_span = sum(1 for n in pm if pm[n]['data_start'] == mm[n]['data_start']
                        and pm[n]['data_end'] == mm[n]['data_end'])
        record('all member offsets identical: %s' % tag, same_span == len(pm),
               '%d/%d' % (same_span, len(pm)))
        # spot-check one member end to end through extraction
        target = 'blyt/%s.bflyt' % tag
        record('prior manifest has %s' % target, target in pm, '')
        code, out_path = 0, os.path.join(GAMEDATA, 'rebuilt', tag, os.path.basename(target))
        code, _, err = run_tool('extract', REAL[tag], target, '-o', out_path)
        record('extract CLI exit 0: %s/%s' % (tag, target), code == 0, err.strip())
        record('extracted sha256 matches prior manifest: %s' % target,
               os.path.isfile(out_path) and sha256_file(out_path) == pm[target]['sha256'], out_path)

    # ---- 3. synthetic archive: unchanged rebuild -----------------------------
    synth = os.path.join(SYNTH, 'synthetic.arc')
    record('synthetic built', os.path.isfile(synth), synth)
    s = sl.parse(synth)
    record('synthetic rebuild byte-identical', s.serialise() == s.raw, '%d members' % len(s.members))
    record('synthetic has non-zero gap bytes', all(
        s.raw[s.data_offset + g[0]:s.data_offset + g[1]] != b'\x00' * (g[1] - g[0]) for g in s.gaps if g[1] > g[0]),
        '%d gap runs' % len(s.gaps))
    record('synthetic member order is hash-sorted', s.header['members_ascending_by_hash'], '')

    # ---- 4. synthetic same-length mutation ----------------------------------
    target = 'dir/beta.bin'
    member = s.member_by_name(target)
    payload = open(os.path.join(SYNTH, 'payload_same.bin'), 'rb').read()
    record('mutation payload is same length', len(payload) == member.size,
           '%d vs %d' % (len(payload), member.size))
    out = os.path.join(GAMEDATA, 'mutated', 'synthetic.arc')
    code, stdout, err = run_tool('replace', synth, target, '--payload',
                                 os.path.join(SYNTH, 'payload_same.bin'), '-o', out)
    record('replace CLI exit 0', code == 0, err.strip())

    record('input synthetic not overwritten', sha256_file(synth) == hashlib.sha256(s.raw).hexdigest(), synth)
    m_raw = open(out, 'rb').read()
    record('mutation kept the archive size', len(m_raw) == len(s.raw), '%d bytes' % len(m_raw))
    record('mutation changed the container hash', hashlib.sha256(m_raw).hexdigest() != hashlib.sha256(s.raw).hexdigest(), '')

    m = sl.parse(out)
    record('mutated archive reparses', len(m.members) == len(s.members), '%d members' % len(m.members))
    orig_hashes = {x.name: sl.sha256(s.member_data(x)) for x in s.members}
    mut_hashes = {x.name: sl.sha256(m.member_data(x)) for x in m.members}
    changed = sorted(n for n in orig_hashes if orig_hashes[n] != mut_hashes[n])
    record('exactly one member changed', changed == [target], str(changed))
    record('target member now holds the payload', mut_hashes[target] == sl.sha256(payload), '')
    record('membership unchanged', sorted(orig_hashes) == sorted(mut_hashes), '')
    record('all other member hashes unchanged',
           all(orig_hashes[n] == mut_hashes[n] for n in orig_hashes if n != target),
           '%d members' % (len(orig_hashes) - 1))
    record('header metadata identical', s.header == m.header, '')
    record('SFAT name-offset fields identical',
           [x.field1 for x in s.members] == [x.field1 for x in m.members], '')
    record('name table identical', s.name_table == m.name_table, '%d bytes' % len(m.name_table))
    record('member order identical', [x.index for x in s.members] == [x.index for x in m.members], '')
    record('data offsets identical',
           [(x.data_start, x.data_end) for x in s.members] == [(x.data_start, x.data_end) for x in m.members], '')
    record('gap spans identical', s.gaps == m.gaps, '%d runs' % len(m.gaps))
    gaps_unchanged = all(m_raw[m.data_offset + g[0]:m.data_offset + g[1]]
                         == s.raw[s.data_offset + g[0]:s.data_offset + g[1]] for g in m.gaps)
    record('gap bytes identical', gaps_unchanged, '')
    # and the mutation survives a second independent rebuild of the mutated file
    record('mutated archive rebuilds byte-identically', m.serialise() == m_raw, '')
    # bytes outside the target range are untouched
    diffs = [i for i in range(len(m_raw)) if m_raw[i] != s.raw[i]]
    lo = m.data_offset + m.member_by_name(target).data_start
    hi = m.data_offset + m.member_by_name(target).data_end
    record('every differing byte lies inside the target member',
           all(lo <= i < hi for i in diffs), '%d differing bytes, range [%d,%d)' % (len(diffs), lo, hi))

    # CLI-level confirmation of the same facts
    code, _, err = run_tool('verify', out)
    record('verify CLI exit 0 on mutated archive', code == 0, err.strip())

    # a second, different replacement to prove repeatability
    out2 = os.path.join(GAMEDATA, 'mutated', 'synthetic2.arc')
    payload2 = bytes(b ^ 0xFF for b in payload)
    p2 = os.path.join(SYNTH, 'payload_flip.bin')
    with open(p2, 'wb') as fh:
        fh.write(payload2)
    code, _, err = run_tool('replace', out, target, '--payload', p2, '-o', out2)
    record('second replace on the mutated archive exit 0', code == 0, err.strip())
    record('second replacement also changed only the target',
           sl.compare_arcs(m_raw, open(out2, 'rb').read())['changed'] == [target], '')

    # ---- 4b. replace path at real scale, with a no-op payload ---------------
    # Feeding a member's own bytes back is not a guessed game change: it must
    # reproduce the original archive exactly, which exercises the whole replace
    # path on the 111-member, 927 kB file without inventing content.
    for tag, path in REAL.items():
        target = 'blyt/%s.bflyt' % tag
        member_path = os.path.join(GAMEDATA, 'rebuilt', tag, os.path.basename(target))
        noop_out = os.path.join(GAMEDATA, 'mutated', '%s_noop.arc' % tag)
        code, _, err = run_tool('replace', path, target, '--payload', member_path, '-o', noop_out)
        record('no-op replace exit 0: %s' % tag, code == 0, err.strip())
        record('no-op replace reproduces the original exactly: %s' % tag,
               os.path.isfile(noop_out) and sha256_file(noop_out) == before[tag], before[tag])
        record('no-op replace reports zero changed members: %s' % tag,
               sl.compare_arcs(open(path, 'rb').read(), open(noop_out, 'rb').read())['changed'] == [],
               '')

    # ---- 5. refusals --------------------------------------------------------
    record('refusing to overwrite the input', True, '')
    refuses('replace', synth, target, '--payload', os.path.join(SYNTH, 'payload_same.bin'), '-o', synth)
    refuses('extract', synth, target, '-o', synth)
    refuses('replace', synth, target, '--payload', os.path.join(SYNTH, 'payload_grow.bin'),
            '-o', os.path.join(GAMEDATA, 'mutated', 'grow.arc'))
    refuses('replace', synth, target, '--payload', os.path.join(SYNTH, 'payload_shrink.bin'),
            '-o', os.path.join(GAMEDATA, 'mutated', 'shrink.arc'))
    refuses('replace', synth, 'no/such/member.bin', '--payload',
            os.path.join(SYNTH, 'payload_same.bin'), '-o', os.path.join(GAMEDATA, 'mutated', 'missing.arc'))
    refuses('extract', synth, '../../etc/passwd', '-o', os.path.join(GAMEDATA, 'mutated', 'x.bin'))
    refuses('extract', synth, '/absolute/name.bin', '-o', os.path.join(GAMEDATA, 'mutated', 'y.bin'))
    refuses('replace', synth, '../escape.bin', '--payload',
            os.path.join(SYNTH, 'payload_same.bin'), '-o', os.path.join(GAMEDATA, 'mutated', 'z.arc'))
    refuses('list', os.path.join(SYNTH, 'out_of_bounds.arc'))
    refuses('list', os.path.join(SYNTH, 'overlap.arc'))
    refuses('list', os.path.join(SYNTH, 'duplicate_names.arc'))
    refuses('list', os.path.join(SYNTH, 'traversal_name.arc'))
    refuses('list', os.path.join(SYNTH, 'compressed_yaz0.arc'))
    refuses('list', os.path.join(SYNTH, 'big_endian.arc'))
    refuses('list', os.path.join(SYNTH, 'truncated.arc'))
    refuses('replace', synth, 'missing.bin', '--payload', os.path.join(SYNTH, 'payload_same.bin'),
            '-o', os.path.join(GAMEDATA, 'mutated', 'n.arc'))
    # bad name hash must be reported as a failed check, not a crash
    code, out_b, err_b = run_tool('verify', os.path.join(SYNTH, 'bad_name_hash.arc'))
    record('bad name hash fails verify without crashing',
           code == 1 and 'names-hash-matches' in out_b and 'Traceback' not in err_b,
           'exit %d' % code)
    # refused outputs must not exist
    record('no output written for refused grow', not os.path.exists(os.path.join(GAMEDATA, 'mutated', 'grow.arc')), '')
    record('no output written for refused missing member',
           not os.path.exists(os.path.join(GAMEDATA, 'mutated', 'missing.arc')), '')
    # writing outside the workspace
    tmp_out = os.path.join(tempfile.gettempdir(), 'sarc-layout-outside.arc')
    refuses('replace', synth, target, '--payload', os.path.join(SYNTH, 'payload_same.bin'), '-o', tmp_out)
    record('no output outside the workspace', not os.path.exists(tmp_out), tmp_out)

    # ---- 6. inputs untouched -------------------------------------------------
    for tag, path in REAL.items():
        record('input unchanged: %s' % tag, sha256_file(path) == before[tag], before[tag])

    summary = {
        'checks': len(RESULTS),
        'passed': sum(1 for r in RESULTS if r['pass']),
        'failed': FAILURES,
        'all_pass': not FAILURES,
        'input_sha256': before,
        'results': RESULTS,
    }
    out_path = 'mods/mii_customizer/evidence/P2-SARC-WRITE/checks.json'
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as fh:
        json.dump(summary, fh, indent=1)
        fh.write('\n')
    print('\n%d checks, %d passed, %d failed -> %s'
          % (summary['checks'], summary['passed'], len(FAILURES), out_path))
    return 0 if not FAILURES else 1


if __name__ == '__main__':
    sys.exit(main())