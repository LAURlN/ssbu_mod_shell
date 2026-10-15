"""Build a local EffectLibrary primitive-preservation repair (v1.1.0).

Pinned source: refs/brave_special_n/effect_library at d5491138d645221ec92189eeff3ded8c43fd0a1a
(KillzXGaming/EffectLibrary, LICENSE MIT, cloned by tools/fetch_effect_library.py).
The v1.9 primitive writer retained the old BFRES binary after rebuilding its
descriptor list. Enable serialization, preserve one model per descriptor,
and export the actual requested model for volume/extra primitives.
Also serialize rebuilt textures and retain the opaque TRMA section.
This tool edits only a derived source copy in builds/.cache, never the pinned
source or framework plugins. --check checks the patch against pinned source.
Output is a build tool, not an SD plugin. Offline effect re-export validation
remains mandatory.

Two build routes, both producing the same bin/ layout the merge tools expect
(EffectConverter.exe + EffectLibrary.dll + HeroTextureRename.exe):
  --from-source  compile the pinned tree with the local .NET SDK (default when
                 toolchain.effect_converter is unset). Project-local only: the
                 NuGet package folder and the source copy live in builds/.cache.
  (default)      relink EffectLibrary.dll with toolchain.roslyn_csc on top of a
                 prebuilt EffectConverter from toolchain.effect_converter.
Usage: python tools/build_hero_effect_converter.py [--check|--from-source]
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tomllib

ROOT = Path(__file__).resolve().parents[1]
CFG = tomllib.loads((ROOT / 'paths.toml').read_text())
SRC = ROOT / 'refs/brave_special_n/effect_library/EffectLibrary'
WORK = ROOT / 'builds/.cache/hero_effect_converter'
PIN = 'd5491138d645221ec92189eeff3ded8c43fd0a1a'
REPO_URL = 'https://github.com/KillzXGaming/EffectLibrary'
NUGET = WORK / 'nuget'

# Upstream EffectConverter/Program.cs at the pinned commit does not compile: it
# uses PtclFile, which lives in namespace EffectLibrary.EFT2, without importing
# it. The original route never noticed because it relinked EffectLibrary.dll
# against a prebuilt converter. One added using is the whole fix.
PROGRAM_USING = ('using EffectLibrary.Tools;', 'using EffectLibrary.Tools;\nusing EffectLibrary.EFT2;')

# The relocation helpers are extra console projects in the derived copy, so the
# SDK route builds them instead of invoking Roslyn by hand. Both need the
# BfresLibrary/Bntx pair; the model helper is the one that reads ResFile.
RENAME_PROJECT = '''<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net6.0</TargetFramework>
    <ImplicitUsings>enable</ImplicitUsings>
    <Nullable>enable</Nullable>
    <AssemblyName>{name}</AssemblyName>
    <RootNamespace>{name}</RootNamespace>
  </PropertyGroup>
  <ItemGroup>
    <Reference Include="BfresLibrary">
      <HintPath>..\\EffectLibrary\\LIb\\BfresLibrary.dll</HintPath>
    </Reference>
    <Reference Include="Syroot.NintenTools.NSW.Bntx">
      <HintPath>..\\EffectLibrary\\LIb\\Syroot.NintenTools.NSW.Bntx.dll</HintPath>
    </Reference>
    <Reference Include="Syroot.BinaryData">
      <HintPath>..\\EffectLibrary\\LIb\\Syroot.BinaryData.dll</HintPath>
    </Reference>
    <Reference Include="Syroot.Maths">
      <HintPath>..\\EffectLibrary\\LIb\\Syroot.Maths.dll</HintPath>
    </Reference>
  </ItemGroup>
  <ItemGroup>
    <PackageReference Include="Newtonsoft.Json" Version="13.0.3" />
  </ItemGroup>
</Project>
'''

# A model whose name already exists in the bank is silently suffixed with its id
# by the primitive-writer patch. That is load-bearing (it stops the donor's mesh
# being dropped) but it makes a byte-exact round trip unpredictable, so the
# merge renames the exported model up front instead.
MODEL_RENAME_SOURCE = r'''
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using BfresLibrary;
using Newtonsoft.Json.Linq;
class HeroModelRename {
    // Everything except the container name, the container alignment fields the
    // reader does not round-trip, and each model's own Name, so the comparison
    // covers bones, vertex buffers, indices, materials and the rest.
    // ResFile.Models serializes as a list of {Key, Value} dictionary entries.
    static readonly string[] ContainerOnly = { "Name", "Alignment", "DataAlignment" };
    // The dumper always writes one model per container, so a mismatch here
    // means the input is not the shape this helper was written for.
    static JToken Fields(ResFile file) {
        var fields = JObject.FromObject(file);
        foreach (var field in ContainerOnly) fields.Remove(field);
        var models = fields[nameof(file.Models)];
        if (models != null)
            foreach (var entry in models.Children().Cast<JObject>()) {
                // The dictionary key is the model's name, so it moves with it.
                entry.Remove("Key");
                var value = entry["Value"] as JObject;
                if (value != null) value.Remove("Name");
            }
        return fields;
    }
    static void Main(string[] args) {
        var original = new ResFile(args[0]);
        if (original.Models.Count != 1) throw new Exception("Expected one exported model");
        var control = Fields(original);
        var model = original.Models.Values.First();
        var name = args[2];
        // Renaming in place leaves the old name in the container's cached name
        // table, so the re-exported bank would not match byte for byte. Build a
        // fresh single-model container using the pinned dumper's own container
        // literal: its header fields are not round-tripped by the reader, so
        // copying them back from the file would produce a different container.
        var renamed = new ResFile() {
            IsPlatformSwitch = true,
            VersionMajor = 0, VersionMajor2 = 5,
            VersionMinor = 0, VersionMinor2 = 3,
            Alignment = 0xC,
            ByteOrder = Syroot.BinaryData.ByteOrder.LittleEndian,
            Name = name,
        };
        model.Name = name;
        renamed.Models.Add(name, model);
        renamed.Save(args[1]);
        var reread = new ResFile(args[1]);
        if (!JToken.DeepEquals(Fields(reread), control))
            throw new Exception("Model payload or metadata changed during rename");
        if (reread.Models.Values.First().Name != name)
            throw new Exception("Model name was not relocated");
        Console.WriteLine("PASS: model name relocated; every other model field identical");
    }
}
'''


def dotnet():
    """Project-local .NET SDK: machine path from paths.toml, else the launcher."""
    configured = CFG['toolchain'].get('dotnet_sdk') or ''
    if configured:
        return Path(configured)
    found = shutil.which('dotnet')
    assert found, 'No .NET SDK: set toolchain.dotnet_sdk in paths.toml'
    return Path(found)

# Rename only a texture's descriptor name. A complete serialize/read cycle
# must preserve every other decoded texture field and every mip byte.
TEXTURE_RENAME_SOURCE = r'''
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using Syroot.NintenTools.NSW.Bntx;
using Newtonsoft.Json.Linq;
class HeroTextureRename {
    static byte[] Save(BntxFile file) {
        using (var stream = new MemoryStream()) { file.Save(stream); return stream.ToArray(); }
    }
    static JToken Fields(Texture texture) {
        var fields = JObject.FromObject(texture); fields.Remove("Name"); return fields;
    }
    static void Main(string[] args) {
        var original = new BntxFile(new MemoryStream(File.ReadAllBytes(args[0])));
        if (original.Textures.Count != 1) throw new Exception("Expected one exported texture");
        var texture = original.Textures[0]; var control = Fields(texture);
        texture.Name = args[2];
        // Match the pinned exporter's fresh single-texture container. Reusing
        // the original container retains an obsolete cached name string.
        var renamed = new BntxFile();
        renamed.Target = original.Target; renamed.Name = texture.Name;
        renamed.Alignment = original.Alignment; renamed.TargetAddressSize = original.TargetAddressSize;
        renamed.VersionMajor = original.VersionMajor; renamed.VersionMajor2 = original.VersionMajor2;
        renamed.VersionMinor = original.VersionMinor; renamed.VersionMinor2 = original.VersionMinor2;
        renamed.Flag = original.Flag; renamed.RelocationTable = new RelocationTable();
        renamed.Textures = new List<Texture>() { texture };
        renamed.TextureDict = new ResDict(); renamed.TextureDict.Add(texture.Name);
        var output = Save(renamed);
        var reread = new BntxFile(new MemoryStream(output));
        if (!JToken.DeepEquals(Fields(reread.Textures[0]), control))
            throw new Exception("Texture payload or metadata changed during rename");
        File.WriteAllBytes(args[1], output);
        Console.WriteLine("PASS: texture name relocated; every other texture field and mip byte identical");
    }
}
'''


def patched_sources():
    sources = {p.relative_to(SRC).as_posix(): p.read_text() for p in SRC.rglob('*.cs')}
    key = 'FileData/EFT2/Primitives.cs'
    text = sources[key]
    assert text.count('// SaveBinary();') == 1
    text = text.replace('// SaveBinary();', 'SaveBinary();')
    old = 'if (!ResFile.Models.ContainsKey(model.Name))\n                ResFile.Models.Add(model.Name, model);'
    assert old in text
    text = text.replace(old, 'if (ResFile.Models.ContainsKey(model.Name))\n'
                        '                model.Name += "_" + id.ToString();\n'
                        '            ResFile.Models.Add(model.Name, model);')
    sources[key] = text
    key = 'Tools/PtclFileDumper.cs'
    text = sources[key]
    old = text[text.index('            void DumpModel('):text.index('            void DumpTexures(')]
    new = old.replace('void DumpModel(string filePath)', 'void DumpModel(string filePath, Model exportModel)')
    new = new.replace('Name = model.Name', 'Name = exportModel.Name')
    new = new.replace('resFile.Models.Add(model.Name, model);', 'resFile.Models.Add(exportModel.Name, exportModel);')
    new = new.replace('PrimitiveID}.bfres"));', 'PrimitiveID}.bfres"), model);')
    new = new.replace('PrimitiveIndex}.bfres"));', 'PrimitiveIndex}.bfres"), model_volume);')
    new = new.replace('PrimitiveExID}.bfres"));', 'PrimitiveExID}.bfres"), model_extra);')
    assert old != new
    sources[key] = text.replace(old, new)
    key = 'FileData/EFT2/Textures.cs'
    text = sources[key]
    assert text.count('/*  if (BntxFile != null)') == 1
    text = text.replace('/*  if (BntxFile != null)', 'if (BntxFile != null)')
    assert text.count('            }*/') == 1
    sources[key] = text.replace('            }*/', '            }')
    key = 'FileData/EFT2/PtclFile.cs'
    text = sources[key]
    assert text.count('//  TRMA?.Write(writer, this);') == 1
    sources[key] = text.replace('//  TRMA?.Write(writer, this);',
                               'if (TRMA?.Data != null) TRMA.Write(writer, this);')
    sources['GlobalUsings.cs'] = '\n'.join('global using ' + n + ';' for n in (
        'System', 'System.Collections.Generic', 'System.IO', 'System.Linq',
        'System.Net.Http', 'System.Threading', 'System.Threading.Tasks'))
    sources['AssemblyInfo.cs'] = '[assembly: System.Reflection.AssemblyVersion("1.0.0.0")]\n'
    return sources


def build_from_source(sources):
    """Compile the patched pinned tree with the local SDK into WORK/bin."""
    tree = WORK / 'src'
    if tree.exists():
        shutil.rmtree(tree)
    tree.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SRC.parent, tree, ignore=shutil.ignore_patterns('.git'))
    for relative, text in sources.items():
        # patched_sources() targets the library; the two extra files it adds are
        # csc-only and conflict with the SDK's implicit usings and attributes.
        if relative in ('GlobalUsings.cs', 'AssemblyInfo.cs'):
            continue
        (tree / 'EffectLibrary' / relative).write_text(text)
    program = tree / 'EffectConverter' / 'Program.cs'
    text = program.read_text()
    assert text.count(PROGRAM_USING[0]) == 1, 'Pinned Program.cs layout changed'
    program.write_text(text.replace(*PROGRAM_USING))
    rename = tree / 'HeroTextureRename'
    rename.mkdir()
    (rename / 'HeroTextureRename.cs').write_text(TEXTURE_RENAME_SOURCE)
    (rename / 'HeroTextureRename.csproj').write_text(
        RENAME_PROJECT.format(name='HeroTextureRename'))
    model_rename = tree / 'HeroModelRename'
    model_rename.mkdir()
    (model_rename / 'HeroModelRename.cs').write_text(MODEL_RENAME_SOURCE)
    (model_rename / 'HeroModelRename.csproj').write_text(
        RENAME_PROJECT.format(name='HeroModelRename'))
    output = WORK / 'bin'
    if output.exists():
        shutil.rmtree(output)
    env = dict(os.environ, DOTNET_CLI_TELEMETRY_OPTOUT='1', DOTNET_NOLOGO='1',
               NUGET_PACKAGES=str(NUGET), DOTNET_CLI_HOME=str(WORK / 'home'))
    for project in ('EffectConverter/EffectConverter.csproj',
                    'HeroTextureRename/HeroTextureRename.csproj',
                    'HeroModelRename/HeroModelRename.csproj'):
        result = subprocess.run([str(dotnet()), 'build', str(tree / project), '-c', 'Release',
                                 '-o', str(output)], capture_output=True, text=True, env=env)
        assert result.returncode == 0, result.stdout[-4000:] + result.stderr[-4000:]
    for name in ('EffectConverter.exe', 'EffectLibrary.dll', 'HeroTextureRename.exe',
                 'HeroModelRename.exe'):
        assert (output / name).is_file(), f'SDK build did not produce {name}'
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--from-source', action='store_true',
                        help='compile the pinned tree with the local .NET SDK')
    args = parser.parse_args()
    commit = subprocess.check_output(['git', '-C', str(SRC.parent), 'rev-parse', 'HEAD'], text=True).strip()
    assert commit == PIN
    sources = patched_sources()
    if args.check:
        print('PASS: pinned source; primitive, texture and TRMA preservation patches')
        return
    if args.from_source or not CFG['toolchain']['effect_converter']:
        output = build_from_source(sources)
        sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
        record = {'date': '2026-10-02', 'tool_version': '1.1.0', 'route': 'sdk-build',
                  'repo': REPO_URL, 'source_commit': commit, 'license': 'MIT',
                  'sdk': str(dotnet()), 'output': output.relative_to(ROOT).as_posix(),
                  'binaries': {p.name: sha(p) for p in sorted(output.glob('*')) if p.is_file()},
                  'patched_sources': {p: hashlib.sha256(t.encode()).hexdigest()
                                      for p, t in sources.items()},
                  'program_using_added': list(PROGRAM_USING[1].splitlines()),
                  'framework_plugins_touched': False, 'hardware_validated': False}
        (WORK / 'MANIFEST.json').write_text(json.dumps(record, indent=2) + '\n')
        print(f'Built repaired EffectConverter from pinned {commit[:12]} into {output}')
        return
    converter = Path(CFG['toolchain']['effect_converter'])
    output = WORK / 'bin'
    output.mkdir(parents=True, exist_ok=True)
    for src in converter.parent.iterdir():
        if src.is_file():
            shutil.copyfile(src, output / src.name)
    runtime = Path(CFG['toolchain']['dotnet_runtime'])
    references = [p for p in runtime.glob('*.dll')
                  if '.Native' not in p.name and (p.name.startswith(('System.', 'Microsoft.'))
                  or p.name in ('netstandard.dll', 'mscorlib.dll'))]
    references += list((SRC / 'LIb').glob('*.dll'))
    references += [converter.with_name('Newtonsoft.Json.dll')]
    args_csc = ['/nologo', '/target:library', '/langversion:10.0', '/nostdlib+', '/optimize+',
                '/out:"' + str(output / 'EffectLibrary.dll') + '"']
    args_csc += ['/reference:"' + str(p) + '"' for p in references]
    for relative, text in sources.items():
        path = WORK / 'src' / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        args_csc.append('"' + str(path) + '"')
    rsp = WORK / 'compile.rsp'
    rsp.write_text('\n'.join(args_csc))
    result = subprocess.run([CFG['toolchain']['roslyn_csc'], '@' + str(rsp)], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    helper = WORK / 'HeroTextureRename.cs'
    helper.write_text(TEXTURE_RENAME_SOURCE)
    helper_rsp = WORK / 'texture_rename.rsp'
    helper_args = ['/nologo', '/target:exe', '/langversion:10.0', '/nostdlib+', '/optimize+',
                   '/out:"' + str(output / 'HeroTextureRename.dll') + '"']
    helper_args += ['/reference:"' + str(p) + '"' for p in references]
    helper_args.append('"' + str(helper) + '"')
    helper_rsp.write_text('\n'.join(helper_args))
    result = subprocess.run([CFG['toolchain']['roslyn_csc'], '@' + str(helper_rsp)], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    shutil.copyfile(output / 'EffectConverter.runtimeconfig.json', output / 'HeroTextureRename.runtimeconfig.json')
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    record = {'date': '2026-09-30', 'tool_version': '1.0.0', 'source_commit': PIN,
              'compiler_sha256': sha(Path(CFG['toolchain']['roslyn_csc'])),
              'effect_library_sha256': sha(output / 'EffectLibrary.dll'),
              'texture_rename_sha256': sha(output / 'HeroTextureRename.dll'),
              'texture_rename_source_sha256': hashlib.sha256(TEXTURE_RENAME_SOURCE.encode()).hexdigest(),
              'patched_sources': {p: hashlib.sha256(t.encode()).hexdigest() for p, t in sources.items()}}
    (WORK / 'MANIFEST.json').write_text(json.dumps(record, indent=2) + '\n')
    print('Built isolated repaired EffectLibrary; framework plugins untouched')


if __name__ == '__main__':
    main()
