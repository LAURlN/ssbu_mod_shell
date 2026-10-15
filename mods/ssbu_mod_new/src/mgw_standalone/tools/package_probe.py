"""Assemble the local Switch test files in mod_output's SD root layout.

Uses the user's c00 model dumps and a pinned upstream archive-path index.
No game archive is downloaded. Donor files are copied from the user's export;
unavailable inputs are recorded separately from the materialized resources.
"""
from pathlib import Path
import hashlib
import json
import shutil
import struct
import subprocess
import sys
import tempfile
import zipfile
import xml.etree.ElementTree as ET
from build_probe_ui import build_ui, import_skin_portraits
from copy_probe_resources import copy_resources, validate_motion_references
from copy_probe_skins import import_model_and_effects

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parents[1]
WORKBENCH = ROOT / "vendor/clone_pack_workbench"
ENGINE = ROOT / "vendor/ssbu_clone_engine"
DOWNLOADS = ROOT / "downloads"
PLUGIN_DIR = Path("atmosphere/contents/01006A800016E000/romfs/skyline/plugins")
PACK_DIR = Path("ultimate/mods/MGW_Standalone_Probe")
PINNED = {
    ENGINE: "b420a90de60584e6fc18266a870570dc7fb0435b",
    WORKBENCH: "495e7ba99f0020cb9a5e87afd6d3fa6a64e03fcc",
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_nro(path):
    data = path.read_bytes()
    if data[0x10:0x14] != b"NRO0":
        raise ValueError(f"Not an NRO: {path}")
    # Assets may follow the declared loadable NRO image.
    image_size = struct.unpack_from("<I", data, 0x18)[0]
    if image_size < 0x80 or image_size > len(data):
        raise ValueError(f"Invalid NRO image size: {path}")


def official_binary(filename, metadata, tag):
    release = json.loads((DOWNLOADS / metadata).read_text(encoding="utf-8-sig"))
    assert release["tag_name"] == tag, (metadata, release["tag_name"])
    asset = next(a for a in release["assets"] if a["name"] == filename)
    binary = DOWNLOADS / filename
    assert binary.stat().st_size == asset["size"], filename
    digest = asset.get("digest")
    if digest:
        assert digest == "sha256:" + sha(binary), filename
    check_nro(binary)
    return binary, {"version": tag, "source": asset["browser_download_url"],
                    "sha256": sha(binary)}


OVERLAY_PATCHES = {
    ENGINE: ROOT / "engine-local-changes.patch",
    WORKBENCH: ROOT / "workbench-local-changes.patch",
}


def recorded_vendor_diff(repo):
    """The MGW overlay edits tracked vendor files, so the tree is never pristine.

    The diff must match the reviewed patch recorded beside this script; any
    further edit fails the package until that patch is regenerated on purpose.
    """
    diff = subprocess.check_output(["git", "-C", str(repo), "diff", "--no-color"], text=True)
    recorded = OVERLAY_PATCHES.get(repo)
    expected = recorded.read_text(encoding="utf-8") if recorded and recorded.is_file() else ""
    normalise = lambda text: text.replace("\r\n", "\n").strip()
    if normalise(diff) != normalise(expected):
        raise ValueError(
            f"Vendor source carries changes the recorded overlay does not describe: {repo}; "
            f"review the diff and regenerate {recorded.name if recorded else 'the overlay patch'}"
        )
    return sha(recorded) if recorded and recorded.is_file() else None


def main():
    overlays = {}
    for repo, revision in PINNED.items():
        actual = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
        if actual != revision:
            raise ValueError(f"Wrong vendor revision: {repo}: {actual}")
        overlay_sha = recorded_vendor_diff(repo)
        if overlay_sha:
            overlays[repo.name] = overlay_sha
    probe = ROOT / "target/aarch64-skyline-switch/release/libmgw_clone_probe.nro"
    check_nro(probe)
    legacy = WORKSPACE / "mod_output" / PLUGIN_DIR / "libmythra_gamewatch_swap.nro"
    legacy_before = sha(legacy) if legacy.is_file() else None
    dependencies = {}
    model_sources = {}
    staging_parent = ROOT / "staging"
    staging_parent.mkdir(exist_ok=True)
    # Every run has an isolated staging directory. Never delete or merge a
    # previous install tree while building a package.
    staging = Path(tempfile.mkdtemp(prefix="p8-", dir=staging_parent))
    sdroot = staging / "sdroot"
    pack = sdroot / PACK_DIR
    shutil.copytree(ROOT / "pack", pack)
    shutil.copy2(probe, pack / "plugin.nro")
    for base, clone in (("elight", "mgw_mythra"), ("eflame", "mgw_pyra")):
        source = WORKSPACE / f"export/fighter/{base}/model/body/c00"
        if not (source / "model.numdlb").is_file():
            raise FileNotFoundError(f"Missing user's base model dump: {source}")
        shutil.copytree(source, pack / f"fighter/{clone}/model/body/c00")
        for path in sorted(source.rglob("*")):
            if path.is_file():
                model_sources[path.relative_to(WORKSPACE).as_posix()] = sha(path)
    messages = ET.Element("xmsbt")
    for identity, label in (("mgw_mythra", "MGW Mythra Pair"), ("mgw_pyra", "MGW Pyra Pair")):
        for variant in range(4):
            entry = ET.SubElement(messages, "entry", label=f"nam_chr{variant}_00_{identity}")
            ET.SubElement(entry, "text").text = label
    msg_path = pack / "ui/message/msg_name.xmsbt"
    msg_path.parent.mkdir(parents=True, exist_ok=True)
    if hasattr(ET, "indent"):
        ET.indent(messages)
    ET.ElementTree(messages).write(msg_path, encoding="utf-8", xml_declaration=True)
    logs = []
    for identity in ("mgw_mythra", "mgw_pyra"):
        command = [sys.executable, str(WORKBENCH / "make_clone_pack.py"),
                   "--clone", identity, "--pack-dir", str(pack),
                   "--out", str(pack / "config.json"), "--merge"]
        logs.append(subprocess.check_output(command, text=True, encoding="utf-8"))
    config = json.loads((pack / "config.json").read_text(encoding="utf-8"))
    donor_manifest = copy_resources(WORKSPACE / "dumps" / "arc", pack, config)
    skin_manifest = import_model_and_effects(WORKSPACE, pack)
    motion_audit = validate_motion_references(pack, donor_manifest)
    (ROOT / 'p8-motion-audit.json').write_text(json.dumps(motion_audit, indent=2)+'\n', encoding='utf-8')
    # Rebuild from the actual files now present. Starting with an empty config
    # prevents the vendor merger retaining stale shares when a section empties.
    (pack / "config.json").write_text("{}\n", encoding="utf-8")
    for identity in ("mgw_mythra", "mgw_pyra"):
        command = [sys.executable, str(WORKBENCH / "make_clone_pack.py"),
                   "--clone", identity, "--pack-dir", str(pack),
                   "--out", str(pack / "config.json"), "--merge"]
        logs.append(subprocess.check_output(command, text=True, encoding="utf-8"))
    config = json.loads((pack / "config.json").read_text(encoding="utf-8"))
    aliased = {dst for targets in config['share-to-vanilla'].values() for dst in targets}
    for resource in donor_manifest['copied']:
        assert resource['destination'] not in aliased, resource['destination']
    (ROOT / 'donor-copy-manifest.json').write_text(json.dumps(donor_manifest, indent=2)+'\n', encoding='utf-8')
    ui_manifest = build_ui(WORKSPACE / "dumps" / "arc", pack, config)
    skin_manifest['portraits'] = import_skin_portraits(
        WORKSPACE, pack, config, ui_manifest
    )
    (ROOT / 'skin-import-manifest.json').write_text(
        json.dumps(skin_manifest, indent=2)+'\n', encoding='utf-8'
    )
    (pack / "config.json").write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    command = [sys.executable, str(WORKBENCH / "lint_clone_pack.py"), str(pack)]
    lint = subprocess.run(command, text=True, encoding="utf-8", capture_output=True)
    logs.append(lint.stdout + lint.stderr)
    (ROOT / "package-check.log").write_text("\n".join(logs), encoding="utf-8")
    if lint.returncode:
        raise RuntimeError("Clone pack lint failed; see package-check.log")
    config = json.loads((pack / "config.json").read_text(encoding="utf-8"))
    is_ours = lambda path: "mgw_mythra" in path or "mgw_pyra" in path
    # Sharing FROM base files is expected; targeting base files is not.
    destinations = list(config["new-dir-infos"])
    destinations += list(config["new-dir-infos-base"])
    for group, members in config["new-dir-files"].items():
        if not group.startswith("ui/replace/chara/chara_"):
            destinations.append(group)
        destinations += members
    for section in ("share-to-vanilla", "share-to-added"):
        destinations += [target for targets in config[section].values() for target in targets]
    foreign = [path for path in destinations if not is_ours(path)]
    if foreign:
        raise ValueError(f"Config writes outside the clone namespaces: {foreign[:10]}")
    plugins = sdroot / PLUGIN_DIR
    plugins.mkdir(parents=True)
    route_log = sdroot / "ultimate/clone_engine/p16-model-route.txt"
    route_log.parent.mkdir(parents=True, exist_ok=True)
    route_log.write_text("p16 route log seeded by the local package\n", encoding="utf-8")
    engine_built = ROOT / "target-engine/aarch64-skyline-switch/release/libssbu_clone_engine.nro"
    if not engine_built.is_file():
        engine_built = ENGINE / "target/aarch64-skyline-switch/release/libssbu_clone_engine.nro"
    if engine_built.is_file() and overlays.get(ENGINE.name):
        check_nro(engine_built)
        shutil.copy2(engine_built, plugins / "libssbu_clone_engine.nro")
        dependencies["libssbu_clone_engine.nro"] = {
            "version": "0.3.1-beta.1 + MGW p16 Pyra Mythra pair prototype",
            "source": "vendor/ssbu_clone_engine",
            "patch_sha256": overlays[ENGINE.name],
            "sha256": sha(engine_built),
        }
    else:
        binary, provenance = official_binary("libssbu_clone_engine.nro", "clone-engine-release.json", "0.3.1-beta.1")
        shutil.copy2(binary, plugins / "libssbu_clone_engine.nro")
        dependencies["libssbu_clone_engine.nro"] = provenance

    binary, provenance = official_binary("libnro_hook.nro", "nro-hook-release.json", "v0.4.0")
    shutil.copy2(binary, plugins / "libnro_hook.nro")
    dependencies["libnro_hook.nro"] = provenance
    runtime = ROOT / "target-smashline/aarch64-skyline-switch/release/libsmashline_plugin.nro"
    check_nro(runtime)
    shutil.copy2(runtime, plugins / "libsmashline_plugin.nro")
    dependencies["libsmashline_plugin.nro"] = {
        "version": "v1.6.8 + MGW p7 verified resource globals, name tables and path hooks",
        "source": "https://github.com/HDR-Development/smashline/releases/tag/v1.6.8",
        "source_archive_sha256": sha(DOWNLOADS / "smashline-v1.6.8-source.zip"),
        "offset_audit_sha256": sha(ROOT / "offset-audit.json"),
        "lockfile_sha256": sha(ROOT / "smashline_1304/Cargo.lock"),
        "sha256": sha(runtime),
    }
    csk_zip = DOWNLOADS / "the_csk_collection_5_0_6.zip"
    assert hashlib.md5(csk_zip.read_bytes()).hexdigest() == "323d6be25d2bff100dad4d3ae3b20bcb"
    csk_name = "libthe_csk_collection.nro"
    with zipfile.ZipFile(csk_zip) as archive:
        # Extract only the runtime, not CSK's optional feature packs.
        (plugins / csk_name).write_bytes(archive.read((PLUGIN_DIR / csk_name).as_posix()))
    check_nro(plugins / csk_name)
    dependencies[csk_name] = {"version": "5.0.6 (13.0.4)",
        "source": "https://gamebanana.com/dl/1745532",
        "archive_sha256": sha(csk_zip), "sha256": sha(plugins / csk_name)}
    shutil.copy2(ROOT / "README.md", staging / "START_HERE.md")
    shutil.copy2(ROOT / "ARCHITECTURE.md", staging / "ARCHITECTURE.md")
    shutil.copy2(ROOT / "DIAGNOSIS.md", staging / "DIAGNOSIS.md")
    shutil.copy2(ROOT / "offset-audit.json", staging / "offset-audit.json")
    for evidence in ("MISSING_DUMPS.md", "donor-copy-manifest.json",
                     "p8-motion-audit.json", "skin-import-manifest.json",
                     "native-support-audit.json", "engine-local-changes.patch",
                     "p11-validation.json", "workbench-local-changes.patch"):
        shutil.copy2(ROOT / evidence, staging / evidence)
    (staging / "ui-validation.json").write_text(json.dumps(ui_manifest,indent=2)+"\n")
    licenses = staging / "licenses"
    licenses.mkdir()
    shutil.copy2(ENGINE / "LICENSE", licenses / "clone-engine-GPL-3.0.txt")
    shutil.copy2(WORKBENCH / "LICENSE", licenses / "clone-pack-workbench.txt")
    shutil.copy2(ROOT / "package-check.log", staging / "package-check.log")
    manifest = {"build": "p16-pair", "game_version": "13.0.4", "hardware_tested": False,
        "engine_commit": PINNED[ENGINE], "workbench_commit": PINNED[WORKBENCH],
        "vendor_overlays": overlays,
        "probe_sha256": sha(probe), "dependencies": dependencies,
        "user_dump_models": model_sources,
        "donor_resources": donor_manifest,
        "skin_imports": skin_manifest,
        "ui_textures": ui_manifest,
        "files": {p.relative_to(sdroot).as_posix(): sha(p) for p in sorted(sdroot.rglob("*")) if p.is_file()}}
    for resource in donor_manifest['copied']:
        assert sha(WORKSPACE / 'dumps' / 'arc' / resource['source']) == resource['source_sha256'], (
            'Donor input changed during packaging; wait for extraction and rebuild', resource['source'])
    for resource in skin_manifest['copied'] + skin_manifest['portraits']:
        assert sha(WORKSPACE / resource['source']) == resource['source_sha256'], (
            'Skin input changed during packaging', resource['source'])
        assert sha(pack / resource['destination']) == resource['output_sha256'], (
            'Skin output changed during packaging', resource['destination'])
    (staging / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    output = WORKSPACE / "mod_output_pair"
    sdroot = staging / "sdroot"
    # An earlier package fabricated a bunshin model by copying the body model.
    # Bunshin actually requests the body directory, so remove only that known
    # stale generated folder from the shared SD output before copying this pack.
    stale_bunshin = output / PACK_DIR / "fighter/mgw_mythra/model/bunshin"
    if stale_bunshin.is_dir():
        relative_stale = stale_bunshin.resolve().relative_to(output.resolve())
        assert len(relative_stale.parts) >= 4, relative_stale
        shutil.rmtree(stale_bunshin)
    copied = []
    for path in sorted(sdroot.rglob("*")):
        if path.is_file():
            destination = output / path.relative_to(sdroot)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, destination)
            if sha(path) != sha(destination):
                raise IOError(f"Copy verification failed: {destination}")
            copied.append(destination.relative_to(output).as_posix())
    if legacy_before is not None:
        assert sha(legacy) == legacy_before, "Legacy plugin changed during packaging"
    result = {"output_directory": str(output), "sdroot_files": len(copied),
              "files": copied, "staging": str(staging),
              "legacy_plugin_sha256": legacy_before,
              "probe_sha256": sha(probe), "pack_lint_exit": lint.returncode}
    (ROOT / "package-result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key:value for key,value in result.items() if key!='files'}, indent=2))


if __name__ == "__main__":
    main()
