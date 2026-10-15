"""Root-level offline CLI launcher; standard-library only, no implicit build or downloads."""
import argparse
import hashlib
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).absolute().parents[2]
PIN = "df35642dd8d43472414a58a45fb7c5c22858764abf114ea09bff7bb08bad5b16"


def confined(value):
    if any(part != '.' and part.endswith((' ', '.')) for part in Path(value).parts):
        raise ValueError("Windows trailing-dot/space path aliases are unsupported.")
    path = Path(os.path.abspath(ROOT / value))
    if ".." in Path(value).parts or not path.is_relative_to(ROOT) or path == ROOT:
        raise ValueError("Use a direct path strictly inside this workspace.")
    for ancestor in (path, *path.parents):
        if ancestor.is_symlink() or ancestor.is_junction():
            raise ValueError("Symlinks and junctions are unsupported.")
    if ":" in str(path)[len(path.anchor):]:
        raise ValueError("Alternate data streams are unsupported.")
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", default="tools/data-arc-extract/.cache/build/bin/DataArcExtract.dll")
    parser.add_argument("--dotnet", default="dotnet", help="Installed SDK host or explicit workspace SDK executable")
    parser.add_argument("mode", choices=("discover", "preflight", "extract"))
    args, remaining = parser.parse_known_args()
    if any(arg == "--workspace" or arg.startswith("--workspace=") for arg in remaining):
        raise ValueError("Workspace is fixed by this launcher.")
    app = confined(args.app)
    if not app.is_file():
        raise ValueError("Missing application. Run setup.ps1 -Build first.")
    dependency = confined(str(app.parent / "LibHac.dll"))
    with dependency.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != PIN:
            raise ValueError("Adjacent LibHac.dll pin mismatch; rerun pinned setup.")
    host = args.dotnet if args.dotnet == "dotnet" else str(confined(args.dotnet))
    # The runtime performs no build or restore; TEMP/TMP stay in this tool's ignored cache so
    # no temporary file can ever land outside gamedata/ or inside the user's dump.
    temp = confined("tools/data-arc-extract/.cache/temp")
    temp.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env.update(DOTNET_CLI_TELEMETRY_OPTOUT="1", DOTNET_SKIP_FIRST_TIME_EXPERIENCE="1",
               DOTNET_MULTILEVEL_LOOKUP="0", DOTNET_EnableDiagnostics="0",
               DOTNET_DbgEnableMiniDump="0", TEMP=str(temp), TMP=str(temp))
    # The runtime performs no restore/build and writes no scratch beyond TEMP above.
    return subprocess.run([host, str(app), args.mode, "--workspace", str(ROOT), *remaining],
                          cwd=ROOT, env=env, check=False).returncode


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, OSError) as error:
        print(f"Launcher prerequisite/path error: {error}", file=sys.stderr)
        sys.exit(1)
