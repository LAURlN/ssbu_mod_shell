using System.Security.Cryptography;
using System.Buffers.Binary;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using LibHac;
using LibHac.Common;
using LibHac.Common.Keys;
using LibHac.Fs;
using LibHac.Fs.Fsa;
using LibHac.FsSystem;
using LibHac.Spl;
using LibHac.Tools.Es;
using LibHac.Tools.FsSystem;
using LibHac.Tools.FsSystem.NcaUtils;
using LibHac.Tools.Ncm;
using LContentType = LibHac.Ncm.ContentType;
using MetaType = LibHac.Ncm.ContentMetaType;
using IOPath = System.IO.Path;

// Experimental: source-reviewed only. No profile discovery, network or container staging.
internal static class Program
{
    const ulong BaseTitle = 0x01006A800016E000, PatchTitle = 0x01006A800016E800;
    const string BackendHash = "df35642dd8d43472414a58a45fb7c5c22858764abf114ea09bff7bb08bad5b16";
    const long Headroom = 1L << 30;
    const int BufferSize = 16 << 20;
    const long ProgressInterval = 1L << 30;
    static string Root = "";
    static bool Cancelled;
    static string Stage = "arguments";
    static readonly JsonSerializerOptions Json = new() { WriteIndented = true };
    sealed class SafeError(string message) : Exception(message);
    sealed record Input(string Path, long Bytes, DateTime LastWriteUtc, DateTime CreationUtc);
    sealed record Selection(string Title, uint Version, string Type, string ApplicationTitle,
        string MetaNca, string ProgramNca, long ProgramBytes, string CnmtSha256,
        string ExpectedProgramSha256, string ProgramTitle, int ContentIndex, byte KeyGeneration);

