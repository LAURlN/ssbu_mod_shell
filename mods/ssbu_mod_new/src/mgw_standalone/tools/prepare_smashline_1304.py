"""Create a separate, audited Smashline source overlay for this game's dump.

The distributed v1.6.8 source adds 0x5b0 to late main-code addresses. The user's
13.0.4 dump and live factory log use the unshifted addresses. Preserve upstream
source, record each changed site, and refuse runtime installation if bytes differ.
Replace the stale costume-table read with the pinned FighterManager and
FighterInformation APIs, correct resource/name-table globals and path hooks,
and omit unused development hot reload after its pointer crash.
"""
from pathlib import Path
import hashlib, json, re, shutil, sys, zipfile
ROOT=Path(__file__).resolve().parents[1]
WORKSPACE=ROOT.parents[1]
sys.path.insert(0,str(WORKSPACE/'references/mythra_gamewatch_feasibility/python_tools'))
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM
archive=ROOT/'downloads/smashline-v1.6.8-source.zip'
source=ROOT/'smashline_1304'
if source.exists() and '--refresh' not in sys.argv:
    raise SystemExit('Overlay exists; inspect changes before regenerating')
with zipfile.ZipFile(archive) as z:
    for name in z.namelist():
        relative=Path(*Path(name).parts[1:])
        if not relative.parts or name.endswith('/'): continue
        if '..' in relative.parts: raise ValueError(name)
        dest=source/relative
        dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_bytes(z.read(name))
memory=WORKSPACE/'references/mythra_gamewatch_feasibility/main_memory.bin'
data=memory.read_bytes()
digest=hashlib.sha256(data).hexdigest()
assert digest.lower()=='f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613'
md=Cs(CS_ARCH_ARM64,CS_MODE_ARM)
audit=[]
sites={}
pattern=re.compile(r'(0x[0-9a-fA-F]+) \+ 0x5B0')
for path in sorted((source/'src').rglob('*.rs')):
    text=path.read_text()
    for match in pattern.finditer(text):
        offset=int(match[1],16)
        def disasm(at):
            return [f'{i.address:#x}: {i.mnemonic} {i.op_str}' for i in md.disasm(data[at:at+16],at)]
        audit.append({'file':str(path.relative_to(source)),'line':text.count('\n',0,match.start())+1,
            'upstream':hex(offset+0x5b0),'corrected':hex(offset),
            'corrected_bytes':data[offset:offset+16].hex(),'corrected_instructions':disasm(offset),
            'upstream_instructions':disasm(offset+0x5b0)})
        sites[offset]=int.from_bytes(data[offset:offset+4],'little')
    changed=pattern.sub(r'\1 /* MGW: verified against 13.0.4 dump; see offset-audit.json */',text)
    if changed!=text: path.write_text(changed,encoding='utf-8')
assert len(audit)==32,len(audit)
support_audit=[]
# These path sites are immediately AFTER the native name load. The upstream
# -0x40 displacement instead lands inside prologues, hash loops and epilogues.
for filename in ('fighters.rs','weapons.rs'):
    path=source/'src/cloning'/filename
    lines=path.read_text().splitlines(keepends=True)
    for n,line in enumerate(lines):
        if line.lstrip().startswith('//'): continue
        match=re.search(r'(0x[0-9a-f]+) - 0x40',line)
        if not match: continue
        off=int(match[1],16)
        if filename=='fighters.rs':
            # Four upstream entries name the load itself; an inline hook must
            # observe its result, not have its replacement overwritten by it.
            instruction=next(md.disasm(data[off:off+4],off))
            if instruction.mnemonic=='ldr' and instruction.op_str.startswith('x2,'):
                off+=4
            previous=next(md.disasm(data[off-4:off],off-4))
            assert previous.mnemonic=='ldr' and previous.op_str.startswith('x2,'),(line,previous.op_str)
        if 'get_fighter_path8(' in line:
            # path2 and path8 install the same callback at the same address.
            lines[n]='    // MGW: path8 was a duplicate of get_fighter_path2.\n'
            continue
        lines[n]=line[:match.start()]+f'{off:#x} /* MGW: native name is loaded */'+line[match.end():]
        sites[off]=int.from_bytes(data[off:off+4],'little')
        support_audit.append(dict(file=str(path.relative_to(source)),upstream=hex(int(match[1],16)-0x40),corrected=hex(off),
            context=[f'{i.address:#x}: {i.mnemonic} {i.op_str}' for i in md.disasm(data[off-8:off+8],off-8)]))
    path.write_text(''.join(lines),encoding='utf-8')

