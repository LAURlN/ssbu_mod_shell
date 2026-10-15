# Session 3, boot 1 - plugin 0.5.0-menu - 2026-10-07 (tier A)

User report: "I couldn't enter the custom menu; whenever I would enter it, it looks like
it's trying to open it, but it just sends me back to the Mii editor menu."

Log: `log_boot1.txt` (282 lines, sha256 `8acf5f20...`, two boots in the file).

- Files loaded: menu 24 entries, list 86 rows (`entries=86|menu=24` in the `sites` line).
- **No UI hook was installed**: `UI|sites|ui=off|ui_off_file=0|sites_ok=6/6|probes_ok=47/48|installed=0`
  on both boots. The failing probe is the entry of the UTF-8 text setter:
  `ui_probe=0x37a22f0|expected=f81d0ffc,a9014ff4,a9027bfd,910083fd|found=58000051,d61f0220,<addr lo>,<addr hi>|match=0`.
  `58000051 d61f0220` = `ldr x17, #8 ; br x17`: another plugin's inline hook sits on that
  function entry (the 64-bit target differs between the two boots).
- The all-or-nothing rule therefore worked as designed. What the user saw is the plain edit
  script publishing exit value 7 without a plugin to rewrite it: state 11, which returns
  to the edit menu (P9-EDIT-DISPATCH: benign). That part is new tier A: **value 7 without
  the hook is harmless, and the plain (non-marker) edit script loads.**
- Nothing of the menu pages ran. `loadouts.txt` unchanged (`loadouts_after.txt`).

Not identified: which plugin hooks `0x37a22f0`. A byte search for the offset in the seven
plugin NROs on the card finds it only in this mod's. 0.4.0 did not probe that address, so
whether the hook was there in session 2 is unknown.

Fix: plugin 0.5.1 (`builds/0.5.1-menu/`, `9cdcbd67...`) accepts exactly that hook stub at
that one entry, which this plugin only calls; the game's own callers go through the same
hook. Installed 2026-10-07. D: that calling the setter through the foreign hook behaves
like the game's own calls.
