"""Generate custom Cloud sword trail textures for Pyra/G&W c06 and c07.

Donor: Cloud (fighter/cloud) trail textures (tex_cloud_sword1, tex_cloud_sword2)
c06: Black & Pink Mythra theme (deep crimson/black core, radiant magenta-pink edge)
c07: Champagne Gold Mythra theme (pure white core, radiant light gold body, warm gold edge)

Preserves NUTEXB container dimensions (256x256), 9 mip levels, Rgba8UnormSrgb format,
alpha channel, and internal resource name headers.
"""
from pathlib import Path
import hashlib
import shutil
import struct
import subprocess
import tempfile
import numpy as np
from PIL import Image

TOOLS = Path(__file__).resolve().parent
PROJECT = TOOLS.parent
ROOT = TOOLS.parents[2]
CLI = TOOLS / 'texture_cli/ultimate_tex_cli.exe'
DONOR_TRAIL_DIR = ROOT / 'refs/cloud_attack_air_f/trail'
if not DONOR_TRAIL_DIR.exists():
    DONOR_TRAIL_DIR = ROOT / 'dumps/arc/effect/fighter/cloud/trail'

# Palette constants matching Mythra custom sword trails (COLOR_THEMES.md)
# c06: Black & Pink Mythra
C06_EDGE_CRIMSON = np.array([118.0, 0.0, 0.0]) / 255.0
C06_MID_CRIMSON  = np.array([124.0, 0.0, 30.0]) / 255.0
C06_CORE_MAGENTA = np.array([145.0, 8.0, 90.0]) / 255.0

# c07: Radiant White & Champagne Gold (from build_color_themes.py c07_trail_gold)
C07_EDGE_GOLD  = np.array([248.0, 215.0, 140.0]) / 255.0
C07_MID_GOLD   = np.array([255.0, 235.0, 170.0]) / 255.0
C07_CORE_WHITE = np.array([255.0, 255.0, 255.0]) / 255.0


def u32(data, offset):
    return struct.unpack_from('<I', data, offset)[0]


def convert_image(src, dst, fmt=None, no_mips=False):
    args = [str(CLI), str(src), str(dst)]
    if fmt:
        args += ['-f', fmt]
    if no_mips:
        args += ['--no-mipmaps']
    subprocess.run(args, check=True, capture_output=True)


def recolor_cloud_trail_c06(image: Image.Image) -> Image.Image:
    """Recolor Cloud's sword trail to match Mythra c06 (Black & Pink)."""
    arr = np.array(image.convert('RGBA'))
    rgb = arr[..., :3].astype(np.float64) / 255.0
    a = arr[..., 3]

    # Luminance of Cloud's green/cyan sword trail
    lum = rgb @ np.array([0.2126, 0.7152, 0.0722])
    t = np.clip((lum - 0.12) / (0.95 - 0.12), 0.0, 1.0)

    # Smooth interpolation: dark crimson edge -> rich crimson mid -> luminous magenta-pink core
    out_rgb = np.where((t < 0.5)[..., None],
                       C06_EDGE_CRIMSON + (C06_MID_CRIMSON - C06_EDGE_CRIMSON) * (t / 0.5)[..., None],
                       C06_MID_CRIMSON + (C06_CORE_MAGENTA - C06_MID_CRIMSON) * ((t - 0.5) / 0.5)[..., None])
    out_rgb = np.where((a == 0)[..., None], 0.0, out_rgb)

    out_arr = np.dstack([np.rint(np.clip(out_rgb, 0.0, 1.0) * 255.0).astype(np.uint8), a])
    return Image.fromarray(out_arr, 'RGBA')


def recolor_cloud_trail_c07(image: Image.Image) -> Image.Image:
    """Recolor Cloud's sword trail to match Mythra c07 (White & Champagne Gold)."""
    arr = np.array(image.convert('RGBA'))
    rgb = arr[..., :3].astype(np.float64) / 255.0
    a = arr[..., 3]

    # Luminance of Cloud's green/cyan sword trail
    lum = rgb @ np.array([0.2126, 0.7152, 0.0722])
    t = np.clip((lum - 0.12) / (0.95 - 0.12), 0.0, 1.0)

    # Radiant champagne gold body with pure white core
    t_high = (np.maximum(0.0, (t - 0.5) / 0.5) ** 0.8)[..., None]
    out_rgb = np.where((t < 0.5)[..., None],
                       C07_EDGE_GOLD + (C07_MID_GOLD - C07_EDGE_GOLD) * (t / 0.5)[..., None],
                       C07_MID_GOLD + (C07_CORE_WHITE - C07_MID_GOLD) * t_high)
    out_rgb = np.where((a == 0)[..., None], 0.0, out_rgb)

    out_arr = np.dstack([np.rint(np.clip(out_rgb, 0.0, 1.0) * 255.0).astype(np.uint8), a])
    return Image.fromarray(out_arr, 'RGBA')


