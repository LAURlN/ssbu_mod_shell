//! Loads independent NRO images/BSS with nn::ro and retains them for the process.
//! Factory addresses are withheld until every fighter-specific import is bound
//! to an explicitly owned executable range. There is no original-function fallback.
use skyline::{libc, nn};
use nn::ro;
use std::{mem, ptr};

pub struct ImportSpec {
    pub name: &'static [u8],
    pub offsets: &'static [(usize, i64)],
}

pub struct ModuleSpec {
    pub name: &'static str,
    pub path: &'static str,
    pub sha256: [u8; 32],
    pub size: usize,
    pub text_size: usize,
    pub data_start: usize,
    pub data_size: usize,
    pub required_imports: &'static [&'static [u8]],
    pub exports: &'static [&'static [u8]],
    pub imports: &'static [ImportSpec],
}

struct Aligned(*mut u8);

impl Aligned {
    unsafe fn new(size: usize) -> Result<Self, String> {
        let size = size.max(0x1000).checked_add(0xfff).ok_or("allocation overflow")? & !0xfff;
        let value = libc::memalign(0x1000, size) as *mut u8;
        if value.is_null() { return Err("allocation failed".into()); }
        ptr::write_bytes(value, 0, size);
        Ok(Self(value))
    }
    fn retain(self) -> *mut u8 {
        let value = self.0;
        mem::forget(self);
        value
    }
}

impl Drop for Aligned {
    fn drop(&mut self) { unsafe { libc::free(self.0.cast()); } }
}

pub struct LoadedModule {
    spec: &'static ModuleSpec,
    // nn::ro keeps pointers into these structures; stable heap addresses matter.
    _module: &'static ro::Module,
    _registration: &'static ro::RegistrationInfo,
    _source: usize,
    _bss: usize,
    _nrr: usize,
    base: usize,
    factories: Vec<usize>,
    isolated: bool,
}

// All mutation is performed under the module-set mutex. nn::ro objects and their
// backing allocations stay resident and are never moved or unloaded in-game.
unsafe impl Send for LoadedModule {}

fn check(result: u32, operation: &str) -> Result<(), String> {
    if result == 0 { Ok(()) } else { Err(format!("{} returned {:#x}", operation, result)) }
}

