"""Conservative reader/writer for Nintendo SARC archives.

Scope is deliberately narrow. This tool answers one question safely: can the
bytes of ONE existing member be swapped without the container moving? So it
implements only four operations:

  list      manifest of header fields and every member
  extract   write one existing member out, by exact name
  rebuild   re-serialise an archive with no member changed
  replace   overwrite ONE existing member with a same-length payload

Everything else is refused explicitly rather than guessed:

  * growth or shrink (payload length must equal the member length)
  * adding, removing or renaming members
  * duplicate member names
  * path traversal or otherwise unsafe member names
  * overlapping or out-of-bounds member ranges
  * Yaz0/Zstd compressed archives and big-endian (BE) archives
  * writing over the input archive

The unchanged `rebuild` is an independent re-serialisation: it is written from
parsed metadata plus captured gap bytes, never by copying the input. If it does
not reproduce the input byte for byte, the writer is wrong.

This proves container behaviour only. It says nothing about whether the game
accepts a modified archive or whether the game validates it at runtime.
"""

import argparse
import hashlib
import json
import os
import posixpath
import struct
import sys

SARC_MAGIC = b'SARC'
SFAT_MAGIC = b'SFAT'
SFNT_MAGIC = b'SFNT'

HEADER_SIZE = 0x14
SFAT_HEADER_SIZE = 0x0C
ENTRY_SIZE = 0x10
NAME_TABLE_HEADER_SIZE = 0x08
NAME_ATTRIBUTE_BIT = 0x01000000
NAME_OFFSET_MASK = 0x00FFFFFF
SARC_HASH_KEY = 0x65

# Read as big-endian: the file stores the bytes ff fe, i.e. BE 0xFFFE, which is
# how this format spells "little endian". Everything else is little-endian.
BYTE_ORDER_LE_BE = 0xFFFE

# Refuse rather than guess when the outer container is not a plain SARC.
COMPRESSED_MAGICS = (
    (b'Yaz0', 'Yaz0 compressed SARC'),
    (b'\x28\xb5\x2f\xfd', 'Zstd compressed SARC'),
    (b'YAZR', 'YazR compressed SARC'),
)

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..'))


class SarcError(Exception):
    """A refusal. Every message is a statement of what was rejected and why."""


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def sarc_hash(name, key=SARC_HASH_KEY):
    """The name hash used by this format: h = h * 0x65 + c per character."""
    h = 0
    for ch in name:
        h = (h * key + ord(ch)) & 0xFFFFFFFF
    return h


def check_member_name(name):
    """Reject anything that could escape the output directory or misname a member."""
    if not name:
        raise SarcError('member name is empty')
    if '\x00' in name:
        raise SarcError('member name %r contains a NUL byte' % name)
    for ch in name:
        if ord(ch) < 0x20 or ord(ch) > 0x7E:
            raise SarcError('member name %r contains a non-printable-ASCII byte' % name)
    if '\\' in name:
        raise SarcError('member name %r contains a backslash; separators are "/" only' % name)
    if name.startswith('/'):
        raise SarcError('member name %r is an absolute path' % name)
    if ':' in name:
        raise SarcError('member name %r contains ":" (drive or stream syntax)' % name)
    if name.endswith('/'):
        raise SarcError('member name %r ends with a separator' % name)
    for part in name.split('/'):
        if part in ('', '.', '..'):
            raise SarcError('member name %r contains a %r path component' % (name, part))
    if posixpath.normpath(name) != name:
        raise SarcError('member name %r is not already normalised' % name)
    return name


class Member:
    def __init__(self, index, field0, field1, data_start, data_end, name):
        self.index = index
        self.field0 = field0
        self.field1 = field1
        self.data_start = data_start
        self.data_end = data_end
        self.name = name

    @property
    def size(self):
        return self.data_end - self.data_start

    @property
    def name_offset_bytes(self):
        return (self.field1 & NAME_OFFSET_MASK) * 4

    @property
    def has_name(self):
        return bool(self.field1 & NAME_ATTRIBUTE_BIT)