    static int Main(string[] args)
    {
        Console.CancelKeyPress += (_, e) => { e.Cancel = true; Cancelled = true; };
        try { return Run(args); }
        catch (Exception e) { Console.Error.WriteLine(Diagnostic(e)); return Cancelled ? 130 : 1; }
    }
    static string Diagnostic(Exception e)
    {
        if (e is SafeError) return $"{Stage}: {e.Message}";
        if (e is MissingKeyException mk)
        {
            // Only a conservative key NAME is emitted, never backend exception text/values.
            string name = mk.Name ?? "";
            if (!Regex.IsMatch(name, @"\A(?:header_key|master_key_[0-9a-f]{2}|titlekek_[0-9a-f]{2}|key_area_key_[a-z]+_[0-9a-f]{2})\z")) name = "required generation or rights key";
            return $"{Stage}: missing {name}. Re-export your own matching keys to the explicit workspace key paths; personalized tickets need matching title.keys. No fallback occurred.";
        }
        return $"{Stage}: {e.GetType().Name}; backend/input/integrity or disk operation failed. Check pinned setup, key coverage, selected identities, free space and permissions. Raw backend messages are suppressed to protect secrets. No base fallback occurred.";
    }
    static void Require(bool ok, string message) { if (!ok) throw new SafeError(message); }
    static void CheckCancel() { if (Cancelled) throw new SafeError("Interrupted; partial output is incomplete and must not be used."); }
    static void Check(Result result, string action)
    { if (result.IsFailure()) throw new SafeError($"{action}: LibHac result {result}. Stop; check inputs/keys and integrity. No fallback."); }
    static bool Under(string path, string parent) => path.StartsWith(parent.TrimEnd('\\') + "\\", StringComparison.OrdinalIgnoreCase);
    static bool Same(string a, string b) => string.Equals(a, b, StringComparison.OrdinalIgnoreCase);
    static string Resolve(string value, bool derived = false)
    {
        Require(!string.IsNullOrWhiteSpace(value), "Empty path.");
        Require(!value.Split('/', '\\').Contains(".."), "Traversal components are rejected; use a direct workspace path.");
        Require(value.Split('/', '\\').All(p => p.Length == 0 || p == "." || (!p.EndsWith(' ') && !p.EndsWith('.'))),
            "Windows trailing-dot/space path aliases are unsupported.");
        string full = IOPath.GetFullPath(value, Root);
        Require(Under(full, Root), "All paths must be strictly inside the workspace.");
        Require(!full[IOPath.GetPathRoot(full)!.Length..].Contains(':'), "Alternate data streams are unsupported.");
        if (derived) Require(Under(full, IOPath.Combine(Root, "gamedata")), "Every derived output must be under gamedata/.");
        // Reject all existing reparse points, including workspace and drive ancestors.
        for (string? cursor = full; cursor != null; cursor = IOPath.GetDirectoryName(cursor))
        {
            try { Require((File.GetAttributes(cursor) & FileAttributes.ReparsePoint) == 0, "Symlink/junction/reparse-point paths are unsupported."); }
            catch (FileNotFoundException) { }
            catch (DirectoryNotFoundException) { }
        }
        return full;
    }
    static List<string> Parts(string path, bool allowSplit)
    {
        if (!Directory.Exists(path)) { Require(File.Exists(path), $"Missing input: {path}"); return [path]; }
        Require(allowSplit, "Update must be a single NSP file; split updates are unsupported.");
        var entries = Directory.EnumerateFileSystemEntries(path).Take(101).OrderBy(x => x, StringComparer.Ordinal).ToList();
        Require(entries.Count is > 0 and <= 100, "Split base must contain 00 through at most 99.");
        for (int i = 0; i < entries.Count; i++)
        {
            Require(IOPath.GetFileName(entries[i]) == i.ToString("D2"), $"Missing/unexpected split part; expected {i:D2}. Only contiguous two-digit numeric files starting at 00 are supported.");
            entries[i] = Resolve(entries[i]);
            Require(File.Exists(entries[i]) && new FileInfo(entries[i]).Length > 0, $"Empty/non-file split part {i:D2}.");
        }
        return entries;
    }
    static Input Snapshot(string path)
    { var f = new FileInfo(path); return new(path, f.Length, f.LastWriteTimeUtc, f.CreationTimeUtc); }
    static FileStream ReadInput(string path) => new(Resolve(path), FileMode.Open, FileAccess.Read, FileShare.Read, 64 << 10, FileOptions.RandomAccess);
    static UniqueRef<IFile> Open(IFileSystem fs, string path)
    { UniqueRef<IFile> file = default; Check(fs.OpenFile(ref file, new U8Span(path), OpenMode.Read), $"Open {path}"); return file; }
    // UniqueRef<IFile>.Dispose() is an obsolete-error in 0.19.0; Destroy() is the supported release.
    static T WithFile<T>(IFileSystem fs, string path, Func<IFile, T> body)
    { var file = Open(fs, path); try { return body(file.Get); } finally { file.Destroy(); } }
    static byte[] SmallRead(IFile file, int max, string label)
    {
        Check(file.GetSize(out long size), $"Size {label}");
        Require(size is > 0 && size <= max, $"Unsupported {label} metadata size (limit {max} bytes).");
        byte[] data = new byte[(int)size];
        Check(file.Read(out long n, 0, data), $"Read {label}");
        Require(n == size, $"Short {label} metadata read."); return data;
    }