impl LoadedModule {
    pub unsafe fn missing_import(spec: &ModuleSpec) -> Option<&'static [u8]> {
        for name in spec.required_imports {
            let mut address = 0usize;
            if ro::LookupSymbol(&mut address, name.as_ptr()) != 0 || address == 0 {
                return Some(name);
            }
        }
        None
    }

    pub fn describe(&self) -> String {
        format!("{} base={:#x} private_factories={} private_bss={:#x}",
                self.spec.name, self.base, self.factories.len(), self._bss)
    }

    pub unsafe fn load(spec: &'static ModuleSpec) -> Result<Self, String> {
        let bytes = std::fs::read(spec.path).map_err(|e| format!("{}: {}", spec.path, e))?;
        if bytes.len() != spec.size || bytes.get(0x10..0x14) != Some(b"NRO0") {
            return Err("module size/header does not match generated manifest".into());
        }
        let mut hash = [0u8; 32];
        nn::crypto::GenerateSha256Hash(hash.as_mut_ptr().cast(), 32, bytes.as_ptr().cast(), bytes.len() as u64);
        if hash != spec.sha256 { return Err("module SHA-256 mismatch; regenerate the manifest after edits".into()); }
        let image = Aligned::new(bytes.len())?;
        ptr::copy_nonoverlapping(bytes.as_ptr(), image.0, bytes.len());
        let mut bss_size = 0u64;
        check(ro::GetBufferSize(&mut bss_size, image.0), "GetBufferSize")?;
        let bss = Aligned::new(bss_size as usize)?;
        let nrr_size = (mem::size_of::<ro::NrrHeader>() + 32 + 0xfff) & !0xfff;
        let nrr = Aligned::new(nrr_size)?;
        let header = &mut *nrr.0.cast::<ro::NrrHeader>();
        header.magic = 0x3052524e;
        header.program_id = ro::ProgramId { value: skyline::info::get_program_id() };
        header.size = nrr_size as u32;
        header.type_ = 0;
        header.hashes_offset = mem::size_of::<ro::NrrHeader>() as u32;
        header.num_hashes = 1;
        ptr::copy_nonoverlapping(hash.as_ptr(), nrr.0.add(header.hashes_offset as usize), 32);
        let mut registration: Box<ro::RegistrationInfo> = Box::new(mem::zeroed());
        check(ro::RegisterModuleInfo(&mut *registration, nrr.0), "RegisterModuleInfo")?;
        let mut module: Box<ro::Module> = Box::new(mem::zeroed());
        let result = ro::LoadModule(&mut *module, image.0, bss.0, bss_size, ro::BindFlag_BindFlag_Now as i32);
        if result != 0 {
            // Keep registration storage alive if the OS refuses to release it.
            if ro::UnregisterModuleInfo(&mut *registration) != 0 {
                Box::leak(registration);
                nrr.retain();
            }
            return Err(format!("LoadModule returned {:#x}", result));
        }
        // A successful load owns executable state. Retain it even if a later
        // validation refuses gameplay; do not free a still-registered image.
        let module = Box::leak(module);
        let registration = Box::leak(registration);
        let source = image.retain() as usize;
        let bss = bss.retain() as usize;
        let nrr = nrr.retain() as usize;
        if module.ModuleObject.is_null() { return Err("loaded module has no ModuleObject".into()); }
        let base = (*module.ModuleObject).module_base as usize;
        if base == 0 { return Err("loaded module has no mapped base".into()); }
        let mut factories = Vec::new();
        for name in spec.exports {
            let mut address = 0usize;
            check(ro::LookupModuleSymbol(&mut address, module, name.as_ptr()), "LookupModuleSymbol")?;
            if !(base + 0x80..base + spec.text_size).contains(&address) {
                return Err("factory does not point into the private executable image".into());
            }
            factories.push(address);
        }
        for import in spec.imports {
            let mut original = 0usize;
            check(ro::LookupSymbol(&mut original, import.name.as_ptr()), "LookupSymbol")?;
            if original == 0 { return Err("native import resolved to null".into()); }
            for &(offset, addend) in import.offsets {
                if offset % 8 != 0 || offset < spec.data_start || offset + 8 > spec.data_start + spec.data_size {
                    return Err("native import slot lies outside writable module data".into());
                }
                if ptr::read_volatile((base + offset) as *const usize) != original.wrapping_add(addend as usize) {
                    return Err("native import slot differs from the expected resolved symbol".into());
                }
            }
        }
        Ok(Self { spec, _module: module, _registration: registration, _source: source,
                  _bss: bss, _nrr: nrr, base, factories, isolated: false })
    }

    /// `owned_code` must list successfully mapped private native-code allocations,
    /// not original game/plugin ranges. Resolve all bindings before changing any.
    pub unsafe fn bind_character_imports(
        &mut self,
        owned_code: &[std::ops::Range<usize>],
        resolver: impl Fn(&[u8]) -> Option<usize>,
    ) -> Result<(), String> {
        let mut replacements = Vec::new();
        for import in self.spec.imports {
            let address = resolver(import.name).ok_or("missing private character implementation")?;
            if address % 4 != 0 || !owned_code.iter().any(|range| range.contains(&address)) {
                return Err("character import is not inside owned executable memory".into());
            }
            let mut original = 0usize;
            check(ro::LookupSymbol(&mut original, import.name.as_ptr()), "LookupSymbol")?;
            if address == original { return Err("refusing an original character function".into()); }
            for &(offset, addend) in import.offsets {
                replacements.push((self.base + offset, address.wrapping_add(addend as usize)));
            }
        }
        for &(slot, address) in &replacements { ptr::write_volatile(slot as *mut usize, address); }
        if replacements.iter().any(|&(slot, address)| ptr::read_volatile(slot as *const usize) != address) {
            return Err("private import writeback mismatch".into());
        }
        self.isolated = true;
        Ok(())
    }

    pub fn factory(&self, index: usize) -> Result<usize, &'static str> {
        if !self.isolated { return Err("character-specific native imports are not isolated"); }
        self.factories.get(index).copied().ok_or("factory index out of range")
    }
}