class Archive:
    def __init__(self, path, raw):
        self.path = path
        self.raw = raw
        self.members = []
        self.gaps = []
        self.header = {}
        self.name_table = b''
        self.name_table_padding = b''
        self.name_table_offset = 0
        self.name_table_end = 0
        self.name_table_used = 0
        self.data_offset = 0
        self.data_length = 0
        self.hash_key = SARC_HASH_KEY

    # -- lookups -------------------------------------------------------------
    def member_by_name(self, name):
        for m in self.members:
            if m.name == name:
                return m
        return None

    def member_data(self, member):
        return self.raw[self.data_offset + member.data_start:self.data_offset + member.data_end]

    # -- serialisation -------------------------------------------------------
    def serialise(self, overrides=None):
        """Re-serialise the container from parsed metadata plus gap bytes.

        `overrides` maps a member name to replacement payload bytes. It is the
        only way a payload can change, and the caller must have already checked
        that each payload has exactly the member's original length.
        """
        overrides = overrides or {}
        for name in overrides:
            if self.member_by_name(name) is None:
                raise SarcError('refusing to write: no member named %r in %s' % (name, self.path))

        out = bytearray()
        out += SARC_MAGIC
        out += struct.pack('<H', self.header['header_size'])
        out += struct.pack('<H', self.header['byte_order_raw'])
        out += struct.pack('<I', self.header['size_field'])
        out += struct.pack('<I', self.header['data_offset'])
        out += struct.pack('<I', self.header['field_0x10'])

        out += SFAT_MAGIC
        out += struct.pack('<H', self.header['sfat_header_size'])
        out += struct.pack('<H', self.header['member_count'])
        out += struct.pack('<I', self.hash_key)

        for m in self.members:
            out += struct.pack('<IIII', m.field0, m.field1, m.data_start, m.data_end)

        out += SFNT_MAGIC
        out += struct.pack('<I', self.header['name_table_header_field'])
        out += self.name_table

        # The slice after the last name up to data_offset is padding this tool
        # does not derive, so it was captured at parse time and is replayed
        # verbatim rather than regenerated.
        out += self.name_table_padding

        if len(out) > self.data_offset:
            raise SarcError('serialised head is %d bytes, past data_offset 0x%x' % (len(out), self.data_offset))
        if len(out) != self.data_offset:
            raise SarcError('serialised head is %d bytes, expected data_offset %d' % (len(out), self.data_offset))

        data = bytearray(self.data_length)
        for start, end in self.gaps:
            data[start:end] = self.raw[self.data_offset + start:self.data_offset + end]
        for m in self.members:
            payload = overrides.get(m.name)
            if payload is None:
                payload = self.member_data(m)
            if len(payload) != m.size:
                raise SarcError(
                    'refusing to write: payload for %r is %d bytes, member is %d bytes'
                    % (m.name, len(payload), m.size))
            data[m.data_start:m.data_end] = payload
        out += bytes(data)
        return bytes(out)

    def manifest(self):
        return {
            'path': self.path,
            'size': len(self.raw),
            'sha256': sha256(self.raw),
            'header': dict(self.header),
            'data_offset': self.data_offset,
            'data_length': self.data_length,
            'gaps': [{'start': s, 'end': e, 'size': e - s} for s, e in self.gaps],
            'members': [
                {
                    'index': m.index,
                    'name': m.name,
                    'field0': m.field0,
                    'name_off_field': m.field1,
                    'name_off_bytes': m.name_offset_bytes,
                    'data_start': m.data_start,
                    'data_end': m.data_end,
                    'size': m.size,
                    'magic': self.member_data(m)[:4].decode('latin1'),
                    'sha256': sha256(self.member_data(m)),
                    'name_hash_matches': (m.field0 == sarc_hash(m.name, self.hash_key)),
                }
                for m in self.members
            ],
        }


def _composite_gaps(intervals, length):
    """Complement of `intervals` inside [0, length), as a sorted list of spans."""
    covered = sorted(intervals)
    gaps = []
    cursor = 0
    for start, end in covered:
        if start > cursor:
            gaps.append((cursor, start))
        cursor = max(cursor, end)
    if cursor < length:
        gaps.append((cursor, length))
    return gaps


