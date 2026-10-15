import os
import shutil
import hashlib
import importlib.util
import subprocess
import sys
import json

python = sys.executable

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

# Derived from this file's own location instead of hard-coded. The previous
# %USERPROFILE%\...\modpack_test_1 literal meant the whole deploy silently broke
# the moment the workspace moved, which is exactly what happens when it is carried
# to another machine.
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
vendor = os.path.join(root, 'mod_files', 'mythra_gamewatch_swap', 'tools', 'vendor')
os.environ['PYTHONPATH'] = vendor + os.pathsep + os.environ.get('PYTHONPATH', '')
# The dump is read-only game data that used to live outside the workspace, on D:.
# It is now kept at <workspace_root>\export, so that is the default; MGW_EXPORT
# still overrides it when the dump lives somewhere else again.
export_dir = os.environ.get("MGW_EXPORT", os.path.join(root, "dumps", "arc"))
print(f"Workspace root: {root}")
print(f"Game dump:      {export_dir}")
if not os.path.isdir(export_dir):
    raise SystemExit(
        f"Game dump not found at {export_dir}. Set MGW_EXPORT to the "
        f"ArcExplorer export directory before deploying."
    )

# 1. Deploy NRO
src_nro = os.path.join(root, r"mod_files\mythra_gamewatch_swap\target\aarch64-skyline-switch\release\libmythra_gamewatch_swap.nro")
dst_nro_dir = os.path.join(root, r"mod_output\atmosphere\contents\01006A800016E000\romfs\skyline\plugins")
os.makedirs(dst_nro_dir, exist_ok=True)
dst_nro = os.path.join(dst_nro_dir, "libmythra_gamewatch_swap.nro")
shutil.copy2(src_nro, dst_nro)
print(f"NRO Deployed: {dst_nro}")
print(f"  Size: {os.path.getsize(dst_nro)} bytes")
print(f"  SHA256: {sha256_file(dst_nro)}")

# 2. Deploy Corrin Up Air Animation
src_anim_uair = os.path.join(export_dir, "fighter", "kamui", "motion", "body", "c00",
                             "c05attackairhi.nuanmb")
dst_anim_dir = os.path.join(root, r"mod_output\ultimate\mods\mythra_gamewatch_swap\fighter\elight\motion\body\c07")
os.makedirs(dst_anim_dir, exist_ok=True)
dst_anim_uair = os.path.join(dst_anim_dir, "c05attackairhi.nuanmb")
shutil.copy2(src_anim_uair, dst_anim_uair)
print(f"Corrin U-Air Animation Deployed: {dst_anim_uair}")
print(f"  Size: {os.path.getsize(dst_anim_uair)} bytes")
print(f"  SHA256: {sha256_file(dst_anim_uair)}")

# 3. Deploy Luigi Down Throw Animation
src_anim_dthrow = os.path.join(export_dir, "fighter", "luigi", "motion", "body", "c00",
                               "e01throwlw.nuanmb")
dst_anim_dthrow = os.path.join(dst_anim_dir, "e01throwlw.nuanmb")
shutil.copy2(src_anim_dthrow, dst_anim_dthrow)
print(f"Luigi D-Throw Animation Deployed: {dst_anim_dthrow}")
print(f"  Size: {os.path.getsize(dst_anim_dthrow)} bytes")
print(f"  SHA256: {sha256_file(dst_anim_dthrow)}")

# 4. Deploy Monkey Flip Assets to Game & Watch c07
#
# This step used to run references/inject_monkey_flip.py, which copies Diddy's
# twelve d01*.nuanmb files byte for byte with shutil.copy2. Diddy has 85 bones
# and G&W c07 has 45, so that deployed 47 stray tracks per motion, plus Diddy's
# own visibility and material groups naming Diddy's meshes and materials.
#
# Worse, it meant every deploy silently reverted any retargeting that had been
# done, so the animation could never improve no matter how often the assets were
# fixed. The retargeting tool replaces it and asserts its own invariants:
# 84 donor transform tracks per motion, 37 surviving bone-name intersection, and
# 746 unrelated motion-list entries byte-identical to the baseline.
#
# inject_monkey_flip.py is left on disk as provenance only. Do not call it.
mflip_script = os.path.join(root, r"mod_files\mythra_gamewatch_swap\tools\build_monkey_flip_assets.py")
if os.path.exists(mflip_script):
    subprocess.run([python, mflip_script], check=True)
    print("Monkey Flip motions retargeted by bone-name intersection and deployed to Game & Watch c07!")
else:
    raise SystemExit(f"Missing retargeting tool: {mflip_script}")

# 5. Build the actual Mii Swordfighter Hi3 clips. The old builder creates Hi1
# (Stone Scabbard) and must never run for this payload.
hero_spin_build = os.path.join(root, r"mod_files\mythra_gamewatch_swap\tools\build_hero_spin3_assets.py")
subprocess.run([python, hero_spin_build], check=True)
hero_spin_manifest = os.path.join(root, r"references\miiswordsman_special_hi3\animation_manifest.json")
with open(hero_spin_manifest, encoding='utf-8') as stream:
    hi3_manifest = json.load(stream)
print("Hi3 assets built and read back; manifest:", hero_spin_manifest)

# 6. Deploy Shulk Fair Assets to Game & Watch c07
fair_script = os.path.join(root, r"mod_files\mythra_gamewatch_swap\tools\build_fair_assets.py")
if os.path.exists(fair_script):
    subprocess.run([python, fair_script], check=True)
    print("Shulk Fair Assets and Motion List Deployed to Game & Watch c07!")

# Extend every current replacement to c06 after all c07 builders finish.
subprocess.run([python, os.path.join(root, r"mod_files\mythra_gamewatch_swap\tools\extend_costume_assets.py")], check=True)
subprocess.run([python, os.path.join(root, r"mod_files\mythra_gamewatch_swap\tools\verify_hero_spin3_payload.py")], check=True)

# Copy BOTH trees to the SD card: the plugin and the animation assets live in
# separate trees, and copying only one of them is exactly how the vanilla-up-B
# defect in the Hero Spin build reached hardware.
print()
print("Deploy complete. Copy BOTH trees to the SD card:")
print("  mod_output/atmosphere/     -> the SD card's atmosphere/     (the Skyline plugin)")
print("  mod_output/ultimate/mods/  -> the SD card's ultimate/mods/  (the animation assets)")
print("  Copying only one tree ships a plugin without its animations, or the reverse.")