    sealed class Container : IDisposable
    {
        readonly List<FileStream> streams = [];
        readonly List<IStorage> storages = [];
        readonly List<UniqueRef<IFile>> files = [];
        readonly List<IStorage> views = [];
        readonly IStorage root;
        public readonly PartitionFileSystem Pfs = new();
        public readonly List<LibHac.Tools.Fs.DirectoryEntryEx> Entries;
        public Container(List<string> paths)
        {
            try
            {
                long total = 0;
                foreach (string path in paths)
                {
                    var stream = ReadInput(path); streams.Add(stream);
                    Require(stream.Length > 0, "Empty container/part."); total = checked(total + stream.Length);
                    storages.Add(new StreamStorage(stream, true));
                }
                root = new ConcatenationStorage(storages, true);
                ValidatePfs(root, total);
                Check(Pfs.Initialize(root), "Initialize NSP PFS0 (NSZ/XCI and other formats unsupported)");
                Entries = Pfs.EnumerateEntries().Take(4097).ToList();
                Require(Entries.Count is > 0 and <= 4096, "Unsupported NSP entry count (maximum 4096).");
                Require(Entries.All(e => e.Type == DirectoryEntryType.File && !e.Name.Contains('/') && !e.Name.Contains('\\')),
                    "Only flat NSP files are supported.");
                Require(Entries.Select(e => e.Name.ToLowerInvariant()).Distinct().Count() == Entries.Count, "Ambiguous duplicate NSP filenames.");
            }
            catch { Dispose(); throw; }
        }
        static void ValidatePfs(IStorage storage, long total)
        {
            Span<byte> header = stackalloc byte[16]; Check(storage.Read(0, header), "Read PFS0 header");
            Require(header[..4].SequenceEqual("PFS0"u8), "Expected ordinary uncompressed PFS0 NSP; XCI/NSZ unsupported.");
            uint count = BinaryPrimitives.ReadUInt32LittleEndian(header[4..]);
            uint strings = BinaryPrimitives.ReadUInt32LittleEndian(header[8..]);
            Require(count is > 0 and <= 4096, "PFS0 entry count outside supported 1..4096 range.");
            long length = checked(16L + count * 24L + strings);
            Require(length <= 16 << 20 && length <= total, "PFS0 metadata exceeds 16 MiB limit or container bounds.");
            byte[] metadata = new byte[(int)length]; Check(storage.Read(0, metadata), "Read bounded PFS0 metadata");
            for (int i = 0; i < count; i++)
            {
                var entry = metadata.AsSpan(16 + i * 24, 24);
                ulong offset = BinaryPrimitives.ReadUInt64LittleEndian(entry);
                ulong size = BinaryPrimitives.ReadUInt64LittleEndian(entry[8..]);
                uint name = BinaryPrimitives.ReadUInt32LittleEndian(entry[16..]);
                Require(offset <= (ulong)(total - length) && size <= (ulong)(total - length) - offset, "PFS0 entry extends beyond ordered parts; incomplete/corrupt dump.");
                Require(name < strings && metadata.AsSpan(checked((int)(16 + count * 24 + name))).IndexOf((byte)0) >= 0, "PFS0 name outside string table or unterminated.");
            }
        }
        public Nca GetNca(string path, KeySet keys)
        {
            var file = Open(Pfs, path); files.Add(file);
            var storage = file.Get.AsStorage(); views.Add(storage); return new Nca(keys, storage);
        }
        public void Tickets(KeySet keys)
        {
            foreach (var entry in Entries.Where(e => e.Name.EndsWith(".tik", StringComparison.OrdinalIgnoreCase)))
            {
                CheckCancel();
                byte[] bytes = WithFile(Pfs, entry.FullPath, file => SmallRead(file, 64 << 10, "ticket"));
                var ticket = new Ticket(new MemoryStream(bytes, false));
                var rights = new RightsId(ticket.RightsId);
                // A user's external key can satisfy a personalized ticket without device RSA keys.
                if ((int)ticket.TitleKeyType != 0 && keys.ExternalKeySet.Contains(rights)) continue;
                byte[]? value = ticket.GetTitleKey(keys);
                if (value == null) { Require(keys.ExternalKeySet.Contains(rights), "Personalized ticket cannot be unwrapped; supply your own matching external title.keys."); continue; }
                Require(value.Length == 16, "Unsupported ticket title-key length.");
                AddKey(keys, rights, new AccessKey(value));
                CryptographicOperations.ZeroMemory(value); CryptographicOperations.ZeroMemory(bytes);
            }
        }
        public (Nca Program, Selection Identity) Select(KeySet keys, bool update)
        {
            var metadata = new List<(Cnmt Cnmt, string MetaName, string Hash)>();
            foreach (var entry in Entries.Where(e => e.Name.EndsWith(".nca", StringComparison.OrdinalIgnoreCase)))
            {
                CheckCancel(); var nca = GetNca(entry.FullPath, keys);
                if (nca.Header.ContentType != NcaContentType.Meta) continue;
                using var fs = nca.OpenFileSystem(NcaSectionType.Data, IntegrityCheckLevel.ErrorOnInvalid);
                var cnmtEntries = fs.EnumerateEntries().Take(65).ToList();
                Require(cnmtEntries.Count <= 64, "Too many Meta filesystem entries.");
                foreach (var cnmtEntry in cnmtEntries)
                {
                    Require(metadata.Count < 64, "Too many CNMT records.");
                    if (!cnmtEntry.Name.EndsWith(".cnmt", StringComparison.OrdinalIgnoreCase)) continue;
                    var data = WithFile(fs, cnmtEntry.FullPath, file => SmallRead(file, 16 << 20, "CNMT"));
                    var cnmt = new Cnmt(new MemoryStream(data, false));
                    Require(nca.Header.TitleId == cnmt.TitleId, "Meta NCA header/CNMT title mismatch.");
                    metadata.Add((cnmt, entry.Name, Convert.ToHexString(SHA256.HashData(data)).ToLowerInvariant()));
                }
            }
            ulong title = update ? PatchTitle : BaseTitle;
            MetaType type = update ? MetaType.Patch : MetaType.Application;
            uint version = update ? 1966080u : 0u;
            Require(metadata.Count == 1, "Expected exactly one application/patch CNMT; missing, DLC-only or multi-title/ambiguous NSP. Supply the base/update package separately.");
            var selected = metadata[0]; var m = selected.Cnmt;
            Require(m.TitleId == title && m.Type == type, $"Mismatched/DLC content: expected {type} title {title:X16}, found {m.Type} {m.TitleId:X16}.");
            Require(m.TitleVersion.Version == version, $"Unsupported CNMT version {m.TitleVersion.Version}; supported {(update ? "13.0.4 patch 1966080" : "base version 0")} only. Filename labels are not evidence.");
            if (update) Require(m.ApplicationTitleId == BaseTitle, "Patch CNMT does not link to SSBU base application.");
            var programs = new List<(Nca Nca, CnmtContentEntry Entry, string Name)>();
            foreach (var content in m.ContentEntries.Where(e => e.Type == LContentType.Program))
            {
                string id = Convert.ToHexString(content.NcaId).ToLowerInvariant();
                var entry = Entries.SingleOrDefault(e => string.Equals(e.Name, id + ".nca", StringComparison.OrdinalIgnoreCase));
                Require(entry != null, $"Missing CNMT-referenced Program NCA {id}; re-export a complete package.");
                Require(entry!.Size == content.Size, $"CNMT Program size mismatch for {id}.");
                var nca = GetNca(entry.FullPath, keys);
                Require(nca.Header.ContentType == NcaContentType.Program && nca.Header.TitleId == BaseTitle && nca.Header.NcaSize == content.Size,
                    $"Referenced NCA {id} is not matching SSBU Program content.");
                if (nca.Header.ContentIndex == 0 && nca.SectionExists(NcaSectionType.Data)) programs.Add((nca, content, id));
            }
            Require(programs.Count == 1, "Expected one unambiguous SSBU Program #0 with a Data section; missing/unsupported content.");
            var p = programs[0];
            return (p.Nca, new(m.TitleId.ToString("X16"), m.TitleVersion.Version, m.Type.ToString(), m.ApplicationTitleId.ToString("X16"),
                selected.MetaName, p.Name, p.Entry.Size, selected.Hash, Convert.ToHexString(p.Entry.Hash).ToLowerInvariant(),
                p.Nca.Header.TitleId.ToString("X16"), p.Nca.Header.ContentIndex, p.Nca.Header.KeyGeneration));
        }
        public void Dispose()
        {
            // Reverse lifetime order: file storage views, then file references, then the
            // partition filesystem that created them, then parts and their read-only streams.
            foreach (var v in views.AsEnumerable().Reverse()) v.Dispose();
            foreach (var f in files.AsEnumerable().Reverse()) f.Destroy();
            Pfs.Dispose(); root?.Dispose();
            foreach (var s in storages.AsEnumerable().Reverse()) s.Dispose();
            foreach (var s in streams.AsEnumerable().Reverse()) s.Dispose();
        }
    }
    static void AddKey(KeySet keys, RightsId id, AccessKey key)
    {
        if (keys.ExternalKeySet.Contains(id))
        { Check(keys.ExternalKeySet.Get(id, out var old), "Read existing rights key"); Require(old == key, "Conflicting external/ticket rights keys. Re-export consistent keys and packages."); }
        else Check(keys.ExternalKeySet.Add(id, key), "Register rights key");
    }
    static void TitleKeys(KeySet keys, FileStream stream)
    {
        Require(stream.Length <= 1 << 20, "External title.keys larger than supported 1 MiB.");
        using var reader = new StreamReader(stream, Encoding.UTF8, true, 4096, true);
        string? line;
        while ((line = reader.ReadLine()) != null)
        {
            line = line.Split('#')[0].Trim(); if (line.Length == 0) continue;
            var match = Regex.Match(line, @"\A([0-9a-fA-F]{32})\s*=\s*([0-9a-fA-F]{32})\z");
            Require(match.Success, "Malformed title.keys; expected rights-id = encrypted title key, without printing values.");
            byte[] value = Convert.FromHexString(match.Groups[2].Value);
            AddKey(keys, new RightsId(Convert.FromHexString(match.Groups[1].Value)), new AccessKey(value));
            CryptographicOperations.ZeroMemory(value);
        }
    }

