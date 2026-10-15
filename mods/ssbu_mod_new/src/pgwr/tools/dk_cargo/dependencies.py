"""Pin victim/control dependencies and explicit semantic graph gaps."""
import json
import audit
from audit import ROOT, OUT, INPUT, h40, motion_entries, sha
import stage

def run():
    names=['shouldered_donkey','thrown_f','thrown_f_donkey_f',
           'thrown_f_donkey_b','thrown_f_donkey_hi','thrown_f_donkey_lw']
    names=[n+s for n in names for s in ['', '_dx', '_girl']]
    lists={'donkey':INPUT/'fighter/donkey/motion/body/c00/motion_list.bin',
           'gamewatch':INPUT/'fighter/gamewatch/motion/body/c00/motion_list.bin',
           'eflame_c06':stage.BASE/'fighter/eflame/motion/body/c06/motion_list.bin',
           'eflame_c07':stage.BASE/'fighter/eflame/motion/body/c07/motion_list.bin'}
    matrix={}
    for name,path in lists.items():
        _,rows=motion_entries(path)
        matrix[name]=dict(sha256=sha(path.read_bytes()),entries={n:[r for r in rows if r['kind']==hex(h40(n))] for n in names})
    graph=json.loads((OUT/'status_instruction_graph.json').read_text())
    victim=json.loads((OUT/'victim_instruction_graph.json').read_text())
    status=json.loads((OUT/'allocation_request.json').read_text())
    semantic=json.loads((OUT/'semantic_annotations.json').read_text())
    roster=json.loads((OUT/'victim_roster_motion_matrix.json').read_text())
    native=json.loads((OUT/'native_message_sites.json').read_text())
    pose_route=json.loads((OUT/'native_pose_route.json').read_text())
    result=dict(tier='B',verified='offline bytes and registrations only',
        victim_common_states={'START':'0xc5','CARRY':'0xc6','THROWN':'0xc7'},
        victim_motion_matrix=matrix,
        motion_warning='Empty entries occur in all 94 roster controls; the donor has actual cargo template clips. The exact resource-sharing resolver is not yet recovered. Do not infer missing poses from empty entries or copy donor poses blindly over victim files.',
        attacker_custom_status_requirement=status,
        victim_new_status_requirement={'role_symbols':['VICTIM_START','VICTIM_CARRY','VICTIM_THROWN'],
            'slots_per_eligible_victim_kind':3,'roster_control_count':94,
            'attacker_symbols':15,'total_role_symbols':18,
            'production_ids':None,
            'note':'Reserve 15 attacker slots on eflame c06/c07 and three victim slots per eligible fighter table. Eflame c06/c07 needs both sets (18). Numeric values may differ by fighter; a uniform victim block must be above every eligible fighter table and concurrent allocation. The 94-list roster is the conservative review universe, including non-playable kinds; actual capture eligibility remains unverified.'},
        donor_status_functions=len(graph),victim_exported_functions=len(victim),
        donor_unresolved_indirect_sites=sum(len(r['unresolved_indirect']) for r in graph),
        victim_unresolved_indirect_sites=sum(len(r['unresolved_indirect']) for r in victim),
        graph_complete=False,
        semantic_donor_functions=len(semantic['images']['donkey']['functions']),
        semantic_common_functions=len(semantic['images']['common']['functions']),
        roster_victim_motion_lists=len(roster['matrix']),
        native_pose_route=pose_route,
        resolved_semantics={
            'forward_entry':'DK initializer 0x640 writes SHOULDER_START into global_table[0x45] at 0x2190..0x21ac. Common CatchCont 0xca854 reads it; CatchWait exit 0xd0780 uses the same direction slots to classify throws. Redirecting common THROW Pre is too late for that cleanup classifier.',
            'pickup':'DK Init 0x83e0 sends shoulder through the existing LINK_NO_CAPTURE, then MA_MSC_SET_IGNORE_CATCHING(true). Native receiver branch main+0x637fa4 queues common victim START 0xc5. No manual set_catch/link sequence.',
            'directional_handoff':'DK Init 0x87a0 calls send_event_nodes_throw(shoulder_throw, thrown_f_donkey_<direction>, true, generic target-group/target-no/motion-rate work IDs). Main+0x637290 writes the victim motion and requests common phase 0xc7.',
            'escape':'Common 0x25be30 sends event 0x21ba53a92c when clatter time <= 0. Candidate donor receiver requests common CATCH_CUT for START..PASS. capture_cut first calls CatchModule::set_send_cut_event(false), identified by exported main+0x1ffc3d0.',
            'lift_helper':'Main+0x995040 toggles the COMMON LIGHT_WEIGHT flag, then invokes +0x280. Both candidate donor and recipient vtables point +0x280 to main+0x68daa0, mov w0,#1;ret. No donor specializer call is required to reproduce the inspected branch.',
            'victim_offsets':'Export main+0x20a8010 tails to 0x7210e0: direction selects +0x28/+0x40/+0x58/+0x70 float vectors, Nana aliases Popo, kind < 94, row map accessor+0x14f8+kind*12, row*3 XYZ. Common victim code scales XYZ and reverses X when flipped.',
            'false_event':'0x5ecd55cc6 hashes to final. The donor receiver Final Smash branch is outside cargo scope.',
            'plt_control':'Earlier 16 donor/22 victim unresolved indirect sites were br x17 PLT traversal artifacts. Stopping imported tail branches produces zero unresolved sites in the Lua status graphs; this does not establish complete native/resource semantics.'},
        missing_semantics=[
            'Exact victim pose resource-sharing lookup for empty motion-list entries and owned aliases. Native MotionModule change path main+0x6df820 -> 0x49a4a0 includes resource callbacks +0x458/+0x680 and a +0x190 delegate; their complete sharing semantics remain unconfirmed.',
            'Victim pose template bank ownership, every body variant and capture anchor, including Pickel multi-animation entries. A 94-kind motion-list matrix is pinned; no guessed victim override is supplied.',
            'Complete ownership/cleanup port for callback lifetimes, stop/clatter, constraints, items, invincibility, invalid-capture, swap/death, and all movement/input priority branches. Instruction reachability is not a completed semantic port.',
            'Exact event trigger of native +0x210 and independent constructor/kind identity proof for candidate donor vtable 0x4fa8c80.',
            'Victim registration coverage with current costume-specific framework entries. Source supports on_start and costume gates, but unfiltered status registrations are skipped for costume groups with specific handlers; runtime/collective coverage still needs a checked design.',
            'Donor cut-in zoom/offset bindings expose no accessor, but native.py pins an exported Singleton<FighterCutInManager>::instance_E data symbol. Implement and validate a checked extern-symbol route rather than infer a reserved offset requirement from the bindings gap.'],
        reserved_boundary=dict(candidate_donor_vtable='0x4fa8c80',
            candidate_donor_receiver='main+0x993ee0',recipient_receiver='main+0xa0c8d0',
            event_slot='0x170',shoulder_end_slot='0x210',candidate_donor_end='main+0x994fe0',
            native_lift_helper='main+0x995040 reads accessor +0xf1c0',
            authorized='User explicitly authorized these two cargo extensions: recipient +0x170 and +0x210 only, c06/c07 cargo-gated, preserve Monkey Flip/G&W and forward other events; framework unchanged.',
            authorization_record='refs/donkey_cargo/native_authorization.json',
            still_reserved='Any additional raw-offset hook and all framework changes. No additional hook requirement has yet been established by this capture.',
            implementation_state='AUTHORIZED_NOT_IMPLEMENTED; complete semantic graph remains the user-required prerequisite.'),
        existing_throw_and_grab_handlers_changed=False,
        article_requirement='No cargo article generation appears in the pinned ACMD subset. Native indirect dependencies remain unresolved.',
        runtime_implemented=False,ready=False)
    for target in [OUT/'DEPENDENCIES.json',stage.PACKAGE/'victim_dependencies.json']:
        target.write_text(json.dumps(result,indent=2)+'\n')
    (stage.PACKAGE/'status_allocation_requirement.json').write_text(json.dumps(result['victim_new_status_requirement'],indent=2)+'\n')
    for name in ['native_authorization.json','native_message_sites.json','victim_roster_motion_matrix.json','native_pose_route.json']:
        (stage.PACKAGE/name).write_bytes((OUT/name).read_bytes())
    print('Pinned 94-kind victim controls, resolved semantics, authorized hooks and remaining graph gaps; NOT READY')

if __name__=='__main__':run()
