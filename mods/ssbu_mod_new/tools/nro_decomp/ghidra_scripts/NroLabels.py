# Jython pre-script: apply labels.json from nro_flatten.py and mark text executable.
import json
from ghidra.program.model.symbol import SourceType
args = getScriptArgs()
j = json.load(open(args[0]))
for a, n in j['labels'].items():
    addr = toAddr(int(a, 16))
    createLabel(addr, n, True, SourceType.IMPORTED)
    if int(a, 16) < j['text_end'] or int(a, 16) >= j['ext_base']:
        disassemble(addr); createFunction(addr, n)