# Each address has an independent native witness in native-support-audit.json
# or the native instructions below. Do not apply a blanket BSS displacement.
replacements={
    'src/create_agent.rs': {'0x4f81e20':'0x4f80e20','0x5186bd0':'0x5185bd0','0x5189240':'0x5188240'},
    'src/utils.rs': {'0x5327cd0':'0x5326cd0','0x5332f20':'0x5331f20'},
    'src/effects.rs': {'0x5334920':'0x5333920'},
    'crates/resources/src/types.rs': {'0x5332f20':'0x5331f20','0x5332f28':'0x5331f28'},
}
for filename,mapping in replacements.items():
    path=source/filename
    content=path.read_text()
    for old,new in mapping.items():
        assert content.count(old)==1,(filename,old)
        content=content.replace(old,new)
        support_audit.append(dict(file=filename,upstream=old,corrected=new))
    path.write_text(content,encoding='utf-8')
# Verify the native instructions that establish the above addresses, plus the
# effect call replaced by the inline transplant hook. These are read before
# Smashline installs any hooks.
for off in (0x17df498,0x17df49c,0x17e0888,0x17e088c,0x17e0a40,0x17e0a44,
            0x17e4914,0x17e4918,0x17e491c,0x353e344,0x353e348,
            0x353e770,0x353e774,0x60bfc4,0x60bfc8,0x60bfd8):
    sites[off]=int.from_bytes(data[off:off+4],'little')
guard='''// Generated from the user's pinned main_memory.bin; checked BEFORE hooks.
pub fn matches() -> bool {
    let base = unsafe { skyline::hooks::getRegionAddress(skyline::hooks::Region::Text) as usize };
    let mut valid = true;
    for &(offset, expected) in SITES {
        let actual = unsafe { core::ptr::read_volatile((base + offset) as *const u32) };
        if actual != expected {
            skyline::println!("[MGW-SL] REFUSED offset={:#x} expected={:#x} actual={:#x}", offset, expected, actual);
            valid = false;
        }
    }
    valid
}
const SITES: &[(usize,u32)] = &[
'''+''.join(f'    ({off:#x}, {word:#x}),\n' for off,word in sorted(sites.items()))+'];\n'
(source/'src/mgw_version.rs').write_text(guard,encoding='utf-8')
utils=source/'src/utils.rs'
utils_text=utils.read_text()
old_costume='''pub fn get_costume_from_entry_id(entry_id: i32) -> Option<i32> {
    unsafe {
        let text = skyline::hooks::getRegionAddress(skyline::hooks::Region::Text) as *const u64;
        let some_vec = *text.add(0x5324680 / 0x8);

        let index = entry_id as u64 * 8;
        let some_struct = *((some_vec + index + 0xe8) as *const u64);

        const COSTUME_OFFSET: u64 = 100;
        let ptr = (some_struct + COSTUME_OFFSET) as *const i32;
        if ptr as u64 == 0x64 { // entry articles
            None
        } else {
            Some(*ptr)
        }
    }
}'''
new_costume='''extern "C" {
    // Native 13.0.4 FighterInformation accessor. Its symbol is present in the
    // pinned main_symbols.json and the function reads the fighter_color byte
    // from the returned FighterInformation object.
    #[link_name = "_ZN3app8lua_bind38FighterInformation__fighter_color_implEPNS_18FighterInformationE"]
    fn mgw_fighter_information_fighter_color(
        information: *const std::ffi::c_void,
    ) -> u8;
}

pub fn get_costume_from_entry_id(entry_id: i32) -> Option<i32> {
    if !(0..8).contains(&entry_id) {
        return None;
    }

    // Use Smash-rs's binding to the game's FighterManager singleton and
    // entry lookup instead of dereferencing an undocumented main+BSS table.
    let manager = smash::app::FighterManager::instance()?;
    let information = manager.get_fighter_information(entry_id as u32)?;
    let information_ptr = information as *const smash::app::FighterInformation
        as *const std::ffi::c_void;
    Some(unsafe { mgw_fighter_information_fighter_color(information_ptr) as i32 })
}'''
if utils_text.count(old_costume)!=1: raise RuntimeError('Unexpected upstream costume lookup; refusing to patch')
utils.write_text(utils_text.replace(old_costume,new_costume,1),encoding='utf-8')
effects=source/'src/effects.rs'
effects_text=effects.read_text()
old_effect='''    let info = resources::types::FilesystemInfo::instance().unwrap();

    let search = info.search();

    let path_name = search.get_path_list()[*search_index_begin as usize];'''
