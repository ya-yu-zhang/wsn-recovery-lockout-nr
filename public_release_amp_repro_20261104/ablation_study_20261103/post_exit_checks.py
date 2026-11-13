import json,glob,sys
from pathlib import Path
def checks(folder):
    f=next(Path(folder).glob('*.controller.json'));c=json.loads(f.read_text());out=[]
    case=json.loads((Path(folder)/'case.json').read_text())
    exits=[h['time_ns'] for i in case['installations'] for h in i['history'] if h.get('outcome')=='abandoned_unconfirmed' and h.get('closed')]
    for s in c['steps']:
        t=s['observation']['time_ns'];cons=s.get('constraints') or {};eq=cons.get('evidence_qualified_admission')
        sv=(s.get('event') or {}).get('settled_service') or {}
        d=s.get('decision');sa=s.get('safety_assessment') or {}
        out.append(dict(t=t//10**9,evaluated=bool(cons),allowed=None if eq is None else eq['allowed'],service_known=sv.get('known'),service_reason=sv.get('reason'),worst_timely=sv.get('worst_timely'),
            candidates=None if eq is None else any(eq['geometry_available']),failure_sources=sa.get('failure_sources'),install=bool(d and d.get('paths')),rejection=s.get('rejection')))
    return exits,out
if __name__=='__main__':
    ex,o=checks(sys.argv[1]);print('exits',[e//10**9 for e in ex])
    for r in o:
        if r['t']>=230:print(r)