def parse(path):
    """Parse a SARC, or refuse. Never writes, never guesses."""
    try:
        with open(path, 'rb') as fh:
            raw = fh.read()
    except OSError as exc:
        raise SarcError('cannot read %s: %s' % (path, exc))

    if len(raw) < 0x14:
        raise SarcError('%s is %d bytes, too short to hold a SARC header' % (path, len(raw)))

    for magic, label in COMPRESSED_MAGICS:
        if raw[:4] == magic:
            raise SarcError('%s is a %s; only uncompressed SARC is supported' % (path, label))
    if raw[:4] != SARC_MAGIC:
        raise SarcError('%s does not start with SARC (found %r)' % (path, raw[:4]))

    header_size = struct.unpack_from('<H', raw, 0x04)[0]
    if header_size != HEADER_SIZE:
        raise SarcError('%s header_size is 0x%x, expected 0x%x' % (path, header_size, HEADER_SIZE))

    byte_order_raw = struct.unpack_from('<H', raw, 0x06)[0]
    byte_order_be = struct.unpack_from('>H', raw, 0x06)[0]
    if byte_order_be != BYTE_ORDER_LE_BE:
        if byte_order_raw == BYTE_ORDER_LE_BE:
            raise SarcError('%s is big-endian (BOM 0x%04x); only little-endian SARC is supported'
                            % (path, byte_order_raw))
        raise SarcError('%s has an unrecognised byte-order marker (raw 0x%04x, BE 0x%04x)'
                        % (path, byte_order_raw, byte_order_be))

    size_field, data_offset, field_0x10 = struct.unpack_from('<III', raw, 0x08)
    if size_field != len(raw):
        raise SarcError('%s header size field is %d but the file is %d bytes' % (path, size_field, len(raw)))
    if data_offset < 0x14 or data_offset > len(raw):
        raise SarcError('%s data_offset 0x%x is outside the file' % (path, data_offset))
    if data_offset % 4:
        raise SarcError('%s data_offset 0x%x is not 4-byte aligned' % (path, data_offset))

    if raw[0x14:0x18] != SFAT_MAGIC:
        raise SarcError('%s has no SFAT at 0x14 (found %r)' % (path, raw[0x14:0x18]))

    sfat_header_size = struct.unpack_from('<H', raw, 0x18)[0]
    if sfat_header_size != SFAT_HEADER_SIZE:
        raise SarcError('%s sfat_header_size is 0x%x, expected 0x%x' % (path, sfat_header_size, SFAT_HEADER_SIZE))
    member_count = struct.unpack_from('<H', raw, 0x1A)[0]
    hash_key = struct.unpack_from('<I', raw, 0x1C)[0]

    entries_offset = 0x20
    entries_end = entries_offset + member_count * ENTRY_SIZE
    if entries_end > len(raw):
        raise SarcError('%s SFAT table of %d entries runs past the file' % (path, member_count))
    if raw[entries_end:entries_end + 4] != SFNT_MAGIC:
        raise SarcError('%s has no SFNT at 0x%x (found %r)' % (path, entries_end, raw[entries_end:entries_end + 4]))

    name_table_offset = entries_end
    name_table_header_field = struct.unpack_from('<I', raw, name_table_offset + 4)[0]
    name_table_start = name_table_offset + 8
    # The name table runs from after the SFNT header to data_offset. It is
    # split below into the used prefix and the padding that follows the last
    # name; the padding is preserved verbatim, never regenerated, because this
    # tool does not derive the padding rule.
    name_table_all = raw[name_table_start:data_offset]

    arc = Archive(path, raw)
    arc.data_offset = data_offset
    arc.data_length = len(raw) - data_offset
    arc.hash_key = hash_key

    seen = {}
    name_table_used = 0
    for i in range(member_count):
        field0, field1, start, end = struct.unpack_from('<IIII', raw, entries_offset + i * ENTRY_SIZE)
        name = None
        if field1 & NAME_ATTRIBUTE_BIT:
            name_rel = (field1 & NAME_OFFSET_MASK) * 4
            if name_rel >= len(name_table_all):
                raise SarcError('%s member %d name offset %d is outside the name table (%d bytes)'
                                % (path, i, name_rel, len(name_table_all)))
            nul = name_table_all.find(b'\x00', name_rel)
            if nul < 0:
                raise SarcError('%s member %d name at %d is not NUL-terminated' % (path, i, name_rel))
            raw_name = name_table_all[name_rel:nul]
            try:
                name = raw_name.decode('ascii')
            except UnicodeDecodeError:
                raise SarcError('%s member %d name %r is not ASCII' % (path, i, raw_name))
            used_end = name_rel + len(name) + 1
            used_end = (used_end + 3) & ~3
            name_table_used = max(name_table_used, used_end)
            check_member_name(name)
        else:
            name = ''
        if name in seen:
            raise SarcError('%s has duplicate member name %r (indices %d and %d)'
                            % (path, name, seen[name], i))
        seen[name] = i

        if end < start:
            raise SarcError('%s member %d (%r) has end 0x%x before start 0x%x' % (path, i, name, end, start))
        if end > arc.data_length:
            raise SarcError('%s member %d (%r) ends at 0x%x, past the %d-byte data section'
                            % (path, i, name, end, arc.data_length))
        arc.members.append(Member(i, field0, field1, start, end, name))

    if name_table_used > len(name_table_all):
        raise SarcError('%s names run to %d bytes, past the %d-byte name table'
                        % (path, name_table_used, len(name_table_all)))
    arc.name_table = name_table_all[:name_table_used]
    arc.name_table_padding = name_table_all[name_table_used:]
    arc.name_table_offset = name_table_offset
    arc.name_table_end = data_offset
    arc.name_table_used = name_table_used

    # Ordering is informational, but overlap is a hard error.
    intervals = []
    for m in arc.members:
        for other_start, other_end, other in ((n.data_start, n.data_end, n) for n in arc.members):
            if other is m:
                continue
            if m.data_start < other_end and other_start < m.data_end and m.size and other.size:
                raise SarcError('%s members %r and %r overlap' % (path, m.name, other.name))
        intervals.append((m.data_start, m.data_end))
    arc.gaps = _composite_gaps(intervals, arc.data_length)

    arc.header = {
        'magic': 'SARC',
        'header_size': header_size,
        'byte_order_raw': byte_order_raw,
        'byte_order_be': byte_order_be,
        'size_field': size_field,
        'data_offset': data_offset,
        'field_0x10': field_0x10,
        'sfat_header_size': sfat_header_size,
        'member_count': member_count,
        'hash_key': hash_key,
        'name_table_header_field': name_table_header_field,
        'name_table_offset': name_table_offset,
        'name_table_used_bytes': arc.name_table_used,
        'name_table_padding_bytes': len(arc.name_table_padding),
        'members_ascending_by_hash': all(
            arc.members[i].field0 <= arc.members[i + 1].field0 for i in range(len(arc.members) - 1)),
        'members_ascending_by_offset': all(
            arc.members[i].data_start <= arc.members[i + 1].data_start for i in range(len(arc.members) - 1)),
    }
    return arc


