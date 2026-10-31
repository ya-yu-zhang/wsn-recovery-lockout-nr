"""Independent native accounting and received-observation audit."""
from pathlib import Path
import collections,csv,gzip,hashlib,json

def audit(record,folder):
    folder=Path(folder);prefix=folder/record['id'];cfg=record['unified_control']
    generated={};delivered={};data=collections.Counter();ack=0;control_by_node=collections.Counter();grants={};credit={};paid=collections.Counter();attempts=collections.Counter();received=[];admissions=0;drops=0;pacing=0
    with gzip.open(str(prefix)+'.protocol.jsonl.gz','rt')as f:
        for line in f:
            e=json.loads(line);kind=e['kind'];t=e['time_ns']
            if kind=='generated':
                k=(e['flow'],e['sequence']);assert k not in generated;generated[k]=e
            elif kind=='delivered':
                k=(e['flow'],e['sequence']);assert k in generated and k not in delivered
                assert e['generated_ns']==generated[k]['time_ns'];delivered[k]=e
            elif kind=='report_received':
                r=e['report'];assert r['stamp_ns']<=r['received_ns']==t;received.append((t,r))
            elif kind=='version_report_admission':
                assert cfg['version_pacing'];elapsed=t-e['last_emitted_ns']
                urgent=t-e['installed_ns']<15_000_000_000 or e['failure']or e['state']!=e['previous_state']
                expected=5 if urgent else 15
                assert e['period_s']==expected and e['emitted']==(e['last_emitted_ns']==0 or elapsed>=expected*10**9);pacing+=1
            elif kind=='unified_control_admission':
                assert cfg['enabled'];n=e['node'];cap=cfg['burst']*10**9
                old,last=credit.get(n,(cap,0));now=min(cap,old+(t-last)*cfg['rate']);assert e['before_q']==now
                reserve=cfg['reserve']if cfg['protected']and not e['priority']else 0
                admitted=now>=(e['reservation_bytes']+reserve)*10**9
                assert admitted==e['admitted'] and e['reservation_bytes']==381
                after=now-(381*10**9 if admitted else 0);assert after==e['after_q'];credit[n]=(after,t)
                k=(n,e['flow'],e['sequence'])
                if admitted:
                    assert k not in grants;grants[k]=e;paid[n]+=381
                else:drops+=1
                admissions+=1
            elif kind=='phy_data':
                assert 0<e['bytes']<=127;data[e['flow']]+=e['bytes']
                if e['flow']>=65000:
                    n=e['node'];control_by_node[n]+=e['bytes']
                    if cfg['enabled']:
                        k=(n,e['flow'],e['sequence']);assert k in grants;attempts[k]+=1;assert attempts[k]<=3
                        assert control_by_node[n]<=paid[n]
                        assert control_by_node[n]*10**9<=cfg['burst']*10**9+cfg['rate']*t
            elif kind=='phy_ack':ack+=e['bytes']
    offered=[sum(k[0]==f for k in generated)for f in(0,1)]
    timely=[sum(k[0]==f and e['time_ns']-e['generated_ns']<=200_000_000 for k,e in delivered.items())for f in(0,1)]
    rates=[timely[f]/offered[f]for f in(0,1)];assert rates==record['timely_by_party']
    with(Path(str(prefix)+'_arrivals.csv')).open(newline='')as f:
        arrivals=list(csv.DictReader(f))
    assert len(arrivals)==len(generated)
    for row in arrivals:
        k=(int(row['flow']),int(row['sequence']));assert k in generated
        assert abs(float(row['time'])*10**9-generated[k]['time_ns'])<=1.1
    controller=json.loads(Path(str(prefix)+'.controller.json').read_text())
    for s in controller['steps']:
        o=s['observation'];t=o['time_ns']
        for r in o['reports']:
            assert r['stamp_ns']<=r['received_ns']<=t
            assert any(received_ns==r['received_ns']and q==r for received_ns,q in received)
        d=s['decision']
        if d is not None:assert d['fe']<=64 and not d.get('ucb_scores')
    assert record['bandit_updates']==[0,0,0,0]
    for suffix in ('.csv','.jobs.csv','.protocol.jsonl','.radio.csv'):
        b=gzip.decompress(Path(str(prefix)+suffix+'.gz').read_bytes());assert hashlib.sha256(b).hexdigest()==record['hashes'][suffix]
    return {'status':'passed','offered':offered,'timely':timely,'worst_source_service':min(rates),'control_DATA_bytes':sum(control_by_node.values()),'report_DATA_bytes':data[65000],'install_DATA_bytes':data[65001],'application_DATA_bytes':sum(v for k,v in data.items()if k<2),'network_ACK_bytes':ack,'budget_admissions':admissions,'budget_rejections':drops,'control_budget_bound_verified':cfg['enabled'],'version_pacing_checks':pacing,'runtime_LLM_calls':0}
