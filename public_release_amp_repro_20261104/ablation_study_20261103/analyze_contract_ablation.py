"""Summarize contract-ablation stages from retained native/controller records."""
import json,csv,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent;R=ROOT/'results'
def post_exit(folder,case):
    c=json.loads(next(folder.glob('*.controller.json')).read_text())
    exits=sorted({h['time_ns'] for i in case['installations'] for h in i['history'] if h.get('outcome')=='abandoned_unconfirmed' and h.get('closed') and not h.get('late_confirmation')})
    stop=case['action_stop_ns'];steps=[]
    for s in c['steps']:
        t=s['observation']['time_ns'];cons=s.get('constraints') or {};eq=cons.get('evidence_qualified_admission')
        sv=(s.get('event')or{}).get('settled_service')or{};d=s.get('decision')
        steps.append(dict(t=t,evaluated=eq is not None,allowed=None if eq is None else eq['allowed'],candidates=None if eq is None else any(eq['geometry_available']),reason=sv.get('reason'),install=bool(d and d.get('paths'))))
    if not exits:return dict(unconfirmed_exits=[],post_exit_checks=0,blocked_unconfirmed=0,authorized=0,first_authorized_s=None,lockout_to_stop=False)
    e=exits[-1] if False else exits[0]
    win=[s for s in steps if e<=s['t']<stop and s['evaluated']]
    blocked=[s for s in win if not s['allowed'] and s['reason']=='installation_unconfirmed']
    auth=[s for s in win if s['allowed']]
    last=exits[-1];after=[s for s in steps if last<=s['t']<stop and s['evaluated']]
    lock=bool(after) and all(s['reason']=='installation_unconfirmed' and not s['install'] for s in after)
    return dict(unconfirmed_exits=[x/1e9 for x in exits],post_exit_checks=len(win),blocked_unconfirmed=len(blocked),blocked_with_candidates=sum(1 for s in blocked if s['candidates']),authorized=len(auth),
                first_authorized_s=auth[0]['t']/1e9 if auth else None,installs_after_exit=sum(s['install'] for s in steps if e<=s['t']<stop),lockout_to_stop=lock,post_exit_checks_after_last_exit=len(after))
def load(sub):
    out=[]
    for f in sorted((R/sub).glob('*/case.json')):
        case=json.loads(f.read_text());a=case['audit']
        out.append(dict(configuration=case['configuration'],key=case['configuration_key'],audit_status=a['status'],worst_source_service=a['worst_source_service'],control_DATA_bytes=a['control_DATA_bytes'],install_DATA_bytes=a['install_DATA_bytes'],report_DATA_bytes=a['report_DATA_bytes'],budget_bound_verified=a.get('control_budget_bound_verified'),**post_exit(f.parent,case)))
    return out
def main():
    arch={}
    with open(R/'horizon_development_case_metrics.csv')as f:
        for r in csv.DictReader(f):arch[(r['topology'],r['scenario'],int(r['seed']),r['model'])]=r
    summary={}
    for sub in('contract_ablation','contract_generalization'):
        if not(R/sub).exists():continue
        rows=load(sub);summary[sub]=rows
    repro=[]
    for r in summary.get('contract_ablation',[]):
        c=r['configuration']
        if c['contract']!='joint':continue
        a=arch[(c['topology'],c['scenario'],c['seed'],c['model'])]
        repro.append(dict(cfg=c,service_match=abs(float(a['worst_source_service'])-r['worst_source_service'])<1e-12,bytes_match=int(a['control_DATA_bytes'])==r['control_DATA_bytes']))
    summary['reproduction_vs_archived_40case']=dict(checked=len(repro),all_match=all(x['service_match']and x['bytes_match']for x in repro),rows=repro)
    pairs=[]
    for sub in summary:
        if sub.startswith('repro'):continue
        idx={json.dumps({k:v for k,v in r['configuration'].items()if k!='contract'and k!='model'},sort_keys=True)+r['configuration']['model']+r['configuration']['contract']:r for r in summary[sub]}
        for r in summary[sub]:
            c=r['configuration']
            if c['contract']!='joint':continue
            base={k:v for k,v in c.items()if k not in('contract','model')}
            pe=idx.get(json.dumps(base,sort_keys=True)+c['model']+'post_exit');lg=idx.get(json.dumps(base,sort_keys=True)+'legacynone')
            if pe is None:continue
            pairs.append(dict(stage=sub,**base,model=c['model'],joint_service=r['worst_source_service'],post_exit_service=pe['worst_source_service'],delta_service_pp=100*(pe['worst_source_service']-r['worst_source_service']),
                joint_control=r['control_DATA_bytes'],post_exit_control=pe['control_DATA_bytes'],delta_control_pct=100*(pe['control_DATA_bytes']/r['control_DATA_bytes']-1),
                legacy_service=None if lg is None else lg['worst_source_service'],legacy_control=None if lg is None else lg['control_DATA_bytes'],
                joint_lockout_to_stop=r['lockout_to_stop'],joint_blocked_checks=r['blocked_unconfirmed'],joint_unconfirmed_exit=bool(r['unconfirmed_exits']),
                post_exit_first_authorized_s=pe['first_authorized_s'],post_exit_lockout_to_stop=pe['lockout_to_stop']))
    summary['paired_contrasts']=pairs
    (R/'contract_ablation_summary.json').write_text(json.dumps(summary,indent=1)+'\n')
    for p in pairs:print(p['stage'][9:],p['topology'],p['scenario'][:5],p['seed'],p['model'],'J=%.4f PE=%.4f d=%+.2fpp dC=%+.2f%% lock=%s blk=%d first=%s L=%s'%(p['joint_service'],p['post_exit_service'],p['delta_service_pp'],p['delta_control_pct'],p['joint_lockout_to_stop'],p['joint_blocked_checks'],p['post_exit_first_authorized_s'],None if p['legacy_service']is None else round(p['legacy_service'],4)))
    print('REPRO',summary['reproduction_vs_archived_40case']['checked'],summary['reproduction_vs_archived_40case']['all_match'])
if __name__=='__main__':main()