def cmd_list(args):
    arc = parse(args.archive)
    manifest = arc.manifest()
    if args.json:
        write_json(args.json, manifest)
    if args.quiet:
        return 0
    h = manifest['header']
    print('archive   %s' % manifest['path'])
    print('size      %d bytes  sha256 %s' % (manifest['size'], manifest['sha256']))
    print('header    size_field=%d data_offset=0x%x field_0x10=0x%x BOM=0x%04x members=%d hash_key=0x%x'
          % (h['size_field'], h['data_offset'], h['field_0x10'], h['byte_order_be'], h['member_count'], h['hash_key']))
    print('table     SFNT at 0x%x, %d name bytes + %d padding bytes, %d gap runs in the data section'
          % (h['name_table_offset'], h['name_table_used_bytes'], h['name_table_padding_bytes'],
             len(manifest['gaps'])))
    print('%-5s %-11s %-11s %-9s %-6s %s' % ('idx', 'start', 'end', 'size', 'magic', 'name'))
    for m in manifest['members']:
        print('%-5d 0x%-9x 0x%-9x %-9d %-6s %s' % (m['index'], m['data_start'], m['data_end'], m['size'], m['magic'], m['name']))
    return 0


def cmd_extract(args):
    arc = parse(args.archive)
    name = check_member_name(args.name)
    member = arc.member_by_name(name)
    if member is None:
        raise SarcError('no member named %r in %s (%d members)' % (name, args.archive, len(arc.members)))
    payload = arc.member_data(member)
    if args.out:
        guard_output(args.archive, args.out)
        parent = os.path.dirname(os.path.abspath(args.out))
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(args.out, 'wb') as fh:
            fh.write(payload)
        print('wrote %s (%d bytes, sha256 %s)' % (args.out, len(payload), sha256(payload)))
    else:
        sys.stdout.buffer.write(payload)
    return 0


def cmd_rebuild(args):
    """Unchanged control: re-serialise with no member modified."""
    arc = parse(args.archive)
    rebuilt = arc.serialise()
    same = rebuilt == arc.raw
    result = {
        'archive': arc.path,
        'input_sha256': sha256(arc.raw),
        'rebuilt_sha256': sha256(rebuilt),
        'byte_identical': same,
        'input_size': len(arc.raw),
        'rebuilt_size': len(rebuilt),
    }
    if args.out:
        if not same:
            raise SarcError('refusing to write %s: rebuild is not byte-identical to the input' % args.out)
        guard_output(arc.path, args.out)
        parent = os.path.dirname(os.path.abspath(args.out))
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(args.out, 'wb') as fh:
            fh.write(rebuilt)
        result['written'] = args.out
    if args.json:
        write_json(args.json, result)
    if not args.quiet:
        print('%-24s input %s' % (os.path.basename(os.path.dirname(arc.path)), result['input_sha256']))
        print('%-24s rebuilt %s' % ('', result['rebuilt_sha256']))
        print('%-24s byte identical: %s (%d bytes)' % ('', same, result['rebuilt_size']))
    return 0 if same else 1


