# Jython post-script: decompile every caller of any function named like args[1] (default sv_set_status_func),
# plus hex addresses given as further args ("0x...").
from ghidra.app.decompiler import DecompInterface
args = list(getScriptArgs()); outp = args[0]
name = 'sv_set_status_func'
addrs = [a for a in args[1:] if a.startswith('0x')]
names = [a for a in args[1:] if not a.startswith('0x')] or ([name] if not addrs else [])
di = DecompInterface(); di.openProgram(currentProgram)
fm = currentProgram.getFunctionManager()
targets = []
for f in fm.getFunctions(True):
    if f.getName() in names:
        for r in getReferencesTo(f.getEntryPoint()):
            c = fm.getFunctionContaining(r.getFromAddress())
            if c and c not in targets: targets.append(c)
for a in addrs:
    ad = toAddr(int(a, 16)); f = fm.getFunctionAt(ad)
    if f is None:
        disassemble(ad); f = createFunction(ad, None)
    if f and f not in targets: targets.append(f)
out = open(outp, 'w')
for f in targets:
    r = di.decompileFunction(f, 300, monitor)
    out.write('// ==== %s @ %s\n' % (f.getName(), f.getEntryPoint()))
    out.write((r.getDecompiledFunction().getC() if r.decompileCompleted() else '// FAILED ' + r.getErrorMessage()) + '\n')
out.close()