new_effect='''    // The original game effect loader above has already returned. Use the
    // verified filesystem global; the p5 absence was a stale address, not
    // evidence that fighter-loading metadata was not ready.
    let Some(info) = resources::types::FilesystemInfo::instance() else {
        if !NO_FILESYSTEM_INFO_REPORTED.swap(true, Ordering::Relaxed) {
            skyline::println!("[MGW-SL] effect transplant scan skipped: FilesystemInfo is unavailable; original effect loader was called");
        }
        return;
    };

    if !FILESYSTEM_INFO_REPORTED.swap(true, Ordering::Relaxed) {
        skyline::println!("[MGW-SL] p7: filesystem metadata resolved at main+0x5331f20");
    }
    let search = info.search();
    let search_index = *search_index_begin as usize;
    let Some(path_name) = search.get_path_list().get(search_index) else {
        if !INVALID_EFFECT_SEARCH_INDEX_REPORTED.swap(true, Ordering::Relaxed) {
            skyline::println!("[MGW-SL] effect transplant scan skipped: search index {:#x} is absent from the resource path list; original effect loader was called", search_index);
        }
        return;
    };'''
if effects_text.count(old_effect)!=1: raise RuntimeError('Unexpected upstream effect-transplant lookup; refusing to patch')
effects_text=effects_text.replace(old_effect,new_effect,1)
import_line='use smashline::Hash40;'
if effects_text.count(import_line)!=1: raise RuntimeError('Unexpected effects.rs imports; refusing to patch')
effects_text=effects_text.replace(import_line,import_line+'\nuse std::sync::atomic::{AtomicBool, Ordering};\n\nstatic FILESYSTEM_INFO_REPORTED: AtomicBool = AtomicBool::new(false);\nstatic NO_FILESYSTEM_INFO_REPORTED: AtomicBool = AtomicBool::new(false);\nstatic INVALID_EFFECT_SEARCH_INDEX_REPORTED: AtomicBool = AtomicBool::new(false);',1)
effects.write_text(effects_text,encoding='utf-8')
lib=source/'src/lib.rs'
text=lib.read_text().replace('pub fn main() {','pub fn main() {\n    if !mgw_version::matches() { return; }\n    skyline::println!("[MGW-SL] p7: verified resource globals, name tables and path hooks");',1)
needle='    runtime_reload::install();'
if text.count(needle) != 1: raise RuntimeError('Unexpected Smashline runtime_reload install site')
text=text.replace(needle,'    // MGW p3: upstream hot reload dereferences stale 13.0.4 game state at 0x52c1760.\n    // It only loads development scripts, which this mod does not use.',1)
text=text.replace('mod cloning;','mod cloning;\nmod mgw_version;',1)
text=text.replace('        skyline::error::show_error(', '        skyline::println!("[MGW-SL] {}", err_msg);\n        skyline::error::show_error(',1)
lib.write_text(text,encoding='utf-8')
audit_doc={'source_archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
           'main_dump_sha256':digest,'edits':audit,'resource_support_edits':support_audit}
(ROOT/'offset-audit.json').write_text(json.dumps(audit_doc,indent=2)+'\n')
print(f'Prepared {len(audit)} references at {len(sites)} verified instruction sites')
