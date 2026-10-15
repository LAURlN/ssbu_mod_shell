"""Pin the reviewed cargo state/dependency ownership contract, offline only.

Usage: python -B src/pgwr/tools/dk_cargo/ownership.py
The contract separates shared engine interfaces from donor-specific storage and
code. It is a port specification, not evidence that an attached victim releases.
"""
import json
from audit import OUT, ROOT, sha, write
from emit_callbacks import ROLES, ADAPTERS

def run():
    graph=json.loads((OUT/'callback_closure.json').read_text())
    assert len(graph['images']['donkey']['functions'])==71
    assert len(graph['images']['common']['functions'])==48
    assert all(not f['indirect_calls'] for v in graph['images'].values() for f in v['functions'])
    assert {r['status'].removeprefix('FIGHTER_DONKEY_STATUS_KIND_') for r in graph['roles']}==set(ROLES)
    states={
      'SHOULDER_START': 'Init sends shoulder on the existing capture link; pickup throw_f sets owned ready flag at 16. Main handles directional throw/jump/walk/turn and situation fall. No set_catch or link construction.',
      'SHOULDER_WAIT': 'Finish pickup before shoulder_wait; directional input, jump, pass, turn and walk follow native priority.',
      'SHOULDER_WALK': 'Enable common LIGHT_WEIGHT, owned walk init/exec helpers and constructor 1.1 walk modifiers; disable at End.',
      'SHOULDER_TURN': 'Own shoulder_turn; common turn timer and one reverse_lr when it expires; ground wait or air fall.',
      'SHOULDER_JUMP_SQUAT': 'Own squat; native mini-jump reserve flag and shared substatus; jump/end/air/throw conditions.',
      'SHOULDER_JUMP_SQUAT_B': 'Button squat follows the same owned shared callbacks with backward/mini input preserved.',
      'SHOULDER_JUMP': 'Own jump; directional cargo throw or fall on end; no added aerial double jump.',
      'SHOULDER_FALL': 'Finish pickup if necessary before owned fall; directional throw or grounded landing.',
      'SHOULDER_LANDING': 'Own landing; air fall or grounded wait on end.',
      'SHOULDER_PASS': 'Reset flick Y; pass floor; set AIR and correct AIR; shift to owned fall loop.',
      'SHOULDER_END': 'Interruption terminal requested by approved +0x210 extension; native wait/fall terminal logic.',
      'THROW_F_F': 'Shared throw Init sends shoulder_throw with owned victim motion and common target work IDs; one ACMD absolute release.',
      'THROW_F_B': 'Shared throw Init/Main/Exit; preserve backward donor timing, facing and one absolute release.',
      'THROW_F_HI': 'Shared throw Init/Main/Exit; preserve high donor timing and one absolute release.',
      'THROW_F_LW': 'Shared throw Init/Exit; special Main clears STOP flag and uses the measured private stop value zero before absolute release.',
    }
    cleanup={'movement_exit':'Retain the capture while next is cargo movement; prepare directional catch-wait motion and clear ignore-cut for cargo throw; otherwise native catch_cut(false,false) and clear ignore-cut.',
       'throw_exit':'Native catch_cut(false,false); release timing is ACMD, not clip end.',
       'check_damage':'Own native damage classifier, captured node identity, common reaction thresholds and 90-degree held-item drop; no opponent-distance approximation.',
       'escape':'Victim clatter expiry sends 0x21ba53a92c; approved captor +0x170 extension requests common CATCH_CUT only for START..PASS. Capture-cut event disables send-cut-event before requesting CATCH_CUT.',
       'reset':'Approved +0x210 extension requests own END only for START..PASS, after preserving Fire and Monkey Flip handlers.',
       'storage':'One donor-only START ready flag becomes object-owned plugin storage. Common turn/jump/throw/capture work is used by its named generic interface. No DK instance work is accessed.'}
    victims={'START':'Stock named ShoulderedDonkeyStart Pre bridges only an active owned captor to owned START. Own Pre/Init/Main/End: damage*1.5+50+existing clatter; start_clatter(total,0,10,-1,0,false,false); false parent color blend; body-variant pickup; end to own CARRY or invalid-capture cleanup.',
      'CARRY':'Own common shoulder callbacks: body variants, LR rotation, clatter and decrement/recovery, camera and constraints; expiry event; End/Exit invalid-capture/LR/camera/MSC cleanup as native.',
      'THROWN':'Stock named ShoulderedDonkeyThrown Pre bridges active owned captor. Own throw-work motion with body variant; translate/rotation flags, per-kind/direction offset and victim flip/scale. Generic Capture check_damage_thrown remains an engine interface. MSC_THROWN_CUT on Exit; no guessed clip-end release.'}
    native={'motion_sharing':'LinkModule parent/transactor route and Motion flag bit 3, independently measured vtables. Captor owns all shared template nodes. Pickel bit 0x1000 retains local overlay metadata/resources. No optional raw +0x190 delegate is written.',
       'constructor':'DK constructor installs walk_speed_max/walk_accel_mul/walk_accel_add modifier records with factor 1.1. Own walk-helper parameter adapters replace this dependency; no DK constructor or class function executes on eflame.',
       'unrelated_class_callbacks':'DK native +0x20 uses private ground/body value 13; +0x38/+0x50 neutral/article flags; +0x120/+0x148 tests ordinary/heavy throw states outside the cargo directional roles. These are outside the cargo callback graph, not called by the port.',
       'shared_engine_boundary':'Named generic L2CValue, FighterBase/Common, Work/Motion/Kinetic/Link/Catch/Capture/Control/Camera/Hit/Status interfaces remain engine dependencies. The existing capture link supplies routing. No framework binary is changed.',
       'host_physics':'Generic motion/jump/fall kinetics run on the recipient body and its existing physics bridge. Cargo-specific walk modifiers, statuses, clips, common decision parameters and victim offsets are owned. This preserves the host body physics rather than replacing its entire fighter stat table.'}
    pins={n:sha((OUT/n).read_bytes()) for n in ['callback_closure.json','status_table.json','victim_registration.json','parameter_contract.json','native_pose_route.json','victim_roster_motion_matrix.json','native_authorization.json','public_sources.json']}
    write('ownership_contract.json',{'tier':'B for pinned binary graph; C for public ACMD; D for runtime outcomes',
       'runtime_verified':False,'state_graph_reviewed':True,'state_roles':states,'cleanup':cleanup,
       'victims':victims,'native_dependencies':native,'adapter_ownership':ADAPTERS,'pins':pins,
       'registration_contract':'Exact 18 native victim registrations use owned binder callbacks. Wildcard status scripts have both costume groups; ACMD is registered per concrete victim fighter hash, filtered groups only for existing eflame/elight custom slots.',
       'status_id_requirement':{'attacker':15,'victim_per_eligible_table':3,'eflame_total':18,'production':None},
       'reserved_hooks':'Only the two explicitly approved cargo extensions; no additional raw hook/framework requirement established.',
       'hardware_obligations':['capture publication','body-variant pose/resource lookup','attachment during transitions','one absolute release','escape','interruption/death/swap cleanup']})
    print('PASS: 15 attacker + 3 victim roles, cleanup and generic/donor dependency ownership pinned; runtime unverified')

if __name__=='__main__':run()
