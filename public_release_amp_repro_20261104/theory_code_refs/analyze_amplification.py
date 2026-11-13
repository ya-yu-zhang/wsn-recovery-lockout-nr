"""Endpoint computation for amplification stages (frozen with registration)."""
import json,sys,collections
from pathlib import Path
from analyze_contract_ablation import post_exit
ROOT=Path(__file__).resolve().parent;R=ROOT/'results'
def detail(folder,case):
    c=json.loads(next(folder.glob('*.controller.json')).read_text())
    ex=[]
    for i in case['installations']:
        for h in i['history']:
            if h.get('outcome')=='abandoned_unconfirmed' and h.get('closed') and not h.get('late_confirmation'):ex.append((h['time_ns']/1e9,i['decision'],h['missing_sources']))
    inst=[(d['time_ns']/1e9,d['decision'],i['outcome']) for i in case['installations'] for d in [dict(time_ns=i['history'][0]['time_ns'] if i['history'] else 0,decision=i['decision'])]]
    return dict(exits=ex,installs=[(i['decision'],i['outcome'],i['history'][0]['time_ns']/1e9 if i['history'] else None) for i in case['installations']])
def load(stage):
    out=[]
    for f in sorted((R/('amplification_'+stage)).glob('*/case.json')):
        case=json.loads(f.read_text());a=case['audit'];pe=post_exit(f.parent,case)
        out.append(dict(configuration=case['configuration'],key=case['configuration_key'],audit_status=a['status'],worst_source_service=a['worst_source_service'],control_DATA_bytes=a['control_DATA_bytes'],budget_bound_verified=a.get('control_budget_bound_verified'),**pe,**detail(f.parent,case)))
    return out
if __name__=='__main__':
    for r in load(sys.argv[1]):
        c=r['configuration'];print(c['topology'],c['seed'],c['recipe'],c['arm'],round(r['worst_source_service'],4),r['control_DATA_bytes'],'lock=',r['lockout_to_stop'],'exits=',r['exits'],'blk',r['blocked_unconfirmed'],'auth1',r['first_authorized_s'],r['installs'])
