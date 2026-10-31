"""Independent local report state, installation exit and score-only audit."""
import bisect,collections,csv,gzip,json
from pathlib import Path


def audit_observable(row,folder):
    prefix=folder/row['id']
    messages=[json.loads(x)for x in gzip.open(str(prefix)+'.protocol.jsonl.gz','rt')]
    with gzip.open(str(prefix)+'.jobs.csv.gz','rt')as f:
        jobs={(int(j['node']),int(j['flow']),int(j['sequence'])):j for j in csv.DictReader(f)}
    generated={(m['flow'],m['sequence']):m for m in messages if m['kind']=='generated'}
    receipts=collections.defaultdict(list)
    for (n,f,s),j in jobs.items():
        if f>=2 or int(j['D_ns'])<0:continue
        path=generated[f,s]['path'];target=path[path.index(n)+1]
        if 2<=target<9:receipts[target].append(int(j['request_ns'])+int(j['D_ns']))
    for v in receipts.values():v.sort()
    queues=collections.defaultdict(list);active={};history=collections.defaultdict(list)
    last=collections.defaultdict(int);previous=collections.defaultdict(int);count=0;relay_sent=0;relay_ticks=0
    for m in messages:
        k=m['kind'];t=m['time_ns'];n=m.get('node')
        if k=='queue_arrival'and m['accepted']:queues[n].append((m['flow'],m['sequence']))
        elif k=='queue_choice':
            assert n not in active
            item=queues[n].pop(m['selected_index']);assert item==(m['flow'],m['sequence']);active[n]=item
        elif k=='queue_terminal':assert active.pop(n)==(m['flow'],m['sequence'])
        elif k=='queue_purge':assert queues[n].pop(0)==(m['flow'],m['sequence'])
        elif k=='mac_job_completed':
            j=jobs[n,m['flow'],m['sequence']];assert int(j['request_ns'])+int(j['J_ns'])==t
            history[n].append((t,int(j['cca']),int(j['busy'])))
        elif k=='local_report_admission':
            count+=1;depth=len(queues[n])+int(n in active)
            recent=[h for h in history[n]if h[0]>=t-20_000_000_000]
            cca=sum(h[1]for h in recent);busy=sum(h[2]for h in recent)
            q=bisect.bisect_right(receipts[n],t)
            until=max(12_000_000_000 if n in(2,3)else 0,receipts[n][q-1]+12_000_000_000 if q else 0)
            state=(0 if depth==0 else 1 if depth<=2 else 2 if depth<=8 else 3)+4*int(cca>0 and busy*100>cca*35)+8*int(until>t)
            assert (m['depth'],m['cca'],m['busy'],m['state'])==(depth,cca,busy,state)
            assert m['previous_state']==previous[n]and m['last_emitted_ns']==last[n]
            urgent=n>=2 and state>=8 and state!=previous[n]
            emitted=n<2 or last[n]==0 or t-last[n]>=15_000_000_000 or (urgent and t-last[n]>=10_000_000_000)
            assert m['urgent']==urgent and m['emitted']==emitted and m['period_s']==(5 if n<2 else 10 if urgent else 15)
            if n>=2:
                relay_ticks+=1;relay_sent+=emitted
                if emitted and last[n]:assert 10_000_000_000<=t-last[n]<=15_000_000_000
            if emitted:last[n]=t;previous[n]=state
    steps=json.loads(Path(str(prefix)+'.controller.json').read_text())['steps']
    exits=0;late=0;decisions={d['decision']:d for d in row['decisions']}
    for s in steps:
        d=s['decision'];fb=s['feedback'];i=s.get('installation');t=s['observation']['time_ns']
        if d is not None and '_scoreonly_'in row['policy']:
            assert d['selection_phase']!='event_exploration'and d['exploration_cap']==0
            if row['model']in('stable6','intercept6'):assert d['action']==max((a for a,v in enumerate(d['constraints']['available'])if v),key=lambda a:(d['ucb_scores'][a],-a))
        if i is not None and 'installation_deadline_ns'in i:
            origin=decisions[i['decision']];deadline=15_000_000_000 if '_reviewmechanism_'in row['policy']and '_install15_'in row['policy']else 10_000_000_000
            assert i['installation_deadline_ns']==origin['time_ns']+deadline
            assert all(v<=1 for v in i['retry_counts'])
            if i['outcome']=='abandoned_unconfirmed':
                exits+=1;assert i['missing_sources']and not i['retry_sources']and t>=i['installation_deadline_ns']
                assert fb is not None and fb['reward']is None and fb['updated_action']is None and fb['exit_kind']=='installation_budget_exit'and not fb['physical_failure_asserted']
            if i['late_confirmation']:
                late+=1;assert i['outcome']=='confirmed'and not i['missing_sources']
        if fb is not None and fb['reward']is None:assert fb['updated_action']is None
    return dict(status='passed',local_report_admissions=count,relay_report_ticks=relay_ticks,relay_reports_emitted=relay_sent,
                unconfirmed_installation_exits=exits,late_installation_reconciliations=late,censored_reward_imputations=0,
                online_truth_leakage=False,scope='local queue/MAC/lease and received confirmation only; not a service guarantee')