def cmd_replace(args):
    """Overwrite exactly one existing member with a same-length payload."""
    arc = parse(args.archive)
    name = check_member_name(args.name)
    member = arc.member_by_name(name)
    if member is None:
        raise SarcError('no member named %r in %s (%d members); this tool only replaces existing members'
                        % (name, arc.path, len(arc.members)))
    try:
        with open(args.payload, 'rb') as fh:
            payload = fh.read()
    except OSError as exc:
        raise SarcError('cannot read payload %s: %s' % (args.payload, exc))
    if len(payload) != member.size:
        raise SarcError(
            'refusing to replace %r: payload is %d bytes, member is %d bytes. '
            'This tool supports same-length replacement only (no growth, no shrink).'
            % (name, len(payload), member.size))

    out = arc.serialise({name: payload})
    if len(out) != len(arc.raw):
        raise SarcError('refusing to write: replacement changed the archive size from %d to %d'
                        % (len(arc.raw), len(out)))

    guard_output(arc.path, args.out)
    parent = os.path.dirname(os.path.abspath(args.out))
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(args.out, 'wb') as fh:
        fh.write(out)

    changed = compare_arcs(arc.raw, out)
    result = {
        'archive': arc.path,
        'output': args.out,
        'member': name,
        'member_size': member.size,
        'payload': args.payload,
        'input_sha256': sha256(arc.raw),
        'output_sha256': sha256(out),
        'size_unchanged': len(out) == len(arc.raw),
        'changed_members': changed['changed'],
        'unchanged_member_count': len(changed['unchanged']),
        'metadata_identical': changed['metadata_identical'],
        'gaps_identical': changed['gaps_identical'],
    }
    if args.json:
        write_json(args.json, result)
    if not args.quiet:
        print('replaced  %s (%d bytes)' % (name, member.size))
        print('output    %s  sha256 %s' % (args.out, result['output_sha256']))
        print('changed members: %s' % (result['changed_members'] or 'none'))
        print('metadata identical: %s   gap bytes identical: %s'
              % (result['metadata_identical'], result['gaps_identical']))
    return 0


def compare_arcs(a_raw, b_raw):
    """Compare two serialised archives by re-parsing both independently."""
    import tempfile
    tmpdir = tempfile.mkdtemp(prefix='sarc-layout-')
    try:
        a_path = os.path.join(tmpdir, 'a.arc')
        b_path = os.path.join(tmpdir, 'b.arc')
        with open(a_path, 'wb') as fh:
            fh.write(a_raw)
        with open(b_path, 'wb') as fh:
            fh.write(b_raw)
        a = parse(a_path)
        b = parse(b_path)
    finally:
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)

    a_hashes = {m.name: sha256(a.member_data(m)) for m in a.members}
    b_hashes = {m.name: sha256(b.member_data(m)) for m in b.members}
    changed = sorted(n for n in set(a_hashes) | set(b_hashes) if a_hashes.get(n) != b_hashes.get(n))
    unchanged = sorted(n for n in a_hashes if a_hashes.get(n) == b_hashes.get(n))

    a_meta = dict(a.header)
    b_meta = dict(b.header)
    for key in ('path',):
        a_meta.pop(key, None)
        b_meta.pop(key, None)
    metadata_identical = a_meta == b_meta and [m.field1 for m in a.members] == [m.field1 for m in b.members]
    gaps_identical = a.gaps == b.gaps
    return {
        'changed': changed,
        'unchanged': unchanged,
        'metadata_identical': metadata_identical,
        'gaps_identical': gaps_identical,
    }