def build_cloud_trail_nutexb(src_nutexb: Path, dst_nutexb: Path, slot: str) -> None:
    """Read donor NUTEXB, recolor for target slot, and write valid NUTEXB with preserved headers."""
    raw = src_nutexb.read_bytes()
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        src_png = td / 'donor.png'
        new_png = td / 'recolored.png'
        new_nutexb = td / 'output.nutexb'

        convert_image(src_nutexb, src_png)
        donor_img = Image.open(src_png)

        if slot == 'c06':
            themed_img = recolor_cloud_trail_c06(donor_img)
        elif slot == 'c07':
            themed_img = recolor_cloud_trail_c07(donor_img)
        else:
            raise ValueError(f'Unsupported slot: {slot}')

        themed_img.save(new_png)
        convert_image(new_png, new_nutexb, fmt='Rgba8UnormSrgb')

        new_data = bytearray(new_nutexb.read_bytes())
        # Preserve original NUTEXB resource name and footer metadata
        new_data[-108:-44] = raw[-108:-44]
        assert new_data[-44:-20] == raw[-44:-20], 'Footer format/mip/dimensions mismatch'
        dst_nutexb.parent.mkdir(parents=True, exist_ok=True)
        dst_nutexb.write_bytes(new_data)


NAME_BLOCK = slice(-108, -44)  # 64-byte NUL-padded resource name, same region One Slot Effects renames


def nutexb_footer_name(data: bytes) -> str:
    return bytes(data[NAME_BLOCK]).split(bytes(1), 1)[0].decode('ascii')


# Internal resource names the c06/c07 Cloud-move ACMD and the Mythra-derived scripts request
# for an eflame-kind object. One file per name. Pyra's own `tex_eflame_sword1..3` requests are
# deliberately NOT shipped: as baseline they resolve to no registered name and so keep the vanilla
# eflame trail; shipping them would re-theme every ordinary Pyra trail (T-0054 scope: preserve).
EFLAME_TRAIL_FILES = (
    'tex_cloud_sword1', 'tex_cloud_sword2',
    'tex_elight_sword1', 'tex_elight_sword2', 'tex_elight_sword3',
    'tex_elight_sword4', 'tex_elight_sword5',
)


def build_eflame_trail_folder(elight_trail_dir: Path, dst: Path, slot: str) -> list:
    """Write effect/fighter/eflame/trail_<slot>/ with exactly one file per internal name.

    The folder is rebuilt from scratch so aliases from earlier builds cannot survive.
    `tex_elight_sword1..5` come from the already themed Mythra slot folder; the Cloud pair is
    the recoloured/donor ribbon. No `tex_eflame_*` alias files are written.
    """
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)
    for i in range(1, 6):
        shutil.copy2(elight_trail_dir / f'tex_elight_sword{i}.nutexb', dst / f'tex_elight_sword{i}.nutexb')
    build_cloud_trail_nutexb(DONOR_TRAIL_DIR / 'tex_cloud_sword1.nutexb', dst / 'tex_cloud_sword1.nutexb', slot)
    shutil.copy2(DONOR_TRAIL_DIR / 'tex_cloud_sword2.nutexb', dst / 'tex_cloud_sword2.nutexb')
    names = {}
    for f in sorted(dst.glob('*.nutexb')):
        internal = nutexb_footer_name(f.read_bytes())
        assert internal.lower() == f.stem, f'{f.name}: internal name {internal} != file name'
        assert internal not in names, f'duplicate internal name {internal} in {dst}'
        names[internal] = f.name
    assert sorted(p.stem for p in dst.glob('*.nutexb')) == sorted(EFLAME_TRAIL_FILES)
    return sorted(names.values())


def build_all_cloud_trails(output_dir: Path = None) -> dict:
    """Build both c06 and c07 Cloud sword trail packages."""
    if output_dir is None:
        output_dir = PROJECT / 'assets/custom_cloud_trails'

    donor_sword1 = DONOR_TRAIL_DIR / 'tex_cloud_sword1.nutexb'
    donor_sword2 = DONOR_TRAIL_DIR / 'tex_cloud_sword2.nutexb'

    assert donor_sword1.is_file(), f'Missing donor: {donor_sword1}'
    assert donor_sword2.is_file(), f'Missing donor: {donor_sword2}'

    results = {}
    for slot in ('c06', 'c07'):
        slot_dir = output_dir / f'trail_{slot}'
        slot_dir.mkdir(parents=True, exist_ok=True)

        target_sword1 = slot_dir / 'tex_cloud_sword1.nutexb'
        build_cloud_trail_nutexb(donor_sword1, target_sword1, slot)

        target_sword2 = slot_dir / 'tex_cloud_sword2.nutexb'
        target_sword2.write_bytes(donor_sword2.read_bytes())

        results[slot] = {
            'tex_cloud_sword1': {
                'path': target_sword1.as_posix(),
                'bytes': len(target_sword1.read_bytes()),
                'sha256': hashlib.sha256(target_sword1.read_bytes()).hexdigest(),
            },
            'tex_cloud_sword2': {
                'path': target_sword2.as_posix(),
                'bytes': len(target_sword2.read_bytes()),
                'sha256': hashlib.sha256(target_sword2.read_bytes()).hexdigest(),
            },
        }

    return results


if __name__ == '__main__':
    print('Building custom Cloud sword trails for c06 and c07...')
    res = build_all_cloud_trails()
    for s, files in res.items():
        print(f'Slot {s}:')
        for fname, meta in files.items():
            print(f'  {fname}: {meta["bytes"]} B, sha256={meta["sha256"][:16]}...')
    print('Smoke test: successfully generated all Cloud sword trail assets.')
