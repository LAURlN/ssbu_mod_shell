import sys; sys.path.insert(0,'scratch')
from prcdump import load
def flat(v,p=''):
    if isinstance(v,dict):
        for k,x in v.items(): yield from flat(x,p+'/'+k)
    elif isinstance(v,list):
        for i,x in enumerate(v): yield from flat(x,p+f'[{i}]')
    else: yield p,v
for name in sys.argv[1:]:
    a=dict(flat(load(f'export/fighter/eflame/motion/body/c06/{name}.prc')))
    b=dict(flat(load(f'export/fighter/gamewatch/motion/body/c06/{name}.prc')))
    print('=====',name,'pyra-only keys:',len(a.keys()-b.keys()),'gw-only keys:',len(b.keys()-a.keys()),'differing values:',sum(1 for k in a.keys()&b.keys() if a[k]!=b[k]))
    for k in sorted(a.keys()|b.keys()):
        if a.get(k,'<absent>')!=b.get(k,'<absent>'): print(f'  {k}: pyra={a.get(k,"<absent>")}  gw={b.get(k,"<absent>")}')