def cmd_verify(args):
    """Structural checks on one archive. Exit 0 only if every check passes."""
    arc = parse(args.archive)
    checks = []

    def check(name, ok, detail=''):
        checks.append({'check': name, 'pass': bool(ok), 'detail': detail})

    check('magic', arc.raw[:4] == SARC_MAGIC)
    check('header-size', arc.header['header_size'] == HEADER_SIZE)
    check('byte-order-le', arc.header['byte_order_be'] == BYTE_ORDER_LE_BE)
    check('size-field-matches-file', arc.header['size_field'] == len(arc.raw))
    check('data-offset-aligned', arc.data_offset % 4 == 0)
    check('member-count', arc.header['member_count'] == len(arc.members))
    check('member-names-safe', all(check_member_name(m.name) is not None for m in arc.members))
    check('member-names-unique', len({m.name for m in arc.members}) == len(arc.members))
    check('ranges-in-bounds', all(m.data_end <= arc.data_length for m in arc.members))
    check('names-hash-matches', all(sarc_hash(m.name, arc.hash_key) == m.field0 for m in arc.members),
          '%d/%d' % (sum(sarc_hash(m.name, arc.hash_key) == m.field0 for m in arc.members), len(arc.members)))
    check('offsets-ascending', arc.header['members_ascending_by_offset'])
    check('hashes-ascending', arc.header['members_ascending_by_hash'])

    rebuilt = arc.serialise()
    check('rebuild-byte-identical', rebuilt == arc.raw,
          'rebuilt sha256 %s' % sha256(rebuilt))

    manifest = arc.manifest()
    result = {'archive': arc.path, 'sha256': sha256(arc.raw), 'size': len(arc.raw),
              'members': len(arc.members), 'checks': checks,
              'all_pass': all(c['pass'] for c in checks)}
    if args.json:
        write_json(args.json, result)
    if not args.quiet:
        for c in checks:
            print('%-4s %-28s %s' % ('ok' if c['pass'] else 'FAIL', c['check'], c['detail']))
        print('all_pass: %s' % result['all_pass'])
    return 0 if result['all_pass'] else 1


def guard_output(src, dst):
    """Refuse to overwrite the input archive, or write outside the workspace."""
    src_abs = os.path.abspath(src)
    dst_abs = os.path.abspath(dst)
    if src_abs == dst_abs:
        raise SarcError('refusing to write: output would overwrite the input %s' % src)
    if os.path.exists(dst_abs) and os.path.samefile(src_abs, dst_abs):
        raise SarcError('refusing to write: output resolves to the input %s' % src)
    repo = REPO_ROOT
    if not os.path.abspath(dst_abs).startswith(repo + os.sep):
        raise SarcError('refusing to write outside the workspace: %s' % dst_abs)
    if not os.path.abspath(src_abs).startswith(repo + os.sep):
        raise SarcError('refusing to read outside the workspace: %s' % src_abs)


def write_json(path, payload):
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(payload, fh, indent=1, sort_keys=True)
        fh.write('\n')


def build_parser():
    p = argparse.ArgumentParser(prog='sarc_layout.py', description=__doc__.split('\n\n')[0])
    sub = p.add_subparsers(dest='command')

    def common(sp, archive=True):
        if archive:
            sp.add_argument('archive', help='path to a SARC archive (read-only)')
        sp.add_argument('--json', help='write a JSON report here')
        sp.add_argument('--quiet', action='store_true', help='suppress stdout')

    sp = sub.add_parser('list', help='print a manifest of the archive')
    common(sp)
    sp.set_defaults(func=cmd_list)

    sp = sub.add_parser('extract', help='write one member out by exact name')
    common(sp)
    sp.add_argument('name', help='exact member name, e.g. blyt/make_mii_edit.bflyt')
    sp.add_argument('-o', '--out', help='output file (default: stdout)')
    sp.set_defaults(func=cmd_extract)

    sp = sub.add_parser('rebuild', help='re-serialise with no member changed (control)')
    common(sp)
    sp.add_argument('-o', '--out', help='write the rebuilt archive here (only if byte-identical)')
    sp.set_defaults(func=cmd_rebuild)

    sp = sub.add_parser('replace', help='overwrite one existing member with a same-length payload')
    common(sp)
    sp.add_argument('name', help='exact member name of an existing member')
    sp.add_argument('--payload', required=True, help='file holding the replacement bytes')
    sp.add_argument('-o', '--out', required=True, help='output archive path')
    sp.set_defaults(func=cmd_replace)

    sp = sub.add_parser('verify', help='run structural checks on one archive')
    common(sp)
    sp.set_defaults(func=cmd_verify)

    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, 'func', None):
        parser.print_help()
        return 2
    try:
        return args.func(args)
    except SarcError as exc:
        sys.stderr.write('refused: %s\n' % exc)
        return 2


if __name__ == '__main__':
    sys.exit(main())