    static int Run(string[] args)
    {
        Require(args.Length > 0 && new[] { "discover", "preflight", "extract" }.Contains(args[0]),
            "Usage: DataArcExtract <discover|preflight|extract> --workspace PATH --base PATH (--base-only | --update PATH) --prod-keys PATH [--title-keys PATH] --backend PATH --output gamedata/.../data.arc");
        string mode = args[0]; var opts = new Dictionary<string, string>(); bool baseOnly = false;
        var allowed = new[] { "--workspace", "--base", "--update", "--prod-keys", "--title-keys", "--backend", "--output" };
        for (int i = 1; i < args.Length; i++)
        {
            if (args[i] == "--base-only") { Require(!baseOnly, "Duplicate --base-only."); baseOnly = true; continue; }
            Require(allowed.Contains(args[i]) && i + 1 < args.Length, "Unknown option or missing value.");
            string option = args[i++]; Require(opts.TryAdd(option, args[i]), "Duplicate option.");
        }
        string Need(string key) { Require(opts.ContainsKey(key), $"Required {key}."); return opts[key]; }
        Root = IOPath.GetFullPath(Need("--workspace")).TrimEnd('\\');
        string? anchor = AppContext.BaseDirectory;
        while (anchor != null && !File.Exists(IOPath.Combine(anchor, "tools", "data-arc-extract", "backend.lock.json"))) anchor = IOPath.GetDirectoryName(anchor.TrimEnd('\\'));
        Require(anchor != null && Same(Root, IOPath.GetFullPath(anchor).TrimEnd('\\')), "--workspace must match this executable's lab workspace; relocated executables are unsupported.");
        Require(Directory.Exists(Root) && File.Exists(IOPath.Combine(Root, "AGENTS.md")) && File.Exists(IOPath.Combine(Root, "tools", "data-arc-extract", "backend.lock.json")), "Workspace root must be the existing lab root.");
        Require(baseOnly != opts.ContainsKey("--update"), "Choose exactly one: --base-only OR explicit --update. Updates never fall back to base.");
        string basePath = Resolve(Need("--base")), output = Resolve(Need("--output"), true);
        string backend = Resolve(Need("--backend")), prod = Resolve(Need("--prod-keys"));
        string? title = opts.TryGetValue("--title-keys", out var t) ? Resolve(t) : null;
        string? update = baseOnly ? null : Resolve(Need("--update"));
        var baseParts = Parts(basePath, true); var updateParts = update == null ? null : Parts(update, false);
        var paths = baseParts.Concat(updateParts ?? []).Concat(new[] { backend, prod }).Concat(title == null ? [] : new[] { title }).ToList();
        Require(paths.Distinct(StringComparer.OrdinalIgnoreCase).Count() == paths.Count, "Base/update/backend/key inputs must be distinct.");
        foreach (string input in paths) Require(File.Exists(input), $"Missing prerequisite: {input}; see README recovery.");
        var derived = new[] { output, output + ".partial", output + ".provenance.json", output + ".provenance.json.partial" };
        foreach (string destination in derived)
        {
            Resolve(destination, true);
            Require(!File.Exists(destination) && !Directory.Exists(destination), $"Existing output/partial/report protected: {destination}. Inspect it and choose a fresh destination; no overwrite/resume.");
            foreach (string input in paths.Concat(new[] { basePath }))
                Require(!Same(destination, input) && !Under(destination, input) && !Under(input, destination), "Input/output overlap rejected.");
        }
        Stage = "backend pin";
        using var backendStream = ReadInput(backend);
        Require(Convert.ToHexString(SHA256.HashData(backendStream)).ToLowerInvariant() == BackendHash, "Backend hash mismatch; run pinned setup. Do not change the pin.");
        // .NET resolves the adjacent copy, so pin that actual loaded dependency too.
        string loaded = Resolve(typeof(Nca).Assembly.Location);
        using var loadedStream = ReadInput(loaded);
        Require(Convert.ToHexString(SHA256.HashData(loadedStream)).ToLowerInvariant() == BackendHash && typeof(Nca).Assembly.GetName().Version!.ToString() == "0.19.0.0", "Loaded backend differs from pinned LibHac 0.19.0.");
        var snapshots = paths.Select(Snapshot).ToList();
        long baseBytes = baseParts.Aggregate(0L, (sum, p) => checked(sum + new FileInfo(p).Length));
        Require(baseBytes > 0, "Empty base container.");
        Console.WriteLine(JsonSerializer.Serialize(new { mode, baseOnly, baseParts, baseBytes, update, prodKeys = prod, titleKeys = title,
            backend, loadedBackend = loaded, backendVersion = "0.19.0", backendSha256 = BackendHash, output,
            destination = "gamedata only", prerequisitesAvailable = true, inputs = snapshots, stagingBytes = 0 }, Json));
        if (mode == "discover") return 0;
        Stage = "explicit keys";
        using var prodLock = ReadInput(prod); using var titleLock = title == null ? null : ReadInput(title);
        Require(prodLock.Length <= 1 << 20, "Common keys larger than supported 1 MiB.");
        var keys = KeySet.CreateDefaultKeySet();
        ExternalKeyReader.ReadKeyFile(keys, prod, null, null, null);
        if (titleLock != null) TitleKeys(keys, titleLock);
        Stage = "NSP tickets and CNMT selection";
        using var b = new Container(baseParts); using var u = updateParts == null ? null : new Container(updateParts);
        b.Tickets(keys); u?.Tickets(keys);
        var baseProgram = b.Select(keys, false); var patch = u?.Select(keys, true);
        Stage = "effective RomFS mount";
        using var romfs = patch == null
            ? baseProgram.Program.OpenFileSystem(NcaSectionType.Data, IntegrityCheckLevel.ErrorOnInvalid)
            : baseProgram.Program.OpenFileSystemWithPatch(patch.Value.Program, NcaSectionType.Data, IntegrityCheckLevel.ErrorOnInvalid);
        var arc = Open(romfs, "/data.arc");
        long expected;
        try { Check(arc.Get.GetSize(out expected), "Effective data.arc size"); } catch { arc.Destroy(); throw; }
        Require(expected > 0, "Effective data.arc is empty.");
        long free = new DriveInfo(IOPath.GetPathRoot(output)!).AvailableFreeSpace;
        long required = checked(expected + Headroom);
        var plan = new { selection = baseOnly ? "base-only" : "patched", selectedVersion = baseOnly ? "base CNMT v0" : "13.0.4 / CNMT 1966080",
            baseIdentity = baseProgram.Identity, updateIdentity = patch?.Identity, expectedBytes = expected,
            requiredFreeBytes = required, availableFreeBytes = free, headroomBytes = Headroom,
            temporaryContainerBytes = 0, bufferBytes = BufferSize, output, backendVersion = "0.19.0", backendSha256 = BackendHash,
            inputs = snapshots, programHashVerification = "CNMT expected hashes recorded; whole NCA hashes not computed; mounted reads use ErrorOnInvalid",
            verification = "Archive readability/version correctness await user confirmation" };
        Console.WriteLine(JsonSerializer.Serialize(plan, Json));
        Require(free >= required, "Insufficient space; need effective archive bytes plus 1 GiB headroom. No join/staging is used.");
        Require(paths.Select(Snapshot).SequenceEqual(snapshots), "Input size/timestamps changed during preflight; stop and inspect originals.");
        if (mode == "preflight") { arc.Destroy(); return 0; }
        try { Extract(arc.Get, expected, output, paths, snapshots, plan); }
        finally { arc.Destroy(); } // only after derived filesystems are finished with the file reference
        return 0;
    }

