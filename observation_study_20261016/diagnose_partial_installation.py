"""Existing-data partial-installation diagnosis and received-only shadow windows."""
from pathlib import Path
import argparse,collections,csv,gzip,hashlib,io,json,zipfile

ROOT=Path(__file__).resolve().parent
NS=10**9;B=5*NS;TARGET=(10,'multi_failure',2026101511)

def sha(b):return hashlib.sha256(b).hexdigest()

def shadow_windows(controller,record):
    known_paths={0:[[0,2,3,9],[1,2,3,9]]}
    for d in record['decisions']:
        if d.get('paths'):known_paths[d['decision']]=d['paths']
    cache={};rows=[]
    for step in controller['steps']:
        obs=step['observation'];t=obs['time_ns']
        sources={r['node']:r for r in obs['reports']if r['node']in(0,1)}
        for f,r in sources.items():
            assert r['stamp_ns']<=r['received_ns']<=t
            anchor=r['epoch_first_bucket'];assert r['buckets'][0]==[2**32-1,anchor]
            for bucket,count in r['buckets']:
                if bucket==2**32-1 or (bucket+1)*B>r['stamp_ns']or bucket<anchor:continue
                k=(f,r['version'],bucket)
                if k in cache:assert cache[k]['count']==count
                cache[k]=dict(source=f,version=r['version'],bucket=bucket,count=count,stamp_ns=r['stamp_ns'],received_ns=r['received_ns'],epoch_first_bucket=anchor)
        if not 245*NS<=t<320*NS:continue
        item=dict(time_s=t/NS,actual_service=step['event']['settled_service'],
            actual_rejection=step.get('rejection'),shadow_known=False,shadow_scope='historical received cohort only; not an executed decision or its outcome')
        if len(sources)!=2 or any(not 0<=t-r['stamp_ns']<=16*NS for r in sources.values()):
            item['shadow_reason']='missing_16s_source_view';rows.append(item);continue
        versions=[sources[f]['version']for f in(0,1)]
        if any(v not in known_paths for v in versions):
            item['shadow_reason']='version_not_in_known_commands';rows.append(item);continue
        anchor=max(sources[f]['epoch_first_bucket']for f in(0,1))
        available={b for f,v,b in cache if f==0 and v==versions[0]and b>=anchor and (b+1)*B+200_000_000<=t and t-(b+1)*B<=20*NS}
        selected=None
        for end in sorted(available,reverse=True):
            buckets=[end-1,end];keys=[(f,versions[f],b)for f in(0,1)for b in buckets]
            if any(b<anchor for b in buckets)or any(k not in cache for k in keys):continue
            proof=[cache[k]for k in keys]
            offered=[sum(cache[f,versions[f],b]['count']for b in buckets)for f in(0,1)]
            if min(offered)<20:continue
            timely=[sum(obs['timely_buckets'].get(str(b),[0,0])[f]for b in buckets)for f in(0,1)]
            assert all(0<=n<=d for n,d in zip(timely,offered))
            selected=dict(shadow_known=True,buckets=buckets,version_by_source=versions,
                known_route_by_source=[known_paths[versions[f]][f]for f in(0,1)],
                earliest_bucket=anchor,offered=offered,timely=timely,
                worst_timely=min(n/d for n,d in zip(timely,offered)),
                cohort_end_age_s=(t-(end+1)*B)/NS,received_denominator_proof=proof)
            break
        if selected:item.update(selected)
        else:item['shadow_reason']='no_bounded_received_pair'
        rows.append(item)
    return rows

