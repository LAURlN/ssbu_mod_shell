| hash | site | enclosing fn (fstart) | call / vtable | callers of fn |
|---|---|---|---|---|
| 0x0607cd5541 | 0x00595a8c | 0x590a50 | none within completing+0x400 | 0 |
| 0x0607cd5541 | 0x0069d018 | 0x69cf90 | `blr x8` (producer ldr x8, [x8, #0x270] @ 0x69d010) | 1 |
| 0x0607cd5541 | 0x006c6590 | 0x6c5df0 | `blr x8` (producer ldr x8, [x8, #0x270] @ 0x6c65a0) | 0 |
| 0x0607cd5541 | 0x006f5278 | 0x6f37b0 | none within completing+0x400 | 0 |
| 0x0607cd5541 | 0x006f9778 | 0x6f7b20 | none within completing+0x400 | 0 |
| 0x0607cd5541 | 0x00ebeb98 | 0xebeadc | `bl` -> 0x39c0d80 | 0 |
| 0x0607cd5541 | 0x01130030 | 0x112fef4 | none within completing+0x400 | 0 |
[18 lines of game disassembly removed for publication; regenerate them from your own 13.0.4 main with this report's check script]
