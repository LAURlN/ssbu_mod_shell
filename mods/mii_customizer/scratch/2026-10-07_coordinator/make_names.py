"""Coordinator: names.txt (mc_names 1) for plugin 0.5.2, from the user's own msg_name.msbt.
One line per preset of list.txt plus miigunner: <preset> <text of nam_chr1_00_<preset>>.
Game text, so the output stays under gamedata/. Run from the workspace root."""
import hashlib, os, sys
sys.path.insert(0, "mods/mii_customizer/tools/stat-presets")
import msbt

MSG = "gamedata/mii_customizer/P11-ROW-TEXT/ui/message/msg_name.msbt"
LIST = "gamedata/mii_customizer/COORD-session3/list.txt"
OUT = "gamedata/mii_customizer/COORD-session3/names.txt"
labels = msbt.read_labels(MSG)
rows = [l.split() for l in open(LIST, encoding="ascii").read().split("\n")
        if l and not l.startswith("#") and l != "mc_list 1"]
rows.append(["miigunner", "nam_chr1_00_miigunner"])
lines, long_ = ["mc_names 1"], []
for name, label in rows:
    text = labels[label].rstrip("\x00").strip()
    raw = text.encode("utf-8")
    ok = 1 <= len(raw) <= 40 and all(0x20 <= ord(c) <= 0xffff and not 0x7f <= ord(c) < 0xa0 for c in text)
    if not ok:
        long_.append((name, text))
        continue
    lines.append("%s %s" % (name, text))
open(OUT, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
print("lines", len(lines) - 1, "skipped", long_, "bytes", os.path.getsize(OUT),
      hashlib.sha256(open(OUT, "rb").read()).hexdigest())
print(max(lines[1:], key=len))