def native_update(z,name,row):
    prefix=str(Path(name).parent/row['id']);packets={};updates=[];generated=collections.Counter();bucket_offered=collections.Counter();bucket_timely=collections.Counter();admissions=[];queue=[];sha_protocol=hashlib.sha256()
    with z.open(prefix+'.protocol.jsonl.gz')as entry,gzip.GzipFile(fileobj=entry)as f:
        for line in f:
            sha_protocol.update(line);e=json.loads(line);kind=e['kind'];t=e['time_ns']
            if kind in('install_applied','install_received','fault_injected'):
                updates.append(e)
            if kind=='install_packet'and t>=210*NS:packets[e['sequence']]=e
            if kind=='generated'and t>=225*NS:
                generated[(e['flow'],e['version'],tuple(e['path']))]+=1
            if kind=='generated':bucket_offered[e['flow'],e['version'],t//B]+=1
            if kind=='delivered'and e['time_ns']-e['generated_ns']<=200_000_000:
                bucket_timely[e['flow'],e['version'],e['generated_ns']//B]+=1
            if t>=210*NS and e.get('flow')==65001:
                if kind=='unified_control_admission':admissions.append(e)
                if kind in('queue_arrival','queue_terminal','control_budget_drop','queue_drop'):queue.append(e)
    assert sha_protocol.hexdigest()==row['hashes']['.protocol.jsonl']
    # CSV column order is fixed by the pinned native driver's jobsTrace serialization.
    raw=gzip.decompress(z.read(prefix+'.jobs.csv.gz'));assert sha(raw)==row['hashes']['.jobs.csv']
    data=csv.reader(io.StringIO(raw.decode()));header=next(data);jobs=[]
    for a in data:
        if int(a[1])==65001 and int(a[2])in packets:
            jobs.append(dict(node=int(a[0]),flow=int(a[1]),sequence=int(a[2]),generated_ns=int(a[3]),
                request_ns=int(a[4]),service_ns=int(a[5]),status=int(a[8]),attempts=int(a[9]),
                cca=int(a[10]),busy=int(a[11])))
    return dict(native_job_header=header,updates=updates,
        native_bucket_offered={','.join(map(str,k)):v for k,v in bucket_offered.items()},
        native_bucket_timely={','.join(map(str,k)):v for k,v in bucket_timely.items()},
        post225_generated_routes=[dict(source=k[0],version=k[1],path=list(k[2]),packets=n)for k,n in sorted(generated.items())],
        installation_packets_after210=list(packets.values()),installation_MAC_jobs=jobs,
        installation_budget_checks=[e for e in admissions if e['sequence']in packets],
        installation_queue_events=[e for e in queue if e.get('sequence')in packets])

def main():
    p=argparse.ArgumentParser();p.add_argument('archive',type=Path);a=p.parse_args()
    with a.archive.open('rb')as f:assert hashlib.file_digest(f,'sha256').hexdigest()=='fdf083436532c88613103363ea548f243cae0b5b525ab1cbc656ffa7d865674d'
    result={}
    with zipfile.ZipFile(a.archive)as z:
        for name in z.namelist():
            if not name.endswith('/case.json'):continue
            row=json.loads(z.read(name));c=row['configuration']
            if (int(c['topology'].split('_')[1]),c['scenario'],c['seed'])!=TARGET:continue
            prefix=str(Path(name).parent/row['id']);raw=z.read(prefix+'.controller.json');assert sha(raw)==row['hashes']['controller']
            controller=json.loads(raw);model=c['model']
            shadow=shadow_windows(controller,row)
            observed=[]
            for s in controller['steps']:
                t=s['observation']['time_ns']/NS
                if not 245<=t<320:continue
                constraints=s.get('constraints')or{};gate=constraints.get('evidence_qualified_admission')or{}
                observed.append(dict(time_s=t,service_known=s['event']['settled_service'].get('known',False),
                    service_reason=s['event']['settled_service'].get('reason'),rejection=s.get('rejection'),
                    geometry_available=gate.get('geometry_available'),evidence_allowed=gate.get('allowed'),
                    current_source_MAC_failure_eligible=any(r['eligible']for r in s['event']['source_failure_reports'].values()),
                    active_install_wait=bool(s.get('installation')and not s['installation']['closed']),
                    feedback_wait=s.get('feedback_wait'),reward_wait=s.get('reward_wait')))
            native=native_update(z,name,row)
            for window in shadow:
                if not window['shadow_known']:continue
                for f in(0,1):
                    keys=[f"{f},{window['version_by_source'][f]},{b}"for b in window['buckets']]
                    assert sum(native['native_bucket_offered'].get(k,0)for k in keys)==window['offered'][f]
                    assert sum(native['native_bucket_timely'].get(k,0)for k in keys)==window['timely'][f]
                window['independently_matched_native_version_bucket_counts']=True
            result[model]=dict(configuration=c,observed=observed,shadow=shadow,native=native)
            print('READ_EXISTING_PARTIAL_INSTALL',model,flush=True)
    assert len(result)==5
    out=dict(exploratory=True,new_simulation_runs=0,runtime_LLM_calls=0,
        source_sha256=sha(Path(__file__).read_bytes()),selected_cell=list(TARGET),
        no_control_action_executed=True,no_effectiveness_claim_from_shadow=True,models=result)
    path=ROOT/'results/partial_installation_diagnosis.json';path.write_text(json.dumps(out,indent=2)+'\n')
    small={m:dict(checks=len(v['observed']),service_reasons=dict(collections.Counter(x['service_reason']for x in v['observed'])),
        geometry_available=sum(any(x['geometry_available']or[])for x in v['observed']),
        blocked_by_evidence=sum(x['evidence_allowed']is False for x in v['observed']),
        shadow_known=sum(x['shadow_known']for x in v['shadow']),
        shadow_deficit=sum(x['shadow_known']and x['worst_timely']<.8 for x in v['shadow']),
        first_shadow_deficit=next((x for x in v['shadow']if x['shadow_known']and x['worst_timely']<.8),None),
        native=v['native'])for m,v in result.items()}
    (ROOT/'results/partial_installation_summary.json').write_text(json.dumps(small,indent=2)+'\n')
    print('COMPLETE_PARTIAL_INSTALL_DIAGNOSIS',flush=True)

if __name__=='__main__':main()
