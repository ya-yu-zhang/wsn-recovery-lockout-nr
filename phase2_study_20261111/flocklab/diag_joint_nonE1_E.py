"""Exploratory (E), read-only: why Joint M1 runs have gate closed in 48/48 but IU-only E1 in 24/48.
Reads frozen per-run controller.json under raw_on_request/scratch_phase2/flocklab_full; no simulation."""
import json
from pathlib import Path
from collections import Counter
rows=json.load(open(Path(__file__).parent/'results_full/runs.json'))['rows']
out=[]
for x in rows:
    c=x['configuration']
    if c['scenario_tag']!='M1' or c['arm']!='joint': continue
    f=Path(x['folder']); case=json.loads((f/'case.json').read_text())
    ctl=json.loads(next(f.glob('*.controller.json')).read_text())
    exits=sorted({h['time_ns'] for i in case['installations'] for h in i['history'] if h.get('outcome')=='abandoned_unconfirmed' and h.get('closed') and not h.get('late_confirmation')})
    stop=case['action_stop_ns']; last=exits[-1]
    rs=Counter(); allowed=0; n=0
    for s in ctl['steps']:
        t=s['observation']['time_ns']; eq=(s.get('constraints') or {}).get('evidence_qualified_admission')
        if last<=t<stop and eq is not None:
            n+=1; rs[((s.get('event') or {}).get('settled_service') or {}).get('reason')]+=1; allowed+=bool(eq['allowed'])
    out.append(dict(day=c['day'],mode='R1' if c['trace_mode']==1 else 'R2',trace_mode=c['trace_mode'],seed=c['seed'],subgraph=c['subgraph'],E1=x['E1'],installs_after_exit=x['installs_after_exit'],
                    fs_after_last_exit=x['fs_after_last_exit'],evaluated_after_last_exit=n,allowed_after_last_exit=allowed,reasons=dict(rs)))
non=[o for o in out if not o['E1']]
summ=dict(n_joint_M1=len(out),E1=sum(o['E1'] for o in out),non_E1=len(non),
          non_E1_with_missing_fresh_source=sum(1 for o in non if o['reasons'].get('missing_fresh_source',0)>0),
          non_E1_reason_sets=Counter(','.join(sorted(k for k in o['reasons'] if k)) for o in non),
          non_E1_any_allowed=sum(1 for o in non if o['allowed_after_last_exit']>0),
          non_E1_fs_after_last_exit=sum(1 for o in non if o['fs_after_last_exit']),
          all_installs_after_exit_zero=all(o['installs_after_exit']==0 for o in out),
          E1_reason_sets=Counter(','.join(sorted(k for k in o['reasons'] if k)) for o in out if o['E1']))
summ['non_E1_reason_sets']=dict(summ['non_E1_reason_sets']); summ['E1_reason_sets']=dict(summ['E1_reason_sets'])
json.dump(dict(note=__doc__,summary=summ,rows=out),open(Path(__file__).parent/'results_full/joint_nonE1_diagnostic_E.json','w'),indent=1)
print(json.dumps(summ,indent=1))
