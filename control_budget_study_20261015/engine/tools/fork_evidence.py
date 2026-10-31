"""Offline physical-prefix and fixed-cohort measurement, never online labels."""
import collections,csv,gzip,hashlib,json
from pathlib import Path
from wsn.fork_controller import digest,clean
DEADLINE_NS=200_000_000
def messages(record,folder):
    with gzip.open(str(folder/record['id'])+'.protocol.jsonl.gz','rt')as f:
        return[json.loads(x)for x in f]
def prefix_proof(record,folder,t):
    h=hashlib.sha256();count=0
    with gzip.open(str(folder/record['id'])+'.protocol.jsonl.gz','rt')as f:
        for line in f:
            if json.loads(line)['time_ns']<=t:h.update(line.encode());count+=1
    radio=[]
    with gzip.open(str(folder/record['id'])+'.radio.csv.gz','rt')as f:
        for x in csv.DictReader(f):
            n,b,e,s=(int(x[k])for k in ('node','start_ns','end_ns','state'))
            if b<t:radio.append([n,b,min(e,t),s])
    jobs=[]
    with gzip.open(str(folder/record['id'])+'.jobs.csv.gz','rt')as f:
        for x in csv.DictReader(f):
            if int(x['request_ns'])+int(x['J_ns'])<=t:jobs.append(x)
    steps=json.loads((folder/(record['id']+'.controller.json')).read_text())['steps']
    observations=[s['observation']for s in steps if s['observation']['time_ns']<=t]
    core=[]
    for s in steps:
        if s['observation']['time_ns']<t:core.append({k:v for k,v in s.items()if k not in ('fork_control','fork_candidate')})
    return dict(time_ns=t,protocol_prefix_sha256=h.hexdigest(),protocol_events=count,radio_prefix_sha256=digest(sorted(radio)),
        completed_jobs_sha256=digest(jobs),observations_sha256=digest(observations),past_core_steps_sha256=digest(core),
        arrivals_sha256=record['hashes']['arrivals'],positions_sha256=record['hashes']['positions'])
def audit_fork(record,folder,reference,reference_folder):
    info=record['fork_info'];assert info is not None;t=info['time_ns'];p=prefix_proof(record,folder,t);q=prefix_proof(reference,reference_folder,t)
    assert p==q,('prefix mismatch',p,q)
    source=next(x for x in reference['state_candidates']if x['time_ns']==t)
    assert source['eligible']and source['decision_emitted']and source['snapshot_sha256']==info['snapshot_sha256']
    assert json.loads(json.dumps(info['snapshot']))==source['snapshot']
    post=[d for d in record['decisions']if d['time_ns']>=t];assert len(post)==1 and post[0]['action']==info['arm']
    assert record['bandit_updates']==[0,0,0,0]
    if info['arm']==0:
        old=next(d for d in reference['decisions']if d['time_ns']==t)
        assert clean(post[0]['paths'])==clean(old['paths'])and post[0]['fe']==old['fe']and clean(post[0].get('admission'))==clean(old.get('admission'))
    return dict(status='passed',prefix=p,common_snapshot_sha256=info['snapshot_sha256'],one_post_fork_decision=True,
        offline_truth_used_by_policy=False,other_branch_rewards_used_by_policy=False,
        scope='deterministic rerun and observable/physical trace-prefix equality; not serialized hidden simulator state')
def window_metrics(record,folder):
    info=record['fork_info'];start=info['time_ns'];end=start+30_000_000_000;settle=end+DEADLINE_NS
    assert end<=record['generation_stop']*1_000_000_000
    ms=messages(record,folder);gen=[x for x in ms if x['kind']=='generated'and start<=x['time_ns']<end]
    delivered={(x['flow'],x['sequence']):x for x in ms if x['kind']=='delivered'};counts=[];timely=[]
    for f in (0,1):
        tasks=[x for x in gen if x['flow']==f];counts.append(len(tasks));assert tasks
        timely.append(sum((d:=delivered.get((f,g['sequence'])))is not None and d['time_ns']-g['time_ns']<=DEADLINE_NS and d['time_ns']<=settle for g in tasks))
    probabilities=[a/b for a,b in zip(timely,counts)];costs=collections.Counter();retry={x['sequence']for x in ms if x['kind']=='report_packet'and x.get('retry')}
    for x in ms:
        if start<=x['time_ns']<settle:
            if x['kind']=='phy_data':
                key='application_DATA'if x['flow']<2 else 'report_retry_DATA'if x['flow']==65000 and x['sequence']in retry else 'ordinary_report_DATA'if x['flow']==65000 else 'installation_DATA'if x['flow']==65001 else 'other_control_DATA'
                costs[key]+=x['bytes']
            elif x['kind']=='phy_ack':costs['network_ACK']+=x['bytes']
    control=sum(costs[k]for k in ('report_retry_DATA','ordinary_report_DATA','installation_DATA','other_control_DATA'))
    energy=0.;currents={1:18.8,2:17.4,6:18.8,9:17.4,8:.426}
    with gzip.open(str(folder/record['id'])+'.radio.csv.gz','rt')as f:
        for r in csv.DictReader(f):
            b,e,s=int(r['start_ns']),int(r['end_ns']),int(r['state']);overlap=max(0,min(e,settle)-max(b,start))
            energy+=overlap/1e9*3*currents[s]/1000
    d=next(d for d in record['decisions']if d['decision']==info['decision']);fbs=[f for f in record['feedbacks']if f['decision']==info['decision']]
    applied={f:[f,2,3,9]for f in (0,1)}
    for x in ms:
        if x['kind']=='install_applied'and x['time_ns']<=end:applied[x['source']]=x['path']
    return dict(start_ns=start,generation_end_ns=end,cost_end_ns=settle,offered_by_source=counts,timely_by_source=timely,service_by_source=probabilities,
        mean_service=sum(probabilities)/2,worst_source_service=min(probabilities),service_utility=.75*sum(probabilities)/2+.25*min(probabilities),
        control_DATA_bytes=control,DATA_breakdown=dict(costs),radio_J=energy,search_FE=d['fe'],simulated_search_delay_ns=d['declared_search_delay_ns'],
        proposed_paths=d['paths']or d.get('admission',{}).get('proposed_paths'),hold=d.get('admitted_hold',False),installed_paths_at_window_end=[applied[f]for f in (0,1)],
        selected_feedback=fbs,qualified_feedback=any(f['reward']is not None for f in fbs),feedback_censored=not any(f['reward']is not None for f in fbs),
        scope='all tasks generated in fixed30s, including installation waiting; all transmissions during30.2s, including preexisting background; radio-only energy; ACK not attributed to control')