    static void Extract(IFile arc, long expected, string output, List<string> paths, List<Input> snapshots, object plan)
    {
        Stage = "streaming data.arc"; CheckCancel();
            string partial = output + ".partial", report = output + ".provenance.json", journal = report + ".partial";
        Directory.CreateDirectory(Resolve(IOPath.GetDirectoryName(output)!, true));
        bool moved = false, ownJournal = false; long written = 0; string? hash = null;
        FileStream? log = null;
        void Record(string state, string? error = null)
        {
            if (log == null) return;
            byte[] data = JsonSerializer.SerializeToUtf8Bytes(new { state, utc = DateTime.UtcNow, plan, expectedBytes = expected,
                outputBytes = written, sha256 = hash, error, complete = state == "complete", originalMetadataUnchanged = paths.Select(Snapshot).SequenceEqual(snapshots) }, Json);
            log.Position = 0; log.Write(data); log.SetLength(data.Length); log.Flush(true);
        }
        try
        {
            Resolve(journal, true); log = new FileStream(journal, FileMode.CreateNew, FileAccess.Write, FileShare.Read); ownJournal = true;
            Record("in-progress"); Resolve(partial, true);
            using (var destination = new FileStream(partial, FileMode.CreateNew, FileAccess.Write, FileShare.None, 64 << 10, FileOptions.SequentialScan))
            using (var sha = IncrementalHash.CreateHash(HashAlgorithmName.SHA256))
            {
                byte[] buffer = new byte[BufferSize];
                long sinceReport = 0;
                while (written < expected)
                {
                    CheckCancel(); int count = (int)Math.Min(buffer.Length, expected - written);
                    Check(arc.Read(out long n, written, buffer.AsSpan(0, count)), "Read effective data.arc");
                    Require(n == count, "Backend short read; partial retained. No final output.");
                    Resolve(partial, true); destination.Write(buffer, 0, count); sha.AppendData(buffer, 0, count); written += count;
                    // Periodic progress: a hard kill must still leave an accurate journal on disk.
                    sinceReport += count;
                    if (sinceReport >= ProgressInterval) { destination.Flush(false); Record("in-progress"); sinceReport = 0; }
                }
                Check(arc.GetSize(out long after), "Final backend size"); Require(after == expected && destination.Length == expected, "Backend/output byte-count changed.");
                destination.Flush(true); hash = Convert.ToHexString(sha.GetHashAndReset()).ToLowerInvariant();
            }
            Require(paths.Select(Snapshot).SequenceEqual(snapshots), "Original input size/timestamps changed; refuse finalization.");
            Require(new FileInfo(partial).Length == expected, "Partial length differs from the backend-reported size; refuse finalization.");
            CheckCancel(); Record("ready-to-finalize");
            Resolve(output, true); Resolve(partial, true); File.Move(partial, output, false); moved = true;
            Record("complete"); log.Dispose(); log = null;
            Resolve(journal, true); Resolve(report, true); File.Move(journal, report, false);
            moved = false; ownJournal = false; // Archive + final sidecar committed; console failure must not roll back only one.
            try { Console.WriteLine($"COMPLETE: {written} bytes; SHA-256 {hash}; provenance {report}. Readability/version correctness still await user confirmation."); }
            catch (IOException) { /* The final sidecar is the durable completion record. */ }
        }
        catch (Exception e)
        {
            if (moved)
            {
                try { Resolve(output, true); Resolve(partial, true); File.Move(output, partial, false); moved = false; }
                catch { Console.Error.WriteLine("Finalization failed; archive may remain at final path with incomplete provenance. It is NOT a successful extraction; inspect both paths."); }
            }
            if (ownJournal)
            {
                try
                {
                    if (log == null) { Resolve(journal, true); log = new FileStream(journal, FileMode.Open, FileAccess.Write, FileShare.Read); }
                    Record(Cancelled ? "interrupted" : "failed", Diagnostic(e));
                }
                catch { Console.Error.WriteLine("Failure journal could not be updated (for example full disk); .partial/in-progress state must be treated as incomplete."); }
            }
            throw;
        }
        finally { log?.Dispose(); }
    }
}
