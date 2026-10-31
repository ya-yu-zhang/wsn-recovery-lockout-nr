import csv,gzip,hashlib,io,json,math
from collections import defaultdict
from pathlib import Path
import numpy as np
from run_closed_loop import ROOT,OUT
from wsn.controller import Controller


def read(path):
    if path.exists():return gzip.decompress(path.read_bytes()) if path.suffix=='.gz' else path.read_bytes()
    if path.name.endswith('.csv.gz'):
        encoded=Path(str(path)[:-7]+'.ccsv.xz')
        if encoded.exists():
            from wsn.csv_archive import decode
            return decode(encoded.read_bytes())
    raise FileNotFoundError(path)



def clean(value):
    if isinstance(value,dict):return {str(k):clean(v) for k,v in value.items() if k not in ('compute_wall_ns','constraint_wall_ns')}
    if isinstance(value,(list,tuple)):return [clean(x) for x in value]
    return value


def audit_case(r,folder,controller_factory=None):
    prefix=folder/r['id']
    for suffix,h in r['hashes'].items():
        p=Path(str(prefix)+('_arrivals.csv' if suffix=='arrivals' else '_positions.csv' if suffix=='positions' else '.controller.json' if suffix=='controller' else suffix+'.gz'))
        assert hashlib.sha256(read(p)).hexdigest()==h,(r['id'],suffix)
    from wsn.topology import geometry
    assert {int(k):tuple(v) for k,v in r['points'].items()}==geometry(r['topology'])
    positions=list(csv.DictReader((folder/(r['id']+'_positions.csv')).open()))
    assert {int(x['node']):(float(x['x']),float(x['y'])) for x in positions}==geometry(r['topology'])
    messages=[json.loads(x) for x in read(Path(str(prefix)+'.protocol.jsonl.gz')).decode().splitlines()]
    gen={};delivered={};received=[];applied=[];started={};no_solution={};holds={};phy=[];ack=[];repgen={}
    observed_ctrl_bytes=defaultdict(int)
    for x in messages:
        k=x['kind']
        if k=='phy_data' and x['flow']>=65000:observed_ctrl_bytes[x['node']]+=x['bytes']
        if k=='report_generated':
            assert x['report']['ctrl_bytes']==observed_ctrl_bytes[x['report']['node']]
            assert x['report']['period_s'] in (5,10,15,20)
        if k=='generated':gen[x['flow'],x['sequence']]=x
        elif k=='delivered':
            key=(x['flow'],x['sequence']);assert key not in delivered;delivered[key]=x
            assert x['generated_ns']==gen[key]['time_ns'] and x['version']==gen[key]['version']
        elif k=='report_received':received.append(x)
        elif k=='report_generated':repgen[x['report']['node'],x['report']['stamp_ns']]=x['report']
        elif k=='install_applied':applied.append(x)
        elif k=='install_started':started[x['decision']]=x
        elif k=='action_no_solution':no_solution[x['decision']]=x
        elif k=='action_hold':holds[x['decision']]=x
        elif k=='phy_data':phy.append(x)
        elif k=='phy_ack':ack.append(x)
    assert len(gen)==r['offered']==sum(r['native']['offered'])
    assert len(delivered)==sum(r['native']['delivered'])
    for x in received:
        a=x['report'].copy();a['received_ns']=0;assert a==repgen[a['node'],a['stamp_ns']]
    jobs=np.loadtxt(io.BytesIO(read(Path(str(prefix)+'.jobs.csv.gz'))),delimiter=',',skiprows=1,dtype=np.int64,ndmin=2)
    assert len(jobs)==r['native']['finalized_jobs'] and len({tuple(row[:3]) for row in jobs})==len(jobs)
    # Join immutable generation metadata to the unchanged 28-column CSV.
    # Protocol callback order, rather than a strict timestamp inequality,
    # determines inclusion at coincident completion/report timestamps.
    from wsn.version_audit import reconstruct
    rebuilt,version_audit=reconstruct(messages,jobs,r['extended_report'],r['source_only_counters'],r.get('epoch_certificate',False))
    assert rebuilt==repgen
    assert int(jobs[:,9].sum())==len(phy)==r['native']['data_transmissions'];assert np.all(jobs[:,9]<=3)
    assert np.all(jobs[:,5]>0) and np.all(jobs[:,7]>=0) and np.all((jobs[:,6]<0)|(jobs[:,6]<=jobs[:,5]))
    last=[]
    for row in jobs[jobs[:,1]<2]:
        node,f,seq=map(int,row[:3]);g=gen[f,seq];assert node in g['path'][:-1]
        if node==g['path'][-2] and row[6]>=0:last.append((f,seq,int(row[4]+row[6])))
    assert {(f,seq):end for f,seq,end in last}=={k:x['time_ns'] for k,x in delivered.items()}
    controlbytes=sum(x['bytes'] for x in phy if x['flow']>=65000);appbytes=sum(x['bytes'] for x in phy if x['flow']<2);ackbytes=sum(x['bytes'] for x in ack)
    assert (controlbytes,appbytes,ackbytes)==tuple(r['native'][k] for k in ('control_psdu_bytes','application_psdu_bytes','ack_psdu_bytes'))
    report_size=127 if r['extended_report'] else 119
    assert max(x['bytes'] for x in phy)<=127 and set(x['bytes'] for x in phy)<={111,119,127}
    report_packets={x['sequence']:x for x in messages if x['kind']=='report_packet'}
    assert sum(not x.get("retry",False) for x in report_packets.values())==len(repgen)
    assert len({(x['source'],x['time_ns']) for x in report_packets.values() if not x.get('retry',False)})==len(repgen)
    for meta in report_packets.values():
        assert (meta['source'],meta.get('stamp_ns',meta['time_ns'])) in repgen
        expected_body=80 if r['extended_report'] and (not r['source_only_counters'] or meta['source']<2) else 72
        assert meta['body_bytes']==expected_body
    for x in phy:
        if x['flow']==65000:assert x['bytes']==report_packets[x['sequence']]['body_bytes']+47
    radio=np.loadtxt(io.BytesIO(read(Path(str(prefix)+'.radio.csv.gz'))),delimiter=',',skiprows=1,dtype=np.int64,ndmin=2)
    currents={1:18.8,2:17.4,6:18.8,9:17.4,8:.426};energy=[]
    for n in range(10):
        rows=radio[radio[:,0]==n];assert rows[0,1]==0 and rows[-1,2]==r['native']['stop_ns'];assert np.array_equal(rows[1:,1],rows[:-1,2])
        assert np.all(rows[:,2]>=rows[:,1]) and int((rows[:,2]-rows[:,1]).sum())==r['native']['stop_ns']
        energy.append(sum((int(e)-int(b))/1e9*3*currents[int(s)]/1000 for node,b,e,s in rows))
    assert np.array_equal(energy,r['estimated_radio_joules_by_node'])
    # Reconstruct controller-visible packets, then replay decisions and selected
    # arm learning. This consumes no native future jobs or other-run outcomes.
    cdata=json.loads(Path(str(prefix)+'.controller.json').read_text());factory=Controller if controller_factory is None else controller_factory
    controller=factory(r['policy'],r['report_profile'],points=r['points'],action_stop_ns=r['action_stop_ns'],selection_seed=r['selection_seed'],**r.get('controller_kwargs',{}));decision_ns={x['decision']:x['time_ns'] for x in r['decisions']}
    visible_bucket_cache={};independent_waits=[]
    for step in cdata['steps']:
        obs=step['observation'];t=obs['time_ns'];latest={}
        for x in received:
            if x['time_ns']>t:continue
            rr=x['report'];n=rr['node']
            if n not in latest or latest[n]['stamp_ns']<rr['stamp_ns']:latest[n]=rr
        assert obs['reports']==[latest[n] for n in sorted(latest)]
        assert obs['sink_control_bytes']==sum(x['bytes']for x in phy if x['node']==9 and x['flow']>=65000 and x['time_ns']<=t)
        # Independent provenance reconstruction from the snapshots actually
        # exposed to the online controller, not all native receptions.
        if '_grace5_' in r['policy'] or '_cache20_' in r['policy']:
            visible_bucket_cache={key:value for key,value in visible_bucket_cache.items() if (key[1]+1)*5_000_000_000>=t-60_000_000_000}
            for rr in obs['reports']:
                if rr['node'] not in (0,1):continue
                for bucket,count in rr['buckets']:
                    if bucket==2**32-1 or (bucket+1)*5_000_000_000>rr['stamp_ns'] or (bucket+1)*5_000_000_000<t-60_000_000_000:continue
                    key=(rr['node'],bucket)
                    proof=dict(source=rr['node'],bucket=bucket,count=count,stamp_ns=rr['stamp_ns'],received_ns=rr['received_ns'],visible_ns=t)
                    if key in visible_bucket_cache:assert visible_bucket_cache[key]['count']==count
                    else:visible_bucket_cache[key]=proof
        timely={}
        for x in delivered.values():
            if x['time_ns']<=t and x['time_ns']-x['generated_ns']<=200_000_000:
                b=str(x['generated_ns']//5_000_000_000);timely.setdefault(b,[0,0])[x['flow']]+=1
        assert obs['timely_buckets']==timely
        # Apply the same JSON boundary as the recorded native controller log.
        # In-memory snapshot maps have integer keys; JSON object keys are strings.
        reply,replay=controller.step(obs);assert clean(replay)==clean(step)
        d=step['decision']
        if d is not None and d.get('admitted_hold'):
            observed={r['node']:r for r in obs['reports']}
            proposed=d['admission']['proposed_paths']
            for f in (0,1):
                rr=observed[f]
                assert 0<=t-rr['stamp_ns']<=8_000_000_000
                if '_ops_' not in r['policy']:
                    assert rr['current_n']>=20
                    assert 0<=rr['current_failed']/rr['current_n']<.2
                history=[a for a in applied if a['source']==f and a['time_ns']<=t]
                physical_path=history[-1]['path'] if history else [f,2,3,9]
                assert list(proposed[f])==physical_path,'hold changed source route or ignored unobserved application'
                for node in proposed[f][:-1]:
                    limit=(8_000_000_000 if node<2 else 16_000_000_000 if '_freshfixed_' in r['policy'] else int(observed[node]['period_s']*1_600_000_000) if '_freshscaled_' in r['policy'] or r['report_profile'] in ('lease10_20','lease10_15') else 16_000_000_000)
                    assert node in observed and 0<=t-observed[node]['stamp_ns']<=limit
            assert d['decision'] not in {a['decision'] for a in applied}
            assert not any(p['kind']=='install_packet' and p['decision']==d['decision'] for p in messages)
        wait=step.get('feedback_wait')
        if wait is not None:
            independent_waits.append(wait);assert wait['extra_packets_requested']==0
            assert wait['time_ns']==wait['due_ns'] and wait['deadline_ns']==wait['due_ns']+5_000_000_000
            assert any(wait['missing_closed_buckets']) and step['decision'] is None and step['feedback'] is None
        if step['feedback'] is not None:
            fb=step['feedback'];assert fb['time_ns']>=fb['cohort_end_ns']+200_000_000
            if 'bucket_evidence' in fb:
                assert 0<=fb['extra_wait_ns']<=fb['grace_budget_ns']
                buckets=list(range(fb['cohort_start_ns']//5_000_000_000,fb['cohort_start_ns']//5_000_000_000+3))
                expected_proof=[visible_bucket_cache[f,b] for f in (0,1) for b in buckets if (f,b) in visible_bucket_cache]
                assert fb['bucket_evidence']==expected_proof
                assert fb['missing_closed_buckets']==[[b for b in buckets if (f,b) not in visible_bucket_cache] for f in (0,1)]
                assert fb['recovered_after_wait']==(any(w['decision']==fb['decision'] for w in independent_waits) and fb['reward'] is not None)
                for proof in fb['bucket_evidence']:
                    assert (proof['bucket']+1)*5_000_000_000<=proof['stamp_ns']<=proof['received_ns']<=proof['visible_ns']<=t
            for f,n in enumerate(fb['offered']):
                expected=sum(g['flow']==f and fb['cohort_start_ns']<=g['time_ns']<fb['cohort_end_ns'] for g in gen.values());assert n==expected
            if fb['updated_action'] is not None:assert fb['updated_action']==next(x['action'] for x in r['decisions'] if x['decision']==fb['decision'])
    assert controller.bandit.updates==r['bandit_updates']
    assert controller.feedback_waits==r['feedback_waits']==cdata['feedback_waits']==independent_waits
    assert np.array_equal(controller.bandit.A,cdata['bandit_A']) and np.array_equal(controller.bandit.b,cdata['bandit_b'])
    for d in r['decisions']:
        assert 1<=d['fe']<=(64 if '_ops_' in r['policy'] else {0:8,1:8,2:16,3:64}[d['action']])
        if d['paths']:
            assert d['decision'] in started and started[d['decision']]['time_ns']==d['time_ns']+d['declared_search_delay_ns']
        elif d.get('admitted_hold'):
            assert d['decision'] in holds and d['decision'] not in started and d['decision'] not in no_solution
            assert holds[d['decision']]['time_ns']==d['time_ns']+d['declared_search_delay_ns']
            assert holds[d['decision']]['fe']==d['fe'] and holds[d['decision']]['action']==d['action']
            assert d['install_budget_bytes']==0 and d['decision'] not in controller.version_paths
        else:assert d['decision'] in no_solution
    for x in applied:
        d=next(d for d in r['decisions'] if d['decision']==x['decision']);assert x['path']==list(d['paths'][x['source']])
        assert x['time_ns']>=started[x['decision']]['time_ns']
    assert controller.warmup_attempts==cdata['warmup_attempts'] and controller.event_attempts==cdata['event_attempts']
    assert clean(controller.constraint_logs)==clean(cdata['constraint_logs'])
    assert sum(x['candidate_pair_freshness_checks'] for x in controller.constraint_logs)==r['constraint_pair_checks']
    for phase in ('paid_warmup','event_exploration'):
        warm=[d for d in r['decisions'] if d['selection_phase']==phase]
        credit_explore='_creditexplore_'in r['policy']and phase=='event_exploration'
        if credit_explore:
            from collections import Counter
            assert len(warm)<=8 and max(Counter(d['action']for d in warm).values(),default=0)<=2
        else:assert len({d['action'] for d in warm})==len(warm)<=4
        assert sum(d['fe'] for d in warm)<=(512 if credit_explore else 256 if '_ops_' in r['policy'] else 96) and sum(d['install_budget_bytes'] for d in warm)<=(47952 if credit_explore else 23976)
        for d in warm:
            assert d['event']['observation_states']['0']==d['event']['observation_states']['1']=='fresh'
            if phase=='event_exploration':assert d['decision']>1 and (d['event']['missing']>0 or d['event']['busy']>.35 or d['event']['source_queue']>2 or d['event'].get('trigger_failure',False))
    for d in r['decisions']:
        if d['constraints'] is not None:assert d['constraints']['available'][d['action']] and (d['paths'] is not None or d.get('admitted_hold'))
    for step in cdata['steps']:
        if step['constraints'] is not None:
            assert step['constraints']['unselected_objective_evaluations']==0
            if not any(step['constraints']['available']):assert step['decision'] is None and step['rejection']=='all_arms_infeasible'
    # Independently reconstruct locally observed data leases from first valid
    # application MAC receptions. No simulator liveness enters the controller.
    receptions=defaultdict(list)
    for row in jobs[jobs[:,1]<2]:
        if row[6]<0:continue
        node,f,seq=map(int,row[:3]);path=gen[f,seq]['path'];target=path[path.index(node)+1]
        if 2<=target<9:receptions[target].append(int(row[4]+row[6]))
    fault_events=[x for x in messages if x['kind']=='fault_injected']
    assert [[x['time_ns']/1e9,x['node']] for x in fault_events]==[list(f) for f in sorted(r['faults'])]
    fault_times={x['node']:x['time_ns']/1e9 for x in fault_events}
    ticks=[x for x in messages if x['kind']=='report_tick'];assert len(ticks)==len({(x['node'],x['slot']) for x in ticks})
    for n in range(9):
        nt=[x for x in ticks if x['node']==n];expected=[];t=5.1+n*.02;slot=0
        while t<r['generation_stop']+15 and t<fault_times.get(n,float('inf')):
            expected.append((slot,round(t*1e9)));t+=5;slot+=1
        assert len(nt)==len(expected)
        last_guarded_stamp=None
        for x,(slot,stamp) in zip(nt,expected):
            assert x['slot']==slot and abs(x['time_ns']-stamp)<=1
            priority=r['report_profile'].startswith('path_priority') or r['report_profile'] in ('lease10_20','lease10_15','local15_event')
            until=max([12_000_000_000 if n in (2,3) else 0]+[q+12_000_000_000 for q in receptions[n] if q<=x['time_ns']]) if priority else 0
            assert x['priority_until_ns']==until,(r['id'],n,x,until)
            period=5 if n<2 or r['report_profile']=='full5' or (priority and until>x['time_ns']) else 10
            if r['report_profile'] in ('lease10_20','lease10_15') and n>=2:period=10 if until>x['time_ns'] else (15 if r['report_profile']=='lease10_15' else 20)
            emitted=(last_guarded_stamp is None or stamp-last_guarded_stamp>=period*1_000_000_000) if r['report_profile']=='lease10_15' else slot%(period//5)==0
            if r['report_profile']=='lease10_15' and emitted:last_guarded_stamp=stamp
            if r['report_profile']=='local15_event':
                admission=next(a for a in messages if a['kind']=='local_report_admission' and a['node']==n and a['time_ns']==x['time_ns'])
                # The separate local report audit reconstructs these input
                # counters from queue and completed MAC histories.
                state=admission['state'];urgent=n>=2 and state>=8 and state!=admission['previous_state']
                period=5 if n<2 else 10 if urgent else 15
                emitted=n<2 or last_guarded_stamp is None or stamp-last_guarded_stamp>=15_000_000_000 or (urgent and stamp-last_guarded_stamp>=10_000_000_000)
                assert admission['urgent']==urgent and admission['period_s']==period and admission['emitted']==emitted
                if emitted:last_guarded_stamp=stamp
            assert x['period_s']==period and x['emitted']==emitted
            if x['emitted']:assert repgen[n,x['time_ns']]['period_s']==period
        assert sum(x['emitted'] for x in nt)==sum(node==n for node,stamp in repgen)
    # Reconcile retransmissions, confirmation history, and exact DATA cost attribution.
    assert clean(controller.logs)==clean(r['decisions'])
    assert controller.retries==r['retries']==cdata['retries']
    assert [dict(decision=x.decision,retry_limit=x.retry_limit,history=x.history,closed=x.closed,outcome=x.outcome) for x in controller.installations]==r['installations']
    packets={x['sequence']:x for x in messages if x['kind']=='install_packet'}
    attempts=[x for x in messages if x['kind']=='install_attempt']
    expected=[dict(time_ns=d['time_ns']+d['declared_search_delay_ns'],decision=d['decision'],targets=3,retry=False,action=d['action'],fe=d['fe']) for d in r['decisions'] if d['paths']]
    for ret in r['retries']:
        d=next(d for d in r['decisions'] if d['decision']==ret['decision'])
        expected.append(dict(time_ns=ret['time_ns'],decision=ret['decision'],targets=sum(1<<f for f in ret['sources']),retry=True,action=d['action'],fe=0))
    assert [{k:x[k] for k in expected[0]} for x in attempts]==sorted(expected,key=lambda x:x['time_ns']) if expected else not attempts
    assert len(packets)==sum(x['targets'].bit_count() for x in attempts)
    for at in attempts:
        ps=[x for x in packets.values() if x['time_ns']==at['time_ns'] and x['decision']==at['decision']]
        assert {x['source'] for x in ps}=={f for f in (0,1) if at['targets']&(1<<f)}
        assert all(x['retry']==at['retry'] for x in ps)
    installbytes=defaultdict(int);retrybytes=0
    for x in phy:
        if x['flow']==65001:
            meta=packets[x['sequence']];installbytes[meta['decision']]+=x['bytes'];retrybytes+=x['bytes'] if meta['retry'] else 0
    assert sum(installbytes.values())==sum(x['bytes'] for x in phy if x['flow']==65001)
    for d in r['decisions']:
        charged=(1998 if d['paths'] else 0)+sum(ret['declared_install_budget_bytes'] for ret in r['retries'] if ret['decision']==d['decision'])
        assert charged==d['install_budget_bytes'] and installbytes[d['decision']]<=charged<=5994
        for f in (0,1):assert sum(f in x['sources'] for x in r['retries'] if x['decision']==d['decision'])<=controller.retry_limit
    redundant=sum(x['kind']=='install_received' and x['previous_version']==x['decision'] for x in messages)
    updates=sum(controller.bandit.updates);assert updates==sum(f['updated_action'] is not None for f in r['feedbacks'])
    assert len({f['decision'] for f in r['feedbacks']})==len(r['feedbacks']), 'duplicate feedback identity'
    # Old-version in-flight packets delivered after an installation are counted.
    continued=sum(any(a['source']==x['flow'] and a['time_ns']>x['generated_ns'] and a['time_ns']<x['time_ns'] and a['version']>x['version'] for a in applied) for x in delivered.values())
    return dict(id=r['id'],status='passed',offered=len(gen),mac_jobs=len(jobs),report_receptions=len(received),install_applications=len(applied),retry_commands=len(r['retries']),retry_actual_data_bytes=retrybytes,redundant_install_receipts=redundant,
      old_version_deliveries_after_install=continued,bandit_updates=updates,control_psdu_bytes=controlbytes,radio_ns_per_node=r['native']['stop_ns'],version_audit=version_audit,report_psdu_bytes=report_size)


def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--functional',action='store_true');args=p.parse_args()
    file='functional_manifest.json' if args.functional else 'development_manifest.json';folder=ROOT/'results/functional' if args.functional else ROOT/'results/development'
    registration=ROOT/'docs'/('functional_registration.json' if args.functional else 'development_registration.json')
    expected=len(json.loads(registration.read_text())['configs'])
    runs=json.loads((ROOT/'results'/file).read_text());assert len(runs)==expected, 'wait for complete registered matrix';report=[]
    for i,r in enumerate(runs):
        report.append(audit_case(r,folder))
        if (i+1)%24==0:print('audited',i+1,'/',len(runs),flush=True)
    if args.functional:
        for r,a in zip(runs,report):
            if r['broken_install']:assert a['install_applications']==0 and a['control_psdu_bytes']>0
            if r['source_reports_missing']:assert sum(r['bandit_updates'])==0 and all(f['reward'] is None for f in r['feedbacks'])
        injected=next(r for r in runs if r.get('source1_first_rejection'))
        assert any(1 in ret['sources'] for ret in injected['retries'])
        assert all(ret['fe']==0 for r in runs for ret in r['retries'])
        dest='functional_integrity.json'
    else:dest='closed_loop_integrity.json'
    result=dict(status='passed',native_runs=len(runs),cases=report,all_report_visibility_reconstructed=True,all_selected_arm_updates_replayed=True,
       all_native_transmissions_and_phy_intervals_reconciled=True,all_priority_leases_reconstructed_from_received_data=True,all_report_periods_and_local_byte_meters_validated=True,total_jobs=sum(x['mac_jobs'] for x in report),original_phase2_integrated=False)
    (ROOT/'results'/dest).write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='cases'}))

if __name__=='__main__':main()
