import sys; sys.path.insert(0,'mod_files/pyra_gamewatch_reskin/tools')
import prc
for f in ['export/fighter/gamewatch/param/vl.prc','export/fighter/eflame/param/vl.prc']:
    t=prc.read(f)
    print(f, t[0] if not isinstance(t,tuple) else t[0])
    d=t[1] if isinstance(t,tuple) else t
    try:
        for k,v in (d.items() if hasattr(d,'items') else d):
            print('  ',k, v[0] if isinstance(v,tuple) else type(v))
    except Exception as e: print(e, type(d))
print(hex(prc.hash40('param_normal_weapon')), prc.hash40('param_normal_weapon'))
for n in ['param_normal_weapon','param_bomb','param_breath','param_panel','param_rescue','param_parachute','param_oil','param_judge','param_food','param_octopus','param_esword','param_special_s','param_special_n','param_special_hi','param_special_lw','param_private','param_normalweapon']:
    print(n, prc.hash40(n))
